import pandas as pd
from .stock_collection import StockCollectionClass


class UnitedKingdomStocksClass(StockCollectionClass):

    def __init__(self, stock_index_name, source, table_index, column, stock_ticker_suffixes):
        # :param stock_ticker_suffixes: The possible stock ticker endings required by yquery
        super().__init__(stock_index_name, source, column, table_index)
        self.stock_ticker_suffixes = stock_ticker_suffixes

    def save_stock_tickers_data_frame_to_csv(self, data_frame):
        self._data_frame_to_csv(data_frame=self.modify_tickers(data_frame))

    def get_default_currency(self):
        return None

    def modify_tickers(self, df):
        L = self.stock_ticker_suffixes[0]
        IL = self.stock_ticker_suffixes[1]

        df1 = df[self.column]
        df2 = df.copy()[self.column] + L
        df3 = df.copy()[self.column] + IL

        return pd.concat([df1, df2, df3])

    def get_stock_ticker_suffixes_or_none(self):
        return self.stock_ticker_suffixes
