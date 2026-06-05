# Traadingbot1 — Full Project Guide

> Paper trading account | Alpaca | $100,000 starting capital | Last updated June 5, 2026
> Repo: `https://github.com/codepioneerr/Traadingbot1-bot`

---

## What This Is

An autonomous Claude-powered paper trading bot managing a **$100,000 Alpaca paper account**. It runs a structured daily workflow, notifies via Telegram, backtests strategies before deploying them, and exposes a live web dashboard. No real money — paper only.

---

## Repo Structure

```
Traadingbot1-bot/
├── .claude/commands/        # 8 local slash commands (manual use)
├── backtest/                # ORB backtesting engine (~3,700 lines Python)
│   ├── strategies/orb.py    # Opening Range Breakout strategy
│   ├── engine.py            # Event-driven backtest loop
│   ├── evaluate.py          # IS/OOS walk-forward evaluator
│   ├── run_overnight.py     # nohup-safe long runner
│   └── results/             # JSON result files
├── dashboard/
│   ├── backend/main.py      # FastAPI — 18 endpoints
│   └── frontend/src/        # React + Tailwind dashboard
├── memory/                  # All persistent bot state (markdown + JSON)
├── routines/                # Scheduled remote agent prompts
├── scripts/                 # Shell wrappers: alpaca.sh, telegram.sh, perplexity.sh
├── railway.toml             # Railway deployment config (repo root)
├── CLAUDE.md                # Claude agent instructions
└── .env                     # Credentials (gitignored)
```

---

## Account

| Field | Value |
|-------|-------|
| Platform | Alpaca Paper Trading |
| Account # | PA32I4MEXBHZ |
| Starting Capital | $100,000.00 |
| Instruments | Stocks + ETFs only — **no options ever** |
| Broker endpoint | `https://paper-api.alpaca.markets` |
| Data endpoint | `https://data.alpaca.markets` |
| PDT status | Not subject — equity above $25k threshold |
| Max positions | 6 (4 in DEFENSIVE mode) |
| Max new trades/week | 5 |

---

## Trading Strategy

Full rules in `memory/TRADING-STRATEGY.md`. Summary below.

### Position Sizing (VIX-based)

| VIX | Mode | Max per position | Capital deployed |
|-----|------|-----------------|-----------------|
| < 15 | AGGRESSIVE | 25% | 85–90% |
| 15–25 | MODERATE | 20% | 75–85% |
| > 25 | DEFENSIVE | 15% | 60–75% (4 max positions) |

Sizing mode is set at pre-market and never changed mid-day.

### Core Rules

- 10% trailing stop placed **immediately** after every fill (GTC order)
- Hard cut at **-7%** — no exceptions, no averaging down
- Tighten trail: **7%** at +15%, **5%** at +20% — never move a stop down
- PDT cap of 3 day-trades/rolling-5-days only applies if equity drops below $25k
- 2 consecutive failed trades in a sector → exit entire sector
- Patience > activity — zero trades can be the right answer

### Entry Checklist (all must pass)

- Catalyst documented in today's RESEARCH-LOG
- Sector in momentum
- Stop level defined (7–10% below entry)
- Minimum 2:1 R:R target
- Total positions after fill ≤ 6 (4 in DEFENSIVE)
- Trades this week ≤ 5
- Position size ≤ sizing mode % of equity
- Instrument is a stock or ETF (not an option)

---

## Daily Workflow

Five scheduled routines run as **Claude Code remote agents** (cron). Each routine: verifies env vars → reads memory → acts → writes memory → git commit + push.

### Schedule (EDT — Summer)

| Time (EDT) | Routine ID | File | What it does |
|-----------|-----------|------|--------------|
| 9:00 AM | `trig_011SvShqB3ehs4He2753Ko1D` | `routines/pre-market.md` | Perplexity research, VIX, sizing mode, trade ideas → RESEARCH-LOG + Telegram |
| 9:35 AM | `trig_01GEMBKtpH13eD1YBBKBqsfk` | `routines/market-open.md` | Validate ideas, execute trades, place trailing stops → TRADE-LOG + Telegram |
| 12:30 PM | `trig_01J92CubBoHzKJADDfi192sJ` | `routines/midday.md` | Cut losers at -7%, tighten stops, thesis check |
| 4:05 PM | `trig_019Mj499gRvAscnHdZMWAUjU` | `routines/daily-summary.md` | EOD P&L snapshot → TRADE-LOG + Telegram |
| 4:05 PM Fri | `trig_013ZvKZEr1sM9vUqy7z5LsRR` | `routines/weekly-review.md` | Week metrics vs S&P, lessons → Telegram |
| Nov 2 2026 | `trig_01LAWThx7wK4KdggHzhj9mw5` | — | One-time DST reminder with updated EST cron strings |

