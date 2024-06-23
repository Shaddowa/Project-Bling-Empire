from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from yahooquery import Ticker
from context.ticker_scraper.main.classes.stock_collection import StockCollectionClass
from ..currency import CurrencyValue, Currency
from ...curreny_requests import convert_currency_value_to_default_currency


@dataclass
class StockPurchase:
    stock_collection: StockCollectionClass
    ticker: str
    quantity: float
    price: CurrencyValue
    brokerage: CurrencyValue
    exchange_rate: Optional[CurrencyValue] = CurrencyValue(1, Currency.NOK)
    date: Optional[datetime] = None


@dataclass
class StockPortfolio:
    stocks: list[
        StockPurchase
    ]

    @staticmethod
    def calculate_roi_for_each_stock(stocks_dict_local_currency) -> dict:
        for stock in stocks_dict_local_currency:
            stocks_dict_local_currency[stock]["roi"] = (
                    convert_currency_value_to_default_currency(   # Add date parameter
                        stocks_dict_local_currency[stock]["value"],
                        from_currency=stocks_dict_local_currency[stock]["base_currency"]
                    ) - stocks_dict_local_currency[stock]["cost_price"]
            )
        return stocks_dict_local_currency

    def calculate_roi_for_whole_portfolio(self) -> float:
        sum_roi = 0
        stocks_dict = self._get_stock_dict()
        for stock in stocks_dict:
            sum_roi += stocks_dict[stock]["roi"]

        return sum_roi

    @staticmethod
    def _get_current_value_for_stocks(stock_dict: dict) -> dict:
        for stock in stock_dict:
            YQTicker = Ticker(stock)
            current_price = YQTicker.financial_data.get(stock).get("currentPrice")
            currency = YQTicker.summary_detail.get(stock).get("currency")
            sum_stock_value = stock_dict[stock]["quantity"] * current_price
            stock_dict[stock]["value"] = sum_stock_value
            stock_dict[stock]["base_currency"] = Currency.from_str(currency)
        return stock_dict

    @staticmethod
    def _get_stock_cost_price(stock: StockPurchase) -> float:
        return (stock.quantity * stock.price.value * stock.exchange_rate.value) + stock.brokerage.value

    def _get_stock_dict(self) -> dict:
        stocks_dict_local_currency = {}
        for stock in self.stocks:

            stock_ticker_suffixes = stock.stock_collection.get_stock_ticker_suffixes_or_none()

            if stock_ticker_suffixes:
                stock_ticker = stock.ticker + stock_ticker_suffixes[0]
            else:
                stock_ticker = stock.ticker

            if stock_ticker in stocks_dict_local_currency:
                stocks_dict_local_currency[stock_ticker]["quantity"] += stock.quantity
                stocks_dict_local_currency[stock_ticker]["cost_price"] += self._get_stock_cost_price(stock)

            else:
                stocks_dict_local_currency[stock_ticker] = {
                    "quantity": stock.quantity,
                    "cost_price": self._get_stock_cost_price(stock)
                }
        return self.calculate_roi_for_each_stock(self._get_current_value_for_stocks(stocks_dict_local_currency))

    def sum(self) -> dict:
        portfolio_value = {Currency.NOK: 0.0, Currency.USD: 0.0}
        stocks_dict = self._get_stock_dict()
        for stock in stocks_dict:
            portfolio_value[stocks_dict[stock]["base_currency"]] += stocks_dict[stock]["value"]
        return portfolio_value

    def sum_local_currency(self, local_currency=Currency.NOK) -> float:
        sum_local_currency = 0
        portfolio_value = self.sum()

        for currency in portfolio_value:
            sum_local_currency += convert_currency_value_to_default_currency(  # Add date parameter
                portfolio_value[currency],
                from_currency=currency,
                to_currency=local_currency
            )
        return round(sum_local_currency, 2)
