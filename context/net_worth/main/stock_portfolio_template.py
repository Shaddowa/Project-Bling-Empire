from datetime import datetime

from .data_classes.asset import TotalAssets, StockPortfolio, StockPurchase
from .data_classes.currency import CurrencyValue, Currency
from ...ticker_scraper.main.stock_collections import NORWAY, STANDARD_AND_POOR_500

stockPortfolio_example = StockPortfolio(
    stocks=[
        StockPurchase(
            stock_collection=STANDARD_AND_POOR_500,
            ticker="MSFT",
            quantity=1400,
            price=CurrencyValue(
                value=0,
                currency=Currency.USD
            ),
            exchange_rate=CurrencyValue(
                value=0,
                currency=Currency.NOK
            ),
            brokerage=CurrencyValue(
                value=0,
                currency=Currency.NOK
            ),
            cost_price=CurrencyValue(0, Currency.NOK),
            date=None
        ),
        StockPurchase(
            stock_collection=STANDARD_AND_POOR_500,
            ticker="NVDA",
            quantity=4210,
            price=CurrencyValue(
                value=62.53,
                currency=Currency.USD
            ),
            exchange_rate=CurrencyValue(
                value=8.85,
                currency=Currency.NOK
            ),
            brokerage=CurrencyValue(
                value=61.95,
                currency=Currency.NOK
            ),
            cost_price=CurrencyValue(16123664.04, Currency.NOK),
            date=datetime(year=2020, month=11, day=27)
        ),
        StockPurchase(
            stock_collection=NORWAY,
            ticker="KIT",
            quantity=210,
            price=CurrencyValue(
                value=10.98,
                currency=Currency.NOK
            ),
            brokerage=CurrencyValue(
                value=13.73,
                currency=Currency.NOK
            ),
            date=datetime(year=2020, month=12, day=28)
        ),
    ],
)
