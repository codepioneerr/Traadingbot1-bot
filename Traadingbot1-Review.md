# Traadingbot1 — Professional Review & Roadmap

*Reviewed as: quant trader · systems architect · software engineer · UX designer · risk manager*
*Date: June 5, 2026 · Subject: `codepioneerr/Traadingbot1-bot` (Alpaca paper, $100k)*

---

## 0. The one thing to read first

You have built an impressive **software project** and an unproven **trading system**. Those are two different things, and the gap between them is the whole story of this review.

The hard truth, stated up front so nothing below softens it:

1. **There is no demonstrated edge yet.** Your own backtest says so. The full 2021–2026 ORB run is *negative* out-of-sample (Sharpe −1.62 frictionless, worse with costs). The only positive result is a single 2-month window (Jan–Feb 2024) with Sharpe 2.82. A 2-month win against a 5-year loss is not "promising" — it is noise, and selecting it as the deploy candidate is textbook overfitting. The negative 5-year OOS is the real signal.
2. **Your architecture and your chosen strategies are fundamentally mismatched.** ORB and news trading earn their edge in seconds-to-minutes. Your execution loop is a Claude remote agent that clones a repo, reads markdown, queries Perplexity, and decides — a minute-to-hour cycle. You cannot scalp a news spike with a system that takes 30+ seconds just to wake up and orient.
3. **The YouTube video is ~85% marketing.** The proof is prop-firm payouts (a selection-biased, B-book-adjacent business), the core "fair price reverts" claim contradicts the academic record *and contradicts itself* (he also sells you "news drift" continuation), and every example is cherry-picked with no sample size. There are two genuinely useful kernels inside it. The rest should be discarded.

None of this means stop. It means: **stay on paper, fix the validation discipline, and don't spend a week of engineering polishing execution for a strategy that hasn't earned the right to be executed.** The good news is that the engineering you've done is real and transferable; you just pointed it at the wrong layer of the problem.

---

## 1. Trading Edge Analysis

### 1.1 Your current strategy — weaknesses and blind spots

**ORB ("Opening Range Breakout") on stocks-in-play.** The premise (edge is in *universe selection* — high relative-volume catalyst names — not the OR pattern) is correct and is the actual finding of the Zarattini-style research. But your implementation has gaps:

- **The 5-year run is negative and you don't know why.** This is the only fact that matters. Until you can explain *mechanistically* why the strategy degrades out of sample, you do not have a strategy — you have a curve fit to early 2024. "Needs more investigation" is the correct status; deploying is not.
- **One run shows Sharpe −81 / −78.** That is not a bad strategy, that's a **bug**. A Sharpe of −81 is mathematically nonsensical for any reasonable annualization — almost certainly a near-zero or mis-scaled return std, or daily-vs-annualized confusion in `metrics.py`. Find and fix it before you trust *any* number the engine prints.
- **Universe construction is the whole game and it's underspecified.** "Ranked by relative volume + catalyst" — but how is the universe assembled *survivorship-free*? If you build the candidate list from data that already knows which names moved, you've leaked the future. The most common silent killer in ORB backtests is using a universe that wouldn't have been knowable at 9:30.
- **No regime conditioning on entries.** You have `regime.py` (VIX percentile) but it's unclear it gates trades. ORB works in trending/high-dispersion regimes and bleeds in chop. An unconditional ORB will average a winning regime with a losing one to roughly zero — which is what your 5-year run shows.
- **Costs are modeled but not *adverse-selection* costs.** A 5–10bps friction model is optimistic for the exact names ORB trades (high-RVOL, gappy, wide-spread small/mid caps at the open). Real slippage on a market order into the open print on a $4 catalyst stock is not 5bps.

**The autonomous swing system (the live one).** Separate from ORB, your scheduled bot is a multi-day momentum swing system (10% trailing stop, 6 positions, catalyst-gated). Its blind spots:

