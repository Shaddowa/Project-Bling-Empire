"""Personal runway model: how long can Hanna stay independent, and what
income closes the gap.

Everything is monthly NOK. The data lives in a local JSON file (gitignored —
see store.py); this module is pure math so it can be unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

SUSTAINABLE_RUNWAY_MONTHS = 18.0  # below this, the model starts asking for income


@dataclass
class LineItem:
    name: str
    amount: float  # balance for assets/debts, monthly for income/expenses


@dataclass
class Debt:
    name: str
    balance: float
    monthly_payment: float
    interest_rate: float = 0.0  # annual, e.g. 0.055


@dataclass
class Holding:
    ticker: str
    shares: float
    cost_basis: float = 0.0  # per share, in the ticker's trading currency


@dataclass
class Finances:
    currency: str = "NOK"
    cash: list[LineItem] = field(default_factory=list)
    investments: list[LineItem] = field(default_factory=list)  # crypto, funds — mark-to-market balances
    income: list[LineItem] = field(default_factory=list)       # monthly
    expenses: list[LineItem] = field(default_factory=list)     # monthly, excluding debt payments
    debts: list[Debt] = field(default_factory=list)
    holdings: list[Holding] = field(default_factory=list)      # stocks tracked live by the engine

    @property
    def total_cash(self) -> float:
        return sum(i.amount for i in self.cash)

    @property
    def total_investments(self) -> float:
        return sum(i.amount for i in self.investments)

    @property
    def total_debt(self) -> float:
        return sum(d.balance for d in self.debts)

    @property
    def monthly_income(self) -> float:
        return sum(i.amount for i in self.income)

    @property
    def monthly_expenses(self) -> float:
        return sum(i.amount for i in self.expenses)

    @property
    def monthly_debt_payments(self) -> float:
        return sum(d.monthly_payment for d in self.debts)

    @property
    def monthly_burn(self) -> float:
        """Net cash out per month; negative means she is cash-flow positive."""
        return self.monthly_expenses + self.monthly_debt_payments - self.monthly_income

    @property
    def liquid(self) -> float:
        return self.total_cash + self.total_investments

    @property
    def net_worth(self) -> float:
        return self.liquid - self.total_debt

    def runway_months(self, extra_monthly_income: float = 0.0,
                      expense_cut: float = 0.0) -> Optional[float]:
        """Months until liquid assets hit zero. None = indefinitely sustainable."""
        burn = self.monthly_burn - extra_monthly_income - expense_cut
        if burn <= 0:
            return None
        return self.liquid / burn

    def required_income_for(self, target_months: float) -> float:
        """Extra monthly income needed so runway reaches target_months (0 if already there)."""
        if self.monthly_burn <= 0:
            return 0.0
        if target_months <= 0:
            return self.monthly_burn  # break even
        needed_burn = self.liquid / target_months
        return max(0.0, self.monthly_burn - needed_burn)


@dataclass
class RunwayReport:
    liquid: float
    net_worth: float
    monthly_burn: float
    runway_months: Optional[float]
    breakeven_income: float           # monthly income that stops the bleed entirely
    income_for_sustainable: float     # income so runway >= SUSTAINABLE_RUNWAY_MONTHS
    scenarios: list[dict]             # what-if rows for the dashboard


def build_report(f: Finances) -> RunwayReport:
    base_runway = f.runway_months()

    scenarios = []
    for label, extra_income, cut in [
        ("As is", 0.0, 0.0),
        ("Cut expenses 10%", 0.0, 0.10 * f.monthly_expenses),
        ("Cut expenses 20%", 0.0, 0.20 * f.monthly_expenses),
        ("+5 000 kr/mo income", 5_000.0, 0.0),
        ("+10 000 kr/mo income", 10_000.0, 0.0),
        ("+10 000 kr/mo & cut 10%", 10_000.0, 0.10 * f.monthly_expenses),
    ]:
        months = f.runway_months(extra_income, cut)
        scenarios.append({
            "label": label,
            "burn": round(f.monthly_burn - extra_income - cut),
            "runway_months": round(months, 1) if months is not None else None,
        })

    return RunwayReport(
        liquid=f.liquid,
        net_worth=f.net_worth,
        monthly_burn=f.monthly_burn,
        runway_months=round(base_runway, 1) if base_runway is not None else None,
        breakeven_income=max(0.0, f.monthly_burn),
        income_for_sustainable=f.required_income_for(SUSTAINABLE_RUNWAY_MONTHS),
        scenarios=scenarios,
    )
