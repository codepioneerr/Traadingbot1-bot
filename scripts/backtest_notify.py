#!/usr/bin/env python3
"""
Run a backtest and send a Telegram notification when it finishes.

Usage:
    python scripts/backtest_notify.py orb 2022-01-01 2026-01-01

Reads credentials from .env automatically.
Sends a summary Telegram message with PASS/FAIL and key scorecard numbers.
"""
import sys
import os
import subprocess
import json
import requests
from pathlib import Path
from datetime import datetime

# Load .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip())


def send_telegram(msg: str) -> None:
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        print('[telegram] credentials missing — printing message instead:')
        print(msg)
        return
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    resp = requests.post(url, data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
    if resp.status_code == 200:
        print('[telegram] notification sent ✓')
    else:
        print(f'[telegram] send failed: {resp.status_code} {resp.text}')


def latest_result(strategy: str) -> dict | None:
    results_dir = Path(__file__).parent.parent / 'backtest' / 'results'
    files = sorted(results_dir.glob(f'{strategy}_*.json'), reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


def format_message(result: dict) -> str:
    verdict = result.get('verdict', 'UNKNOWN')
    icon = '✅' if verdict == 'PASS' else '❌'
    strategy = result.get('strategy', '?').upper()
    feed = result.get('feed', '?').upper()
    oos_start = result.get('oos_start', '?')
    end = result.get('end', '?')

    sc = result.get('passes', {}).get('realistic_5bps', {})
    spy = result.get('spy_oos', {})

    lines = [
        f'{icon} *Backtest complete: {strategy}*',
        f'Feed: {feed}  |  OOS: {oos_start} → {end}',
        '',
        f'*Verdict: {verdict}* (OOS realistic 5bps vs SPY)',
        '',
        f'Return : {sc.get("total_return", 0):+.1%}  (SPY: {spy.get("total_return", 0):+.1%})',
        f'Sharpe : {sc.get("sharpe", 0):.2f}  (SPY: {spy.get("sharpe", 0):.2f})',
        f'Max DD : {sc.get("max_drawdown", 0):.1%}  (SPY: {spy.get("max_drawdown", 0):.1%})',
        f'PF     : {sc.get("profit_factor", 0):.2f}  |  Trades: {sc.get("trade_count", 0)}',
        f'Win %  : {sc.get("win_rate", 0):.1%}',
    ]

    failures = result.get('failures', [])
    if failures:
        lines.append('')
        lines.append('*Failures:*')
        for f in failures:
            lines.append(f'  ✗ {f}')

    params = result.get('best_params', {})
    if params:
        lines.append(f'\nBest params: `{params}`')

    return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python scripts/backtest_notify.py <strategy> <start> <end>')
        sys.exit(1)

    strategy, start, end = sys.argv[1], sys.argv[2], sys.argv[3]

    print(f'[{datetime.now():%H:%M:%S}] Starting backtest: {strategy} {start} → {end}')
    send_telegram(f'⏳ *Backtest starting: {strategy.upper()}*\n{start} → {end}\n_Results will arrive when complete._')

    # Run the backtest as a subprocess so output streams live
    repo_root = Path(__file__).parent.parent
    cmd = [sys.executable, '-m', 'backtest.evaluate', strategy, start, end]
    result_proc = subprocess.run(cmd, cwd=str(repo_root))

    if result_proc.returncode != 0:
        send_telegram(f'💥 *Backtest crashed: {strategy.upper()}*\nCheck the terminal for the traceback.')
        sys.exit(result_proc.returncode)

    # Read the result and send summary
    result = latest_result(strategy)
    if result:
        msg = format_message(result)
        send_telegram(msg)
    else:
        send_telegram(f'⚠️ Backtest finished but no result file found for {strategy}.')
