from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from yahooquery import Ticker
from context.ticker_scraper.main.classes.stock_collection import StockCollectionClass
from .currency import CurrencyValue


@dataclass
class StockPurchase:
    stock_collection: StockCollectionClass
    ticker: str
    quantity: float
    price: CurrencyValue
    brokerage: CurrencyValue
    date: datetime
    exchange_rate: Optional[CurrencyValue] = None


@dataclass
class StockPortfolio:
    stocks: list[
        StockPurchase
    ]

    def _get_stock_quantity_dict(self) -> dict:
        stocks_quantity_dict = {}
        for stock in self.stocks:
            stock_ticker_suffixes = stock.stock_collection.get_stock_ticker_suffixes_or_none()
            if stock_ticker_suffixes:
                stock_ticker = stock.ticker + stock_ticker_suffixes[0]
            else:
                stock_ticker = stock.ticker

            if stock_ticker in stocks_quantity_dict:
                stocks_quantity_dict[stock_ticker]["quantity"] += stock.quantity
            else:
                stocks_quantity_dict[stock_ticker] = {"quantity": stock.quantity}
        return stocks_quantity_dict

    def sum(self) -> dict:
        portfolio_value = {"NOK":  0.0, "USD": 0.0}
        stocks_quantity_dict = self._get_stock_quantity_dict()

        for stock in stocks_quantity_dict:
            YQTicker = Ticker(stock)
            current_price = YQTicker.financial_data.get(stock).get("currentPrice")
            currency = YQTicker.summary_detail.get(stock).get("currency")
            sum_stock_value = stocks_quantity_dict[stock]["quantity"] * current_price
            portfolio_value[currency] += sum_stock_value

        return portfolio_value


@dataclass
class TotalAssets:
    cash: float
    stocks: float
    funds: float
    crypto: float
    real_estate: float

    def sum(self) -> float:
        return sum(
            [
                self.cash,
                self.stocks,
                self.funds,
                self.crypto,
                self.real_estate
            ]
        )

