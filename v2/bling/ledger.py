"""The trade ledger: the system's memory and report card.

One JSON-lines file (v2/data/ledger.jsonl — gitignored, it derives from
Hanna's real activity) holds two record kinds:

  signal records  what the engine SAID. Every day the refresh job runs, any
                  NEW long-term BUY, fresh swing setup, or sell-guidance flip
                  is appended once (deduped: an already-open call is never
                  re-recorded). Each record snapshots price, quality/valuation
                  and the matching benchmark-index level, and mark-to-market
                  keeps `last_price` / `index_last_price` current on open
                  records — so the app can grade calls: "+X% since signaled
                  vs the index over the same window".
  trade records   what Hanna DID. Real buys/sells via record_trade(); FIFO
                  lot matching turns them into open positions (positions())
                  and realized round trips, and performance() rolls those up:
                  realized/unrealized P&L, win rate, per-mode stats, NOK
                  conversion via bling.fx, vs-index comparison.

Design rules:
  * Append-only spirit: events are appended; only mark-to-market/close fields
    on signal records mutate, via an atomic whole-file rewrite (os.replace).
  * Reads NEVER touch the network. Current prices come from the bundle cache
    the daily screen already filled (bling.data), or from explicit `prices=`
    dicts (tests, callers with fresher data). When a dict is passed it is
    authoritative — missing symbols degrade to None, no cache fallback.
    The one exception is refresh_index_cache(), which the daily refresh job
    calls to warm the index bundles (a handful of light fetches).
  * A corrupt line in the file is skipped, never fatal.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date as _date
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from . import data as _data
from . import fx as _fx
from .universe import MARKETS, V2_ROOT

LEDGER_PATH = V2_ROOT / "data" / "ledger.jsonl"
HOME_CURRENCY = "NOK"
SWING_MAX_HOLD_DAYS = 28          # swing = days-to-weeks; time-exit keeps grading honest
TRADE_MODES = ("longterm", "swing", "day")
_SELL_PREFIXES = ("SELL", "TAKE PROFIT")
_EPS = 1e-9

# Yahoo suffix -> market key in universe.MARKETS ("" = US listings -> S&P 500).
_SUFFIX_TO_MARKET = {
    "": "sp500", ".OL": "oslo", ".ST": "sweden", ".CO": "denmark", ".HE": "finland",
    ".DE": "germany", ".L": "uk", ".PA": "france", ".AS": "netherlands",
    ".TO": "canada", ".T": "japan", ".HK": "hongkong", ".AX": "australia",
}
# Last-resort trading-currency inference when no cached bundle knows better.
_SUFFIX_CURRENCY = {
    "": "USD", ".OL": "NOK", ".ST": "SEK", ".CO": "DKK", ".HE": "EUR",
    ".DE": "EUR", ".L": "GBp", ".PA": "EUR", ".AS": "EUR",
    ".TO": "CAD", ".T": "JPY", ".HK": "HKD", ".AX": "AUD",
}


# ── file primitives ─────────────────────────────────────────────────────────

def _read(path: Path = LEDGER_PATH) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # one mangled line must not take the ledger down
        if isinstance(record, dict):
            records.append(record)
    return records


def _append(record: dict, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _rewrite(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    os.replace(tmp, path)  # atomic: readers see old or new file, never half


# ── symbol helpers ──────────────────────────────────────────────────────────

def _suffix(ticker: str) -> str:
    return "." + ticker.rsplit(".", 1)[1] if "." in ticker else ""


def index_symbol_for(ticker: str) -> Optional[str]:
    """Benchmark index symbol for a ticker's market; None when unknown."""
    market = _SUFFIX_TO_MARKET.get(_suffix(ticker))
    return MARKETS[market]["index"] if market else None


def _cached_close(symbol: str) -> Optional[float]:
    """Latest close from the disk bundle cache; NEVER fetches."""
    bundle = _data._load_cached(symbol)
    if bundle is None or bundle.prices is None or getattr(bundle.prices, "empty", True):
        return None
    closes = bundle.prices["Close"].dropna()
    return float(closes.iloc[-1]) if len(closes) else None


def _price_of(symbol: Optional[str], prices: Optional[dict]) -> Optional[float]:
    """prices dict when given (authoritative), else the bundle cache."""
    if not symbol:
        return None
    if prices is not None:
        value = prices.get(symbol)
        return float(value) if value else None
    return _cached_close(symbol)