- **The "signal" is Perplexity prose.** Using an LLM web-search to "determine VIX, sizing mode, trade ideas" means you are trading on a *paraphrase of already-public news*, with hallucination risk on the numbers and zero determinism. By the time a catalyst is summarizable by Perplexity, it is priced. You are systematically late.
- **No definition of "sector in momentum" or "catalyst."** These gates are qualitative and LLM-judged, so they are non-reproducible. Two runs on the same day could pick different trades. You cannot backtest a discretionary LLM.
- **Entry has no edge test.** "Catalyst + sector momentum + 2:1 R:R" is a reasonable *filter*, but none of it is a measured, positive-expectancy *signal*. A filter removes bad trades; it does not create good ones.

### 1.2 The YouTube transcript: signal vs. hype

**Discard (hype / bias / unproven):**

- **The "proof."** Prop-firm payout screenshots are selection bias industrialized. Prop challenges are largely simulated/B-book; "payouts" are a marketing funnel, and the creator's real income is the Discord + YouTube, not the trading. One person's 12 months of payouts tells you nothing about expectancy — you're seeing the survivor, not the distribution.
- **"Fair price reverts after expected news."** The claim that an as-forecast print means "no new information, so the move is unfair and reverts" is wrong in both theory and data. The market's *reaction* is itself information (positioning unwinds, second-order details, guidance, whisper vs. consensus). The macro-announcement and post-earnings-drift literature shows price *continues* in the surprise direction more often than it cleanly round-trips. He even contradicts himself by separately selling you "news drift" continuation trades — you can't have an edge fading the move *and* an edge riding it without a rule that distinguishes them, which he never gives.
- **"Break of structure" entries.** Undefined, discretionary, unbacktestable. This is the part that *feels* like skill on a chart replay and evaporates in live, out-of-sample trading.
- **Instrument mismatch.** He trades 1-minute NQ futures reversions. You trade multi-day equities on Alpaca. His tactics do not port to your system at all — different microstructure, different holding period, different everything. Copying his entries into your bot is a category error.

**Keep (genuinely useful kernels):**

1. **Economic-calendar awareness as a *risk* tool, not a signal.** Knowing exactly when high-impact releases hit (CPI, NFP, FOMC, PCE) and *not getting run over* is real and free. For your swing bot the right use is defensive: tighten or flatten risk into known events, don't size up blind.
2. **Surprise magnitude (actual − consensus, normalized) is a real, studied feature.** Not "did news happen" but "how far from consensus, scaled by the typical surprise for that series." This *is* used by pros (economic surprise indices, e.g. Citi ESI). It's a legitimate input — for regime/positioning, not for 1-minute scalps.
3. **Scheduled vs. unscheduled distinction.** Treating planned releases differently from unplanned headlines is correct framing. Planned events you can prepare for (calendar); unplanned ones are a volatility/risk event to survive.

### 1.3 What pros use that retail overlooks

| Category | Retail uses | What pros add |
|---|---|---|
| News | "Did it happen" headlines | **Structured machine-readable feeds** with timestamps to the millisecond; surprise vs. consensus *and* vs. whisper; revisions to prior prints |
| Sentiment | A model's vibe summary | Options skew/put-call, **dealer gamma positioning** (e.g. GEX), short interest & borrow rates, fund-flow data |
| Liquidity | Last price | **Order-book depth, quote spread regime, ADV participation %, market-impact estimates** before sizing |
| Market structure | RSI/MACD | VWAP & relative-VWAP, **opening auction imbalances**, sector breadth, cross-asset (rates/USD/credit) confirmation |
| Macro | Headline number | **Economic surprise indices**, real-yield moves, the *reaction function* (how the asset historically responds to a given surprise) |
| Volatility | VIX level | VIX *term structure* (contango/backwardation), realized-vs-implied spread, VVIX, intraday realized vol |

The retail blind spot in one sentence: **retail trades the news; pros trade the gap between the news and what was already positioned for.** The surprise, the positioning, and the liquidity to get in and out — not the headline.

---

## 2. Dashboard Review

### 2.1 Component-by-component

What's there is clean and the visual design is good (dark, legible, sensible hierarchy). But it's a **monitoring dashboard for a system that hasn't run**, and several widgets are either misleading or irrelevant to trading performance.

