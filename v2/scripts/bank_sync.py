"""CLI for the GoCardless bank sync (see bling/finance/bank.py docstring).

    python scripts/bank_sync.py institutions no       # find institution ids
    python scripts/bank_sync.py connect DNB_DNBANOKK  # print consent link
    python scripts/bank_sync.py sync                  # balances -> finances.json
"""
from __future__ import annotations

import sys
from pathlib import Path

V2_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_ROOT))

from bling.finance import store  # noqa: E402
from bling.finance.bank import BankClient  # noqa: E402
from bling.finance.model import LineItem  # noqa: E402

BANK_TAG = "(bank)"


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "sync"
    client = BankClient()

    if command == "institutions":
        for inst in client.institutions(sys.argv[2] if len(sys.argv) > 2 else "no"):
            print(f"{inst['id']:<30} {inst['name']}")
    elif command == "connect":
        link = client.create_requisition(sys.argv[2])
        print("Open this on your phone and approve in the bank:\n" + link)
    elif command == "sync":
        balances = [b for b in client.balances() if b["type"] in ("expected", "interimAvailable", None)]
        finances = store.load()
        manual = [c for c in finances.cash if BANK_TAG not in c.name]
        synced = [LineItem(f"{b['institution']} {b['account'][:6]} {BANK_TAG}", b["amount"])
                  for b in balances]
        finances.cash = manual + synced
        store.save(finances)
        for b in balances:
            print(f"{b['institution']:<24} {b['amount']:>12,.0f} {b['currency']}")
        print(f"\n{len(synced)} bank balances written to finances.json")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