def refresh_index_cache(tickers: Iterable[str],
                        max_age: timedelta = timedelta(hours=12)) -> list[str]:
    """Warm the bundle cache for every benchmark index the tickers map to.

    The ONE network-touching function here — the daily refresh job calls it
    right after screening so signal records and performance() can read index
    levels from cache. Returns the symbols it ensured (best effort)."""
    warmed = []
    for symbol in sorted({s for s in (index_symbol_for(t) for t in tickers) if s}):
        try:
            bundle = _data.fetch_bundle(symbol, max_age=max_age)
            if bundle.is_usable:
                warmed.append(symbol)
        except Exception:
            continue
    return warmed


def _iso(value=None) -> str:
    if value is None:
        return _date.today().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, _date):
        return value.isoformat()
    return str(value)[:10]


# ── signal records ──────────────────────────────────────────────────────────

def _new_signal_record(*, ticker: str, event: str, mode: str, date: str,
                       price: Optional[float], currency: Optional[str] = None,
                       quality_score=None, valuation_verdict=None, discount_to_sticker=None,
                       swing_win_rate=None, swing_trades=None, signal_age=None,
                       index_symbol: Optional[str] = None, index_price=None,
                       status: str = "open") -> dict:
    return {
        "kind": "signal", "id": f"sig-{uuid.uuid4().hex[:8]}",
        "ticker": ticker, "event": event, "mode": mode, "date": date,
        "price": float(price) if price else None,
        "currency": currency or _SUFFIX_CURRENCY.get(_suffix(ticker)),
        "quality_score": quality_score, "valuation_verdict": valuation_verdict,
        "discount_to_sticker": discount_to_sticker,
        "swing_win_rate": swing_win_rate, "swing_trades": swing_trades,
        "signal_age": signal_age,
        "index_symbol": index_symbol,
        "index_price": float(index_price) if index_price else None,
        "status": status, "last_price": None, "last_marked": None,
        "index_last_price": None,
        "closed_date": None, "closed_price": None, "closed_reason": None,
        "closed_index_price": None,
    }


def _close_record(record: dict, day: str, price: Optional[float], reason: str,
                  index_prices: Optional[dict]) -> None:
    record["status"] = "closed"
    record["closed_date"] = day
    record["closed_price"] = (float(price) if price
                              else record.get("last_price") or record.get("price"))
    record["closed_reason"] = reason
    index_price = _price_of(record.get("index_symbol"), index_prices)
    record["closed_index_price"] = index_price or record.get("index_last_price")


def _stat(stats, name):
    if stats is None:
        return None
    if isinstance(stats, dict):
        return stats.get(name)
    return getattr(stats, name, None)


def record_daily_signals(reports: Iterable, swing_rows: Iterable[dict] = (),
                         date=None, index_prices: Optional[dict] = None,
                         path: Path = LEDGER_PATH) -> dict:
    """One post-screen call: append new BUY/SWING events, close on SELL flips.

    `reports` are engine TickerReport-alikes (needs .ticker, .action,
    .sell_guidance, .currency, .quality.score, .valuation.{price,verdict,
    discount_to_sticker}); `swing_rows` are modes.swing_scan() rows.
    Dedupe: a ticker+mode with an OPEN record is never re-recorded; a sell
    flip closes it (recorded once — already-closed records don't re-flip).
    Returns {"new_buys": n, "new_swings": n, "sell_flips": n}.
    """
    day = _iso(date)
    records = _read(path)
    open_by_key: dict[tuple[str, str], dict] = {}
    for record in records:
        if record.get("kind") == "signal" and record.get("status") == "open":
            open_by_key[(record.get("ticker"), record.get("mode"))] = record

    appended: list[dict] = []
    closed_any = False
    counts = {"new_buys": 0, "new_swings": 0, "sell_flips": 0}

    for report in reports:
        ticker = report.ticker
        key = (ticker, "longterm")
        valuation = getattr(report, "valuation", None)
        price = getattr(valuation, "price", None)
        guidance = getattr(report, "sell_guidance", "") or ""
        open_record = open_by_key.get(key)
        if open_record is not None and guidance.startswith(_SELL_PREFIXES):
            _close_record(open_record, day, price, guidance, index_prices)
            open_by_key.pop(key)
            closed_any = True
            counts["sell_flips"] += 1
        elif open_record is None and getattr(report, "action", "") == "BUY" and price:
            symbol = index_symbol_for(ticker)
            record = _new_signal_record(
                ticker=ticker, event="BUY", mode="longterm", date=day,
                price=price, currency=getattr(report, "currency", None),
                quality_score=getattr(getattr(report, "quality", None), "score", None),
                valuation_verdict=getattr(valuation, "verdict", None),
                discount_to_sticker=getattr(valuation, "discount_to_sticker", None),
                index_symbol=symbol, index_price=_price_of(symbol, index_prices),
            )
            appended.append(record)
            open_by_key[key] = record
            counts["new_buys"] += 1

    for row in swing_rows:
        ticker, price = row.get("ticker"), row.get("price")
        if not ticker or not price or (ticker, "swing") in open_by_key:
            continue
        stats = row.get("stats")
        symbol = index_symbol_for(ticker)
        record = _new_signal_record(
            ticker=ticker, event="SWING", mode="swing", date=day,
            price=price, currency=row.get("currency"),
            swing_win_rate=_stat(stats, "win_rate"), swing_trades=_stat(stats, "trades"),
            signal_age=row.get("signal_age"),
            index_symbol=symbol, index_price=_price_of(symbol, index_prices),
        )
        appended.append(record)
        open_by_key[(ticker, "swing")] = record
        counts["new_swings"] += 1

    if closed_any:
        _rewrite(records + appended, path)
    else:
        for record in appended:
            _append(record, path)
    return counts


