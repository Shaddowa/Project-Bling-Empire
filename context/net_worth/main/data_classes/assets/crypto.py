import os
import yfinance as yf
from dataclasses import dataclass
from datetime import datetime
from ..currency import CurrencyValue, Currency
from ..transaction_type import TransactionType
from ...curreny_requests import convert_currency_value_to_default_currency
from ...firi_requests import get_grouped_transaction_history_by_year


@dataclass
class CryptoCoin:
    currency: Currency
    quantity: float
    cost_price: CurrencyValue


@dataclass
class CryptoPortfolio:

    def __init__(self):
        self.coins: list[
            CryptoCoin
        ] = []
        self.cash: CurrencyValue = CurrencyValue(0.0, Currency.NOK)

    def _set_cash_balance(self, grouped_transaction_history: dict):
        nok_match_transactions = grouped_transaction_history.get(Currency.NOK, {}).get(TransactionType.MATCH, [])
        total_amount_2025 = sum(
            transaction['amount']
            for transaction in nok_match_transactions
            if transaction['date'].startswith('2025')
        )
        self.cash = CurrencyValue(
            value=total_amount_2025,
            currency=Currency.NOK
        )

    def _parse_summed_transaction_history(self, summed_transaction_history):
        for currency in summed_transaction_history:
            self.coins.append(
                CryptoCoin(
                    currency=currency,
                    quantity=summed_transaction_history[currency]["total_amount"],
                    cost_price=CurrencyValue(
                        value=summed_transaction_history[currency]["total_converted_cost_price"],
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
        portfolio_value = {Currency.NOK.value: self.cash.value}
        crypto_dict = self._get_crypto_dict()

        for coin in crypto_dict:
            portfolio_value[coin] = crypto_dict[coin]
            portfolio_value[Currency.NOK.value] += crypto_dict[coin]["value"]

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
                Currency.BTC,
                Currency.ETH,
                Currency.SOL
            ]:
                filtered_transaction_dict[currency] = {}
                if currency == Currency.NOK and TransactionType.MATCH_FEE in transaction_dict[currency]:
                    filtered_transaction_dict[currency][TransactionType.MATCH_FEE] = transaction_dict[currency][TransactionType.MATCH_FEE]
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
                to_currency=Currency.USD,
                end_period=datetime.strptime(fee['date'], "%Y-%m-%dT%H:%M:%S.%fZ")
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
            summed_transaction_history[currency] = {
                "total_amount": 0.0,
                "total_cost_price": 0.0,
                "total_converted_cost_price": 0.0
            }

            for transaction_type in transaction_history[currency]:
                total_amount = 0.0
                total_cost_price = 0.0
                total_converted_cost_price = 0.0

                for transaction in transaction_history[currency][transaction_type]:
                    amount = transaction["amount"]
                    cost_price = transaction["cost_price"]
                    transaction_date = datetime.strptime(transaction["date"], "%Y-%m-%dT%H:%M:%S.%fZ")

                    converted_cost_price = convert_currency_value_to_default_currency(
                        cost_price,
                        from_currency=Currency.USD,
                        to_currency=Currency.NOK,
                        end_period=transaction_date
                    )

                    total_amount += amount
                    total_cost_price += cost_price
                    total_converted_cost_price += converted_cost_price

                summed_transaction_history[currency]["total_amount"] += total_amount
                summed_transaction_history[currency]["total_cost_price"] += total_cost_price
                summed_transaction_history[currency]["total_converted_cost_price"] += total_converted_cost_price
                summed_transaction_history[currency][transaction_type] = total_amount

        return summed_transaction_history

    def synchronize_with_firi(self) -> "CryptoPortfolio":
        grouped_transaction_history = get_grouped_transaction_history_by_year(years=[2023, 2024, 2025])
        self._set_cash_balance(grouped_transaction_history)
        filtered_transaction_history = self._filter_transaction_history(grouped_transaction_history)
        transformed_transaction_history = self._add_match_fee_to_cost_price(filtered_transaction_history)
        summed_transaction_history = self.sum_transaction_history(transformed_transaction_history)
        return self._parse_summed_transaction_history(summed_transaction_history)

