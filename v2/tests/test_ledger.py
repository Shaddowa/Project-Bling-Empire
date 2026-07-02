"""Unit tests for the trade ledger (bling/ledger.py).

Everything runs against a temp ledger file with explicit prices / index
prices / fx rates — no network, no bundle cache, no touching Hanna's real
v2/data/ledger.jsonl.
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from bling import ledger


def fake_report(ticker="AAPL", action="BUY", price=100.0, sell_guidance="HOLD",
                currency="USD", quality_score=80.0, verdict="ON_SALE", discount=0.35):
    return SimpleNamespace(
        ticker=ticker,
        action=action,
        sell_guidance=sell_guidance,
        currency=currency,
        quality=SimpleNamespace(score=quality_score),
        valuation=SimpleNamespace(price=price, verdict=verdict,
                                  discount_to_sticker=discount),
    )


def swing_row(ticker="EQNR.OL", price=300.0, currency="NOK",
              win_rate=0.7, trades=12, signal_age=2):
    return {"ticker": ticker, "name": ticker, "price": price, "currency": currency,
            "signal_age": signal_age,
            "stats": SimpleNamespace(win_rate=win_rate, trades=trades)}


class LedgerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "ledger.jsonl"
        self.addCleanup(self._tmp.cleanup)

    def lines(self):
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]


class TestSignalRecords(LedgerCase):
    def test_new_buy_recorded_once(self):
        reports = [fake_report()]
        first = ledger.record_daily_signals(reports, date="2026-07-01",
                                            index_prices={}, path=self.path)
        again = ledger.record_daily_signals(reports, date="2026-07-02",
                                            index_prices={}, path=self.path)
        self.assertEqual(first["new_buys"], 1)
        self.assertEqual(again["new_buys"], 0)  # deduped: still the same open call
        self.assertEqual(len(self.lines()), 1)

    def test_buy_snapshot_fields(self):
        ledger.record_daily_signals([fake_report()], date="2026-07-01",
                                    index_prices={"^GSPC": 5500.0}, path=self.path)
        record = self.lines()[0]
        self.assertEqual(record["kind"], "signal")
        self.assertEqual(record["event"], "BUY")
        self.assertEqual(record["mode"], "longterm")
        self.assertEqual(record["date"], "2026-07-01")
        self.assertEqual(record["price"], 100.0)
        self.assertEqual(record["currency"], "USD")
        self.assertEqual(record["quality_score"], 80.0)
        self.assertEqual(record["valuation_verdict"], "ON_SALE")
        self.assertEqual(record["discount_to_sticker"], 0.35)
        self.assertEqual(record["index_symbol"], "^GSPC")
        self.assertEqual(record["index_price"], 5500.0)
        self.assertEqual(record["status"], "open")

    def test_non_buy_and_priceless_reports_are_skipped(self):
        ledger.record_daily_signals(
            [fake_report(action="WATCH"), fake_report(ticker="X", action="BUY", price=None)],
            date="2026-07-01", index_prices={}, path=self.path)
        self.assertEqual(self.lines(), [])

    def test_swing_setup_recorded_with_stats(self):
        counts = ledger.record_daily_signals([], [swing_row()], date="2026-07-01",
                                             index_prices={"OBX.OL": 1400.0}, path=self.path)
        self.assertEqual(counts["new_swings"], 1)
        record = self.lines()[0]
        self.assertEqual(record["event"], "SWING")
        self.assertEqual(record["mode"], "swing")
        self.assertEqual(record["swing_win_rate"], 0.7)
        self.assertEqual(record["swing_trades"], 12)
        self.assertEqual(record["signal_age"], 2)
        self.assertEqual(record["index_symbol"], "OBX.OL")
        self.assertEqual(record["index_price"], 1400.0)

    def test_sell_flip_closes_open_buy_once(self):
        ledger.record_daily_signals([fake_report()], date="2026-07-01",
                                    index_prices={"^GSPC": 5000.0}, path=self.path)
        flipped = [fake_report(action="FAIR", price=120.0,
                               sell_guidance="SELL (below 200-day trend)")]
        counts = ledger.record_daily_signals(flipped, date="2026-08-01",
                                             index_prices={"^GSPC": 5100.0}, path=self.path)
        self.assertEqual(counts["sell_flips"], 1)
        record = self.lines()[0]
        self.assertEqual(record["status"], "closed")
        self.assertEqual(record["closed_date"], "2026-08-01")
        self.assertEqual(record["closed_price"], 120.0)
        self.assertEqual(record["closed_reason"], "SELL (below 200-day trend)")
        self.assertEqual(record["closed_index_price"], 5100.0)
        # already closed: the same flip does not fire again
        again = ledger.record_daily_signals(flipped, date="2026-08-02",
                                            index_prices={}, path=self.path)
        self.assertEqual(again["sell_flips"], 0)
        self.assertEqual(len(self.lines()), 1)

    def test_reopen_after_close_is_a_new_record(self):
        ledger.record_daily_signals([fake_report()], date="2026-07-01",
                                    index_prices={}, path=self.path)
        ledger.record_daily_signals([fake_report(sell_guidance="TAKE PROFIT (above sticker price)")],
                                    date="2026-08-01", index_prices={}, path=self.path)
        counts = ledger.record_daily_signals([fake_report(price=90.0)], date="2026-09-01",
                                             index_prices={}, path=self.path)
        self.assertEqual(counts["new_buys"], 1)
        records = self.lines()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["status"], "closed")
        self.assertEqual(records[1]["status"], "open")
        self.assertEqual(records[1]["price"], 90.0)

    def test_holding_sell_flip_without_open_record(self):
        record = ledger.record_sell_flip("NVDA", "SELL NOW (stop loss 90.00 hit)",
                                         price=88.0, date="2026-07-01",
                                         index_prices={"^GSPC": 5000.0}, path=self.path)
        self.assertEqual(record["event"], "SELL")
        self.assertEqual(record["status"], "closed")
        self.assertEqual(record["closed_price"], 88.0)
        # identical flip again -> deduped
        again = ledger.record_sell_flip("NVDA", "SELL NOW (stop loss 90.00 hit)",
                                        price=87.0, date="2026-07-02",
                                        index_prices={}, path=self.path)
        self.assertIsNone(again)
        self.assertEqual(len(self.lines()), 1)

    def test_record_sell_flip_closes_matching_open_record(self):
        ledger.record_daily_signals([fake_report(ticker="MSFT")], date="2026-07-01",
                                    index_prices={}, path=self.path)
        record = ledger.record_sell_flip("MSFT", "TAKE PROFIT (target 140.00 reached)",
                                         price=141.0, date="2026-07-20",
                                         index_prices={}, path=self.path)
        self.assertEqual(record["event"], "BUY")  # the original call, now closed
        self.assertEqual(record["status"], "closed")
        self.assertEqual(record["closed_price"], 141.0)
        self.assertEqual(len(self.lines()), 1)

    def test_mark_open_signals_updates_price_and_index(self):
        ledger.record_daily_signals([fake_report()], date="2026-07-01",
                                    index_prices={"^GSPC": 5000.0}, path=self.path)
        marked = ledger.mark_open_signals(prices={"AAPL": 111.0},
                                          index_prices={"^GSPC": 5250.0},
                                          date="2026-07-10", path=self.path)
        self.assertEqual(marked, 1)
        record = self.lines()[0]
        self.assertEqual(record["last_price"], 111.0)
        self.assertEqual(record["last_marked"], "2026-07-10")
        self.assertEqual(record["index_last_price"], 5250.0)
        self.assertEqual(record["status"], "open")

    def test_mark_with_missing_price_leaves_record_unmarked(self):
        ledger.record_daily_signals([fake_report()], date="2026-07-01",
                                    index_prices={}, path=self.path)
        marked = ledger.mark_open_signals(prices={}, index_prices={},
                                          date="2026-07-10", path=self.path)
        self.assertEqual(marked, 0)
        self.assertIsNone(self.lines()[0]["last_price"])

    def test_swing_time_exit_after_hold_window(self):
        ledger.record_daily_signals([], [swing_row()], date="2026-07-01",
                                    index_prices={}, path=self.path)
        ledger.mark_open_signals(prices={"EQNR.OL": 330.0}, index_prices={},
                                 date="2026-08-15", path=self.path)  # 45 days later
        record = self.lines()[0]
        self.assertEqual(record["status"], "closed")
        self.assertEqual(record["closed_price"], 330.0)
        self.assertIn("time exit", record["closed_reason"])

    def test_signals_grading_and_filters(self):
        ledger.record_daily_signals([fake_report()], date="2026-07-01",
                                    index_prices={"^GSPC": 5000.0}, path=self.path)
        ledger.mark_open_signals(prices={"AAPL": 120.0}, index_prices={"^GSPC": 5500.0},
                                 date="2026-07-20", path=self.path)
        graded = ledger.signals(status="open", path=self.path)
        self.assertEqual(len(graded), 1)
        self.assertAlmostEqual(graded[0]["return_pct"], 20.0)
        self.assertAlmostEqual(graded[0]["index_return_pct"], 10.0)
        self.assertAlmostEqual(graded[0]["alpha_pct"], 10.0)
        self.assertEqual(ledger.signals(status="closed", path=self.path), [])
        self.assertEqual(len(ledger.signals(mode="longterm", path=self.path)), 1)
        self.assertEqual(ledger.signals(mode="swing", path=self.path), [])

    def test_corrupt_line_is_skipped(self):
        self.path.write_text('{"kind": "signal", "ticker": "A", "mode": "longterm", '
                             '"status": "open", "price": 10.0}\nNOT JSON{{{\n')
        self.assertEqual(len(ledger.signals(path=self.path)), 1)
        marked = ledger.mark_open_signals(prices={"A": 12.0}, index_prices={},
                                          date="2026-07-10", path=self.path)
        self.assertEqual(marked, 1)  # and the rewrite drops only the garbage line

    def test_index_symbol_for(self):
        self.assertEqual(ledger.index_symbol_for("AAPL"), "^GSPC")
        self.assertEqual(ledger.index_symbol_for("EQNR.OL"), "OBX.OL")
        self.assertEqual(ledger.index_symbol_for("7203.T"), "^N225")
        self.assertEqual(ledger.index_symbol_for("VOLV-B.ST"), "^OMX")
        self.assertIsNone(ledger.index_symbol_for("FOO.XX"))


class TestTradeRecords(LedgerCase):
    def test_record_trade_shape(self):
        record = ledger.record_trade("eqnr.ol", "buy", 10, 250.0, date="2026-07-01",
                                     mode="longterm", note="first tranche", path=self.path)
        self.assertEqual(record["kind"], "trade")
        self.assertEqual(record["ticker"], "EQNR.OL")
        self.assertEqual(record["side"], "BUY")
        self.assertEqual(record["shares"], 10.0)
        self.assertEqual(record["price"], 250.0)
        self.assertEqual(record["date"], "2026-07-01")
        self.assertEqual(record["mode"], "longterm")
        self.assertEqual(record["note"], "first tranche")
        self.assertEqual(len(ledger.trades(path=self.path)), 1)

    def test_currency_inference_from_suffix(self):
        oslo = ledger.record_trade("KIT.OL", "BUY", 5, 40.0, date="2026-07-01",
                                   path=self.path)
        tokyo = ledger.record_trade("7203.T", "BUY", 5, 2500.0, date="2026-07-01",
                                    path=self.path)
        explicit = ledger.record_trade("SAP.DE", "BUY", 1, 180.0, date="2026-07-01",
                                       currency="EUR", path=self.path)
        self.assertEqual(oslo["currency"], "NOK")
        self.assertEqual(tokyo["currency"], "JPY")
        self.assertEqual(explicit["currency"], "EUR")

    def test_invalid_trades_raise(self):
        with self.assertRaises(ValueError):
            ledger.record_trade("AAPL", "HODL", 1, 100.0, path=self.path)
        with self.assertRaises(ValueError):
            ledger.record_trade("AAPL", "BUY", 0, 100.0, path=self.path)
        with self.assertRaises(ValueError):
            ledger.record_trade("AAPL", "BUY", 1, -5.0, path=self.path)
        with self.assertRaises(ValueError):
            ledger.record_trade("AAPL", "BUY", 1, 100.0, mode="yolo", path=self.path)
        self.assertEqual(ledger.trades(path=self.path), [])

    def test_oversell_raises(self):
        ledger.record_trade("AAPL", "BUY", 10, 100.0, date="2026-07-01", path=self.path)
        with self.assertRaises(ValueError):
            ledger.record_trade("AAPL", "SELL", 11, 120.0, date="2026-07-02", path=self.path)
        with self.assertRaises(ValueError):  # never bought at all
            ledger.record_trade("MSFT", "SELL", 1, 100.0, path=self.path)

    def test_positions_fifo_partial_sell(self):
        ledger.record_trade("AAPL", "BUY", 10, 100.0, date="2026-07-01",
                            currency="USD", path=self.path)
        ledger.record_trade("AAPL", "BUY", 10, 110.0, date="2026-07-05",
                            currency="USD", path=self.path)
        ledger.record_trade("AAPL", "SELL", 15, 120.0, date="2026-07-10",
                            currency="USD", path=self.path)
        open_positions = ledger.positions(prices={"AAPL": 130.0}, path=self.path)
        self.assertEqual(len(open_positions), 1)
        position = open_positions[0]
        self.assertEqual(position["shares"], 5.0)          # FIFO: first 10 + 5 of lot 2 gone
        self.assertEqual(position["avg_cost"], 110.0)      # what remains is lot-2 shares
        self.assertEqual(position["lots"], [{"date": "2026-07-05", "shares": 5.0,
                                             "price": 110.0}])
        self.assertEqual(position["price"], 130.0)
        self.assertEqual(position["unrealized_pnl"], 100.0)  # (130-110)*5

    def test_positions_without_price_degrades(self):
        ledger.record_trade("AAPL", "BUY", 10, 100.0, date="2026-07-01", path=self.path)
        position = ledger.positions(prices={}, path=self.path)[0]
        self.assertIsNone(position["price"])
        self.assertIsNone(position["unrealized_pnl"])
        self.assertEqual(position["cost_value"], 1000.0)

    def test_fully_sold_position_disappears(self):
        ledger.record_trade("AAPL", "BUY", 10, 100.0, date="2026-07-01", path=self.path)
        ledger.record_trade("AAPL", "SELL", 10, 120.0, date="2026-07-10", path=self.path)
        self.assertEqual(ledger.positions(prices={}, path=self.path), [])

    def test_performance_realized_fifo_and_win_rate(self):
        for ticker, buy, sell in (("WIN.OL", 100.0, 150.0), ("LOSE.OL", 100.0, 80.0)):
            ledger.record_trade(ticker, "BUY", 10, buy, date="2026-07-01",
                                currency="NOK", path=self.path)
            ledger.record_trade(ticker, "SELL", 10, sell, date="2026-07-10",
                                currency="NOK", path=self.path)
        report = ledger.performance(prices={}, index_closes={}, fx_rates={}, path=self.path)
        self.assertEqual(report["realized_pnl_nok"], 300.0)  # +500 - 200
        self.assertEqual(report["win_rate"], 0.5)
        self.assertEqual(len(report["round_trips"]), 2)
        self.assertEqual(report["total_pnl_nok"], 300.0)
        self.assertEqual(report["open_positions"], 0)

    def test_performance_nok_conversion_and_fx_missing(self):
        ledger.record_trade("AAPL", "BUY", 10, 100.0, date="2026-07-01",
                            currency="USD", path=self.path)
        ledger.record_trade("AAPL", "SELL", 10, 110.0, date="2026-07-10",
                            currency="USD", path=self.path)
        report = ledger.performance(prices={}, index_closes={},
                                    fx_rates={"USD": 10.0}, path=self.path)
        self.assertEqual(report["realized_pnl_nok"], 1000.0)  # 100 USD * 10
        self.assertEqual(report["fx_missing"], [])
        # no rate known -> falls back to 1.0 and says so instead of lying
        degraded = ledger.performance(prices={}, index_closes={}, fx_rates={},
                                      path=self.path)
        self.assertEqual(degraded["realized_pnl_nok"], 100.0)
        self.assertEqual(degraded["fx_missing"], ["USD"])

    def test_performance_unrealized_and_by_mode(self):
        ledger.record_trade("HOLD.OL", "BUY", 10, 100.0, date="2026-07-01",
                            mode="longterm", currency="NOK", path=self.path)
        ledger.record_trade("SWING.OL", "BUY", 10, 50.0, date="2026-07-02",
                            mode="swing", currency="NOK", path=self.path)
        ledger.record_trade("SWING.OL", "SELL", 10, 55.0, date="2026-07-09",
                            currency="NOK", path=self.path)
        report = ledger.performance(prices={"HOLD.OL": 120.0}, index_closes={},
                                    fx_rates={}, path=self.path)
        self.assertEqual(report["unrealized_pnl_nok"], 200.0)
        self.assertEqual(report["realized_pnl_nok"], 50.0)
        self.assertEqual(report["total_pnl_nok"], 250.0)
        longterm = report["by_mode"]["longterm"]
        swing = report["by_mode"]["swing"]
        self.assertEqual(longterm["unrealized_pnl_nok"], 200.0)
        self.assertEqual(longterm["open_positions"], 1)
        self.assertEqual(swing["realized_pnl_nok"], 50.0)   # round trip keeps its BUY mode
        self.assertEqual(swing["round_trips"], 1)
        self.assertEqual(swing["win_rate"], 1.0)

    def test_performance_vs_index(self):
        # Stock +20% while the index went +10% over the same window -> alpha +10pp.
        ledger.record_trade("AAPL", "BUY", 10, 100.0, date="2026-07-01",
                            currency="USD", path=self.path)
        ledger.record_trade("AAPL", "SELL", 10, 120.0, date="2026-07-31",
                            currency="USD", path=self.path)
        index = pd.Series([5000.0, 5250.0, 5500.0],
                          index=pd.to_datetime(["2026-07-01", "2026-07-15", "2026-07-31"]))
        report = ledger.performance(prices={}, index_closes={"^GSPC": index},
                                    fx_rates={"USD": 10.0}, path=self.path)
        trip = report["round_trips"][0]
        self.assertAlmostEqual(trip["return_pct"], 20.0)
        self.assertAlmostEqual(trip["index_return_pct"], 10.0)
        self.assertAlmostEqual(trip["alpha_pct"], 10.0)
        self.assertAlmostEqual(report["vs_index"]["return_pct"], 20.0)
        self.assertAlmostEqual(report["vs_index"]["index_return_pct"], 10.0)
        self.assertAlmostEqual(report["vs_index"]["alpha_pct"], 10.0)
        self.assertEqual(report["vs_index"]["coverage"], 1.0)

    def test_performance_vs_index_covers_open_lots(self):
        ledger.record_trade("AAPL", "BUY", 10, 100.0, date="2026-07-01",
                            currency="USD", path=self.path)
        index = pd.Series([5000.0, 5100.0],
                          index=pd.to_datetime(["2026-07-01", "2026-07-20"]))
        report = ledger.performance(prices={"AAPL": 105.0}, index_closes={"^GSPC": index},
                                    fx_rates={"USD": 10.0}, path=self.path)
        self.assertAlmostEqual(report["vs_index"]["return_pct"], 5.0)
        self.assertAlmostEqual(report["vs_index"]["index_return_pct"], 2.0)
        self.assertAlmostEqual(report["vs_index"]["alpha_pct"], 3.0)
        self.assertAlmostEqual(report["unrealized_pnl_nok"], 500.0)

    def test_performance_unpriced_open_position_reported(self):
        ledger.record_trade("MYSTERY.OL", "BUY", 5, 10.0, date="2026-07-01",
                            currency="NOK", path=self.path)
        report = ledger.performance(prices={}, index_closes={}, fx_rates={},
                                    path=self.path)
        self.assertEqual(report["unpriced"], ["MYSTERY.OL"])
        self.assertEqual(report["unrealized_pnl_nok"], 0.0)
        self.assertEqual(report["open_positions"], 1)

    def test_empty_ledger_performance(self):
        report = ledger.performance(prices={}, index_closes={}, fx_rates={},
                                    path=self.path)
        self.assertEqual(report["realized_pnl_nok"], 0.0)
        self.assertIsNone(report["win_rate"])
        self.assertEqual(report["round_trips"], [])
        self.assertIsNone(report["vs_index"]["return_pct"])


class TestMixedFile(LedgerCase):
    def test_signals_and_trades_coexist(self):
        ledger.record_daily_signals([fake_report(ticker="KIT.OL", currency="NOK",
                                                 price=40.0)],
                                    [swing_row()], date="2026-07-01",
                                    index_prices={"OBX.OL": 1400.0}, path=self.path)
        ledger.record_trade("KIT.OL", "BUY", 25, 40.0, date="2026-07-01",
                            currency="NOK", path=self.path)
        self.assertEqual(len(ledger.signals(path=self.path)), 2)
        self.assertEqual(len(ledger.trades(path=self.path)), 1)
        self.assertEqual(len(ledger.positions(prices={}, path=self.path)), 1)
        # marking signals does not disturb trade records
        ledger.mark_open_signals(prices={"KIT.OL": 44.0, "EQNR.OL": 310.0},
                                 index_prices={}, date="2026-07-05", path=self.path)
        self.assertEqual(len(ledger.trades(path=self.path)), 1)
        graded = ledger.signals(mode="longterm", path=self.path)[0]
        self.assertAlmostEqual(graded["return_pct"], 10.0)


if __name__ == "__main__":
    unittest.main()