- **Four stat cards (Equity / Day P&L / Open Positions / Day Trades Used).** Fine. But **"Day Trades Used 0/3" is misleading** — your own docs say PDT doesn't apply above $25k, so this counter implies a constraint you don't have. Either remove it or relabel it to the real constraint (max new trades/week 5).
- **Open Positions + Equity Curve.** Right idea. The equity curve should also show your **start-of-day baseline and current drawdown from peak**, not just a line.
- **Bot Status panel.** Useful, but Market Open / Midday are hardcoded "Pending" ("no detection yet") — so the panel lies on a live day. Wire real detection or don't show a status you can't verify.
- **P&L Calendar.** Good long-term habit-tracker. Low priority until there's data.
- **Recent Alerts.** Good. Depends on `TELEGRAM-LOG.md` which doesn't exist yet.
- **Quick Controls** (Refresh / Pause / Backtest / Close All). The **Close All** with a confirm modal is the single most important control on the page — make it impossible to miss. Pause is good.
- **Life Hub + motivational quote.** Be honest with yourself: these do **nothing for trading performance**. They're not harmful, but on a *trading* dashboard a Jesse Livermore quote and a goals tracker are decoration. Keep them collapsed (you do) or move them to a separate page. Don't let them imply the dashboard is "done."

### 2.2 What's missing (ranked by trading value)

1. **Live risk/heat panel.** Current gross & net exposure, % of equity deployed, **largest single-name and single-sector exposure**, portfolio beta, and **distance from any daily/weekly max-loss limit**. This is the most important missing widget by a wide margin.
2. **Per-position detail you can act on.** For each holding: entry, current stop, **distance to stop in $ and %, current R-multiple, unrealized P&L, and the documented thesis/catalyst**. Right now you can see P&L but not risk.
3. **Sizing mode + live VIX, prominently.** You make every sizing decision from VIX/mode, yet it's not on the dashboard. Put VIX, VIX term-structure state, and today's mode (AGGRESSIVE/MODERATE/DEFENSIVE) top-center.
4. **Economic calendar with countdown.** A live "next high-impact event in 02:14:30" banner that turns red inside a pre-event window — the one genuinely useful idea from the video, implemented as situational awareness.
5. **Open orders panel.** You show positions but not working orders (your trailing stops). If a stop got rejected, you'd never know from this screen.
6. **Bot health / heartbeat.** Last successful run time per routine, last git commit time, last error. If a remote agent silently failed (a known issue in your docs), the dashboard should scream, not sit quietly at "Running."
7. **Drawdown + circuit-breaker status.** Current DD from peak, and whether any kill-switch threshold is armed/tripped.

### 2.3 Execution speed & situational awareness

Your dashboard polls REST every 30s and the backend re-shells `alpaca.sh` on each poll. For "high-impact news situational awareness," 30s is an eternity. If you ever want this to matter intraday: **Alpaca WebSocket stream** → backend pushes to frontend over **SSE/WebSocket**, sub-second. Until then, the dashboard is a *review* tool, not a *trading* tool — which is fine, as long as you call it that.

---

## 3. Codebase & Architecture Review

### 3.1 The four structural problems

**(A) The backend shells out to bash for trades.** `main.py` calls `scripts/alpaca.sh` via subprocess, which spawns a shell and curl per call, parses string output, and blocks the FastAPI event loop. This is slow, fragile, untestable, and a **shell-injection risk** the moment any user input touches a command. Replace with the **`alpaca-py` SDK** (or `httpx.AsyncClient` with a pooled connection) called directly in async Python. This single change improves speed, reliability, security, and testability at once.

**(B) Git-as-a-database.** Storing state as markdown committed to GitHub is elegant *for passing context to an LLM agent* and **terrible as a system of record**: no concurrency control (two overlapping routines can clobber each other), P&L extracted by **regex from prose**, no transactions, and — your own doc's words — "if a run fails before committing, that day's data is lost." The EOD commit being the equity baseline for tomorrow's P&L is a **single point of failure** that will eventually corrupt your records. Fix: **SQLite (or Postgres)** as the source of truth for trades, equity snapshots, and orders. Keep markdown if you like as a *human-readable export*, generated *from* the DB — not the other way around.

