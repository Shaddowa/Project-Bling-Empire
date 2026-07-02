"""Regenerate universe ticker CSVs from live sources.

Every market except the S&P 500 comes from Yahoo's own equity screener
(region query), so symbols are exactly what yfinance can fetch — including
suffix conventions (.OL, .ST, .DE, .L, .T, .HK, ...). Illiquid tail is
dropped (signals mean nothing at 2k shares/day) and each market is capped
to the most-traded names so daily screens stay fast and under rate limits.
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from .universe import MARKETS, TICKER_DIR, UNIVERSE_FILES

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
PAGE_SIZE = 250
MIN_DAY_VOLUME = 5_000
MAX_PER_MARKET = 500


def refresh_region(region: str) -> list[str]:
    query = yf.EquityQuery("eq", ["region", region])
    quotes: list[dict] = []
    offset = 0
    while True:
        result = yf.screen(query, size=PAGE_SIZE, offset=offset)
        page = result.get("quotes", [])
        quotes.extend(page)
        offset += PAGE_SIZE
        if offset >= (result.get("total") or 0) or not page or offset >= 2500:
            break
    rows = [
        (q["symbol"], q.get("averageDailyVolume3Month") or 0)
        for q in quotes
        if q.get("symbol") and (q.get("averageDailyVolume3Month") or 0) >= MIN_DAY_VOLUME
    ]
    rows.sort(key=lambda r: -r[1])
    return sorted({symbol for symbol, _ in rows[:MAX_PER_MARKET]})


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


def refresh(names: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in names:
        market = MARKETS[name]
        try:
            symbols = refresh_sp500() if market["region"] is None else refresh_region(market["region"])
        except Exception as error:
            print(f"  {name}: refresh failed ({error}) — keeping existing file")
            continue
        if len(symbols) < 50:  # live source returning a stub means breakage
            print(f"  {name}: refusing to overwrite with only {len(symbols)} symbols")
            continue
        write_universe(name, symbols)
        counts[name] = len(symbols)
        print(f"  {name}: {len(symbols)} tickers written")
    return counts


def refresh_all() -> dict[str, int]:
    return refresh(list(MARKETS))
