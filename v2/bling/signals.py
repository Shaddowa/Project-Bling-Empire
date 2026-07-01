"""Timing signals: Phil Town's "three tools" plus a long-term trend filter.

The three tools (from Rule #1 / Payback Time, referenced in the Notion
knowledge base) applied to daily closes:

  MACD        - 8/17/9 EMA convergence-divergence; bullish when the MACD line
                is above its signal line.
  Stochastic  - 14-day %K smoothed over 5; bullish when %K is above %D.
  Moving avg  - bullish when price is above its 10-day SMA.

Composite per day: BUY when all three are bullish, SELL when all three are
bearish, HOLD otherwise. The 200-day SMA trend state is reported alongside
so the report can flag counter-trend buys; the backtest trades the pure
three-tool composite so the published results match the rules as stated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

MACD_FAST, MACD_SLOW, MACD_SIGNAL = 8, 17, 9
STOCH_WINDOW, STOCH_SMOOTH = 14, 5
FAST_SMA = 10
TREND_SMA = 200


def macd_state(close: pd.Series) -> pd.Series:
    fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = fast - slow
    signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    return macd_line > signal_line


def stochastic_state(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    lowest = low.rolling(STOCH_WINDOW).min()
    highest = high.rolling(STOCH_WINDOW).max()
    span = (highest - lowest).replace(0.0, np.nan)  # flat 14d window: no signal
    percent_k = 100.0 * (close - lowest) / span
    percent_k_smooth = percent_k.rolling(STOCH_SMOOTH).mean()
    percent_d = percent_k_smooth.rolling(STOCH_SMOOTH).mean()
    return percent_k_smooth > percent_d


def sma_state(close: pd.Series, window: int = FAST_SMA) -> pd.Series:
    return close > close.rolling(window).mean()


def tool_states(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily True/False per tool. Expects yfinance OHLCV columns."""
    close, high, low = prices["Close"], prices["High"], prices["Low"]
    return pd.DataFrame({
        "macd": macd_state(close),
        "stochastic": stochastic_state(high, low, close),
        "sma10": sma_state(close),
        "trend200": sma_state(close, TREND_SMA),
    })


def composite_signal(states: pd.DataFrame) -> pd.Series:
    """BUY / SELL / HOLD per day from the three tools."""
    tools = states[["macd", "stochastic", "sma10"]]
    bullish = tools.sum(axis=1)
    signal = pd.Series("HOLD", index=states.index)
    signal[bullish == 3] = "BUY"
    signal[bullish == 0] = "SELL"
    return signal


@dataclass
class SignalResult:
    ticker: str
    signal: str                    # BUY | SELL | HOLD | UNKNOWN
    macd_bullish: Optional[bool]
    stochastic_bullish: Optional[bool]
    sma10_bullish: Optional[bool]
    above_200_sma: Optional[bool]
    days_in_current_signal: Optional[int]


def assess_signals(ticker: str, prices: Optional[pd.DataFrame]) -> SignalResult:
    if prices is None or len(prices) < TREND_SMA:
        return SignalResult(ticker, "UNKNOWN", None, None, None, None, None)

    states = tool_states(prices).dropna()
    if states.empty:
        return SignalResult(ticker, "UNKNOWN", None, None, None, None, None)

    signal = composite_signal(states)
    latest = states.iloc[-1]
    current = signal.iloc[-1]
    changed = signal != current
    days_in_signal = int((~changed[::-1]).cummin().sum())

    return SignalResult(
        ticker=ticker,
        signal=current,
        macd_bullish=bool(latest["macd"]),
        stochastic_bullish=bool(latest["stochastic"]),
        sma10_bullish=bool(latest["sma10"]),
        above_200_sma=bool(latest["trend200"]),
        days_in_current_signal=days_in_signal,
    )
