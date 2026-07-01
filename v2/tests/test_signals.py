import unittest

import numpy as np
import pandas as pd

from bling.signals import assess_signals, composite_signal, tool_states


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


def accelerating_up(days=300):
    # Constant-slope series make MACD/stochastic exactly tie their signal
    # lines; accelerating trends behave like real trending prices.
    i = np.arange(days)
    return 50.0 * np.exp(0.00005 * i ** 2)


def accelerating_down(days=300):
    # Downward parabola: the *absolute* decline must steepen, otherwise the
    # MACD line curls back above its signal near the end.
    i = np.arange(days)
    return 150.0 - (i / 32.0) ** 2


class TestSignals(unittest.TestCase):
    def test_steady_uptrend_is_buy(self):
        prices = make_prices(accelerating_up())
        result = assess_signals("UP", prices)
        self.assertEqual(result.signal, "BUY")
        self.assertTrue(result.macd_bullish)
        self.assertTrue(result.above_200_sma)

    def test_steady_downtrend_is_sell(self):
        prices = make_prices(accelerating_down())
        result = assess_signals("DOWN", prices)
        self.assertEqual(result.signal, "SELL")
        self.assertFalse(result.above_200_sma)

    def test_short_history_is_unknown(self):
        result = assess_signals("SHORT", make_prices(np.linspace(50, 60, 30)))
        self.assertEqual(result.signal, "UNKNOWN")

    def test_composite_needs_all_three_for_buy(self):
        prices = make_prices(accelerating_up())
        states = tool_states(prices).dropna()
        states.loc[states.index[-1], "macd"] = False  # one tool disagrees
        self.assertEqual(composite_signal(states).iloc[-1], "HOLD")

    def test_signal_age_counts_consecutive_days(self):
        prices = make_prices(accelerating_up())
        result = assess_signals("UP", prices)
        self.assertGreater(result.days_in_current_signal, 1)


class TestBacktestPlumbing(unittest.TestCase):
    def test_no_lookahead_and_costs_charged(self):
        from bling.backtest import strategy_returns, position_series
        prices = make_prices(accelerating_up())
        position = position_series(prices)
        self.assertEqual(set(position.unique()) - {0.0, 1.0}, set())
        net = strategy_returns(prices, cost=0.0015)
        gross = strategy_returns(prices, cost=0.0)
        self.assertLess(net.sum(), gross.sum())  # costs must bite
        # First day a position exists produces no return yet (entered at that close).
        first_day_in = position[position == 1.0].index[0]
        self.assertEqual(position.shift(1).fillna(0.0).loc[first_day_in], 0.0)


if __name__ == "__main__":
    unittest.main()
