"""The discipline layer: an Investment Policy the app ENFORCES.

Research summary (2026-07 gap analysis): the best-evidenced behavioral finding
in retail trading (Fischbacher/Hoffmann/Schudy, RFS 2017) is that pre-committed
AUTOMATIC rules change outcomes while reminders alone do not. So these rules
are not advice on a page — bling.ledger.record_trade() runs check_trade() on
every BUY and refuses to record one that breaks policy unless it is explicitly
overridden, and every override is written into the ledger line itself
(accountability, not prevention theater).

The rules, with Hanna's numbers derived LIVE from the finance model
(build_targets: investable = liquid after cards minus a 12-month burn buffer):

  1. Max MAX_OPEN_POSITIONS open positions — at ~40k NOK, 3+ Nordic names are
     already one bet on the same cycle; more is di-worse-ification.
  2. Max per position = 25% of investable (adding to an existing name counts
     the whole position, not just the new lot).
  3. Never buy above the sticker price (when the cached screen knows it).
  4. Every holding must have a stop — the model's auto stop at 8% under cost
     (model.DEFAULT_STOP_FRACTION) always applies; the policy's job is to
     remind that the REAL order belongs at the broker, not on a dashboard.
  5. Cooldown: after 2 stop-outs within 20 days, no new BUYs for 5 trading
     days — the window in which revenge-trading happens.
  6. Drawdown circuit breaker: open positions in aggregate below -10%
     unrealized -> new buys pause until the book recovers.
  7. Monthly deploy cap: at most 50% of investable spent on BUYs per calendar
     month — a bad month can never consume the whole war chest.

Everything reads the same offline sources as the rest of the app: the trade
ledger (round trips, open positions), the finance file, and the bundle cache.
Tests inject finances/prices/fx_rates/sticker_price so nothing touches the
network or Hanna's real files.
"""
from __future__ import annotations

from datetime import date as _date
from datetime import timedelta
from typing import Optional

from . import ledger as _ledger
from .finance.model import DEFAULT_STOP_FRACTION, Finances, build_targets

# ── the policy numbers ──────────────────────────────────────────────────────
MAX_OPEN_POSITIONS = 5
MAX_POSITION_FRACTION = 0.25       # of investable, per name (whole position)
COOLDOWN_STOP_OUTS = 2             # this many stop-outs ...
COOLDOWN_WINDOW_DAYS = 20          # ... within this many calendar days ...
COOLDOWN_TRADING_DAYS = 5          # ... freeze new buys this many trading days
BREAKER_DRAWDOWN_PCT = -10.0       # aggregate unrealized % that pauses buys
MONTHLY_DEPLOY_FRACTION = 0.50     # of investable, per calendar month

# A closed round trip at/below this net return counts as a stop-out: the auto
# stop sits 8% under cost (DEFAULT_STOP_FRACTION), minus 1pp fill tolerance.
STOP_OUT_RETURN_PCT = (DEFAULT_STOP_FRACTION - 1.0) * 100.0 + 1.0   # -7.0

_UNSET = object()   # sentinel: "look the sticker up in the cache"


class PolicyViolationError(ValueError):
    """A BUY that breaks policy and was not overridden. .violations holds the
    structured list so callers (the dashboard form) can show every rule hit."""

    def __init__(self, violations: list[dict]):
        self.violations = violations
        super().__init__("; ".join(v["message"] for v in violations))


# ── small helpers ───────────────────────────────────────────────────────────

def _kr(amount: float) -> str:
    return f"{amount:,.0f} kr".replace(",", " ")


def _to_nok(amount: Optional[float], currency: Optional[str],
            fx_rates: Optional[dict]) -> float:
    """NOK value; missing rates degrade to 1.0 (same convention as
    ledger.performance) — a wrong-but-bounded number beats a crash here."""
    if not amount:
        return 0.0
    cur = currency or "NOK"
    if cur == "NOK":
        return float(amount)
    if fx_rates is not None:
        rate = fx_rates.get(cur)
    else:
        from . import fx as _fx
        rate = _fx.rate(cur, "NOK")
    return float(amount) * (rate or 1.0)


def add_trading_days(day: _date, count: int) -> _date:
    """`count` weekdays after `day` (weekend-aware; holidays ignored —
    close enough for a cooling-off rule)."""
    stepped = 0
    while stepped < count:
        day += timedelta(days=1)
        if day.weekday() < 5:
            stepped += 1
    return day


def _parse_day(value) -> Optional[_date]:
    try:
        return _date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _cached_sticker(ticker: str) -> Optional[float]:
    """Sticker price from the cached bundle only — NEVER fetches. None when
    the cache can't value the name (rule 3 is then unverifiable)."""
    try:
        from . import data as _data
        from .fundamentals import extract_fundamentals
        from .valuation import assess_valuation
        bundle = _data._load_cached(ticker)
        if bundle is None or not bundle.is_usable:
            return None
        return assess_valuation(extract_fundamentals(bundle)).sticker_price
    except Exception:
        return None


