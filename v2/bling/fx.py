"""FX rates for the financial-currency vs trading-currency mismatch.

Many Oslo Børs companies trade in NOK but report statements in USD or EUR
(Equinor, Kitron, ...). Any per-share value derived from statements must be
converted into the trading currency before comparing with the market price.
"""
from __future__ import annotations

from typing import Optional

import yfinance as yf

_CACHE: dict[tuple[str, str], Optional[float]] = {}

# Yahoo quotes GBp (pence) for London listings; statements are in GBP.
_MINOR_UNITS = {"GBp": ("GBP", 100.0), "ZAc": ("ZAR", 100.0), "ILA": ("ILS", 100.0)}


def rate(from_currency: Optional[str], to_currency: Optional[str]) -> Optional[float]:
    """Units of to_currency per one unit of from_currency; None when unknown."""
    if not from_currency or not to_currency:
        return None
    from_major, from_scale = _MINOR_UNITS.get(from_currency, (from_currency, 1.0))
    to_major, to_scale = _MINOR_UNITS.get(to_currency, (to_currency, 1.0))
    if from_major == to_major:
        return to_scale / from_scale

    key = (from_major, to_major)
    if key not in _CACHE:
        _CACHE[key] = _fetch(from_major, to_major)
    major_rate = _CACHE[key]
    if major_rate is None:
        return None
    return major_rate * to_scale / from_scale


def _fetch(from_major: str, to_major: str) -> Optional[float]:
    try:
        history = yf.Ticker(f"{from_major}{to_major}=X").history(period="5d")
        if history is not None and not history.empty:
            return float(history["Close"].iloc[-1])
    except Exception:
        pass
    return None
