"""Events & news engine — know what's coming BEFORE it hits the tape.

Three jobs, all read-only and all failure-tolerant:

- ``upcoming_events(tickers)``  — next earnings date + ex-dividend date per
  ticker, with days_until for each, so positioning can be adjusted *before*
  the event rather than explained after it.
- ``news(ticker)``              — recent headlines with age, for a quick
  "why is this moving?" glance.
- ``alerts(holdings, watch)``   — the actionable subset: holdings reporting
  within 5 days (stops gap through earnings), watch names reporting within
  3 days (don't buy into a coin-flip), and imminent ex-dividend dates.

Every yfinance touch goes through a ``_fetch_*`` seam wrapped in
try/except, so a Yahoo hiccup degrades to "no events / no news" instead of
a 500 on the dashboard. Results are cached to ``data/events_cache.json``
(TTL ~12h) because event dates move on a scale of weeks, not minutes.

Empirical notes on the installed yfinance (probed 2026-07-01, v1.5.1):

- ``Ticker.calendar`` -> plain dict. ``'Earnings Date'`` is a *list* of
  ``datetime.date`` (can be a 1-2 day window); ``'Ex-Dividend Date'`` is a
  single ``datetime.date`` and is frequently the *last* (past) ex-date on
  Oslo names, so days_until can be negative and alerts must gate on the
  future. Non-payers (LULU) simply omit the key.
- ``Ticker.get_earnings_dates`` -> DataFrame indexed by tz-aware
  Timestamps (past + next). Raises ``KeyError(['Earnings Date'])`` on thin
  Oslo names like KIT.OL — calendar still works there, hence calendar
  first, earnings-dates as fallback only.
- ``Ticker.info['exDividendDate']`` -> unix seconds; ``dividendYield`` is
  a *percent* number (3.84 == 3.84%) in this version, older versions used
  a fraction — ``_normalize_yield`` accepts both.
- ``Ticker.news`` -> list of ``{'id', 'content': {...}}`` with the payload
  nested under ``content`` (title / pubDate / provider.displayName /
  canonicalUrl.url); older yfinance returned flat items with ``title`` /
  ``publisher`` / ``link`` / ``providerPublishTime``. Both shapes parsed.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yfinance as yf

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "events_cache.json"
CACHE_TTL = timedelta(hours=12)

EARNINGS_HOLDING_WINDOW_DAYS = 5
EARNINGS_WATCH_WINDOW_DAYS = 3
EX_DIV_WINDOW_DAYS = 5

_cache_lock = threading.Lock()


# --------------------------------------------------------------------------
# yfinance seams — the ONLY places that touch the network. Each returns a
# plain-python value or None/[] on any failure; tests monkeypatch these.
# --------------------------------------------------------------------------

def _fetch_calendar(ticker: str) -> dict:
    """`Ticker.calendar` as a dict ({} on failure)."""
    try:
        cal = yf.Ticker(ticker).calendar
        return dict(cal) if cal else {}
    except Exception:
        return {}


def _fetch_next_earnings_from_dates(ticker: str) -> Optional[date]:
    """Earliest future date in `get_earnings_dates` (None on failure/thin data)."""
    try:
        df = yf.Ticker(ticker).get_earnings_dates(limit=12)
        if df is None or df.empty:
            return None
        today = date.today()
        future = sorted(ts.date() for ts in df.index if ts.date() >= today)
        return future[0] if future else None
    except Exception:  # KeyError(['Earnings Date']) on thin Oslo names, etc.
        return None


def _fetch_info_dividend_fields(ticker: str) -> dict:
    """{exDividendDate, dividendYield, trailingAnnualDividendYield} from info.

    Tries the local TickerBundle pickle cache first (no network — the engine
    already keeps info for every scored name), then live info.
    """
    try:
        from bling.data import _load_cached  # local disk only, never network

        bundle = _load_cached(ticker)
        if bundle is not None and bundle.info:
            return bundle.info
    except Exception:
        pass
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


def _fetch_news_raw(ticker: str) -> list:
    """`Ticker.news` raw list ([] on failure)."""
    try:
        return yf.Ticker(ticker).news or []
    except Exception:
        return []


# --------------------------------------------------------------------------
# Cache: one JSON file, {"events": {tkr: {...}}, "news": {tkr: {...}}}.
# Dates are stored as ISO strings; days_until is recomputed at read time so
# a 12h-old cache entry still reports the right countdown.
# --------------------------------------------------------------------------

def _load_cache() -> dict:
    try:
        with CACHE_PATH.open() as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_PATH.with_suffix(".json.tmp")
        with tmp.open("w") as fh:
            json.dump(cache, fh, indent=1, default=str)
        tmp.replace(CACHE_PATH)
    except Exception:
        pass  # cache is an optimization, never a failure


def _is_fresh(entry: dict) -> bool:
    try:
        fetched = datetime.fromisoformat(entry["fetched_at"])
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - fetched < CACHE_TTL
    except Exception:
        return False


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------

def _coerce_date(value) -> Optional[date]:
    """date / datetime / unix seconds / ISO string -> date (None if hopeless)."""
    try:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, (int, float)):
            if value <= 0:
                return None
            return datetime.fromtimestamp(value, tz=timezone.utc).date()
        if isinstance(value, str):
            return datetime.fromisoformat(value[:10]).date()
        if hasattr(value, "date"):  # pandas Timestamp
            return value.date()
    except Exception:
        return None
    return None


def _normalize_yield(value) -> Optional[float]:
    """Dividend yield as a fraction. Accepts 0.038 (old yf) or 3.84 (new yf)."""
    try:
        y = float(value)
    except (TypeError, ValueError):
        return None
    if y <= 0:
        return None
    if y > 1:  # percent-style (3.84 == 3.84%)
        y = y / 100.0
    return y if y <= 0.25 else None  # >25% is a data artifact, not a dividend


def _days_until(iso: Optional[str], today: Optional[date] = None) -> Optional[int]:
    d = _coerce_date(iso)
    if d is None:
        return None
    return (d - (today or date.today())).days


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def _build_event_entry(ticker: str) -> dict:
    """Fetch + normalize one ticker's event facts (dates as ISO strings)."""
    cal = _fetch_calendar(ticker)

    earnings = None
    raw = cal.get("Earnings Date")
    candidates = raw if isinstance(raw, (list, tuple)) else [raw]
    dates = sorted(d for d in (_coerce_date(c) for c in candidates) if d is not None)
    if dates:
        # prefer the first *future* date; a lone past date means Yahoo is stale
        future = [d for d in dates if d >= date.today()]
        earnings = future[0] if future else None
    if earnings is None:
        earnings = _fetch_next_earnings_from_dates(ticker)

    ex_div = _coerce_date(cal.get("Ex-Dividend Date"))
    div_yield = None
    info = _fetch_info_dividend_fields(ticker)
    if ex_div is None:
        ex_div = _coerce_date(info.get("exDividendDate"))
    div_yield = _normalize_yield(info.get("dividendYield"))
    if div_yield is None:
        div_yield = _normalize_yield(info.get("trailingAnnualDividendYield"))

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "earnings_date": earnings.isoformat() if earnings else None,
        "ex_dividend_date": ex_div.isoformat() if ex_div else None,
        "dividend_yield": div_yield,
    }


