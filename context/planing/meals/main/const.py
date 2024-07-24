from datetime import datetime

DAYS = ["01_Monday", "02_Tuesday", "03_Wednesday", "04_Thursday", "05_Friday", "06_Saturday", "07_Sunday"]
WEEK_NUMBER = datetime.now().isocalendar()[1]
GENERATED_MEAL_PLANS_PATH = f"context/planing/meals/main/generated_meal_plans/week_{WEEK_NUMBER}"
