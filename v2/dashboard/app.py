"""Bling Empire dashboard: signals + portfolio + runway, phone-first.

Run: uvicorn dashboard.app:app --host 127.0.0.1 --port 3400  (from v2/)
"""
from __future__ import annotations

import csv
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware

V2_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_ROOT))

from bling.engine import (analyze_ticker, holding_subtext, holding_verdict,  # noqa: E402
                          simple_subtext, simple_verdict)
from bling.finance import store  # noqa: E402
from bling.finance.model import Debt, Holding, LineItem, build_report, build_targets  # noqa: E402
from bling.universe import MARKETS, TICKER_DIR, active_universes, load_config, save_config  # noqa: E402
from dashboard import auth  # noqa: E402

OUTPUT_DIR = V2_ROOT / "output"
SWING_PATH = V2_ROOT / "data" / "swing.json"


def universe_labels() -> dict[str, str]:
    return {name: MARKETS[name]["label"] for name in active_universes()}

app = FastAPI(title="Bling Empire", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=500)  # HTML/JSON over cell networks
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
# BUY/HOLD/SELL vocabulary helpers, available in every template
templates.env.globals.update(
    simple_verdict=simple_verdict, simple_subtext=simple_subtext,
    holding_verdict=holding_verdict, holding_subtext=holding_subtext,
)


# ── helpers ──────────────────────────────────────────────────────────────

def logged_in(request: Request) -> bool:
    return auth.verify_session(request.cookies.get(auth.COOKIE_NAME))


def latest_output_dir() -> Path | None:
    if not OUTPUT_DIR.exists():
        return None
    days = sorted((d for d in OUTPUT_DIR.iterdir() if d.is_dir()), reverse=True)
    return days[0] if days else None


class _TTLCache:
    """Tiny thread-safe (key -> value) cache with per-cache TTL. On a
    stampede the value may be computed twice — harmless for a one-user app,
    and it keeps every hot path lock-free while computing."""

    def __init__(self, ttl_seconds: float, max_entries: int = 32):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._data: dict = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            hit = self._data.get(key)
        if hit is None or time.monotonic() - hit[0] >= self.ttl:
            return None
        return hit[1]

    def put(self, key, value) -> None:
        with self._lock:
            self._data.pop(key, None)
            self._data[key] = (time.monotonic(), value)
            while len(self._data) > self.max_entries:
                self._data.pop(next(iter(self._data)))


# signals CSVs only change when the daily screen writes a new file — memoize
# the parse by (path, mtime) instead of re-reading ~80KB of CSV per request.
_signals_memo: dict[str, tuple[float, list[dict]]] = {}
_signals_lock = threading.Lock()


def load_signals(universe: str) -> tuple[str, list[dict]]:
    day = latest_output_dir()
    if day is None:
        return "", []
    path = day / f"signals_{universe}.csv"
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return day.name, []
    key = str(path)
    with _signals_lock:
        hit = _signals_memo.get(key)
    if hit is not None and hit[0] == mtime:
        return day.name, hit[1]
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    with _signals_lock:
        _signals_memo[key] = (mtime, rows)
        while len(_signals_memo) > 16:
            _signals_memo.pop(next(iter(_signals_memo)))
    return day.name, rows


# Holding analysis reuses the daily bundle cache but still costs unpickle +
# scoring per ticker — cache the enriched rows briefly so / and /finances
# render instantly on repeat loads. Keyed by the holdings themselves, so any
# edit on /finances invalidates immediately.
_holdings_cache = _TTLCache(ttl_seconds=90.0, max_entries=4)


def live_holdings(finances) -> list[dict]:
    from bling.engine import analyze_universe, enrich_holding
    if not finances.holdings:
        return []
    key = tuple((h.ticker, h.shares, h.cost_basis, h.stop_price) for h in finances.holdings)
    cached = _holdings_cache.get(key)
    if cached is not None:
        return [dict(row) for row in cached]  # callers may copy-and-tweak
    reports = analyze_universe([h.ticker for h in finances.holdings],
                               max_age=timedelta(days=1), progress=False)
    rows = [enrich_holding(report, h) for report, h in zip(reports, finances.holdings)]
    _holdings_cache.put(key, rows)
    return [dict(row) for row in rows]


