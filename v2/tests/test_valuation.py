import unittest

import pandas as pd

from bling.fundamentals import Fundamentals
from bling.valuation import assess_valuation, payback_time, sticker_price


def series(*values):
    index = pd.date_range("2021-12-31", periods=len(values), freq="YE")
    return pd.Series(values, index=index, dtype=float)


class TestStickerPrice(unittest.TestCase):
    def test_known_rule_one_example(self):
        # EPS 1.00 growing 15%/yr for 10y -> 4.0456; future PE = 2*15 = 30
        # future price 121.37; discounted at 15% for 10y -> ~30.0
        sticker = sticker_price(eps_now=1.0, growth=0.15, trailing_pe=None)
        self.assertAlmostEqual(sticker, 30.0, delta=0.1)

    def test_negative_eps_has_no_sticker(self):
        self.assertIsNone(sticker_price(eps_now=-2.0, growth=0.10, trailing_pe=15))

    def test_low_current_pe_caps_future_pe(self):
        rich = sticker_price(eps_now=1.0, growth=0.15, trailing_pe=None)
        capped = sticker_price(eps_now=1.0, growth=0.15, trailing_pe=10.0)
        self.assertLess(capped, rich)


class TestPaybackTime(unittest.TestCase):
    def test_flat_cash_flow(self):
        # 100 market cap, 12.5/yr flat -> 8 years
        self.assertEqual(payback_time(100.0, 12.5, growth=0.0), 8.0)

    def test_growth_shortens_payback(self):
        self.assertLess(payback_time(100.0, 10.0, growth=0.15), 10.0)

    def test_no_cash_flow(self):
        self.assertIsNone(payback_time(100.0, 0.0, growth=0.10))


class TestAssessValuation(unittest.TestCase):
    def test_on_sale_below_mos(self):
        f = Fundamentals(
            ticker="CHEAP",
            eps=series(1.0, 1.15, 1.32, 1.52),
            equity_plus_dividends=series(100, 115, 132, 152),
            info={"currentPrice": 10.0, "trailingPE": 8.0, "marketCap": 1000.0},
            free_cash_flow=series(100, 115, 132, 152),
        )
        result = assess_valuation(f)
        self.assertIsNotNone(result.sticker_price)
        self.assertEqual(result.verdict, "ON_SALE")

    def test_unknown_without_price(self):
        result = assess_valuation(Fundamentals(ticker="NODATA"))
        self.assertEqual(result.verdict, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
