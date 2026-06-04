#!/usr/bin/env python3
"""
TradingBot-Live session runner.
Usage: python run_trading_session.py --workflow pre-market
"""

import anthropic
import argparse
import os
import sys

BASE = "/workspace/Traadingbot1-bot"
SCRIPTS = f"{BASE}/scripts"
MEMORY = f"{BASE}/memory"

WORKFLOWS = {
    "pre-market": (
        f"Run the pre-market workflow: check VIX and S&P futures via {SCRIPTS}/perplexity.sh, "
        f"determine today's sizing mode per {MEMORY}/TRADING-STRATEGY.md, identify 3-5 trade candidates, "
        f"update {MEMORY}/RESEARCH-LOG.md with your findings and sizing mode, "
        f"and send a pre-market Telegram summary via {SCRIPTS}/telegram.sh."
    ),
    "market-open": (
        f"Run the market-open workflow: review today's {MEMORY}/RESEARCH-LOG.md trade ideas, "
        f"validate each against live prices via {SCRIPTS}/alpaca.sh, execute approved trades "
        f"with {SCRIPTS}/alpaca.sh buy, place 10% trailing stops immediately after each fill, "
        f"log every trade to {MEMORY}/TRADE-LOG.md, and send a Telegram notification per trade."
    ),
    "midday": (
        f"Run the midday workflow: check all open positions via {SCRIPTS}/alpaca.sh positions, "
        f"cut any losers at -7% with {SCRIPTS}/alpaca.sh close, tighten trailing stops for "
        f"positions up >=15% or >=20% per {MEMORY}/TRADING-STRATEGY.md, scan for new intraday "
        f"opportunities via {SCRIPTS}/perplexity.sh, update {MEMORY}/TRADE-LOG.md, "
        f"and send a Telegram midday update."
    ),
    "daily-summary": (
        f"Run the daily-summary workflow: pull EOD account equity and all position P&L via "
        f"{SCRIPTS}/alpaca.sh, compute day P&L vs prior close, append an EOD snapshot to "
        f"{MEMORY}/TRADE-LOG.md, and send the daily summary Telegram message. "
        f"Even on no-trade days the Telegram summary must fire."
    ),
    "weekly-review": (
        f"Run the weekly-review workflow: compute week P&L and compare vs S&P 500, "
        f"tally trades/win-rate/biggest winner/loser, document lessons learned, "
        f"append the entry to {MEMORY}/WEEKLY-REVIEW.md, and send the weekly Telegram summary."
    ),
    "research": (
        f"Run an ad-hoc research query using {SCRIPTS}/perplexity.sh. "
        f"Report findings and append a timestamped entry to {MEMORY}/RESEARCH-LOG.md."
    ),
    "status": (
        f"Run the status workflow: pull current equity, open positions, and open orders "
        f"via {SCRIPTS}/alpaca.sh. Display a concise snapshot — no trades, no writes needed."
    ),
}

REQUIRED_ENV_VARS = [
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "ALPACA_ENDPOINT",
    "ALPACA_DATA_ENDPOINT",
    "PERPLEXITY_API_KEY",
    "PERPLEXITY_MODEL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "GETX_API_KEY",
    "TRADINGBOT_AGENT_ID",
    "TRADINGBOT_ENV_ID",
    "GITHUB_TOKEN",
]


def load_dotenv():
    """Load .env file from the repo root into os.environ using python-dotenv."""
    try:
        from dotenv import load_dotenv as _load
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        _load(dotenv_path=env_path, override=False)
    except ImportError:
        # Fallback: manual parse if python-dotenv isn't installed
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if not os.path.exists(env_path):
            return
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())


def check_env_vars():
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)




