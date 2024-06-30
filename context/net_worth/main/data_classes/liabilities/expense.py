from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UpcomingExpense:
    expense: str
    term_payment: float
    interest: float
    principal: float
    loan_balance: float
    date: datetime
    fee: Optional[float] = None

