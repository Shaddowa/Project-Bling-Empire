import csv
import os
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Dict, List
from config import TIME_STAMP
from const import GENERATED_CSV_FILES_PATH
from context.ticker_scraper.main.classes.stock_collection import StockCollectionClass
from context.yquery_ticker.main.classes.global_stock_data import YahooStockDataClass, SimpleStockDataClass
from context.yquery_ticker.main.utils.dict_key_enum import DictKey

GENERATE_INDIVIDUAL_TICKER_CSV = True
GENERATE_DIVIDEND_SCORE_CSV = True
GENERATE_ANALYST_RATING_CSV = True


class DividendScoreHeaders(Enum):
    TICKER = "TICKER"
    DIVIDEND_SCORE = "DIVIDEND SCORE"


class AnalystRatingHeaders(Enum):
    TICKER = "TICKER"
    TARGET_HIGH_PRICE = "TARGET HIGH PRICE"
    TARGET_LOW_PRICE = "TARGET LOW PRICE"
    RECOMMENDATION_MEAN = "RECOMMENDATION MEAN"
    RECOMMENDATION_KEY = "RECOMMENDATION KEY"
    NUMBER_OF_ANALYSTS = "NUMBER OF ANALYSTS"
    ANALYST_RATING = "ANALYST RATING SCORE"


class MainCriteriaHeaders(Enum):
    TICKER = "TICKER"
    COMPANY = "COMPANY"
    WEBSITE = "WEBSITE"
    INDUSTRY = "INDUSTRY"
    SECTOR = "SECTOR"
    PRICE = "PRICE"
    CURRENCY = "CURRENCY"
    CRITERIA_PASS_COUNT = "CRITERIA PASSED"
    DIVIDEND_SCORE = "DIVIDEND SCORE"
    ANALYST_RATING = "ANALYST RATING SCORE"


class CSVType(Enum):
    MAIN_CRITERIA = ("MAIN_CRITERIA", MainCriteriaHeaders, "ticker_comparison_by_criteria.csv")
    DIVIDEND_SCORE = ("DIVIDEND_SCORE", DividendScoreHeaders, "ticker_comparison_by_dividend.csv")
    ANALYST_RATING = ("ANALYST_RATING", AnalystRatingHeaders, "ticker_comparison_by_analyst_rating.csv")

    @property
    def __str__(self):
        return self.value[0]

    @property
    def headers(self):
        return self.value[1]

    @property
    def path(self):
        return self.value[2]


