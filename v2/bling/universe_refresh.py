"""Regenerate the universe ticker CSVs from live sources.

The committed CSVs go stale (the v1 Oslo list was from ~2023: Bouvet had
moved to BOUV.OL, DOF relisted as DOFG.OL, ...). Refreshing pulls:

  oslo   - Yahoo's own equity screener, region NO / exchange OSL, so symbols
           are exactly what yfinance can fetch. Includes Euronext Growth.
  sp500  - the canonical Wikipedia constituents table.
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from .universe import TICKER_DIR, UNIVERSE_FILES

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
PAGE_SIZE = 250
MIN_DAY_VOLUME = 5_000  # skip the totally illiquid tail; signals mean nothing there


def refresh_oslo() -> list[str]:
    query = yf.EquityQuery("and", [
        yf.EquityQuery("eq", ["region", "no"]),
        yf.EquityQuery("eq", ["exchange", "OSL"]),
    ])
    symbols: set[str] = set()
    offset = 0
    while True:
        result = yf.screen(query, size=PAGE_SIZE, offset=offset)
        quotes = result.get("quotes", [])
        for quote in quotes:
            symbol = quote.get("symbol", "")
            volume = quote.get("averageDailyVolume3Month") or 0
            if symbol.endswith(".OL") and volume >= MIN_DAY_VOLUME:
                symbols.add(symbol)
        offset += PAGE_SIZE
        if offset >= (result.get("total") or 0) or not quotes:
            break
    return sorted(symbols)


def refresh_sp500() -> list[str]:
    import io

    import requests

    response = requests.get(SP500_WIKI_URL, timeout=30,
                            headers={"User-Agent": "project-bling-empire/2.0 (hobby screener)"})
    response.raise_for_status()
    table = pd.read_html(io.StringIO(response.text))[0]
    # Yahoo uses dashes where the index file uses dots (BRK.B -> BRK-B).
    return sorted(str(s).replace(".", "-") for s in table["Symbol"])


def write_universe(name: str, symbols: list[str]) -> None:
    TICKER_DIR.mkdir(parents=True, exist_ok=True)
    (TICKER_DIR / UNIVERSE_FILES[name]).write_text("\n".join(symbols) + "\n")


def refresh_all() -> dict[str, int]:
    counts = {}
    for name, refresher in [("oslo", refresh_oslo), ("sp500", refresh_sp500)]:
        symbols = refresher()
        if len(symbols) < 100:  # a live source returning a stub means breakage, keep the old file
            print(f"  {name}: refusing to overwrite with only {len(symbols)} symbols")
            continue
        write_universe(name, symbols)
        counts[name] = len(symbols)
        print(f"  {name}: {len(symbols)} tickers written")
    return counts
