from dataclasses import dataclass
from datetime import datetime


@dataclass
class MonthlyLiabilities:
    mortgage_loan: float
    student_loan: float
    joint_mortgage_expense: float
    insurance: float


@dataclass
class UpcomingExpense:
    expense: str
    amount: float
    date: datetime


