import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import pandas as pd

from bling.finance import transactions


def write_xlsx(path: Path, rows: list[tuple], extra_columns: int = 0, drop_columns: int = 0):
    columns = ["Dato", "Beskrivelse", "Rentedato", "Ut fra konto", "Inn på konto"]
    frame = pd.DataFrame(rows, columns=columns)
    for i in range(extra_columns):
        frame[f"Extra{i}"] = ""
    if drop_columns:
        frame = frame.iloc[:, :-drop_columns]
    frame.to_excel(path, index=False, engine="openpyxl")
    return str(path)


ROWS = [
    # March: salary month
    ("2026-03-01", "Lønn Acme AS", "2026-03-01", None, 30_000.0),
    ("2026-03-03", "Rema 1000 Oslo", "2026-03-03", 900.0, None),
    ("2026-03-05", "Overføring til sparekonto", "2026-03-05", 5_000.0, None),
    ("2026-03-10", "Netflix.com", "2026-03-10", 149.0, None),
    # April: no salary
    ("2026-04-02", "Kiwi Grünerløkka", "2026-04-02", 1_200.0, None),
    ("2026-04-07", "Burger joint", "2026-04-07", 300.0, None),
    ("2026-04-15", "Kontoregulering", "2026-04-15", 2_000.0, None),
    ("2026-04-20", "Vy app", "2026-04-20", 500.0, None),
    # May: no salary
    ("2026-05-04", "Coop Mega", "2026-05-04", 2_500.0, None),
    ("2026-05-09", "Ukjent butikk", "2026-05-09", 700.0, None),
    ("2026-05-13", "Firi AS", "2026-05-13", 1_000.0, None),
]


class TransactionsBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # NEVER write to the real v2/data/ during tests.
        patcher = mock.patch.object(transactions, "DATA_PATH", self.tmp / "transactions.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)


class TestParseExport(TransactionsBase):
    def parse(self, rows=ROWS, **kwargs):
        return transactions.parse_export(write_xlsx(self.tmp / "export.xlsx", rows, **kwargs))

    def test_monthly_rollup(self):
        result = self.parse()
        months = {m["month"]: m for m in result["months"]}
        self.assertEqual(sorted(months), ["2026-03", "2026-04", "2026-05"])
        march = months["2026-03"]
        self.assertEqual(march["salary"], 30_000)
        self.assertEqual(march["in"], 30_000)
        self.assertEqual(march["out"], 6_049)
        self.assertEqual(march["net"], 30_000 - 6_049)
        # card spend excludes the transfer
        self.assertEqual(march["card_spend"], 1_049)
        april = months["2026-04"]
        self.assertEqual(april["salary"], 0)
        self.assertEqual(april["card_spend"], 2_000)  # Kontoregulering excluded

    def test_categories_cover_direct_spend_once(self):
        result = self.parse()
        cats = result["categories"]
        self.assertEqual(cats["groceries"], 900 + 1_200 + 2_500)
        self.assertEqual(cats["food out"], 300)
        self.assertEqual(cats["transport"], 500)
        self.assertEqual(cats["crypto/investing"], 1_000)
        self.assertEqual(cats["subscriptions/mobile"], 149)
        self.assertEqual(cats["other"], 700)
        # every direct krone lands in exactly one bucket
        direct_total = 900 + 1_200 + 2_500 + 300 + 500 + 1_000 + 149 + 700
        self.assertEqual(sum(cats.values()), direct_total)

    def test_burn_habit_uses_no_salary_months(self):
        result = self.parse()
        self.assertEqual(sorted(result["burn_basis_months"]), ["2026-04", "2026-05"])
        # outs: April 4000, May 4200 -> median 4100 -> rounded to 4000
        self.assertEqual(result["rough_burn"], 4_000)
        self.assertEqual(result["avg_burn"], 4_100)
        self.assertEqual(result["irregular_months"], [])

    def test_salary_summary(self):
        result = self.parse()
        self.assertEqual(result["typical_salary"], 30_000)
        self.assertEqual(result["last_salary_month"], "2026-03")

    def test_result_is_cached_to_patched_path(self):
        result = self.parse()
        on_disk = json.loads((self.tmp / "transactions.json").read_text())
        self.assertEqual(on_disk["transaction_count"], result["transaction_count"])
        self.assertEqual(on_disk["rough_burn"], result["rough_burn"])

    def test_current_month_only_export_does_not_crash(self):
        # regression: median of an empty basis used to raise IndexError
        month = datetime.now().strftime("%Y-%m")
        rows = [(f"{month}-01", "Rema 1000", f"{month}-01", 800.0, None),
                (f"{month}-02", "Kiwi", f"{month}-02", 400.0, None)]
        result = self.parse(rows=rows)
        self.assertEqual(result["rough_burn"], 0)
        self.assertEqual(result["avg_burn"], 0)
        self.assertEqual(result["burn_basis_months"], [])

    def test_extra_trailing_columns_are_tolerated(self):
        result = self.parse(extra_columns=2)
        self.assertEqual(result["transaction_count"], len(ROWS))

    def test_too_few_columns_raise_a_clear_error(self):
        with self.assertRaises(ValueError):
            self.parse(drop_columns=1)

    def test_empty_export_raises(self):
        with self.assertRaises(ValueError):
            self.parse(rows=[])

    def test_date_span(self):
        result = self.parse()
        self.assertEqual(result["first_date"], "2026-03-01")
        self.assertEqual(result["last_date"], "2026-05-13")


class TestLoad(TransactionsBase):
    def test_load_round_trip(self):
        self.assertIsNone(transactions.load())
        transactions.DATA_PATH.write_text(json.dumps({"rough_burn": 4000}))
        self.assertEqual(transactions.load(), {"rough_burn": 4000})


if __name__ == "__main__":
    unittest.main()
