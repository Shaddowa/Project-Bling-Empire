"""Unit tests for the investment policy (bling/policy.py) and its enforcement
hook in ledger.record_trade.

Everything runs against a temp ledger file with injected finances / prices /
fx rates / sticker prices — no network, no bundle cache, no touching Hanna's
real v2/data files.
"""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from bling import ledger, policy
from bling.finance.model import Finances, LineItem

# Hanna-shaped numbers: 163k liquid, 10k/mo burn -> 12-month buffer 120k ->
# investable 43 000 kr; max position 10 750; monthly deploy cap 21 500.
def hanna_finances() -> Finances:
    return Finances(cash=[LineItem("bank", 163_000.0)],
                    expenses=[LineItem("life", 10_000.0)])


# Permissive context for SEEDING trades (the policy under test must not block
# the fixtures that set the stage).
PERMISSIVE = {"finances": Finances(cash=[LineItem("x", 1e9)]),
              "prices": {}, "fx_rates": {}, "sticker_price": None}


class PolicyCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "ledger.jsonl"
        self.addCleanup(self._tmp.cleanup)

    def ctx(self, **overrides):
        base = {"finances": hanna_finances(), "prices": {}, "fx_rates": {},
                "sticker_price": None, "path": self.path}
        base.update(overrides)
        return base

    def check(self, ticker="NEW.OL", side="BUY", shares=10, price=100.0,
              date="2026-07-02", **overrides):
        return policy.check_trade(ticker, side, shares, price, date=date,
                                  **self.ctx(**overrides))

    def rules_hit(self, violations):
        return {v["rule"] for v in violations if v["severity"] == "block"}

    def seed_buy(self, ticker, shares, price, day, mode="longterm"):
        # override=True: fixtures set the stage, the policy under test must
        # never block them (e.g. seeding a 6th position on purpose)
        ledger.record_trade(ticker, "BUY", shares, price, date=day, mode=mode,
                            currency="NOK", path=self.path, override=True,
                            policy_context=PERMISSIVE)

    def seed_stop_out(self, ticker, buy_day, sell_day, loss_pct=8.0):
        """One realized round trip losing loss_pct% (a stop-out at 8%)."""
        self.seed_buy(ticker, 10, 100.0, buy_day)
        ledger.record_trade(ticker, "SELL", 10, 100.0 - loss_pct,
                            date=sell_day, currency="NOK", path=self.path)


class TestTradingDays(unittest.TestCase):
    def test_weekdays_only(self):
        friday = date(2026, 7, 10)
        self.assertEqual(policy.add_trading_days(friday, 5), date(2026, 7, 17))
        wednesday = date(2026, 7, 1)
        self.assertEqual(policy.add_trading_days(wednesday, 5), date(2026, 7, 8))
        self.assertEqual(policy.add_trading_days(friday, 1), date(2026, 7, 13))  # Monday


