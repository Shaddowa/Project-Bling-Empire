from ..liabilities.expense import DebtExpense
from ...const import NOW, FROM_DATE, TO_DATE, TO_DATE


class StudentLoan:

    def __init__(self, student_loan: list[DebtExpense]):
        self.student_loan = student_loan

    def sum_monthly_student_loan_payment(self):
        return sum([expense.term_payment for expense in self.student_loan if FROM_DATE <= expense.date < TO_DATE])

    def _sum_future_amounts(self, attribute: str):
        return sum(getattr(expense, attribute) for expense in self.student_loan if expense.date >= NOW)

    def _sum_historic_amounts(self, attribute: str):
        return sum(getattr(expense, attribute) for expense in self.student_loan)

    def sum_total_student_loan(self):
        return self._sum_historic_amounts('term_payment')

    def sum_total_remaining_student_loan(self):
        return self._sum_future_amounts('term_payment')

    def sum_total_remaining_interest(self):
        return self._sum_future_amounts('interest')

    def sum_total_remaining_principal(self):
        return self._sum_future_amounts('principal')

    def sum_interest_remaining_balance(self):
        return self._sum_future_amounts('interest_balance')

    def sum_loan_balance(self):
        future_expenses = [expense.loan_balance for expense in self.student_loan if expense.date >= NOW]
        return future_expenses[-1] if future_expenses else 0.0

