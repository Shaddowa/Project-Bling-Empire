# AUDIT-NEXT — tomorrow's high-value work (written 2026-07-02, post discipline-layer ship)

Context snapshot: suite green (214 tests), policy layer live in code (`bling/policy.py`),
prod :3400 still runs pre-policy code until Hanna restarts the service. First position
RUSTA.ST pending fill. 163k liquid / 10.1k burn / 42 244 kr investable after the
12-month buffer. Ranked by **impact × evidence × effort**, drawing on the 2026-07-01
research gap analysis (Faber SSRN 962461, RFS 2017 stop-loss pre-commitment,
survivorship/selection-bias literature) plus repo state read today.

Effort: S = <half day, M = ~a day, L = multi-day.

---

## 1. Encrypted off-box backup of `v2/data/` — Effort S · Impact CRITICAL · mostly autonomous

**Why first:** `.gitignore` excludes exactly the files that matter — `finances.json`,
`auth.json`, `bank.json` (contains the **GoCardless secret_key in plaintext**),
`notify.json`, `transactions.json`, and soon `ledger.jsonl` (her permanent trade +
override accountability record). The nightly VPS backup pushes to GitHub, which must
never hold plaintext finances — so today these files exist on **one disk on one VPS.
A single disk failure erases her financial state and the entire ledger history.**
Every other item on this list writes *more* data into that unprotected directory.

**Shape:** nightly cron → `tar czf - v2/data | openssl enc -aes-256-cbc -pbkdf2 -pass file:…`
(or `gpg --symmetric`; both already on the box, zero new deps) → push the ciphertext
blob to the existing private backup repo or rclone target. Keep 14 rotations. Add a
restore-test script that decrypts and diffs md5s so the backup is *proven*, not assumed.

**Needs Hanna:** only the passphrase custody decision (she must store a copy off-VPS —
password manager / iCloud note). Build + cron + restore-test are autonomous; ship it
with a generated passphrase in a mode=600 file and a push telling her to copy it out.

## 2. Index-level 200-day regime gate on new BUYs — Effort S · Impact HIGH · autonomous

**Why:** the single best-evidenced signal-quality gap from the research pass. Per-ticker
200d filters exist, but momentum BUYs cluster late in bull markets; Faber's index-level
long-MA filter is the documented drawdown-cutter (S&P maxDD ~50% → teens at similar CAGR).
**The data is already cached daily**: `refresh_index_cache()` (ledger.py:132) warms
OSEBX/OMXS30/S&P bundles, and `index_symbol_for()` maps any ticker to its benchmark —
today used only for *grading*, never *gating*. ~10 lines in the entry path + a policy/
engine note ("🌧 market below its 200-day — new buys wait"), plus backtest evidence in
`backtest.py` to prove it on her universe before it gates anything.

**Honesty note:** sell it as insurance (drawdown/whipsaw trade-off), not alpha. Make it
a `warn`-severity policy rule first; promote to blocking only if the universe backtest
supports it.

## 3. GoCardless consent-expiry countdown — Effort S · Impact MED-HIGH · autonomous

**Why:** PSD2 bank consents expire (typically 90 days). When the DNB + Bank Norwegian
requisitions lapse, `bank_sync.py` silently stops updating cash and **every downstream
number is wrong** — investable, buffer, position caps, runway — while looking fresh.
`bank.json` already stores requisition IDs; the requisitions API returns `created` +
status, so the countdown needs no new consent flow. Surface "bank link expires in N days"
on /finances, and push at N=7 and N=1 with the reconnect link (`bank_sync.py connect`
already prints it). This protects the integrity of everything the policy layer computes.

## 4. Position-sizing suggestion at BUY time — Effort S · Impact MED · autonomous

**Why:** research gap #1 was "no sizing code exists". The policy layer now *caps* size
(25% ≈ 10.5k), and at the default 8% stop the cap implies ~845 kr risk ≈ 2% of investable
— coincidentally the textbook fixed-fractional maximum. But a cap answers "how much is
too much", not **"how many shares should I buy?"** Add
`suggested_shares(ticker, price, risk_pct=0.01)` = `(investable × risk%) / (entry − stop)`,
show it on every BUY signal card and pre-fill the /ledger add-trade form. Turns the last
discretionary decision (size) into a computed one. Show 1% and 2% variants; never block.

## 5. Norwegian tax: ASK-vs-aksjekonto note + ledger tax report — Effort M · Impact MED-HIGH · **needs Hanna first**

**Why:** the single biggest unmodeled friction. Gains outside an aksjesparekonto (ASK)
are taxed ~37.84% on realization; inside ASK they defer and compound, plus
skjermingsfradrag shelters a risk-free-rate slice. On 1–2-month swings this is the
difference between keeping ~100% vs ~62% of every win at year-end. RUSTA.ST (SEK, EEA-
listed) **is ASK-eligible.** Code today mentions tax nowhere.

**Sequence:** (a) tiny, tonight-able: a docs/dashboard note "confirm the RUSTA fill lands
in an ASK — if Nordnet account isn't ASK, open one before filling" → **needs Hanna's
answer on which account type she trades from**; (b) then autonomous: a `/ledger` tax
section computing realized gains per calendar year from FIFO round trips, ASK vs
ordinary treatment, skjermingsfradrag estimate. Value grows with every trade recorded —
build the report before the ledger has a year of history in the wrong shape.

