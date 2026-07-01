"""Ticker universes: which stocks the engine screens.

Universe CSVs live in v2/data/tickers/ (one Yahoo ticker per line), one per
market, refreshed from Yahoo's own screener (see universe_refresh.py) so the
symbols are exactly what yfinance can fetch. Which markets are ACTIVE (i.e.
screened daily and shown in the dashboard) is a config choice in
v2/data/config.json — screening every market on the planet daily would be
slow and rate-limited for no benefit.
"""
from __future__ import annotations

import json
from pathlib import Path

V2_ROOT = Path(__file__).resolve().parent.parent
TICKER_DIR = V2_ROOT / "data" / "tickers"
CONFIG_PATH = V2_ROOT / "data" / "config.json"

# name -> (csv file, Yahoo screener region, display label, benchmark note)
MARKETS: dict[str, dict] = {
    "oslo":        {"file": "OSLO.csv",        "region": "no", "label": "Oslo Børs 🇳🇴"},
    "sp500":       {"file": "SP500.csv",       "region": None, "label": "S&P 500 🇺🇸"},  # Wikipedia list
    "sweden":      {"file": "SWEDEN.csv",      "region": "se", "label": "Stockholm 🇸🇪"},
    "denmark":     {"file": "DENMARK.csv",     "region": "dk", "label": "Copenhagen 🇩🇰"},
    "finland":     {"file": "FINLAND.csv",     "region": "fi", "label": "Helsinki 🇫🇮"},
    "germany":     {"file": "GERMANY.csv",     "region": "de", "label": "Germany 🇩🇪"},
    "uk":          {"file": "UK.csv",          "region": "gb", "label": "London 🇬🇧"},
    "france":      {"file": "FRANCE.csv",      "region": "fr", "label": "Paris 🇫🇷"},
    "netherlands": {"file": "NETHERLANDS.csv", "region": "nl", "label": "Amsterdam 🇳🇱"},
    "canada":      {"file": "CANADA.csv",      "region": "ca", "label": "Toronto 🇨🇦"},
    "japan":       {"file": "JAPAN.csv",       "region": "jp", "label": "Tokyo 🇯🇵"},
    "hongkong":    {"file": "HONGKONG.csv",    "region": "hk", "label": "Hong Kong 🇭🇰"},
    "australia":   {"file": "AUSTRALIA.csv",   "region": "au", "label": "Sydney 🇦🇺"},
}
DEFAULT_ACTIVE = ["oslo", "sp500"]

# kept for backwards compatibility with universe_refresh
UNIVERSE_FILES = {name: m["file"] for name, m in MARKETS.items()}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"active_universes": list(DEFAULT_ACTIVE)}


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def active_universes() -> list[str]:
    active = [u for u in load_config().get("active_universes", DEFAULT_ACTIVE) if u in MARKETS]
    return active or list(DEFAULT_ACTIVE)


def available_universes() -> list[str]:
    return list(MARKETS)


def _read_symbols(path: Path) -> list[str]:
    if not path.exists():
        return []
    symbols = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "###" not in line:
            symbols.append(line)
    return symbols


def load_universe(name: str) -> list[str]:
    key = name.lower()
    if key not in MARKETS:
        raise ValueError(f"unknown universe {name!r}; available: {', '.join(MARKETS)}")
    symbols = _read_symbols(TICKER_DIR / MARKETS[key]["file"])
    blacklist = set(_read_symbols(TICKER_DIR / f"{key}.blacklist.txt"))
    return [s for s in symbols if s not in blacklist]


def load_universes(names: list[str]) -> dict[str, list[str]]:
    return {name: load_universe(name) for name in names}
