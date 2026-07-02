# Project Bling Empire — v2 signal engine

The v1 engine (repo root) ranked companies by quality criteria and wrote CSVs. v2 keeps
that philosophy — the [Notion knowledge base](https://relieved-walker-58b.notion.site/Project-Bling-Empire-dbee9a3b0f1a41febc0098a6e901188c)
(Rule #1 / value investing) is still the spec — and adds the three things a "when do I
actually buy and sell?" system needs:

1. **Valuation** — a *price* to act on, not just a quality rank: sticker price,
   margin-of-safety (MOS) price, ten-cap price, payback time.
2. **Timing signals** — Phil Town's three tools (MACD 8/17/9, stochastic 14/5,
   10-day SMA) plus a 200-day trend state → BUY / HOLD / SELL per stock.
3. **Backtesting** — measures what the timing rules would have done over the last
   10 years, after transaction costs, against buy & hold. No claims, just numbers.

## How a stock earns a BUY

Every rung must hold — the system is designed to say "no" almost always:

| Rung | Question | Test |
|---|---|---|
| Quality | Wonderful company? | ≥60% of the Notion criteria pass: Big Four growth ≥10%/yr (net income, book value+dividends, sales, operating cash flow), ROE ≥15%, ROIC ≥15%, owner earnings growth ≥10%, FCF increasing, debt < 4y of FCF |
| Valuation | Wonderful price? | Below the MOS price (half the sticker price), or payback ≤ 8y while below sticker |
| Timing | Is the market done marking it down? | All three tools bullish |

`WATCH` = right company, right price, wrong timing (the shopping list — these become
BUYs when the tools flip). `FAIR` = right company, wrong price. `AVOID` = failed quality.
For holders every row carries sell guidance: `SELL` when all three tools turn bearish,
`TAKE PROFIT` when price exceeds the sticker price.

Missing data never counts in a stock's favor: unknown criteria simply don't pass, and
financial-currency vs trading-currency mismatches (Kitron reports EUR, trades NOK) are
FX-converted rather than compared raw.

## Usage

```bash
cd v2
python3 -m venv env && source env/bin/activate
pip install -r requirements.txt

python -m bling run --universe oslo sp500   # screen -> output/<date>/signals_*.{csv,html}
python -m bling analyze KIT.OL              # one-ticker deep dive with reasons
python -m bling backtest --universe oslo --qualified-only   # validate the timing rules
```

Data comes from Yahoo Finance via `yfinance` (free, no API key) and is cached in
`v2/cache/` — a re-run or backtest after a screen costs no new requests.

## Timing rules: what the backtest actually said (2026-07-01)

Backtested on the 137 stocks that passed the quality screen (Oslo + S&P 500,
10 years daily, 0.15%/side costs, signals traded next close, no look-ahead):

| Rule | CAGR | Max drawdown | Sharpe | Trades/yr |
|---|---|---|---|---|
| Three tools in AND out (pure Phil Town) | +12.8% | −20.3% | 0.71 | 10.7 |
| 200-day SMA only | +22.5% | −29.2% | 1.12 | 3.6 |
| **Hybrid: three-tool entry, 200-day exit (shipped)** | **+23.5%** | **−25.8%** | **1.20** | **2.7** |
| Buy & hold (same names) | +47.8%* | −60.1% | 1.21 | 0 |

\* inflated by survivorship — these are *today's* quality winners measured over the
exact decade that made them winners. Ignore the level; trust the comparisons.

Conclusions baked into the engine:
- **Exiting on three-tool flips whipsaws away half the return.** The tools are good
  at *entries* (they demand the downtrend has stopped), terrible as exits.
- So the shipped rule is: **enter** when quality + price + three tools + 200-day trend
  all agree; **exit** (sell guidance) only on a 200-day trend break or price above
  sticker. Tool flips while above trend = "HOLD, watch the 200-day line".
- ~2.7 trades/yr keeps costs and (non-ASK) tax friction low.
- The drawdown line is the low-risk part: −26% worst case vs −60% unhedged.

## Honesty section (read this, future us)

- **No system reliably beats the market.** What this engine does is enforce discipline:
  only quality companies, only at a discounted price, only with the trend confirming,
  and an explicit exit rule. The margin of safety is the low-risk part — the edge, if
  any, comes from *not* buying 95% of the time.
- The backtest is the referee. If `backtest --qualified-only` shows the timing rules
  underperforming buy & hold on quality names, believe it — trade less, hold longer.
- Yahoo gives ~4 years of annual statements, so "growing ≥10%/yr" is measured over a
   shorter window than Rule #1's ideal 10 years. Treat scores as screens, not verdicts.
- Screens run on statements; they know nothing about news, fraud, or that a cycle peaked
  (Equinor scores badly *because* 2022 was an oil-price peak — that is the screen working).

## Live dashboard (VPS)

`v2/dashboard/` is a phone-first FastAPI app (login-protected, single password in
`v2/.dashboard-creds`, hash in `v2/data/auth.json`) deployed on the VPS:

- **systemd**: `bling-dashboard.service` (uvicorn on 0.0.0.0:3400 —
  orchestrator-style: direct `http://<vps-ip>:3400`, own port, no DNS/proxy) and
  `bling-refresh.timer` → `bling-refresh.service` (weekdays 05:10 UTC: refresh
  screen, then push only *changes* to Hanna's phone via ntfy —
  new BUYs, sell-guidance changes on actual holdings, new WATCH names, and a
  monthly runway status). Unit files in `v2/deploy/`.
- **Pages**: overview (runway + holdings guidance, everything in the three-word
  BUY / HOLD / SELL vocabulary), full signal tables, per-ticker deep dive, a
  **Swing tab** (1–2-month trend rides: three-tool entry while price sits above
  both the 50- and 200-day lines, exit after two consecutive closes below the
  50-day SMA — ~37% win rate but winners run; each name shows its own 2-year
  track record under exactly these rules, see `documentation-swing-retune.md`),
  an intraday check, the **Ledger** (real trades + the engine's graded report
  card + the enforced **investment policy**: max 5 positions, 25%-of-investable
  position cap, never above sticker, stop-out cooldown, −10% drawdown breaker,
  50% monthly deploy cap — BUYs that break policy are blocked unless explicitly
  overridden, and overrides are stamped into the ledger), and Finances —
  editable cash/income/expenses/debts/holdings stored in gitignored
  `v2/data/finances.json`, with runway scenarios ("cut 10%", "+10 000 kr/mo", …)
  and the number that matters: extra monthly income needed to break even or to
  hold an 18-month runway.

## Notes for Norwegian investors

- **Use an aksjesparekonto (ASK)** for stocks/funds domiciled in the EEA — Oslo Børs
  and most European listings qualify; gains compound tax-deferred and you keep the
  skjermingsfradrag. US stocks (S&P 500 universe) do *not* fit in an ASK — they belong
  in a regular aksje- og fondskonto, where each sale is a taxable event; the engine's
  lower-turnover WATCH→BUY→hold flow suits that account type better than day-trading.
- Dividends from US stocks carry 15% withholding tax (reclaimable as credit).
- S&P 500 positions add USD/NOK currency exposure on top of stock risk — a NOK-priced
  Oslo portfolio and a USD portfolio should be judged separately (the report keeps
  universes in separate files for exactly this reason).
- Nothing here is financial advice. It is a decision-support screen you built for
  yourself. Verify numbers (e.g. on the company's own investor pages) before trading.

## Layout

```
v2/bling/
  data.py          cached yfinance fetch (bundles: info, statements, 10y prices)
  fundamentals.py  statement rows -> chronological series (+ fallbacks)
  quality.py       Notion growth criteria -> PASS/FAIL/UNKNOWN + 0-100 score
  valuation.py     sticker / MOS / ten-cap / payback (FX-aware)
  signals.py       three tools + 200SMA -> BUY/HOLD/SELL
  backtest.py      per-ticker + portfolio backtest vs buy & hold, after costs
  dividends.py     dividend score 0-10 (ported from v1)
  engine.py        orchestration + the action ladder
  modes.py         swing (three-tool entry / 50-day exit, 1-2mo holds) + day view
  ledger.py        real trades (FIFO) + graded signal records, all vs index
  policy.py        the enforced investment policy (sizing/cooldown/breaker/caps)
  report.py        ranked CSV + HTML
  universe.py      ticker lists (data/tickers/*.csv) minus blacklists
tests/             unit tests over the financial math, signals, ledger and policy
```