def record_sell_flip(ticker: str, guidance: str, price: Optional[float] = None,
                     date=None, mode: str = "longterm",
                     index_prices: Optional[dict] = None,
                     path: Path = LEDGER_PATH) -> Optional[dict]:
    """A sell-guidance flip (e.g. on a real holding). Closes the open signal
    record for ticker+mode when there is one; otherwise appends a standalone
    (already-closed) SELL event so the flip is still on the record. Deduped:
    an identical flip right after the last one is a no-op (returns None)."""
    day = _iso(date)
    records = _read(path)
    open_record, latest = None, None
    for record in records:
        if record.get("kind") == "signal" and record.get("ticker") == ticker \
                and record.get("mode") == mode:
            latest = record
            if record.get("status") == "open":
                open_record = record
    if open_record is not None:
        _close_record(open_record, day, price, guidance, index_prices)
        _rewrite(records, path)
        return open_record
    if latest is not None and latest.get("event") == "SELL" \
            and latest.get("closed_reason") == guidance:
        return None  # same flip already recorded, nothing new happened
    price = price if price else _price_of(ticker, None)
    symbol = index_symbol_for(ticker)
    record = _new_signal_record(ticker=ticker, event="SELL", mode=mode, date=day,
                                price=price, index_symbol=symbol,
                                index_price=_price_of(symbol, index_prices),
                                status="closed")
    record.update(closed_date=day, closed_price=record["price"], closed_reason=guidance,
                  closed_index_price=record["index_price"])
    return _append(record, path)


def mark_open_signals(prices: Optional[dict] = None, index_prices: Optional[dict] = None,
                      date=None, path: Path = LEDGER_PATH) -> int:
    """Mark-to-market every open signal record (last_price/index_last_price)
    from the given dicts or the bundle cache — no network. Swing records past
    SWING_MAX_HOLD_DAYS are time-exited at their last mark, so days-to-weeks
    calls get graded on a days-to-weeks window. Returns records marked."""
    day = _iso(date)
    records = _read(path)
    marked, changed = 0, False
    for record in records:
        if record.get("kind") != "signal" or record.get("status") != "open":
            continue
        price = _price_of(record.get("ticker"), prices)
        if price is not None:
            record["last_price"], record["last_marked"] = price, day
            marked += 1
            changed = True
        index_price = _price_of(record.get("index_symbol"), index_prices)
        if index_price is not None:
            record["index_last_price"] = index_price
            changed = True
        if record.get("mode") == "swing" and record.get("date"):
            try:
                age_days = (_date.fromisoformat(day) - _date.fromisoformat(record["date"])).days
            except ValueError:
                age_days = 0
            if age_days > SWING_MAX_HOLD_DAYS:
                _close_record(record, day, record.get("last_price"),
                              f"time exit (swing window > {SWING_MAX_HOLD_DAYS}d)", index_prices)
                changed = True
    if changed:
        _rewrite(records, path)
    return marked


