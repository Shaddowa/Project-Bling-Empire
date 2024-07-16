from dataclasses import dataclass


@dataclass
class CashManager:
    # get_bank_account_total_balance_from_dnb() -> USE THIS WHEN DONE DEVELOPING
    cash = 0  # TODO, change when ready

    def get_total_cash_reserve(self) -> int:
        return self.cash
