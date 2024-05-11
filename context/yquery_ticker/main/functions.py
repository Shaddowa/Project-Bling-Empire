import csv
import os
import re
import concurrent.futures
from typing import Optional, Dict, List, TextIO
from yahooquery import Ticker

from config import ITERABLE_DATA_SHOW_DEBUG_PRINT, USE_OPTIMIZED_ALGORITHM, TIME_STAMP
from const import (
    BLACKLISTED_STOCK_TICKERS_PATH,
    CONST_COLLECTION, AUTO_GENERATED_FILE_STRING, GENERATED_CSV_FILES_PATH
)
from context.ticker_scraper.main.classes.stock_collection import StockCollectionClass
from context.yquery_ticker.main.classes.global_stock_data import YahooStockDataClass, SimpleStockDataClass
from context.yquery_ticker.main.const import DATA_NOT_AVAILABLE


def _passed_yahoo_query_validation_check(ticker_symbol: str, ticker: Ticker) -> bool:
    try:
        if DATA_NOT_AVAILABLE in ticker.summary_detail.get(ticker_symbol) or \
                DATA_NOT_AVAILABLE in ticker.financial_data.get(ticker_symbol) or \
                DATA_NOT_AVAILABLE in ticker.key_stats.get(ticker_symbol) or \
                DATA_NOT_AVAILABLE in ticker.earnings[ticker_symbol] or \
                ticker.earnings.items() == {} or \
                isinstance(ticker.cash_flow(), str) or ticker.cash_flow().empty is True:
            return False
    except Exception as e:
        print(f"Failed yahoo query validation check for ticker: {ticker_symbol} - {e}")
        return False
    return True


def validate_and_get_yahoo_query_ticker_object(ticker_symbol: str) -> Optional[YahooStockDataClass]:
    yquery_ticker = Ticker(ticker_symbol)
    if _passed_yahoo_query_validation_check(ticker_symbol=ticker_symbol, ticker=yquery_ticker):
        return YahooStockDataClass(
            ticker_symbol=ticker_symbol
        )
    else:
        if ITERABLE_DATA_SHOW_DEBUG_PRINT:
            print(f"Required information for ticker {ticker_symbol} is missing.")
    return None


def _open_or_create_blacklisted_stock_file(stock_collection: str) -> TextIO:
    full_blacklisted_path = BLACKLISTED_STOCK_TICKERS_PATH + stock_collection + ".txt"

    if not os.path.exists(BLACKLISTED_STOCK_TICKERS_PATH):
        os.makedirs(BLACKLISTED_STOCK_TICKERS_PATH)

    if not os.path.exists(full_blacklisted_path):
        with open(full_blacklisted_path, "a+") as file:
            file.write(AUTO_GENERATED_FILE_STRING)

    return open(full_blacklisted_path, "r+")


