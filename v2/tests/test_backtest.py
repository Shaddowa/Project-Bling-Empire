import unittest

import numpy as np
import pandas as pd

from bling.backtest import (
    TRANSACTION_COST,
    position_series,
    strategy_returns,
    summarize,
)


def make_prices(closes):
    index = pd.date_range("2022-01-03", periods=len(closes), freq="B")
    close = pd.Series(closes, index=index, dtype=float)
    return pd.DataFrame({
        "Close": close,
        "High": close * 1.01,
        "Low": close * 0.99,
        "Open": close,
        "Volume": 1_000_000,
    })


def up_down(days_up=350, days_down=150):
    i = np.arange(days_up)
    up = 50.0 * np.exp(0.00005 * i ** 2)
    down = up[-1] * np.linspace(1.0, 0.55, days_down)
    return np.concatenate([up, down])


class TestCostMath(unittest.TestCase):
    def test_total_cost_equals_cost_rate_times_position_changes(self):
        prices = make_prices(up_down())
        gross = strategy_returns(prices, cost=0.0)
        net = strategy_returns(prices, cost=TRANSACTION_COST)
        position = position_series(prices).reindex(gross.index).fillna(0.0)
        legs = position.diff().abs().fillna(position).sum()
        self.assertGreater(legs, 0)  # the up-down path must actually trade
        self.assertAlmostEqual(float((gross - net).sum()), float(legs * TRANSACTION_COST), places=12)

    def test_costs_hit_only_on_position_changes(self):
        prices = make_prices(up_down())
        gross = strategy_returns(prices, cost=0.0)
        net = strategy_returns(prices, cost=TRANSACTION_COST)
        diff = (gross - net).round(12)
        position = position_series(prices).reindex(gross.index).fillna(0.0)
        changes = position.diff().abs().fillna(position) > 0
        self.assertTrue((diff[~changes].dropna() == 0.0).all())
        self.assertTrue((diff[changes].dropna() > 0.0).all())

    def test_full_round_trip_costs_two_sides(self):
        prices = make_prices(up_down())
        position = position_series(prices)
        self.assertEqual(float(position.iloc[-1]), 0.0)   # exited on the trend break
        self.assertEqual(float(position.max()), 1.0)      # and was in at some point
        legs = position.diff().abs().fillna(position).sum()
        self.assertEqual(float(legs) % 2, 0.0)            # entries and exits pair up


class TestSummarize(unittest.TestCase):
    def index(self, n):
        return pd.date_range("2020-01-01", periods=n, freq="B")

    def test_empty_returns_report_zeros_not_nan(self):
        m = summarize(pd.Series(dtype=float), "empty")
        self.assertEqual(m.years, 0.0)
        self.assertIsNone(m.cagr)
        self.assertEqual(m.max_drawdown, 0.0)
        self.assertIsNone(m.sharpe)

    def test_single_observation_is_safe(self):
        m = summarize(pd.Series([0.01], index=self.index(1)), "one")
        self.assertEqual(m.years, 0.0)
        self.assertIsNone(m.cagr)
        self.assertFalse(np.isnan(m.max_drawdown))

    def test_constant_positive_returns(self):
        returns = pd.Series(0.001, index=pd.date_range("2020-01-01", "2021-12-31", freq="B"))
        m = summarize(returns, "steady")
        self.assertGreater(m.cagr, 0.0)
        self.assertEqual(m.max_drawdown, 0.0)   # never below the running peak
        self.assertIsNone(m.sharpe)             # zero volatility: sharpe undefined
        self.assertEqual(m.time_in_market, 1.0)

    def test_drawdown_measures_the_dip(self):
        returns = pd.Series([0.0, -0.2, 0.05], index=self.index(3))
        m = summarize(returns, "dip")
        self.assertAlmostEqual(m.max_drawdown, -0.2, places=9)

    def test_calendar_years_not_row_count(self):
        # 2 calendar years of daily rows -> ~2.0y even with 522 rows
        returns = pd.Series(0.0005, index=pd.date_range("2020-01-01", "2021-12-31", freq="B"))
        m = summarize(returns, "cal")
        self.assertAlmostEqual(m.years, 2.0, delta=0.1)

    def test_position_share_reported(self):
        returns = pd.Series(0.001, index=self.index(4))
        position = pd.Series([0.0, 1.0, 1.0, 0.0], index=self.index(4))
        m = summarize(returns, "pos", position=position)
        self.assertEqual(m.time_in_market, 0.5)

    def test_wipeout_has_no_cagr(self):
        returns = pd.Series([-1.0, 0.0], index=self.index(2))
        m = summarize(returns, "wipe")
        self.assertIsNone(m.cagr)
        self.assertEqual(m.max_drawdown, -1.0)


if __name__ == "__main__":
    unittest.main()
