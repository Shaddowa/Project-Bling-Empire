from enum import Enum

import requests
import os
from dotenv import load_dotenv

from context.net_worth.main.data_classes.currency import Currency

load_dotenv()


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
                    "date": date
                }]
            else:
                grouped_transactions[currency][transaction_type].append({
                    "amount": amount,
                    "date": date
                })

    return grouped_transactions


def get_filtered_transaction_history(transaction_dict):

    filtered_transaction_dict = {}

    for currency in transaction_dict:
        if currency not in [
            Currency.NOK,
            Currency.LINK,
            Currency.XRP
        ]:
            filtered_transaction_dict[currency] = {}
            for transaction_type in transaction_dict[currency]:
                if transaction_type not in [
                    TransactionType.INTERNAL_TRANSFER,
                    TransactionType.MATCH_FEE,
                    TransactionType.DEPOSIT_FEE,
                    TransactionType.VIPPS_DEPOSIT,
                    TransactionType.BANK_DEPOSIT,
                    TransactionType.STAKE,
                ]:
                    filtered_transaction_dict[currency][transaction_type] = transaction_dict[currency][transaction_type]

    return filtered_transaction_dict


def get_summed_transaction_history(transaction_history):
    summed_transaction_history = {}

    for currency in transaction_history:
        summed_transaction_history[currency] = {"total_amount": 0.0}
        for transaction_type in transaction_history[currency]:
            sum_transaction_type = sum(
                [transaction["amount"] for transaction in transaction_history[currency][transaction_type]]
            )
            summed_transaction_history[currency]["total_amount"] += sum_transaction_type
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