# ── the live policy state ───────────────────────────────────────────────────

def _cooldown_state(round_trips: list[dict], day: _date) -> dict:
    """Cooldown from realized round trips: COOLDOWN_STOP_OUTS stop-outs whose
    sell dates fall within COOLDOWN_WINDOW_DAYS of each other freeze new buys
    from the later stop-out through COOLDOWN_TRADING_DAYS trading days after."""
    stop_dates = sorted({d for trip in round_trips
                         if trip.get("return_pct") is not None
                         and trip["return_pct"] <= STOP_OUT_RETURN_PCT
                         for d in [_parse_day(trip.get("sell_date"))] if d})
    active, until, triggered = False, None, None
    for earlier, later in zip(stop_dates, stop_dates[1:]):
        if (later - earlier).days <= COOLDOWN_WINDOW_DAYS:
            end = add_trading_days(later, COOLDOWN_TRADING_DAYS)
            if later <= day <= end and (until is None or end > until):
                active, until, triggered = True, end, later
    return {"active": active,
            "until": until.isoformat() if until else None,
            "triggered": triggered.isoformat() if triggered else None,
            "stop_outs": len(stop_dates)}


def _state(day: _date, finances: Optional[Finances], prices: Optional[dict],
           fx_rates: Optional[dict], path) -> dict:
    """Everything every rule needs, computed once (offline: ledger file,
    finance file, bundle cache)."""
    if finances is None:
        from .finance import store
        finances = store.load()
    targets = build_targets(finances)
    investable = float(targets.investable)

    positions = _ledger.positions(prices=prices, path=path)
    cost_by_ticker = {p["ticker"]: _to_nok(p["cost_value"], p["currency"], fx_rates)
                      for p in positions}
    priced = [p for p in positions if p["value"] is not None]
    open_cost = sum(_to_nok(p["cost_value"], p["currency"], fx_rates) for p in priced)
    open_value = sum(_to_nok(p["value"], p["currency"], fx_rates) for p in priced)
    drawdown_pct = (round((open_value / open_cost - 1.0) * 100.0, 2)
                    if open_cost > 0 else None)

    _, round_trips = _ledger._fifo(_ledger.trades(path))
    month = day.isoformat()[:7]
    deployed = sum(_to_nok(t["shares"] * t["price"], t.get("currency"), fx_rates)
                   for t in _ledger.trades(path)
                   if t.get("side") == "BUY" and str(t.get("date", ""))[:7] == month)

    return {
        "day": day, "finances": finances, "investable": investable,
        "max_position_nok": investable * MAX_POSITION_FRACTION,
        "open_positions": len(positions), "cost_by_ticker": cost_by_ticker,
        "drawdown_pct": drawdown_pct,
        "cooldown": _cooldown_state(round_trips, day),
        "monthly_deployed_nok": deployed,
        "monthly_cap_nok": investable * MONTHLY_DEPLOY_FRACTION,
    }


# ── public API ──────────────────────────────────────────────────────────────

