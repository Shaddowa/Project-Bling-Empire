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
    dishes = random.sample(diet_dishes, 7)

    for dish in dishes:
        for ingredient in dish.ingredients:
            ingredient_name = ingredient.name
            measurement = ingredient.measurement

            if measurement is not None:
                ingredient_entries[ingredient_name].append((measurement.amount, measurement.unit.value))

                if measurement.unit in ingredient_totals[ingredient_name]:
                    ingredient_totals[ingredient_name][measurement.unit.value] += measurement.amount
                else:
                    ingredient_totals[ingredient_name][measurement.unit.value] = measurement.amount

    return {
        "dishes": dishes,
        "ingredient_entries": dict(sorted(ingredient_entries.items())),
        "ingredient_totals": dict(sorted(ingredient_totals.items()))
    }


def add_meal_plan_overview_to_pdf(pdf, plan):
    ingredient_entries = plan["ingredient_entries"]
    ingredient_totals = plan["ingredient_totals"]

    pdf.add_page()

    # Setting up the main title
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, f"Weekly Meal Plan PDF for week {WEEK_NUMBER}", ln=True, align='C')
    pdf.ln(5)

    # Setting up the summary title
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Summary of batch ingredients", ln=True, align='C')
    pdf.ln(3)

    section_separator(pdf)

    # Prepare data for the two columns
    entries = []
    for ingredient, units_dict in ingredient_totals.items():
        combined_list = []
        for unit, total_amount in units_dict.items():
            if total_amount != 0:
                combined_list.append(f"{round(total_amount, 2)} {unit}")

        entry_text = f"{ingredient.capitalize()}: [ {', '.join(combined_list) if combined_list else ', '.join(str(entry) for entry in ingredient_entries[ingredient])} ]"
        entries.append(entry_text)

    # Split entries into two columns
    mid_index = len(entries) // 2
    left_column = entries[:mid_index]
    right_column = entries[mid_index:]

    # Set font for columns
    pdf.set_font("Arial", "", 9)

    # Width of each column
    col_width = (pdf.w - 2 * pdf.l_margin) / 2

    # Get the maximum number of entries
    max_len = max(len(left_column), len(right_column))

    for i in range(max_len):
        y_current = pdf.get_y()

        # Left column entry
        if i < len(left_column):
            left_entry = left_column[i]
            pdf.set_xy(pdf.l_margin, y_current)
            pdf.multi_cell(col_width, 5, left_entry, border=0, align='L')
            left_cell_height = pdf.get_y() - y_current
        else:
            left_cell_height = 0

        # Right column entry
        if i < len(right_column):
            right_entry = right_column[i]
            pdf.set_xy(pdf.l_margin + col_width, y_current)
            pdf.multi_cell(col_width, 5, right_entry, border=0, align='L')
            right_cell_height = pdf.get_y() - y_current
        else:
            right_cell_height = 0

        # Determine the maximum cell height
        max_cell_height = max(left_cell_height, right_cell_height, 5)

        # Move cursor to the next line
        pdf.set_y(y_current + max_cell_height)

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
        to_emails="hannatro@hotmail.com",
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