def upcoming_events(tickers: list[str]) -> dict[str, dict]:
    """Per-ticker event snapshot, cached ~12h.

    Returns {ticker: {earnings_date, earnings_days, ex_dividend_date,
    ex_dividend_days, dividend_yield}} — dates are ISO strings or None,
    days_until are ints (negative == past, e.g. a stale Oslo ex-date) or None.
    """
    out: dict[str, dict] = {}
    with _cache_lock:
        cache = _load_cache()
        events = cache.setdefault("events", {})
        dirty = False
        for ticker in dict.fromkeys(t for t in tickers if t):  # dedupe, keep order
            entry = events.get(ticker)
            if not (isinstance(entry, dict) and _is_fresh(entry)):
                entry = _build_event_entry(ticker)
                events[ticker] = entry
                dirty = True
            out[ticker] = {
                "earnings_date": entry.get("earnings_date"),
                "earnings_days": _days_until(entry.get("earnings_date")),
                "ex_dividend_date": entry.get("ex_dividend_date"),
                "ex_dividend_days": _days_until(entry.get("ex_dividend_date")),
                "dividend_yield": entry.get("dividend_yield"),
            }
        if dirty:
            _save_cache(cache)
    return out


def _parse_news_item(item) -> Optional[dict]:
    """One raw yfinance news item -> {title, publisher, link, published_at}."""
    if not isinstance(item, dict):
        return None
    content = item.get("content") if isinstance(item.get("content"), dict) else item

    title = content.get("title")
    if not title or not isinstance(title, str):
        return None

    publisher = None
    provider = content.get("provider")
    if isinstance(provider, dict):
        publisher = provider.get("displayName")
    if not publisher:
        pub = content.get("publisher")
        publisher = pub if isinstance(pub, str) else None

    link = None
    for key in ("canonicalUrl", "clickThroughUrl"):
        url = content.get(key)
        if isinstance(url, dict) and url.get("url"):
            link = url["url"]
            break
    if not link and isinstance(content.get("link"), str):
        link = content["link"]

    published_at = None
    pub_date = content.get("pubDate") or content.get("displayTime")
    if isinstance(pub_date, str) and pub_date:
        try:
            published_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
        except ValueError:
            published_at = None
    if published_at is None:
        ts = content.get("providerPublishTime")
        if isinstance(ts, (int, float)) and ts > 0:
            published_at = datetime.fromtimestamp(ts, tz=timezone.utc)

    return {
        "title": title.strip(),
        "publisher": publisher or "?",
        "link": link or "",
        "published_at": published_at.isoformat() if published_at else None,
    }


