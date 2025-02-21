import os
from datetime import datetime

import pandas
import pandas as pd

from context.net_worth.main.const import NOW
from context.net_worth.main.data_classes.assets.crypto import CryptoPortfolio
from context.net_worth.main.data_classes.assets.stock_portfolio import stockPortfolio
from context.net_worth.main.data_classes.assetsManager import AssetsManager
from context.net_worth.main.data_classes.liabilitiesManager import LiabilitiesManager
from context.net_worth.main.functions import calculate_future_gross_liquid_net_worth, format_currency, \
    calculate_future_net_worth, calculate_gross_liquid_net_worth, calculate_net_worth, \
    calculate_expenses_after_cash_flow


class SnapshotManager:

    def __init__(self):
        self.snapshot_root_path = f"context/net_worth/main/snapshots/"

    def snapshot_monthly_budgeting(self):

        def get_monthly_budgeting_data():
            monthly_liabilities = LiabilitiesManager().get_monthly_liabilities()
            total_monthly_income = AssetsManager().get_total_monthly_cashflow()

            liabilities = [
                {"name": key, "amount": value}
                for liability in monthly_liabilities
                for key, value in liability.items()
            ]

            income = [
                {"name": key, "amount": value}
                for income_item in total_monthly_income
                for key, value in income_item.items()
            ]

            sum_liabilities = sum([liability["amount"] for liability in liabilities])
            sum_income = sum([income_item["amount"] for income_item in income])

            summary = [
                {"name": "Total monthly liabilities", "amount": sum_liabilities},
                {"name": "Total monthly income", "amount": sum_income},
                {"name": "Total monthly budget", "amount": sum_income - sum_liabilities}
            ]

            return liabilities + income + summary

        def _convert_to_df():
            df = pd.DataFrame(monthly_budgeting_data)
            df.columns = ['Category', 'Amount']
            df['Snapshot Date'] = datetime.now().strftime('%Y-%m')
            return df

        budgeting_snapshot_file = "monthly_budgeting.csv"
        budgeting_snapshot_path = f"{self.snapshot_root_path}monthly_budgeting/"
        full_path = budgeting_snapshot_path + budgeting_snapshot_file

        if not os.path.exists(budgeting_snapshot_path):
            os.makedirs(budgeting_snapshot_path)

        monthly_budgeting_data = get_monthly_budgeting_data()
        new_df = _convert_to_df()

        if os.path.exists(full_path):
            updated_df = pd.concat([pd.read_csv(full_path), new_df], ignore_index=True)
            updated_df = updated_df.drop_duplicates(subset=['Category', 'Snapshot Date'], keep='last')
        else:
            updated_df = new_df

        updated_df.to_csv(full_path, index=False)

    # Not needed right now, I don't own any stocks

    # def snapshot_stock_portfolio(self):
    #     open(self.snapshot_root_path + "/stock_portfolio.csv", "w").write(
    #         pandas.DataFrame({
    #             "Stock portfolio": stockPortfolio.sum_local_currency(),
    #             "Stock portfolio ROI": stockPortfolio.calculate_roi_for_whole_portfolio()
    #         }).to_csv())

    # Not sure if the ROI logic is correct, so this should be investigated
    def snapshot_crypto_portfolio(self):

        def _get_crypto_portfolio():
            synced_firi_portfolio = CryptoPortfolio().synchronize_with_firi()
            sum_local_currency = synced_firi_portfolio.sum_local_currency()
            normalized_data = {
                key: value if isinstance(value, dict) else {"value": value, "roi": None}
                for key, value in sum_local_currency.items()
            }

            return normalized_data

        def _convert_to_df():
            df = pd.DataFrame.from_dict(crypto_portfolio, orient='index').reset_index()
            df.columns = ['Currency', 'Value (NOK)', 'ROI (NOK)']
            df['Snapshot Date'] = datetime.now().strftime('%Y-%m-%d')
            return df

        crypto_snapshot_file = "crypto_portfolio.csv"
        crypto_snapshot_path = f"{self.snapshot_root_path}crypto_portfolio/"
        full_path = crypto_snapshot_path + crypto_snapshot_file

        if not os.path.exists(crypto_snapshot_path):
            os.makedirs(crypto_snapshot_path)

        crypto_portfolio = _get_crypto_portfolio()
        new_df = _convert_to_df()

        if os.path.exists(full_path):
            updated_df = pd.concat([pd.read_csv(full_path), new_df], ignore_index=True)
            updated_df = updated_df.drop_duplicates(subset=['Currency', 'Snapshot Date'], keep='last')
        else:
            updated_df = new_df

        updated_df.to_csv(full_path, index=False)

    def snapshot_net_worth(self):

        def get_net_worth_data():
            return {"total_debts": LiabilitiesManager().sum_total_debts()}

        def _convert_to_df():
            df = pd.DataFrame.from_dict(net_worth_data, orient='index').reset_index()
            df.columns = ['Category', 'Amount']
            df['Snapshot Date'] = datetime.now().strftime('%Y-%m')
            return df

        net_worth_snapshot_file = "net_worth.csv"
        net_worth_snapshot_path = f"{self.snapshot_root_path}net_worth/"
        full_path = net_worth_snapshot_path + net_worth_snapshot_file

        if not os.path.exists(net_worth_snapshot_path):
            os.makedirs(net_worth_snapshot_path)

        net_worth_data = get_net_worth_data()
        new_df = _convert_to_df()

        if os.path.exists(full_path):
            updated_df = pd.concat([pd.read_csv(full_path), new_df], ignore_index=True)
            updated_df = updated_df.drop_duplicates(subset=['Category', 'Snapshot Date'], keep='last')
        else:
            updated_df = new_df

        updated_df.to_csv(full_path, index=False)

    def snapshot_data(self):
        self.snapshot_crypto_portfolio()
        self.snapshot_monthly_budgeting()
        self.snapshot_net_worth()


SnapshotManager().snapshot_data()