**(C) LLM in the latency-critical path.** A remote agent that boots, clones, reads, queries Perplexity, and decides is a fine pattern for *slow* decisions (overnight research, weekly review, thesis checks). It is structurally incapable of intraday edges. **Split the system in two:** a deterministic, fast **execution engine** (Python service, websocket-driven, sub-second, no LLM) that runs the actual rules; and a slow **LLM research/review layer** that proposes ideas and audits behavior but never touches the hot path. Right now they're fused, which caps your strategy ceiling at "things that are fine to do once an hour."

**(D) Perplexity as a data source.** Use **real APIs for facts**: VIX from a market data feed, not an LLM; economic calendar from a calendar API; quotes/bars from Alpaca. Reserve the LLM for *synthesis and narrative*, where hallucinating a number doesn't put on a position.

### 3.2 Performance, reliability, maintainability

- **Async + caching:** Wrap all outbound calls in `httpx.AsyncClient`; cache `/api/account`, `/api/positions`, `/api/equity-history` for ~5–15s so 30s polling from N tabs doesn't fan out into N×(shell+curl) round trips. Today every dashboard refresh hammers Alpaca.
- **Blocking I/O:** subprocess in an async endpoint blocks the loop unless offloaded — another reason to drop the shell-out.
- **Tests:** there appear to be none. With money (even paper) on the line, the execution rules (sizing, stop placement, entry gate) need unit tests. A bug in `metrics.py` already produced Sharpe −81 and you didn't catch it for 6 runs.
- **Determinism in backtest:** pin data versions, seed any randomness, and snapshot the universe so a rerun reproduces byte-for-byte. Right now you can't fully trust a result you can't reproduce.

### 3.3 Security (fix these regardless of strategy)

- **Public repo.** `github.com/codepioneerr/Traadingbot1-bot` is public. Verify `.env` and every key was **never committed in history** (`git log -p -- .env`, scan with `gitleaks`). If anything leaked, **rotate all keys now**. Your account number and Telegram chat ID are already in the guide doc.
- **Secrets in routine prompts.** Credentials pasted into claude.ai routine prompts are stored in those routines. Rotating a key means editing every routine. Move to a secrets manager / env injection and reference, don't embed.
- **`localStorage` password.** A single shared password in `localStorage` is XSS-exposed and grants close-all-positions power. At minimum use a short-lived token; ideally real auth. The Close All endpoint deserves a second factor or a typed-confirmation.

### 3.4 How institutional infra differs

Pros separate **strategy / execution / data / risk** into independent services; run a deterministic execution engine with microsecond logging and order-state reconciliation; treat the **risk service as a veto layer that sits in front of every order** (not as rules sprinkled in business logic); maintain a tick-level data lake with point-in-time correctness; and never put a non-deterministic component in the order path. You don't need their scale — but the *separation of concerns*, the *risk-as-a-gate*, and *deterministic execution* are adoptable today and are exactly what's missing.

---

## 4. Profitability Improvements (ranked)

Impact / Difficulty / Time are 1–5 (5 = highest impact, hardest, longest).

| # | Improvement | Impact | Difficulty | Time | Why it's an edge |
|---|---|---|---|---|---|
| 1 | **Stop treating the 2-month window as validation; require positive, cost-adjusted OOS on the full period before any live consideration** | 5 | 1 | 1 | Prevents deploying a curve fit — the highest-EV decision you can make is *not* losing money on a non-edge |
| 2 | **Fix the `metrics.py` Sharpe bug** | 5 | 2 | 1 | Every downstream decision rests on these numbers; one is provably wrong |
| 3 | **Audit the backtest universe for look-ahead/survivorship** | 5 | 3 | 3 | If the candidate list leaks the future, *all* results are fiction |
| 4 | **Risk-based position sizing (size by stop distance to a fixed % equity-at-risk, not notional %)** | 4 | 2 | 2 | Normalizes risk across names; the #1 thing your sizing currently ignores |
| 5 | **Daily/weekly max-loss circuit breaker that halts trading** | 4 | 2 | 1 | Caps tail losses; the control prop firms enforce and you lack |
| 6 | **Replace shell-out with `alpaca-py`; add a risk-veto layer in front of orders** | 4 | 3 | 3 | Speed + reliability + a single chokepoint where every order is risk-checked |
| 7 | **Economic-calendar event gate (flatten/tighten into CPI/NFP/FOMC)** | 3 | 2 | 2 | The real, usable kernel from the video; cheap tail-risk reduction |
| 8 | **Add surprise-index / positioning features (skew, put-call, breadth) to research** | 3 | 4 | 4 | Moves you from "news happened" to "news vs. positioning" — where edge lives |
| 9 | **SQLite as source of truth; markdown as export** | 3 | 3 | 3 | Ends silent data loss and regex-from-prose P&L |
| 10 | **Marketable-limit orders instead of market orders** | 3 | 2 | 2 | Caps slippage on the gappy names you trade |