# Events (earnings / ex-dividend) are cached 12h inside bling.events, but a
# cold ticker costs 2-3 yfinance round-trips — bound page renders with a
# timeout and memoize the result briefly so the overview stays instant.
_events_cache = _TTLCache(ttl_seconds=1800.0, max_entries=8)


def safe_events(holdings: list[str], watch: list[str],
                timeout: float = 6.0) -> tuple[dict, list[dict]]:
    """(upcoming_events dict, alerts list) — never raises, never hangs.

    On timeout the fetch keeps running in the background so the events cache
    is warm on the next request; this request renders without events.
    """
    holdings = [t for t in dict.fromkeys(holdings) if t]
    watch = [t for t in dict.fromkeys(watch) if t and t not in holdings][:12]
    if not holdings and not watch:
        return {}, []
    key = (tuple(holdings), tuple(watch))
    cached = _events_cache.get(key)
    if cached is not None:
        return cached

    def fetch():
        from bling import events
        return events.upcoming_events(holdings + watch), events.alerts(holdings, watch)

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        result = pool.submit(fetch).result(timeout=timeout)
    except Exception:  # timeout, network, parsing — events are never load-bearing
        return {}, []
    finally:
        pool.shutdown(wait=False)
    _events_cache.put(key, result)
    return result


_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _event_phrase(ticker: str, ev: dict) -> str | None:
    """'KIT.OL reports earnings Thursday' — deterministic, closest first."""
    from datetime import date as _date, datetime as _dt
    days = ev.get("earnings_days")
    if days is None or days < 0 or not ev.get("earnings_date"):
        return None
    if days == 0:
        when = "today"
    elif days == 1:
        when = "tomorrow"
    elif days <= 7:
        when = _WEEKDAYS[_dt.strptime(ev["earnings_date"], "%Y-%m-%d").weekday()]
    else:
        when = f"in {days} days ({ev['earnings_date']})"
    return f"{ticker} reports earnings {when}."


def overview_summary(report, buys: list[str], sell_rows: list[dict],
                     swing_count: int, events: dict) -> str:
    """1-2 plain sentences that summarize the whole dashboard, from data."""
    runway = "runway ∞" if report.runway_months is None else f"runway {report.runway_months} months"
    actions = []
    if buys:
        actions.append("BUY " + ", ".join(buys[:4]) + ("…" if len(buys) > 4 else ""))
    for h in sell_rows[:2]:
        actions.append(f"SELL {h['ticker']} ({h.get('why') or 'see below'})")
    if actions:
        first = f"{len(actions)} thing{'s' if len(actions) > 1 else ''} need{'' if len(actions) > 1 else 's'} you today: " \
                + "; ".join(actions) + f" — {runway}."
    else:
        first = f"Nothing needs you today: no buys, no sells, {runway}."
    # second sentence: a genuinely-near event (≤14d), else the swing count
    phrases = sorted(((ev.get("earnings_days"), t, ev) for t, ev in events.items()
                      if ev.get("earnings_days") is not None and 0 <= ev["earnings_days"] <= 14),
                     key=lambda x: x[0])
    second = ""
    if phrases:
        second = _event_phrase(phrases[0][1], phrases[0][2]) or ""
    elif swing_count:
        second = f"{swing_count} swing setups are waiting on the Swing tab."
    return (first + " " + second).strip()


# ── auth ─────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login(request: Request, password: str = Form(...)):
    if not auth.verify_password(password):
        return templates.TemplateResponse(request, "login.html", {"error": "Wrong password"}, status_code=401)
    response = RedirectResponse("/", status_code=303)
    # secure=False: served orchestrator-style over plain HTTP on IP:port —
    # a Secure cookie would silently never be sent back.
    response.set_cookie(auth.COOKIE_NAME, auth.issue_session(), max_age=auth.SESSION_TTL_SECONDS,
                        httponly=True, secure=False, samesite="lax")
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.COOKIE_NAME)
    return response


