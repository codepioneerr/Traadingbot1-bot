# Trading Bot — Full Overview

> Paper trading account | Alpaca | ~$100,000 starting capital | As of June 2026

---

## What This Bot Does

Fully autonomous trading bot that researches the market each morning, executes trades at open, monitors positions at midday, and sends you an EOD summary to Telegram — every weekday, no manual intervention needed.

It uses Claude Code scheduled remote agents (cloud-hosted, fresh repo clone each run) to execute the full daily workflow. All state is persisted to GitHub via git commits so each run picks up where the last left off.

---

## Account

| Field | Value |
|-------|-------|
| Platform | Alpaca Paper Trading |
| Account # | PA32I4MEXBHZ |
| Starting Capital | $100,000.00 |
| Instruments | Stocks + ETFs only (options strictly prohibited) |
| Broker endpoint | `https://paper-api.alpaca.markets` |
| Data endpoint | `https://data.alpaca.markets` |

---

## Trading Strategy

Full rules live in `memory/TRADING-STRATEGY.md`. Summary:

### Position Limits
- Max **6 open positions** at once
- Max **5 new trades per week**
- Max **3 day trades per rolling 5 days** (PDT rule — account < $25k)

### Entry Rules
- Must have a documented catalyst in today's RESEARCH-LOG
- Position size determined by VIX-based sizing mode (see below)
- Bid/ask spread must be < 0.5% of price (liquidity check)
- Must clear all 7 hard checks before any order is placed

### Sizing Modes (VIX-Driven)
| VIX | Mode | Max per position | Target deployment |
|-----|------|-----------------|-------------------|
| < 15 | AGGRESSIVE | 25% | 85–90% |
| 15–25 | MODERATE | 20% | 75–85% |
| > 25 | DEFENSIVE | 15% | 60–75% (max 4 positions) |

### Stop Loss & Exits
- **10% trailing stop** placed immediately after every fill (GTC)
- **Hard cut at -7%** — no exceptions, no hope-holding
- **Tighten trailing stop** when winners run:
  - ≥ +15% gain → tighten trail to 7%
  - ≥ +20% gain → tighten trail to 5%
- Never move a stop lower — only tighten or hold
- Cut on thesis break even if not at -7% yet

### Order Types
- Entries: market orders, day TIF
- Stops: trailing stop GTC (fallback to fixed stop if PDT-blocked)

---

## Daily Schedule (EDT — Summer)

| Time (EDT) | Routine | What Happens |
|-----------|---------|--------------|
| 9:00 AM | **Morning** | Pre-market research + wait for open + execute trades |
| 12:30 PM | **Midday** | Cut losers, tighten stops, thesis check, opportunity scan |
| 4:05 PM | **EOD** | Daily P&L snapshot + Telegram summary (+ weekly review on Fridays) |

> ⚠️ **DST Note:** These run on EDT (UTC-4) times. When clocks fall back in November, a scheduled reminder (`trig_01LAWThx7wK4KdggHzhj9mw5`) will fire on Nov 2, 2026 and send you the updated cron strings to paste in.

---

## Scheduled Routines (claude.ai/code/routines)

| Routine ID | Name | Cron (UTC) | Status |
|-----------|------|------------|--------|
| `trig_011SvShqB3ehs4He2753Ko1D` | Morning (Research + Execute) | `0 13 * * 1-5` | ✅ Active |
| `trig_01J92CubBoHzKJADDfi192sJ` | Midday | `30 16 * * 1-5` | ✅ Active |
| `trig_019Mj499gRvAscnHdZMWAUjU` | EOD (Summary + Friday Review) | `5 20 * * 1-5` | ✅ Active |
| `trig_01GEMBKtpH13eD1YBBKBqsfk` | Market Open | `35 13 * * 1-5` | 🚫 Disabled (merged into Morning) |
| `trig_013ZvKZEr1sM9vUqy7z5LsRR` | Weekly Review | `5 20 * * 5` | 🚫 Disabled (merged into EOD) |
| `trig_01LAWThx7wK4KdggHzhj9mw5` | DST Reminder | Nov 2 2026 9AM EST | ⏰ One-time |

---

