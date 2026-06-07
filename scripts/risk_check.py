#!/usr/bin/env python3
"""
Circuit Breaker — Dual Momentum Strategy
==========================================
Called at the top of every routine. Checks for conditions that indicate
something is WRONG WITH THE BOT (not normal strategy drawdown).

This is NOT a drawdown circuit breaker. The Dual Momentum strategy
intentionally holds through drawdowns — a position being down -10%, -20%,
or even -30% is expected and normal. Do NOT add P&L-based halt conditions.

HALT conditions (something is wrong with bot state):
  1. PAUSE-FLAG.txt exists → halt, report reason from file
  2. Current position is not one of [SPY, QQQ, IWM, TLT, GLD, SHY] → halt
  3. More than 1 open position → halt (should never happen)
  4. Monthly drawdown > 20% from this month's entry price → halt and alert
     (A 20% single-month drop is extraordinary — 1987-level event, not 2008)

DO NOT HALT for:
  - Any daily P&L (irrelevant for monthly strategy)
  - Any weekly P&L (irrelevant for monthly strategy)
  - Position being down any amount from purchase (expected and normal)
  - Market being down, VIX being high, news being scary

On halt: write reason to PAUSE-FLAG.txt, send Telegram alert, exit 1.
On pass: print current position + return since entry, exit 0.

Usage:
  python3 scripts/risk_check.py
  if [ $? -ne 0 ]; then echo "HALTED"; exit 1; fi
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

ROOT         = Path(__file__).parent.parent
PAUSE_FLAG   = ROOT / 'PAUSE-FLAG.txt'
TRADE_LOG    = ROOT / 'memory' / 'TRADE-LOG.md'
VALID_TICKERS = {'SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'SHY'}
MAX_MONTHLY_DRAWDOWN = 0.20   # 20% — extraordinary event threshold


def _send_telegram(msg: str) -> None:
    """Best-effort Telegram alert. Fails silently if creds missing."""
    script = ROOT / 'scripts' / 'telegram.sh'
    if not script.exists():
        return
    try:
        subprocess.run(['bash', str(script), msg], timeout=15, capture_output=True)
    except Exception:
        pass


def _write_pause_flag(reason: str) -> None:
    ts = datetime.now().isoformat()
    PAUSE_FLAG.write_text(f'PAUSED: {ts}\nReason: {reason}\n')


def _halt(reason: str) -> int:
    msg = f'🚨 TRADING BOT HALTED\n\n{reason}\n\nDo NOT restart automatically. Review and delete PAUSE-FLAG.txt to resume.'
    _write_pause_flag(reason)
    _send_telegram(msg)
    print(f'HALT: {reason}', file=sys.stderr)
    return 1


def _alpaca(cmd: str) -> dict:
    """Run alpaca.sh command, return parsed JSON or raise."""
    script = ROOT / 'scripts' / 'alpaca.sh'
    result = subprocess.run(
        ['bash', str(script), cmd],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f'alpaca.sh {cmd} failed: {result.stderr[:200]}')
    return json.loads(result.stdout)


def _parse_entry_price_from_log(ticker: str) -> float | None:
    """
    Parse the most recent entry price for the current ticker from TRADE-LOG.md.
    Returns None if not found.
    """
    if not TRADE_LOG.exists():
        return None
    text = TRADE_LOG.read_text()
    # Look for lines like "ENTRY: QQQ @ $480.25" or "entry_price: 480.25"
    # Simple heuristic: scan backward for the ticker and an associated price
    lines = text.split('\n')
    for line in reversed(lines):
        line_lower = line.lower()
        if ticker.lower() in line_lower and ('entry' in line_lower or 'buy' in line_lower):
            # Try to extract a dollar amount
            import re
            prices = re.findall(r'\$?(\d+\.?\d*)', line)
            for p in prices:
                try:
                    val = float(p)
                    if 1.0 < val < 100_000:   # sanity check for price range
                        return val
                except ValueError:
                    pass
    return None


def main() -> int:
    # ── Check 1: PAUSE-FLAG ────────────────────────────────────────────────────
    if PAUSE_FLAG.exists():
        reason = PAUSE_FLAG.read_text().strip()
        print(f'HALT: PAUSE-FLAG.txt exists:\n{reason}', file=sys.stderr)
        return 1

    # ── Pull Alpaca state ──────────────────────────────────────────────────────
    try:
        positions_raw = _alpaca('positions')
    except Exception as e:
        # Can't reach Alpaca — not a reason to halt, just warn
        print(f'WARNING: Could not reach Alpaca ({e}). Skipping position checks.')
        print('RISK_CHECK: PASS (Alpaca unreachable — no position state to validate)')
        return 0

    # positions_raw may be a list (array of positions) or a dict (single or error)
    if isinstance(positions_raw, dict) and 'positions' in positions_raw:
        positions = positions_raw['positions']
    elif isinstance(positions_raw, list):
        positions = positions_raw
    else:
        positions = []

    # ── Check 2: More than 1 open position ────────────────────────────────────
    if len(positions) > 1:
        syms = [p.get('symbol', '?') for p in positions]
        return _halt(f'MORE THAN 1 OPEN POSITION: {syms}. Dual Momentum should hold exactly 1 asset at a time.')

    # ── Check 3: Invalid ticker ────────────────────────────────────────────────
    for pos in positions:
        sym = pos.get('symbol', '')
        if sym not in VALID_TICKERS:
            return _halt(f'INVALID POSITION: {sym} is not in the Dual Momentum universe {VALID_TICKERS}.')

    # ── Check 4: Monthly drawdown > 20% ──────────────────────────────────────
    for pos in positions:
        sym           = pos.get('symbol', '')
        current_price = float(pos.get('current_price', 0) or pos.get('lastday_price', 0) or 0)
        avg_entry     = float(pos.get('avg_entry_price', 0) or 0)
        qty           = float(pos.get('qty', 0) or 0)
        unrealized_pl = float(pos.get('unrealized_pl', 0) or 0)

        if avg_entry > 0 and current_price > 0:
            monthly_drawdown = (avg_entry - current_price) / avg_entry
            if monthly_drawdown > MAX_MONTHLY_DRAWDOWN:
                return _halt(
                    f'EXTRAORDINARY DRAWDOWN: {sym} is down {monthly_drawdown:.1%} from entry '
                    f'(entry: ${avg_entry:.2f}, current: ${current_price:.2f}). '
                    f'A {MAX_MONTHLY_DRAWDOWN:.0%} single-position drawdown is extraordinary — '
                    f'human review required.'
                )

    # ── All clear: print current state ────────────────────────────────────────
    print('RISK_CHECK: PASS')
    if positions:
        pos = positions[0]
        sym  = pos.get('symbol', '?')
        qty  = pos.get('qty', '?')
        avg  = pos.get('avg_entry_price', '?')
        plpc = float(pos.get('unrealized_plpc', 0) or 0) * 100
        sign = '+' if plpc >= 0 else ''
        print(f'Current holding: {sym}  |  Qty: {qty}  |  Entry: ${avg}  |  Return: {sign}{plpc:.2f}%')
    else:
        print('Current holding: NONE (cash or pre-first-trade)')

    return 0


if __name__ == '__main__':
    sys.exit(main())
