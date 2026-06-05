# Traadingbot1 — Improvement Roadmap

Derived from `Traadingbot1-Review.md` (June 5, 2026).
Phases are ordered: safety first, then soundness, then ceiling.

---

## Phase 0 — Stop the Bleeding ✅ (done June 5, 2026)

**Goal: don't lie to yourself with bad numbers, don't deploy a negative-Sharpe strategy.**

- [x] **Fix Sharpe bug in `metrics.py`** — per-bar equity_curve was being passed to `sharpe()` which assumes daily data, overstating annualisation by `sqrt(390) ≈ 19.7×` (produced Sharpe = −81). Fixed: added minimum 10-point guard and documented the daily-only contract. `evaluate.py` now always uses `daily_equity` and warns on short OOS windows.
- [x] **Adopt validation rule** — no live deployment until positive cost-adjusted OOS on a multi-year window. Encoded as a decision, not just code: the ORB strategy is FAIL until further notice.
- [x] **Secrets audit** — `.env` was never committed. Variable names only (no actual keys) appear in code. Clean.
- [x] **Relabel misleading "Day Trades 0/3" stat card** — PDT doesn't apply (account > $25k). Replaced with "Weekly Trades X/5" from `memory/TRADE-LOG.md`.
- [x] **Add bot heartbeat** — `BotStatusPanel` now shows last git commit age. Turns red on weekdays if no commit in 26+ hours (silent failure indicator).
- [x] **Add last-run dates to routine rows** — each routine shows the last date it ran, sourced from memory files.
- [x] **Show backtest PASS/FAIL verdict** on the dashboard alongside the run count.
- [x] **Save `Traadingbot1-Review.md`** to repo root.

---

## Phase 1 — Make It Safe (weeks 1–3)

**Goal: even if the strategy is wrong, you can't blow up.**

- [ ] **Risk-based position sizing** — size by `(entry − stop) × shares = 0.5–1% of equity`, not notional %. The current 20% notional treats a 1%-ATR ETF the same as a 4%-ATR catalyst stock.
- [ ] **Daily/weekly max-loss circuit breaker** — hard limit: if daily P&L ≤ −2% or weekly ≤ −5%, halt new entries automatically (write PAUSE-FLAG.txt).
- [ ] **Pre-trade risk-veto layer** — a single function in front of every order that checks: size limit, heat, sector concentration, event-window proximity, circuit-breaker state. If it fails, the order does not go.
- [ ] **Marketable-limit orders** — replace market orders with limit orders at ask+5bps (longs) to cap slippage, especially at the open on gappy names.
- [ ] **Clarify initial stop logic** — the −7% hard cut fires *before* the 10% trailing stop binds on the downside. Document them as two separate roles: initial risk = 7%, trailing = profit-protection after position is in profit.

---

## Phase 2 — Make It Sound (weeks 3–6)

**Goal: the code matches the strategy, and you can trust the numbers.**

- [ ] **Replace `scripts/alpaca.sh` shell-out with `alpaca-py` SDK** — subprocess + curl per call blocks the FastAPI event loop, is fragile to parse, and is a shell-injection risk. Use async Python HTTP directly.
- [ ] **SQLite as source of truth for trades and equity** — git-as-database with regex-from-prose P&L has no concurrency control and loses data on failed commits. Generate markdown *from* the DB, not the other way around.
- [ ] **Unit tests for sizing, stop placement, and the entry gate** — a bug in `metrics.py` produced Sharpe = −81 for 6 runs unnoticed. The execution rules need deterministic, automated verification.
- [ ] **Backtest universe audit for look-ahead/survivorship** — `DEFAULT_UNIVERSE` in `evaluate.py` is a static 10-symbol list (AAPL, NVDA, etc.) — not a pre-market unknown universe. If candidates are selected with knowledge of which names moved, all results are fiction.
- [ ] **Fix `metrics.py` for short windows** — Sharpe returns 0.0 for < 10 days; document this clearly in result JSON so the `orb_20260605_012702` result is explicitly flagged as unreliable.
- [ ] **Pull VIX and facts from real APIs** — not Perplexity. VIX from a market data feed; economic calendar from a calendar API. Reserve LLM for synthesis, not numbers.

