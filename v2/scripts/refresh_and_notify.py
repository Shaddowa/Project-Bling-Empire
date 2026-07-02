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

from dataclasses import asdict  # noqa: E402
from datetime import datetime  # noqa: E402

from bling import ledger  # noqa: E402
from bling.engine import analyze_ticker, analyze_universe, enrich_holding  # noqa: E402
from bling.finance import store  # noqa: E402
from bling.finance.model import build_report  # noqa: E402
from bling.modes import swing_scan  # noqa: E402
from bling.notify import get_prefs, push  # noqa: E402
from bling.report import reports_to_frame, write_reports  # noqa: E402
from bling.universe import active_universes, load_universe  # noqa: E402

STATE_PATH = V2_ROOT / "data" / "notify_state.json"
SWING_PATH = V2_ROOT / "data" / "swing.json"
MAX_PUSHES = 6


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"actions": {}, "guidance": {}, "last_runway_push": ""}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def main() -> None:
    state = load_state()
    prefs = get_prefs()
    pushes: list[tuple[str, str, str]] = []  # (title, body, url)

    # ── 1-3. screen and diff ────────────────────────────────────────────
    new_actions: dict[str, str] = {}
    new_watches: list[str] = []
    all_tickers: list[str] = []
    all_reports: list = []          # for the trade ledger (signal records)
    held_sell_flips: list[tuple[str, str, object]] = []
    for universe in active_universes():
        tickers = load_universe(universe)
        all_tickers += tickers
        print(f"screening {len(tickers)} in {universe}")
        reports = analyze_universe(tickers, progress=False)
        all_reports.extend(reports)
        frame = reports_to_frame(reports)
        write_reports(frame, universe)
        for r in reports:
            new_actions[r.ticker] = r.action
            previous = state["actions"].get(r.ticker, "")
            if r.action == "BUY" and previous != "BUY" and prefs["longterm_buy"]:
                pushes.append((
                    f"🟢 BUY: {r.ticker}",
                    f"{r.name or r.ticker} — quality {r.quality.score}, "
                    f"{(r.valuation.discount_to_sticker or 0) * 100:.0f}% below sticker, all tools bullish.",
                    f"/ticker/{r.ticker}",
                ))
            elif r.action == "WATCH" and previous not in ("WATCH", "BUY"):
                new_watches.append(r.ticker)

    # Swing setups: computed here (cached bundles, no new fetches) so the
    # /swing page loads instantly.
    previous_swing = set()
    if SWING_PATH.exists():
        previous_swing = {r["ticker"] for r in json.loads(SWING_PATH.read_text()).get("rows", [])}
    swing_rows = swing_scan(all_tickers)
    SWING_PATH.write_text(json.dumps({
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "rows": [{**{k: v for k, v in r.items() if k != "stats"},
                  "stats": asdict(r["stats"]) if r["stats"] else None} for r in swing_rows],
    }, indent=2))
    print(f"swing setups: {len(swing_rows)}")
    if prefs["swing_buy"]:
        # Only proven names make the push — the full list lives on /swing.
        # The 1–2-month rule is trend-following (~37% win rate, winners run),
        # so "proven" means the rule MADE MONEY on the name over 2y (positive
        # avg trade net of costs, or it beat holding the same name) — a 60%
        # win-rate bar would mute nearly every push under this profile.
        def proven_stats(stats) -> bool:
            if not stats:
                return False
            if (stats.avg_trade_return or 0) > 0:
                return True
            return (stats.strategy_return is not None and stats.hold_return is not None
                    and stats.strategy_return > stats.hold_return)

        proven = [r["ticker"] for r in swing_rows
                  if r["ticker"] not in previous_swing and proven_stats(r["stats"])]
        if proven:
            pushes.append((
                f"〰 Swing setups: {', '.join(proven[:8])}",
                "Fresh 1–2 month trend entries on names where the rule historically "
                "made money net of costs. Track records on /swing.",
                "/swing",
            ))

    # Bank balances: sync if connected; a failing consent gets one push per day.
    if (V2_ROOT / "data" / "bank.json").exists():
        import subprocess
        import sys as _sys
        result = subprocess.run([_sys.executable, str(V2_ROOT / "scripts" / "bank_sync.py"), "sync"],
                                capture_output=True, text=True, cwd=V2_ROOT, timeout=600)
        print("bank sync:", "ok" if result.returncode == 0 else result.stderr.strip()[-200:])
        if result.returncode != 0 and any(code in result.stderr for code in ("401", "403", "409")):
            pushes.append(("🏦 Bank consent needs renewal",
                           "The daily balance sync was rejected — approve a fresh consent: "
                           "python scripts/bank_sync.py connect <bank>", "/finances"))

    finances = store.load()
    for holding in finances.holdings:
        report = analyze_ticker(holding.ticker, max_age=timedelta(hours=12))
        guidance = enrich_holding(report, holding)["guidance"]  # includes stop-loss override
        previous = state["guidance"].get(holding.ticker, "")
        if (guidance != previous and prefs["holding_sell"]
                and (guidance.startswith("SELL") or guidance.startswith("TAKE PROFIT"))):
            pushes.insert(0, (  # holdings outrank new buys
                f"🔴 {holding.ticker}: {guidance.split(' (')[0]}",
                f"{report.name or holding.ticker} — {guidance}. You hold {holding.shares:g} shares.",
                f"/ticker/{holding.ticker}",
            ))
        state["guidance"][holding.ticker] = guidance
        if guidance != previous and (guidance.startswith("SELL")
                                     or guidance.startswith("TAKE PROFIT")):
            held_sell_flips.append((holding.ticker, guidance, report.valuation.price))

    # ── trade ledger: record signal events + mark open calls to market ──
    # (its own memory; a ledger hiccup must never block the pushes)
    try:
        ledger.refresh_index_cache([r.ticker for r in all_reports])
        recorded = ledger.record_daily_signals(all_reports, swing_rows)
        for ticker, flip_guidance, flip_price in held_sell_flips:
            ledger.record_sell_flip(ticker, flip_guidance, price=flip_price)
        marked = ledger.mark_open_signals()
        print(f"ledger: +{recorded['new_buys']} buy, +{recorded['new_swings']} swing, "
              f"+{recorded['sell_flips'] + len(held_sell_flips)} sell-flip, {marked} marked")
    except Exception as error:
        print(f"ledger update failed: {error}")

    # ── investment policy: push ONCE when cooldown/breaker flips ────────
    # (state in notify_state.json — a pause that is already known stays quiet)
    try:
        from bling import policy
        status = policy.policy_status(finances=finances)
        previous_policy = state.get("policy", {})
        if status["cooldown_active"] and \
                previous_policy.get("cooldown_until") != status["cooldown_until"]:
            pushes.insert(0, (
                f"🧊 Cooldown active until {status['cooldown_until']}",
                "Two stop-outs inside 20 days — the system buys nothing while you "
                "would be revenge-trading. Sells and stops still work; buys resume "
                f"after {status['cooldown_until']}.",
                "/ledger",
            ))
        if status["breaker_active"] and not previous_policy.get("breaker_active"):
            drawdown = status.get("drawdown_pct")
            pushes.insert(0, (
                "⛔ Circuit breaker: new buys paused",
                (f"Open positions are down {abs(drawdown):.1f}% — past the −10% line. "
                 if drawdown is not None else "Open positions are past the −10% line. ")
                + "No new buys until the book recovers; stops protect every position.",
                "/ledger",
            ))
        elif previous_policy.get("breaker_active") and not status["breaker_active"]:
            pushes.append((
                "✅ Circuit breaker off",
                "The open book recovered above −10% — the policy allows new buys again.",
                "/ledger",
            ))
        state["policy"] = {"cooldown_active": status["cooldown_active"],
                           "cooldown_until": status["cooldown_until"],
                           "breaker_active": status["breaker_active"]}
        print(f"policy: cooldown={status['cooldown_active']} "
              f"breaker={status['breaker_active']} "
              f"deployed {status['monthly_deployed_nok']}/{status['monthly_cap_nok']} kr")
    except Exception as error:
        print(f"policy check failed: {error}")

    if new_watches and prefs["watch"]:
        pushes.append((
            f"👀 New on the shopping list: {', '.join(new_watches[:5])}",
            "HOLD for now — right company, right price. Each flips to BUY the day "
            "the timing tools confirm; no action needed today.",
            "/",
        ))

    # ── 4. monthly runway note ──────────────────────────────────────────
    month = date.today().strftime("%Y-%m")
    if date.today().day == 1 and state.get("last_runway_push") != month and prefs["runway_monthly"]:
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
