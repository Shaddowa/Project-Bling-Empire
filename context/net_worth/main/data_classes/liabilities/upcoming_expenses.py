from datetime import datetime

from ..liabilities.expense import UpcomingExpense
from ...gocardless_requests import get_credit_card_used_balance_and_due_date


def get_upcoming_expenses():
    # sum_used_credit, due_date = get_credit_card_used_balance_and_due_date()
    sum_used_credit, due_date = 0, "2024-07-20"

    expenses = [
        UpcomingExpense(
            expense="Sats PT & Membership",
            amount=3196.30,
            date=datetime(year=2024, month=7, day=20)
        ),
        UpcomingExpense(
            expense="Credit Card",
            amount=400,
            date=datetime(year=2024, month=8, day=12)
        ),
        UpcomingExpense(
            expense="Insurance",
            amount=1001,
            date=datetime(year=2024, month=8, day=20)
        ),
        UpcomingExpense(
            expense="Insurance",
            amount=5414,
            date=datetime(year=2024, month=8, day=11)
        )
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