@app.middleware("http")
async def require_login(request: Request, call_next):
    open_paths = {"/login", "/healthz", "/favicon.ico", "/apple-touch-icon.png", "/manifest.json"}
    if request.url.path in ("/api/widget", "/api/widget-script"):  # token-authed
        if not auth.verify_widget_token(request.query_params.get("token")):
            return JSONResponse({"error": "bad token"}, status_code=401)
        return await call_next(request)
    if (request.url.path not in open_paths
            and not request.url.path.startswith("/static/")
            and not logged_in(request)):
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    """Static assets never change without a redeploy — let the phone keep them."""
    response = await call_next(request)
    path = request.url.path
    if response.status_code == 200 and "cache-control" not in response.headers:
        if path.startswith("/static/") or path in ("/favicon.ico", "/apple-touch-icon.png"):
            response.headers["Cache-Control"] = "public, max-age=604800, immutable"
        elif path == "/manifest.json":
            response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.get("/widget-setup", response_class=HTMLResponse)
def widget_setup(request: Request):
    """The loader with the token pre-filled, copyable from the phone —
    terminal copy-paste picks up prompt garbage; this doesn't."""
    loader = (V2_ROOT / "widgets" / "bling-widget.js").read_text()
    loader = loader.replace("PASTE_WIDGET_TOKEN_HERE", auth.widget_token())
    body = f"""{{% extends "base.html" %}}
{{% block title %}}Widget setup — Bling Empire{{% endblock %}}
{{% block content %}}
<h1 class="page">Widget setup</h1>
<div class="card">
  <h2>Paste-once loader (token already filled in)</h2>
  <ol class="muted" style="line-height:1.9;padding-left:1.2rem">
    <li>Tap the box — it copies everything.</li>
    <li>Scriptable app → <b>+</b> → paste → name it <b>Bling</b>.</li>
    <li>Home screen → long-press → add <b>Scriptable</b> widget → choose Bling.</li>
    <li>Long-press the widget → Edit → <b>Parameter</b>: <code>brief</code>, <code>runway</code>,
        <code>positions</code>, <code>signals</code> or <code>pulse</code>.
        Combine with commas — e.g. <code>positions:6, nopulse, dark</code>.
        Flags: <code>positions:N</code>/<code>max:N</code>, <code>nopulse</code>, <code>nofooter</code>,
        <code>nospark</code>, <code>plain</code>, <code>dark</code>, <code>light</code>.</li>
  </ol>
  <pre id="code" onclick="navigator.clipboard.writeText(this.textContent).then(()=>this.style.borderColor='var(--good)')"
       style="white-space:pre-wrap;word-break:break-all;font-size:.72rem;cursor:pointer;
              background:var(--surface-2);border:2px solid var(--border);border-radius:10px;
              padding:.8rem">{loader.replace("&", "&amp;").replace("<", "&lt;")}</pre>
  <div class="muted">After this, widget improvements ship from the server automatically — you never paste again.</div>
</div>
{{% endblock %}}"""
    return HTMLResponse(templates.env.from_string(body).render(request=request))


@app.get("/api/widget-script")
def widget_script(request: Request):
    """The widget core, fetched by the on-phone loader on every run —
    editing v2/widgets/bling-widget-core.js updates every widget.
    ETag + a short max-age: the loader revalidates cheaply (304, no body)
    and still picks up server-side widget improvements within minutes."""
    path = V2_ROOT / "widgets" / "bling-widget-core.js"
    stat = path.stat()
    etag = f'"{int(stat.st_mtime)}-{stat.st_size}"'
    headers = {"Cache-Control": "public, max-age=300", "ETag": etag}
    if etag in (request.headers.get("if-none-match") or ""):
        return Response(status_code=304, headers=headers)
    return FileResponse(path, media_type="application/javascript", headers=headers)


# Assembled widget payloads are cached briefly (per live flag + input-file
# mtimes, so a /finances save or new signals invalidate instantly). 15s keeps
# quotes trading-fresh while making the frequent widget refreshes free.
_widget_cache = _TTLCache(ttl_seconds=15.0, max_entries=8)


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


