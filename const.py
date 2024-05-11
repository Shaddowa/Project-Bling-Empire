from context.ticker_scraper.main.const import TICKER_SCRAPER_TEST_PATH
from context.ticker_scraper.main.stock_collections import NORWAY, STANDARD_AND_POOR_500
from context.yquery_ticker.main.const import YQUERY_TEST_PATH


class CONST_COLLECTION:

    STCOK_COLLECTION_LIST = [
        NORWAY,
        STANDARD_AND_POOR_500,
        # GERMANY,
        # HONG_KONG,
        # UNITED_KINGDOM, They changed table format
        # NETHERLANDS,
        # FRANCE
    ]


GENERATED_CSV_FILES_PATH = "generated_csv_files/"
BLACKLISTED_STOCK_TICKERS_PATH = 'blacklisted_stock_ticker/'
AUTO_GENERATED_FILE_STRING = " ### This file is auto generated and shouldn't be touched! ### "
TEST_PATHS = [
    TICKER_SCRAPER_TEST_PATH,
    YQUERY_TEST_PATH,
]
CONST_COLLECTION = CONST_COLLECTION()
