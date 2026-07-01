"""Phone push notifications, reusing the Whisper Vault PWA push channel that
already reaches Hanna's device (same endpoint the orchestrator's
workflow-notify uses)."""
from __future__ import annotations

import json
import urllib.request

API_BASE = "https://whisper-vault-prod-api.onrender.com/api"
ADMIN_USER_ID = "f1400362-eb3f-4348-a32d-8e121c722b44"  # Hanna


def push(title: str, body: str, url: str = "/") -> bool:
    payload = json.dumps({"title": title[:80], "body": body[:240], "url": url}).encode()
    request = urllib.request.Request(
        f"{API_BASE}/v1/push/test",
        data=payload,
        headers={"Content-Type": "application/json", "X-User-ID": ADMIN_USER_ID},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode() or "{}")
            return response.status == 200 and (result.get("sent") or 0) > 0
    except Exception:
        return False
