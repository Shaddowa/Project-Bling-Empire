"""Import a bank transaction export and wire its burn estimate into the
runway model.

    python scripts/import_transactions.py "/root/Siste transaksjoner.xlsx"

Sets the auto expense line to the measured average monthly outflow (only
touches line items marked (auto) — Hanna's manual entries are preserved).
"""
from __future__ import annotations

import sys
from pathlib import Path

V2_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_ROOT))

from bling.finance import store, transactions  # noqa: E402
from bling.finance.model import LineItem, build_report  # noqa: E402

AUTO_TAG = "(auto from bank)"


def main(xlsx_path: str) -> None:
    result = transactions.parse_export(xlsx_path)
    print(f"parsed {result['transaction_count']} transactions "
          f"{result['first_date']} → {result['last_date']}")
    print(f"last salary: {result['last_salary_month']} (typical ~{result['typical_salary']:,} kr)")
    print(f"habit burn: ~{result['rough_burn']:,} kr/mo (median no-salary month; "
          f"mean {result['avg_burn']:,}; irregular: {', '.join(result['irregular_months']) or '—'})")

    finances = store.load()
    manual_expenses = [e for e in finances.expenses if AUTO_TAG not in e.name and e.amount]
    finances.expenses = manual_expenses + [
        LineItem(f"Levekostnader, nomad-modus {AUTO_TAG}", float(result["rough_burn"]))
    ]
    # Jobless months in the data -> zero out placeholder income rows that were
    # never filled in; keep any real (non-zero) income Hanna entered.
    finances.income = [i for i in finances.income if i.amount]
    store.save(finances)

    report = build_report(finances)
    runway = "∞" if report.runway_months is None else f"{report.runway_months} mo"
    print(f"\nrunway model updated: burn {report.monthly_burn:,.0f} kr/mo, "
          f"liquid {report.liquid:,.0f} kr → runway {runway}")
    if report.liquid == 0:
        print("NOTE: liquid is 0 — enter account balances on /finances for a real runway number.")


if __name__ == "__main__":
    main(sys.argv[1])
