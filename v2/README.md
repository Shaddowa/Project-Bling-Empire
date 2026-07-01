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
  report.py        ranked CSV + HTML
  universe.py      ticker lists (data/tickers/*.csv) minus blacklists
tests/             31 unit tests over the financial math and signal logic
```
