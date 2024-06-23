from dataclasses import dataclass

from .liabilities.mortgage_loan_payment_plan import get_mortgage_loan
from .liabilities.student_loan_payment_plan import get_student_loan
from .liabilities.student_loan import StudentLoan
from .liabilities.mortgage import Mortgage


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
    mortgage: Mortgage = Mortgage(mortgage=get_mortgage_loan())
    student_loan: StudentLoan = StudentLoan(student_loan=get_student_loan())

    def get_total_debts(self):
        return sum([self.get_student_loan(), self.get_mortgage()])

    def get_student_loan(self):
        return self.student_loan.sum_total_remaining_student_loan()

    def get_mortgage(self):
        return self.mortgage.sum_total_remaining_mortgage_loan()
