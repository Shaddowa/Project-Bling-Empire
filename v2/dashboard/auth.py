"""Single-user auth with stdlib only: PBKDF2 password hash + HMAC-signed
session cookie. Credentials live in v2/data/auth.json (gitignored)."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Optional

AUTH_PATH = Path(__file__).resolve().parent.parent / "data" / "auth.json"
SESSION_TTL_SECONDS = 30 * 24 * 3600  # a month; it's her own phone
PBKDF2_ITERATIONS = 600_000
COOKIE_NAME = "bling_session"


def _load() -> Optional[dict]:
    if AUTH_PATH.exists():
        return json.loads(AUTH_PATH.read_text())
    return None


def initialize_password(password: str) -> None:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS).hex()
    AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTH_PATH.write_text(json.dumps({
        "salt": salt,
        "hash": digest,
        "iterations": PBKDF2_ITERATIONS,
        "cookie_secret": secrets.token_hex(32),
    }))
    AUTH_PATH.chmod(0o600)


def verify_password(password: str) -> bool:
    auth = _load()
    if auth is None:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(auth["salt"]), auth["iterations"]).hex()
    return hmac.compare_digest(digest, auth["hash"])


def issue_session() -> str:
    auth = _load()
    expiry = str(int(time.time()) + SESSION_TTL_SECONDS)
    signature = hmac.new(bytes.fromhex(auth["cookie_secret"]), expiry.encode(), "sha256").hexdigest()
    return f"{expiry}.{signature}"


def widget_token() -> str:
    """Long-lived read-only token for home-screen widgets (Scriptable)."""
    auth = _load()
    if "widget_token" not in auth:
        auth["widget_token"] = secrets.token_urlsafe(24)
        AUTH_PATH.write_text(json.dumps(auth))
        AUTH_PATH.chmod(0o600)
    return auth["widget_token"]


def verify_widget_token(token: Optional[str]) -> bool:
    auth = _load()
    return bool(auth and token and hmac.compare_digest(token, auth.get("widget_token", "")))


def verify_session(token: Optional[str]) -> bool:
    auth = _load()
    if auth is None or not token or "." not in token:
        return False
    expiry, signature = token.split(".", 1)
    expected = hmac.new(bytes.fromhex(auth["cookie_secret"]), expiry.encode(), "sha256").hexdigest()
    return hmac.compare_digest(signature, expected) and int(expiry) > time.time()
