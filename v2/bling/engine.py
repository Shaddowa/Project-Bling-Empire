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
