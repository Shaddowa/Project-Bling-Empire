from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import requests
from yahooquery import Ticker
from context.ticker_scraper.main.classes.stock_collection import StockCollectionClass
from .currency import CurrencyValue, Currency
from ..firi_requests import get_grouped_transaction_history_by_year, get_filtered_transaction_history, \
    get_summed_transaction_history
import yfinance as yf


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
class CryptoCoin:
    currency: Currency
    quantity: float


@dataclass
class CryptoPortfolio:
    coins: list[
        CryptoCoin
    ]

    def _parse_summed_transaction_history(self, summed_transaction_history):
        for currency in summed_transaction_history:
            self.coins.append(
                CryptoCoin(
                    currency=currency,
                    quantity=summed_transaction_history[currency]["total_amount"]
                )
            )

        return self

    def _get_crypto_dict(self) -> dict:
        crypto_dict = {}
        for coin in self.coins:
            crypto_ticker = yf.Ticker(f"{coin.currency.value}-USD")
            closing_price = crypto_ticker.info.get("regularMarketPreviousClose")
            crypto_dict[coin.currency] = (
                convert_currency_value_to_default_currency(
                    value=coin.quantity * closing_price, from_currency=Currency.USD
                )
            )
        return crypto_dict

    def sum(self) -> dict:
        portfolio_value = {Currency.NOK: 0.0}
        crypto_dict = self._get_crypto_dict()

        for coin in crypto_dict:
            portfolio_value[Currency.NOK] += crypto_dict[coin]

        return portfolio_value

    @staticmethod
    def synchronize_with_firi() -> "CryptoPortfolio":
        grouped_transaction_history = get_grouped_transaction_history_by_year(years=[2023, 2024])
        filtered_transaction_history = get_filtered_transaction_history(grouped_transaction_history)
        return CryptoPortfolio(coins=[])._parse_summed_transaction_history(
            get_summed_transaction_history(filtered_transaction_history)
        )


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
                convert_currency_value_to_default_currency(
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
