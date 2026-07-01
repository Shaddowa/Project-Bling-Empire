"""Ticker universes: which stocks the engine screens.

Universe CSVs live in v2/data/tickers/ (one ticker per line, Yahoo notation,
e.g. EQNR.OL). Blacklists in the repo root's blacklisted_stock_ticker/ are
honored so known-dead tickers are skipped.
"""
from __future__ import annotations

from pathlib import Path

V2_ROOT = Path(__file__).resolve().parent.parent
TICKER_DIR = V2_ROOT / "data" / "tickers"
# Optional manual exclusions, one ticker per line: data/tickers/<name>.blacklist.txt
# (the v1 auto-generated blacklists are NOT used: they encode the old fetcher's
# failures against a 2023 ticker list, not reality)
BLACKLIST_DIR = TICKER_DIR

UNIVERSE_FILES = {
    "oslo": "OSLO.csv",
    "sp500": "SP500.csv",
}
BLACKLIST_FILES = {
    "oslo": "oslo.blacklist.txt",
    "sp500": "sp500.blacklist.txt",
}


def available_universes() -> list[str]:
    return sorted(UNIVERSE_FILES)


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
    if key not in UNIVERSE_FILES:
        raise ValueError(f"unknown universe {name!r}; available: {', '.join(available_universes())}")
    symbols = _read_symbols(TICKER_DIR / UNIVERSE_FILES[key])
    blacklisted = set(_read_symbols(BLACKLIST_DIR / BLACKLIST_FILES.get(key, "")))
    return [s for s in symbols if s not in blacklisted]


def load_universes(names: list[str]) -> dict[str, list[str]]:
    return {name: load_universe(name) for name in names}
