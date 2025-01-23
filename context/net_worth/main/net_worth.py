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
        get_total_monthly_liabilities = LiabilitiesManager().get_total_monthly_liabilities()
        get_total_monthly_income = AssetsManager().get_total_monthly_cashflow()

        open(self.snapshot_root_path + "/monthly_budgeting.csv", "w").write(
            pandas.DataFrame({
                "Total monthly liabilities": get_total_monthly_liabilities,
                "Total monthly income": get_total_monthly_income,
                "Budget": get_total_monthly_income - get_total_monthly_liabilities
            }).to_csv())

    def snapshot_stock_portfolio(self):
        open(self.snapshot_root_path + "/stock_portfolio.csv", "w").write(
            pandas.DataFrame({
                "Stock portfolio": stockPortfolio.sum_local_currency(),
                "Stock portfolio ROI": stockPortfolio.calculate_roi_for_whole_portfolio()
            }).to_csv())

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

    @staticmethod
    def snapshot_net_worth(self):
        calculate_net_worth()
        calculate_expenses_after_cash_flow()
        calculate_future_net_worth()
        calculate_gross_liquid_net_worth()
        calculate_future_gross_liquid_net_worth()
        # print(calculate_future_gross_liquid_net_worth())
        # print(f"Net Worth: {format_currency(calculate_net_worth(TotalAssets, TotalDebts))}")
        # print(
        #     f"Future Net Worth: {format_currency(calculate_future_net_worth(TotalAssets, TotalDebts, UpcomingCashFlowIn, UpcomingExpenses))}")
        # print(f"Gross Liquid Net Worth: {format_currency(calculate_gross_liquid_net_worth(TotalAssets))}")
        # print(
        #     f"Gross Liquid Future Net Worth: {format_currency(calculate_future_gross_liquid_net_worth(TotalAssets, UpcomingCashFlowIn, UpcomingExpenses))}")
        # print(f"Total Assets: {format_currency(TotalAssets.sum())}")
        # print(f"Total Debts: {format_currency(TotalDebts.sum())}")


SnapshotManager().snapshot_crypto_portfolio()