> **DST note:** Crons are set to EDT (UTC-4). They shift 1 hour in November. The one-time reminder fires Nov 2, 2026 with updated strings to paste in.

The same routines are also available as **local slash commands** in `.claude/commands/` for manual use — these read `.env` automatically and skip the git push step.

### How a Morning Run Works

```
9:00 AM — Remote agent spins up, clones repo
    │
    ├── Phase 1: Pre-Market Research
    │   ├── Read TRADING-STRATEGY.md, TRADE-LOG, RESEARCH-LOG
    │   ├── Pull Alpaca account state
    │   ├── Run Perplexity queries (VIX, futures, sectors, catalysts, earnings)
    │   ├── Determine sizing mode from VIX
    │   ├── Write dated entry to RESEARCH-LOG.md
    │   ├── Telegram: sector watchlist + sizing mode
    │   └── git commit + push
    │
    └── Phase 2: Market-Open Execution (9:35 AM)
        ├── Re-check live quotes + spreads
        ├── Run 7 hard-check rules per trade idea
        ├── Place market orders for approved trades
        ├── Immediately place 10% trailing stops
        ├── Append to TRADE-LOG.md
        ├── Telegram per trade (or "no trades" message)
        └── git commit + push
```

---

## Backtest Engine

### Purpose

Validate the **ORB (Opening Range Breakout)** strategy before going live. The strategy is **not live yet** — it deploys only after the out-of-sample realistic pass shows a clear PASS.

### Architecture (`backtest/` — ~3,700 lines)

| File | Role |
|------|------|
| `strategies/orb.py` | ORB signal logic — OR window, VWAP filter, ATR stops, EOD flat |
| `engine.py` | Event-driven bar-by-bar backtest loop |
| `evaluate.py` | Walk-forward IS/OOS evaluator, grid-searches params, runs 3 passes |
| `features.py` | VWAP, relative volume, ATR, regime indicators |
| `regime.py` | VIX-based market regime detection (rolling percentile) |
| `costs.py` | Realistic friction model (spread, commission, slippage) |
| `metrics.py` | Sharpe, CAGR, max drawdown, win rate, profit factor |
| `monte_carlo.py` | Monte Carlo confidence intervals on OOS results |
| `walk_forward.py` | Expanding-window walk-forward validation |
| `analysis.py` | Post-run analysis and reporting |
| `diagnose.py` | Diagnostic tools for debugging strategy behavior |
| `sensitivity.py` | Param sensitivity / robustness analysis |
| `run_overnight.py` | nohup-safe long runner for multi-day backtests |
| `data.py` | Alpaca historical data fetcher with local caching |

### Three Evaluation Passes

Every `evaluate.py` run produces a result JSON with three OOS passes:

1. **Frictionless** — no costs (upper bound)
2. **Realistic 5bps** — spread + 5bps commission
3. **Realistic 10bps** — spread + 10bps commission

### Current Results (6 runs in `backtest/results/`)

| File | Period | Key result |
|------|--------|------------|
| `orb_analysis_20260604_*` (×2) | Jan–Feb 2024 | OOS frictionless only |
| `orb_analysis_20260604_221447` | Jan–Feb 2024 | Expanded analysis |
| `orb_20260605_010607` | **2021–2026 full** | ❌ OOS negative across all passes (Sharpe -1.6 → -1.0) |
| `orb_20260605_012702` | Jan–Feb 2024 (short) | Abnormal Sharpe (-78) — likely data/lookback issue |
| `orb_20260605_012941` | Jan–Feb 2024 | ✅ realistic_5bps: Sharpe **2.82**, 57.8% win rate — most promising |

**Status:** The short-window result shows real edge at realistic costs. The full 5-year run is negative, suggesting degradation — likely a universe selection and parameter stability issue. Needs more investigation before going live.

---

## Dashboard

### Stack

