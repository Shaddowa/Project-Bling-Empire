import pandas as pd
from abc import ABC, abstractmethod


from context.ticker_scraper.main.const import FILE_NAME_SUFFIX, STOCK_COLLECTIONS_PATH


class StockCollectionClass(ABC):

    def __init__(self, stock_index_name, source, column, table_index):
        """
        :param stock_index_name: The name of the stock collection.
        :param source: The source of the stock data.
        :param column: The column where the tickers are located.
        :param table_index: The index of the stock data table.
        """
        self.stock_index_name = stock_index_name
        self.source = source
        self.file_name = self.stock_index_name + FILE_NAME_SUFFIX
        self.file_path = f"{STOCK_COLLECTIONS_PATH}{self.file_name}"
        self.column = column
        self.table_index = table_index

    def _data_frame_to_csv(self, data_frame: pd.DataFrame, header=False, index=False):
        """
        Save a dataframe as a CSV file.

        :param data_frame: The dataframe to save.
        :param header: Whether to include the column names in the CSV file.
        :param index: Whether to include the row index in the CSV file.
        """
        data_frame.to_csv(
            self.file_path,
            columns=[self.column],
            header=header,
            index=index
        )

    def save_stock_tickers_data_frame_to_csv(self, data_frame):
        self._data_frame_to_csv(data_frame=data_frame)

    def fetch_stock_tickers_data_frame(self):
        """
        Get the dataframe at the specified table index.
        """
        tables = pd.read_html(self.source)
        return tables[self.table_index]

    @abstractmethod
    def get_default_currency(self):
        pass

    @abstractmethod
    def get_stock_ticker_suffixes_or_none(self):
        pass

    def __str__(self):
        return self.stock_index_name
