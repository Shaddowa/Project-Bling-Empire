from dataclasses import dataclass
from datetime import datetime


@dataclass
class MonthlyIncome:
    salary: float


@dataclass
class UpcomingCashFlowIn:
    cash_flow: str
    amount: float
    date: datetime
