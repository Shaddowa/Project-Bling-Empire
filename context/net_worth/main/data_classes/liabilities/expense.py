from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Basis(Enum):
    monthly = "monthly"
    yearly = "yearly"
    weekly = "weekly"
    daily = "daily"


@dataclass
class ReoccurringExpense:
    expense: str
    amount: float
    basis: Basis


@dataclass
class UpcomingExpense:
    expense: str
    amount: float
    date: datetime


@dataclass
class DebtExpense:
    expense: str
    term_payment: float
    interest: float
    principal: float
    loan_balance: float
    date: datetime
    fee: Optional[float] = None

