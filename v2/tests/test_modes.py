import threading
import time
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from bling.modes import DayRow, _day_row, _num, day_view, swing_trade_stats


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
    i = np.arange(days)
    return 50.0 * np.exp(0.00005 * i ** 2)


def accelerating_down(days=300):
    i = np.arange(days)
    return 150.0 - (i / 32.0) ** 2


class TestSwingTradeStats(unittest.TestCase):
    def test_short_history_is_none(self):
        self.assertIsNone(swing_trade_stats(make_prices(np.linspace(50, 60, 100))))

    def test_uptrend_produces_winning_trades(self):
        stats = swing_trade_stats(make_prices(accelerating_up(400)))
        self.assertIsNotNone(stats)
        self.assertGreaterEqual(stats.trades, 1)
        self.assertGreater(stats.win_rate, 0.0)
        self.assertGreater(stats.strategy_return, 0.0)
        self.assertGreater(stats.hold_return, 0.0)

    def test_pure_downtrend_never_buys(self):
        stats = swing_trade_stats(make_prices(accelerating_down(400)))
        self.assertIsNotNone(stats)
        self.assertEqual(stats.trades, 0)
        self.assertIsNone(stats.win_rate)
        self.assertIsNone(stats.strategy_return)

    def test_round_trip_up_then_down(self):
        closes = np.concatenate([accelerating_up(350), accelerating_down(150)[:150] * 0 + accelerating_up(350)[-1] * np.linspace(1.0, 0.55, 150)])
        stats = swing_trade_stats(make_prices(closes))
        self.assertIsNotNone(stats)
        # the up-leg trade closed during the collapse: at least one full round trip
        self.assertGreaterEqual(stats.trades, 1)
        self.assertIsNotNone(stats.avg_trade_return)
        self.assertIsNotNone(stats.hold_return)

    def test_nan_close_days_do_not_crash_or_poison(self):
        closes = accelerating_up(400)
        prices = make_prices(closes)
        prices.iloc[250, prices.columns.get_loc("Close")] = np.nan
        stats = swing_trade_stats(prices)
        self.assertIsNotNone(stats)
        for value in (stats.win_rate, stats.avg_trade_return, stats.strategy_return, stats.hold_return):
            if value is not None:
                self.assertFalse(np.isnan(value))


def intraday_bars(prev_close=100.0, today_closes=(100.0, 101.0, 103.0, 105.0), volume=5000.0):
    prev_index = pd.date_range("2026-06-30 09:00", periods=4, freq="15min")
    today_index = pd.date_range("2026-07-01 09:00", periods=len(today_closes), freq="15min")
    closes = [prev_close] * 4 + list(today_closes)
    index = prev_index.append(today_index)
    close = pd.Series(closes, index=index, dtype=float)
    return pd.DataFrame({
        "Open": close,
        "High": close + 0.5,
        "Low": close - 0.5,
        "Close": close,
        "Volume": volume,
    })


class TestDayRow(unittest.TestCase):
    def test_breakout_above_opening_range(self):
        row = _day_row("TEST", intraday_bars())
        self.assertIsInstance(row, DayRow)
        self.assertEqual(row.price, 105.0)
        self.assertEqual(row.orb_state, "ABOVE")       # 105 > max(100,101)+0.5
        self.assertEqual(row.open_range_high, 101.5)
        self.assertEqual(row.open_range_low, 99.5)
        self.assertTrue(row.above_vwap)
        self.assertAlmostEqual(row.day_change_pct, 5.0, places=2)
        self.assertTrue(row.momentum_15m)

    def test_breakdown_below_opening_range(self):
        row = _day_row("TEST", intraday_bars(today_closes=(100.0, 99.0, 96.0, 94.0)))
        self.assertEqual(row.orb_state, "BELOW")
        self.assertFalse(row.momentum_15m)
        self.assertAlmostEqual(row.day_change_pct, -6.0, places=2)

    def test_inside_opening_range(self):
        row = _day_row("TEST", intraday_bars(today_closes=(100.0, 101.0, 100.5, 100.4)))
        self.assertEqual(row.orb_state, "INSIDE")

    def test_zero_volume_means_no_vwap_not_nan(self):
        row = _day_row("TEST", intraday_bars(volume=0.0))
        self.assertIsNotNone(row)
        self.assertIsNone(row.vwap)
        self.assertIsNone(row.above_vwap)

    def test_nan_last_close_is_unusable(self):
        bars = intraday_bars()
        bars.iloc[-1, bars.columns.get_loc("Close")] = np.nan
        self.assertIsNone(_day_row("TEST", bars))

    def test_no_previous_day_means_no_day_change(self):
        bars = intraday_bars().iloc[4:]  # today only
        row = _day_row("TEST", bars)
        self.assertIsNotNone(row)
        self.assertIsNone(row.day_change_pct)

    def test_empty_or_missing_bars(self):
        self.assertIsNone(_day_row("TEST", None))
        self.assertIsNone(_day_row("TEST", pd.DataFrame()))


class TestDayView(unittest.TestCase):
    def test_parallel_fetch_preserves_sort_contract(self):
        moves = {"A": (100.0, 101.0), "B": (100.0, 108.0), "C": (100.0, 95.0)}
        seen_threads = set()

        def fake_fetch(ticker):
            seen_threads.add(threading.get_ident())
            time.sleep(0.03)  # force overlap so the pool actually parallelizes
            prev, last = moves[ticker]
            return intraday_bars(prev_close=prev, today_closes=(prev, prev, last))

        with mock.patch("bling.modes._fetch_intraday", side_effect=fake_fetch):
            rows = day_view(["A", "B", "C"])
        self.assertEqual([r.ticker for r in rows], ["B", "A", "C"])  # day change desc
        self.assertGreater(len(seen_threads), 1)  # ran on more than one thread

    def test_failed_tickers_are_dropped_not_fatal(self):
        def fake_fetch(ticker):
            if ticker == "DEAD":
                return None
            return intraday_bars()

        with mock.patch("bling.modes._fetch_intraday", side_effect=fake_fetch):
            rows = day_view(["OK", "DEAD"])
        self.assertEqual([r.ticker for r in rows], ["OK"])

    def test_max_tickers_cap_and_empty_input(self):
        calls = []

        def fake_fetch(ticker):
            calls.append(ticker)
            return intraday_bars()

        with mock.patch("bling.modes._fetch_intraday", side_effect=fake_fetch):
            day_view([f"T{i}" for i in range(30)], max_tickers=5)
            self.assertEqual(len(calls), 5)
            self.assertEqual(day_view([]), [])


class TestNumGuard(unittest.TestCase):
    def test_num(self):
        self.assertEqual(_num(3.14), 3.14)
        self.assertIsNone(_num(float("nan")))
        self.assertIsNone(_num(float("inf")))
        self.assertIsNone(_num(None))
        self.assertIsNone(_num("junk"))


if __name__ == "__main__":
    unittest.main()
