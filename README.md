# Trading Bot

Autonomous Claude-powered trading bot for a ~$100,000 Alpaca paper trading account. Trades stocks and ETFs only. Sends all alerts via Telegram.

## Quick Start

```bash
# 1. Copy and fill in credentials
cp env.template .env
# Edit .env with your Alpaca, Perplexity, and Telegram credentials

# 2. Verify scripts are executable
chmod +x scripts/*.sh

# 3. Run a smoke test (no credentials needed — falls back gracefully)
bash scripts/telegram.sh "Bot online"
bash scripts/alpaca.sh account

# 4. Run your first workflow
# In Claude Code: /pre-market
```

## Daily Workflow

| Time | Command | What happens |
|------|---------|-------------|
| ~9:00 AM ET | `/pre-market` | Research market, set sizing mode, log trade ideas |
| ~9:35 AM ET | `/market-open` | Validate and execute planned trades |
| ~12:30 PM ET | `/midday` | Cut losers, tighten stops on winners |
| ~4:05 PM ET | `/daily-summary` | EOD snapshot + Telegram summary |
| Friday ~4:05 PM ET | `/weekly-review` | Week metrics vs S&P + Telegram review |

Use `/status` at any time to see current account equity, positions, and open orders.
Use `/research <topic>` for an on-demand Perplexity query.

## Project Structure

```
.
├── CLAUDE.md               # Full project instructions for Claude
├── env.template            # Copy to .env and fill in credentials
├── scripts/
│   ├── alpaca.sh           # Alpaca API wrapper
│   ├── perplexity.sh       # Perplexity research wrapper
│   └── telegram.sh         # Telegram notification sender
├── routines/               # Scheduled routine prompts (for cron/remote agents)
├── memory/                 # Persistent state: logs, strategy, context
└── .claude/commands/       # Slash commands for local Claude Code use
```

## Environment Variables

See `env.template` for the full list. Never commit `.env`.