**Looks useful, probably isn't:** more dashboard widgets before there's a live edge; the motivational quote/Life Hub; adding the video's "reversion" tactic; a faster polling interval while the strategy is still negative; building the sneaker/news-scalp ideas into *this* system. Polishing execution for a negative-expectancy strategy is negative work.

---

## 5. Risk Management

Current controls: 10% trailing stop, −7% hard cut, tighten-on-profit ladder, VIX-bucket sizing, 6-position cap, 5-trades/week cap, sector 2-loss rule. Reasonable for a beginner; incomplete for a real system.

- **Initial-risk logic conflicts.** A −7% hard cut triggers *before* a 10% trailing stop ever binds on the downside, so the 10% trail is decorative until a position is in profit. State your initial risk explicitly as ~7% and let the trail govern only the give-back on winners. Right now the two rules read as if both protect entry; only one does.
- **Notional sizing ≠ risk sizing.** 20% of equity in a 1%-ATR ETF and 20% in a 4%-ATR catalyst stock are wildly different bets. **Size so that (entry − stop) × shares = a fixed % of equity** (e.g. 0.5–1%). This is the single biggest risk upgrade.
- **No portfolio heat / correlation control.** "2 losses in a sector" is weak. Six high-beta tech names is one factor bet wearing six tickers. Add **max correlated/sector exposure and a portfolio-beta cap**.
- **No drawdown circuit breaker.** Add hard daily and weekly loss limits that **stop new entries and optionally flatten**. Non-negotiable for any real deployment.
- **Slippage unprotected live.** Backtest models cost; live uses market orders. Switch to **marketable-limit** with a max-slippage band, especially into the open and around news.
- **Frozen VIX mode ignores realized vol.** Mode set at 9:00 and never revisited means a midday vol spike doesn't de-risk you. At least let the circuit breaker and a realized-vol check override the frozen mode downward (never upward intraday).

---

## 6. Professional-Trader Features (what a real platform has)

