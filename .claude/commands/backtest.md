Run a full §2 backtest evaluation for a strategy over a date range.

Usage: /backtest orb 2021-01-01 2026-01-01

NOTE — LOCAL MODE: Credentials are loaded from .env automatically by each script. If a
wrapper prints "not set in environment", stop and report which variable is missing.

You are running the backtest evaluation workflow.

STEP 1 — Parse arguments.
The slash command arguments are the three tokens after "/backtest": strategy, start, end.
If any are missing, print:
  Usage: /backtest <strategy> <start> <end>
  Example: /backtest orb 2021-01-01 2026-01-01
and stop.

STEP 2 — Set up the environment.
Run: cd "$(git rev-parse --show-toplevel)" && source .env

STEP 3 — Run the backtest.
Execute:
  python -m backtest.evaluate <strategy> <start> <end>

This will:
- Detect the Alpaca data feed (SIP vs IEX) — IEX results are INDICATIVE ONLY
- Load minute bars for the default universe (AAPL, NVDA, MSFT, TSLA, META, AMZN, GOOGL, AMD, NFLX, SPY)
- Split into 65% in-sample / 35% out-of-sample
- Sweep params on IS, pick best
- Run frictionless + realistic (5bps + 10bps) passes on OOS
- Print the full scorecard and PASS/FAIL verdict
- Save a JSON result to backtest/results/

STEP 4 — Interpret the verdict.
After the script completes, read and summarize the result:
- PASS: strategy beat SPY on return, Sharpe, and drawdown (≤1.5×), with profit_factor > 1.3 and ≥100 trades
- FAIL: list each criterion that failed

STEP 5 — Update memory.
Append a brief entry to memory/RESEARCH-LOG.md:

## Backtest — <strategy> <start>→<end> — <DATE>
- Verdict: PASS / FAIL
- OOS return: X%  |  SPY: X%
- OOS Sharpe: X.XX  |  SPY: X.XX
- OOS MaxDD: X%  |  SPY limit: X%
- Profit factor: X.XX  |  Trade count: N
- Best params: {params}
- Failures (if any): ...
- Result file: backtest/results/<file>.json

IMPORTANT CONSTRAINTS:
- Do NOT commit or push anything — this is a local manual command
- Do NOT start live trading based on a single backtest run; always validate and review first
- If the feed is IEX, results are INDICATIVE ONLY — re-run with SIP feed before making trading decisions
- Options are strictly prohibited — this backtest framework only handles stocks/ETFs
