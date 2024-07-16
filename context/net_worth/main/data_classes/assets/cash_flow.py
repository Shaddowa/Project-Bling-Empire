from dataclasses import dataclass
from datetime import datetime

from context.net_worth.main.data_classes.basis import Basis


@dataclass
class ReoccurringCashFlow:
    cash_flow: str
    amount: float
    basis: Basis


@dataclass
class UpcomingCashFlow:
    cash_flow: str
    amount: float
    date: datetime
