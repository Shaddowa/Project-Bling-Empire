from datetime import datetime

from ..liabilities.expense import UpcomingExpense
from ...gocardless_requests import get_credit_card_used_balance_and_due_date


def get_upcoming_expenses():
    # sum_used_credit, due_date = get_credit_card_used_balance_and_due_date()
    sum_used_credit, due_date = 0, "2024-07-20"

    expenses = [

        UpcomingExpense(
            expense="Credit Card",
            amount=11202,
            date=datetime(year=2024, month=11, day=15)
        ),
        UpcomingExpense(
            expense="Insurance",
            amount=442,
            date=datetime(year=2024, month=11, day=17)
        ),
        UpcomingExpense(
            expense="Electricity",
            amount=345.94,
            date=datetime(year=2024, month=11, day=18)
        ),
        UpcomingExpense(
            expense="Carpenter",
            amount=5000,
            date=datetime(year=2024, month=11, day=18)
        ),
        UpcomingExpense(
            expense="SALE",
            amount=20000,
            date=datetime(year=2024, month=11, day=29)
        ),
    ]

    if sum_used_credit < 0:
        due_date_datetime = datetime.strptime(due_date, "%Y-%m-%d")
        expenses.append(
            UpcomingExpense(
                expense="CreditCard",
                amount=sum_used_credit,
                date=due_date_datetime
            )
        )

    return expenses
