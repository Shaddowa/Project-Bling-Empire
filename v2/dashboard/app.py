"""Bling Empire dashboard: signals + portfolio + runway, phone-first.

Run: uvicorn dashboard.app:app --host 127.0.0.1 --port 3400  (from v2/)
"""
from __future__ import annotations

import csv
import sys
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

V2_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_ROOT))

from bling.engine import analyze_ticker  # noqa: E402
from bling.finance import store  # noqa: E402
from bling.finance.model import Debt, Holding, LineItem, build_report, build_targets  # noqa: E402
from bling.universe import MARKETS, TICKER_DIR, active_universes, load_config, save_config  # noqa: E402
from dashboard import auth  # noqa: E402

OUTPUT_DIR = V2_ROOT / "output"
SWING_PATH = V2_ROOT / "data" / "swing.json"


def universe_labels() -> dict[str, str]:
    return {name: MARKETS[name]["label"] for name in active_universes()}

app = FastAPI(title="Bling Empire", docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


# ── helpers ──────────────────────────────────────────────────────────────

def logged_in(request: Request) -> bool:
    return auth.verify_session(request.cookies.get(auth.COOKIE_NAME))


def latest_output_dir() -> Path | None:
    if not OUTPUT_DIR.exists():
        return None
    days = sorted((d for d in OUTPUT_DIR.iterdir() if d.is_dir()), reverse=True)
    return days[0] if days else None


def load_signals(universe: str) -> tuple[str, list[dict]]:
    day = latest_output_dir()
    if day is None:
        return "", []
    path = day / f"signals_{universe}.csv"
    if not path.exists():
        return day.name, []
    with path.open() as fh:
        return day.name, list(csv.DictReader(fh))


def live_holdings(finances) -> list[dict]:
    from bling.engine import enrich_holding
    return [enrich_holding(analyze_ticker(h.ticker, max_age=timedelta(days=1)), h)
            for h in finances.holdings]


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
    if request.url.path == "/api/widget":  # token-authed, not cookie-authed
        if not auth.verify_widget_token(request.query_params.get("token")):
            return JSONResponse({"error": "bad token"}, status_code=401)
        return await call_next(request)
    if (request.url.path not in open_paths
            and not request.url.path.startswith("/static/")
            and not logged_in(request)):
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


@app.get("/api/widget")
def widget_api():
    """Compact JSON for home-screen widgets: runway + today's actions."""
    finances = store.load()
    report = build_report(finances)
    buys, watch_count, day = [], 0, ""
    for universe in active_universes():
        day, rows = load_signals(universe)
        buys += [r["TICKER"] for r in rows if r["ACTION"] == "BUY"]
        watch_count += sum(1 for r in rows if r["ACTION"] == "WATCH")
    sells = []
    if (V2_ROOT / "data" / "notify_state.json").exists():
        import json as _json
        guidance = _json.loads((V2_ROOT / "data" / "notify_state.json").read_text()).get("guidance", {})
        sells = [t for t, g in guidance.items() if g.startswith(("SELL", "TAKE PROFIT"))]
    holdings = [{
        "ticker": h["ticker"], "price": h["price"], "cost": h["cost"],
        "stop": h["stop"], "target": h["target"], "progress": h["progress"],
        "gain_pct": h["gain_pct"],
        "stop_hit": bool(h["guidance"].startswith("SELL NOW")),
    } for h in live_holdings(finances)]
    return {
        "updated": day,
        "runway_months": report.runway_months,
        "liquid": round(report.liquid),
        "burn": round(report.monthly_burn),
        "buys": buys[:6],
        "watch_count": watch_count,
        "sell_alerts": sells[:4],
        "holdings": holdings[:5],
    }


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
        "background_color": "#0b0e14",
        "theme_color": "#0b0e14",
        "start_url": "/",
        "icons": [{"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    })


# ── pages ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    finances = store.load()
    report = build_report(finances)
    labels = universe_labels()
    cards = {}
    for universe in labels:
        day, rows = load_signals(universe)
        cards[universe] = {
            "day": day,
            "buy": [r for r in rows if r["ACTION"] == "BUY"],
            "watch": [r for r in rows if r["ACTION"] == "WATCH"],
        }
    return templates.TemplateResponse(request, "index.html", {
        "cards": cards, "labels": labels,
        "finances": finances, "report": report,
        "targets": build_targets(finances),
        "holdings": live_holdings(finances),
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
    return templates.TemplateResponse(request, "longterm.html", {"cards": cards, "labels": labels})


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
    return templates.TemplateResponse(request, "day.html", {
        "rows": day_view(seen, max_tickers=15),
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
    report = analyze_ticker(symbol.upper(), max_age=timedelta(days=1))
    return templates.TemplateResponse(request, "ticker.html", {"r": report})


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
