"""Load/save the personal finance file and import from Hanna's Excel budget.

The data file is v2/data/finances.json — gitignored, VPS-local, editable from
the dashboard. The Excel importer accepts the OneDrive workbook (exported or
copied onto the box) and maps its sheets into the same structure.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .model import Debt, Finances, Holding, LineItem

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "finances.json"

EMPTY_TEMPLATE = Finances(
    cash=[LineItem("Brukskonto", 0.0)],
    investments=[LineItem("Crypto (Firi)", 0.0)],
    income=[LineItem("NAV / dagpenger", 0.0)],
    expenses=[LineItem("Rent", 0.0), LineItem("Food", 0.0), LineItem("Other", 0.0)],
    debts=[Debt("Student loan (Lånekassen)", 0.0, 0.0, 0.0)],
    holdings=[],
)


def load(path: Path = DATA_PATH) -> Finances:
    if not path.exists():
        return EMPTY_TEMPLATE
    raw = json.loads(path.read_text())
    return Finances(
        currency=raw.get("currency", "NOK"),
        cash=[LineItem(**i) for i in raw.get("cash", [])],
        investments=[LineItem(**i) for i in raw.get("investments", [])],
        income=[LineItem(**i) for i in raw.get("income", [])],
        expenses=[LineItem(**i) for i in raw.get("expenses", [])],
        debts=[Debt(**d) for d in raw.get("debts", [])],
        holdings=[Holding(**h) for h in raw.get("holdings", [])],
    )


def save(finances: Finances, path: Path = DATA_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(finances), indent=2, ensure_ascii=False))


def import_excel(xlsx_path: str) -> Finances:
    """Best-effort import of a budget workbook: any sheet with name/amount-like
    columns becomes line items; sheet names route them to the right bucket."""
    import pandas as pd

    finances = load()
    book = pd.read_excel(xlsx_path, sheet_name=None)
    for sheet_name, frame in book.items():
        frame = frame.dropna(how="all")
        if frame.shape[1] < 2:
            continue
        name_col, amount_col = frame.columns[0], None
        for column in frame.columns[1:]:
            if pd.api.types.is_numeric_dtype(frame[column]):
                amount_col = column
                break
        if amount_col is None:
            continue
        items = [LineItem(str(row[name_col]), float(row[amount_col]))
                 for _, row in frame.iterrows()
                 if str(row[name_col]).strip() and pd.notna(row[amount_col])]
        lowered = sheet_name.lower()
        if any(k in lowered for k in ("income", "inntekt", "cash flow")):
            finances.income = items
        elif any(k in lowered for k in ("expense", "utgift", "budget", "budsjett", "kostnad")):
            finances.expenses = items
        elif any(k in lowered for k in ("debt", "gjeld", "loan", "lån")):
            finances.debts = [Debt(i.name, i.amount, 0.0, 0.0) for i in items]
        elif any(k in lowered for k in ("crypto", "invest", "portfolio", "portefølje")):
            finances.investments = items
        elif any(k in lowered for k in ("cash", "konto", "saving", "sparing")):
            finances.cash = items
    save(finances)
    return finances
