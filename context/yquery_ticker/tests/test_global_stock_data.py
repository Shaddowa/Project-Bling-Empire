import unittest
from typing import Optional, Type

from context.yquery_ticker.main.classes.yahoo.historical_earnings_data import HistoricalEarningsData
from context.yquery_ticker.main.data_classes.charts import YearlyFinancialsDataChart
from context.yquery_ticker.main.data_classes.date import Date
from context.yquery_ticker.main.data_classes.expenses import Expenses
from context.yquery_ticker.main.data_classes.financial_data import EarningsPerShare, FinancialData, PriceToEarnings
from context.yquery_ticker.main.data_classes.financial_summary import FinancialSummary
from context.yquery_ticker.main.data_classes.general_stock_info import GeneralStockInfo
from context.yquery_ticker.main.enums.cash_flow_type import CashFlowType
from context.yquery_ticker.main.enums.growth_criteria import GrowthCriteria
from context.yquery_ticker.main.enums.quarter import Quarter
from context.yquery_ticker.main.errors.generic_error import GenericError
from context.yquery_ticker.tests.utils.test_case import TestCase


class test_global_stock_data(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(test_global_stock_data, self).__init__(*args, **kwargs)

    def setUp(self):
        self.general_stock_info = GeneralStockInfo.mockk()
        self.financial_data = FinancialData.mockk()
        self.earnings_and_earnings_history = HistoricalEarningsData.mockk()

    @staticmethod
    def assert_price_to_cash_flow(
            financial_data: FinancialData,
            price: Optional[float],
            cash_flow: Optional[float],
            expected: Optional[float]
    ):
        financial_data.price = price
        financial_data.set_cash_flow(cash_flow=cash_flow)
        assert financial_data.calculate_price_to_cashflow() == expected

    @staticmethod
    def assert_return_on_invested_capital(
            financial_data: FinancialData,
            net_income_to_common: Optional[float],
            book_value: Optional[float],
            total_debt: Optional[float],
            expected: Optional[float]
    ):
        financial_data.net_income_to_common = net_income_to_common
        financial_data.book_value = book_value
        financial_data.total_debt = total_debt
        result = financial_data.calculate_return_on_invested_capital()

        if result is not None:
            assert round(result, 2) == expected
        else:
            assert result == expected

    @staticmethod
    def assert_return_on_investment(
            financial_data: FinancialData,
            expenses: Expenses,
            expected: Optional[float | Type[GenericError]]
    ):
        financial_data.net_income_to_common = 100
        financial_data.expenses = expenses
        result = financial_data.calculate_return_on_investment()

        if not isinstance(result, GenericError):
            assert round(result, 2) == expected
        else:
            isinstance(result, expected)

    def test_general_stock_info(self):
        general_stock_info = GeneralStockInfo(
            ticker='aapl',
            company='Apple Inc',
            country=None,  # type: ignore
            industry='Consumer Electronics',
            sector='Technology',
            website='https://www.apple.com',
            long_business_summary='N/A',
            financial_summary=FinancialSummary(
                previous_close=None,
                open=0.0,
                dividend_rate="2020-05-08 00:00:00",  # type: ignore
                payout_ratio=0.0,
                ex_dividend_date="20",  # type: ignore
                beta=0.0,
                price_to_earnings=PriceToEarnings(
                    trailing_pe=0.0,
                    forward_pe=0.0,
                ),
                market_cap="N/A",  # type: ignore
                currency="N/A"  # type: ignore
            )
        ).normalize_values()

        test_cases = [
            # TestCase(none_value=general_stock_info.country), # TODO (Hanna): Fix this when we support country properly
            TestCase(none_value=general_stock_info.long_business_summary),
            TestCase(none_value=general_stock_info.financial_summary.previous_close),
            TestCase(none_value=general_stock_info.financial_summary.market_cap),
            TestCase(none_value=general_stock_info.financial_summary.currency),
            TestCase(none_value=general_stock_info.financial_summary.dividend_rate)
        ]

        for case in test_cases:
            self.assertIsNone(case.none_value)

    def test_financial_data(self):
        financial_data = FinancialData(
            price=10,
            target_high_price=0,
            target_low_price=0,
            recommendation_mean=0,
            recommendation_key=None,
            number_of_analyst_opinions=0,
            total_revenue=0.00000,
            revenue_per_share="",  # type: ignore
            revenue_growth="N/A",  # type: ignore
            total_debt=-1,
            debt_to_equity=0,
            profit_margins=3,
            gross_profit_margins="N/A",  # type: ignore
            operating_margins=None,
            dividend_rate=0,
            dividend_yield=0,
            five_year_avg_dividend_yield=0,
            trailing_annual_dividend_rate=0,
            trailing_annual_dividend_yield=0,
            free_cash_flow=0,
            operating_cash_flow=0,
            enterprise_to_ebitda=0,
            price_to_book=0,
            return_on_assets=0,
            return_on_equity=0,
            net_income_to_common=0,
            earnings_growth=0,
            book_value=0,
            price_to_earnings=PriceToEarnings(
                trailing_pe="N/A",  # type: ignore
                forward_pe=2
            ),
            earnings_per_share=EarningsPerShare(
                trailing_eps=2,
                forward_eps="N/A"  # type: ignore
            ),
            enterprise_to_revenue=0,
            expenses=None
        ).normalize_values()

        test_cases = [
            TestCase(none_value=financial_data.revenue_per_share),
            TestCase(none_value=financial_data.revenue_growth),
            TestCase(none_value=financial_data.total_debt),
            TestCase(none_value=financial_data.total_debt),
            TestCase(none_value=financial_data.gross_profit_margins),
            TestCase(none_value=financial_data.operating_margins),
            TestCase(none_value=financial_data.price_to_earnings.trailing_pe),
            TestCase(none_value=financial_data.earnings_per_share.forward_eps),
            TestCase(none_value=financial_data.expenses)
        ]

        for case in test_cases:
            self.assertIsNone(case.none_value)

    def test_expenses(self):
        expenses = Expenses(
            capital_expenditure=float('nan'),
            interest_expense=None,
            interest_expense_non_operating="N/A",  # type: ignore
            total_other_finance_cost=0
        ).normalize_values()

        test_cases = [
            TestCase(none_value=expenses.capital_expenditure),
            TestCase(none_value=expenses.interest_expense),
            TestCase(none_value=expenses.interest_expense_non_operating),
        ]

        for case in test_cases:
            self.assertIsNone(case.none_value)

    def test_calculate_price_to_cashflow(self):
        test_cases = [
            TestCase(price=None, cash_flow=10, expected_result=None),
            TestCase(price=10, cash_flow=None, expected_result=None),
            TestCase(price=100.0, cash_flow=10.0, expected_result=10.0),
            TestCase(price=0.0, cash_flow=10.0, expected_result=0.0),
            TestCase(price=0.0, cash_flow=0.0, expected_result=None),
            TestCase(price=100.0, cash_flow=-10.0, expected_result=-10),
            TestCase(price=-100.0, cash_flow=10.0, expected_result=-10),
            TestCase(price=-100.0, cash_flow=-10.0, expected_result=10),
            TestCase(price=100.0, cash_flow=3.3333333333333335, expected_result=30.0),
            TestCase(price=1e10, cash_flow=1e9, expected_result=10.0),
            TestCase(price=1e-10, cash_flow=1e-10, expected_result=1.0),
            TestCase(price=123456.789, cash_flow=0.0001, expected_result=1234567890.0),
            TestCase(price=100.0, cash_flow=0.000001, expected_result=100000000.0)
        ]

        for case in test_cases:
            self.assert_price_to_cash_flow(
                financial_data=self.financial_data,
                price=case.price,
                cash_flow=case.cash_flow,
                expected=case.expected_result
            )

    def test_get_and_set_cash_flow(self):
        operating_cash_flow = 100
        free_cash_flow = 50

        self.financial_data.set_cash_flow(
            cash_flow=operating_cash_flow,
            cash_flow_type=CashFlowType.OPERATING_CASH_FLOW
        )
        self.financial_data.set_cash_flow(cash_flow=free_cash_flow, cash_flow_type=CashFlowType.FREE_CASH_FLOW)
        operating_cash_flow_result = self.financial_data.get_cash_flow(cash_flow_type=CashFlowType.OPERATING_CASH_FLOW)
        free_cash_flow_result = self.financial_data.get_cash_flow(cash_flow_type=CashFlowType.FREE_CASH_FLOW)

        assert operating_cash_flow_result == operating_cash_flow
        assert free_cash_flow_result == free_cash_flow

    def test_calculate_return_on_investments(self):
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=1000,
            book_value=2000,
            total_debt=1000,
            expected=0.33
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=0,
            book_value=2000,
            total_debt=1000,
            expected=0.0
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=1000,
            book_value=0,
            total_debt=0,
            expected=None
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=0,
            book_value=0,
            total_debt=0,
            expected=None
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=None,
            book_value=None,
            total_debt=None,
            expected=None
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=-1000,
            book_value=2000,
            total_debt=1000,
            expected=-0.33
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=1000,
            book_value=2000,
            total_debt=-1000,
            expected=1.00
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=1000,
            book_value=1000,
            total_debt=-1000,
            expected=None
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=10,
            book_value=33,
            total_debt=67,
            expected=0.1  # Test for precision with decimal results
        )
        self.assert_return_on_invested_capital(
            financial_data=self.financial_data,
            net_income_to_common=-100,
            book_value=1000,
            total_debt=-1000,
            expected=None
        )

    def test_calculate_return_on_investment(self):
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=0,
                interest_expense=None,
                interest_expense_non_operating=0,
                total_other_finance_cost=0
            ),
            expected=GenericError
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=0,
                interest_expense=0,
                interest_expense_non_operating=0,
                total_other_finance_cost=0
            ),
            expected=GenericError
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=0,
                interest_expense=1,
                interest_expense_non_operating=0,
                total_other_finance_cost=0
            ),
            expected=1.0
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=1,
                interest_expense=1,
                interest_expense_non_operating=0,
                total_other_finance_cost=0
            ),
            expected=0.5
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=-1,
                interest_expense=-1,
                interest_expense_non_operating=0,
                total_other_finance_cost=0
            ),
            expected=-0.5
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=None,
                interest_expense=None,
                interest_expense_non_operating=None,
                total_other_finance_cost=None
            ),
            expected=GenericError
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=-10,
                interest_expense=10,
                interest_expense_non_operating=0,
                total_other_finance_cost=0
            ),
            expected=GenericError
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=-10,
                interest_expense=10,
                interest_expense_non_operating=0,
                total_other_finance_cost=0
            ),
            expected=GenericError
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=10,
                interest_expense=None,
                interest_expense_non_operating=5,
                total_other_finance_cost=5
            ),
            expected=GenericError
        )
        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=10,
                interest_expense=10,
                interest_expense_non_operating=10,
                total_other_finance_cost=10
            ),
            expected=0.03  # real result 0.025
        )

        self.assert_return_on_investment(
            financial_data=self.financial_data,
            expenses=Expenses(
                capital_expenditure=1e9,
                interest_expense=1e9,
                interest_expense_non_operating=1e9,
                total_other_finance_cost=1e9
            ),
            expected=0.0
        )

    def test_type_checking(self):
        expenses: Expenses = Expenses(
            capital_expenditure=1.0,
            interest_expense="1.01",  # type: ignore
            interest_expense_non_operating="Zero",  # type: ignore
            total_other_finance_cost=None
        ).normalize_values()

        self.assertIsNotNone(expenses.interest_expense)
        assert expenses.interest_expense == 1.01
        self.assertIsNone(expenses.interest_expense_non_operating)
        self.assertIsNone(expenses.total_other_finance_cost)

        financial_data = FinancialData(
            price=10,
            target_high_price=0,
            target_low_price=0,
            recommendation_mean=0,
            recommendation_key=None,
            number_of_analyst_opinions=0,
            total_revenue=0.00000,
            revenue_per_share="",  # type: ignore
            revenue_growth="N/A",  # type: ignore
            total_debt=-1,
            debt_to_equity=0,
            profit_margins=3,
            gross_profit_margins="n/a",  # type: ignore
            operating_margins=None,
            dividend_rate=0,
            dividend_yield=0,
            five_year_avg_dividend_yield=0,
            trailing_annual_dividend_rate=0,
            trailing_annual_dividend_yield=0,
            free_cash_flow=0,
            operating_cash_flow=0,
            enterprise_to_ebitda=0,
            price_to_book=0,
            return_on_assets=0,
            return_on_equity=0,
            net_income_to_common=0,
            earnings_growth=0,
            book_value=0,
            price_to_earnings=PriceToEarnings(
                trailing_pe="N/A",  # type: ignore
                forward_pe="2.0"  # type: ignore
            ),
            earnings_per_share=EarningsPerShare(
                trailing_eps=10,
                forward_eps="Test"  # type: ignore
            ),
            enterprise_to_revenue=10,
            expenses=None,
        ).normalize_values()

        assert financial_data.price_to_earnings.forward_pe == 2.0
        assert financial_data.earnings_per_share.trailing_eps == 10.0
        self.assertIsNone(financial_data.price_to_earnings.trailing_pe)
        self.assertIsNone(financial_data.gross_profit_margins)
        self.assertIsNone(financial_data.earnings_per_share.forward_eps)

        financial_data.price = "10"
        financial_data.five_year_avg_dividend_yield = "n/a"
        financial_data.debt_to_equity = "Test"
        financial_data.normalize_values()

        assert financial_data.price == 10.0
        self.assertIsNone(financial_data.five_year_avg_dividend_yield)
        self.assertIsNone(financial_data.debt_to_equity)

    def test_evaluate_growth_criteria_for_revenue_and_earnings_history(self):
        self.yearly_financials_data_positive = [
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.FIRST_QUARTER),
                earnings=100,
                revenue=100.75
            ),
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.SECOND_QUARTER),
                earnings=120,
                revenue=110
            ),
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.THIRD_QUARTER),
                earnings=150,
                revenue=150.25
            )
        ]

        self.yearly_financials_data_negative = [
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.FIRST_QUARTER),
                earnings=-50,
                revenue=-40.25
            ),
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.SECOND_QUARTER),
                earnings=-30,
                revenue=-20.5
            ),
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.THIRD_QUARTER),
                earnings=-10,
                revenue=0
            )
        ]

        self.yearly_financials_data_unsorted = [
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.THIRD_QUARTER),
                earnings=150,
                revenue=140.75
            ),
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.SECOND_QUARTER),
                earnings=120,
                revenue=110
            ),
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.FIRST_QUARTER),
                earnings=100,
                revenue=90.25
            )
        ]

        self.yearly_financials_data_no_always_up_trending = [
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.FIRST_QUARTER),
                earnings=100,
                revenue=100.75
            ),
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.SECOND_QUARTER),
                earnings=150,
                revenue=110
            ),
            YearlyFinancialsDataChart(
                date=Date(year=2022, quarter=Quarter.THIRD_QUARTER),
                earnings=120,
                revenue=150.25
            )
        ]

        result = HistoricalEarningsData.evaluate_growth_criteria(
            self.yearly_financials_data_positive,
            GrowthCriteria.EARNINGS.percentage_criteria,
            GrowthCriteria.EARNINGS.attribute
        )
        self.assertTrue(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            chart_list=self.yearly_financials_data_positive,
            percentage_criteria=30,
            attribute=GrowthCriteria.EARNINGS.attribute,
        )
        self.assertFalse(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            self.yearly_financials_data_negative,
            GrowthCriteria.EARNINGS.percentage_criteria,
            GrowthCriteria.EARNINGS.attribute
        )
        self.assertTrue(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            chart_list=self.yearly_financials_data_negative,
            percentage_criteria=30,
            attribute=GrowthCriteria.EARNINGS.attribute,
        )
        self.assertTrue(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            chart_list=self.yearly_financials_data_negative,
            percentage_criteria=45,
            attribute=GrowthCriteria.EARNINGS.attribute,
        )
        self.assertFalse(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            self.yearly_financials_data_unsorted,
            GrowthCriteria.EARNINGS.percentage_criteria,
            GrowthCriteria.EARNINGS.attribute
        )
        self.assertTrue(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            chart_list=self.yearly_financials_data_unsorted,
            percentage_criteria=30,
            attribute=GrowthCriteria.EARNINGS.attribute,
        )
        self.assertFalse(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            self.yearly_financials_data_positive,
            GrowthCriteria.REVENUE.percentage_criteria,
            GrowthCriteria.REVENUE.attribute
        )
        self.assertFalse(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            chart_list=self.yearly_financials_data_positive,
            percentage_criteria=5,
            attribute=GrowthCriteria.REVENUE.attribute,
        )
        self.assertTrue(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            self.yearly_financials_data_negative,
            GrowthCriteria.REVENUE.percentage_criteria,
            GrowthCriteria.REVENUE.attribute
        )
        self.assertTrue(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            chart_list=self.yearly_financials_data_negative,
            percentage_criteria=50,
            attribute=GrowthCriteria.REVENUE.attribute,
        )
        self.assertFalse(result)

        result = HistoricalEarningsData.evaluate_growth_criteria(
            chart_list=self.yearly_financials_data_no_always_up_trending,
            percentage_criteria=GrowthCriteria.REVENUE.percentage_criteria,
            attribute=GrowthCriteria.REVENUE.attribute,
        )
        self.assertFalse(result)
