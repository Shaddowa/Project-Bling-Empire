from dataclasses import dataclass
from datetime import datetime


@dataclass
class UpcomingExpense:
    expense: str
    term_payment: float
    interest: float
    principal: float
    interest_balance: float
    loan_balance: float
    date: datetime

