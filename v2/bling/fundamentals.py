"""Extract the annual fundamental series the strategy needs from a TickerBundle.

All series are pandas Series indexed by fiscal year end, sorted oldest -> newest,
so growth math downstream can assume chronological order. Row labels follow
yfinance >= 1.x statement naming; every lookup has an explicit fallback chain
because coverage varies per company and exchange.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .data import TickerBundle


def _row(df: Optional[pd.DataFrame], *labels: str) -> Optional[pd.Series]:
    """First matching statement row as an oldest-first series, else None."""
    if df is None or df.empty:
        return None
    for label in labels:
        if label in df.index:
            series = df.loc[label].dropna()
            if isinstance(series, pd.DataFrame):  # duplicated label
                series = series.iloc[0].dropna()
            if not series.empty:
                return series.sort_index()
    return None


def _combine(*parts: Optional[pd.Series]) -> Optional[pd.Series]:
    """Sum the parts over the years where every part is present."""
    present = [p for p in parts if p is not None]
    if len(present) != len(parts) or not present:
        return None
    combined = present[0]
    for part in present[1:]:
        combined = combined.add(part, fill_value=None)
    combined = combined.dropna()
    return combined if not combined.empty else None


@dataclass
class Fundamentals:
    ticker: str
    revenue: Optional[pd.Series] = None
    net_income: Optional[pd.Series] = None
    eps: Optional[pd.Series] = None
    equity: Optional[pd.Series] = None
    equity_plus_dividends: Optional[pd.Series] = None
    total_debt: Optional[pd.Series] = None
    shares: Optional[pd.Series] = None
    operating_cash_flow: Optional[pd.Series] = None
    free_cash_flow: Optional[pd.Series] = None
    owner_earnings: Optional[pd.Series] = None
    owner_earnings_is_approximate: bool = False
    roe: Optional[pd.Series] = None
    roic: Optional[pd.Series] = None
    info: dict = field(default_factory=dict)

    @property
    def years_of_data(self) -> int:
        candidates = [s for s in (self.net_income, self.revenue, self.operating_cash_flow) if s is not None]
        return max((len(s) for s in candidates), default=0)


def extract_fundamentals(bundle: TickerBundle) -> Fundamentals:
    inc, bs, cf = bundle.income_stmt, bundle.balance_sheet, bundle.cashflow

    revenue = _row(inc, "Total Revenue", "Operating Revenue")
    net_income = _row(inc, "Net Income", "Net Income Common Stockholders",
                      "Net Income From Continuing Operations")
    eps = _row(inc, "Diluted EPS", "Basic EPS")
    equity = _row(bs, "Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest")
    total_debt = _row(bs, "Total Debt")
    if total_debt is None:
        long_term = _row(bs, "Long Term Debt")
        current = _row(bs, "Current Debt")
        if long_term is not None or current is not None:
            zero = pd.Series(0.0, index=(long_term if long_term is not None else current).index)
            total_debt = (long_term if long_term is not None else zero).add(
                current if current is not None else zero, fill_value=0.0)
    shares = _row(bs, "Ordinary Shares Number", "Share Issued")
    ocf = _row(cf, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    fcf = _row(cf, "Free Cash Flow")
    capex = _row(cf, "Capital Expenditure")
    if fcf is None:
        fcf = _combine(ocf, capex)  # capex is reported negative
    dividends_paid = _row(cf, "Cash Dividends Paid", "Common Stock Dividend Paid")

    # "Book value + dividends" per the Notion criteria: equity with cumulative
    # dividends added back so payouts don't mask real compounding.
    equity_plus_dividends = equity
    if equity is not None and dividends_paid is not None:
        paid = dividends_paid.abs().reindex(equity.index).fillna(0.0)
        equity_plus_dividends = equity + paid.cumsum()

    # Owner earnings per the Notion formula when the working-capital rows
    # exist; otherwise the conservative approximation OCF - |capex|.
    owner_earnings = _combine(
        net_income,
        _row(cf, "Depreciation And Amortization", "Depreciation Amortization Depletion", "Depreciation"),
        _row(cf, "Change In Receivables", "Changes In Account Receivables"),
        _row(cf, "Change In Payables", "Change In Payable"),
        _row(inc, "Tax Provision"),
        capex,
    )
    approximate = owner_earnings is None
    if approximate:
        owner_earnings = _combine(ocf, capex)

    roe = roic = None
    if net_income is not None and equity is not None:
        aligned = pd.concat([net_income, equity], axis=1, keys=["ni", "eq"]).dropna()
        valid = aligned[aligned["eq"] > 0]
        if not valid.empty:
            roe = valid["ni"] / valid["eq"]
        if total_debt is not None:
            with_debt = pd.concat([aligned, total_debt.rename("debt")], axis=1).dropna()
            with_debt = with_debt[(with_debt["eq"] + with_debt["debt"]) > 0]
            if not with_debt.empty:
                roic = with_debt["ni"] / (with_debt["eq"] + with_debt["debt"])
        elif roe is not None:
            roic = roe  # debt-free: ROIC == ROE under the Notion formula

    return Fundamentals(
        ticker=bundle.ticker,
        revenue=revenue,
        net_income=net_income,
        eps=eps,
        equity=equity,
        equity_plus_dividends=equity_plus_dividends,
        total_debt=total_debt,
        shares=shares,
        operating_cash_flow=ocf,
        free_cash_flow=fcf,
        owner_earnings=owner_earnings,
        owner_earnings_is_approximate=approximate,
        roe=roe,
        roic=roic,
        info=bundle.info,
    )
