"""Bank sync scaffold: DNB / DNB Spare / Bank Norwegian via GoCardless
Bank Account Data (the free open-banking API the v1 net_worth code used).

Setup (one-time, needs Hanna):
  1. Create a free account at https://bankaccountdata.gocardless.com
  2. Generate a secret id + key, put them in v2/data/bank.json:
       {"secret_id": "...", "secret_key": "..."}
  3. Run: python scripts/bank_sync.py connect DNB_DNBANOKK
     -> prints a consent link; open it on the phone, approve in the bank.
  4. Daily: python scripts/bank_sync.py sync
     -> balances land in finances.json cash items tagged (bank),
        fresh transactions extend the habit analysis.

Institution ids: DNB retail = DNB_DNBANOKK, Bank Norwegian = NORWEGIAN_NO_NORWNOK1
(verify with `python scripts/bank_sync.py institutions no`). Consents last 90
days (PSD2), then step 3 again.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import requests

API = "https://bankaccountdata.gocardless.com/api/v2"
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "bank.json"


class BankClient:
    def __init__(self) -> None:
        if not CONFIG_PATH.exists():
            raise RuntimeError(f"no {CONFIG_PATH} — see module docstring for setup")
        self.config = json.loads(CONFIG_PATH.read_text())
        self._token: Optional[str] = None

    def _save(self) -> None:
        CONFIG_PATH.write_text(json.dumps(self.config, indent=2))
        CONFIG_PATH.chmod(0o600)

    def token(self) -> str:
        if self._token is None:
            response = requests.post(f"{API}/token/new/", timeout=30, json={
                "secret_id": self.config["secret_id"],
                "secret_key": self.config["secret_key"],
            })
            response.raise_for_status()
            self._token = response.json()["access"]
        return self._token

    def _get(self, path: str) -> dict:
        response = requests.get(f"{API}{path}", timeout=30,
                                headers={"Authorization": f"Bearer {self.token()}"})
        response.raise_for_status()
        return response.json()

    def institutions(self, country: str = "no") -> list[dict]:
        return self._get(f"/institutions/?country={country}")

    def create_requisition(self, institution_id: str) -> str:
        """Start a consent; returns the link Hanna opens to approve."""
        response = requests.post(f"{API}/requisitions/", timeout=30,
                                 headers={"Authorization": f"Bearer {self.token()}"},
                                 json={"redirect": "http://187.127.113.131:3400/finances",
                                       "institution_id": institution_id})
        response.raise_for_status()
        data = response.json()
        self.config.setdefault("requisitions", {})[institution_id] = data["id"]
        self._save()
        return data["link"]

    def balances(self) -> list[dict]:
        """Balance per connected account across all approved requisitions."""
        results = []
        for institution, requisition_id in self.config.get("requisitions", {}).items():
            requisition = self._get(f"/requisitions/{requisition_id}/")
            for account_id in requisition.get("accounts", []):
                data = self._get(f"/accounts/{account_id}/balances/")
                for balance in data.get("balances", []):
                    amount = balance.get("balanceAmount", {})
                    results.append({
                        "institution": institution,
                        "account": account_id,
                        "amount": float(amount.get("amount", 0)),
                        "currency": amount.get("currency"),
                        "type": balance.get("balanceType"),
                    })
        return results
