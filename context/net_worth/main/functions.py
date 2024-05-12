from datetime import datetime

from context.net_worth.main.data_classes.expense import UpcomingExpense
from context.net_worth.main.data_classes.asset import TotalAssets
from context.net_worth.main.data_classes.debt import TotalDebts
from context.net_worth.main.data_classes.cash_flow import UpcomingCashFlowIn


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

    total_debts = sum([total_debts.mortgage_loan, total_debts.student_loan])

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

    total_debts = sum([total_debts.mortgage_loan, total_debts.student_loan])

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
