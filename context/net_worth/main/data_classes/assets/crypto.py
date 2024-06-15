import os
from dataclasses import dataclass
import yfinance as yf
from ..currency import CurrencyValue, Currency
from ..transaction_type import TransactionType
from ...functions import convert_currency_value_to_default_currency
from ...firi_requests import get_grouped_transaction_history_by_year


@dataclass
class CryptoCoin:
    currency: Currency
    quantity: float
    cost_price: CurrencyValue


@dataclass
class CryptoPortfolio:
    coins: list[
        CryptoCoin
    ]

    def sum_daedalus_coins(self) -> "CryptoPortfolio":
        self.coins.append(
            CryptoCoin(
                currency=Currency.ADA,
                quantity=float(os.getenv('ADA_DAEDALUS_COINS')),
                cost_price=CurrencyValue(
                    value=-1,  # Not sure what the cost price was...
                    currency=Currency.NOK
                )
            )
        )
        return self

    def _parse_summed_transaction_history(self, summed_transaction_history):
        for currency in summed_transaction_history:
            self.coins.append(
                CryptoCoin(
                    currency=currency,
                    quantity=summed_transaction_history[currency]["total_amount"],
                    cost_price=CurrencyValue(
                        value=convert_currency_value_to_default_currency(
                            summed_transaction_history[currency]["total_cost_price"],
                            from_currency=Currency.USD
                        ),
                        currency=Currency.NOK
                    )
                )
            )
        return self

    def _get_crypto_dict(self) -> dict:
        crypto_dict = {}
        for coin in self.coins:
            crypto_ticker = yf.Ticker(f"{coin.currency.value}-USD")
            closing_price = crypto_ticker.info.get("regularMarketPreviousClose")
            if closing_price:
                converted_value = convert_currency_value_to_default_currency(
                    coin.quantity * closing_price, from_currency=Currency.USD
                )
                if coin.currency.value not in crypto_dict:
                    crypto_dict[coin.currency.value] = {"value": converted_value, "roi": 0.0}
                else:
                    crypto_dict[coin.currency.value]["value"] += converted_value

                crypto_dict[coin.currency.value]["roi"] = (
                        crypto_dict[coin.currency.value]["value"] - coin.cost_price.value
                )
        return crypto_dict

    def sum_local_currency(self) -> dict:
        portfolio_value = {Currency.NOK: 0.0}
        crypto_dict = self._get_crypto_dict()

        for coin in crypto_dict:
            portfolio_value[coin] = crypto_dict[coin]
            portfolio_value[Currency.NOK] += crypto_dict[coin]["value"]

        return portfolio_value

    def calculate_roi_for_whole_portfolio(self) -> float:
        total_roi = sum(coin_data["roi"] for coin_data in self._get_crypto_dict().values())
        return total_roi

    @staticmethod
    def _filter_transaction_history(transaction_dict):
        filtered_transaction_dict = {}

        for currency in transaction_dict:
            if currency not in [
                Currency.USD,
                Currency.LINK,
                Currency.XRP,
            ]:
                filtered_transaction_dict[currency] = {}
                if currency == Currency.NOK and TransactionType.MATCH_FEE in transaction_dict[currency]:
                    filtered_transaction_dict[currency][TransactionType.MATCH_FEE] = transaction_dict[currency][
                        TransactionType.MATCH_FEE]
                else:
                    for transaction_type in transaction_dict[currency]:
                        if transaction_type not in [
                            TransactionType.INTERNAL_TRANSFER,
                            TransactionType.DEPOSIT_FEE,
                            TransactionType.VIPPS_DEPOSIT,
                            TransactionType.BANK_DEPOSIT,
                            TransactionType.STAKE,
                        ]:
                            filtered_transaction_dict[currency][transaction_type] = (
                                transaction_dict[currency][transaction_type]
                            )

        return filtered_transaction_dict

    @staticmethod
    def _add_match_fee_to_cost_price(transactions):
        match_fees = {
            fee['date']: convert_currency_value_to_default_currency(
                value=fee['amount'],
                from_currency=Currency.NOK,
                to_currency=Currency.USD
            )
            for fee in transactions.pop(Currency.NOK, {}).get(TransactionType.MATCH_FEE, [])
        }

        updated_transactions = {}

        for currency, currency_transactions in transactions.items():
            updated_transactions[currency] = {}

            for transaction_type, txn_list in currency_transactions.items():
                if transaction_type == TransactionType.MATCH:
                    for txn in txn_list:
                        match_fee_amount = match_fees.get(txn['date'], 0)
                        txn['cost_price'] -= abs(match_fee_amount)
                updated_transactions[currency][transaction_type] = txn_list

        return updated_transactions

    @staticmethod
    def sum_transaction_history(transaction_history):
        summed_transaction_history = {}

        for currency in transaction_history:
            summed_transaction_history[currency] = {"total_amount": 0.0, "total_cost_price": 0.0}
            for transaction_type in transaction_history[currency]:
                sum_transaction_type = sum(
                    [transaction["amount"] for transaction in transaction_history[currency][transaction_type]]
                )
                sum_cost_price = sum(
                    [transaction["cost_price"] for transaction in transaction_history[currency][transaction_type]]
                )
                summed_transaction_history[currency]["total_amount"] += sum_transaction_type
                summed_transaction_history[currency]["total_cost_price"] += sum_cost_price
                summed_transaction_history[currency][transaction_type] = sum_transaction_type

        return summed_transaction_history

    @classmethod
    def synchronize_with_firi(cls) -> "CryptoPortfolio":
        crypto_portfolio = cls(coins=[])
        grouped_transaction_history = get_grouped_transaction_history_by_year(years=[2023, 2024])
        filtered_transaction_history = cls._filter_transaction_history(grouped_transaction_history)
        transformed_transaction_history = cls._add_match_fee_to_cost_price(filtered_transaction_history)
        return crypto_portfolio._parse_summed_transaction_history(
            cls.sum_transaction_history(transformed_transaction_history)
        )