- **Backend:** FastAPI (Python) → Railway  
- **Frontend:** React 18 + Vite + Tailwind CSS → Vercel  
- **Auth:** Single password via `X-Password` header, stored in `localStorage`  
- **Refresh:** Every 30 seconds automatically

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ TOP BAR: Nick's Trading Hub | Market Status | Clock | Date  │
├───────────┬──────────────┬──────────────┬───────────────────┤
│  Equity   │  Day P&L     │  Positions   │  Day Trades Used  │
├───────────────────────────┬─────────────────────────────────┤
│ Positions Table           │ Bot Status Panel                 │
│ + Equity Curve Chart      │ Routine statuses + Backtest bar  │
├─────────────┬─────────────┬─────────────────────────────────┤
│ Monthly     │ Recent      │ Quick Controls                   │
│ Calendar    │ Alerts Feed │ + Daily Quote                    │
│ (P&L color) │ (10 entries)│                                  │
├─────────────────────────────────────────────────────────────┤
│ LIFE HUB (collapsible)                                       │
│ Goals Tracker | Daily Notes | Upcoming (placeholder)        │
└─────────────────────────────────────────────────────────────┘
```

### Backend API (18 endpoints)

| Method | Endpoint | Source |
|--------|----------|--------|
| GET | `/health` | Static |
| GET | `/api/ping` | Auth check |
| GET | `/api/account` | `scripts/alpaca.sh account` |
| GET | `/api/positions` | `scripts/alpaca.sh positions` |
| GET | `/api/orders` | `scripts/alpaca.sh orders open` |
| GET | `/api/equity-history` | Alpaca portfolio history API (5-min bars) |
| GET | `/api/status` | Reads `memory/` + `backtest/results/` |
| GET | `/api/backtest` | Latest JSON in `backtest/results/` |
| GET | `/api/alerts` | `memory/TELEGRAM-LOG.md` (last 10) |
| GET | `/api/calendar` | Parses `memory/TRADE-LOG.md` |
| GET | `/api/quote` | 50-quote list, rotates by day-of-year |
| POST | `/api/pause` | Writes `memory/PAUSE-FLAG.txt` |
| POST | `/api/resume` | Deletes `memory/PAUSE-FLAG.txt` |
| POST | `/api/close-all` | Alpaca `DELETE /v2/positions` |
| GET/POST | `/api/goals` | Reads/writes `memory/GOALS.json` |
| GET/POST | `/api/notes` | Reads/writes `memory/DAILY-NOTES.md` |

### Frontend Components

| Component | What it shows |
|-----------|--------------|
| `TopBar` | Title, live clock, market status dot (pre/open/after/closed), date |
| `StatCard` | Reusable metric tile |
| `PositionsPanel` | Positions table (symbol, qty, cost, current, day%, unreal P&L) + equity curve |
| `BotStatusPanel` | Running/Paused badge, 4 routine status rows, backtest count progress bar |
| `CalendarPanel` | Monthly grid — green/red by P&L, purple dot on trade days, today highlighted |
| `AlertsFeed` | Last 10 Telegram log entries, color-coded by type (buy/sell/profit/loss/warning) |
| `QuickControls` | Refresh, Pause/Resume, View Backtest, Close All (confirm modal), daily quote |
| `LifeHub` | Collapsible: 3 editable goal bars, daily notes textarea, upcoming placeholder |

---

## Memory System

All persistent state in `memory/` — committed to GitHub after every routine run so each subsequent agent picks up the latest state.

| File | Contents | Status |
|------|----------|--------|
| `TRADING-STRATEGY.md` | Master rules — sizing table, entry/exit checklist, ORB spec | Current |
| `TRADE-LOG.md` | Every trade + daily EOD snapshots | Day 0 baseline only (no live trades yet) |
| `RESEARCH-LOG.md` | Pre-market research + sizing mode + trade ideas | No entries yet |
| `WEEKLY-REVIEW.md` | Friday reviews — performance vs S&P, lessons, grade | No entries yet |
| `PROJECT-CONTEXT.md` | Account details, phase, constraints | Current |
| `GOALS.json` | 3 personal goals with progress (auto-created by dashboard) | Created |
| `DAILY-NOTES.md` | Daily freeform notes via dashboard | Created on first save |
| `PAUSE-FLAG.txt` | Presence = bot paused (gitignored) | Not present = running |
| `TELEGRAM-LOG.md` | Raw Telegram notification log (feeds dashboard alerts) | Not yet — populates once bot runs |

> **Critical:** If a remote agent run fails before committing, that day's data is lost. The EOD commit is especially important — it provides the equity baseline for the next day's P&L calculation.

---

## Scripts

All in `scripts/`, all `chmod +x`, all read `.env` automatically on local runs.

| Script | Key commands |
|--------|-------------|
| `alpaca.sh` | `account`, `positions`, `quote <sym>`, `orders [open\|closed\|all]`, `buy <sym> <notional>`, `trailing-stop <sym> <qty> <pct>`, `stop <sym> <qty> <price>`, `close <sym>`, `cancel <order_id>` |
| `telegram.sh` | Sends a message to your Telegram chat; falls back to `DAILY-SUMMARY.md` if credentials are missing |
| `perplexity.sh` | Accepts a query string, returns Perplexity research text |

---

## Telegram Notifications

| Event | Trigger |
|-------|---------|
| 📊 Pre-market sector watch | Every morning — sectors, VIX, sizing mode |
| 🟢 Trade executed | Real-time on every buy, with stop/target/thesis |
| 🔴 Position closed | Immediate on -7% stop or thesis break |
| ⚡ Stop tightened | When trailing stop is tightened on a winner |
| 📈 EOD summary | Every market close — P&L, positions, week count |
| 📊 Weekly review | Fridays — week vs S&P, grade, next week sectors |

Bot token: in `.env` locally / exported as env var in remote routines  
Chat ID: `5567513606`

---

## Credentials

Stored in `.env` locally (gitignored). Exported as env vars in each remote routine prompt (remote agents have no `.env` access).

| Variable | Purpose |
|----------|---------|
| `ALPACA_API_KEY` | Paper trading auth |
| `ALPACA_SECRET_KEY` | Paper trading auth |
| `ALPACA_ENDPOINT` | `https://paper-api.alpaca.markets` |
| `ALPACA_DATA_ENDPOINT` | `https://data.alpaca.markets` |
| `PERPLEXITY_API_KEY` | Market research queries |
| `PERPLEXITY_MODEL` | `sonar` |
| `TELEGRAM_BOT_TOKEN` | Notification bot |
| `TELEGRAM_CHAT_ID` | `5567513606` |
| `DASHBOARD_PASSWORD` | Dashboard login (Railway env var) |
| `FRONTEND_URL` | Vercel URL for CORS (Railway env var) |
| `REPO_ROOT` | `/app` (Railway env var) |

