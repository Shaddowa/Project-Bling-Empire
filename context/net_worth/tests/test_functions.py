import unittest
from datetime import datetime

from context.net_worth.main.data_classes.liabilities.expense import UpcomingExpense
from context.net_worth.main.data_classes.assetsManager import TotalAssets
from context.net_worth.main.data_classes.liabilitiesManager import TotalDebts
from context.net_worth.main.data_classes.assets.cash_flow import UpcomingCashFlowIn
from context.net_worth.main.functions import calculate_net_worth, calculate_gross_liquid_net_worth, \
    calculate_future_gross_liquid_net_worth, calculate_future_net_worth

# (TODO) Fix tests
# class test_functions(unittest.TestCase):
#
#     def __init__(self, *args, **kwargs):
#         super(test_functions, self).__init__(*args, **kwargs)
#         self.TotalAssets = TotalAssets(
#             cash=100,
#             funds=100,
#             stocks=100,
#             crypto=100,
#             real_estate=0
#         )
#
#         self.TotalDebts = TotalDebts(
#             mortgage=-100,
#             student_loan=-100
#         )
#
#         self.UpcomingExpenses = [
#             UpcomingExpense(
#                 expense="Apartment",
#                 amount=-1000,
#                 date=datetime(year=2024, month=7, day=1)
#             )
#         ]
#
#         self.UpcomingCashFlowIn = [
#             UpcomingCashFlowIn(
#                 cash_flow="Salary",
#                 amount=10000,
#                 date=datetime(year=2024, month=5, day=15)
#             ),
#             UpcomingCashFlowIn(
#                 cash_flow="Salary",
#                 amount=10000,
#                 date=datetime(year=2024, month=6, day=15)
#             ),
#             UpcomingCashFlowIn(
#                 cash_flow="Salary",
#                 amount=10000,
#                 date=datetime(year=2024, month=7, day=15)
#             ),
#             UpcomingCashFlowIn(
#                 cash_flow="Holiday Pay",
#                 amount=5000,
#                 date=datetime(year=2024, month=6, day=15)
#             )
#         ]
#
#     def test_calculate_net_worth(self):
#         self.assertEqual(calculate_net_worth(total_assets=self.TotalAssets, total_debts=self.TotalDebts), 200)
#
#         self.assertEqual(
#             calculate_future_net_worth(
#                 total_assets=self.TotalAssets,
#                 total_debts=self.TotalDebts,
#                 upcoming_cash_flow_in=self.UpcomingCashFlowIn,
#                 upcoming_expenses=self.UpcomingExpenses
#             ),
#             24200)
#
#         self.assertEqual(
#             calculate_future_net_worth(
#                 total_assets=self.TotalAssets,
#                 total_debts=self.TotalDebts,
#                 upcoming_cash_flow_in=self.UpcomingCashFlowIn,
#                 upcoming_expenses=self.UpcomingExpenses,
#                 date_threshold=datetime(year=2024, month=8, day=2)
#             ),
#             34200)
#
#     def test_calculate_gross_liquid_net_worth(self):
#         self.TotalAssets = TotalAssets(
#             cash=100,
#             funds=100,
#             stocks=100,
#             crypto=100,
#             real_estate=100
#         )
#         self.assertEqual(calculate_gross_liquid_net_worth(
#             total_assets=self.TotalAssets
#         ), 400)
#
#         self.assertEqual(
#             calculate_future_gross_liquid_net_worth(
#                 total_assets=self.TotalAssets,
#                 upcoming_cash_flow_in=self.UpcomingCashFlowIn,
#                 upcoming_expenses=self.UpcomingExpenses
#             ),
#             24400
#         )
#
#         self.assertEqual(
#             calculate_future_gross_liquid_net_worth(
#                 total_assets=self.TotalAssets,
#                 upcoming_cash_flow_in=self.UpcomingCashFlowIn,
#                 upcoming_expenses=self.UpcomingExpenses,
#                 date_threshold=datetime(year=2024, month=8, day=2)
#             ),
#             34400
#         )