- **Risk-as-a-gate service:** every order passes a pre-trade check (size, heat, correlation, event-window, drawdown) that can veto.
- **Order/position reconciliation:** continuously reconcile local state against the broker; alert on any mismatch (a rejected stop, a partial fill).
- **Execution analytics:** slippage vs. arrival price, fill quality, time-to-fill — so you know your *real* costs, not your modeled ones.
- **Performance attribution:** P&L decomposed by setup, sector, regime, day-of-week, time-of-day, and by *signal* vs. *sizing* vs. *timing*. This is how you learn what actually works.
- **Regime dashboard:** VIX term structure, breadth, cross-asset (rates/USD/credit), surprise index — the context every entry is conditioned on.
- **Backtest ↔ live parity monitor:** compare live fills and slippage to backtest assumptions; flag drift early (this is how you'd have caught an over-optimistic cost model).
- **Tamper-evident audit log:** immutable, timestamped record of every decision and order for honest post-mortems.
- **Kill switch + dead-man's switch:** prominent manual flatten *and* an automatic flatten if the engine loses its heartbeat.

---

## 7. Final Report

### 7.1 Top 20 improvements (prioritized)

1. Adopt a hard validation rule: **no live until positive cost-adjusted OOS on the full period** (not a 2-month window).
2. Fix the **Sharpe / metrics bug** (the −81 result).
3. **Audit the backtest universe** for look-ahead and survivorship.
4. Verify **no secrets in git history**; rotate keys if anything leaked.
5. Add a **daily/weekly max-loss circuit breaker** (halts entries).
6. Switch to **risk-based position sizing** (fixed % equity-at-risk by stop distance).
7. Replace **bash shell-out with `alpaca-py`** in the backend.
8. Insert a **pre-trade risk-veto layer** in front of every order.
9. Move state to **SQLite**; generate markdown as an export.
10. Use **marketable-limit orders** with a max-slippage band.
11. Add a **bot health/heartbeat** monitor (last run, last commit, last error) to the dashboard.
12. Add a **live risk/heat panel** (gross/net, top exposures, distance to limits).
13. Add **per-position risk** (stop distance, R-multiple, thesis) to the positions table.
14. Add an **economic-calendar event gate** (tighten/flatten into CPI/NFP/FOMC).
15. Pull **VIX and other facts from real APIs**, not Perplexity.
16. **Separate execution (deterministic) from research (LLM)** into two layers.
17. Add **unit tests** for sizing, stop placement, and the entry gate.
18. Add **execution analytics** (slippage vs. arrival, fill quality).
19. Add **performance attribution** (by setup/sector/regime/time).
20. Add **surprise/positioning features** (skew, put-call, breadth) to research.

### 7.2 Quick wins (this week, low effort, high value)

- Fix the Sharpe bug (#2).
- Adopt the validation rule (#1) — it's a decision, not code.
- Secrets/key audit (#4).
- Relabel/remove the misleading "Day Trades 0/3" widget.
- Add a bot heartbeat indicator (#11) so silent failures surface.

### 7.3 Medium-term (2–6 weeks)

- Risk-based sizing (#6), circuit breaker (#5), risk-veto layer (#8).
- `alpaca-py` migration (#7), SQLite source of truth (#9), marketable-limit orders (#10).
- Risk/heat panel (#12) and per-position risk (#13) on the dashboard.
- Universe audit (#3) and unit tests (#17).

### 7.4 Long-term strategic (2–6 months)

- Split execution vs. research layers (#16) — the architecture change that raises your strategy ceiling.
- Real-time data via Alpaca WebSocket → SSE/WebSocket to the UI.
- Surprise/positioning feature set (#20), execution analytics (#18), performance attribution (#19), backtest↔live parity (#6 platform feature).
- Only after a *real, reproducible, cost-adjusted OOS edge exists*: consider live capital, starting tiny.

### 7.5 Remove / deprioritize

- The video's reversion-scalp tactic (instrument & timeframe mismatch, unproven).
- Motivational quote and Life Hub on the trading view (move to a separate page).
- Faster polling / fancier widgets *before* there's a validated edge.
- Folding the sneaker-bot / news-scalp side projects into this codebase.

### 7.6 Roadmap (order of operations)

```
Phase 0 — Stop the bleeding (days)
  Fix metrics bug → adopt validation rule → secrets audit → heartbeat widget
        │
Phase 1 — Make it safe (weeks 1–3)
  Risk-based sizing → circuit breaker → risk-veto layer → marketable-limit orders
        │
Phase 2 — Make it sound (weeks 3–6)
  alpaca-py migration → SQLite source of truth → unit tests → universe audit
        │
Phase 3 — Make it honest (weeks 4–8, overlaps)
  Risk/heat panel → per-position risk → execution analytics → attribution
        │
Phase 4 — Raise the ceiling (months 2–4)
  Split execution/research → real-time data → surprise/positioning features
        │
Phase 5 — Earn the right to go live (month 4+)
  Reproducible positive cost-adjusted OOS → tiny live size → parity monitoring
```

**The meta-point:** every phase before Phase 5 is about *not losing money on a non-edge and not lying to yourself with bad numbers*. That ordering is deliberate. The most profitable code you can write this month is the code that stops you from deploying the negative-Sharpe strategy you currently have.
