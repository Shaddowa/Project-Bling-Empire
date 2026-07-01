"""Ties the pieces together: one ticker in, one decided row out.

The action ladder is deliberately strict — every rung must hold before the
engine will say BUY:

  quality   >= QUALITY_THRESHOLD  (wonderful company)
  valuation == ON_SALE            (price below margin-of-safety territory)
  signal    == BUY                (all three timing tools bullish)

  BUY    quality + on sale + timing all agree
  WATCH  quality + on sale, timing not there yet (the shopping list)
  FAIR   quality holds but price is only fair — wait for a better price
  AVOID  quality or data insufficient
  SELL   guidance for holders: timing tools all bearish or price above sticker
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from .data import fetch_bundle
from .dividends import DividendResult, assess_dividends
from .fundamentals import extract_fundamentals
from .quality import QualityResult, assess_quality
from .signals import SignalResult, assess_signals
from .valuation import ValuationResult, assess_valuation

QUALITY_THRESHOLD = 60.0
FETCH_WORKERS = 6


@dataclass
class TickerReport:
    ticker: str
    name: Optional[str]
    sector: Optional[str]
    currency: Optional[str]
    quality: QualityResult
    valuation: ValuationResult
    signal: SignalResult
    dividends: DividendResult
    action: str
    sell_guidance: str
    error: Optional[str] = None


def decide_action(quality: QualityResult, valuation: ValuationResult, signal: SignalResult) -> str:
    if quality.score < QUALITY_THRESHOLD or valuation.verdict == "UNKNOWN":
        return "AVOID"
    if valuation.verdict in ("EXPENSIVE", "FAIR"):
        return "FAIR"  # quality company, wrong price
    # Entry needs the tools AND the long-term trend (the backtested hybrid rule).
    return "BUY" if signal.signal == "BUY" and signal.above_200_sma else "WATCH"


def decide_sell_guidance(valuation: ValuationResult, signal: SignalResult) -> str:
    """For someone already holding the stock. Backtests showed exiting on
    three-tool flips whipsaws away most of the return; the exit that held up
    is the 200-day trend break (plus taking profit above sticker)."""
    if signal.above_200_sma is False:
        return "SELL (below 200-day trend)"
    if valuation.verdict == "EXPENSIVE":
        return "TAKE PROFIT (above sticker price)"
    if signal.signal == "SELL":
        return "HOLD (tools bearish — watch the 200-day line)"
    return "HOLD"


def _error_report(ticker: str, error: str) -> TickerReport:
    return TickerReport(
        ticker=ticker, name=None, sector=None, currency=None,
        quality=QualityResult(ticker, {}, {}, 0),
        valuation=ValuationResult(ticker, None, None, None, None, None, None, "UNKNOWN"),
        signal=SignalResult(ticker, "UNKNOWN", None, None, None, None, None),
        dividends=DividendResult(ticker, 0.0, None, None, None),
        action="AVOID", sell_guidance="",
        error=error,
    )


def enrich_holding(report: TickerReport, holding) -> dict:
    """Trade-management view of one held position: stop, target, progress.

    Target = sticker price (take profit); stop = holding's sell limit
    (explicit or 8% under cost). Stop-loss overrides all other guidance —
    the point is that no single trade is allowed to hurt the runway.
    """
    price = report.valuation.price
    stop = holding.effective_stop
    cost = holding.cost_basis
    # Target: the sticker price when it sits above cost (a value position);
    # otherwise the trader's 2R rule — reward = 2x the risk taken to the stop.
    sticker = report.valuation.sticker_price
    target = None
    target_kind = None
    if sticker and cost and sticker > cost:
        target, target_kind = sticker, "sticker"
    elif cost and stop and cost > stop:
        target, target_kind = cost + 2.0 * (cost - stop), "2R"
    guidance = report.sell_guidance
    progress = None
    if price and target and cost and target > cost:
        progress = max(0.0, min(1.0, (price - cost) / (target - cost)))
    if price and target and price >= target:
        guidance = f"TAKE PROFIT (target {target:.2f} reached)"
    if price and stop and price <= stop:
        guidance = f"SELL NOW (stop loss {stop:.2f} hit)"
    gain = (price / holding.cost_basis - 1.0) * 100.0 if price and holding.cost_basis else None
    return {
        "ticker": holding.ticker,
        "name": report.name,
        "shares": holding.shares,
        "price": price,
        "currency": report.currency,
        "value": price * holding.shares if price else None,
        "gain_pct": round(gain, 1) if gain is not None else None,
        "cost": holding.cost_basis or None,
        "stop": round(stop, 2) if stop else None,
        "target": round(target, 2) if target else None,
        "target_kind": target_kind,
        "progress": round(progress, 3) if progress is not None else None,
        "guidance": guidance or "—",
        "signal": report.signal.signal,
    }


def analyze_ticker(ticker: str, max_age: timedelta = timedelta(days=1)) -> TickerReport:
    try:
        return _analyze_ticker(ticker, max_age)
    except Exception as error:  # one bad ticker must never kill a universe run
        return _error_report(ticker, f"{type(error).__name__}: {error}")


def _analyze_ticker(ticker: str, max_age: timedelta) -> TickerReport:
    bundle = fetch_bundle(ticker, max_age=max_age)
    if not bundle.is_usable:
        return _error_report(ticker, bundle.info.get("_error", "no data"))

    fundamentals = extract_fundamentals(bundle)
    quality = assess_quality(fundamentals)
    valuation = assess_valuation(fundamentals)
    signal = assess_signals(ticker, bundle.prices)
    dividends = assess_dividends(ticker, bundle.info)

    return TickerReport(
        ticker=ticker,
        name=bundle.info.get("longName") or bundle.info.get("shortName"),
        sector=bundle.info.get("sector"),
        currency=bundle.info.get("currency"),
        quality=quality,
        valuation=valuation,
        signal=signal,
        dividends=dividends,
        action=decide_action(quality, valuation, signal),
        sell_guidance=decide_sell_guidance(valuation, signal),
    )


def analyze_universe(tickers: list[str], max_age: timedelta = timedelta(days=1),
                     progress: bool = True) -> list[TickerReport]:
    reports: list[TickerReport] = []
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        for index, report in enumerate(pool.map(lambda t: analyze_ticker(t, max_age), tickers), 1):
            reports.append(report)
            if progress and index % 25 == 0:
                print(f"  analyzed {index}/{len(tickers)}")
    return reports
