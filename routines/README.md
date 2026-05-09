# Routines

These are the **scheduled routine prompts** — the versions run by Claude Code remote agents (cron). They differ from the `.claude/commands/` slash commands in two ways:

1. **Env-var verification block** — they check that all required credentials are exported as process env vars (since there's no `.env` file in a fresh remote clone).
2. **Mandatory git commit/push** — they persist memory changes back to the repo so the next routine sees up-to-date state.

## Recommended Schedule (ET)

| Routine | File | When to run |
|---------|------|-------------|
| Pre-market research | `pre-market.md` | Mon–Fri 9:00 AM |
| Market-open execution | `market-open.md` | Mon–Fri 9:35 AM |
| Midday scan | `midday.md` | Mon–Fri 12:30 PM |
| Daily summary | `daily-summary.md` | Mon–Fri 4:05 PM |
| Weekly review | `weekly-review.md` | Friday 4:05 PM |

## Setting Up as Scheduled Routines

Use `/schedule` in Claude Code to register each routine file as a recurring remote agent. Pass the required env vars (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, etc.) as secrets in the routine configuration.

## Local Use

For manual local runs, use the slash commands in `.claude/commands/` instead — they read `.env` automatically and skip the git push step.
