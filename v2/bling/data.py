"""Cached market-data layer on top of yfinance.

Everything downstream consumes the `TickerBundle` produced here, so the rest
of the engine never touches yfinance directly. Bundles are cached on disk so
a full universe run can be re-run (or a backtest added) without hammering
Yahoo again.
"""
from __future__ import annotations

import pickle
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
# In-process memo over the pickle cache: (file mtime, bundle) per ticker, so
# repeat requests in the dashboard skip disk + unpickle entirely. Small cap —
# the server only ever touches holdings + a few viewed tickers; universe runs
# just churn through it without growing memory.
_MEMO_MAX = 64
_memo: dict[str, tuple[float, "TickerBundle"]] = {}
_memo_lock = threading.Lock()
FUNDAMENTALS_TTL = timedelta(days=7)
PRICES_TTL = timedelta(days=1)
PRICE_HISTORY_PERIOD = "10y"


@dataclass
class TickerBundle:
    ticker: str
    fetched_at: datetime
    info: dict = field(default_factory=dict)
    income_stmt: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    cashflow: Optional[pd.DataFrame] = None
    prices: Optional[pd.DataFrame] = None  # daily OHLCV, PRICE_HISTORY_PERIOD

    @property
    def is_usable(self) -> bool:
        return bool(self.info) and self.prices is not None and not self.prices.empty


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker.replace('/', '_')}.pkl"


def _memo_put(ticker: str, mtime: float, bundle: TickerBundle) -> None:
    with _memo_lock:
        _memo.pop(ticker, None)
        _memo[ticker] = (mtime, bundle)
        while len(_memo) > _MEMO_MAX:  # evict oldest insertion
            _memo.pop(next(iter(_memo)))


def _load_cached(ticker: str) -> Optional[TickerBundle]:
    path = _cache_path(ticker)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    with _memo_lock:
        hit = _memo.get(ticker)
    if hit is not None and hit[0] == mtime:
        return hit[1]
    try:
        with path.open("rb") as fh:
            bundle = pickle.load(fh)
    except Exception:
        return None
    if not isinstance(bundle, TickerBundle):
        return None
    _memo_put(ticker, mtime, bundle)
    return bundle


def _save_cached(bundle: TickerBundle) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(bundle.ticker)
    with path.open("wb") as fh:
        pickle.dump(bundle, fh)
    try:
        _memo_put(bundle.ticker, path.stat().st_mtime, bundle)
    except OSError:
        pass


def fetch_bundle(ticker: str, max_age: timedelta = PRICES_TTL, retries: int = 3) -> TickerBundle:
    """Return a (possibly cached) bundle of everything the engine needs."""
    cached = _load_cached(ticker)
    if cached is not None and datetime.now() - cached.fetched_at < max_age:
        return cached

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            yft = yf.Ticker(ticker)
            info = yft.info or {}
            bundle = TickerBundle(
                ticker=ticker,
                fetched_at=datetime.now(),
                info=info,
                income_stmt=yft.income_stmt,
                balance_sheet=yft.balance_sheet,
                cashflow=yft.cashflow,
                prices=yft.history(period=PRICE_HISTORY_PERIOD, auto_adjust=True),
            )
            if bundle.is_usable:
                _save_cached(bundle)
                return bundle
            last_error = ValueError("empty info or price history")
        except Exception as error:  # network hiccups, delisted tickers, rate limits
            last_error = error
        if "Too Many Requests" in str(last_error) or "Rate limited" in str(last_error):
            time.sleep(30.0 * (attempt + 1))  # 429s need a real pause, not a polite one
        else:
            time.sleep(1.5 * (attempt + 1))

    if cached is not None:  # stale beats nothing
        return cached
    return TickerBundle(ticker=ticker, fetched_at=datetime.now(), info={"_error": str(last_error)})
