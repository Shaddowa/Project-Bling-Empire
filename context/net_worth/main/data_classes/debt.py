from dataclasses import dataclass


@dataclass
class TotalDebts:
    mortgage_loan: float
    student_loan: float

    def sum(self) -> float:
        return sum([self.mortgage_loan, self.student_loan])