## How the Morning Routine Works

```
9:00 AM EDT — Remote agent spins up, clones repo
    │
    ├── Phase 1: Pre-Market Research (~25 min)
    │   ├── Read TRADING-STRATEGY.md, TRADE-LOG, RESEARCH-LOG
    │   ├── Pull Alpaca account state
    │   ├── Run 8 Perplexity queries (oil, futures, VIX, catalysts, earnings, econ calendar, sectors)
    │   ├── Determine sizing mode from VIX
    │   ├── Write dated entry to RESEARCH-LOG.md
    │   ├── Send Telegram: sector watch + sizing mode
    │   └── git commit + push RESEARCH-LOG.md
    │
    ├── Phase 2: Wait for Market Open
    │   └── Sleep loop until 9:30 AM ET
    │
    └── Phase 3: Market-Open Execution
        ├── Re-check live quotes + spreads
        ├── Run 7 hard-check rules per trade idea
        ├── Place market orders for approved trades
        ├── Immediately place 10% trailing stops
        ├── Append to TRADE-LOG.md
        ├── Send Telegram per trade (or silence if no trades)
        └── git commit + push TRADE-LOG.md (if trades)
```

---

## How the Midday Routine Works

```
12:30 PM EDT — Remote agent spins up
    ├── Read TRADING-STRATEGY.md, TRADE-LOG, RESEARCH-LOG
    ├── Pull positions + orders from Alpaca
    ├── Cut any position at ≤ -7% unrealized → Telegram alert
    ├── Tighten trailing stops on winners ≥ +15% or ≥ +20%
    ├── Thesis check on each position (Perplexity if sharp move)
    ├── Opportunity scan if capacity exists (flag for tomorrow, no trades)
    ├── Telegram only if action taken (silent otherwise)
    └── git commit + push if any memory files changed
```

---

## How the EOD Routine Works

```
4:05 PM EDT — Remote agent spins up
    ├── PART 1: Daily Summary (every weekday)
    │   ├── Read TRADE-LOG for yesterday's equity baseline
    │   ├── Pull final account state from Alpaca
    │   ├── Compute Day P&L and Phase P&L
    │   ├── Append EOD snapshot to TRADE-LOG.md
    │   ├── Send Telegram EOD summary (always, even on no-trade days)
    │   └── git commit + push TRADE-LOG.md (mandatory)
    │
    └── PART 2: Weekly Review (Fridays only, DOW=5)
        ├── Read full week from TRADE-LOG + RESEARCH-LOG
        ├── Run 4 Perplexity queries (S&P return, sectors, next week outlook)
        ├── Compute win rate, profit factor, bot vs S&P
        ├── Append full review to WEEKLY-REVIEW.md
        ├── Update TRADING-STRATEGY.md if rules need changing
        ├── Send Telegram weekly review summary
        └── git commit + push
```

---

## Memory System

All persistent state is in `memory/` — committed to GitHub after every run so the next agent picks it up.

| File | Purpose |
|------|---------|
| `memory/TRADING-STRATEGY.md` | Master rules — position limits, sizing table, entry/exit checklist |
| `memory/TRADE-LOG.md` | Every trade + daily EOD snapshots. Used for P&L tracking |
| `memory/RESEARCH-LOG.md` | Pre-market research entries. Market context + sizing mode + trade ideas |
| `memory/WEEKLY-REVIEW.md` | Friday weekly reviews — performance vs S&P, lessons, grade |
| `memory/PROJECT-CONTEXT.md` | Setup notes, account details, phase info |

> **Critical:** If a remote agent run fails before committing, that day's data is lost. The EOD commit is especially important — it provides the equity baseline for the next day's P&L calculation.

---

## Scripts

| Script | Usage | Notes |
|--------|-------|-------|
| `scripts/alpaca.sh` | `bash scripts/alpaca.sh account` | REST wrapper for Alpaca API |
| | `bash scripts/alpaca.sh positions` | |
| | `bash scripts/alpaca.sh orders` | |
| | `bash scripts/alpaca.sh quote AAPL` | |
| | `bash scripts/alpaca.sh order '{...json...}'` | Place order |
| | `bash scripts/alpaca.sh close AAPL` | Close position |
| | `bash scripts/alpaca.sh cancel ORDER_ID` | Cancel open order |
| `scripts/perplexity.sh` | `bash scripts/perplexity.sh "query"` | Returns text response |
| `scripts/telegram.sh` | `bash scripts/telegram.sh "message"` | Sends to your chat; falls back to DAILY-SUMMARY.md if creds missing |

