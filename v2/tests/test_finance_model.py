import unittest

from bling.finance.model import (
    SAFETY_BUFFER_MONTHS,
    PORTFOLIO_RETURN_ASSUMPTION,
    SUSTAINABLE_RUNWAY_MONTHS,
    Debt,
    Finances,
    Holding,
    LineItem,
    build_report,
    build_targets,
)


def finances(cash=100_000.0, income=0.0, expenses=8_000.0, card=0.0, mortgage_payment=2_000.0):
    debts = [Debt("Mortgage", 1_000_000.0, mortgage_payment, 0.05)]
    if card:
        debts.append(Debt("Credit card (Visa)", card, 0.0))
    return Finances(
        cash=[LineItem("Bank", cash)],
        investments=[],
        income=[LineItem("Job", income)] if income else [],
        expenses=[LineItem("Living", expenses)],
        debts=debts,
    )


class TestAggregates(unittest.TestCase):
    def test_burn_and_liquid(self):
        f = finances()
        self.assertEqual(f.monthly_burn, 10_000.0)  # 8k living + 2k mortgage
        self.assertEqual(f.liquid, 100_000.0)
        self.assertEqual(f.net_worth, 100_000.0 - 1_000_000.0)

    def test_credit_card_matching_is_name_based(self):
        f = finances(card=15_000.0)
        self.assertEqual(f.credit_card_used, 15_000.0)
        self.assertEqual(f.liquid_after_cards, 85_000.0)

    def test_income_reduces_burn_below_zero(self):
        f = finances(income=20_000.0)
        self.assertEqual(f.monthly_burn, -10_000.0)


class TestRunway(unittest.TestCase):
    def test_simple_runway(self):
        self.assertEqual(finances().runway_months(), 10.0)  # 100k / 10k

    def test_cash_flow_positive_is_indefinite(self):
        self.assertIsNone(finances(income=20_000.0).runway_months())

    def test_extra_income_and_cuts_extend_runway(self):
        f = finances()
        self.assertEqual(f.runway_months(extra_monthly_income=5_000.0), 20.0)
        self.assertEqual(f.runway_months(expense_cut=5_000.0), 20.0)
        self.assertIsNone(f.runway_months(extra_monthly_income=10_000.0))

    def test_cards_exceeding_liquid_is_zero_not_negative(self):
        f = finances(cash=10_000.0, card=25_000.0)
        self.assertEqual(f.liquid_after_cards, -15_000.0)
        self.assertEqual(f.runway_months(), 0.0)  # regression: used to be negative


class TestRequiredIncome(unittest.TestCase):
    def test_partial_income_closes_the_gap(self):
        # burn 10k, liquid 100k, target 20 months -> allowed burn 5k -> need 5k
        self.assertEqual(finances().required_income_for(20.0), 5_000.0)

    def test_already_sustainable_needs_nothing(self):
        f = finances(cash=500_000.0)
        self.assertEqual(f.required_income_for(SUSTAINABLE_RUNWAY_MONTHS), 0.0)

    def test_cash_flow_positive_needs_nothing(self):
        self.assertEqual(finances(income=20_000.0).required_income_for(18.0), 0.0)

    def test_zero_target_means_break_even(self):
        self.assertEqual(finances().required_income_for(0.0), 10_000.0)

    def test_no_liquid_degrades_to_break_even(self):
        # regression: negative liquid used to DEMAND MORE than break-even
        f = finances(cash=10_000.0, card=25_000.0)
        self.assertEqual(f.required_income_for(18.0), f.monthly_burn)
        g = finances(cash=0.0)
        self.assertEqual(g.required_income_for(18.0), g.monthly_burn)


class TestTargetsAndReport(unittest.TestCase):
    def test_build_targets_math(self):
        f = finances(cash=200_000.0)  # burn 10k
        plan = build_targets(f)
        self.assertEqual(plan.breakeven, 10_000.0)
        self.assertEqual(plan.target, round(11_000.0))
        expected_investable = 200_000.0 - SAFETY_BUFFER_MONTHS * 10_000.0
        self.assertEqual(plan.investable, round(expected_investable))
        self.assertEqual(plan.portfolio_monthly,
                         round(expected_investable * PORTFOLIO_RETURN_ASSUMPTION / 12.0))
        self.assertEqual(plan.income_target, round(11_000.0 - plan.portfolio_monthly))

    def test_targets_never_negative_when_buffer_eats_everything(self):
        plan = build_targets(finances(cash=50_000.0))  # buffer 120k > 50k liquid
        self.assertEqual(plan.investable, 0)
        self.assertEqual(plan.portfolio_monthly, 0)
        self.assertEqual(plan.income_target, plan.target)

    def test_targets_cash_flow_positive(self):
        plan = build_targets(finances(income=25_000.0))
        self.assertEqual(plan.breakeven, 0.0)
        self.assertEqual(plan.target, 0)
        self.assertEqual(plan.income_target, 0)

    def test_report_scenarios_are_consistent(self):
        f = finances()
        report = build_report(f)
        self.assertEqual(report.runway_months, 10.0)
        self.assertEqual(report.breakeven_income, 10_000.0)
        as_is = report.scenarios[0]
        self.assertEqual(as_is["label"], "As is")
        self.assertEqual(as_is["burn"], 10_000)
        self.assertEqual(as_is["runway_months"], 10.0)
        plus10 = next(s for s in report.scenarios if s["label"] == "+10 000 kr/mo income")
        self.assertIsNone(plus10["runway_months"])  # burn hits exactly 0 -> indefinite
        cut10 = next(s for s in report.scenarios if s["label"] == "Cut expenses 10%")
        self.assertEqual(cut10["burn"], 10_000 - 800)  # cut applies to expenses, not debt payments

    def test_report_income_for_sustainable(self):
        f = finances()  # runway 10 < 18 months
        report = build_report(f)
        # allowed burn = 100k / 18; requirement tops burn up to that level
        self.assertAlmostEqual(report.income_for_sustainable, 10_000.0 - 100_000.0 / 18.0, places=6)


class TestHolding(unittest.TestCase):
    def test_explicit_stop_wins(self):
        self.assertEqual(Holding("EQNR.OL", 10, cost_basis=300.0, stop_price=290.0).effective_stop, 290.0)

    def test_auto_stop_is_8_percent_below_cost(self):
        self.assertAlmostEqual(Holding("EQNR.OL", 10, cost_basis=100.0).effective_stop, 92.0)

    def test_no_cost_basis_means_no_stop(self):
        self.assertEqual(Holding("EQNR.OL", 10).effective_stop, 0.0)


if __name__ == "__main__":
    unittest.main()
