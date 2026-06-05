"""
Overnight backtest runner — designed to survive terminal closure.

Run with nohup so the process keeps going if the terminal disconnects:

    nohup python -m backtest.run_overnight > backtest/logs/overnight.log 2>&1 &
    echo "PID: $!"   # save this to kill it if needed

Default run: full analysis on 2021-2026 with IS=2021-2023, OOS=2024-2026.
Sends Telegram when it starts, and again with the full scorecard when done.

Optional flags:
    --oos-start 2024-01-02   explicit IS/OOS boundary (default)
    --start     2021-01-04   backtest start date (default)
    --end       2026-01-03   backtest end date (default)
    --quick                  skip walk-forward (faster, good for debugging)
    --strategy  orb          strategy name (default: orb)
"""
from __future__ import annotations

import os
import sys
import json
import signal
import traceback
from datetime import datetime
from pathlib import Path

# ── ensure repo root is importable ─────────────────────────────────────────
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

# ── load .env if present (not present in scheduled/remote runs) ────────────
_env = REPO / '.env'
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith('#') and '=' in _line:
            _k, _, _v = _line.partition('=')
            os.environ.setdefault(_k.strip(), _v.strip())


# ── Telegram helper ─────────────────────────────────────────────────────────

def _telegram(msg: str) -> None:
    """Send a plain-text Telegram message. Silently skips if creds missing."""
    import requests
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        print('[telegram] credentials missing — skipping notification')
        return
    try:
        r = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data={'chat_id': chat_id, 'text': msg},
            timeout=15,
        )
        if r.status_code == 200:
            print(f'[telegram] sent ✓')
        else:
            print(f'[telegram] failed {r.status_code}: {r.text[:100]}')
    except Exception as e:
        print(f'[telegram] error: {e}')


# ── Result formatter ────────────────────────────────────────────────────────

