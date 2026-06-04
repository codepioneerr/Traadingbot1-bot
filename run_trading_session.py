#!/usr/bin/env python3
"""
TradingBot-Live session runner.
Usage: python run_trading_session.py --workflow pre-market
"""

import anthropic
import argparse
import os
import sys

WORKFLOWS = {
    "pre-market": (
        "Run the pre-market workflow: check VIX and S&P futures via scripts/perplexity.sh, "
        "determine today's sizing mode per TRADING-STRATEGY.md, identify 3-5 trade candidates, "
        "update memory/RESEARCH-LOG.md with your findings and sizing mode, "
        "and send a pre-market Telegram summary via scripts/telegram.sh."
    ),
    "market-open": (
        "Run the market-open workflow: review today's RESEARCH-LOG trade ideas, "
        "validate each against live prices via scripts/alpaca.sh, execute approved trades "
        "with scripts/alpaca.sh buy, place 10% trailing stops immediately after each fill, "
        "log every trade to memory/TRADE-LOG.md, and send a Telegram notification per trade."
    ),
    "midday": (
        "Run the midday workflow: check all open positions via scripts/alpaca.sh positions, "
        "cut any losers at -7% with scripts/alpaca.sh close, tighten trailing stops for "
        "positions up >=15% or >=20% per TRADING-STRATEGY.md, scan for new intraday opportunities "
        "via scripts/perplexity.sh, update TRADE-LOG.md, and send a Telegram midday update."
    ),
    "daily-summary": (
        "Run the daily-summary workflow: pull EOD account equity and all position P&L via "
        "scripts/alpaca.sh, compute day P&L vs prior close, append an EOD snapshot to "
        "memory/TRADE-LOG.md, and send the daily summary Telegram message. "
        "Even on no-trade days the Telegram summary must fire."
    ),
    "weekly-review": (
        "Run the weekly-review workflow: compute week P&L and compare vs S&P 500, "
        "tally trades/win-rate/biggest winner/loser, document lessons learned, "
        "append the entry to memory/WEEKLY-REVIEW.md, and send the weekly Telegram summary."
    ),
    "research": (
        "Run an ad-hoc research query using scripts/perplexity.sh. "
        "Report findings and append a timestamped entry to memory/RESEARCH-LOG.md."
    ),
    "status": (
        "Run the status workflow: pull current equity, open positions, and open orders "
        "via scripts/alpaca.sh. Display a concise snapshot — no trades, no writes needed."
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

    # --- Smoke test: verify Alpaca is reachable before burning tokens ---
    print("[tradingbot] Smoke-testing Alpaca connectivity...")
    client.beta.sessions.events.send(
        session_id=session.id,
        events=[{
            "type": "user.message",
            "content": [{"type": "text", "text":
                "SMOKE TEST: Run `bash /workspace/scripts/alpaca.sh account` and confirm "
                "you get a valid account equity response. Reply with just the equity value. "
                "Do NOT start the main workflow yet."
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
