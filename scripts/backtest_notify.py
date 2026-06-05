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


def latest_result(strategy: str, pattern_suffix: str = '') -> dict | None:
    results_dir = Path(__file__).parent.parent / 'backtest' / 'results'
    files = sorted(results_dir.glob(f'{strategy}{pattern_suffix}*.json'), reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


def format_evaluate_message(result: dict) -> str:
    """Format message for evaluate.py results (single-universe gate)."""
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


def format_analysis_message(result: dict) -> str:
    """Format message for analysis.py results (full grid)."""
    strategy = result.get('strategy', '?').upper()
    feed = result.get('feed', '?').upper()
    spy = result.get('spy_oos', {})
    grid = result.get('grid', {})

    # Count passes across grid
    passes = sum(1 for v in grid.values() if isinstance(v, dict) and v.get('verdict') == 'PASS')
    total = len(grid)

    lines = [
        f'🔬 *Full Analysis: {strategy}*',
        f'Feed: {feed}  |  OOS: {result.get("oos_start")} → {result.get("end")}',
        f'SPY return: {spy.get("total_return", 0):+.1%}  |  Sharpe: {spy.get("sharpe", 0):.2f}',
        '',
        f'*Grid: {passes}/{total} universe×timeframe cells PASS*',
        '',
    ]

    # Show best performing cell
    best = max(
        ((k, v) for k, v in grid.items() if isinstance(v, dict) and v.get('total_return') is not None),
        key=lambda x: x[1].get('total_return', -999),
        default=(None, None),
    )
    if best[0]:
        bk, bv = best
        lines.append(f'Best cell: `{bk}`')
        lines.append(f'  Return={bv.get("total_return", 0):+.1%}  Sharpe={bv.get("sharpe", 0):.2f}  '
                     f'PF={bv.get("profit_factor", 0):.2f}  Trades={bv.get("trade_count", 0)}')

    # Monte Carlo summary
    mc = result.get('monte_carlo', {})
    if mc and 'actual_rank_pct' in mc:
        rank = mc['actual_rank_pct']
        ruin = mc.get('ruin_probability', 0)
        lines.append(f'\nMC rank: {rank:.0f}th pct  |  Ruin prob: {ruin:.1%}')

    # Walk-forward
    wf = result.get('walk_forward')
    if wf and wf.get('n_windows'):
        lines.append(f'Walk-forward: {wf["n_windows"]} windows  |  {wf.get("trade_count", 0)} OOS trades')

    # Feature importance — top 2
    fi = result.get('feature_importance', {})
    imp = fi.get('importances', {})
    if imp:
        top2 = sorted(imp.items(), key=lambda x: -x[1])[:2]
        lines.append(f'Top features: {top2[0][0]} ({top2[0][1]:.3f}), {top2[1][0]} ({top2[1][1]:.3f})')

    return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python scripts/backtest_notify.py <strategy> <start> <end> [--full-analysis] [--quick]')
        sys.exit(1)

    strategy, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
    full_analysis = '--full-analysis' in sys.argv
    quick = '--quick' in sys.argv
    mode = 'full-analysis' if full_analysis else 'evaluate'

    print(f'[{datetime.now():%H:%M:%S}] Starting {mode}: {strategy} {start} → {end}')
    send_telegram(
        f'⏳ *{"Full Analysis" if full_analysis else "Backtest"} starting: {strategy.upper()}*\n'
        f'{start} → {end}\n_Results will arrive when complete._'
    )

    repo_root = Path(__file__).parent.parent
    oos_start_flag = None
    for i, arg in enumerate(sys.argv):
        if arg == '--oos-start' and i + 1 < len(sys.argv):
            oos_start_flag = sys.argv[i + 1]

    if full_analysis:
        cmd = [sys.executable, '-u', '-m', 'backtest.analysis', strategy, start, end]
        if quick:
            cmd.append('--quick')
        if oos_start_flag:
            cmd += ['--oos-start', oos_start_flag]
        result_suffix = '_analysis_'
        format_fn = format_analysis_message
    else:
        cmd = [sys.executable, '-u', '-m', 'backtest.evaluate', strategy, start, end]
        if oos_start_flag:
            cmd += ['--oos-start', oos_start_flag]
        result_suffix = '_'
        format_fn = format_evaluate_message

    result_proc = subprocess.run(cmd, cwd=str(repo_root))

    if result_proc.returncode != 0:
        send_telegram(f'💥 *{"Analysis" if full_analysis else "Backtest"} crashed: {strategy.upper()}*\n'
                      f'Check the terminal for the traceback.')
        sys.exit(result_proc.returncode)

    result = latest_result(strategy, pattern_suffix=result_suffix if full_analysis else '')
    if result:
        msg = format_fn(result)
        send_telegram(msg)
    else:
        send_telegram(f'⚠️ Run finished but no result file found for {strategy}.')
