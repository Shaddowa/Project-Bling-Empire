"""Backtest: do the timing rules actually earn their keep?

Strategy per ticker (the "hybrid" rule, chosen empirically — see README):
enter at the close after the three tools all turn bullish WHILE price is
above its 200-day SMA; exit at the close after price falls below the
200-day SMA. Exiting on three-tool flips instead was tested and whipsawed
away half the return for little extra protection. Signals computed on day t
are traded at the close of day t+1 — no look-ahead. A per-side transaction
cost is charged on every position change.

The portfolio result is the equal-weight average of per-ticker daily
strategy returns, compared against equal-weight buy & hold of the same
tickers. This is an honest measuring stick, not a promise: costs are
simplified, dividends are included via adjusted closes, taxes and slippage
are not modeled — and backtesting today's screen winners overstates buy &
hold most of all (survivorship).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .data import fetch_bundle
from .signals import composite_signal, tool_states

TRANSACTION_COST = 0.0015  # 0.15% per side (roughly Nordnet-tier commission + spread)
TRADING_DAYS = 252


def position_series(prices: pd.DataFrame) -> pd.Series:
    """1.0 while the strategy is in the market, 0.0 while out (state at close of each day).

    Hybrid rule: enter on a three-tool BUY confirmed by the 200-day trend,
    stay in until the price closes below the 200-day SMA.
    """
    states = tool_states(prices).dropna()
    signal = composite_signal(states)
    raw = pd.Series(np.nan, index=states.index)
    raw[(signal == "BUY") & states["trend200"]] = 1.0
    raw[~states["trend200"]] = 0.0
    return raw.ffill().fillna(0.0)


def strategy_returns(prices: pd.DataFrame, cost: float = TRANSACTION_COST) -> pd.Series:
    """Daily net returns of trading the composite signal on one ticker."""
    close = prices["Close"]
    daily = close.pct_change()
    position = position_series(prices).reindex(daily.index).fillna(0.0)
    held = position.shift(1).fillna(0.0)  # decided yesterday, applied today
    trades = position.diff().abs().fillna(position)
    return held * daily - trades * cost


@dataclass
class BacktestMetrics:
    label: str
    years: float
    cagr: Optional[float]
    max_drawdown: float
    sharpe: Optional[float]
    time_in_market: float
    trades_per_year: float


def summarize(returns: pd.Series, label: str, position: Optional[pd.Series] = None,
              trades_per_year: float = 0.0) -> BacktestMetrics:
    returns = returns.dropna()
    if position is None:
        in_market = 1.0  # buy & hold benchmark
    else:
        in_market = float(position.mean()) if len(position.dropna()) else 0.0
    if returns.empty:  # nothing tradable: report zeros, not NaN
        return BacktestMetrics(label=label, years=0.0, cagr=None, max_drawdown=0.0,
                               sharpe=None, time_in_market=in_market,
                               trades_per_year=round(trades_per_year, 1))
    equity = (1.0 + returns).cumprod()
    # Calendar span, not row count: merged Oslo+US calendars have more rows
    # per year than either market alone, which would inflate row-based years.
    years = (returns.index[-1] - returns.index[0]).days / 365.25 if len(returns) > 1 else 0.0
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 and equity.iloc[-1] > 0 else None
    # peak == 0 means the strategy was wiped out at that point: drawdown is
    # -100%, not the NaN a raw 0/0 would produce.
    peak = equity.cummax()
    drawdown = float((equity / peak.replace(0.0, np.nan) - 1.0).fillna(-1.0).min())
    volatility = returns.std()
    # 1e-12 floor: a numerically-constant return series has no meaningful
    # Sharpe; float noise in std() must not explode it to 1e16.
    sharpe = float(returns.mean() / volatility * np.sqrt(TRADING_DAYS)) if volatility and volatility > 1e-12 else None
    return BacktestMetrics(
        label=label,
        years=round(years, 1),
        cagr=cagr,
        max_drawdown=drawdown,
        sharpe=sharpe,
        time_in_market=in_market,
        trades_per_year=round(trades_per_year, 1),
    )


def backtest_ticker(ticker: str) -> Optional[dict]:
    bundle = fetch_bundle(ticker)
    prices = bundle.prices
    if prices is None or len(prices) < 300:
        return None
    net = strategy_returns(prices)
    position = position_series(prices)
    switches = position.diff().abs().sum()
    years = max(len(net) / TRADING_DAYS, 1e-9)
    return {
        "ticker": ticker,
        "strategy": summarize(net, f"{ticker} strategy", position, trades_per_year=switches / 2.0 / years),
        "buy_hold": summarize(prices["Close"].pct_change(), f"{ticker} buy & hold"),
        "returns": net,
        "bh_returns": prices["Close"].pct_change(),
        "position": position,
    }


@dataclass
class PortfolioBacktest:
    tickers: list[str]
    strategy: BacktestMetrics
    buy_hold: BacktestMetrics
    per_ticker: list[dict]


def backtest_portfolio(tickers: list[str]) -> Optional[PortfolioBacktest]:
    """Equal-weight portfolio of per-ticker signal strategies vs buy & hold."""
    results = [r for r in (backtest_ticker(t) for t in tickers) if r is not None]
    if not results:
        return None
    strat = pd.concat([r["returns"] for r in results], axis=1, sort=True).mean(axis=1)
    bh = pd.concat([r["bh_returns"] for r in results], axis=1, sort=True).mean(axis=1)
    position = pd.concat([r["position"] for r in results], axis=1, sort=True).mean(axis=1)
    trades = float(np.mean([r["strategy"].trades_per_year for r in results]))
    return PortfolioBacktest(
        tickers=[r["ticker"] for r in results],
        strategy=summarize(strat, "portfolio strategy", position, trades_per_year=trades),
        buy_hold=summarize(bh, "portfolio buy & hold"),
        per_ticker=results,
    )


def format_metrics(m: BacktestMetrics) -> str:
    cagr = f"{m.cagr:+.1%}" if m.cagr is not None else "n/a"
    sharpe = f"{m.sharpe:.2f}" if m.sharpe is not None else "n/a"
    return (f"{m.label:<28} {m.years:>5.1f}y  CAGR {cagr:>8}  maxDD {m.max_drawdown:>7.1%}  "
            f"Sharpe {sharpe:>5}  in-market {m.time_in_market:>5.1%}  trades/yr {m.trades_per_year}")
