from dataclasses import dataclass

from .assets.reoccurring_cash_flow import get_monthly_reoccurring_cash_flow
from .assets.upcoming_cash_flow import get_upcoming_cash_flow
from .liabilities.expense import Basis
from ..const import FROM_DATE, TO_DATE


@dataclass
class TotalInvestments:
    stocks: float  # TODO replace when ready
    funds: float  # TODO replace when ready
    crypto: float  # TODO replace when ready
    real_estate: float  # TODO replace when ready

    def sum_all(self) -> float:
        return sum(
            [
                self.stocks,
                self.funds,
                self.crypto,
                self.real_estate
            ]
        )

    def sum_liquid(self) -> float:
        return sum(
            [
                self.stocks,
                self.funds,
                self.crypto,
            ]
        )


@dataclass
class AssetsManager:
    total_investments: TotalInvestments = TotalInvestments(0, 0, 0, 0)  # TODO change when ready
    reoccurring_cash_flow = get_monthly_reoccurring_cash_flow()
    upcoming_cash_flow = get_upcoming_cash_flow()

    def get_monthly_reoccurring_cash_flow(self):
        return [{cash_flow.cash_flow: cash_flow.amount} for cash_flow in self.reoccurring_cash_flow if
                cash_flow.basis == Basis.monthly]

    def get_upcoming_cash_flow_within_monthly_interval(self, date_threshold=TO_DATE):
        return [{cash_flow.cash_flow: cash_flow.amount} for cash_flow in self.upcoming_cash_flow if
                FROM_DATE <= cash_flow.date < date_threshold]

    def sum_investments(self):
        return self.total_investments.sum_all()

    def sum_liquid_investments(self):
        return self.total_investments.sum_liquid()

    def get_total_monthly_cashflow(self):
        monthly_reoccurring_cash_flow = self.get_monthly_reoccurring_cash_flow()
        upcoming_cash_flow = self.get_upcoming_cash_flow_within_monthly_interval()
        return monthly_reoccurring_cash_flow + upcoming_cash_flow

