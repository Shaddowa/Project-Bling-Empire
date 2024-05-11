from enum import Enum


def evaluate_recommendation_key_criteria(recommendation_key) -> int:
    if recommendation_key is not None:
        if recommendation_key == "buy":
            return 100
    return 0


def evaluate_difference_current_to_high(current_price, target_high_price):
    if target_high_price is not None:
        return max(target_high_price - current_price, 0)
    return 0


class AnalystRatingCriteria(Enum):
    TARGET_HIGH_PRICE_DIFF_CURRENT_PRICE = "Target High Price Diff Current Price"
    RECOMMENDATION_KEY = "Recommendation Key"

    @property
    def __str__(self):
        return self.value
