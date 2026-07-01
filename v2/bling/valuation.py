"""Valuation: what price makes a quality company a low-risk purchase.

Implements the Rule #1 toolkit referenced throughout the Notion knowledge
base ("Margin of Safety", "Capital rate", payback time):

  Sticker price   - EPS grown 10 years at a conservative growth rate, valued
                    at a future P/E, discounted back at 15%/yr (the minimum
                    acceptable return).
  MOS price       - half the sticker price. Buying below this is the actual
                    low-risk entry.
  Ten cap         - 10x owner earnings per share: the price at which the
                    business yields 10% cash-on-cash in year one.
  Payback time    - years of growing free cash flow needed to return the
                    full market cap. <= 8 years passes.

The growth estimate is deliberately conservative: the LOWER of book-value
growth and EPS growth, capped at 15%.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .fundamentals import Fundamentals
from .fx import rate as fx_rate
from .quality import cagr

DISCOUNT_RATE = 0.15
MOS_FACTOR = 0.5
GROWTH_CAP = 0.15
YEARS_PROJECTED = 10
PAYBACK_YEARS_MAX = 8
FUTURE_PE_CAP = 30.0


@dataclass
class ValuationResult:
    ticker: str
    price: Optional[float]
    growth_estimate: Optional[float]
    sticker_price: Optional[float]
    mos_price: Optional[float]
    ten_cap_price: Optional[float]
    payback_years: Optional[float]
    verdict: str  # ON_SALE | FAIR | EXPENSIVE | UNKNOWN

    @property
    def discount_to_sticker(self) -> Optional[float]:
        """How far below sticker the stock trades; positive = underpriced."""
        if self.price is None or not self.sticker_price:
            return None
        return round(1.0 - self.price / self.sticker_price, 4)


def conservative_growth_estimate(f: Fundamentals) -> Optional[float]:
    candidates = [rate for rate in (cagr(f.equity_plus_dividends), cagr(f.eps)) if rate is not None]
    if not candidates:
        return None
    return min(min(candidates), GROWTH_CAP)


def sticker_price(eps_now: float, growth: float, trailing_pe: Optional[float]) -> Optional[float]:
    if eps_now <= 0 or growth is None or growth <= 0:
        return None  # Rule #1 valuation is meaningless for a shrinking company
    future_eps = eps_now * (1.0 + growth) ** YEARS_PROJECTED
    # Rule #1 default future P/E is 2x the growth rate (as a whole number),
    # bounded by today's P/E when that is lower, and by a sanity cap.
    pe_candidates = [2.0 * growth * 100.0, FUTURE_PE_CAP]
    if trailing_pe is not None and trailing_pe > 0:
        pe_candidates.append(trailing_pe)
    future_pe = max(min(pe_candidates), 5.0)
    future_price = future_eps * future_pe
    return future_price / (1.0 + DISCOUNT_RATE) ** YEARS_PROJECTED


def payback_time(market_cap: float, fcf_now: float, growth: float, max_years: int = 30) -> Optional[float]:
    """Years of growing FCF needed to accumulate the full market cap."""
    if market_cap <= 0 or fcf_now <= 0:
        return None
    cumulative, fcf = 0.0, fcf_now
    for year in range(1, max_years + 1):
        fcf *= (1.0 + max(growth or 0.0, 0.0))
        cumulative += fcf
        if cumulative >= market_cap:
            return float(year)
    return float(max_years)


def _clean_number(value) -> Optional[float]:
    """yfinance info fields occasionally carry NaN/inf/strings; a NaN price
    would make every `price <= x` comparison False and misclassify the stock
    as EXPENSIVE. Coerce to float, treat anything non-finite as missing."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def assess_valuation(f: Fundamentals) -> ValuationResult:
    info = f.info or {}
    price = _clean_number(info.get("currentPrice")) or _clean_number(info.get("regularMarketPrice"))
    trailing_pe = _clean_number(info.get("trailingPE"))
    market_cap = _clean_number(info.get("marketCap"))

    # Statements are reported in financialCurrency, the share price in
    # currency (Kitron: EUR books, NOK price). Everything derived from
    # statements must be converted before comparing with the price.
    to_price_ccy = fx_rate(info.get("financialCurrency"), info.get("currency")) or (
        1.0 if info.get("financialCurrency") in (None, info.get("currency")) else None)

    growth = conservative_growth_estimate(f)

    eps_now = None
    if f.eps is not None and not f.eps.empty and to_price_ccy is not None:
        eps_now = float(f.eps.iloc[-1]) * to_price_ccy
    elif info.get("trailingEps"):
        eps_now = _clean_number(info["trailingEps"])  # already in trading currency

    sticker = sticker_price(eps_now, growth, trailing_pe) if (eps_now and growth is not None) else None
    mos = sticker * MOS_FACTOR if sticker else None

    ten_cap = None
    if (f.owner_earnings is not None and f.shares is not None
            and not f.shares.empty and to_price_ccy is not None):
        shares_now = float(f.shares.iloc[-1])
        if shares_now > 0:
            ten_cap = 10.0 * float(f.owner_earnings.iloc[-1]) * to_price_ccy / shares_now

    payback = None
    if (market_cap and f.free_cash_flow is not None
            and not f.free_cash_flow.empty and to_price_ccy is not None):
        fcf_now = float(f.free_cash_flow.iloc[-1]) * to_price_ccy
        payback = payback_time(float(market_cap), fcf_now, growth)

    if price is None or sticker is None:
        verdict = "UNKNOWN"
    elif price <= mos or (payback is not None and payback <= PAYBACK_YEARS_MAX and price <= sticker):
        verdict = "ON_SALE"
    elif price <= sticker:
        verdict = "FAIR"
    else:
        verdict = "EXPENSIVE"

    return ValuationResult(
        ticker=f.ticker,
        price=price,
        growth_estimate=growth,
        sticker_price=sticker,
        mos_price=mos,
        ten_cap_price=ten_cap,
        payback_years=payback,
        verdict=verdict,
    )
