import csv
from enum import Enum
from typing import Callable
from const import GENERATED_CSV_FILES_PATH
from context.yquery_ticker.main.data_classes.financial_summary import FinancialSummary
from context.yquery_ticker.main.data_classes.general_stock_info import GeneralStockInfo
from context.yquery_ticker.main.errors.generic_error import GenericError


class Section(Enum):
    GENERAL_STOCK_INFO = "GENERAL STOCK INFO"
    REVENUE = "REVENUE"
    EARNINGS = "EARNINGS"
    DEBT = "DEBT"
    MARGINS = "MARGINS"
    DIVIDEND = "DIVIDEND"
    FINANCIAL_RATIO = "FINANCIAL RATIO"
    CASH_FLOW = "CASH FLOW"
    PROFITABILITY = "PROFITABILITY"
    DIVIDEND_SCORE = "DIVIDEND SCORE"
    ANALYST_RATING_SCORE = "ANALYST RATING SCORE"
    GROWTH_CRITERIA = "PASSES GROWTH CRITERIA"


def _get_items(data_func):
    if isinstance(data_func, dict):
        return data_func.items()
    else:
        return data_func().items()


def _process_data_item(writer, key, value):
    if not isinstance(value, GenericError) and value is not None:
        writer.writerow([key, value])
    else:
        if value is None:
            writer.writerow([key, "None"])
        else:
            error = GenericError(value.reason)
            writer.writerow([key, error.reason])


class CsvConverter:

    @staticmethod
    def _to_csv(
            stock_collection: str,
            ticker_symbol: str,
            general_stock_info: GeneralStockInfo,
            revenue_data: Callable[[], dict],
            earnings_data: Callable[[], dict],
            debt_data: Callable[[], dict],
            margins_data: Callable[[], dict],
            dividends_data: Callable[[], dict],
            financial_ratio_data: Callable[[], dict],
            cash_flow_data: Callable[[], dict],
            profitability_data: Callable[[], dict],
            evaluated_dividend_score: Callable[[], dict],
            get_dividend_score: Callable[[], dict],
            evaluated_analyst_rating_score: Callable[[], dict],
            get_analyst_rating_score: Callable[[], dict],
            evaluated_growth_criteria: Callable[[], dict],
            get_criteria_pass_count: Callable[[], dict],
    ):
        mapped_data = {
            Section.REVENUE: revenue_data,
            Section.EARNINGS: earnings_data,
            Section.DEBT: debt_data,
            Section.MARGINS: margins_data,
            Section.DIVIDEND: dividends_data,
            Section.FINANCIAL_RATIO: financial_ratio_data,
            Section.CASH_FLOW: cash_flow_data,
            Section.PROFITABILITY: profitability_data,
            Section.DIVIDEND_SCORE: {**evaluated_dividend_score(), **get_dividend_score()},
            Section.ANALYST_RATING_SCORE: {**evaluated_analyst_rating_score(), **get_analyst_rating_score()},
            Section.GROWTH_CRITERIA: {**evaluated_growth_criteria(), **get_criteria_pass_count()},
        }

        with open(f"{GENERATED_CSV_FILES_PATH}/{stock_collection}/{ticker_symbol}.csv", mode='w', newline='') as file:
            writer = csv.writer(file)

            # Write general stock information section
            writer.writerow([Section.GENERAL_STOCK_INFO.value])
            for key, value in general_stock_info:
                if key != "long_business_summary":
                    if isinstance(value, FinancialSummary):
                        for _key, _value in general_stock_info.financial_summary:
                            if _key == "previous_close":
                                writer.writerow(["Price", _value])
                            if _key == "currency":
                                writer.writerow([_key.capitalize(), _value.value])
                    else:
                        value = value if value is not None else "None"
                        writer.writerow([key.capitalize(), value])

            writer.writerow([])

            # Write each section
            for section, data_func in mapped_data.items():
                if section == Section.GROWTH_CRITERIA:
                    writer.writerows([[], []])

                writer.writerow([section.value])  # Write section header

                for key, value in _get_items(data_func):
                    _process_data_item(writer, key, value)
                writer.writerow([])
        file.close()