def signals(status: Optional[str] = None, mode: Optional[str] = None,
            path: Path = LEDGER_PATH) -> list[dict]:
    """Signal records (newest first) with the grading pre-computed:
    return_pct (call price -> latest/close), index_return_pct (same window),
    alpha_pct (call minus index). None where data is missing."""
    out = []
    for record in _read(path):
        if record.get("kind") != "signal":
            continue
        if status and record.get("status") != status:
            continue
        if mode and record.get("mode") != mode:
            continue
        closed = record.get("status") == "closed"
        now_price = record.get("closed_price") if closed else record.get("last_price")
        now_index = record.get("closed_index_price") if closed else record.get("index_last_price")
        return_pct = (round((now_price / record["price"] - 1.0) * 100.0, 2)
                      if now_price and record.get("price") else None)
        index_return_pct = (round((now_index / record["index_price"] - 1.0) * 100.0, 2)
                            if now_index and record.get("index_price") else None)
        alpha_pct = (round(return_pct - index_return_pct, 2)
                     if return_pct is not None and index_return_pct is not None else None)
        out.append({**record, "return_pct": return_pct,
                    "index_return_pct": index_return_pct, "alpha_pct": alpha_pct})
    out.sort(key=lambda r: (r.get("date") or "", r.get("id") or ""), reverse=True)
    return out


# ── trade records ───────────────────────────────────────────────────────────

def record_trade(ticker: str, side: str, shares: float, price: float,
                 date=None, mode: str = "longterm", note: str = "",
                 currency: Optional[str] = None, path: Path = LEDGER_PATH) -> dict:
    """Append one real trade. side is BUY/SELL; a SELL may not exceed the
    open FIFO position (typo protection — this is a personal ledger, not a
    margin account). Currency: explicit > cached bundle info > suffix map."""
    side = str(side).strip().upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")
    shares, price = float(shares), float(price)
    if shares <= 0 or price <= 0:
        raise ValueError("shares and price must both be positive")
    if mode not in TRADE_MODES:
        raise ValueError(f"mode must be one of {TRADE_MODES}, got {mode!r}")
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("ticker is required")

    if side == "SELL":
        lots, _ = _fifo([r for r in _read(path) if r.get("kind") == "trade"])
        held = sum(lot["shares"] for lot in lots.get(ticker, []))
        if shares > held + _EPS:
            raise ValueError(f"cannot sell {shares:g} {ticker}: only {held:g} held")

    if currency is None:
        bundle = _data._load_cached(ticker)
        currency = (bundle.info.get("currency") if bundle is not None and bundle.info
                    else None) or _SUFFIX_CURRENCY.get(_suffix(ticker))

    return _append({
        "kind": "trade", "id": f"trd-{uuid.uuid4().hex[:8]}",
        "ticker": ticker, "side": side, "shares": shares, "price": price,
        "date": _iso(date), "mode": mode, "note": note or "", "currency": currency,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    }, path)


def trades(path: Path = LEDGER_PATH) -> list[dict]:
    """All trade records in file order (chronological per recording)."""
    return [r for r in _read(path) if r.get("kind") == "trade"]


