from datetime import datetime

DAYS = ["01-Monday", "02-Tuesday", "03-Wednesday", "04-Thursday", "05-Friday", "06-Saturday", "07-Sunday"]
WEEK_NUMBER = datetime.now().isocalendar()[1]
GENERATED_MEAL_PLANS_PATH = f"context/planing/meals/main/generated_meal_plans/week-{WEEK_NUMBER}"
