import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_SECRET_ID = os.getenv('API_SECRET_ID')
API_SECRET_KEY = os.getenv('API_SECRET_KEY')
DEFAULT_ACCOUNT_ID = os.getenv('DEFAULT_ACCOUNT_ID')
MIDDLE_ACCOUNT_ID = os.getenv('MIDDLE_ACCOUNT_ID')
SUPER_SAVER_ACCOUNT_ID = os.getenv('SUPER_SAVER_ACCOUNT_ID')
DEFAULT_STOCKS_ACCOUNT_ID = os.getenv('DEFAULT_STOCKS_ACCOUNT_ID')
GEEK_FREAK_ACCOUNT_ID = os.getenv('GEEK_FREAK_ACCOUNT_ID')
STUDENT_LOAN_ACCOUNT = os.getenv('STUDENT_LOAN_ACCOUNT')

ACCOUNTS = [
    DEFAULT_ACCOUNT_ID,
    MIDDLE_ACCOUNT_ID,
    SUPER_SAVER_ACCOUNT_ID,
    DEFAULT_STOCKS_ACCOUNT_ID,
    GEEK_FREAK_ACCOUNT_ID,
    STUDENT_LOAN_ACCOUNT
]

BASE_URL = "https://bankaccountdata.gocardless.com/api/v2/"


def get_access_token():
    response = requests.post(
        BASE_URL + "token/new/",
        json={
            "secret_id": API_SECRET_ID,
            "secret_key": API_SECRET_KEY
        },
        headers={
            "accept": "application/json",
            "Content-Type": "application/json"
        }
    )
    if response.status_code == 200:
        return response.json().get('access')
    else:
        return None


def make_authenticated_request(access_token):
    response = requests.post(
        BASE_URL + "requisitions/",
        json={
            "redirect": "https://www.bulq.no",  # URL to redirect to after requisition is complete
            "institution_id": "DNB_DNBANOKK"  # ID of the institution (bank) involved in the requisition
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json().get('id'), response.json().get('link')


def get_bank_account_balances(access_token, account_id):
    response = requests.get(f"{BASE_URL}accounts/{account_id}/balances/", headers={
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json"
    })

    if response.status_code == 200:
        return response.json().get('balances')
    else:
        return response.status_code, response.text


def get_bank_account_total_balance_from_api():
    sum_balance = 0.0
    access_token = get_access_token()
    if access_token:
        # The requisitions ID is used to help find account ids
        # we have already saved our ids and don't need to use this for now
        requisition_id, link = make_authenticated_request(access_token)
        print(f"use this link to authenticate if needed: {link}")
        for account in ACCOUNTS:
            balances = get_bank_account_balances(access_token, account)
            for balance in balances:
                balanceType = balance.get("balanceType")
                balanceAmount = balance.get("balanceAmount")
                if balanceAmount:
                    if balanceType == "interimAvailable":
                        sum_balance += float(balanceAmount.get("amount"))

    return sum_balance

