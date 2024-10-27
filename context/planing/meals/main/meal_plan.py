import base64
import os
import random
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from .const import DAYS, GENERATED_MEAL_PLANS_PATH, WEEK_NUMBER
from .diet_dishes_dict import diet_dishes
from ...meals.main.data_classes.pdf import PDF
from ...meals.main.dishes_dict import dishes
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from dotenv import load_dotenv
# Email the PDF to yourself
# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

load_dotenv()


def generate_weekly_plan():
    return random.sample(diet_dishes, 7)


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
        ingredients += (
            f" {ingredient.ingredientType} {ingredient.name}"
            f" [{ingredient.measurement.amount if ingredient.measurement is not None else ''} {ingredient.measurement.unit.value if ingredient.measurement is not None else ''}] "
            f"({ingredient.price if ingredient.price else 'Price not discovered yet' })\n"
        )
    pdf.chapter_body(ingredients)
    pdf.section_separator()
    recipe = "Recipe:\n"
    for step_number, step in sorted(dish.recipe.items()):
        recipe += f"{step_number}. {step}\n"

    pdf.chapter_body(recipe)
    pdf.section_separator()


def save_to_pdf(plan):
    if not os.path.exists(GENERATED_MEAL_PLANS_PATH):
        os.makedirs(GENERATED_MEAL_PLANS_PATH)

    for day, dish in zip(DAYS, plan):
        pdf = PDF()
        pdf.add_page()
        pdf.chapter_title(re.sub(r'^\d+_', '', day))
        add_dish_details_to_pdf(pdf, dish)
        pdf.output(os.path.join(GENERATED_MEAL_PLANS_PATH, f"{day.lower()}.pdf"))


def save_weekly_pdf(plan):
    combined_pdf = PDF()

    for day, dish in zip(DAYS, plan):
        combined_pdf.add_page()
        combined_pdf.chapter_title(re.sub(r'^\d+_', '', day))
        add_dish_details_to_pdf(combined_pdf, dish)

    _pdf_path = os.path.join(GENERATED_MEAL_PLANS_PATH, "weekly_meal_plan.pdf")
    combined_pdf.output(_pdf_path)
    return _pdf_path


def email_pdf(_pdf_path, from_email="hanntro@hotmail.com", to_email=None):
    # Create the SendGrid message
    message = Mail(
        from_email=from_email,
        to_emails="hanna.tronsen@airthings.com",
        subject=f"Weekly Meal Plan PDF for week ",
        html_content='Attached is your weekly meal plan PDF'
    )

    # with open(_pdf_path, 'rb') as f:
    #     file_data = f.read()
    #     encoded_file = base64.b64encode(file_data).decode()
    #
    #     # Attach PDF to SendGrid email
    # attached_file = Attachment(
    #     FileContent(encoded_file),
    #     FileName(os.path.basename(_pdf_path)),
    #     FileType("application/pdf"),
    #     Disposition("attachment")
    # )
    #message.attachment = attached_file

    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
        print("SendGrid Email sent!")
    except Exception as e:
        print(e)


weekly_plan = generate_weekly_plan()
save_to_pdf(weekly_plan)
pdf_path = save_weekly_pdf(weekly_plan)
email_pdf(pdf_path)
