"""Phone push notifications via ntfy.sh.

The WV server's /v1/push/test route 404s in prod (removed with the X-User-ID
auth hardening), and the orchestrator's pushes have been silently failing the
same way — so the dashboard uses ntfy instead: POST to a private random topic,
Hanna subscribes to that topic in the ntfy app (iOS/Android) and gets pushes.

Topic lives in v2/data/notify.json (gitignored; the topic name IS the secret).
"""
from __future__ import annotations

import json
import secrets
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "notify.json"
NTFY_BASE = "https://ntfy.sh"
DASHBOARD_URL = "https://bling.whispervault.app"


def get_topic() -> str:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())["ntfy_topic"]
    topic = f"bling-hanna-{secrets.token_urlsafe(12)}"
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"ntfy_topic": topic}, indent=2))
    CONFIG_PATH.chmod(0o600)
    return topic


def push(title: str, body: str, url: str = "/") -> bool:
    request = urllib.request.Request(
        f"{NTFY_BASE}/{get_topic()}",
        data=body[:1000].encode(),
        headers={
            "Title": title[:120].encode("ascii", "ignore").decode(),  # header must be latin-safe
            "Click": f"{DASHBOARD_URL}{url}",
            "Tags": "moneybag",
            "Priority": "high",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status == 200
    except Exception:
        return False
