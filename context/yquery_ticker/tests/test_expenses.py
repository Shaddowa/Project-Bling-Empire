import unittest

from context.yquery_ticker.main.data_classes.expenses import Expenses
from context.yquery_ticker.main.enums.expenses import ExpensesFields


class test_expenses(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(test_expenses, self).__init__(*args, **kwargs)

    def test_sum_expenses(self):
        assert Expenses(
            capital_expenditure=1,
            interest_expense=0,
            interest_expense_non_operating=0,
            total_other_finance_cost=0
        ).sum() == 1
        assert Expenses(
            capital_expenditure=1,
            interest_expense=-2,
            interest_expense_non_operating=0,
            total_other_finance_cost=0
        ).sum() == -1
        assert Expenses(
            capital_expenditure=1,
            interest_expense=1,
            interest_expense_non_operating=2,
            total_other_finance_cost=0
        ).sum(exclude=[ExpensesFields.INTEREST_EXPENSE_NON_OPERATING]) == 2
        assert Expenses(
            capital_expenditure=1,
            interest_expense=1,
            interest_expense_non_operating=3,
            total_other_finance_cost=2
        ).sum(exclude=[ExpensesFields.TOTAL_OTHER_FINANCE_COST]) == 5

    def test_sum_all_zeros(self):
        expenses = Expenses(0, 0, 0, 0)
        self.assertEqual(expenses.sum(), 0, "Test failed: Sum of all zeros should be zero")

    def test_sum_all_negative(self):
        expenses = Expenses(-1, -1, -1, -1)
        self.assertEqual(expenses.sum(), -4, "Test failed: Sum of all negatives should be -4")

    def test_sum_exclude_multiple_fields(self):
        expenses = Expenses(10, 20, 30, 40)
        excluded_fields = [ExpensesFields.CAPITAL_EXPENDITURE, ExpensesFields.TOTAL_OTHER_FINANCE_COST]
        expected_sum = 20 + 30  # Only interest_expense and interest_expense_non_operating
        self.assertEqual(expenses.sum(exclude=excluded_fields), expected_sum, "Test failed: Incorrect sum with multiple exclusions")

    def test_sum_large_numbers(self):
        expenses = Expenses(1e9, 1e9, 1e9, 1e9)
        self.assertEqual(expenses.sum(), 4e9, "Test failed: Sum of large numbers did not match expected")

    def test_sum_with_none_values(self):
        expenses = Expenses(10, None, 20, None)
        with self.assertRaises(TypeError):
            expenses.sum()
