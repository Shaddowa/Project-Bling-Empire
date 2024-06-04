from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import requests
from yahooquery import Ticker
from context.ticker_scraper.main.classes.stock_collection import StockCollectionClass
from .currency import CurrencyValue, Currency


def convert_currency_value_to_default_currency(value: float, from_currency: Currency, to_currency=Currency.NOK) -> float:
    # https://exchange.nanoapi.dev/
    if from_currency != to_currency:
        response = requests.get(
            "https://exchange.nanoapi.dev/api/exchange",
            params={
                "from": from_currency.value,
                "to": to_currency.value,
                "amount": value,
            },
            headers={
                "Authorization": "FREE",
            },
            timeout=10
        )

        return response.json()["nanoapi"]
    return value


@dataclass
class StockPurchase:
    stock_collection: StockCollectionClass
    ticker: str
    quantity: float
    price: CurrencyValue
    brokerage: CurrencyValue
    date: Optional[datetime] = None
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
        portfolio_value = {Currency.NOK:  0.0, Currency.USD: 0.0}
        stocks_quantity_dict = self._get_stock_quantity_dict()

        for stock in stocks_quantity_dict:
            YQTicker = Ticker(stock)
            current_price = YQTicker.financial_data.get(stock).get("currentPrice")
            currency = YQTicker.summary_detail.get(stock).get("currency")
            sum_stock_value = stocks_quantity_dict[stock]["quantity"] * current_price
            portfolio_value[Currency.from_str(currency)] += sum_stock_value

        return portfolio_value

    def sum_local_currency(self, local_currency=Currency.NOK) -> float:
        sum_local_currency = 0
        portfolio_value = self.sum()

        for currency in portfolio_value:
            sum_local_currency += convert_currency_value_to_default_currency(
                portfolio_value[currency],
                from_currency=currency,
                to_currency=local_currency
            )

        return round(sum_local_currency, 2)


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

