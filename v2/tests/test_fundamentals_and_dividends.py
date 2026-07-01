import unittest
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from bling.data import TickerBundle
from bling.dividends import assess_dividends, compare_forward_to_trailing, ex_date_score
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

    def test_nan_fields_score_nothing(self):
        # regression: NaN is truthy — rates went through comparisons as garbage
        nan = float("nan")
        result = assess_dividends("NAN", {
            "trailingAnnualDividendYield": nan, "dividendYield": nan,
            "trailingAnnualDividendRate": nan, "dividendRate": nan,
            "payoutRatio": nan, "exDividendDate": nan,
        })
        self.assertEqual(result.score, 0.0)
        self.assertIsNone(result.trailing_yield)
        self.assertIsNone(result.forward_yield)

    def test_nan_forward_rate_does_not_earn_forward_only_points(self):
        self.assertEqual(compare_forward_to_trailing(4.0, float("nan")), 0.5)
        self.assertEqual(compare_forward_to_trailing(float("nan"), 4.0), 2.0)


class TestExDateScore(unittest.TestCase):
    def test_recent_epoch_seconds(self):
        recent = (datetime.now(tz=timezone.utc) - timedelta(days=30)).timestamp()
        self.assertEqual(ex_date_score(recent), 1.0)
        self.assertEqual(ex_date_score(int(recent)), 1.0)

    def test_old_epoch_seconds(self):
        old = (datetime.now(tz=timezone.utc) - timedelta(days=400)).timestamp()
        self.assertEqual(ex_date_score(old), 0.0)

    def test_aware_and_naive_datetimes(self):
        aware = datetime.now(tz=timezone.utc) - timedelta(days=10)
        self.assertEqual(ex_date_score(aware), 1.0)
        naive = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=10)  # assumed UTC
        self.assertEqual(ex_date_score(naive), 1.0)

    def test_pandas_timestamp_and_date(self):
        # regression: these used to crash datetime.fromtimestamp with TypeError
        self.assertEqual(ex_date_score(pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=5)), 1.0)
        self.assertEqual(ex_date_score(date.today() - timedelta(days=5)), 1.0)

    def test_iso_string(self):
        recent = (datetime.now(tz=timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        self.assertEqual(ex_date_score(recent), 1.0)
        self.assertEqual(ex_date_score("2010-01-01"), 0.0)

    def test_garbage_is_zero_not_a_crash(self):
        for junk in (None, 0, -1, float("nan"), float("inf"), "not a date", object()):
            self.assertEqual(ex_date_score(junk), 0.0, msg=repr(junk))


class TestFundamentalsEdges(unittest.TestCase):
    def test_duplicated_statement_label_with_nans(self):
        # regression: dropna-before-iloc raised IndexError when every
        # duplicate row had at least one NaN year
        columns = pd.to_datetime(["2024-12-31", "2023-12-31", "2022-12-31"])
        inc = pd.DataFrame(
            [[130.0, np.nan, 100.0], [np.nan, 116.0, 101.0]],
            index=["Total Revenue", "Total Revenue"], columns=columns)
        bundle = TickerBundle(ticker="DUP", fetched_at=datetime.now(), info={},
                              income_stmt=inc)
        f = extract_fundamentals(bundle)
        self.assertIsNotNone(f.revenue)
        self.assertEqual(list(f.revenue.values), [100.0, 130.0])  # first dup row, NaN year dropped

    def test_negative_equity_years_excluded_from_roe(self):
        columns = pd.to_datetime(["2024-12-31", "2023-12-31", "2022-12-31"])
        inc = pd.DataFrame([[26.0, 23.0, 20.0]], index=["Net Income"], columns=columns)
        bs = pd.DataFrame([[150.0, -10.0, 0.0]], index=["Stockholders Equity"], columns=columns)
        bundle = TickerBundle(ticker="NEGEQ", fetched_at=datetime.now(), info={},
                              income_stmt=inc, balance_sheet=bs)
        f = extract_fundamentals(bundle)
        self.assertEqual(len(f.roe), 1)  # only the positive-equity year
        self.assertAlmostEqual(float(f.roe.iloc[-1]), 26.0 / 150.0)

    def test_all_negative_equity_means_no_roe(self):
        columns = pd.to_datetime(["2024-12-31", "2023-12-31"])
        inc = pd.DataFrame([[26.0, 23.0]], index=["Net Income"], columns=columns)
        bs = pd.DataFrame([[-150.0, -10.0]], index=["Stockholders Equity"], columns=columns)
        bundle = TickerBundle(ticker="UNDERWATER", fetched_at=datetime.now(), info={},
                              income_stmt=inc, balance_sheet=bs)
        f = extract_fundamentals(bundle)
        self.assertIsNone(f.roe)
        self.assertIsNone(f.roic)

    def test_empty_bundle_yields_empty_fundamentals(self):
        bundle = TickerBundle(ticker="EMPTY", fetched_at=datetime.now(), info={})
        f = extract_fundamentals(bundle)
        self.assertIsNone(f.revenue)
        self.assertIsNone(f.free_cash_flow)
        self.assertEqual(f.years_of_data, 0)


if __name__ == "__main__":
    unittest.main()