@app.get("/api/widget")
def widget_api(live: int = 1):
    """Everything a widget needs: runway, targets, positions (live quotes),
    today's actions, swing count, market pulse."""
    import json as _json
    from datetime import datetime

    from bling.pulse import live_quote, market_pulse
    from bling.finance.store import DATA_PATH as FINANCES_PATH

    cache_key = (bool(live), _mtime(FINANCES_PATH), _mtime(SWING_PATH),
                 _mtime(V2_ROOT / "data" / "notify_state.json"))
    cached = _widget_cache.get(cache_key)
    if cached is not None:
        return cached

    finances = store.load()
    report = build_report(finances)
    targets = build_targets(finances)
    buys, watch_count, day = [], 0, ""
    for universe in active_universes():
        day, rows = load_signals(universe)
        buys += [r["TICKER"] for r in rows if r["ACTION"] == "BUY"]
        watch_count += sum(1 for r in rows if r["ACTION"] == "WATCH")
    sells = []
    if (V2_ROOT / "data" / "notify_state.json").exists():
        guidance = _json.loads((V2_ROOT / "data" / "notify_state.json").read_text()).get("guidance", {})
        sells = [t for t, g in guidance.items() if g.startswith(("SELL", "TAKE PROFIT"))]
    swing_count = 0
    if SWING_PATH.exists():
        swing_count = len(_json.loads(SWING_PATH.read_text()).get("rows", []))

    # Live extras run in parallel: the pulse alongside one light quote call
    # per holding, so wall time is one round-trip instead of N+1.
    base_rows = live_holdings(finances)
    quotes, pulse = {}, []
    if live:
        with ThreadPoolExecutor(max_workers=8) as pool:
            pulse_future = pool.submit(market_pulse)
            quote_futures = {row["ticker"]: pool.submit(live_quote, row["ticker"])
                             for row in base_rows}
            pulse = pulse_future.result()
            quotes = {t: f.result() for t, f in quote_futures.items()}

    holdings = []
    for h, holding in zip(base_rows, finances.holdings):
        day_pct = None
        if live:  # overlay a fresh quote on the cached daily analysis
            price, day_pct = quotes.get(h["ticker"], (None, None))
            if price:
                h = dict(h)
                h["price"] = round(price, 2)
                if h["cost"]:
                    h["gain_pct"] = round((price / h["cost"] - 1.0) * 100.0, 1)
                if h["target"] and h["cost"] and h["target"] > h["cost"]:
                    h["progress"] = round(max(0.0, min(1.0, (price - h["cost"]) / (h["target"] - h["cost"]))), 3)
                if h["stop"] and price <= h["stop"]:
                    h["guidance"] = f"SELL NOW (stop loss {h['stop']} hit)"
        holdings.append({
            "ticker": h["ticker"], "price": h["price"], "cost": h["cost"],
            "stop": h["stop"], "target": h["target"], "target_kind": h.get("target_kind"),
            "progress": h["progress"], "gain_pct": h["gain_pct"], "day_pct": day_pct,
            "stop_hit": bool(h["guidance"].startswith("SELL NOW")),
        })

    payload = {
        "updated": day,
        "generated_at": datetime.now().strftime("%H:%M"),
        "runway_months": report.runway_months,
        "liquid": round(report.liquid_after_cards),
        "burn": round(report.monthly_burn),
        "income_target": round(targets.income_target),
        "buys": buys[:8],
        "watch_count": watch_count,
        "swing_count": swing_count,
        "sell_alerts": sells[:4],
        "holdings": holdings[:6],
        "markets": pulse if live else [],
    }
    _widget_cache.put(cache_key, payload)
    return payload


@app.get("/healthz")
def healthz():
    return {"ok": True}


# ── icons / manifest (open: iOS fetches these without cookies) ──────────

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/static/favicon.png", include_in_schema=False)
def favicon():
    return FileResponse(STATIC_DIR / "favicon.png", media_type="image/png")


@app.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch_icon():
    return FileResponse(STATIC_DIR / "apple-touch-icon.png", media_type="image/png")


@app.get("/static/icon-512.png", include_in_schema=False)
def icon_512():
    return FileResponse(STATIC_DIR / "icon-512.png", media_type="image/png")


