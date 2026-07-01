"""Daily cron: refresh the screen, then push only what changed.

Pushes (max 4/run, most important first):
  1. Tickers that newly became BUY.
  2. Sell-guidance changes on Hanna's actual holdings (HOLD -> SELL/TAKE PROFIT).
  3. New WATCH names (one grouped push).
  4. On the 1st of the month: runway status.

State in v2/data/notify_state.json so nothing fires twice.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

V2_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_ROOT))

from bling.engine import analyze_ticker, analyze_universe  # noqa: E402
from bling.finance import store  # noqa: E402
from bling.finance.model import build_report  # noqa: E402
from bling.notify import push  # noqa: E402
from bling.report import reports_to_frame, write_reports  # noqa: E402
from bling.universe import load_universe  # noqa: E402

STATE_PATH = V2_ROOT / "data" / "notify_state.json"
MAX_PUSHES = 4
UNIVERSES = ["oslo", "sp500"]


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"actions": {}, "guidance": {}, "last_runway_push": ""}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def main() -> None:
    state = load_state()
    pushes: list[tuple[str, str, str]] = []  # (title, body, url)

    # ── 1-3. screen and diff ────────────────────────────────────────────
    new_actions: dict[str, str] = {}
    new_watches: list[str] = []
    for universe in UNIVERSES:
        tickers = load_universe(universe)
        print(f"screening {len(tickers)} in {universe}")
        reports = analyze_universe(tickers, progress=False)
        frame = reports_to_frame(reports)
        write_reports(frame, universe)
        for r in reports:
            new_actions[r.ticker] = r.action
            previous = state["actions"].get(r.ticker, "")
            if r.action == "BUY" and previous != "BUY":
                pushes.append((
                    f"🟢 BUY: {r.ticker}",
                    f"{r.name or r.ticker} — quality {r.quality.score}, "
                    f"{(r.valuation.discount_to_sticker or 0) * 100:.0f}% below sticker, all tools bullish.",
                    f"/ticker/{r.ticker}",
                ))
            elif r.action == "WATCH" and previous not in ("WATCH", "BUY"):
                new_watches.append(r.ticker)

    finances = store.load()
    for holding in finances.holdings:
        report = analyze_ticker(holding.ticker, max_age=timedelta(hours=12))
        guidance = report.sell_guidance
        previous = state["guidance"].get(holding.ticker, "")
        if guidance != previous and (guidance.startswith("SELL") or guidance.startswith("TAKE PROFIT")):
            pushes.insert(0, (  # holdings outrank new buys
                f"🔴 {holding.ticker}: {guidance.split(' (')[0]}",
                f"{report.name or holding.ticker} — {guidance}. You hold {holding.shares:g} shares.",
                f"/ticker/{holding.ticker}",
            ))
        state["guidance"][holding.ticker] = guidance

    if new_watches:
        pushes.append((
            f"👀 New on the shopping list: {', '.join(new_watches[:5])}",
            "Right company, right price — waiting for the timing tools to confirm.",
            "/",
        ))

    # ── 4. monthly runway note ──────────────────────────────────────────
    month = date.today().strftime("%Y-%m")
    if date.today().day == 1 and state.get("last_runway_push") != month:
        runway = build_report(finances)
        months = "∞" if runway.runway_months is None else f"{runway.runway_months} mo"
        pushes.append((
            f"🏦 Runway: {months}",
            f"Burn {runway.monthly_burn:,.0f} kr/mo, liquid {runway.liquid:,.0f} kr. "
            f"Break-even needs {runway.breakeven_income:,.0f} kr/mo.",
            "/finances",
        ))
        state["last_runway_push"] = month

    state["actions"] = new_actions
    save_state(state)

    for title, body, url in pushes[:MAX_PUSHES]:
        sent = push(title, body, url)
        print(f"push {'OK' if sent else 'FAILED'}: {title}")
    if not pushes:
        print("no changes worth a push")


if __name__ == "__main__":
    main()
