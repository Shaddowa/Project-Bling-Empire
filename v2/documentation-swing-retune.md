# Swing retune — from days to 1–2 months (2026-07-01)

Hanna wants swing trades held ~1–2 months, not days. The old swing rule (three-tool
composite in AND out) averaged **11 trading days** per hold. This note is the empirical
retune of the **exit** — the entry stays a three-tool BUY in an uptrend.

## Method

- **Universe**: the 153 names passing the quality screen today (Oslo + S&P 500, was
  ~137 at the last README refresh) ∪ the 149-name current swing universe → 273 tickers,
  268 with usable cached history (~10y daily). **Cached bundles only, zero network.**
- **Entry (all variants)**: three-tool composite BUY (MACD 8/17/9 + stochastic 14/5 +
  10-day SMA all bullish) while close > 200-day SMA.
- **Execution**: a condition seen at the close of day *t* trades at the close of day
  *t+1* — no look-ahead. **0.15%/side** costs on every position change.
- **Portfolio**: equal-weight average of per-ticker daily strategy returns.
- Win rate is net of costs; open trades are marked to market. "Hold" = trading days.
- Harness: scratchpad `exit_backtest.py` (session scratchpad), results reproduced twice.

## Round 1 — the four specified exits

| Exit variant | CAGR | maxDD | Sharpe | Win | Avg hold | Trades/yr/name |
|---|---|---|---|---|---|---|
| (a) three-tool flip (old rule) | +8.8% | −10.9% | 0.85 | 42% | 11.3d (med 9) | 7.7 |
| (b) close < 20-day SMA | +7.5% | −14.6% | 0.68 | 40% | 10.5d (med 5) | 9.2 |
| (c) close < 50-day SMA | +10.0% | −16.5% | 0.75 | 40% | 12.8d (med 1) | 9.3 |
| (d) 2R target or close < 50-day SMA | +7.8% | −16.6% | 0.62 | 44% | 9.9d (med 2) | 11.3 |

**None reached the 20–60-day target.** Diagnosis: the three-tool BUY often fires while
price is still *below* the 20/50-day SMA (early in a rebound), so SMA exits trigger the
very next day — variant (c)'s **median hold was 1 day**. The exit line must also gate
the entry.

## Round 2 — gate the entry above the exit line

| Exit variant | CAGR | maxDD | Sharpe | Win | Avg hold | Trades/yr/name |
|---|---|---|---|---|---|---|
| (b2) entry > 20SMA, exit close < 20SMA | +8.1% | −13.5% | 0.75 | 39% | 12.6d | 7.4 |
| (c2) entry > 50SMA, exit close < 50SMA | +12.0% | −14.0% | 0.91 | 37% | 22.6d | 5.0 |
| **(c3) entry > 50SMA, exit 2 consecutive closes < 50SMA — SHIPPED** | **+14.2%** | **−15.6%** | **0.99** | **37%** | **30.3d (med 17)** | **4.0** |
| (d2) entry > 50SMA, 2R or close < 50SMA | +9.8% | −13.9% | 0.79 | 44% | 15.6d | 6.9 |

Robustness checks:

- (c4) 3 consecutive closes < 50SMA: +15.2% CAGR, −18.8% maxDD, Sharpe 1.00, 36.3d —
  the surface around c3 is smooth (no fluke peak); c3 keeps the shallower drawdown.
- Last ~2 years only: (a) +3.4%/Sharpe 0.74 · (c2) +6.9%/1.21 · **(c3) +7.9%/1.30** —
  the ranking holds in the recent regime, not just the full decade.
- 2R profit targets consistently HURT (d, d2): they amputate exactly the multi-month
  winners this mode now exists to ride. Win rate up, everything else down.

## Decision — SHIPPED

**Enter** on a three-tool BUY while close > 200-day SMA **and** close > 50-day SMA.
**Exit** after **two consecutive closes below the 50-day SMA**, executed next close.

- Avg hold **30.3 trading days ≈ 6 calendar weeks** (median 17) — squarely in the
  1–2-month band Hanna asked for.
- Best risk-adjusted return of every variant in the target band (Sharpe 0.99 vs 0.85
  for the old rule) with +5.4pp CAGR and ~half the trades (4.0 vs 7.7/yr/name → less
  cost and tax friction).
- Note the trade-shape change: win rate *drops* to ~37% but average winners get much
  bigger — this is a trend-following profile (many small scratches, occasional
  multi-month runners), not the old scalp profile. Don't judge it by win rate alone.

Implemented in `bling/modes.py`:

- `swing_position_and_trades()` — bar-by-bar simulator of exactly this rule
  (next-close execution, costs, confirm-days counter).
- `swing_trade_stats()` — per-name 2y stats now reflect the SHIPPED rule, net of
  0.15%/side, and add `avg_hold_days`.
- `swing_scan()` — entry gate now also requires close > 50-day SMA, so the dashboard
  never surfaces a setup the shipped rule wouldn't take. On today's cache: 136 fresh
  setups, per-name avg hold ≈ 28.6 trading days.

Constants: `SWING_EXIT_SMA = 50`, `SWING_EXIT_CONFIRM_DAYS = 2`, `SWING_COST = 0.0015`.
The long-term engine's hybrid rule (`backtest.position_series`, 200-day exit) is
untouched — this retune is the swing mode only.

## Caveats (honesty section)

- Same survivorship caveat as the README: today's quality winners backtested over the
  decade that made them winners. Trust the *comparisons* between variants (identical
  universe/costs/execution), not the absolute CAGR levels.
- Per-name 2y stats now contain fewer trades (~4/yr instead of ~8) — a single name's
  win rate is noisier; the portfolio table above is the real evidence.
- Follow-ups for whoever touches this next (files not owned by this change):
  `dashboard/templates/swing.html` mode description still says "exit when all three
  flip bearish / days-to-weeks" and could show the new `avg_hold_days` column;
  `scripts/refresh_and_notify.py` pushes only win-rate ≥ 60% names — under the new
  ~37%-win-rate profile that threshold mutes most pushes and should be rethought
  (e.g. avg_trade_return > 0 or strategy_return > hold_return).