def _format_result(result: dict) -> str:
    """Plain-text summary for Telegram."""
    strategy = result.get('strategy', '?').upper()
    feed = result.get('feed', '?').upper()
    oos_start = result.get('oos_start', '?')
    end = result.get('end', '?')
    spy = result.get('spy_oos', {})
    grid = result.get('grid', {})

    passes = sum(1 for v in grid.values() if isinstance(v, dict) and v.get('verdict') == 'PASS')
    total = len(grid)

    lines = [
        f'BACKTEST COMPLETE: {strategy}',
        f'Feed: {feed}  OOS: {oos_start} to {end}',
        f'SPY benchmark: return={spy.get("total_return", 0):+.1%}  sharpe={spy.get("sharpe", 0):.2f}',
        '',
        f'GRID: {passes}/{total} cells PASS',
        '',
    ]

    # Best and worst cells
    scored = [(k, v) for k, v in grid.items()
              if isinstance(v, dict) and v.get('total_return') is not None]
    if scored:
        best = max(scored, key=lambda x: x[1].get('total_return', -999))
        worst = min(scored, key=lambda x: x[1].get('total_return', 999))
        bk, bv = best
        wk, wv = worst
        lines.append(f'Best:  {bk}  return={bv.get("total_return", 0):+.1%}  '
                     f'sharpe={bv.get("sharpe", 0):.2f}  PF={bv.get("profit_factor", 0):.2f}  '
                     f'verdict={bv.get("verdict","?")}')
        lines.append(f'Worst: {wk}  return={wv.get("total_return", 0):+.1%}  '
                     f'sharpe={wv.get("sharpe", 0):.2f}  PF={wv.get("profit_factor", 0):.2f}')
        lines.append('')

    # All grid rows
    lines.append('Full grid (OOS realistic vs SPY):')
    for universe in ['large_cap', 'small_cap', 'etf', 'crypto']:
        for or_w in [1, 5, 15]:
            v = grid.get(f"('{universe}', {or_w})")
            if v is None:
                # try tuple-key format written by json.dump(default=str)
                for k in grid:
                    if universe in str(k) and str(or_w) in str(k):
                        v = grid[k]; break
            if v and isinstance(v, dict):
                icon = 'PASS' if v.get('verdict') == 'PASS' else 'FAIL'
                lines.append(f'  {universe:<12} {or_w:>2}m  '
                              f'{v.get("total_return", 0):+.1%}  '
                              f'sharpe={v.get("sharpe", 0):.2f}  '
                              f'PF={v.get("profit_factor", 0):.2f}  {icon}')

    # Monte Carlo
    mc = result.get('monte_carlo', {})
    if mc and 'bootstrap_return_rank_pct' in mc:
        lines.append(f'\nMC bootstrap rank: {mc["bootstrap_return_rank_pct"]:.0f}th pct  '
                     f'ruin prob: {mc.get("bootstrap_ruin_probability", 0):.1%}')

    # Walk-forward summary
    wf = result.get('walk_forward')
    if wf and wf.get('n_windows'):
        lines.append(f'Walk-forward: {wf["n_windows"]} windows  '
                     f'{wf.get("trade_count", 0)} OOS trades  '
                     f'final equity: ${wf.get("final_equity", 0):,.0f}')

    # Feature importance top 2
    fi = result.get('feature_importance', {})
    imp = fi.get('importances', {})
    if imp:
        top = sorted(imp.items(), key=lambda x: -x[1])[:2]
        lines.append(f'Top features: {top[0][0]} ({top[0][1]:.3f}), '
                     f'{top[1][0]} ({top[1][1]:.3f})')

    # Slippage breakeven
    sens = result.get('sensitivity', {})
    if sens:
        breakeven = None
        for bps in [0, 5, 10, 15, 20]:
            sc = sens.get(f'{bps}bps', {})
            if sc.get('total_return', 0) <= 0:
                breakeven = bps; break
        if breakeven is not None:
            lines.append(f'Slippage breakeven: {breakeven} bps/side')
        else:
            lines.append('Slippage: profitable at all tested levels (0-20 bps)')

    return '\n'.join(lines)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    # Parse CLI flags
    args = sys.argv[1:]

    def _get(flag, default):
        for i, a in enumerate(args):
            if a == flag and i + 1 < len(args):
                return args[i + 1]
        return default

    strategy  = _get('--strategy',  'orb')
    start     = _get('--start',     '2021-01-04')
    end       = _get('--end',       '2026-01-03')
    oos_start = _get('--oos-start', '2024-01-02')
    quick     = '--quick' in args

    # Ensure log dir exists
    log_dir = REPO / 'backtest' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] run_overnight starting', flush=True)
    print(f'  strategy={strategy}  start={start}  end={end}  oos_start={oos_start}  quick={quick}', flush=True)

    _telegram(
        f'BACKTEST STARTING: {strategy.upper()}\n'
        f'{start} to {end}\n'
        f'IS: {start} to {oos_start}  OOS: {oos_start} to {end}\n'
        f'Mode: {"quick (no walk-forward)" if quick else "full"}\n'
        f'Results will arrive when complete.'
    )

    # ── Graceful SIGTERM handler ─────────────────────────────────────────────
    def _handle_sigterm(signum, frame):
        _telegram(f'BACKTEST INTERRUPTED: {strategy.upper()}\n'
                  f'Process received SIGTERM — run killed before completion.')
        sys.exit(1)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    # ── Run the analysis ─────────────────────────────────────────────────────
    result = None
    try:
        from backtest.analysis import run_full_analysis
        result = run_full_analysis(
            strategy_name=strategy,
            start=start,
            end=end,
            oos_start=oos_start,
            quick=quick,
        )

    except KeyboardInterrupt:
        _telegram(f'BACKTEST INTERRUPTED: {strategy.upper()}\nProcess killed (KeyboardInterrupt).')
        raise

    except Exception as e:
        tb = traceback.format_exc()
        print(f'\nFATAL ERROR:\n{tb}', flush=True)
        _telegram(
            f'BACKTEST CRASHED: {strategy.upper()}\n'
            f'Error: {str(e)[:200]}\n'
            f'Check backtest/logs/overnight.log for traceback.'
        )
        sys.exit(1)

    # ── Send completion notification ─────────────────────────────────────────
    print(f'\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Analysis complete.', flush=True)

    if result:
        msg = _format_result(result)
        _telegram(msg)
    else:
        _telegram(f'BACKTEST COMPLETE: {strategy.upper()}\nResult object was empty — check logs.')

    print('[run_overnight] Done.', flush=True)


if __name__ == '__main__':
    main()
