import os
import random
import re
from .const import DAYS, GENERATED_MEAL_PLANS_PATH
from ...meals.main.data_classes.pdf import PDF
from ...meals.main.dishes_dict import dishes


def generate_weekly_plan():
    return random.sample(dishes, 3)


def add_dish_details_to_pdf(pdf, dish):
    pdf.chapter_image(dish.image_url)
    pdf.add_page()
    body = f"Dish name: {dish.title}\n"
    body += f"Time: {dish.time} minutes\nBudget Friendly: {dish.budget_friendly}\n"
    body += f"Region: {dish.region}\nSpicy: {dish.spicy}\nDifficulty: {dish.difficulty}\n"
    body += f"Description: {dish.description}\n"
    pdf.chapter_body(body)
    pdf.section_separator()
    ingredients = "Ingredients:\n"
    for ingredient in dish.ingredients:
        ingredients += f" - {ingredient.name} ({ingredient.price if ingredient.price else 'Price not available'})\n"
    pdf.chapter_body(ingredients)
    pdf.section_separator()
    recipe = "Recipe:\n"
    for step in dish.recipe:
        recipe += f" - {step}\n"
    pdf.chapter_body(recipe)
    pdf.section_separator()


def save_to_pdf(plan):
    if not os.path.exists(GENERATED_MEAL_PLANS_PATH):
        os.makedirs(GENERATED_MEAL_PLANS_PATH)

    for day, dish in zip(DAYS, plan):
        pdf = PDF()
        pdf.add_page()
        pdf.chapter_title(re.sub(r'^\d+-', '', day))
        add_dish_details_to_pdf(pdf, dish)
        pdf.output(os.path.join(GENERATED_MEAL_PLANS_PATH, f"{day.lower()}.pdf"))


def save_weekly_pdf(plan):
    combined_pdf = PDF()

    for day, dish in zip(DAYS, plan):
        combined_pdf.add_page()
        combined_pdf.chapter_title(re.sub(r'^\d+-', '', day))
        add_dish_details_to_pdf(combined_pdf, dish)

    combined_pdf.output(os.path.join(GENERATED_MEAL_PLANS_PATH, "weekly_meal_plan.pdf"))


weekly_plan = generate_weekly_plan()
save_to_pdf(weekly_plan)
save_weekly_pdf(weekly_plan)
