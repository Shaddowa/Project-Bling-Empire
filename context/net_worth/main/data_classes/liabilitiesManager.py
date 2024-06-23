from dataclasses import dataclass

from liabilities.student_loan import StudentLoan
from liabilities.mortgage import Mortgage


# sum_used_credit, due_date = get_credit_card_used_balance_and_due_date()

# UpcomingExpenses = [
#     UpcomingExpense(
#         expense="Apartment",
#         amount=-712640,
#         date=datetime(year=2024, month=7, day=1)
#     )
# ]

# if sum_used_credit < 0:
#     due_date_datetime = datetime.strptime(due_date, "%Y-%m-%d")
#     UpcomingExpenses.append(UpcomingExpense(
#         expense="CreditCard",
#         amount=sum_used_credit,
#         date=due_date_datetime
#     ))


@dataclass
class TotalDebts:
    mortgage: Mortgage
    student_loan: StudentLoan
