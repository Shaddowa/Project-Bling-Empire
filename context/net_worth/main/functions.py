import locale

from .const import TO_DATE
from .data_classes.liabilitiesManager import LiabilitiesManager
from .data_classes.assetsManager import AssetsManager
from .data_classes.cashManager import CashManager

LIABILITIES_MANAGER = LiabilitiesManager()
ASSETS_MANAGER = AssetsManager()
CASH_MANAGER = CashManager()

locale.setlocale(locale.LC_ALL, 'no_NO')


def format_currency(value: float) -> str:
    return locale.currency(value, grouping=True)


def calculate_net_worth() -> int:
    INVESTMENTS = ASSETS_MANAGER.sum_investments()
    CASH_RESERVE = CASH_MANAGER.get_total_cash_reserve()
    DEBTS = LIABILITIES_MANAGER.sum_total_debts()

    return INVESTMENTS + CASH_RESERVE - DEBTS


def calculate_expenses_after_cash_flow(date_threshold=TO_DATE) -> int:
    CASH_FLOW = ASSETS_MANAGER.sum_upcoming_cash_flow_within_monthly_interval(date_threshold)
    EXPENSES = LIABILITIES_MANAGER.sum_upcoming_expenses_within_monthly_interval(date_threshold)

    return CASH_FLOW - EXPENSES


def calculate_future_net_worth(date_threshold=TO_DATE) -> int:
    CURRENT_NET_WORTH = calculate_net_worth()

    return CURRENT_NET_WORTH + calculate_expenses_after_cash_flow(date_threshold)


def calculate_gross_liquid_net_worth() -> int:
    LIQUID_INVESTMENTS = ASSETS_MANAGER.sum_liquid_investments()
    CASH_RESERVE = CASH_MANAGER.get_total_cash_reserve()

    return sum([LIQUID_INVESTMENTS, CASH_RESERVE])


def calculate_future_gross_liquid_net_worth(date_threshold=TO_DATE) -> int:
    return sum([calculate_gross_liquid_net_worth(), calculate_expenses_after_cash_flow(date_threshold)])