## 6. yfinance fallback data source — Effort M · Impact MED · autonomous

**Why:** every price, index bundle, and morning push flows through yfinance, an
unofficial scraper that breaks without notice (rate-limit waves are well documented).
Caches + stale-while-revalidate (`pulse.py`) already soften this, but a multi-day break
= blind dashboard + missed SELL/stop alerts, exactly when volatility is high. Stooq
serves EOD OHLC as plain CSV over HTTP (`https://stooq.com/q/d/l/?s=…`) — **zero new
deps** — and covers OSE/OMX tickers. Wire it as a fallback seam behind the existing
`_fetch_*` seams (events.py pattern), EOD-only, clearly labeled "fallback data" in the
UI. Don't chase intraday parity; the swing/long modes only need closes.

## 7. `stop_placed` flag + nag until the real broker stop exists — Effort S · Impact MED (best evidence-per-line) · autonomous

**Why:** the RFS-2017 finding the policy rules text already cites: automatic broker
stops change behavior, dashboard reminders don't. The system computes `effective_stop`
but nothing tracks whether the **real Nordnet stop order was actually placed**. Add a
boolean per holding (finances holdings row or ledger event), a one-tap "stop placed ✓"
on the holding card, and an escalating nag (overview banner + morning push) for any
holding ≥1 day old without it. ~30 lines; converts the highest-evidence behavioral
finding from prose into mechanism. Do it before/with the RUSTA fill so the habit starts
on trade #1.

## 8. Weekly digest push — Effort S · Impact LOW-MED · autonomous

**Why:** daily pushes are transactional; nothing summarizes. Sunday-evening ntfy digest:
week's P&L (kr and vs index), open positions vs stops, policy state (cooldown/breaker/
monthly budget), signal report-card delta, runway. Cheap (all functions exist in
`ledger.py`/`policy.py`/`model.py`), and it's the artifact that keeps a solo operator
reviewing the system instead of individual trades. Piggyback on `refresh_and_notify.py`
with a `notify_state.json` weekly key.

## 9. Dividend income calendar toward the ~10.6k/mo income target — Effort M · Impact MED (grows later) · autonomous

**Why:** `income_target` (model.py) is the north-star number and `dividends.py` already
scores payers — but nothing projects **kroner per month from actual holdings**, and with
zero filled positions today a calendar renders empty. Right-sized move now: a "dividend
lens" on the long-term screen (forward yield → est. annual kr at max position size,
ex-dates), so dividend income becomes visible in *selection*. The full calendar view
becomes valuable after 2–3 core positions exist. Defer the fancy version; ship the lens.

## 10. Paper-trading / shadow-ledger mode — Effort M · Impact LOW now · autonomous — DEFER

**Why honest:** valuable the day she wants to change strategy parameters with real money
at stake; today the *backtester* already answers "would the retuned rule have worked",
and the ledger has zero real trades to protect. A `"paper": true` flag on
`record_trade` + separate stats bucket is the cheap core if wanted, but it ranks below
everything above. Revisit after the first strategy retune post-live-trading.

## 11. DNB Spare / Firi holdings sync — **BLOCKED on Hanna** · Effort M-L

**Why blocked:** GoCardless requisitions cover bank *payment* accounts; DNB Spare (fund
platform) and Firi (crypto) need their own credentials/API keys only she can issue, and
Firi API tokens carry withdrawal-scope risk that needs her explicit scoping. Until then
`investments: []` stays manual. Ask her for: (a) whether DNB Spare has holdings worth
syncing, (b) a read-only Firi API key if she holds crypto there. Build is straightforward
once keys exist (Firi has a plain REST API; hold it to read-only scope).

---

## Hygiene batch (bundle into any session, ~1h total, autonomous)

- **`SWING_MAX_HOLD_DAYS = 28`** (ledger.py) still grades swing signals on a
  days-to-weeks window while the retuned profile holds ~30 *trading* days — winners get
  time-boxed to "expired" before the rule would have exited. Move to ~45 calendar days;
  known carry-over from the discipline-layer report.
- **Win-rate small-sample caveat:** flag per-ticker swing `win_rate` when `trades < 10`
  ("small sample — could be luck") on /swing and signal cards; the scan ranks by in-sample
  win rate, which is the selection-bias hole the research pass flagged.
- **Trade↔signal linkage:** optional `signal_id` on `record_trade` so "did following the
  engine beat overriding it?" is answerable in a year. Cheap now, impossible to backfill.
- **Prod restart reminder:** :3400 serves pre-policy code; the policy card, override flow,
  and cooldown/breaker pushes are inert in prod until Hanna restarts the service
  (**needs Hanna** — standing rule: agents never restart services).

## Suggested tomorrow (if run autonomously overnight)

1 (backup, minus passphrase handoff) → 3 (consent countdown) → 7 (stop_placed) →
2 (regime gate, warn-mode + backtest evidence) → hygiene batch. Items 5a, 11, and the
prod restart are queued questions for Hanna's morning.