def news(ticker: str, limit: int = 5) -> list[dict]:
    """Recent headlines: [{title, publisher, link, age_hours}], cached ~12h.

    age_hours is a float rounded to 1 decimal, or None when the item carries
    no usable timestamp. Never raises; empty list on any failure.
    """
    if not ticker:
        return []
    with _cache_lock:
        cache = _load_cache()
        news_cache = cache.setdefault("news", {})
        entry = news_cache.get(ticker)
        if not (isinstance(entry, dict) and _is_fresh(entry)):
            items = []
            for raw in _fetch_news_raw(ticker):
                parsed = _parse_news_item(raw)
                if parsed is not None:
                    items.append(parsed)
            entry = {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "items": items,
            }
            news_cache[ticker] = entry
            _save_cache(cache)

    now = datetime.now(timezone.utc)
    out = []
    for item in entry.get("items", [])[: max(0, limit)]:
        age_hours = None
        if item.get("published_at"):
            try:
                published = datetime.fromisoformat(item["published_at"])
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                age_hours = round(max(0.0, (now - published).total_seconds() / 3600), 1)
            except ValueError:
                age_hours = None
        out.append({
            "title": item.get("title", ""),
            "publisher": item.get("publisher", "?"),
            "link": item.get("link", ""),
            "age_hours": age_hours,
        })
    return out


def alerts(holdings_tickers: list[str], watch_tickers: list[str]) -> list[dict]:
    """Actionable event alerts, soonest first.

    - holding reports earnings within 5 days  -> kind 'earnings_holding'
    - watch name reports earnings within 3 days -> kind 'earnings_watch'
    - ex-dividend within 5 days on any name with a dividend yield
      -> kind 'ex_dividend'

    Each alert: {ticker, kind, days, message}. A ticker in both lists is
    treated as a holding (the position risk is what matters).
    """
    holdings = list(dict.fromkeys(t for t in (holdings_tickers or []) if t))
    watch = [t for t in dict.fromkeys(w for w in (watch_tickers or []) if w) if t not in holdings]
    events = upcoming_events(holdings + watch)

    result: list[dict] = []
    for ticker in holdings + watch:
        ev = events.get(ticker) or {}
        e_days = ev.get("earnings_days")
        if e_days is not None:
            if ticker in holdings and 0 <= e_days <= EARNINGS_HOLDING_WINDOW_DAYS:
                when = "today" if e_days == 0 else f"in {e_days}d"
                result.append({
                    "ticker": ticker, "kind": "earnings_holding", "days": e_days,
                    "message": (
                        f"{ticker} reports earnings {when} ({ev.get('earnings_date')}) — "
                        "stops gap through earnings — size/tighten accordingly."
                    ),
                })
            elif ticker in watch and 0 <= e_days <= EARNINGS_WATCH_WINDOW_DAYS:
                when = "today" if e_days == 0 else f"in {e_days}d"
                result.append({
                    "ticker": ticker, "kind": "earnings_watch", "days": e_days,
                    "message": (
                        f"{ticker} (watch) reports earnings {when} ({ev.get('earnings_date')}) — "
                        "buying now is betting on the print; wait or size small."
                    ),
                })
        x_days = ev.get("ex_dividend_days")
        if (
            x_days is not None
            and 0 <= x_days <= EX_DIV_WINDOW_DAYS
            and ev.get("dividend_yield")
        ):
            pct = ev["dividend_yield"] * 100
            when = "today" if x_days == 0 else f"in {x_days}d"
            result.append({
                "ticker": ticker, "kind": "ex_dividend", "days": x_days,
                "message": (
                    f"{ticker} goes ex-dividend {when} ({ev.get('ex_dividend_date')}, "
                    f"~{pct:.1f}% yield) — hold through the ex-date to collect; "
                    "expect the mechanical open-gap down."
                ),
            })
    result.sort(key=lambda a: (a["days"], a["ticker"]))
    return result
