from dataclasses import dataclass
from typing import Optional
from context.yquery_ticker.main.interfaces.castable_data import CastableDataInterface
from ..const import DEFAULT_CASH_FLOW_METRIC
from ..data_classes.expenses import Expenses
from ..enums.cash_flow_type import CashFlowType
from context.yquery_ticker.main.interfaces.iterable_data import IterableDataInterface
from ..errors.generic_error import GenericError


@dataclass
class PriceToEarnings(IterableDataInterface, CastableDataInterface):
    trailing_pe: Optional[float]
    forward_pe: Optional[float]


@dataclass
class EarningsPerShare(IterableDataInterface, CastableDataInterface):
    trailing_eps: Optional[float]
    forward_eps: Optional[float]


@dataclass
class FinancialData(IterableDataInterface, CastableDataInterface):
    price: Optional[float]
    target_high_price: Optional[float]
    target_low_price: Optional[float]
    recommendation_mean: Optional[float]
    recommendation_key: Optional[str]
    number_of_analyst_opinions: Optional[float]
    total_revenue: Optional[float]
    revenue_per_share: Optional[float]
    revenue_growth: Optional[float]
    total_debt: Optional[Optional[float]]
    debt_to_equity: Optional[float]
    gross_profit_margins: Optional[float]
    operating_margins: Optional[float]
    profit_margins: Optional[float]
    dividend_rate: Optional[float]
    dividend_yield: Optional[float]
    five_year_avg_dividend_yield: Optional[float]
    trailing_annual_dividend_rate: Optional[float]
    trailing_annual_dividend_yield: Optional[float]
    free_cash_flow: Optional[float]
    operating_cash_flow: Optional[float]
    enterprise_to_ebitda: Optional[float]
    price_to_book: Optional[float]
    price_to_earnings: Optional[PriceToEarnings]
    earnings_per_share: Optional[EarningsPerShare]
    enterprise_to_revenue: Optional[float]
    return_on_equity: Optional[float]
    return_on_assets: Optional[float]
    net_income_to_common: Optional[float]  # net earnings
    earnings_growth: Optional[float]
    book_value: Optional[float]
    expenses: Optional[Expenses]

    def apply_local_rules(self):
        if self.total_debt is None or not self.total_debt:
            return

        if self.total_debt < 0:
            self.total_debt = None

    def get_cash_flow(self, cash_flow_type: CashFlowType = DEFAULT_CASH_FLOW_METRIC):
        if cash_flow_type == CashFlowType.FREE_CASH_FLOW:
            return self.free_cash_flow
        elif cash_flow_type == CashFlowType.OPERATING_CASH_FLOW:
            return self.operating_cash_flow
        return None

    def set_cash_flow(self, cash_flow, cash_flow_type: CashFlowType = DEFAULT_CASH_FLOW_METRIC):
        if cash_flow_type == CashFlowType.FREE_CASH_FLOW:
            self.free_cash_flow = cash_flow
        elif cash_flow_type == CashFlowType.OPERATING_CASH_FLOW:
            self.operating_cash_flow = cash_flow

    def calculate_price_to_cashflow(self):
        cash_flow = self.get_cash_flow()
        if self.price is not None and cash_flow is not None:
            if float(cash_flow) != 0.0:
                return self.price / cash_flow
        return None

    def calculate_return_on_invested_capital(self):
        if (
                self.net_income_to_common is not None
                and self.book_value is not None
                and self.total_debt is not None
        ):
            if (numerator := self.book_value + self.total_debt) != 0:
                return self.net_income_to_common / numerator
        return None

    def calculate_return_on_investment(self):
        if self.expenses is not None:
            has_invalid_expenses_value = self.expenses.has_invalid_value(
                self.expenses.capital_expenditure,
                self.expenses.interest_expense,
                self.expenses.interest_expense_non_operating,
                self.expenses.total_other_finance_cost
            )
            if (
                    self.net_income_to_common is not None
                    and not has_invalid_expenses_value
            ):
                if (sum_expenses := self.expenses.sum()) != 0:
                    return self.net_income_to_common / (sum_expenses * 100)
        return GenericError(reason="Expenses fields is `None` or has invalid values for calculations")

    @classmethod
    def mockk(cls):
        return FinancialData(
            price=0,
            target_high_price=0,
            target_low_price=0,
            recommendation_mean=0,
            recommendation_key=None,
            number_of_analyst_opinions=0,
            total_revenue=0,
            revenue_per_share=0,
            revenue_growth=0,
            total_debt=0,
            debt_to_equity=0,
            gross_profit_margins=0,
            operating_margins=0,
            profit_margins=0,
            dividend_rate=0,
            dividend_yield=0,
            five_year_avg_dividend_yield=0,
            trailing_annual_dividend_rate=0,
            trailing_annual_dividend_yield=0,
            free_cash_flow=0,
            operating_cash_flow=0,
            enterprise_to_ebitda=0,
            price_to_book=0,
            price_to_earnings=None,
            earnings_per_share=None,
            enterprise_to_revenue=0,
            return_on_equity=0,
            return_on_assets=0,
            net_income_to_common=0,
            earnings_growth=0,
            book_value=0,
            expenses=None,
        )