def run_session(workflow: str, query: str | None = None):
    load_dotenv()
    check_env_vars()

    client = anthropic.Anthropic()
    agent_id = os.environ["TRADINGBOT_AGENT_ID"]
    env_id = os.environ["TRADINGBOT_ENV_ID"]
    github_token = os.environ["GITHUB_TOKEN"]

    kickoff = WORKFLOWS[workflow]
    if workflow == "research" and query:
        kickoff += f" Query: {query}"

    import datetime
    print(f"[tradingbot] Creating session for workflow: {workflow}")
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        title=f"TradingBot-Live / {workflow} / {datetime.date.today()}",
        resources=[
            {
                "type": "github_repository",
                "url": "https://github.com/codepioneerr/Traadingbot1-bot",
                "authorization_token": github_token,
                "mount_path": "/workspace",
                "checkout": {"type": "branch", "name": "main"},
            },
        ],
    )

    print(f"[tradingbot] Session: {session.id}")
    print(f"[tradingbot] Watch in Console: https://platform.claude.com/workspaces/default/sessions/{session.id}")

    # --- Step 1: Write credentials into the container's .env ---
    dotenv_vars = [
        "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ALPACA_ENDPOINT", "ALPACA_DATA_ENDPOINT",
        "PERPLEXITY_API_KEY", "PERPLEXITY_MODEL",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "GETX_API_KEY",
    ]
    dotenv_lines = "\n".join(f'{v}={os.environ[v]}' for v in dotenv_vars)
    dotenv_path = f"{BASE}/.env"

    print(f"[tradingbot] Writing credentials to container {dotenv_path}...")
    client.beta.sessions.events.send(
        session_id=session.id,
        events=[{
            "type": "user.message",
            "content": [{"type": "text", "text":
                f"Write the following content to {dotenv_path} exactly as shown "
                f"(use bash: printf '...') then confirm the file exists with `ls -la {dotenv_path}`:\n\n"
                f"{dotenv_lines}"
            }],
        }],
    )

    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(f"[setup] {block.text.strip()}")
            elif event.type == "session.status_idle":
                stop = getattr(event, "stop_reason", None)
                if stop and getattr(stop, "type", None) == "requires_action":
                    continue
                break
            elif event.type == "session.status_terminated":
                print("[tradingbot] Session terminated during .env setup.", file=sys.stderr)
                sys.exit(1)

    # --- Step 2: Smoke test Alpaca ---
    print("[tradingbot] Smoke-testing Alpaca connectivity...")
    client.beta.sessions.events.send(
        session_id=session.id,
        events=[{
            "type": "user.message",
            "content": [{"type": "text", "text":
                f"SMOKE TEST: Run `bash {SCRIPTS}/alpaca.sh account` and confirm "
                f"you get a valid account equity response. Reply with just the equity value. "
                f"Do NOT start the main workflow yet."
            }],
        }],
    )

    smoke_ok = False
    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(f"[smoke] {block.text.strip()}")
                        smoke_ok = True
            elif event.type == "session.status_idle":
                stop = getattr(event, "stop_reason", None)
                if stop and getattr(stop, "type", None) == "requires_action":
                    continue
                break
            elif event.type == "session.status_terminated":
                print("[tradingbot] Session terminated during smoke test.", file=sys.stderr)
                sys.exit(1)

    if not smoke_ok:
        print("[tradingbot] Smoke test failed — aborting.", file=sys.stderr)
        sys.exit(1)

    # --- Main workflow ---
    print(f"\n[tradingbot] Starting {workflow} workflow...")
    client.beta.sessions.events.send(
        session_id=session.id,
        events=[{
            "type": "user.message",
            "content": [{"type": "text", "text": kickoff}],
        }],
    )

    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(block.text, end="", flush=True)
            elif event.type == "agent.tool_use":
                print(f"\n[tool] {event.name}", flush=True)
            elif event.type == "session.error":
                print(f"\n[error] {event}", file=sys.stderr)
            elif event.type == "session.status_idle":
                stop = getattr(event, "stop_reason", None)
                if stop and getattr(stop, "type", None) == "requires_action":
                    continue
                break
            elif event.type == "session.status_terminated":
                break

    print(f"\n[tradingbot] Workflow complete.")


def main():
    parser = argparse.ArgumentParser(description="TradingBot-Live session runner")
    parser.add_argument(
        "--workflow",
        choices=list(WORKFLOWS.keys()),
        required=True,
        help="Which workflow to run",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Ad-hoc query string (for --workflow research only)",
    )
    args = parser.parse_args()
    run_session(args.workflow, args.query)


if __name__ == "__main__":
    main()
