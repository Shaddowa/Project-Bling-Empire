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
DASHBOARD_URL = "http://187.127.113.131:3400"  # orchestrator-style: own port, no DNS


# What gets pushed. "Action" events (buys/sells) default ON.
DEFAULT_PREFS = {
    "longterm_buy": True,    # 🟢 stock newly qualifies as long-term BUY
    "holding_sell": True,    # 🔴 sell guidance flips on a stock you hold
    "swing_buy": True,       # 〰 fresh swing setups (grouped, one push)
    "watch": True,           # 👀 new WATCH names (grouped)
    "runway_monthly": True,  # 🏦 runway status on the 1st
}


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    CONFIG_PATH.chmod(0o600)


def get_topic() -> str:
    config = _load_config()
    if "ntfy_topic" in config:
        return config["ntfy_topic"]
    config["ntfy_topic"] = f"bling-hanna-{secrets.token_urlsafe(12)}"
    _save_config(config)
    return config["ntfy_topic"]


def get_prefs() -> dict:
    return {**DEFAULT_PREFS, **_load_config().get("prefs", {})}


def save_prefs(prefs: dict) -> None:
    config = _load_config()
    config["prefs"] = {key: bool(prefs.get(key)) for key in DEFAULT_PREFS}
    _save_config(config)


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
