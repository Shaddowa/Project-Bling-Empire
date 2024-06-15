from datetime import datetime, timedelta
from typing import Optional
import numpy as np
import pytz
import yfinance as yf
import requests
import os
from dotenv import load_dotenv
from context.net_worth.main.data_classes.currency import Currency
from context.net_worth.main.data_classes.transaction_type import TransactionType

load_dotenv()


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
