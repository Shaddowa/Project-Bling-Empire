from dataclasses import dataclass
from ..liabilities.expense import UpcomingExpense
from ...const import NOW


@dataclass
class Mortgage:

    def __init__(self, mortgage: list[UpcomingExpense]):
        self.mortgage = mortgage

    def _sum_future_amounts(self, attribute: str):
        return sum(getattr(expense, attribute) for expense in self.mortgage if expense.date >= NOW)

    def _sum_historic_amounts(self, attribute: str):
        return sum(getattr(expense, attribute) for expense in self.mortgage)

    def sum_total_mortgage_loan(self):
        return self._sum_historic_amounts('term_payment')

    def sum_total_remaining_mortgage_loan(self):
        return self._sum_future_amounts('term_payment')

    def sum_total_remaining_interest(self):
        return self._sum_future_amounts('interest')

    def sum_total_remaining_principal(self):
        return self._sum_future_amounts('principal')

    def sum_loan_balance(self):
        future_expenses = [expense.loan_balance for expense in self.mortgage if expense.date >= NOW]
        return future_expenses[-1] if future_expenses else 0.0


