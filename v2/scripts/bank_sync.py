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
        # One balance per account: prefer "expected" (the real position).
        # "interimAvailable" on a credit card is the remaining credit LINE —
        # not money — so it must never win.
        per_account: dict = {}
        for b in client.balances():
            if b["type"] == "expected" or b["account"] not in per_account:
                per_account[b["account"]] = b
        finances = store.load()
        manual = [c for c in finances.cash if BANK_TAG not in c.name]
        synced = []
        for b in per_account.values():
            kind = " credit card" if b["amount"] < 0 else ""
            synced.append(LineItem(f"{b['institution'].split('_')[0]}{kind} {b['account'][:6]} {BANK_TAG}",
                                   b["amount"]))
        finances.cash = manual + synced
        store.save(finances)
        for item in synced:
            print(f"{item.name:<44} {item.amount:>12,.0f}")
        print(f"\n{len(synced)} accounts written; manual lines kept: {[c.name for c in manual]}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
