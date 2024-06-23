from datetime import datetime, timedelta
from typing import Optional
import requests
from context.net_worth.main.data_classes.currency import Currency

BASE_URL = "https://data.norges-bank.no/api/data/EXR/"
DEFAULT_TIME_DELTA = 60

"""
Example URL: ${BASE_URL}M.USD.NOK.SP?format=sdmx-json&startPeriod=2014-06-23&endPeriod=2024-06-23&locale=en
This URL retrieves data for the M USD NOK SP exchange rate, which represents the spot exchange rate between 
the US dollar (USD) and the Norwegian krone (NOK) on a monthly basis. 
The data is provided in SDMX-JSON format and covers the period from June 23, 2014, to June 23, 2024.
"""


def _get_full_url(from_currency: str, to_currency: str, start_period: str, end_period: str):
    return (
        f"{BASE_URL}M.{from_currency}.{to_currency}.SP?"
        f"format=sdmx-json&startPeriod={start_period}"
        f"&endPeriod={end_period}&locale=en"
    )


def _calculate_average_rate(observations) -> float:
    rates = [float(ob[0]) for ob in observations.values()]
    return sum(rates) / len(rates)


def convert_currency_value_to_default_currency(
        value: float,
        from_currency: Currency,
        to_currency=Currency.NOK,
        start_period: Optional[datetime] = None,
        end_period: datetime = datetime.now()
) -> float:
    if from_currency != to_currency:
        invert_rate = False
        if start_period is None:
            start_period = end_period - timedelta(days=DEFAULT_TIME_DELTA)

        if from_currency == Currency.NOK:
            invert_rate = True
            from_currency, to_currency = to_currency, from_currency

        response = requests.get(_get_full_url(
            from_currency=from_currency.value,
            to_currency=to_currency.value,
            start_period=start_period.strftime("%Y-%m-%d"),
            end_period=end_period.strftime("%Y-%m-%d")
        ))

        average_rate = _calculate_average_rate(
            observations=response.json()['data']['dataSets'][0]['series']['0:0:0:0']['observations']
        )

        return value * average_rate if not invert_rate else value / average_rate
    return value