@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return JSONResponse({
        "name": "Bling Empire",
        "short_name": "Bling",
        "display": "standalone",
        "background_color": "#f2ece0",
        "theme_color": "#f2ece0",
        "start_url": "/",
        "icons": [{"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    })


# ── pages ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    import json as _json
    finances = store.load()
    report = build_report(finances)
    labels = universe_labels()

    day = ""
    buy_rows = []  # actionable BUY cards, all universes merged
    for universe in labels:
        day, rows = load_signals(universe)
        for r in rows:
            if r["ACTION"] == "BUY":
                buy_rows.append({**r, "universe": universe, "label": labels[universe]})

    holdings = live_holdings(finances)
    swing_count = 0
    if SWING_PATH.exists():
        swing_count = len(_json.loads(SWING_PATH.read_text()).get("rows", []))

    # events for held + buy-candidate names (bounded, cached, never blocking)
    events, alerts = safe_events([h["ticker"] for h in holdings],
                                 [r["TICKER"] for r in buy_rows])
    earnings_soon = {a["ticker"]: a for a in alerts if a["kind"] == "earnings_holding"}

    sell_rows, attention = [], []
    for h in holdings:
        verdict = holding_verdict(h["guidance"])
        if verdict == "SELL":
            sell_rows.append({**h, "why": holding_subtext(h["guidance"])})
        if verdict == "SELL" or h["ticker"] in earnings_soon:
            attention.append(h)

    summary = overview_summary(report, [r["TICKER"] for r in buy_rows],
                               sell_rows, swing_count, events)
    return templates.TemplateResponse(request, "index.html", {
        "summary": summary, "day": day,
        "finances": finances, "report": report,
        "targets": build_targets(finances),
        "buy_rows": buy_rows, "sell_rows": sell_rows,
        "holdings": holdings, "attention": attention,
        "earnings_soon": earnings_soon, "events": events,
    })


@app.get("/signals/{universe}", response_class=HTMLResponse)
def signals(request: Request, universe: str, action: str = ""):
    day, rows = load_signals(universe)
    label = MARKETS.get(universe, {}).get("label", universe)
    if action:
        rows = [r for r in rows if r["ACTION"] == action.upper()]
    return templates.TemplateResponse(request, "signals.html", {
        "universe": universe, "label": label,
        "day": day, "rows": rows[:400], "action": action.upper(),
    })


@app.get("/signals", response_class=HTMLResponse)
def signals_hub(request: Request, mode: str = "long"):
    if mode == "swing":
        return swing(request)
    if mode == "day":
        return day_page(request)
    labels = universe_labels()
    cards = {}
    for universe in labels:
        day, rows = load_signals(universe)
        cards[universe] = {
            "day": day,
            "buy": [r for r in rows if r["ACTION"] == "BUY"],
            "watch": [r for r in rows if r["ACTION"] == "WATCH"],
        }
    # upcoming events on holdings + today's BUY/WATCH names
    finances = store.load()
    watch_tickers = [r["TICKER"] for c in cards.values() for r in c["buy"] + c["watch"]]
    events, alerts = safe_events([h.ticker for h in finances.holdings], watch_tickers)
    upcoming = sorted(
        ((t, ev) for t, ev in events.items()
         if (ev.get("earnings_days") is not None and ev["earnings_days"] >= 0)
         or (ev.get("ex_dividend_days") is not None and ev["ex_dividend_days"] >= 0
             and ev.get("dividend_yield"))),
        key=lambda p: min(d for d in (p[1].get("earnings_days"),
                                      p[1].get("ex_dividend_days")) if d is not None and d >= 0))
    return templates.TemplateResponse(request, "longterm.html", {
        "cards": cards, "labels": labels,
        "upcoming": upcoming[:8], "event_alerts": alerts,
    })


@app.get("/swing", response_class=HTMLResponse)
def swing(request: Request):
    import json as _json
    rows, generated_at = [], None
    if SWING_PATH.exists():
        data = _json.loads(SWING_PATH.read_text())
        generated_at = data.get("generated_at")
        rows = [type("Row", (), {**r, "stats": type("S", (), r["stats"])() if r.get("stats") else None})()
                for r in data.get("rows", [])]
    return templates.TemplateResponse(request, "swing.html", {"rows": rows, "generated_at": generated_at})


# Intraday rows cache: 60s is well within "live enough" for decision support
# and makes tab-hopping back to /day instant.
_day_cache = _TTLCache(ttl_seconds=60.0, max_entries=4)


@app.get("/day", response_class=HTMLResponse)
def day_page(request: Request):
    from datetime import datetime

    from bling.modes import day_view
    finances = store.load()
    shortlist = [h.ticker for h in finances.holdings]
    if SWING_PATH.exists():
        import json as _json
        shortlist += [r["ticker"] for r in _json.loads(SWING_PATH.read_text()).get("rows", [])]
    for universe in active_universes():
        _, rows = load_signals(universe)
        shortlist += [r["TICKER"] for r in rows if r["ACTION"] in ("BUY", "WATCH")]
    seen: list[str] = []
    for t in shortlist:
        if t not in seen:
            seen.append(t)
    seen = seen[:15]  # same cap day_view(max_tickers=15) applied

    key = tuple(seen)
    day_rows = _day_cache.get(key)
    if day_rows is None:
        # day_view parallelizes its own fetches internally (thread pool in
        # modes.py) and sorts by day change — one call does it all.
        day_rows = day_view(seen, max_tickers=len(seen) or 1)
        _day_cache.put(key, day_rows)
    return templates.TemplateResponse(request, "day.html", {
        "rows": day_rows,
        "loaded_at": datetime.now().strftime("%H:%M UTC"),
    })


@app.get("/markets", response_class=HTMLResponse)
def markets_page(request: Request, saved: int = 0):
    counts = {}
    for name, m in MARKETS.items():
        path = TICKER_DIR / m["file"]
        counts[name] = sum(1 for line in path.read_text().splitlines() if line.strip()) if path.exists() else 0
    day = latest_output_dir()
    has_signals = {name: bool(day and (day / f"signals_{name}.csv").exists()) for name in MARKETS}
    return templates.TemplateResponse(request, "markets.html", {
        "markets": MARKETS, "active": active_universes(),
        "counts": counts, "has_signals": has_signals, "saved": saved,
    })


@app.post("/markets")
async def markets_save(request: Request):
    form = await request.form()
    chosen = [name for name in form.getlist("active") if name in MARKETS]
    config = load_config()
    config["active_universes"] = chosen or ["oslo"]
    save_config(config)
    return RedirectResponse("/markets?saved=1", status_code=303)


@app.get("/ticker/{symbol}", response_class=HTMLResponse)
def ticker(request: Request, symbol: str):
    symbol = symbol.upper()
    report = analyze_ticker(symbol, max_age=timedelta(days=1))
    finances = store.load()
    owned = any(h.ticker == symbol for h in finances.holdings)

    def fetch_extras():
        from bling import events as ev
        return ev.upcoming_events([symbol]).get(symbol, {}), ev.news(symbol, limit=5)

    ticker_events, headlines = {}, []
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        ticker_events, headlines = pool.submit(fetch_extras).result(timeout=8.0)
    except Exception:
        pass  # events/news are garnish — the report is the meal
    finally:
        pool.shutdown(wait=False)
    return templates.TemplateResponse(request, "ticker.html", {
        "r": report, "owned": owned,
        "events": ticker_events, "headlines": headlines,
    })


# ── ledger: real trades + how good the signals actually were ────────────────

def _signal_report_card(closed: list[dict]) -> dict:
    """Grade the engine's own calls from closed signal records."""
    def bucket(records: list[dict]) -> dict:
        graded = [r for r in records if r.get("return_pct") is not None]
        alphas = [r["alpha_pct"] for r in graded if r.get("alpha_pct") is not None]
        wins = sum(1 for r in graded if r["return_pct"] > 0)
        return {
            "count": len(records), "graded": len(graded), "wins": wins,
            "win_rate": round(wins / len(graded), 2) if graded else None,
            "avg_return": round(sum(r["return_pct"] for r in graded) / len(graded), 2) if graded else None,
            "avg_alpha": round(sum(alphas) / len(alphas), 2) if alphas else None,
        }
    return {"all": bucket(closed),
            "longterm": bucket([r for r in closed if r.get("mode") == "longterm"]),
            "swing": bucket([r for r in closed if r.get("mode") == "swing"])}


@app.get("/ledger", response_class=HTMLResponse)
def ledger_page(request: Request, saved: int = 0, error: str = ""):
    from datetime import date as _date

    from bling import ledger as L
    from bling.pulse import live_quote

    # fresh quotes for open positions (cache closes can be a day old)
    base_positions = L.positions()
    prices: dict[str, float] = {}
    if base_positions:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {p["ticker"]: pool.submit(live_quote, p["ticker"]) for p in base_positions}
            for t, f in futures.items():
                try:
                    price, _ = f.result(timeout=10)
                    if price:
                        prices[t] = price
                except Exception:
                    pass
    positions = L.positions(prices=prices or None)
    perf = L.performance(prices=prices or None)
    open_signals = L.signals(status="open")
    closed_signals = L.signals(status="closed")
    trade_rows = list(reversed(L.trades()))
    return templates.TemplateResponse(request, "ledger.html", {
        "saved": saved, "error": error,
        "positions": positions, "perf": perf,
        "open_signals": open_signals[:60], "closed_signals": closed_signals[:60],
        "signal_card": _signal_report_card(closed_signals),
        "trades": trade_rows[:100], "today": _date.today().isoformat(),
    })


@app.post("/ledger")
async def ledger_add_trade(request: Request):
    from urllib.parse import quote

    from bling import ledger as L
    form = await request.form()

    def clean_number(name: str) -> float:
        return float(str(form.get(name) or "0").replace(" ", "").replace(",", "."))

    try:
        L.record_trade(
            ticker=str(form.get("ticker") or ""),
            side=str(form.get("side") or ""),
            shares=clean_number("shares"),
            price=clean_number("price"),
            date=str(form.get("date") or "").strip() or None,
            mode=str(form.get("mode") or "longterm"),
            note=str(form.get("note") or "").strip(),
        )
    except (ValueError, TypeError) as err:
        return RedirectResponse(f"/ledger?error={quote(str(err))}", status_code=303)
    return RedirectResponse("/ledger?saved=1", status_code=303)


@app.get("/push", response_class=HTMLResponse)
def push_setup(request: Request, tested: int = 0, prefs_saved: int = 0):
    from bling.notify import get_prefs, get_topic
    return templates.TemplateResponse(request, "push.html", {
        "topic": get_topic(), "tested": tested,
        "prefs": get_prefs(), "prefs_saved": prefs_saved,
    })


@app.post("/push/prefs")
async def push_prefs(request: Request):
    from bling.notify import save_prefs
    form = await request.form()
    save_prefs({key: form.get(key) == "on" for key in
                ("longterm_buy", "holding_sell", "swing_buy", "watch", "runway_monthly")})
    return RedirectResponse("/push?prefs_saved=1", status_code=303)


@app.post("/push/test")
def push_test():
    from bling.notify import push as send_push
    send_push("💰 Bling test", "Push channel confirmed — this is what signal alerts will look like.", "/")
    return RedirectResponse("/push?tested=1", status_code=303)


@app.get("/finances", response_class=HTMLResponse)
def finances_page(request: Request, saved: int = 0, edit: int = 0):
    from bling.finance import transactions
    finances = store.load()
    return templates.TemplateResponse(request, "finances.html", {
        "f": finances, "report": build_report(finances), "saved": saved, "edit": edit,
        "targets": build_targets(finances),
        "holdings": live_holdings(finances),
        "tx": transactions.load(),
    })


@app.post("/finances")
async def finances_save(request: Request):
    """Rows arrive as parallel form arrays per section."""
    form = await request.form()

    def rows(section: str, fields: tuple[str, ...]) -> list[dict]:
        columns = [form.getlist(f"{section}_{field}") for field in fields]
        parsed = []
        for values in zip(*columns):
            if not values[0].strip():
                continue
            row = {"name": values[0].strip()}
            for field, value in zip(fields[1:], values[1:]):
                try:
                    row[field] = float(value.replace(" ", "").replace(",", ".") or 0)
                except ValueError:
                    row[field] = 0.0
            parsed.append(row)
        return parsed

    finances = store.load()
    finances.cash = [LineItem(r["name"], r["amount"]) for r in rows("cash", ("name", "amount"))]
    finances.investments = [LineItem(r["name"], r["amount"]) for r in rows("inv", ("name", "amount"))]
    finances.income = [LineItem(r["name"], r["amount"]) for r in rows("inc", ("name", "amount"))]
    finances.expenses = [LineItem(r["name"], r["amount"]) for r in rows("exp", ("name", "amount"))]
    finances.debts = [Debt(r["name"], r["balance"], r["monthly_payment"], r.get("interest_rate", 0.0) / 100.0)
                      for r in rows("debt", ("name", "balance", "monthly_payment", "interest_rate"))]
    holdings = []
    for r in rows("hold", ("name", "shares", "cost_basis", "stop_price")):
        holdings.append(Holding(r["name"].upper(), r["shares"], r["cost_basis"], r.get("stop_price", 0.0)))
    finances.holdings = holdings
    store.save(finances)
    return RedirectResponse("/finances?saved=1", status_code=303)
