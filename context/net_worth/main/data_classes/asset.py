from dataclasses import dataclass
from datetime import datetime


@dataclass
class StockPurchase:
    stock_collection: str
    ticker: str
    quantity: int
    price: float
    date: datetime


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