def _fifo(trade_records: list[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
    """FIFO lot matching -> (open lots per ticker, realized round trips)."""
    lots: dict[str, list[dict]] = {}
    round_trips: list[dict] = []
    ordered = sorted(enumerate(trade_records), key=lambda p: (p[1].get("date", ""), p[0]))
    for _, trade in ordered:
        ticker = trade["ticker"]
        if trade["side"] == "BUY":
            lots.setdefault(ticker, []).append({
                "date": trade.get("date"), "shares": float(trade["shares"]),
                "price": float(trade["price"]), "mode": trade.get("mode", "longterm"),
                "currency": trade.get("currency"),
            })
            continue
        remaining = float(trade["shares"])
        queue = lots.get(ticker, [])
        while remaining > _EPS and queue:
            lot = queue[0]
            take = min(lot["shares"], remaining)
            sell_price = float(trade["price"])
            round_trips.append({
                "ticker": ticker, "mode": lot["mode"],
                "currency": lot["currency"] or trade.get("currency"),
                "shares": round(take, 6),
                "buy_date": lot["date"], "buy_price": lot["price"],
                "sell_date": trade.get("date"), "sell_price": sell_price,
                "pnl_native": round((sell_price - lot["price"]) * take, 4),
                "return_pct": (round((sell_price / lot["price"] - 1.0) * 100.0, 2)
                               if lot["price"] else None),
            })
            lot["shares"] -= take
            remaining -= take
            if lot["shares"] <= _EPS:
                queue.pop(0)
        # any excess (hand-edited file) is dropped rather than fabricated short
    return lots, round_trips


def positions(prices: Optional[dict] = None, path: Path = LEDGER_PATH) -> list[dict]:
    """Open lots per ticker (FIFO remainders), marked with current price when
    known (prices dict when given, else the bundle cache; never network)."""
    lots_by_ticker, _ = _fifo(trades(path))
    out = []
    for ticker, lots in sorted(lots_by_ticker.items()):
        open_lots = [lot for lot in lots if lot["shares"] > _EPS]
        if not open_lots:
            continue
        shares = sum(lot["shares"] for lot in open_lots)
        cost = sum(lot["shares"] * lot["price"] for lot in open_lots)
        price = _price_of(ticker, prices)
        value = price * shares if price else None
        out.append({
            "ticker": ticker, "shares": round(shares, 6),
            "avg_cost": round(cost / shares, 4), "cost_value": round(cost, 2),
            "currency": open_lots[-1]["currency"], "mode": open_lots[-1]["mode"],
            "lots": [{"date": lot["date"], "shares": round(lot["shares"], 6),
                      "price": lot["price"]} for lot in open_lots],
            "price": price, "value": round(value, 2) if value is not None else None,
            "unrealized_pnl": round(value - cost, 2) if value is not None else None,
            "unrealized_pct": (round((value / cost - 1.0) * 100.0, 2)
                               if value is not None and cost else None),
        })
    return out


def _close_series(symbol: str, index_closes: Optional[dict]):
    if index_closes is not None:
        return index_closes.get(symbol)
    bundle = _data._load_cached(symbol)
    if bundle is None or bundle.prices is None or getattr(bundle.prices, "empty", True):
        return None
    return bundle.prices["Close"].dropna()


def _asof(series, day: Optional[str]) -> Optional[float]:
    """Last close at or before `day` (YYYY-MM-DD); None when out of range."""
    if series is None or not day or not len(series):
        return None
    try:
        if getattr(series.index, "tz", None) is not None:
            series = series.copy()
            series.index = series.index.tz_localize(None)
        window = series.loc[:pd.Timestamp(day)]
        return float(window.iloc[-1]) if len(window) else None
    except Exception:
        return None


def performance(prices: Optional[dict] = None, index_closes: Optional[dict] = None,
                fx_rates: Optional[dict] = None, path: Path = LEDGER_PATH) -> dict:
    """The report card over Hanna's REAL trades.

    Realized P&L (FIFO round trips) + unrealized (open lots vs current price),
    win rate, per-mode stats, everything converted to NOK via bling.fx (or the
    `fx_rates` currency->NOK dict — tests, offline). vs_index compares the
    cost-weighted portfolio return against each lot's benchmark index over the
    same holding window, using cached bundle prices (`index_closes` maps
    index symbol -> close Series to override). Missing FX degrades to rate 1.0
    and is reported in fx_missing rather than poisoning the totals."""
    lots_by_ticker, round_trips = _fifo(trades(path))

    fx_used: dict[str, Optional[float]] = {}
    fx_missing: set[str] = set()

    def to_nok(amount: Optional[float], currency: Optional[str]) -> Optional[float]:
        if amount is None:
            return None
        cur = currency or HOME_CURRENCY
        if cur == HOME_CURRENCY:
            return amount
        if cur not in fx_used:
            fx_used[cur] = (fx_rates.get(cur) if fx_rates is not None
                            else _fx.rate(cur, HOME_CURRENCY))
        rate = fx_used[cur]
        if not rate:
            fx_missing.add(cur)
            rate = 1.0
        return amount * rate

    def mode_bucket(stats: dict, mode: str) -> dict:
        return stats.setdefault(mode, {"realized_pnl_nok": 0.0, "unrealized_pnl_nok": 0.0,
                                       "round_trips": 0, "wins": 0, "win_rate": None,
                                       "open_positions": 0})

    by_mode: dict[str, dict] = {}
    weighted: list[tuple[float, float, Optional[float]]] = []  # (cost_nok, ret, index_ret)
    realized_nok, wins = 0.0, 0

    for trip in round_trips:
        pnl_nok = to_nok(trip["pnl_native"], trip["currency"]) or 0.0
        trip["pnl_nok"] = round(pnl_nok, 2)
        series = _close_series(index_symbol_for(trip["ticker"]) or "", index_closes)
        index_start = _asof(series, trip["buy_date"])
        index_end = _asof(series, trip["sell_date"])
        trip["index_return_pct"] = (round((index_end / index_start - 1.0) * 100.0, 2)
                                    if index_start and index_end else None)
        trip["alpha_pct"] = (round(trip["return_pct"] - trip["index_return_pct"], 2)
                             if trip["return_pct"] is not None
                             and trip["index_return_pct"] is not None else None)
        realized_nok += pnl_nok
        won = trip["pnl_native"] > 0
        wins += won
        bucket = mode_bucket(by_mode, trip["mode"])
        bucket["realized_pnl_nok"] += pnl_nok
        bucket["round_trips"] += 1
        bucket["wins"] += won
        cost_nok = to_nok(trip["buy_price"] * trip["shares"], trip["currency"])
        if cost_nok:
            weighted.append((cost_nok, trip["sell_price"] / trip["buy_price"] - 1.0,
                             (index_end / index_start - 1.0) if index_start and index_end else None))

    unrealized_nok: Optional[float] = 0.0
    open_cost_nok, open_value_nok = 0.0, 0.0
    unpriced: list[str] = []
    open_positions = 0
    for ticker, lots in sorted(lots_by_ticker.items()):
        open_lots = [lot for lot in lots if lot["shares"] > _EPS]
        if not open_lots:
            continue
        open_positions += 1
        mode_bucket(by_mode, open_lots[-1]["mode"])["open_positions"] += 1
        price = _price_of(ticker, prices)
        if price is None:
            unpriced.append(ticker)
            continue
        series = _close_series(index_symbol_for(ticker) or "", index_closes)
        index_now = float(series.iloc[-1]) if series is not None and len(series) else None
        for lot in open_lots:
            pnl_nok = to_nok((price - lot["price"]) * lot["shares"], lot["currency"]) or 0.0
            unrealized_nok += pnl_nok
            mode_bucket(by_mode, lot["mode"])["unrealized_pnl_nok"] += pnl_nok
            cost_nok = to_nok(lot["price"] * lot["shares"], lot["currency"])
            open_cost_nok += cost_nok or 0.0
            open_value_nok += to_nok(price * lot["shares"], lot["currency"]) or 0.0
            index_start = _asof(series, lot["date"])
            if cost_nok:
                weighted.append((cost_nok, price / lot["price"] - 1.0,
                                 (index_now / index_start - 1.0)
                                 if index_start and index_now else None))

    for bucket in by_mode.values():
        bucket["realized_pnl_nok"] = round(bucket["realized_pnl_nok"], 2)
        bucket["unrealized_pnl_nok"] = round(bucket["unrealized_pnl_nok"], 2)
        if bucket["round_trips"]:
            bucket["win_rate"] = round(bucket["wins"] / bucket["round_trips"], 2)

    total_cost = sum(c for c, _, _ in weighted)
    covered = [(c, r, i) for c, r, i in weighted if i is not None]
    if covered:
        covered_cost = sum(c for c, _, _ in covered)
        portfolio_return = sum(c * r for c, r, _ in covered) / covered_cost
        index_return = sum(c * i for c, _, i in covered) / covered_cost
        vs_index = {"return_pct": round(portfolio_return * 100.0, 2),
                    "index_return_pct": round(index_return * 100.0, 2),
                    "alpha_pct": round((portfolio_return - index_return) * 100.0, 2),
                    "coverage": round(covered_cost / total_cost, 2) if total_cost else None}
    else:
        vs_index = {"return_pct": None, "index_return_pct": None,
                    "alpha_pct": None, "coverage": 0.0}

    return {
        "currency": HOME_CURRENCY,
        "realized_pnl_nok": round(realized_nok, 2),
        "unrealized_pnl_nok": round(unrealized_nok, 2),
        "total_pnl_nok": round(realized_nok + unrealized_nok, 2),
        "open_cost_nok": round(open_cost_nok, 2),
        "open_value_nok": round(open_value_nok, 2),
        "open_positions": open_positions,
        "round_trips": round_trips,
        "win_rate": round(wins / len(round_trips), 2) if round_trips else None,
        "by_mode": by_mode,
        "vs_index": vs_index,
        "unpriced": unpriced,
        "fx_missing": sorted(fx_missing),
    }
