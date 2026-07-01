"""Bank transaction import ("Siste transaksjoner" export from the bank).

The export is a single hub account: salary/inflows land here and spending
leaves via card purchases AND transfers to other accounts/cards
("Overføring", "Kontoregulering"). Net flow ≈ 0 every month, so the number
that matters is the OUTFLOW — that's the real spending rate the runway
model needs. Balances are not in the export; Hanna enters those by hand.

Parsed result is cached to v2/data/transactions.json for the dashboard.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "transactions.json"

TRANSFER_PATTERN = "Overføring|Kontoregulering|Egen konto"
SALARY_PATTERN = "Lønn"
CATEGORY_RULES = [
    ("groceries", "Meny|Rema|Kiwi|Coop|Extra |Bunnpris|Joker|Spar |Obs |Meny|matbutikk"),
    ("food out", "Pizza|Restaurant|Cafe|Kafe|Burger|Sushi|Kebab|McDonald|Espresso|Deli"),
    ("transport", "Ruter|Vy |Flytoget|Taxi|Bolt|Uber|Voi|Tier"),
    ("crypto/investing", "Firi|Fondshandel|Verdipapir|Nordnet|Coinbase"),
    ("subscriptions/mobile", "Netflix|Spotify|Apple|Google|iCloud|Mobil|Telenor|Telia|Ice[ .]"),
]


def parse_export(xlsx_path: str) -> dict:
    frame = pd.read_excel(xlsx_path)
    frame.columns = ["date", "desc", "interest_date", "out", "in"][: len(frame.columns)]
    frame["date"] = pd.to_datetime(frame["date"])
    frame["out"] = frame["out"].fillna(0.0)
    frame["in"] = frame["in"].fillna(0.0)
    frame["month"] = frame["date"].dt.to_period("M").astype(str)

    is_transfer = frame["desc"].str.contains(TRANSFER_PATTERN, case=False, na=False)
    is_salary = frame["desc"].str.contains(SALARY_PATTERN, case=False, na=False)

    months = []
    for month, rows in frame.groupby("month"):
        transfers = is_transfer.loc[rows.index]
        salary = is_salary.loc[rows.index]
        months.append({
            "month": month,
            "out": round(float(rows["out"].sum())),
            "in": round(float(rows["in"].sum())),
            "net": round(float(rows["in"].sum() - rows["out"].sum())),
            "salary": round(float(rows.loc[salary, "in"].sum())),
            "card_spend": round(float(rows.loc[~transfers, "out"].sum())),
        })
    months.sort(key=lambda m: m["month"])

    # Category breakdown of direct (non-transfer) spending, whole period.
    categories = {}
    direct = frame[~is_transfer & (frame["out"] > 0)]
    remaining = direct
    for name, pattern in CATEGORY_RULES:
        hit = remaining["desc"].str.contains(pattern, case=False, na=False)
        categories[name] = round(float(remaining.loc[hit, "out"].sum()))
        remaining = remaining[~hit]
    categories["other"] = round(float(remaining["out"].sum()))

    # Habit-based burn estimate, deliberately rough. The median outflow of
    # no-salary months is "how she actually lives"; months far above it are
    # one-offs (moves, repositioning), listed but not baked into the habit.
    current_month = datetime.now().strftime("%Y-%m")
    full_months = [m for m in months if m["month"] != current_month]
    jobless = [m for m in full_months if m["salary"] == 0][-8:]
    basis = jobless if len(jobless) >= 2 else full_months[-3:]
    outs = sorted(m["out"] for m in basis)
    median = outs[len(outs) // 2] if len(outs) % 2 else (outs[len(outs)//2 - 1] + outs[len(outs)//2]) / 2
    rough_burn = int(round(median / 1000.0)) * 1000 if outs else 0
    irregular = [m["month"] for m in basis if m["out"] > 1.6 * median] if median else []
    avg_burn = round(sum(outs) / len(outs)) if outs else 0

    salary_months = [m for m in months if m["salary"] > 0]
    typical_salary = 0
    if salary_months:
        pays = sorted(m["salary"] for m in salary_months)
        typical_salary = int(round(pays[len(pays) // 2] / 1000.0)) * 1000

    result = {
        "source": Path(xlsx_path).name,
        "imported_at": datetime.now().isoformat(timespec="seconds"),
        "first_date": str(frame["date"].min().date()),
        "last_date": str(frame["date"].max().date()),
        "transaction_count": int(len(frame)),
        "months": months,
        "categories": categories,
        "rough_burn": rough_burn,          # the habit: ~median no-salary month
        "avg_burn": avg_burn,              # mean, kept for reference
        "irregular_months": irregular,     # one-offs excluded from the habit
        "burn_basis_months": [m["month"] for m in basis],
        "last_salary_month": max((m["month"] for m in salary_months), default=None),
        "typical_salary": typical_salary,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(result, indent=2))
    return result


def load() -> dict | None:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text())
    return None
