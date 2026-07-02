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

    def growing(self, price, **extra_info):
        info = {"currentPrice": price, "trailingPE": 8.0}
        info.update(extra_info)
        return Fundamentals(
            ticker="T",
            eps=series(1.0, 1.15, 1.32, 1.52),
            equity_plus_dividends=series(100, 115, 132, 152),
            info=info,
        )

    def test_expensive_far_above_sticker(self):
        result = assess_valuation(self.growing(price=1_000.0))
        self.assertEqual(result.verdict, "EXPENSIVE")
        self.assertLess(result.discount_to_sticker, 0.0)

    def test_fair_between_mos_and_sticker(self):
        # no FCF -> no payback shortcut; price just under sticker but above MOS
        cheap = assess_valuation(self.growing(price=10.0))
        sticker = cheap.sticker_price
        result = assess_valuation(self.growing(price=sticker * 0.9))
        self.assertEqual(result.verdict, "FAIR")
        self.assertGreater(result.discount_to_sticker, 0.0)

    def test_nan_price_is_unknown_not_expensive(self):
        # regression: NaN price made every comparison False -> EXPENSIVE
        result = assess_valuation(self.growing(price=float("nan")))
        self.assertEqual(result.verdict, "UNKNOWN")
        self.assertIsNone(result.price)

    def test_nan_market_cap_and_pe_are_ignored(self):
        f = self.growing(price=10.0, marketCap=float("nan"), trailingPE=float("nan"))
        result = assess_valuation(f)
        self.assertIsNone(result.payback_years)
        self.assertIsNotNone(result.sticker_price)

    def test_shrinking_company_has_no_sticker(self):
        f = Fundamentals(
            ticker="SHRINK",
            eps=series(2.0, 1.6, 1.2, 1.0),
            equity_plus_dividends=series(152, 132, 115, 100),
            info={"currentPrice": 10.0},
        )
        result = assess_valuation(f)
        self.assertIsNone(result.sticker_price)
        self.assertEqual(result.verdict, "UNKNOWN")

    def test_ten_cap_per_share(self):
        f = Fundamentals(
            ticker="CAP",
            owner_earnings=series(80, 90, 100),
            shares=series(10, 10, 10),
            info={"currentPrice": 50.0},
        )
        result = assess_valuation(f)
        self.assertEqual(result.ten_cap_price, 100.0)  # 10 * 100 / 10 shares

    def test_minor_unit_currency_conversion_no_network(self):
        # GBP statements, GBp (pence) quote: conversion factor is exactly 100
        f = Fundamentals(
            ticker="LON",
            owner_earnings=series(80, 90, 100),
            shares=series(10, 10, 10),
            info={"currentPrice": 5_000.0, "financialCurrency": "GBP", "currency": "GBp"},
        )
        result = assess_valuation(f)
        self.assertEqual(result.ten_cap_price, 10_000.0)  # 100 GBP -> 10 000 pence

    def test_zero_shares_no_ten_cap(self):
        f = Fundamentals(
            ticker="ZERO",
            owner_earnings=series(80, 90, 100),
            shares=series(0, 0, 0),
            info={"currentPrice": 50.0},
        )
        self.assertIsNone(assess_valuation(f).ten_cap_price)


class TestPaybackEdges(unittest.TestCase):
    def test_never_reached_caps_at_max_years(self):
        self.assertEqual(payback_time(1e12, 1.0, growth=0.0), 30.0)

    def test_negative_growth_treated_as_flat(self):
        self.assertEqual(payback_time(100.0, 12.5, growth=-0.5), 8.0)

    def test_none_growth_treated_as_flat(self):
        self.assertEqual(payback_time(100.0, 12.5, growth=None), 8.0)

    def test_zero_market_cap(self):
        self.assertIsNone(payback_time(0.0, 10.0, growth=0.1))


if __name__ == "__main__":
    unittest.main()
