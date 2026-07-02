"""Quality scoring: the Notion "growth requirement summary" made executable.

Criteria (see documentation/vision.md and the Notion page):
  Big Four growing >= 10%/yr  - net income, book value + dividends, sales, operating cash flow
  ROE and ROIC >= 15%
  Owner earnings growing >= 10%/yr
  Free cash flow increasing
  Debt payable from FCF within 4 years (Rule #1 debt check)

Each criterion is PASS / FAIL / UNKNOWN (missing data). UNKNOWN never counts
as a pass: thin data lowers the score, which is the conservative direction.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd

from .fundamentals import Fundamentals

GROWTH_REQUIREMENT = 0.10
RETURNS_REQUIREMENT = 0.15
DEBT_PAYOFF_YEARS_MAX = 4.0
MIN_YEARS = 3  # fewer annual data points than this and a growth verdict is noise


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


def cagr(series: Optional[pd.Series]) -> Optional[float]:
    """Compound annual growth from first to last data point.

    Requires a positive starting value; a negative-to-positive swing has no
    meaningful growth rate. Returns None when it cannot be computed.
    """
    if series is None or len(series) < 2:
        return None
    first, last = float(series.iloc[0]), float(series.iloc[-1])
    if math.isnan(first) or math.isnan(last):
        return None  # a NaN endpoint would silently propagate through the score
    if first <= 0:
        return None
    if last <= 0:
        return -1.0  # fell to or below zero: unambiguous fail
    years = len(series) - 1
    return (last / first) ** (1.0 / years) - 1.0


def _growth_verdict(series: Optional[pd.Series], requirement: float) -> tuple[Verdict, Optional[float]]:
    if series is None or len(series) < MIN_YEARS:
        return Verdict.UNKNOWN, None
    rate = cagr(series)
    if rate is None:
        return Verdict.UNKNOWN, None
    return (Verdict.PASS if rate >= requirement else Verdict.FAIL), rate


def _returns_verdict(series: Optional[pd.Series]) -> tuple[Verdict, Optional[float]]:
    if series is None or series.dropna().empty:
        return Verdict.UNKNOWN, None
    mean = float(series.mean())  # pandas mean skips NaN
    if math.isnan(mean):
        return Verdict.UNKNOWN, None
    return (Verdict.PASS if mean >= RETURNS_REQUIREMENT else Verdict.FAIL), mean


@dataclass
class QualityResult:
    ticker: str
    verdicts: dict  # criterion name -> Verdict
    metrics: dict   # criterion name -> underlying number (rate/ratio), may hold None
    years_of_data: int

    @property
    def passed(self) -> int:
        return sum(1 for v in self.verdicts.values() if v == Verdict.PASS)

    @property
    def total(self) -> int:
        return len(self.verdicts)

    @property
    def score(self) -> float:
        """0-100, share of criteria passed."""
        return round(100.0 * self.passed / self.total, 1) if self.total else 0.0


def assess_quality(fundamentals: Fundamentals) -> QualityResult:
    f = fundamentals
    verdicts: dict = {}
    metrics: dict = {}

    for name, series in [
        ("net_income_growth", f.net_income),
        ("book_value_dividends_growth", f.equity_plus_dividends),
        ("sales_growth", f.revenue),
        ("operating_cash_flow_growth", f.operating_cash_flow),
        ("owner_earnings_growth", f.owner_earnings),
    ]:
        verdicts[name], metrics[name] = _growth_verdict(series, GROWTH_REQUIREMENT)

    verdicts["roe"], metrics["roe"] = _returns_verdict(f.roe)
    verdicts["roic"], metrics["roic"] = _returns_verdict(f.roic)

    # Free cash flow "increasing": last year above the first, and at least
    # half of the year-over-year steps up.
    if f.free_cash_flow is None or len(f.free_cash_flow) < MIN_YEARS:
        verdicts["fcf_increasing"], metrics["fcf_increasing"] = Verdict.UNKNOWN, None
    else:
        steps_up = (f.free_cash_flow.diff().dropna() > 0)
        increasing = f.free_cash_flow.iloc[-1] > f.free_cash_flow.iloc[0] and steps_up.mean() >= 0.5
        verdicts["fcf_increasing"] = Verdict.PASS if increasing else Verdict.FAIL
        metrics["fcf_increasing"] = float(f.free_cash_flow.iloc[-1])

    if f.total_debt is None or f.free_cash_flow is None or f.free_cash_flow.empty:
        verdicts["debt_payoff"], metrics["debt_payoff"] = Verdict.UNKNOWN, None
    else:
        debt = float(f.total_debt.iloc[-1])
        fcf = float(f.free_cash_flow.iloc[-1])
        if math.isnan(debt) or math.isnan(fcf):
            verdicts["debt_payoff"], metrics["debt_payoff"] = Verdict.UNKNOWN, None
        elif debt <= 0:
            verdicts["debt_payoff"], metrics["debt_payoff"] = Verdict.PASS, 0.0
        elif fcf <= 0:
            verdicts["debt_payoff"], metrics["debt_payoff"] = Verdict.FAIL, None
        else:
            years = debt / fcf
            verdicts["debt_payoff"] = Verdict.PASS if years <= DEBT_PAYOFF_YEARS_MAX else Verdict.FAIL
            metrics["debt_payoff"] = round(years, 2)

    return QualityResult(
        ticker=f.ticker,
        verdicts=verdicts,
        metrics=metrics,
        years_of_data=f.years_of_data,
    )
