"""Tests for bling.events — fixture data only, no network.

All yfinance access in bling.events goes through the `_fetch_*` seams;
these tests monkeypatch those seams and point CACHE_PATH at a temp file,
so a run can never touch Yahoo or the real data/events_cache.json.
"""
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from bling import events


def _iso(days_from_now: int) -> str:
    return (date.today() + timedelta(days=days_from_now)).isoformat()


class EventsTestCase(unittest.TestCase):
    """Shared temp cache + seam patches."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache_path = Path(self.tmp.name) / "events_cache.json"
        patcher = mock.patch.object(events, "CACHE_PATH", self.cache_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def patch_fetch(self, calendar=None, earnings_dates=None, info=None, news_raw=None):
        for name, value in [
            ("_fetch_calendar", calendar if calendar is not None else {}),
            ("_fetch_next_earnings_from_dates", earnings_dates),
            ("_fetch_info_dividend_fields", info if info is not None else {}),
            ("_fetch_news_raw", news_raw if news_raw is not None else []),
        ]:
            p = mock.patch.object(events, name, mock.Mock(return_value=value))
            setattr(self, name.lstrip("_"), p.start())
            self.addCleanup(p.stop)


class TestUpcomingEvents(EventsTestCase):
    def test_calendar_shape_like_orkla(self):
        # Real shape from the installed yfinance for ORK.OL: list of dates for
        # earnings, single (often PAST) date for ex-dividend.
        self.patch_fetch(
            calendar={
                "Earnings Date": [date.today() + timedelta(days=50)],
                "Ex-Dividend Date": date.today() - timedelta(days=68),
            },
            info={"dividendYield": 3.84},  # new-yf percent style
        )
        out = events.upcoming_events(["ORK.OL"])
        ev = out["ORK.OL"]
        self.assertEqual(ev["earnings_date"], _iso(50))
        self.assertEqual(ev["earnings_days"], 50)
        self.assertEqual(ev["ex_dividend_days"], -68)  # past ex-date kept, negative
        self.assertAlmostEqual(ev["dividend_yield"], 0.0384)

    def test_earnings_window_prefers_first_future_date(self):
        self.patch_fetch(calendar={"Earnings Date": [_iso(4), _iso(5)]})
        ev = events.upcoming_events(["LULU"])["LULU"]
        self.assertEqual(ev["earnings_days"], 4)

    def test_stale_calendar_falls_back_to_earnings_dates(self):
        # Calendar only has a past date -> use get_earnings_dates fallback.
        self.patch_fetch(
            calendar={"Earnings Date": [date.today() - timedelta(days=30)]},
            earnings_dates=date.today() + timedelta(days=61),
        )
        ev = events.upcoming_events(["KIT.OL"])["KIT.OL"]
        self.assertEqual(ev["earnings_days"], 61)

    def test_thin_oslo_name_degrades_to_none(self):
        # Everything fails / empty (KeyError inside the seams returns {}/None).
        self.patch_fetch()
        ev = events.upcoming_events(["THIN.OL"])["THIN.OL"]
        self.assertEqual(
            ev,
            {
                "earnings_date": None,
                "earnings_days": None,
                "ex_dividend_date": None,
                "ex_dividend_days": None,
                "dividend_yield": None,
            },
        )

    def test_ex_div_falls_back_to_info_unix_timestamp(self):
        target = datetime.now(timezone.utc) + timedelta(days=3)
        self.patch_fetch(
            calendar={},
            info={"exDividendDate": int(target.timestamp()), "dividendYield": 0.0056},
        )
        ev = events.upcoming_events(["KIT.OL"])["KIT.OL"]
        self.assertIsNotNone(ev["ex_dividend_date"])
        self.assertIn(ev["ex_dividend_days"], (2, 3))  # UTC date rounding
        self.assertAlmostEqual(ev["dividend_yield"], 0.0056)  # old-yf fraction kept

    def test_absurd_yield_treated_as_artifact(self):
        self.patch_fetch(info={"dividendYield": 68.0})  # 68% "yield" = bad data
        ev = events.upcoming_events(["X"])["X"]
        self.assertIsNone(ev["dividend_yield"])

    def test_cache_written_and_reused_within_ttl(self):
        self.patch_fetch(calendar={"Earnings Date": [_iso(10)]})
        events.upcoming_events(["LULU"])
        events.upcoming_events(["LULU"])
        self.assertEqual(self.fetch_calendar.call_count, 1)  # second call = cache hit
        on_disk = json.loads(self.cache_path.read_text())
        self.assertEqual(on_disk["events"]["LULU"]["earnings_date"], _iso(10))

    def test_expired_cache_refetches(self):
        self.patch_fetch(calendar={"Earnings Date": [_iso(10)]})
        events.upcoming_events(["LULU"])
        stale = json.loads(self.cache_path.read_text())
        old = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
        stale["events"]["LULU"]["fetched_at"] = old
        self.cache_path.write_text(json.dumps(stale))
        events.upcoming_events(["LULU"])
        self.assertEqual(self.fetch_calendar.call_count, 2)

    def test_corrupt_cache_file_is_survived(self):
        self.cache_path.write_text("{not json")
        self.patch_fetch(calendar={"Earnings Date": [_iso(7)]})
        ev = events.upcoming_events(["LULU"])["LULU"]
        self.assertEqual(ev["earnings_days"], 7)


class TestNews(EventsTestCase):
    NEW_STYLE_ITEM = {  # real shape from installed yfinance (nested `content`)
        "id": "abc",
        "content": {
            "title": "Orkla adds Danish baker TC Brød to acquisition spree",
            "pubDate": "2026-06-17T16:08:55Z",
            "provider": {"displayName": "Just Food"},
            "canonicalUrl": {"url": "https://www.just-food.com/news/orkla-tc-brod/"},
            "clickThroughUrl": {"url": "https://finance.yahoo.com/x.html"},
        },
    }

    def test_new_style_payload_parsed(self):
        self.patch_fetch(news_raw=[self.NEW_STYLE_ITEM])
        items = events.news("ORK.OL")
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["publisher"], "Just Food")
        self.assertEqual(item["link"], "https://www.just-food.com/news/orkla-tc-brod/")
        self.assertIn("Orkla", item["title"])
        self.assertIsInstance(item["age_hours"], float)
        self.assertGreater(item["age_hours"], 0)

    def test_old_style_flat_payload_parsed(self):
        ts = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
        self.patch_fetch(news_raw=[{
            "title": "LULU beats", "publisher": "Reuters",
            "link": "https://reut.rs/x", "providerPublishTime": ts,
        }])
        item = events.news("LULU")[0]
        self.assertEqual(item["publisher"], "Reuters")
        self.assertEqual(item["link"], "https://reut.rs/x")
        self.assertAlmostEqual(item["age_hours"], 2.0, delta=0.2)

    def test_limit_and_garbage_items_skipped(self):
        good = self.NEW_STYLE_ITEM
        garbage = [None, 42, {}, {"content": {"title": None}}, {"content": "str"}]
        self.patch_fetch(news_raw=garbage + [good] * 7)
        items = events.news("ORK.OL", limit=3)
        self.assertEqual(len(items), 3)

    def test_missing_timestamp_gives_none_age(self):
        self.patch_fetch(news_raw=[{"title": "Untimed", "publisher": "X", "link": "l"}])
        self.assertIsNone(events.news("T")[0]["age_hours"])

    def test_empty_on_fetch_failure_and_blank_ticker(self):
        self.patch_fetch(news_raw=[])
        self.assertEqual(events.news("DEAD.OL"), [])
        self.assertEqual(events.news(""), [])

    def test_news_cached(self):
        self.patch_fetch(news_raw=[self.NEW_STYLE_ITEM])
        events.news("ORK.OL")
        events.news("ORK.OL")
        self.assertEqual(self.fetch_news_raw.call_count, 1)


class TestAlerts(EventsTestCase):
    def seed_events(self, mapping):
        """Pre-write the events cache so alerts() never fetches."""
        entry_base = {"fetched_at": datetime.now(timezone.utc).isoformat()}
        cache = {"events": {}}
        for tkr, fields in mapping.items():
            cache["events"][tkr] = {
                **entry_base,
                "earnings_date": fields.get("earnings"),
                "ex_dividend_date": fields.get("ex_div"),
                "dividend_yield": fields.get("yield"),
            }
        self.cache_path.write_text(json.dumps(cache))
        self.patch_fetch()  # any fetch would return empty -> test fails loudly

    def test_holding_earnings_within_5_days_alerts(self):
        self.seed_events({"ORK.OL": {"earnings": _iso(4)}})
        out = events.alerts(["ORK.OL"], [])
        self.assertEqual(len(out), 1)
        a = out[0]
        self.assertEqual((a["ticker"], a["kind"], a["days"]), ("ORK.OL", "earnings_holding", 4))
        self.assertIn("stops gap through earnings", a["message"])
        self.assertIn("size/tighten", a["message"])

    def test_holding_earnings_at_6_days_is_silent(self):
        self.seed_events({"ORK.OL": {"earnings": _iso(6)}})
        self.assertEqual(events.alerts(["ORK.OL"], []), [])

    def test_watch_window_is_3_days(self):
        self.seed_events({"LULU": {"earnings": _iso(3)}, "KIT.OL": {"earnings": _iso(4)}})
        out = events.alerts([], ["LULU", "KIT.OL"])
        self.assertEqual([a["ticker"] for a in out], ["LULU"])
        self.assertEqual(out[0]["kind"], "earnings_watch")

    def test_past_earnings_never_alerts(self):
        self.seed_events({"ORK.OL": {"earnings": _iso(-1)}})
        self.assertEqual(events.alerts(["ORK.OL"], []), [])

    def test_ex_div_requires_yield(self):
        self.seed_events({
            "KIT.OL": {"ex_div": _iso(2), "yield": 0.0066},
            "NOYIELD.OL": {"ex_div": _iso(2), "yield": None},
        })
        out = events.alerts(["KIT.OL", "NOYIELD.OL"], [])
        self.assertEqual([a["ticker"] for a in out], ["KIT.OL"])
        self.assertEqual(out[0]["kind"], "ex_dividend")
        self.assertIn("ex-dividend", out[0]["message"])

    def test_past_ex_div_is_silent(self):
        # The ORK.OL trap: calendar reports the LAST ex-date (in the past).
        self.seed_events({"ORK.OL": {"ex_div": _iso(-68), "yield": 0.0384}})
        self.assertEqual(events.alerts(["ORK.OL"], []), [])

    def test_ticker_in_both_lists_treated_as_holding(self):
        self.seed_events({"ORK.OL": {"earnings": _iso(5)}})
        out = events.alerts(["ORK.OL"], ["ORK.OL"])
        self.assertEqual(len(out), 1)  # no duplicate, holding window (5d) applies
        self.assertEqual(out[0]["kind"], "earnings_holding")

    def test_sorted_soonest_first_and_multi_kind(self):
        self.seed_events({
            "A": {"earnings": _iso(5)},
            "B": {"earnings": _iso(0), "ex_div": _iso(3), "yield": 0.02},
        })
        out = events.alerts(["A", "B"], [])
        self.assertEqual(
            [(a["ticker"], a["kind"], a["days"]) for a in out],
            [("B", "earnings_holding", 0), ("B", "ex_dividend", 3), ("A", "earnings_holding", 5)],
        )
        self.assertIn("today", out[0]["message"])

    def test_empty_inputs(self):
        self.patch_fetch()
        self.assertEqual(events.alerts([], []), [])
        self.assertEqual(events.alerts(None, None), [])


if __name__ == "__main__":
    unittest.main()
