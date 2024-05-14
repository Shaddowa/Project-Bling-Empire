from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .currency import CurrencyValue


@dataclass
class StockPurchase:
    stock_collection: str
    ticker: str
    quantity: float
    price: CurrencyValue
    brokerage: CurrencyValue
    date: datetime
    exchange_rate: Optional[CurrencyValue] = None


@dataclass
class StockPortfolio:
    stocks: list[
        StockPurchase
    ]


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