def _get_query_ticker_objects_from_csv(stock_collection: StockCollectionClass) -> List[SimpleStockDataClass]:
    csv_tickers: List[SimpleStockDataClass] = []

    folder_path = f'{GENERATED_CSV_FILES_PATH}{stock_collection.stock_index_name}'

    # KEYS
    TICKER = "Ticker"
    COMPANY = "Company"
    WEBSITE = "Website"
    INDUSTRY = "Industry"
    SECTOR = "Sector"
    PRICE = "Price"
    TARGET_HIGH_PRICE = "Target High Price"
    RECOMMENDATION_MEAN = "Recommendation Mean"
    ANALYST_RATING_SCORE = "Analyst Rating Score"
    CURRENCY = "Currency"
    CRITERIA_PASS_COUNT = "CRITERIA PASS COUNT"
    DIVIDEND_SCORE = "DIVIDEND SCORE"

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        simple_stock_data = {}
        if os.path.isfile(file_path):
            with open(file_path, 'r', newline='') as file:
                reader = csv.reader(file, delimiter='\t')
                for row in reader:
                    if len(row) != 0:
                        comma_separated_row = [value.strip() for value in row[0].strip().split(',')]
                        if len(comma_separated_row) == 2:
                            key = comma_separated_row[0]
                            value = comma_separated_row[1]
                            if key in [
                                TICKER,
                                COMPANY,
                                WEBSITE,
                                INDUSTRY,
                                SECTOR,
                                PRICE,
                                TARGET_HIGH_PRICE,
                                RECOMMENDATION_MEAN,
                                CURRENCY,
                                CRITERIA_PASS_COUNT,
                                DIVIDEND_SCORE
                            ]:
                                simple_stock_data[key] = value.strip()

                csv_tickers.append(
                    SimpleStockDataClass(
                        ticker_symbol=simple_stock_data[TICKER],
                        company=simple_stock_data[COMPANY] if COMPANY in simple_stock_data else "",
                        website=simple_stock_data[WEBSITE],
                        industry=simple_stock_data[INDUSTRY],
                        sector=simple_stock_data[SECTOR],
                        price=simple_stock_data[PRICE],
                        target_high_price=simple_stock_data[TARGET_HIGH_PRICE],
                        recommendation_mean=simple_stock_data[RECOMMENDATION_MEAN],
                        analyst_rating_score=simple_stock_data[ANALYST_RATING_SCORE],
                        currency=simple_stock_data[CURRENCY],
                        criteria_pass_count=simple_stock_data[CRITERIA_PASS_COUNT],
                        dividend_score=simple_stock_data[DIVIDEND_SCORE]
                    )
                )
    return csv_tickers


def _get_query_ticker_objects_from_api(stock_collection: StockCollectionClass) -> List[YahooStockDataClass]:
    yquery_tickers: List[YahooStockDataClass] = []

    blacklisted_stocks_file = _open_or_create_blacklisted_stock_file(stock_collection.stock_index_name)

    blacklisted_stocks_file_content = blacklisted_stocks_file.read()

    stock_tickers_file = open(stock_collection.file_path, "r").readlines()

    for ticker in stock_tickers_file:
        stripped_ticker = ticker.strip()
        if re.search(ticker, blacklisted_stocks_file_content) is None:
            yquery_ticker = Ticker(stripped_ticker)
            if not _passed_yahoo_query_validation_check(ticker_symbol=stripped_ticker, ticker=yquery_ticker):
                if ITERABLE_DATA_SHOW_DEBUG_PRINT:
                    print(f"Required information for ticker {stripped_ticker} is missing.")
                blacklisted_stocks_file.write(f"{stripped_ticker}\n")
            else:
                if ITERABLE_DATA_SHOW_DEBUG_PRINT:
                    print(f"Found information for ticker {stripped_ticker}")
                ticker = YahooStockDataClass(ticker_symbol=stripped_ticker, ticker=yquery_ticker)
                yquery_tickers.append(ticker)
        else:
            if ITERABLE_DATA_SHOW_DEBUG_PRINT:
                print(f"Ticker symbol: {stripped_ticker} found in blacklisted stock file and will be skipped")

    blacklisted_stocks_file.close()
    return yquery_tickers


def get_grouped_yahoo_query_ticker_objects() -> Dict[
    StockCollectionClass, List[YahooStockDataClass | SimpleStockDataClass]]:
    stock_collection_tickers: Dict[StockCollectionClass, List[YahooStockDataClass | SimpleStockDataClass]] = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Create a dictionary to store the future and corresponding stock collection
        futures_to_collections = {
            executor.submit(
                _get_query_ticker_objects_from_csv if USE_OPTIMIZED_ALGORITHM and os.path.exists(
                    f'{GENERATED_CSV_FILES_PATH}{stock_collection.stock_index_name}/comparison/{TIME_STAMP}/'
                ) else _get_query_ticker_objects_from_api,
                stock_collection,
            ): stock_collection
            for stock_collection in CONST_COLLECTION.STCOK_COLLECTION_LIST
        }

        # Iterate over completed futures and retrieve results
        for future in concurrent.futures.as_completed(futures_to_collections):
            stock_collection = futures_to_collections[future]
            try:
                result = future.result()
                stock_collection_tickers[stock_collection] = result
            except Exception as e:
                print(f"An error occurred while processing {stock_collection}: {e}")
    return stock_collection_tickers
