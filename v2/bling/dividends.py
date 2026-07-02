"""Dividend score, ported from the v1 engine (yquery_ticker dividend criteria).

Scoring, normalized to 0-10:
  - forward vs trailing dividend yield  (0-4, higher forward is better)
  - forward vs trailing dividend rate   (0-4)
  - payout ratio in the sustainable 40-60% band (0 or 1)
  - ex-dividend date within the last year        (0 or 1)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

MAX_RAW_SCORE = 10.0


def _present(value: Optional[float]) -> Optional[float]:
    """None for missing/zero/NaN — yfinance emits all three for 'no data'."""
    if value is None or not value:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def compare_forward_to_trailing(trailing: Optional[float], forward: Optional[float]) -> float:
    """4: forward > trailing, 3: equal, 2: forward only, 1: forward < trailing,
    0.5: trailing only, 0: neither. Zero and NaN values count as missing."""
    forward = _present(forward)
    trailing = _present(trailing)
    if forward is not None and trailing is not None:
        if forward > trailing:
            return 4.0
        return 3.0 if forward == trailing else 1.0
    if forward is not None:
        return 2.0
    return 0.5 if trailing is not None else 0.0


def payout_ratio_score(payout_ratio: Optional[float]) -> float:
    return 1.0 if payout_ratio is not None and 0.40 <= payout_ratio <= 0.60 else 0.0


def _ex_date_utc(value) -> Optional[datetime]:
    """Normalize whatever yfinance ships as exDividendDate to an aware UTC
    datetime. Across versions the field has been epoch seconds (int/float),
    an ISO string, a datetime.date, or a (sometimes tz-naive) datetime /
    pandas Timestamp. Naive datetimes are assumed UTC; garbage becomes None
    instead of a crash."""
    if value is None:
        return None
    if isinstance(value, datetime):  # includes pandas Timestamp
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):  # plain date (checked after datetime: datetime is a date)
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    try:
        stamp = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(stamp) or stamp <= 0:
        return None
    try:
        return datetime.fromtimestamp(stamp, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def ex_date_score(ex_dividend_date) -> float:
    ex_date = _ex_date_utc(ex_dividend_date)
    if ex_date is None:
        return 0.0
    return 1.0 if datetime.now(tz=timezone.utc) - ex_date <= timedelta(days=365) else 0.0


@dataclass
class DividendResult:
    ticker: str
    score: float  # 0-10
    trailing_yield: Optional[float]
    forward_yield: Optional[float]
    payout_ratio: Optional[float]


MAX_PLAUSIBLE_YIELD = 0.25  # 25%+ "yield" is a data artifact, not a dividend


def _normalized_yields(info: dict) -> tuple[Optional[float], Optional[float]]:
    """yfinance unit trap: dividendYield is a PERCENT (4.62), while
    trailingAnnualDividendYield is a FRACTION (0.0462). Normalize both to
    fractions and drop implausible values instead of comparing garbage."""
    forward = info.get("dividendYield")
    forward = forward / 100.0 if forward else None
    trailing = info.get("trailingAnnualDividendYield") or None
    if forward is not None and not (0.0 < forward <= MAX_PLAUSIBLE_YIELD):
        forward = None
    if trailing is not None and not (0.0 < trailing <= MAX_PLAUSIBLE_YIELD):
        trailing = None
    return trailing, forward


def _comparable_rates(info: dict) -> tuple[Optional[float], Optional[float]]:
    """Cross-currency payers (Equinor declares USD, trades NOK) make the two
    rate fields different units. Only compare when they're the same ballpark."""
    trailing = _present(info.get("trailingAnnualDividendRate"))
    forward = _present(info.get("dividendRate"))
    if trailing and forward and not (0.25 <= forward / trailing <= 4.0):
        trailing = None
    return trailing, forward


def assess_dividends(ticker: str, info: dict) -> DividendResult:
    trailing_yield, forward_yield = _normalized_yields(info)
    trailing_rate, forward_rate = _comparable_rates(info)
    raw = (
        compare_forward_to_trailing(trailing_yield, forward_yield)
        + compare_forward_to_trailing(trailing_rate, forward_rate)
        + payout_ratio_score(info.get("payoutRatio"))
        + ex_date_score(info.get("exDividendDate"))
    )
    return DividendResult(
        ticker=ticker,
        score=round(10.0 * raw / MAX_RAW_SCORE, 2),
        trailing_yield=trailing_yield,
        forward_yield=forward_yield,
        payout_ratio=info.get("payoutRatio"),
    )
