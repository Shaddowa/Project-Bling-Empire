from dataclasses import dataclass

from .liabilities.expense import Basis, ReoccurringExpense
from .liabilities.mortgage import Mortgage
from .liabilities.mortgage_loan_payment_plan import get_mortgage_loan
from .liabilities.reoccurring_expenses import get_monthly_reoccurring_expenses, get_extra_monthly_payments
from .liabilities.student_loan import StudentLoan
from .liabilities.student_loan_payment_plan import get_student_loan
from .liabilities.upcoming_expenses import get_upcoming_expenses
from ..const import FROM_DATE, TO_DATE


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

    @staticmethod
    def process_extra_expenses(expenses: list[ReoccurringExpense]):
        return sum([expense.amount for expense in expenses])

    def get_monthly_debt_expenses(self):
        # I have postponed payment of student loan to pay off mortgage loan
        # student_loan = self.student_loan.sum_monthly_student_loan_payment()
        mortgage_loan = self.mortgage.sum_monthly_mortgage_loan_payment()
        extra_payments = self.process_extra_expenses(get_extra_monthly_payments())

        return [{
            "extra_payments": extra_payments,
            "mortgage_loan": mortgage_loan,
            "student_loan": 0,
        }]


@dataclass
class LiabilitiesManager:
    total_debts: TotalDebts = TotalDebts()
    reoccurring_expenses = get_monthly_reoccurring_expenses()
    upcoming_expenses = get_upcoming_expenses()

    def sum_total_debts(self):
        return self.total_debts.get_total_debts()

    def get_monthly_reoccurring_expenses(self):
        return [{expense.expense: expense.amount} for expense in self.reoccurring_expenses if
                expense.basis == Basis.monthly]

    def sum_monthly_debt_expenses(self):
        return self.total_debts.get_monthly_debt_expenses()

    def sum_upcoming_expenses_within_monthly_interval(self, date_threshold=TO_DATE):
        return sum([expense.amount for expense in self.upcoming_expenses if FROM_DATE <= expense.date < date_threshold])

    def get_monthly_liabilities(self):
        monthly_debt_expenses = self.total_debts.get_monthly_debt_expenses()
        monthly_reoccurring_expenses = self.get_monthly_reoccurring_expenses()
        return monthly_debt_expenses + monthly_reoccurring_expenses