class TestCheckTrade(PolicyCase):
    def test_clean_buy_passes(self):
        violations = self.check(shares=10, price=100.0, sticker_price=150.0)
        self.assertEqual(violations, [])

    def test_sell_is_never_checked(self):
        # even with an empty position and zero investable, SELLs pass the policy
        # (the FIFO oversell guard is the ledger's own, separate check)
        violations = policy.check_trade("ANY.OL", "SELL", 10, 100.0,
                                        date="2026-07-02",
                                        **self.ctx(finances=Finances()))
        self.assertEqual(violations, [])

    def test_max_open_positions(self):
        for n in range(5):
            self.seed_buy(f"POS{n}.OL", 10, 10.0, "2026-06-15")
        violations = self.check(ticker="SIXTH.OL", shares=10, price=100.0,
                                sticker_price=150.0)
        self.assertEqual(self.rules_hit(violations), {"max_open_positions"})
        # adding to a name already held is NOT a new position
        ok = self.check(ticker="POS0.OL", shares=10, price=10.0,
                        sticker_price=150.0)
        self.assertEqual(ok, [])

    def test_max_position_size_single_buy(self):
        # 200 * 60 = 12 000 kr > 25% of 43 000 investable (10 750 kr)
        violations = self.check(shares=200, price=60.0, sticker_price=150.0)
        self.assertEqual(self.rules_hit(violations), {"max_position_size"})
        self.assertIn("25%", violations[0]["message"])

    def test_max_position_size_counts_existing_position(self):
        self.seed_buy("NEW.OL", 60, 100.0, "2026-06-15")   # 6 000 kr held
        # +5 000 kr -> 11 000 kr total > 10 750 cap
        violations = self.check(shares=50, price=100.0, sticker_price=150.0)
        self.assertIn("max_position_size", self.rules_hit(violations))
        # a smaller top-up stays under the cap
        ok = self.check(shares=40, price=100.0, sticker_price=150.0)
        self.assertEqual(ok, [])

    def test_zero_investable_blocks_everything(self):
        broke = Finances(cash=[LineItem("bank", 50_000.0)],
                         expenses=[LineItem("life", 10_000.0)])  # buffer eats it
        violations = self.check(shares=1, price=10.0, finances=broke,
                                sticker_price=150.0)
        self.assertIn("max_position_size", self.rules_hit(violations))
        self.assertIn("safety buffer", violations[0]["message"])

    def test_above_sticker_blocks(self):
        violations = self.check(shares=10, price=120.0, sticker_price=100.0)
        self.assertEqual(self.rules_hit(violations), {"above_sticker"})

    def test_unknown_sticker_warns_but_does_not_block(self):
        violations = self.check(shares=10, price=100.0, sticker_price=None)
        self.assertEqual(self.rules_hit(violations), set())
        warns = [v for v in violations if v["severity"] == "warn"]
        self.assertEqual([v["rule"] for v in warns], ["sticker_unknown"])

    # ── cooldown ────────────────────────────────────────────────────────
    def test_cooldown_after_two_stop_outs_within_window(self):
        self.seed_stop_out("A.OL", "2026-06-20", "2026-07-01")
        self.seed_stop_out("B.OL", "2026-06-25", "2026-07-10")   # 9 days later
        # Fri 2026-07-10 + 5 trading days -> blocked through Fri 2026-07-17
        blocked = self.check(date="2026-07-15", sticker_price=150.0)
        self.assertIn("cooldown", self.rules_hit(blocked))
        self.assertIn("2026-07-17", blocked[0]["message"])
        self.assertIn("revenge-trading", blocked[0]["message"])
        on_the_day = self.check(date="2026-07-10", sticker_price=150.0)
        self.assertIn("cooldown", self.rules_hit(on_the_day))
        after = self.check(date="2026-07-20", sticker_price=150.0)  # next Monday
        self.assertEqual(self.rules_hit(after), set())

    def test_no_cooldown_when_stop_outs_are_spread_out(self):
        self.seed_stop_out("A.OL", "2026-05-20", "2026-06-05")
        self.seed_stop_out("B.OL", "2026-06-20", "2026-07-01")   # 26 days later
        violations = self.check(date="2026-07-02", sticker_price=150.0)
        self.assertEqual(self.rules_hit(violations), set())

    def test_single_stop_out_or_small_loss_is_no_cooldown(self):
        self.seed_stop_out("A.OL", "2026-06-20", "2026-07-01")
        self.seed_stop_out("B.OL", "2026-06-25", "2026-07-10", loss_pct=3.0)  # not a stop
        violations = self.check(date="2026-07-13", sticker_price=150.0)
        self.assertEqual(self.rules_hit(violations), set())

    # ── drawdown circuit breaker ────────────────────────────────────────
    def test_breaker_on_aggregate_drawdown(self):
        self.seed_buy("A.OL", 10, 100.0, "2026-06-15")
        blocked = self.check(prices={"A.OL": 85.0}, sticker_price=150.0)  # -15%
        self.assertEqual(self.rules_hit(blocked), {"drawdown_breaker"})
        ok = self.check(prices={"A.OL": 95.0}, sticker_price=150.0)       # -5%
        self.assertEqual(self.rules_hit(ok), set())

    def test_breaker_is_aggregate_not_per_position(self):
        self.seed_buy("A.OL", 10, 100.0, "2026-06-15")
        self.seed_buy("B.OL", 10, 100.0, "2026-06-15")
        # A -25%, B +10% -> aggregate -7.5%: no breaker
        ok = self.check(prices={"A.OL": 75.0, "B.OL": 110.0}, sticker_price=150.0)
        self.assertEqual(self.rules_hit(ok), set())
        # A -25%, B -5% -> aggregate -15%: breaker
        blocked = self.check(prices={"A.OL": 75.0, "B.OL": 95.0}, sticker_price=150.0)
        self.assertEqual(self.rules_hit(blocked), {"drawdown_breaker"})

    def test_unpriced_positions_do_not_trip_breaker(self):
        self.seed_buy("A.OL", 10, 100.0, "2026-06-15")
        ok = self.check(prices={}, sticker_price=150.0)  # no price -> no verdict
        self.assertEqual(self.rules_hit(ok), set())

    # ── monthly deploy cap ──────────────────────────────────────────────
    def test_monthly_deploy_cap(self):
        self.seed_buy("A.OL", 100, 150.0, "2026-07-01")   # 15 000 kr this month
        # +10 000 -> 25 000 > 21 500 cap
        blocked = self.check(ticker="B.OL", shares=100, price=100.0,
                             date="2026-07-02", sticker_price=150.0)
        self.assertEqual(self.rules_hit(blocked), {"monthly_deploy_cap"})
        # same buy in a fresh month is fine
        ok = self.check(ticker="B.OL", shares=100, price=100.0,
                        date="2026-08-03", sticker_price=150.0)
        self.assertEqual(self.rules_hit(ok), set())

    def test_multiple_violations_reported_together(self):
        for n in range(5):
            self.seed_buy(f"POS{n}.OL", 10, 10.0, "2026-06-15")
        self.seed_stop_out("A.OL", "2026-06-20", "2026-06-29")
        self.seed_stop_out("B.OL", "2026-06-22", "2026-07-01")
        violations = self.check(ticker="SIXTH.OL", shares=200, price=120.0,
                                date="2026-07-02", sticker_price=100.0)
        self.assertEqual(self.rules_hit(violations),
                         {"max_open_positions", "max_position_size",
                          "above_sticker", "cooldown", "monthly_deploy_cap"})