---

## Deployment

### Backend → Railway

Service root: `dashboard/backend/`  
Start command (from `railway.toml`): `uvicorn main:app --host 0.0.0.0 --port $PORT`  
Health check: `/health`

### Frontend → Vercel

Build: `npm run build` → output: `dist/`  
Framework: Vite (auto-detected)  
Root directory: `dashboard/frontend/`  
Required env var: `VITE_API_URL=<Railway URL>`

---

## Manual Slash Commands (Local Use)

Run in Claude Code for one-off actions. Read `.env` automatically, skip the git push.

| Command | When to use |
|---------|------------|
| `/pre-market` | Manually trigger morning research |
| `/market-open` | Manually execute planned trades |
| `/midday` | Manual midday check |
| `/daily-summary` | Force EOD snapshot |
| `/weekly-review` | Manual weekly review |
| `/status` | Quick account snapshot (equity, positions, orders, sizing mode) |
| `/research <query>` | Ad-hoc Perplexity research |
| `/backtest` | Run a full backtest evaluation |

---

## Current Status

| Layer | Status |
|-------|--------|
| Alpaca paper account | ✅ Active — $100,000, no open positions |
| Trading routines | ⏸ Not yet scheduled — bot hasn't run its first live day |
| Backtest engine | 🔬 Active — 6 runs completed, short-window shows Sharpe 2.82 at 5bps but full 5-year run is negative |
| ORB live deployment | ❌ Not yet — pending backtest PASS validation |
| Dashboard backend | ✅ All 18 endpoints tested and working |
| Dashboard frontend | ✅ Built and committed — pending Vercel deploy |
| Railway deployment | 🔧 In progress — `railway.toml` fix pushed, awaiting successful deploy |

---

## What's Next

1. **Finish Railway deploy** — redeploy with the fixed `railway.toml`
2. **Deploy frontend to Vercel** — set `VITE_API_URL` env var, trigger build
3. **Schedule routines** — use `/schedule` to register `routines/*.md` as cron agents with required env vars
4. **Create `memory/TELEGRAM-LOG.md`** — the dashboard alerts feed populates once the bot starts logging there
5. **Investigate ORB on longer window** — test different universe filters and parameter ranges to understand the 5-year degradation before going live

---

## Monitoring & Intervention

| Action | How |
|--------|-----|
| Check account status | Run `/status` in Claude Code |
| Override a trade | Go to `app.alpaca.markets`, cancel/close manually |
| Pause the bot | Dashboard → Pause Bot, or disable routines at `claude.ai/code/routines` |
| Update trading rules | Edit `memory/TRADING-STRATEGY.md` and commit — next routine picks it up |
| If a routine fails silently | Check `memory/RESEARCH-LOG.md` for today's entry; check `DAILY-SUMMARY.md` for Telegram fallback errors |
| Rotate a credential | Update `.env` locally + update all 3 active routine env vars at `claude.ai/code/routines` |

---

## Known Issues & Limitations

- **DST:** Crons are set to EDT (UTC-4). They shift 1 hour in November. Reminder fires Nov 2, 2026 with EST cron strings.
- **PDT Rule:** Bot won't day-trade if `daytrade_count >= 3`. On those days it will skip new positions that require same-day exit.
- **Market holidays:** Routines fire on schedule regardless. On non-trading days Alpaca returns no data and the bot exits cleanly.
- **Remote agent context limit:** Heavy research days (many positions + many Perplexity calls) can approach session token limits. Symptom: no commit for that day.
- **No `.env` in remote runs:** Credentials are embedded in routine prompts. Rotating a key requires updating all active routines manually.
