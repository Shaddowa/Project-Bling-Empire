from context.yquery_ticker.main.enums.currency import Currency
from .stock_collection import StockCollectionClass


class NorwegianStocksClass(StockCollectionClass):

    def __init__(self, stock_index_name, source, table_index, column, stock_ticker_suffixes):
        """
        :param stock_ticker_suffixes: The possible stock ticker endings required by yquery.
        """
        super().__init__(stock_index_name, source, column, table_index)
        self.stock_ticker_suffixes = stock_ticker_suffixes

    def save_stock_tickers_data_frame_to_csv(self, data_frame):
        self._data_frame_to_csv(data_frame=self.modify_tickers(data_frame))

    def modify_tickers(self, data_frame):
        OL = self.stock_ticker_suffixes[0]
        return data_frame[self.column].str.replace('OSE: ', '') + OL

    def get_default_currency(self):
        return Currency.NOK.value

    def get_stock_ticker_suffixes_or_none(self):
        return self.stock_ticker_suffixes