class TestPolicyStatus(PolicyCase):
    def test_quiet_state(self):
        status = policy.policy_status(date="2026-07-02", finances=hanna_finances(),
                                      prices={}, fx_rates={}, path=self.path)
        self.assertEqual(status["investable"], 43_000)
        self.assertEqual(status["max_position_nok"], 10_750)
        self.assertEqual(status["open_positions"], 0)
        self.assertEqual(status["positions_left"], 5)
        self.assertFalse(status["cooldown_active"])
        self.assertIsNone(status["cooldown_until"])
        self.assertFalse(status["breaker_active"])
        self.assertFalse(status["buys_paused"])
        self.assertEqual(status["monthly_cap_nok"], 21_500)
        self.assertEqual(status["monthly_left_nok"], 21_500)
        self.assertEqual(len(status["rules"]), 7)

    def test_active_cooldown_and_breaker_state(self):
        self.seed_stop_out("A.OL", "2026-06-20", "2026-07-01")
        self.seed_stop_out("B.OL", "2026-06-25", "2026-07-10")
        self.seed_buy("C.OL", 10, 100.0, "2026-07-06")
        status = policy.policy_status(date="2026-07-15", finances=hanna_finances(),
                                      prices={"C.OL": 85.0}, fx_rates={},
                                      path=self.path)
        self.assertTrue(status["cooldown_active"])
        self.assertEqual(status["cooldown_until"], "2026-07-17")
        self.assertTrue(status["breaker_active"])
        self.assertEqual(status["drawdown_pct"], -15.0)
        self.assertTrue(status["buys_paused"])
        self.assertEqual(status["open_positions"], 1)
        self.assertEqual(status["monthly_deployed_nok"], 1_000)


class TestLedgerEnforcement(PolicyCase):
    def hook_ctx(self, **overrides):
        """Policy context for record_trade — record_trade passes the ledger
        path itself, so the context must not carry one."""
        context = self.ctx(**overrides)
        context.pop("path")
        return context

    def test_violating_buy_is_blocked_and_not_recorded(self):
        with self.assertRaises(policy.PolicyViolationError) as caught:
            ledger.record_trade("NEW.OL", "BUY", 200, 60.0, date="2026-07-02",
                                path=self.path,
                                policy_context=self.hook_ctx(sticker_price=150.0))
        self.assertEqual([v["rule"] for v in caught.exception.violations],
                         ["max_position_size"])
        self.assertEqual(ledger.trades(path=self.path), [])

    def test_override_records_trade_with_accountability_stamp(self):
        record = ledger.record_trade("NEW.OL", "BUY", 200, 60.0, date="2026-07-02",
                                     override=True, path=self.path,
                                     policy_context=self.hook_ctx(sticker_price=150.0))
        self.assertTrue(record["override"])
        self.assertEqual(record["policy_violations"], ["max_position_size"])
        line = json.loads(self.path.read_text().splitlines()[-1])
        self.assertTrue(line["override"])   # persisted, not just returned
        self.assertEqual(line["policy_violations"], ["max_position_size"])

    def test_clean_buy_records_without_stamp(self):
        record = ledger.record_trade("NEW.OL", "BUY", 10, 100.0, date="2026-07-02",
                                     path=self.path,
                                     policy_context=self.hook_ctx(sticker_price=150.0))
        self.assertNotIn("override", record)
        self.assertNotIn("policy_violations", record)

    def test_warn_only_violations_do_not_block(self):
        record = ledger.record_trade("NEW.OL", "BUY", 10, 100.0, date="2026-07-02",
                                     path=self.path,
                                     policy_context=self.hook_ctx(sticker_price=None))
        self.assertEqual(record["side"], "BUY")      # sticker_unknown is a warn
        self.assertNotIn("override", record)

    def test_sell_allowed_during_cooldown(self):
        self.seed_stop_out("A.OL", "2026-06-20", "2026-07-01")
        self.seed_stop_out("B.OL", "2026-06-25", "2026-07-10")
        self.seed_buy("C.OL", 10, 100.0, "2026-06-01")
        record = ledger.record_trade("C.OL", "SELL", 10, 105.0, date="2026-07-15",
                                     path=self.path)  # no context needed: no check
        self.assertEqual(record["side"], "SELL")

    def test_override_false_by_default(self):
        self.seed_stop_out("A.OL", "2026-06-20", "2026-07-01")
        self.seed_stop_out("B.OL", "2026-06-25", "2026-07-10")
        with self.assertRaises(policy.PolicyViolationError):
            ledger.record_trade("NEW.OL", "BUY", 5, 100.0, date="2026-07-15",
                                path=self.path,
                                policy_context=self.hook_ctx(sticker_price=150.0))


if __name__ == "__main__":
    unittest.main()
