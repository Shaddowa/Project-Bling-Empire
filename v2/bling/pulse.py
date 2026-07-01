"""Live-ish snapshots for widgets: market pulse + holding quotes.

Widgets refresh every few minutes all day; Yahoo would rate-limit a full
fetch per refresh. So: benchmark-index pulse is cached on disk for 15
minutes, and holding quotes use yfinance fast_info (one light call per
held ticker, only a handful of those).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import yfinance as yf

from .universe import MARKETS, V2_ROOT, active_universes

PULSE_PATH = V2_ROOT / "data" / "market_pulse.json"
PULSE_TTL_SECONDS = 15 * 60


def market_pulse() -> list[dict]:
    """Per active market: index day move + 200-day trend state."""
    if PULSE_PATH.exists():
        cached = json.loads(PULSE_PATH.read_text())
        if time.time() - cached.get("at", 0) < PULSE_TTL_SECONDS \
                and [m["market"] for m in cached.get("markets", [])] == active_universes():
            return cached["markets"]

    markets = []
    for name in active_universes():
        symbol = MARKETS[name].get("index")
        if not symbol:
            continue
        try:
            import math
            history = yf.Ticker(symbol).history(period="1y")["Close"].dropna()
            if len(history) < 2:
                continue
            last = float(history.iloc[-1])
            prev = float(history.iloc[-2])
            if not (math.isfinite(last) and math.isfinite(prev)) or prev == 0:
                continue
            sma200 = float(history.rolling(200).mean().iloc[-1]) if len(history) >= 200 else None
            if sma200 is not None and not math.isfinite(sma200):
                sma200 = None
            markets.append({
                "market": name,
                "label": MARKETS[name]["label"].split()[-1],  # the flag emoji
                "day_pct": round((last / prev - 1.0) * 100.0, 2),
                "trend_up": bool(last > sma200) if sma200 else None,
            })
        except Exception:
            continue
    PULSE_PATH.write_text(json.dumps({"at": time.time(), "markets": markets}))
    return markets


def live_quote(ticker: str) -> tuple[Optional[float], Optional[float]]:
    """(last_price, day_change_pct) via the light fast_info path."""
    import math
    try:
        info = yf.Ticker(ticker).fast_info
        last, prev = info.last_price, info.previous_close
        last = float(last) if last and math.isfinite(float(last)) else None
        prev = float(prev) if prev and math.isfinite(float(prev)) else None
        if last and prev:
            return last, round((last / prev - 1.0) * 100.0, 2)
        return last, None
    except Exception:
        return None, None
