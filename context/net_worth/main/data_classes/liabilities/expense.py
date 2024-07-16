from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from context.net_worth.main.data_classes.basis import Basis


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