---

## Telegram Notifications

You receive alerts for:

| Event | When |
|-------|------|
| 📊 Pre-market sector watch | Every morning — sectors, VIX, sizing mode |
| 🚨 Urgent alert | Only if position -7% pre-market or thesis broke overnight |
| 🟢 Trade executed | Real-time on every buy, with stop/target/thesis |
| 🔴 Position closed | Immediate on -7% stop or thesis break |
| ⚡ Stop tightened | When trailing stop is tightened on a winner |
| 📈 EOD Summary | Every market close — P&L, positions, week count |
| 📊 Weekly Review | Fridays — week vs S&P, grade, next week sectors |

Bot token: in `.env` (local) / exported as env var in remote routines.
Chat ID: `5567513606`

---

## Credentials

Stored in `.env` locally (gitignored). Embedded as `export` statements in each remote routine prompt since remote agents don't have access to `.env`.

| Variable | Purpose |
|----------|---------|
| `ALPACA_API_KEY` | Paper trading auth |
| `ALPACA_SECRET_KEY` | Paper trading auth |
| `ALPACA_ENDPOINT` | `https://paper-api.alpaca.markets` |
| `ALPACA_DATA_ENDPOINT` | `https://data.alpaca.markets` |
| `PERPLEXITY_API_KEY` | Market research queries |
| `PERPLEXITY_MODEL` | `sonar` |
| `TELEGRAM_BOT_TOKEN` | Notification bot |
| `TELEGRAM_CHAT_ID` | Your chat ID |

---

## Repo

`https://github.com/codepioneerr/Traadingbot1-bot`

- `scripts/` — API wrappers
- `routines/` — Full routine prompts (used by scheduled agents)
- `.claude/commands/` — Slash commands for manual local runs (read `.env` automatically, skip git push)
- `memory/` — All persistent state

---

## Manual Commands (Local Use)

Run these in Claude Code for one-off actions. They use `.env` automatically and skip the git push step.

| Command | When to use |
|---------|------------|
| `/pre-market` | Manually trigger morning research |
| `/market-open` | Manually execute planned trades |
| `/midday` | Manual midday check |
| `/daily-summary` | Force EOD snapshot |
| `/weekly-review` | Manual weekly review |
| `/status` | Quick account snapshot |
| `/research <query>` | Ad-hoc Perplexity research |

---

## Monitoring & Intervention

**To check status anytime:** Run `/status` in Claude Code — pulls live Alpaca data + reads memory files.

**To override a trade:** Go to `app.alpaca.markets` and cancel/close manually. The next routine run will read the updated positions.

**To pause the bot:** Disable routines at `https://claude.ai/code/routines`.

**If a routine fails silently:** Check `memory/RESEARCH-LOG.md` — if no entry was written for today, the run didn't complete. Also check `DAILY-SUMMARY.md` (Telegram fallback) for any error messages.

**To update trading rules:** Edit `memory/TRADING-STRATEGY.md` directly and commit. The next routine run will read the updated rules.

---

## Known Issues & Limitations

- **DST:** Crons are set to EDT (UTC-4). They shift 1 hour in winter. A reminder fires Nov 2, 2026 with the EST cron strings.
- **PDT Rule:** Bot won't day-trade if `daytrade_count >= 3`. On those days it won't enter new positions that would require same-day exit.
- **Market holidays:** Routines fire on schedule regardless of market holidays. On non-trading days, Alpaca will return no data and the bot will exit cleanly (no orders placed).
- **Remote agent context limit:** If a run gets too long (many positions + heavy Perplexity research), it may hit the session token limit. Symptom: no commit for that day.
- **No `.env` in remote runs:** Credentials are embedded in the routine prompts directly. Rotating a key requires updating all 3 active routines at `https://claude.ai/code/routines`.