def check_trade(ticker: str, side: str, shares: float, price: float,
                date=None, *, finances: Optional[Finances] = None,
                prices: Optional[dict] = None, fx_rates: Optional[dict] = None,
                currency: Optional[str] = None, sticker_price=_UNSET,
                path=None) -> list[dict]:
    """Check a proposed trade against the policy.

    Returns a list of violations, each {"rule", "message", "severity"} —
    severity "block" stops the trade (unless overridden at record time),
    "warn" only informs. SELLs always pass: the policy never blocks an exit.

    All state is injectable for tests (finances/prices/fx_rates/sticker_price);
    defaults read the finance file, bundle cache and live FX.
    """
    path = path if path is not None else _ledger.LEDGER_PATH
    if str(side).strip().upper() != "BUY":
        return []
    ticker = str(ticker).strip().upper()
    day = _parse_day(_ledger._iso(date)) or _date.today()
    shares, price = float(shares), float(price)
    if currency is None:
        currency = _ledger._SUFFIX_CURRENCY.get(_ledger._suffix(ticker))
    state = _state(day, finances, prices, fx_rates, path)
    cost_nok = _to_nok(shares * price, currency, fx_rates)
    violations: list[dict] = []

    def block(rule: str, message: str) -> None:
        violations.append({"rule": rule, "message": message, "severity": "block"})

    # 1. max open positions (adding to a name you already hold is fine)
    if ticker not in state["cost_by_ticker"] and \
            state["open_positions"] >= MAX_OPEN_POSITIONS:
        block("max_open_positions",
              f"Already {state['open_positions']} open positions — the policy caps you at "
              f"{MAX_OPEN_POSITIONS}. Close something before opening a new name.")

    # 2. max position size = 25% of investable (whole position after this buy)
    if state["investable"] <= 0:
        block("max_position_size",
              "Investable capital is 0 kr right now — the 12-month safety buffer "
              "eats everything liquid. The policy allows no buys at all.")
    else:
        position_after = state["cost_by_ticker"].get(ticker, 0.0) + cost_nok
        if position_after > state["max_position_nok"]:
            block("max_position_size",
                  f"This buy makes {ticker} a {_kr(position_after)} position — over the "
                  f"{MAX_POSITION_FRACTION:.0%} cap of {_kr(state['max_position_nok'])} "
                  f"({_kr(state['investable'])} investable).")

    # 3. never buy above sticker price
    sticker = _cached_sticker(ticker) if sticker_price is _UNSET else sticker_price
    if sticker and price > sticker:
        block("above_sticker",
              f"{price:g} is above the sticker price ({sticker:.2f}) — never pay more "
              f"than the business is worth. Wait or walk away.")
    elif not sticker:
        violations.append({
            "rule": "sticker_unknown", "severity": "warn",
            "message": f"Couldn't verify the sticker price for {ticker} (no cached "
                       f"valuation) — check /ticker/{ticker} before buying."})

    # 5. cooldown after clustered stop-outs
    if state["cooldown"]["active"]:
        block("cooldown",
              f"Cooldown until {state['cooldown']['until']}: {COOLDOWN_STOP_OUTS} stop-outs "
              f"inside {COOLDOWN_WINDOW_DAYS} days — the system buys nothing while you "
              f"would be revenge-trading.")

    # 6. drawdown circuit breaker
    if state["drawdown_pct"] is not None and state["drawdown_pct"] < BREAKER_DRAWDOWN_PCT:
        block("drawdown_breaker",
              f"Open positions are down {state['drawdown_pct']:.1f}% — past the "
              f"{BREAKER_DRAWDOWN_PCT:.0f}% circuit breaker. New buys pause until the "
              f"book recovers.")

    # 7. monthly deploy cap
    if state["investable"] > 0 and \
            state["monthly_deployed_nok"] + cost_nok > state["monthly_cap_nok"]:
        block("monthly_deploy_cap",
              f"{_kr(state['monthly_deployed_nok'])} already deployed in "
              f"{day.isoformat()[:7]} — this buy would pass the monthly cap of "
              f"{_kr(state['monthly_cap_nok'])} ({MONTHLY_DEPLOY_FRACTION:.0%} of investable).")

    return violations


def policy_status(date=None, *, finances: Optional[Finances] = None,
                  prices: Optional[dict] = None, fx_rates: Optional[dict] = None,
                  path=None) -> dict:
    """The policy's current state for dashboards/notifications: capacity left,
    cooldown, breaker, monthly budget, and the rules in plain language."""
    path = path if path is not None else _ledger.LEDGER_PATH
    day = _parse_day(_ledger._iso(date)) or _date.today()
    state = _state(day, finances, prices, fx_rates, path)
    cooldown = state["cooldown"]
    breaker_active = (state["drawdown_pct"] is not None
                      and state["drawdown_pct"] < BREAKER_DRAWDOWN_PCT)
    monthly_left = max(0.0, state["monthly_cap_nok"] - state["monthly_deployed_nok"])
    stop_pct = (1.0 - DEFAULT_STOP_FRACTION) * 100.0
    return {
        "date": day.isoformat(),
        "investable": round(state["investable"]),
        "max_position_nok": round(state["max_position_nok"]),
        "open_positions": state["open_positions"],
        "max_open_positions": MAX_OPEN_POSITIONS,
        "positions_left": max(0, MAX_OPEN_POSITIONS - state["open_positions"]),
        "cooldown_active": cooldown["active"],
        "cooldown_until": cooldown["until"],
        "stop_outs_recorded": cooldown["stop_outs"],
        "breaker_active": breaker_active,
        "drawdown_pct": state["drawdown_pct"],
        "monthly_deployed_nok": round(state["monthly_deployed_nok"]),
        "monthly_cap_nok": round(state["monthly_cap_nok"]),
        "monthly_left_nok": round(monthly_left),
        "buys_paused": cooldown["active"] or breaker_active,
        "rules": [
            f"Max {MAX_OPEN_POSITIONS} open positions (now {state['open_positions']}).",
            f"Max {_kr(state['max_position_nok'])} in any one name — "
            f"{MAX_POSITION_FRACTION:.0%} of the {_kr(state['investable'])} investable "
            f"(liquid minus the untouchable 12-month buffer).",
            "Never buy above the sticker price.",
            f"Every holding has a stop ({stop_pct:.0f}% under cost unless set tighter) — "
            "place the REAL order at the broker; a dashboard reminder is not a stop.",
            f"{COOLDOWN_STOP_OUTS} stop-outs inside {COOLDOWN_WINDOW_DAYS} days freeze "
            f"new buys for {COOLDOWN_TRADING_DAYS} trading days (revenge-trading window).",
            f"If open positions are down more than {abs(BREAKER_DRAWDOWN_PCT):.0f}% "
            "overall, new buys pause until the book recovers.",
            f"Deploy at most {_kr(state['monthly_cap_nok'])} per calendar month "
            f"({MONTHLY_DEPLOY_FRACTION:.0%} of investable) — "
            f"{_kr(monthly_left)} left this month.",
        ],
    }
