from enum import Enum


class TransactionType(Enum):
    INTERNAL_TRANSFER = "InternalTransfer"
    MATCH = "Match"
    MATCH_FEE = "MatchFee"
    VIPPS_DEPOSIT = "VippsDeposit"
    DEPOSIT_FEE = "DepositFee"
    STAKING_REWARD = "StakingReward"
    BANK_DEPOSIT = "BankDeposit"
    STAKE = "Stake"
    BONUS = "Bonus"

    @classmethod
    def from_str(cls, transaction_type_str):
        try:
            return cls(transaction_type_str)
        except ValueError:
            print(f"Could not convert {transaction_type_str} to TransactionType")
            return None
