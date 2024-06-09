from dataclasses import dataclass
from enum import Enum


class Currency(Enum):
    NOK = "NOK"
    USD = "USD"
    BTC = "BTC"
    ADA = "ADA"
    ETH = "ETH"
    SOL = "SOL"
    LINK = "LINK"
    XRP = "XRP"

    @classmethod
    def from_str(cls, currency_str):
        try:
            return cls(currency_str)
        except ValueError:
            print(f"Could not convert {currency_str} to Currency")
            return None


@dataclass
class CurrencyValue:
    value: float
    currency: Currency

    def __repr__(self):
        return f"{self.value:.2f} {self.currency.value}"
