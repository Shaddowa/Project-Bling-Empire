from datetime import datetime

from .data_classes.liabilities.expense import UpcomingExpense
from .data_classes.assetsManager import TotalAssets
from .data_classes.liabilitiesManager import TotalDebts
from .data_classes.assets.cash_flow import UpcomingCashFlowIn


def calculate_net_worth(total_assets: TotalAssets = TotalAssets, total_debts: TotalDebts = TotalDebts) -> int:
    total_assets = sum(
        [
            total_assets.cash,
            total_assets.stocks,
            total_assets.funds,
            total_assets.crypto,
            total_assets.real_estate
        ]
    )

    total_debts = sum([total_debts.mortgage, total_debts.student_loan.sum_total_student_loan()])

    return sum([total_assets, total_debts])


def calculate_future_net_worth(
        total_assets: TotalAssets = TotalAssets,
        total_debts: TotalDebts = TotalDebts,
        upcoming_cash_flow_in: list[UpcomingCashFlowIn] = None,
        upcoming_expenses: list[UpcomingExpense] = None,
        date_threshold=datetime(year=2024, month=7, day=2)
) -> int:
    total_assets = sum(
        [
            total_assets.cash,
            total_assets.stocks,
            total_assets.funds,
            total_assets.crypto,
            total_assets.real_estate
        ]
    )

    total_debts = sum([total_debts.mortgage, total_debts.student_loan])

    total_upcoming_cash_flow_in = sum(
        [cash_flow_in.amount for cash_flow_in in upcoming_cash_flow_in if cash_flow_in.date <= date_threshold]
    )

    total_upcoming_expenses = sum(
        [expense.amount for expense in upcoming_expenses if expense.date <= date_threshold]
    )

    return sum([total_assets, total_upcoming_cash_flow_in, total_debts, total_upcoming_expenses])


def calculate_gross_liquid_net_worth(total_assets: TotalAssets = TotalAssets) -> int:
    total_assets = sum(
        [
            total_assets.cash,
            total_assets.stocks,
            total_assets.funds,
            total_assets.crypto,
        ]
    )

    return total_assets


def calculate_future_gross_liquid_net_worth(
        total_assets: TotalAssets = TotalAssets,
        upcoming_cash_flow_in: list[UpcomingCashFlowIn] = None,
        upcoming_expenses: list[UpcomingExpense] = None,
        date_threshold=datetime(year=2024, month=7, day=2)
) -> int:
    total_assets = sum(
        [
            total_assets.cash,
            total_assets.stocks,
            total_assets.funds,
            total_assets.crypto
        ]
    )

    total_upcoming_cash_flow_in = sum(
        [cash_flow_in.amount for cash_flow_in in upcoming_cash_flow_in if cash_flow_in.date <= date_threshold]
    )

    total_upcoming_expenses = sum(
        [expense.amount for expense in upcoming_expenses if expense.date <= date_threshold]
    )

    return sum([total_assets, total_upcoming_cash_flow_in, total_upcoming_expenses])
