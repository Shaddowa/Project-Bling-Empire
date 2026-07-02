import unittest

import numpy as np
import pandas as pd

from bling.fundamentals import Fundamentals
from bling.quality import Verdict, assess_quality, cagr


def series(*values):
    index = pd.date_range("2021-12-31", periods=len(values), freq="YE")
    return pd.Series(values, index=index, dtype=float)


class TestCagr(unittest.TestCase):
    def test_ten_percent_growth(self):
        s = series(100, 110, 121, 133.1)
        self.assertAlmostEqual(cagr(s), 0.10, places=6)

    def test_negative_start_is_none(self):
        self.assertIsNone(cagr(series(-5, 10, 20)))

    def test_fell_below_zero_is_total_loss(self):
        self.assertEqual(cagr(series(100, 50, -10)), -1.0)

    def test_too_short(self):
        self.assertIsNone(cagr(series(100)))
        self.assertIsNone(cagr(None))

    def test_nan_endpoints_are_none_not_nan(self):
        # regression: a NaN endpoint used to propagate NaN through the score
        self.assertIsNone(cagr(series(np.nan, 110, 121)))
        self.assertIsNone(cagr(series(100, 110, np.nan)))

    def test_empty_series(self):
        self.assertIsNone(cagr(pd.Series(dtype=float)))

    def test_zero_start_is_none(self):
        self.assertIsNone(cagr(series(0.0, 10, 20)))


class TestQuality(unittest.TestCase):
    def wonderful_company(self):
        growing = series(100, 115, 132, 152)  # ~15%/yr
        return Fundamentals(
            ticker="TEST",
            revenue=growing,
            net_income=series(20, 23, 27, 31),
            equity=series(100, 115, 132, 152),
            equity_plus_dividends=series(100, 118, 139, 163),
            total_debt=series(10, 10, 10, 10),
            operating_cash_flow=series(25, 29, 33, 38),
            free_cash_flow=series(15, 18, 21, 25),
            owner_earnings=series(18, 21, 25, 29),
            roe=series(0.20, 0.20, 0.20, 0.20),
            roic=series(0.18, 0.18, 0.18, 0.18),
        )

    def test_wonderful_company_passes_everything(self):
        result = assess_quality(self.wonderful_company())
        self.assertEqual(result.passed, result.total)
        self.assertEqual(result.score, 100.0)

    def test_missing_data_is_unknown_not_pass(self):
        result = assess_quality(Fundamentals(ticker="EMPTY"))
        self.assertEqual(result.passed, 0)
        self.assertTrue(all(v == Verdict.UNKNOWN for v in result.verdicts.values()))
        self.assertEqual(result.score, 0.0)

    def test_slow_growth_fails(self):
        f = self.wonderful_company()
        f.revenue = series(100, 102, 104, 106)  # ~2%/yr
        result = assess_quality(f)
        self.assertEqual(result.verdicts["sales_growth"], Verdict.FAIL)

    def test_heavy_debt_fails_payoff(self):
        f = self.wonderful_company()
        f.total_debt = series(500, 500, 500, 500)  # 20x FCF of 25
        result = assess_quality(f)
        self.assertEqual(result.verdicts["debt_payoff"], Verdict.FAIL)
        self.assertEqual(result.metrics["debt_payoff"], 20.0)

    def test_debt_free_passes_payoff(self):
        f = self.wonderful_company()
        f.total_debt = series(0, 0, 0, 0)
        result = assess_quality(f)
        self.assertEqual(result.verdicts["debt_payoff"], Verdict.PASS)
        self.assertEqual(result.metrics["debt_payoff"], 0.0)

    def test_negative_fcf_fails_payoff(self):
        f = self.wonderful_company()
        f.free_cash_flow = series(15, 18, 21, -5)
        result = assess_quality(f)
        self.assertEqual(result.verdicts["debt_payoff"], Verdict.FAIL)

    def test_nan_debt_or_fcf_is_unknown(self):
        # regression: NaN used to fall through to a FAIL with a NaN metric
        f = self.wonderful_company()
        f.total_debt = series(10, 10, 10, np.nan)
        result = assess_quality(f)
        self.assertEqual(result.verdicts["debt_payoff"], Verdict.UNKNOWN)
        self.assertIsNone(result.metrics["debt_payoff"])

    def test_all_nan_returns_series_is_unknown(self):
        f = self.wonderful_company()
        f.roe = series(np.nan, np.nan, np.nan, np.nan)
        result = assess_quality(f)
        self.assertEqual(result.verdicts["roe"], Verdict.UNKNOWN)
        self.assertIsNone(result.metrics["roe"])

    def test_two_years_of_data_is_unknown_growth(self):
        f = Fundamentals(ticker="THIN", revenue=series(100, 120))
        result = assess_quality(f)
        self.assertEqual(result.verdicts["sales_growth"], Verdict.UNKNOWN)

    def test_fcf_increasing_verdicts(self):
        f = self.wonderful_company()
        result = assess_quality(f)  # 15 -> 25 monotone
        self.assertEqual(result.verdicts["fcf_increasing"], Verdict.PASS)
        f.free_cash_flow = series(25, 20, 18, 15)  # falling
        self.assertEqual(assess_quality(f).verdicts["fcf_increasing"], Verdict.FAIL)
        f.free_cash_flow = series(15, 25)  # too short
        self.assertEqual(assess_quality(f).verdicts["fcf_increasing"], Verdict.UNKNOWN)

    def test_score_counts_only_passes(self):
        f = self.wonderful_company()
        f.revenue = None  # one criterion drops to UNKNOWN
        result = assess_quality(f)
        self.assertEqual(result.verdicts["sales_growth"], Verdict.UNKNOWN)
        self.assertEqual(result.total, 9)
        self.assertEqual(result.passed, 8)
        self.assertEqual(result.score, round(100.0 * 8 / 9, 1))


if __name__ == "__main__":
    unittest.main()
