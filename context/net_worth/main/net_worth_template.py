
import locale
from datetime import datetime

from context.net_worth.main.gocardless_requests import get_bank_account_total_balance_from_dnb, \
    get_credit_card_used_balance_and_due_date
from data_classes.expense import UpcomingExpense
from data_classes.asset import TotalAssets
from data_classes.debt import TotalDebts
from data_classes.cash_flow import UpcomingCashFlowIn

locale.setlocale(locale.LC_ALL, 'no_NO')


def format_currency(value: float) -> str:
    return locale.currency(value, grouping=True)


def get_not_listed_account_sum_balance():
    saving_account_stocks_ASK = 0
    bsu = 0
    swing_trading_ASK = 0
    return saving_account_stocks_ASK + bsu + swing_trading_ASK


TotalAssets = TotalAssets(
    cash=get_bank_account_total_balance_from_dnb() + get_not_listed_account_sum_balance(),
    stocks=0,
    funds=0,
    crypto=0,
    real_estate=0
)

TotalDebts = TotalDebts(
    mortgage_loan=-0,
    student_loan=-0
)

sum_used_credit, due_date = get_credit_card_used_balance_and_due_date()
UpcomingExpenses = [
    UpcomingExpense(
        expense="Apartment",
        amount=-0,
        date=datetime(year=2024, month=7, day=1)
    )
]

if sum_used_credit < 0:
    due_date_datetime = datetime.strptime(due_date, "%Y-%m-%d")
    UpcomingExpenses.append(UpcomingExpense(
        expense="CreditCard",
        amount=sum_used_credit,
        date=due_date_datetime
    ))

UpcomingCashFlowIn = [
    UpcomingCashFlowIn(
        cash_flow="Salary",
        amount=0,
        date=datetime(year=2024, month=5, day=15)
    ),
    UpcomingCashFlowIn(
        cash_flow="Holiday Pay",
        amount=0,
        date=datetime(year=2024, month=6, day=15)
    )
]
