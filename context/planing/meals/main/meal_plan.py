import base64
import os
import random
import re
from collections import defaultdict
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from .const import DAYS, GENERATED_MEAL_PLANS_PATH, WEEK_NUMBER
from .diet_dishes_dict import diet_dishes
from .email_recipients import EMAIL_RECIPIENTS
from ...meals.main.data_classes.pdf import PDF

load_dotenv()


def section_separator(pdf):
    pdf.set_line_width(0.2)  # Set a thinner line width
    pdf.set_draw_color(150, 150, 150)  # Optional: change color for a lighter line
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Draw the line across the page
    pdf.ln(3)  # Add a small line break for spacing after the separator


def generate_weekly_plan():
    ingredient_entries = defaultdict(list)
    ingredient_totals = defaultdict(lambda: defaultdict(float))
    ingredient_types = {}
    dishes = random.sample(diet_dishes, 7)

    for dish in dishes:
        for ingredient in dish.ingredients:
            ingredient_name = ingredient.name
            measurement = ingredient.measurement
            ingredient_type = ingredient.__class__.__name__

            ingredient_types[ingredient_name] = ingredient_type  # Store the mapping

            if measurement is not None:
                ingredient_entries[ingredient_name].append((measurement.amount, measurement.unit.value))

                if measurement.unit in ingredient_totals[ingredient_name]:
                    ingredient_totals[ingredient_name][measurement.unit.value] += measurement.amount
                else:
                    ingredient_totals[ingredient_name][measurement.unit.value] = measurement.amount

    return {
        "dishes": dishes,
        "ingredient_entries": dict(sorted(ingredient_entries.items())),
        "ingredient_totals": dict(sorted(ingredient_totals.items())),
        "ingredient_types": ingredient_types  # Include the mapping in the return
    }


def add_meal_plan_overview_to_pdf(pdf, plan):
    ingredient_entries = plan["ingredient_entries"]
    ingredient_totals = plan["ingredient_totals"]
    ingredient_types = plan["ingredient_types"]  # Get the ingredient types mapping

    # Group ingredients by their types
    ingredients_by_type = defaultdict(list)
    for ingredient_name in ingredient_entries.keys():
        ingredient_type = ingredient_types.get(ingredient_name, "Other")
        ingredients_by_type[ingredient_type].append(ingredient_name)

    pdf.add_page()

    # Setting up the main title
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, f"Weekly Meal Plan PDF for week {WEEK_NUMBER}", ln=True, align='C')
    pdf.ln(5)

    # Setting up the summary title
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Summary of Batch Ingredients", ln=True, align='C')
    pdf.ln(3)

    section_separator(pdf)

    # For each ingredient type
    for ingredient_type in sorted(ingredients_by_type.keys()):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 6, ingredient_type, ln=True, align='L')
        pdf.ln(2)
        pdf.set_font("Arial", "", 9)

        entries = []
        for ingredient_name in sorted(ingredients_by_type[ingredient_type]):
            units_dict = ingredient_totals.get(ingredient_name, {})
            combined_list = []
            for unit, total_amount in units_dict.items():
                if total_amount != 0:
                    combined_list.append(f"{round(total_amount, 2)} {unit}")
            entry_text = f"{ingredient_name.capitalize()}: [ {', '.join(combined_list) if combined_list else ', '.join(str(entry) for entry in ingredient_entries[ingredient_name])} ]"
            entries.append(entry_text)

        # Display the entries
        for entry in entries:
            pdf.multi_cell(0, 5, entry, border=0, align='L')
        pdf.ln(5)
        section_separator(pdf)


def add_dish_details_to_pdf(pdf, dish):
    pdf.chapter_image(dish.image_url)
    pdf.add_page()
    body = f"Dish name: {dish.title}\n"
    body += f"Time: {dish.time} minutes\nBudget Friendly: {dish.budget_friendly}\n"
    body += f"Region: {dish.region}\nSpicy: {dish.spicy}\nDifficulty: {dish.difficulty}\n"
    body += f"Description: {dish.description}\n"
    pdf.chapter_body(body)

    section_separator(pdf)

    ingredients = "Ingredients:\n"
    for ingredient in dish.ingredients:
        ingredients += (
            f" {ingredient.ingredientType} {ingredient.name}"
            f" [{ingredient.measurement.amount if ingredient.measurement is not None else ''} {ingredient.measurement.unit.value if ingredient.measurement is not None else ''}] "
            f"({ingredient.price if ingredient.price else 'Price not discovered yet'})\n"
        )
    pdf.chapter_body(ingredients)

    section_separator(pdf)

    recipe = "Recipe:\n"
    for step_number, step in sorted(dish.recipe.items()):
        recipe += f"{step_number}. {step}\n"

    pdf.chapter_body(recipe)

    section_separator(pdf)


def save_to_pdf(plan):
    if not os.path.exists(GENERATED_MEAL_PLANS_PATH):
        os.makedirs(GENERATED_MEAL_PLANS_PATH)

    for day, dish in zip(DAYS, plan["dishes"]):
        pdf = PDF()
        pdf.add_page()
        pdf.chapter_title(re.sub(r'^\d+_', '', day))
        add_dish_details_to_pdf(pdf, dish)
        pdf.output(os.path.join(GENERATED_MEAL_PLANS_PATH, f"{day.lower()}.pdf"))


def save_weekly_pdf(plan):
    combined_pdf = PDF()
    add_meal_plan_overview_to_pdf(combined_pdf, plan)

    for day, dish in zip(DAYS, plan["dishes"]):
        combined_pdf.add_page()
        combined_pdf.chapter_title(re.sub(r'^\d+_', '', day))
        add_dish_details_to_pdf(combined_pdf, dish)

    _pdf_path = os.path.join(GENERATED_MEAL_PLANS_PATH, "weekly_meal_plan.pdf")
    combined_pdf.output(_pdf_path)
    return _pdf_path


def email_pdf(_pdf_path, from_email="hanntro@hotmail.com", to_email=None):
    # Create the SendGrid message
    message = Mail(
        from_email="hanna.tronsen@airthings.com",
        to_emails=EMAIL_RECIPIENTS,
        subject=f"Weekly Meal Plan PDF for week {WEEK_NUMBER}",
        html_content='Attached is your weekly meal plan PDF'
    )

    with open(_pdf_path, 'rb') as f:
        data = f.read()
        f.close()
        encoded_file = base64.b64encode(data).decode()

    attachedFile = Attachment(
        FileContent(encoded_file),
        FileName('attachment.pdf'),
        FileType('application/pdf'),
        Disposition('attachment')
    )
    message.attachment = attachedFile

    sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
    response = sg.send(message)
    print(response.status_code, response.body, response.headers)
    print("SendGrid Email sent!")


weekly_plan = generate_weekly_plan()
save_to_pdf(weekly_plan)
pdf_path = save_weekly_pdf(weekly_plan)
email_pdf(pdf_path)
