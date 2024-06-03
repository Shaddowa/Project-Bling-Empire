from context.yquery_ticker.main.enums.currency import Currency
from .stock_collection import StockCollectionClass


class StandardAndPoor500StocksClass(StockCollectionClass):

    def __init__(self, stock_index_name, source, column, table_index):
        super().__init__(stock_index_name, source, column, table_index)

    def get_default_currency(self):
        return Currency.USD.value

    def get_stock_ticker_suffixes_or_none(self):
        return None
