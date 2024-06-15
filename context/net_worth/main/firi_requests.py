from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import numpy as np
import pytz
import yfinance as yf
import requests
import os
from dotenv import load_dotenv
from context.net_worth.main.data_classes.currency import Currency

load_dotenv()


# Duplicated, remove when refactoring is done
def convert_currency_value_to_default_currency(value: float, from_currency: Currency,
                                               to_currency=Currency.NOK) -> float:
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


class TransactionType(Enum):
    INTERNAL_TRANSFER = "InternalTransfer"
    MATCH = "Match"
    MATCH_FEE = "MatchFee"
    VIPPS_DEPOSIT = "VippsDeposit"
    DEPOSIT_FEE = "DepositFee"
    STAKING_REWARD = "StakingReward"
    BANK_DEPOSIT = "BankDeposit"
    STAKE = "Stake"
    BONUS = "Bonus"

    @classmethod
    def from_str(cls, transaction_type_str):
        try:
            return cls(transaction_type_str)
        except ValueError:
            print(f"Could not convert {transaction_type_str} to TransactionType")
            return None


FIRI_ACCESS_KEY = os.getenv('FIRI_ACCESS_KEY')

BASE_URL = "https://api.firi.com/v2/"


def _get_cost_price(date, amount, currency) -> Optional[float]:
    if currency not in [Currency.NOK, Currency.USD]:
        crypto_symbol = f"{currency.value}-USD"
        target_datetime = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
        firi_timezone = pytz.timezone("Europe/Oslo")
        target_datetime = firi_timezone.localize(target_datetime).astimezone(pytz.UTC)

        start_datetime = target_datetime - timedelta(hours=1)
        end_datetime = target_datetime + timedelta(hours=1)

        crypto_data = yf.download(crypto_symbol, start=start_datetime, end=end_datetime, interval="1h", progress=False)

        # Calculate the absolute differences and find the closest timestamp
        time_diffs = np.abs((crypto_data.index - target_datetime).total_seconds())
        closest_index = time_diffs.argmin()
        closest_price_data = crypto_data.iloc[closest_index]
        return abs(amount * closest_price_data["Close"])
    else:
        return None


def _group_response_by_currency(transaction_history):
    grouped_transactions = {}
    for year in transaction_history:
        for transaction in year:
            currency = Currency.from_str(transaction["currency"])
            amount = float(transaction["amount"])
            transaction_type = TransactionType.from_str(transaction["type"])
            date = transaction["date"]
            if currency not in grouped_transactions:
                grouped_transactions[currency] = {}

            if transaction_type not in grouped_transactions[currency]:
                grouped_transactions[currency][transaction_type] = [{
                    "amount": amount,
                    "date": date,
                    "cost_price": _get_cost_price(date, amount, currency),
                }]
            else:
                grouped_transactions[currency][transaction_type].append({
                    "amount": amount,
                    "date": date,
                    "cost_price": _get_cost_price(date, amount, currency)
                })
    return grouped_transactions


def get_filtered_transaction_history(transaction_dict):
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
                        filtered_transaction_dict[currency][transaction_type] = transaction_dict[currency][
                            transaction_type]

    return filtered_transaction_dict


def add_match_fee_to_cost_price(transactions):
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


def get_summed_transaction_history(transaction_history):
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


def get_grouped_transaction_history_by_year(years: list[int]):
    merged_responses = []
    for year in years:
        response = requests.get(f"{BASE_URL}history/transactions/{str(year)}/", headers={
            "firi-access-key": FIRI_ACCESS_KEY,
            "accept": "application/json"
        })

        if response.status_code == 200:
            merged_responses.append(response.json())
        else:
            return response.status_code, response.text

    return _group_response_by_currency(merged_responses)
