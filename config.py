import os
from datetime import datetime

from context.ticker_scraper.main.const import STOCK_COLLECTIONS_PATH
from const import GENERATED_CSV_FILES_PATH

TIME_STAMP = datetime.now().strftime("%Y-%m-%d")

RUN_TESTS = True
GENERATE_TICKER_CSV = True
GENERATE_COMPARABLE_CSV = True

USE_OPTIMIZED_ALGORITHM = False


CASTABLE_DATA_SHOW_DEBUG_PRINT = False
QUARTER_SHOW_DEBUG_PRINT = True
ITERABLE_DATA_SHOW_DEBUG_PRINT = True


def initialize_environment():
    if not os.path.exists(STOCK_COLLECTIONS_PATH):
        os.makedirs(STOCK_COLLECTIONS_PATH)

    if not os.path.exists(GENERATED_CSV_FILES_PATH):
        os.makedirs(GENERATED_CSV_FILES_PATH)
