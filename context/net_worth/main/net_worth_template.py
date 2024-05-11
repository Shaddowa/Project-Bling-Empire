
import locale
from datetime import datetime
from data_classes.expense import UpcomingExpense
from data_classes.asset import TotalAssets
from data_classes.debt import TotalDebts
from data_classes.cash_flow import UpcomingCashFlowIn
from functions import (
    calculate_net_worth,
    calculate_future_net_worth,
    calculate_gross_liquid_net_worth,
    calculate_future_gross_liquid_net_worth
)

locale.setlocale(locale.LC_ALL, 'no_NO')


TotalAssets = TotalAssets(
    cash=0,
    stocks=0,
    funds=0,
    crypto=0,
    real_estate=0
)

TotalDebts = TotalDebts(
    mortgage_loan=0,
    student_loan=0
)

UpcomingExpenses = [
    UpcomingExpense(
        expense="Apartment",
        amount=0,
        date=datetime(year=2024, month=7, day=1)
    )
]

UpcomingCashFlowIn = [
    UpcomingCashFlowIn(
        cash_flow="Salary",
        amount=0,
        date=datetime(year=2024, month=5, day=15)
    ),
    UpcomingCashFlowIn(
        cash_flow="Holiday Pay",
        amount=34500,
        date=datetime(year=2024, month=6, day=15)
    )
]

print(f"Net Worth: {calculate_net_worth(TotalAssets, TotalDebts)}")
print(f"Future Net Worth: {calculate_future_net_worth(TotalAssets, TotalDebts, UpcomingCashFlowIn, UpcomingExpenses)}")
print(f"Gross Liquid Net Worth: {calculate_gross_liquid_net_worth(TotalAssets)}")
print(f"Gross Liquid Future Net Worth: {calculate_future_gross_liquid_net_worth(TotalAssets, UpcomingCashFlowIn, UpcomingExpenses)}")
print(f"Total Assets: {locale.currency(TotalAssets.sum(), grouping=True)}")
print(f"Total Debts: {locale.currency(TotalDebts.sum(), grouping=True)}")


