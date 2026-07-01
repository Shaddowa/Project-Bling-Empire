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
from bling.finance.model import Debt, Holding, LineItem, build_report  # noqa: E402
from dashboard import auth  # noqa: E402

OUTPUT_DIR = V2_ROOT / "output"
UNIVERSE_LABELS = {"oslo": "Oslo Børs", "sp500": "S&P 500"}

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
    rows = []
    for holding in finances.holdings:
        report = analyze_ticker(holding.ticker, max_age=timedelta(days=1))
        price = report.valuation.price
        value = price * holding.shares if price else None
        gain = None
        if price and holding.cost_basis:
            gain = (price / holding.cost_basis - 1.0) * 100.0
        rows.append({
            "ticker": holding.ticker, "name": report.name, "shares": holding.shares,
            "price": price, "currency": report.currency, "value": value,
            "gain_pct": round(gain, 1) if gain is not None else None,
            "guidance": report.sell_guidance or "—",
            "signal": report.signal.signal,
        })
    return rows


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
    if (request.url.path not in open_paths
            and not request.url.path.startswith("/static/")
            and not logged_in(request)):
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


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
    cards = {}
    for universe in UNIVERSE_LABELS:
        day, rows = load_signals(universe)
        cards[universe] = {
            "day": day,
            "buy": [r for r in rows if r["ACTION"] == "BUY"],
            "watch": [r for r in rows if r["ACTION"] == "WATCH"],
        }
    return templates.TemplateResponse(request, "index.html", {
        "cards": cards, "labels": UNIVERSE_LABELS,
        "finances": finances, "report": report,
        "holdings": live_holdings(finances),
    })


@app.get("/signals/{universe}", response_class=HTMLResponse)
def signals(request: Request, universe: str, action: str = ""):
    day, rows = load_signals(universe)
    if action:
        rows = [r for r in rows if r["ACTION"] == action.upper()]
    return templates.TemplateResponse(request, "signals.html", {
        "universe": universe, "label": UNIVERSE_LABELS.get(universe, universe),
        "day": day, "rows": rows[:400], "action": action.upper(),
    })


@app.get("/ticker/{symbol}", response_class=HTMLResponse)
def ticker(request: Request, symbol: str):
    report = analyze_ticker(symbol.upper(), max_age=timedelta(days=1))
    return templates.TemplateResponse(request, "ticker.html", {"r": report})


@app.get("/push", response_class=HTMLResponse)
def push_setup(request: Request, tested: int = 0):
    from bling.notify import get_topic
    return templates.TemplateResponse(request, "push.html", {"topic": get_topic(), "tested": tested})


@app.post("/push/test")
def push_test():
    from bling.notify import push as send_push
    send_push("💰 Bling test", "Push channel confirmed — this is what signal alerts will look like.", "/")
    return RedirectResponse("/push?tested=1", status_code=303)


@app.get("/finances", response_class=HTMLResponse)
def finances_page(request: Request, saved: int = 0):
    from bling.finance import transactions
    finances = store.load()
    return templates.TemplateResponse(request, "finances.html", {
        "f": finances, "report": build_report(finances), "saved": saved,
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
    for r in rows("hold", ("name", "shares", "cost_basis")):
        holdings.append(Holding(r["name"].upper(), r["shares"], r["cost_basis"]))
    finances.holdings = holdings
    store.save(finances)
    return RedirectResponse("/finances?saved=1", status_code=303)
