# Trading Bot — CLAUDE.md

## Project Overview

Autonomous trading bot managing a ~$10,000 Alpaca **paper trading** account. The bot researches, executes, monitors, and summarizes trades across a scheduled daily workflow. All state is persisted in `memory/`. All notifications go to Telegram.

## Instruments

**Allowed: Stocks and ETFs only.**
Options are strictly prohibited — never place, suggest, or reference an options order.

## Environment

Copy `env.template` to `.env` and fill in your credentials. The `.env` file is gitignored and never committed.

Required variables:
| Variable | Purpose |
|----------|---------|
| `ALPACA_API_KEY` | Alpaca paper trading key |
| `ALPACA_SECRET_KEY` | Alpaca paper trading secret |
| `ALPACA_ENDPOINT` | Alpaca REST base URL (paper) |
| `ALPACA_DATA_ENDPOINT` | Alpaca market data URL |
| `PERPLEXITY_API_KEY` | Perplexity API key |
| `PERPLEXITY_MODEL` | Perplexity model name |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat/channel ID |

All scripts read `.env` automatically when run locally. When run as a remote routine (scheduled agent), credentials must be exported as process environment variables instead — `.env` will not be present in that context.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/alpaca.sh` | Alpaca REST API wrapper — account, positions, orders, buy, trailing-stop, close, cancel |
| `scripts/perplexity.sh` | Perplexity research query wrapper — accepts a query string, returns text |
| `scripts/telegram.sh` | Sends a Telegram message; falls back to writing `DAILY-SUMMARY.md` if credentials are absent |

All scripts are `chmod +x`. Run them directly: `bash scripts/alpaca.sh account`.

## Slash Commands (Local)

Seven Claude slash commands in `.claude/commands/` for manual local invocation:

| Command | What it does |
|---------|-------------|
| `/pre-market` | Morning research — VIX, S&P futures, sizing mode, trade ideas → RESEARCH-LOG |
| `/market-open` | Validate and execute planned trades → TRADE-LOG, Telegram |
| `/midday` | Cut losers, tighten stops, thesis check, opportunity scan |
| `/daily-summary` | EOD P&L snapshot → TRADE-LOG, Telegram |
| `/weekly-review` | Week metrics, vs S&P, lessons → WEEKLY-REVIEW, Telegram |
| `/research` | Ad-hoc Perplexity query on any topic |
| `/status` | Quick account snapshot: equity, positions, open orders, sizing mode |

## Routines (Scheduled / Remote)

Full workflow prompts in `routines/` — these are the versions run by Claude Code scheduled routines (cron). They include env-var verification and mandatory git commit/push steps to persist state across fresh clones.

See `routines/README.md` for the recommended schedule.

## Memory System

All persistent state lives in `memory/`:

| File | Contents |
|------|---------|
| `memory/TRADING-STRATEGY.md` | Core strategy, rules, position sizing table, entry/exit checklist |
| `memory/TRADE-LOG.md` | Chronological log of every trade and EOD snapshot |
| `memory/RESEARCH-LOG.md` | Daily pre-market research entries with sizing mode and trade ideas |
| `memory/WEEKLY-REVIEW.md` | Friday weekly review entries with performance vs S&P |
| `memory/PROJECT-CONTEXT.md` | Project setup, account details, current phase |

Always read the relevant memory files before taking any action. Always write back to memory after any trade or workflow step.

## Trading Rules (summary — full detail in memory/TRADING-STRATEGY.md)

- Max 6 open positions at once
- Max 5 new trades per week
- 10% trailing stop on every new position (placed immediately after fill)
- Cut losers at -7% (no exceptions)
- Tighten trailing stop: ≥+15% → 7%, ≥+20% → 5%
- Never move a stop lower
- PDT rule: max 3 day trades per rolling 5 days (account < $25k)
- Dynamic position sizing based on VIX (see TRADING-STRATEGY.md)
- Notify via Telegram for: every trade, every stop change, every position closed, EOD summary, weekly review

## Notifications

All Telegram alerts use `scripts/telegram.sh`. The script reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from the environment. If credentials are missing, it falls back to appending messages to `DAILY-SUMMARY.md` locally.