class ComparableCSV:
    def __init__(self, stock_collection: Dict[StockCollectionClass, List[YahooStockDataClass | SimpleStockDataClass]]):
        self.stock_collection = stock_collection

    def _create_csv(
            self,
            pathPrefix: str,
            csv_type: CSVType,
            collection: StockCollectionClass
    ):
        with open(file=f"{pathPrefix}{csv_type.path}", mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([header.value for header in csv_type.headers])

            if len(self.stock_collection[collection]) > 0:
                first_stock = self.stock_collection[collection][0]
                if isinstance(first_stock, YahooStockDataClass):
                    self._create_from_tickers(
                        collection=collection,
                        writer=writer,
                        csv_type=csv_type
                    )
                elif isinstance(first_stock, SimpleStockDataClass):
                    self._create_from_csv_files(
                        collection=collection,
                        writer=writer,
                        csv_type=csv_type
                    )
        file.close()

    def create_csv_files(self):

        for collection in self.stock_collection.keys():

            pathPrefix = f'{GENERATED_CSV_FILES_PATH}{collection.stock_index_name}/comparison/{TIME_STAMP}/'
            if not os.path.exists(pathPrefix):
                os.makedirs(pathPrefix)
            if GENERATE_DIVIDEND_SCORE_CSV:
                self._create_csv(
                    pathPrefix=pathPrefix,
                    csv_type=CSVType.DIVIDEND_SCORE,
                    collection=collection
                )

            if GENERATE_ANALYST_RATING_CSV:
                self._create_csv(
                    pathPrefix=pathPrefix,
                    csv_type=CSVType.ANALYST_RATING,
                    collection=collection
                )

            self._create_csv(
                pathPrefix=pathPrefix,
                csv_type=CSVType.MAIN_CRITERIA,
                collection=collection,
            )

    @staticmethod
    def get_sort_key(csv_type: CSVType, stock_ticker, source):
        if csv_type is CSVType.DIVIDEND_SCORE:
            if source == "from_ticker":
                return stock_ticker.get_dividend_score()
            else:
                return stock_ticker.dividend_score
        elif csv_type is CSVType.ANALYST_RATING:
            if source == "from_ticker":
                return stock_ticker.get_analyst_rating_score()
            else:
                return stock_ticker.analyst_rating_score
        else:
            if source == "from_ticker":
                return stock_ticker.get_criteria_pass_count()
            else:
                return stock_ticker.criteria_pass_count

    def _create_from_tickers(
            self,
            collection: StockCollectionClass,
            writer: csv.writer,
            csv_type: CSVType
    ):

        sorted_collection: list[YahooStockDataClass] = sorted(
            self.stock_collection[collection],
            key=lambda stock_ticker: self.get_sort_key(csv_type, stock_ticker, source="from_ticker"),
            reverse=True
        )

        for ticker in sorted_collection:
            if GENERATE_INDIVIDUAL_TICKER_CSV:
                with ThreadPoolExecutor() as executor:
                    executor.submit(ticker.to_csv(stock_collection=collection.stock_index_name))

            if csv_type is CSVType.MAIN_CRITERIA:
                currency = ticker.general_stock_info.financial_summary.currency

                writer.writerow([
                    ticker.general_stock_info.ticker,
                    ticker.general_stock_info.company,
                    ticker.general_stock_info.website,
                    ticker.general_stock_info.industry,
                    ticker.general_stock_info.sector,
                    ticker.financial_data.price,
                    currency.value if currency is not None else collection.get_default_currency(),
                    int(ticker.get_criteria_pass_count()),
                    ticker.get_dividend_score(),
                    ticker.get_analyst_rating_score()
                ])
            elif csv_type is CSVType.DIVIDEND_SCORE:
                writer.writerow([
                    ticker.general_stock_info.ticker,
                    ticker.get_dividend_score()
                ])
            elif csv_type is CSVType.ANALYST_RATING:
                analyst_opinion_data = ticker.get_analyst_opinion_data()
                writer.writerow([
                    ticker.general_stock_info.ticker,
                    analyst_opinion_data.get(DictKey.TARGET_HIGH_PRICE.__str__),
                    analyst_opinion_data.get(DictKey.TARGET_LOW_PRICE.__str__),
                    analyst_opinion_data.get(DictKey.RECOMMENDATION_MEAN.__str__),
                    analyst_opinion_data.get(DictKey.RECOMMENDATION_KEY.__str__),
                    analyst_opinion_data.get(DictKey.NUMBER_OF_ANALYSTS.__str__),
                    ticker.get_analyst_rating_score()
                ])

    def _create_from_csv_files(
            self,
            collection: StockCollectionClass,
            writer: csv.writer,
            csv_type: CSVType
    ):
        sorted_collection: list[SimpleStockDataClass] = sorted(
            self.stock_collection[collection],
            key=lambda stock_ticker: self.get_sort_key(csv_type, stock_ticker, source="from_csv"),
            reverse=True
        )

        for ticker in sorted_collection:

            if csv_type is CSVType.MAIN_CRITERIA:
                writer.writerow([
                    ticker.ticker_symbol,
                    ticker.company,
                    ticker.website,
                    ticker.industry,
                    ticker.sector,
                    ticker.price,
                    ticker.currency,
                    ticker.criteria_pass_count,
                ])
            elif csv_type is CSVType.DIVIDEND_SCORE:
                writer.writerow([
                    ticker.ticker_symbol,
                    ticker.dividend_score
                ])
            elif csv_type is CSVType.ANALYST_RATING:
                writer.writerow([
                    ticker.ticker_symbol,
                    ticker.recommendation_mean,
                    ticker.target_high_price
                ])
