"""Trading modes on top of the same data layer.

  LONG-TERM  - the engine's core: quality + margin-of-safety + hybrid timing
               (engine.py). Weeks-to-years holding period.
  SWING      - three-tool composite in AND out, trend-filtered. Days-to-weeks.
               Every candidate carries ITS OWN 2-year backtest stats, because
               the tools whipsaw on some names and work on others — the table
               shows on which names the mode has actually paid.
  DAY        - intraday dashboard for a shortlist: opening range, VWAP,
               15-minute momentum. Decision support for entries/exits within
               the day; there is deliberately no "auto day-trade" signal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from .data import fetch_bundle
from .signals import composite_signal, tool_states

SWING_LOOKBACK_DAYS = 504  # ~2 years of trading days
SWING_MAX_SIGNAL_AGE = 7   # only fresh setups are actionable


@dataclass
class SwingStats:
    trades: int
    win_rate: Optional[float]      # share of round trips that closed green
    avg_trade_return: Optional[float]
    strategy_return: Optional[float]  # compounded, after nothing (gross)
    hold_return: Optional[float]


def swing_trade_stats(prices: pd.DataFrame) -> Optional[SwingStats]:
    """Backtest the pure three-tool in/out rule on ONE ticker's recent history."""
    window = prices.tail(SWING_LOOKBACK_DAYS)
    if len(window) < 120:
        return None
    states = tool_states(window).dropna()
    if states.empty:
        return None
    signal = composite_signal(states)
    position = (signal.replace("HOLD", np.nan).ffill() == "BUY").astype(float)
    close = window["Close"].reindex(position.index)

    trades = []
    entry = None
    for day, held in position.items():
        if held == 1.0 and entry is None:
            entry = close.loc[day]
        elif held == 0.0 and entry is not None:
            trades.append(close.loc[day] / entry - 1.0)
            entry = None
    if entry is not None:  # still open: mark to market
        trades.append(close.iloc[-1] / entry - 1.0)
    if not trades:
        return SwingStats(0, None, None, None, None)

    daily = close.pct_change()
    strategy = float((1.0 + position.shift(1).fillna(0.0) * daily.fillna(0.0)).prod() - 1.0)
    hold = float(close.iloc[-1] / close.iloc[0] - 1.0)
    return SwingStats(
        trades=len(trades),
        win_rate=round(sum(1 for t in trades if t > 0) / len(trades), 2),
        avg_trade_return=round(float(np.mean(trades)), 4),
        strategy_return=round(strategy, 4),
        hold_return=round(hold, 4),
    )


def swing_scan(tickers: list[str]) -> list[dict]:
    """Fresh three-tool BUY setups in an uptrend, with per-ticker track record.

    Uses cached bundles only (the daily screen already fetched them) — no new
    network traffic for a full-universe scan.
    """
    rows = []
    for ticker in tickers:
        try:
            bundle = fetch_bundle(ticker, max_age=pd.Timedelta(days=2).to_pytimedelta())
            prices = bundle.prices
            if prices is None or len(prices) < 220:
                continue
            states = tool_states(prices).dropna()
            if states.empty or not bool(states["trend200"].iloc[-1]):
                continue
            signal = composite_signal(states)
            current = signal.iloc[-1]
            if current != "BUY":
                continue
            changed = signal != current
            age = int((~changed[::-1]).cummin().sum())
            if age > SWING_MAX_SIGNAL_AGE:
                continue
            stats = swing_trade_stats(prices)
            info = bundle.info or {}
            rows.append({
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName"),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "currency": info.get("currency"),
                "signal_age": age,
                "stats": stats,
            })
        except Exception:
            continue
    # Names where the mode has historically worked come first.
    rows.sort(key=lambda r: -(r["stats"].win_rate or 0.0) if r["stats"] else 0.0)
    return rows


@dataclass
class DayRow:
    ticker: str
    price: Optional[float]
    currency: Optional[str]
    open_range_high: Optional[float]
    open_range_low: Optional[float]
    orb_state: str          # ABOVE (broke out) | INSIDE | BELOW (broke down)
    vwap: Optional[float]
    above_vwap: Optional[bool]
    day_change_pct: Optional[float]
    momentum_15m: Optional[bool]  # last 15m close above its 8-bar EMA


def day_view(tickers: list[str], max_tickers: int = 20) -> list[DayRow]:
    """Live intraday state for a shortlist. Fetches 15m bars — call on demand."""
    rows: list[DayRow] = []
    for ticker in tickers[:max_tickers]:
        try:
            bars = yf.Ticker(ticker).history(period="5d", interval="15m")
            if bars is None or bars.empty:
                continue
            last_day = bars.index[-1].date()
            today = bars[bars.index.date == last_day]
            if today.empty:
                continue
            opening = today.head(2)  # first 30 minutes
            orb_high, orb_low = float(opening["High"].max()), float(opening["Low"].min())
            price = float(today["Close"].iloc[-1])
            typical = (today["High"] + today["Low"] + today["Close"]) / 3.0
            volume = today["Volume"].replace(0, np.nan)
            vwap = float((typical * volume).sum() / volume.sum()) if volume.notna().any() else None
            prev_days = bars[bars.index.date < last_day]
            prev_close = float(prev_days["Close"].iloc[-1]) if not prev_days.empty else None
            ema8 = today["Close"].ewm(span=8, adjust=False).mean()
            rows.append(DayRow(
                ticker=ticker,
                price=round(price, 2),
                currency=None,
                open_range_high=round(orb_high, 2),
                open_range_low=round(orb_low, 2),
                orb_state="ABOVE" if price > orb_high else ("BELOW" if price < orb_low else "INSIDE"),
                vwap=round(vwap, 2) if vwap else None,
                above_vwap=bool(price > vwap) if vwap else None,
                day_change_pct=round((price / prev_close - 1.0) * 100.0, 2) if prev_close else None,
                momentum_15m=bool(today["Close"].iloc[-1] > ema8.iloc[-1]),
            ))
        except Exception:
            continue
    rows.sort(key=lambda r: -(r.day_change_pct or 0.0))
    return rows
