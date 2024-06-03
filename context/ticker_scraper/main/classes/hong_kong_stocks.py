import pandas as pd
from .stock_collection import StockCollectionClass


class HongKongStocksClass(StockCollectionClass):

    def __init__(self, stock_index_name, source, table_index_range, column, stock_ticker_suffixes):
        """
        :param table_index_range: The range of indices of the stock data tables.
        :param stock_ticker_suffixes: The possible stock ticker endings required by yquery.
        """
        super().__init__(stock_index_name, source, column, None)
        self.table_index_range = table_index_range
        self.stock_ticker_suffixes = stock_ticker_suffixes

    def get_data_frame(self, table_index_range):
        tables = pd.read_html(self.source)
        first_table_index = table_index_range[0]
        last_table_index = table_index_range[-1]

        df = pd.DataFrame()
        for table_index in range(first_table_index, last_table_index):
            df = pd.concat([df, tables[table_index]], axis=0)
        return df

    def fetch_stock_tickers_data_frame(self):
        return self.get_data_frame(table_index_range=self.table_index_range)

    def save_stock_tickers_data_frame_to_csv(self, data_frame):
        self._data_frame_to_csv(data_frame=self.modify_tickers(data_frame))

    def get_default_currency(self):
        return None

    def modify_tickers(self, df):
        HK = self.stock_ticker_suffixes[0]
        df[0] = df[0].str[:10]
        df[0] = df[0].str.replace(r'(\D+)', '', regex=True)
        return df[0].str.zfill(4) + HK

    def get_stock_ticker_suffixes_or_none(self):
        return self.stock_ticker_suffixes