---

## Phase 3 — Make It Honest (weeks 4–8, overlaps Phase 2)

**Goal: see what's actually happening, not what you hope is happening.**

- [ ] **Live risk/heat panel on dashboard** — gross exposure, % deployed, largest single-name exposure, sector concentration, portfolio beta, distance from daily/weekly loss limit.
- [ ] **Per-position risk detail** — for each open position: entry, current stop, distance to stop in $ and %, current R-multiple, unrealised P&L, documented thesis/catalyst.
- [ ] **Open orders panel** — show working orders (trailing stops). If a stop was rejected by Alpaca, you'd never know from the current dashboard.
- [ ] **Execution analytics** — actual slippage vs. arrival price, fill quality, time-to-fill. Know your real costs, not your modeled ones.
- [ ] **Performance attribution** — P&L decomposed by setup, sector, regime, day-of-week, time-of-day. This is how you learn what actually works.
- [ ] **Economic calendar event gate** — flatten or tighten into CPI/NFP/FOMC/PCE. The one genuinely useful idea from the video review; cheap tail-risk reduction.

---

## Phase 4 — Raise the Ceiling (months 2–4)

**Goal: architecture that can support a real edge.**

- [ ] **Split execution (deterministic) from research (LLM)** — a remote Claude agent is fine for overnight research and weekly reviews; it is structurally incapable of intraday edges. Build a deterministic Python execution service for the hot path. Keep LLM for slow decisions.
- [ ] **Alpaca WebSocket stream → SSE/WebSocket to UI** — replace 30s REST polling with push. Makes the dashboard a trading tool, not just a review tool.
- [ ] **Surprise/positioning features** — move research from "news happened" to "news vs. what was positioned for": economic surprise index (actual − consensus), options skew, put-call ratio, dealer gamma (GEX), short interest.
- [ ] **Backtest ↔ live parity monitor** — compare live slippage/fills to backtest assumptions continuously; flag drift early.
- [ ] **Regime dashboard** — VIX term structure (contango/backwardation), breadth, cross-asset (rates/USD/credit), realized-vs-implied spread. Context for every entry.

---

## Phase 5 — Earn the Right to Go Live (month 4+)

**Goal: only after the edge is real.**

- [ ] Reproducible, positive, cost-adjusted OOS on a multi-year window (not a 2-month window).
- [ ] All Phase 1–3 controls in place: circuit breaker, risk-veto, risk-based sizing.
- [ ] Paper trading performance consistent with backtest expectations (parity check).
- [ ] Start with tiny live size (1–5% of intended capital); scale only after 3+ months of live data matching the model.

---

## Deprioritised / Removed

- **The video's reversion-scalp tactic** — instrument and timeframe mismatch (NQ futures 1-min vs. equity swings); unproven, unbacktestable break-of-structure entries.
- **Faster dashboard polling** before there's a validated edge — cosmetic improvement on a negative-Sharpe system.
- **More dashboard widgets** (beyond Phase 0 fixes) before live trading starts.
- **Merging sneaker-bot / news-scalp side projects into this codebase** — separate concerns.

---

## Quick Reference — Phase 0 Status

| Item | Status | Notes |
|------|--------|-------|
| Sharpe bug fixed | ✅ | `metrics.py` + `evaluate.py` |
| Validation rule adopted | ✅ | Decision — ORB stays FAIL |
| Secrets audit | ✅ | Clean — no keys in history |
| PDT counter relabelled | ✅ | Now "Weekly Trades X/5" |
| Heartbeat widget | ✅ | Shows last commit age, goes red if stale |
| Last-run dates on routines | ✅ | Sourced from memory files |
| Backtest verdict on dashboard | ✅ | PASS/FAIL badge |
| Review saved to repo | ✅ | `Traadingbot1-Review.md` |
