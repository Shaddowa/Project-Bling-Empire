import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from bling.data import TickerBundle
from bling.dividends import assess_dividends, compare_forward_to_trailing
from bling.fundamentals import extract_fundamentals


def statement(rows: dict) -> pd.DataFrame:
    # yfinance statements: columns are fiscal year ends, newest first
    columns = pd.to_datetime(["2024-12-31", "2023-12-31", "2022-12-31"])
    return pd.DataFrame({c: {k: v[i] for k, v in rows.items()} for i, c in enumerate(columns)})


class TestExtractFundamentals(unittest.TestCase):
    def bundle(self):
        return TickerBundle(
            ticker="TEST",
            fetched_at=datetime.now(),
            info={"currentPrice": 100.0},
            income_stmt=statement({
                "Total Revenue": [130.0, 115.0, 100.0],
                "Net Income": [26.0, 23.0, 20.0],
                "Diluted EPS": [2.6, 2.3, 2.0],
                "Tax Provision": [6.0, 5.0, 4.0],
            }),
            balance_sheet=statement({
                "Stockholders Equity": [150.0, 125.0, 100.0],
                "Long Term Debt": [40.0, 45.0, 50.0],  # no Total Debt row on purpose
                "Ordinary Shares Number": [10.0, 10.0, 10.0],
            }),
            cashflow=statement({
                "Operating Cash Flow": [30.0, 26.0, 22.0],
                "Capital Expenditure": [-5.0, -4.0, -4.0],
                "Cash Dividends Paid": [-2.0, -2.0, -2.0],
                "Depreciation And Amortization": [4.0, 4.0, 4.0],
            }),
            prices=pd.DataFrame({"Close": [100.0]}),
        )

    def test_series_are_chronological(self):
        f = extract_fundamentals(self.bundle())
        self.assertEqual(list(f.revenue.values), [100.0, 115.0, 130.0])

    def test_debt_falls_back_to_long_term_debt(self):
        f = extract_fundamentals(self.bundle())
        self.assertEqual(float(f.total_debt.iloc[-1]), 40.0)

    def test_fcf_derived_from_ocf_and_capex(self):
        f = extract_fundamentals(self.bundle())
        self.assertEqual(float(f.free_cash_flow.iloc[-1]), 25.0)

    def test_owner_earnings_falls_back_when_working_capital_missing(self):
        f = extract_fundamentals(self.bundle())
        self.assertTrue(f.owner_earnings_is_approximate)
        self.assertEqual(float(f.owner_earnings.iloc[-1]), 25.0)  # OCF - capex

    def test_dividends_added_back_to_book_value(self):
        f = extract_fundamentals(self.bundle())
        # equity 150 + cumulative dividends (2+2+2) = 156 in the last year
        self.assertEqual(float(f.equity_plus_dividends.iloc[-1]), 156.0)

    def test_roe_and_roic(self):
        f = extract_fundamentals(self.bundle())
        self.assertAlmostEqual(float(f.roe.iloc[-1]), 26.0 / 150.0)
        self.assertAlmostEqual(float(f.roic.iloc[-1]), 26.0 / 190.0)


class TestDividendScore(unittest.TestCase):
    def test_comparison_ladder(self):
        self.assertEqual(compare_forward_to_trailing(2.0, 3.0), 4.0)
        self.assertEqual(compare_forward_to_trailing(3.0, 3.0), 3.0)
        self.assertEqual(compare_forward_to_trailing(None, 3.0), 2.0)
        self.assertEqual(compare_forward_to_trailing(3.0, 2.0), 1.0)
        self.assertEqual(compare_forward_to_trailing(3.0, None), 0.5)
        self.assertEqual(compare_forward_to_trailing(None, None), 0.0)

    def test_full_house(self):
        recent_ex_date = (datetime.now(tz=timezone.utc) - timedelta(days=30)).timestamp()
        result = assess_dividends("DIV", {
            # yfinance units: trailing yield is a FRACTION, forward is a PERCENT
            "trailingAnnualDividendYield": 0.030, "dividendYield": 3.5,
            "trailingAnnualDividendRate": 4.0, "dividendRate": 4.5,
            "payoutRatio": 0.50, "exDividendDate": recent_ex_date,
        })
        self.assertEqual(result.score, 10.0)

    def test_no_dividend(self):
        self.assertEqual(assess_dividends("NODIV", {}).score, 0.0)

    def test_cross_currency_rates_not_compared(self):
        # Equinor-style: trailing rate in USD (1.52), forward in NOK (14.48).
        result = assess_dividends("EQNR", {
            "trailingAnnualDividendYield": 0.0048, "dividendYield": 4.62,
            "trailingAnnualDividendRate": 1.52, "dividendRate": 14.48,
        })
        # yields: forward 0.0462 > trailing 0.0048 -> 4; rates: trailing dropped
        # as unit-incompatible -> forward-only branch = 2. Total 6 -> score 6.
        self.assertEqual(result.score, 6.0)

    def test_implausible_yield_dropped(self):
        result = assess_dividends("JUNK", {"trailingAnnualDividendYield": 0.80, "dividendYield": 90.0})
        self.assertEqual(result.score, 0.0)


if __name__ == "__main__":
    unittest.main()
