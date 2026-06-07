"""
Strategy Pivot — Experiments A and B
======================================

Runs two competing hypotheses against the earnings universe:
  A: 1-Day Earnings Momentum (long the gap-up open, exit at EOD)
  B: Overreaction Fade (short the gap-up open, cover at TP/stop/EOD, max 3 days)

Uses a standalone simulation (NOT BacktestEngine) because both strategies require:
  - Entry at open price (not close)
  - Intraday exit levels (stop/TP approximated from OHLC low/high)
  - Engine fills at bar['c'] by default, which is wrong for these strategies

Position sizing:
  20% of starting equity per position, max 6 concurrent.
  On days with more signals than available slots, signals ranked by |SUE| (highest first).
  Each simulation tracks daily equity for Sharpe and max-drawdown.

Usage:
    python3 backtest/run_pivot.py
    python3 backtest/run_pivot.py --exp A
    python3 backtest/run_pivot.py --exp B
"""
from __future__ import annotations

import sys
import json
import math
import argparse
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backtest.earnings_data import load_all_earnings
from backtest.sp500_pool import SP500_STABLE_POOL
from backtest.run_pead import load_daily_bars_cached, _load_pkl_or_json, RESULTS_DIR
from backtest.strategies.earnings_momentum_1d import (
    compute_momentum_1d_signals, simulate_momentum_1d_trade
)
from backtest.strategies.overreaction_fade import (
    compute_overreaction_fade_signals, simulate_overreaction_trade
)

OOS_START  = '2024-01-01'
FULL_START = '2021-01-01'
FULL_END   = '2026-01-03'

POS_PCT      = 0.20    # 20% of equity per position
MAX_POSITIONS = 6
START_EQUITY  = 100_000.0


# ── Shared data loading ───────────────────────────────────────────────────────

def load_shared_data() -> dict:
    t0 = time.time()
    daily_bars_by_sym: dict[str, list[dict]] = {}
    for sym in SP500_STABLE_POOL:
        b = load_daily_bars_cached(sym)
        if b:
            daily_bars_by_sym[sym] = b

    earnings_by_sym = load_all_earnings(SP500_STABLE_POOL)
    usable = set(earnings_by_sym) & set(daily_bars_by_sym)
    earnings_by_sym   = {s: v for s, v in earnings_by_sym.items()   if s in usable}
    daily_bars_by_sym = {s: v for s, v in daily_bars_by_sym.items() if s in usable}

    print(f'  {len(usable)} symbols usable  ({time.time()-t0:.1f}s)')
    return {'earnings_by_sym': earnings_by_sym, 'daily_bars_by_sym': daily_bars_by_sym}


# ── Portfolio simulation ──────────────────────────────────────────────────────

def simulate_portfolio(
    trade_results: list[dict],   # output of simulate_*_trade for each signal
    start_equity: float = START_EQUITY,
    pos_pct:      float = POS_PCT,
    max_pos:      int   = MAX_POSITIONS,
    calendar_bars: list[dict] | None = None,  # full trading calendar for equity curve
) -> dict:
    """
    Simulate a portfolio of independent trades.

    Design:
      - Groups signals by entry_date, takes top max_pos per day (sorted by |SUE|)
      - P&L is realised on exit_date (computed from hold_days or same day for 1-day)
      - Equity curve spans every date in calendar_bars (or just signal dates if None)
      - For max_pos enforcement on multi-day holds: tracks concurrent open count

    Key fix: 1-day trades (entry_date == exit_date) are fully processed in one pass.
    Open positions are only penalised against max_pos BEFORE exit, not after.
    """
    # Group by entry_date
    by_entry: dict[str, list[dict]] = defaultdict(list)
    for t in trade_results:
        by_entry[t['entry_date']].append(t)

    # Pre-compute exit_date for each signal
    def _exit_date(result: dict) -> str:
        hb = result.get('hold_bars', [])
        hd = result.get('hold_days', 1)
        if hb and 0 < hd <= len(hb):
            return hb[hd - 1]['t']
        return result['entry_date']   # same-day for 1-day strategies

    # Sort all entry dates
    all_entry_dates = sorted(by_entry.keys())

    # Track which positions are still open on each date (for max_pos enforcement)
    # open_count[date] = number of positions that entered ≤ date and exit ≥ date
    # Simplified: process chronologically and track a running open count
    equity    = start_equity
    all_trades: list[dict] = []
    pnl_by_date: dict[str, float] = defaultdict(float)  # realised P&L by exit_date

    # Track concurrent open positions
    open_slots: list[str] = []   # exit_dates of currently open positions

    for date in all_entry_dates:
        # Remove positions that closed before today
        open_slots = [ed for ed in open_slots if ed >= date]
        available  = max_pos - len(open_slots)

        todays = sorted(
            by_entry[date],
            key=lambda t: abs(t.get('sue', 0)),
            reverse=True,
        )[:available]

        for result in todays:
            entry_fill = result['entry_fill']
            if entry_fill <= 0:
                continue
            qty = max(1, int(equity * pos_pct / entry_fill))
            realised   = qty * result['pnl_pct'] * entry_fill
            exit_d     = _exit_date(result)

            pnl_by_date[exit_d] += realised
            open_slots.append(exit_d)

            all_trades.append({
                **{k: v for k, v in result.items() if k != 'hold_bars'},
                'qty':        qty,
                'realised':   realised,
                'entry_date': date,
                'exit_date':  exit_d,
            })

        # Update equity at end of day (realise any P&L closing today)
        equity += pnl_by_date.get(date, 0.0)

    # Build daily equity curve over all trading dates with trades
    # Use the full set of dates (entry + exit dates) for a smooth curve
    all_dates_set = set(pnl_by_date.keys()) | set(all_entry_dates)
    if calendar_bars:
        # Add all calendar dates between first and last trade
        first_d = min(all_dates_set) if all_dates_set else FULL_START
        last_d  = max(all_dates_set) if all_dates_set else FULL_END
        all_dates_set |= {b['t'] for b in calendar_bars
                          if first_d <= b['t'] <= last_d}

    eq    = start_equity
    daily_equity: list[float] = []
    for date in sorted(all_dates_set):
        if not (FULL_START <= date <= FULL_END):
            continue
        eq += pnl_by_date.get(date, 0.0)
        daily_equity.append(eq)

    return {
        'trades':       all_trades,
        'daily_equity': daily_equity or [start_equity],
        'final_equity': eq,
    }


# ── Metrics ───────────────────────────────────────────────────────────────────

def _profit_factor(trades: list[dict]) -> float:
    wins   = sum(t['realised'] for t in trades if t['realised'] > 0)
    losses = sum(-t['realised'] for t in trades if t['realised'] < 0)
    return wins / losses if losses > 0 else (float('inf') if wins > 0 else 0.0)

def _win_rate(trades: list[dict]) -> float:
    if not trades: return 0.0
    return sum(1 for t in trades if t['realised'] > 0) / len(trades)

def _total_return(curve: list[float]) -> float:
    if len(curve) < 2 or curve[0] == 0: return 0.0
    return (curve[-1] - curve[0]) / curve[0]

def _sharpe(curve: list[float], rf: float = 0.04) -> float:
    if len(curve) < 11: return 0.0
    rets = [(curve[i] - curve[i-1]) / curve[i-1] for i in range(1, len(curve))
            if curve[i-1] > 0]
    if len(rets) < 10: return 0.0
    rf_d   = (1 + rf) ** (1/252) - 1
    excess = [r - rf_d for r in rets]
    mean   = sum(excess) / len(excess)
    var    = sum((r - mean)**2 for r in excess) / max(1, len(excess) - 1)
    std    = math.sqrt(var) if var > 0 else 0.0
    return (mean / std) * math.sqrt(252) if std > 0 else 0.0

def _max_drawdown(curve: list[float]) -> float:
    peak = curve[0] if curve else 0
    dd   = 0.0
    for v in curve:
        if v > peak: peak = v
        if peak > 0: dd = max(dd, (peak - v) / peak)
    return dd

def _year_breakdown(trades: list[dict]) -> dict:
    years: dict = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
    for t in trades:
        y = t['entry_date'][:4]
        years[y]['trades'] += 1
        years[y]['pnl']    += t['realised']
        if t['realised'] > 0:
            years[y]['wins'] += 1
    return dict(years)

def _ci_wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0: return 0.0, 0.0
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / d
    return max(0.0, c-h), min(1.0, c+h)

def _avg_hold(trades: list[dict]) -> float:
    holds = [t.get('hold_days', 1) for t in trades]
    return sum(holds) / len(holds) if holds else 0.0

def _exit_breakdown(trades: list[dict]) -> dict:
    counts: dict[str, int] = defaultdict(int)
    for t in trades:
        r = t.get('exit_reason', 'unknown')
        # normalise multi-day time stops
        if r and r.startswith('time_day'):
            r = f'time_day{t.get("hold_days", "?")}'
        counts[r] += 1
    return dict(counts)


def _print_scorecard(label: str, trades: list[dict], curve: list[float]):
    pf  = _profit_factor(trades)
    wr  = _win_rate(trades)
    tr  = _total_return(curve)
    sh  = _sharpe(curve)
    dd  = _max_drawdown(curve)
    n   = len(trades)
    wins = sum(1 for t in trades if t['realised'] > 0)
    ci_lo, ci_hi = _ci_wilson(wins, n)

    print(f'\n  {"─"*55}')
    print(f'  {label}')
    print(f'  {"─"*55}')
    print(f'  Trades      : {n}')
    print(f'  Profit Factor: {pf:.3f}')
    print(f'  Sharpe       : {sh:.3f}')
    print(f'  Win Rate     : {wr:.1%}  (95% CI [{ci_lo:.1%}, {ci_hi:.1%}])')
    print(f'  Total Return : {tr:+.2%}')
    print(f'  Max Drawdown : {dd:.2%}')
    exits = _exit_breakdown(trades)
    if exits:
        print(f'  Exit reasons : {dict(exits)}')
    avg_hold = _avg_hold(trades)
    if avg_hold > 0:
        print(f'  Avg hold days: {avg_hold:.1f}')

    if n > 0:
        win_trades  = [t for t in trades if t['realised'] > 0]
        loss_trades = [t for t in trades if t['realised'] < 0]
        avg_win_pct  = sum(t.get('pnl_pct', 0) for t in win_trades)  / len(win_trades)  if win_trades  else 0
        avg_loss_pct = sum(t.get('pnl_pct', 0) for t in loss_trades) / len(loss_trades) if loss_trades else 0
        print(f'  Avg win  %   : {avg_win_pct:+.2%}')
        print(f'  Avg loss %   : {avg_loss_pct:+.2%}')


def _print_year_table(year_data: dict, oos_start: str = OOS_START):
    print(f'\n  {"Year":<6} {"Trades":>7} {"WR%":>6} {"$PnL":>12}  {"IS/OOS"}')
    print(f'  {"─"*42}')
    for yr in sorted(year_data):
        yd  = year_data[yr]
        wr  = yd['wins'] / yd['trades'] if yd['trades'] else 0
        tag = 'OOS' if yr >= oos_start[:4] else 'IS'
        print(f'  {yr:<6} {yd["trades"]:>7} {wr:>6.1%} {yd["pnl"]:>12,.0f}  {tag}')
    print(f'  {"─"*42}')


def _split_is_oos(trades: list[dict], daily_eq: list[float], date_list: list[str]):
    """
    Split trades and equity curve into IS/OOS halves.
    date_list must be aligned 1:1 with daily_eq (same length, same order).
    """
    is_trades  = [t for t in trades if t['entry_date'] < OOS_START]
    oos_trades = [t for t in trades if t['entry_date'] >= OOS_START]

    # Find the split index in the equity curve date list
    try:
        oos_idx = next(i for i, d in enumerate(date_list) if d >= OOS_START)
    except StopIteration:
        oos_idx = len(daily_eq)

    is_curve  = daily_eq[:oos_idx] or [START_EQUITY]
    oos_start_eq = daily_eq[oos_idx - 1] if oos_idx > 0 else START_EQUITY
    oos_curve = [oos_start_eq] + daily_eq[oos_idx:] if daily_eq[oos_idx:] else [oos_start_eq]

    return is_trades, oos_trades, is_curve, oos_curve


# ── EXPERIMENT A ──────────────────────────────────────────────────────────────

def run_experiment_a(data: dict) -> dict:
    print('\n' + '='*65)
    print('  EXPERIMENT A — 1-Day Earnings Momentum (Long Only)')
    print('  SUE ≥ 10%, reaction ≥ +2%, vol ≥ 1.5×')
    print('  Entry: day-1 open  |  Exit: day-1 close or −3% stop')
    print('  Cost: REALISTIC_5 (5bps each way + 0.1% spread)')
    print('='*65)

    # 1. Compute signals
    raw_signals = compute_momentum_1d_signals(
        earnings_by_sym=data['earnings_by_sym'],
        daily_bars_by_sym=data['daily_bars_by_sym'],
    )
    print(f'\n  Signals: {len(raw_signals)} qualifying trades across {len(set(s["entry_date"] for s in raw_signals))} entry dates')

    # 2. Simulate each trade
    trade_results = [simulate_momentum_1d_trade(s) for s in raw_signals]

    # 3. Portfolio simulation — pass SPY calendar for smooth equity curve
    spy_bars = _load_pkl_or_json('SPY_2021-01-04_2026-01-03_1Day_sip_*.json')
    port = simulate_portfolio(trade_results, calendar_bars=spy_bars)
    trades    = port['trades']
    daily_eq  = port['daily_equity']

    # 4. Build date list aligned with daily_eq for IS/OOS split
    all_dates_for_eq = sorted(set(
        [b['t'] if isinstance(b['t'], str) else str(b['t'])[:10]
         for b in (spy_bars or [])]
        + [t['entry_date'] for t in raw_signals]
    ))
    # Trim to actual equity curve length
    date_list = all_dates_for_eq[:len(daily_eq)]
    is_tr, oos_tr, is_curve, oos_curve = _split_is_oos(trades, daily_eq, date_list)

    # 5. Print scorecards
    _print_scorecard('Full Period 2021–2026', trades, daily_eq)
    _print_scorecard('IS  (2021–2023)', is_tr,  is_curve)
    _print_scorecard('OOS (2024–2026)', oos_tr, oos_curve)

    year_data = _year_breakdown(trades)
    print(f'\n  Per-year breakdown:')
    _print_year_table(year_data)

    # 6. Stop-out % analysis
    stops = sum(1 for t in trades if t.get('exit_reason') == 'stop')
    close = sum(1 for t in trades if t.get('exit_reason') == 'close')
    print(f'\n  Stopped intraday (−3%): {stops}/{len(trades)} = {stops/max(len(trades),1):.1%}')
    print(f'  Held to close:          {close}/{len(trades)} = {close/max(len(trades),1):.1%}')

    # Verdict
    oos_pf = _profit_factor(oos_tr)
    oos_sh = _sharpe(oos_curve)
    oos_n  = len(oos_tr)
    if oos_n < 30:
        verdict = 'INSUFFICIENT SAMPLE'
    elif oos_pf > 1.0 and oos_sh > 0.3:
        verdict = 'VIABLE'
    else:
        verdict = 'FAILED'

    print(f'\n  EXPERIMENT A VERDICT: {verdict}')
    print(f'  (OOS PF {oos_pf:.3f} | Sharpe {oos_sh:.3f} | n={oos_n})')

    return {
        'experiment': 'A',
        'verdict':    verdict,
        'full': {
            'pf': _profit_factor(trades), 'wr': _win_rate(trades),
            'tr': _total_return(daily_eq), 'sh': _sharpe(daily_eq),
            'dd': _max_drawdown(daily_eq), 'n': len(trades),
        },
        'is':  {'pf': _profit_factor(is_tr),  'sh': _sharpe(is_curve),  'n': len(is_tr)},
        'oos': {'pf': oos_pf, 'sh': oos_sh, 'n': oos_n,
                'wr': _win_rate(oos_tr), 'tr': _total_return(oos_curve)},
        'per_year': year_data,
        'stops_pct': stops / max(len(trades), 1),
        'n_signals': len(raw_signals),
    }


# ── EXPERIMENT B ──────────────────────────────────────────────────────────────

def run_experiment_b(data: dict) -> dict:
    print('\n' + '='*65)
    print('  EXPERIMENT B — Overreaction Fade (Short the Gap)')
    print('  SUE ≥ 15%, reaction ≥ +4%, vol ≥ 2×, NOT within 5% of ATH')
    print('  Short at day-1 open  |  TP: 50% gap fill  |  Stop: +3%')
    print('  Max hold: 3 days  |  Cost: 20.5bps entry + 5.1bps exit')
    print('='*65)

    # 1. Compute signals
    raw_signals = compute_overreaction_fade_signals(
        earnings_by_sym=data['earnings_by_sym'],
        daily_bars_by_sym=data['daily_bars_by_sym'],
    )
    print(f'\n  Signals: {len(raw_signals)} qualifying trades across {len(set(s["entry_date"] for s in raw_signals))} entry dates')

    # 2. Simulate each trade
    trade_results = [simulate_overreaction_trade(s) for s in raw_signals]

    # Inject hold_bars reference for portfolio simulation (to determine exit dates)
    for sig, res in zip(raw_signals, trade_results):
        res['hold_bars'] = sig.get('hold_bars', [])

    # 3. Portfolio simulation
    spy_bars = _load_pkl_or_json('SPY_2021-01-04_2026-01-03_1Day_sip_*.json')
    port = simulate_portfolio(trade_results, calendar_bars=spy_bars)
    trades   = port['trades']
    daily_eq = port['daily_equity']

    # 4. IS/OOS split
    all_dates_for_eq = sorted(set(
        [b['t'] if isinstance(b['t'], str) else str(b['t'])[:10]
         for b in (spy_bars or [])]
        + [t['entry_date'] for t in raw_signals]
    ))
    date_list = all_dates_for_eq[:len(daily_eq)]
    is_tr, oos_tr, is_curve, oos_curve = _split_is_oos(trades, daily_eq, date_list)

    # 5. Print scorecards
    _print_scorecard('Full Period 2021–2026', trades, daily_eq)
    _print_scorecard('IS  (2021–2023)', is_tr,  is_curve)
    _print_scorecard('OOS (2024–2026)', oos_tr, oos_curve)

    year_data = _year_breakdown(trades)
    print(f'\n  Per-year breakdown:')
    _print_year_table(year_data)

    # Exit reason analysis
    exits = _exit_breakdown(trades)
    n = len(trades)
    print(f'\n  Exit reason breakdown (all trades):')
    for reason, count in sorted(exits.items(), key=lambda x: -x[1]):
        print(f'    {reason:<20}: {count:>4} ({count/max(n,1):.1%})')

    # Verdict
    oos_pf = _profit_factor(oos_tr)
    oos_sh = _sharpe(oos_curve)
    oos_n  = len(oos_tr)
    if oos_n < 30:
        verdict = 'INSUFFICIENT SAMPLE'
    elif oos_pf > 1.0 and oos_sh > 0.3:
        verdict = 'VIABLE'
    else:
        verdict = 'FAILED'

    print(f'\n  EXPERIMENT B VERDICT: {verdict}')
    print(f'  (OOS PF {oos_pf:.3f} | Sharpe {oos_sh:.3f} | n={oos_n})')

    return {
        'experiment': 'B',
        'verdict':    verdict,
        'full': {
            'pf': _profit_factor(trades), 'wr': _win_rate(trades),
            'tr': _total_return(daily_eq), 'sh': _sharpe(daily_eq),
            'dd': _max_drawdown(daily_eq), 'n': len(trades),
        },
        'is':  {'pf': _profit_factor(is_tr),  'sh': _sharpe(is_curve),  'n': len(is_tr)},
        'oos': {'pf': oos_pf, 'sh': oos_sh, 'n': oos_n,
                'wr': _win_rate(oos_tr), 'tr': _total_return(oos_curve)},
        'per_year': year_data,
        'exit_breakdown': exits,
        'n_signals': len(raw_signals),
    }


# ── EXPERIMENT C (optional) ───────────────────────────────────────────────────

def run_experiment_c(data: dict, res_a: dict, res_b: dict) -> dict | None:
    if res_a['verdict'] != 'VIABLE' or res_b['verdict'] != 'VIABLE':
        print('\n  Experiment C skipped (A or B did not pass)')
        return None

    print('\n' + '='*65)
    print('  EXPERIMENT C — Combined Portfolio (A + B, conflicting signals cancel)')
    print('='*65)

    # Signals for both
    sigs_a = compute_momentum_1d_signals(
        earnings_by_sym=data['earnings_by_sym'],
        daily_bars_by_sym=data['daily_bars_by_sym'],
    )
    sigs_b = compute_overreaction_fade_signals(
        earnings_by_sym=data['earnings_by_sym'],
        daily_bars_by_sym=data['daily_bars_by_sym'],
    )

    # Cancel overlapping signals (same sym, same entry_date)
    b_keys = {(s['sym'], s['entry_date']) for s in sigs_b}
    a_clean = [s for s in sigs_a if (s['sym'], s['entry_date']) not in b_keys]
    a_keys  = {(s['sym'], s['entry_date']) for s in sigs_a}
    b_clean = [s for s in sigs_b if (s['sym'], s['entry_date']) not in a_keys]

    cancelled = len(sigs_a) + len(sigs_b) - len(a_clean) - len(b_clean)
    print(f'  Signals: A={len(sigs_a)}, B={len(sigs_b)}, cancelled={cancelled}')
    print(f'  A after cancel: {len(a_clean)}  B after cancel: {len(b_clean)}')

    res_a_clean = [simulate_momentum_1d_trade(s) for s in a_clean]
    res_b_clean = [simulate_overreaction_trade(s) for s in b_clean]
    for sig, res in zip(b_clean, res_b_clean):
        res['hold_bars'] = sig.get('hold_bars', [])

    combined = res_a_clean + res_b_clean
    port = simulate_portfolio(combined)
    trades   = port['trades']
    daily_eq = port['daily_equity']

    pf = _profit_factor(trades)
    sh = _sharpe(daily_eq)
    dd = _max_drawdown(daily_eq)
    tr = _total_return(daily_eq)

    print(f'  Combined: {len(trades)} trades | PF {pf:.3f} | Sharpe {sh:.3f} | Return {tr:+.2%} | MaxDD {dd:.2%}')

    verdict = 'VIABLE' if pf > 1.0 and sh > 0.3 else 'FAILED'
    print(f'  EXPERIMENT C VERDICT: {verdict}')
    return {'verdict': verdict, 'pf': pf, 'sh': sh, 'dd': dd, 'tr': tr}


# ── Final Verdict ─────────────────────────────────────────────────────────────

def print_final_verdict(res_a: dict, res_b: dict, res_c: dict | None):
    v_a = res_a['verdict']
    v_b = res_b['verdict']

    print('\n' + '='*65)
    print('  FINAL SUMMARY')
    print('='*65)
    print(f'\n  EXPERIMENT A (1-Day Momentum):')
    print(f'    OOS PF: {res_a["oos"]["pf"]:.3f}  |  Sharpe: {res_a["oos"]["sh"]:.3f}  '
          f'|  Trades: {res_a["oos"]["n"]}  |  Verdict: {v_a}')
    print(f'\n  EXPERIMENT B (Overreaction Fade):')
    print(f'    OOS PF: {res_b["oos"]["pf"]:.3f}  |  Sharpe: {res_b["oos"]["sh"]:.3f}  '
          f'|  Trades: {res_b["oos"]["n"]}  |  Verdict: {v_b}')
    if res_c:
        print(f'\n  EXPERIMENT C (Combined): {res_c["verdict"]} '
              f'(PF {res_c["pf"]:.3f}, Sharpe {res_c["sh"]:.3f})')

    print(f'\n{"─"*65}')

    a_viable = v_a == 'VIABLE'
    b_viable = v_b == 'VIABLE'
    c_viable = res_c is not None and res_c.get('verdict') == 'VIABLE'

    if a_viable and b_viable and c_viable:
        rec = 'C'
        print('  OVERALL RECOMMENDATION: C')
        print('  Both pass — run combined portfolio. Proceed to Track 2.')
    elif a_viable and not b_viable:
        rec = 'A'
        print('  OVERALL RECOMMENDATION: A')
        print('  Experiment A passes — 1-Day Momentum is the next strategy.')
        print('  Proceed to Track 2 safety infrastructure with this as live strategy.')
    elif b_viable and not a_viable:
        rec = 'B'
        print('  OVERALL RECOMMENDATION: B')
        print('  Experiment B passes — Overreaction Fade is the next strategy.')
        print('  Note: requires short-selling infrastructure review before live deployment.')
    else:
        rec = 'D'
        print('  OVERALL RECOMMENDATION: D')
        print('  Neither passes with sufficient sample — pivoting away from earnings universe.')
        print()
        print('  NEXT STRATEGY TO TEST: Sector ETF Momentum (SPY/QQQ/IWM Rotation)')
        print('  ─────────────────────────────────────────────────────────────────')
        print('  Why first: highest signal frequency of any systematic approach')
        print('  (monthly rebalance = 12 decisions/year vs 20-30 trades/year earnings).')
        print('  Strong post-2015 evidence. Works with daily bars already cached.')
        print('  No earnings data dependency. PDT-friendly (few trades, not day-trading).')
        print()
        print('  Variant to test first: DUAL-MOMENTUM (Antonacci)')
        print('    - Universe: SPY, QQQ, IWM, TLT, GLD, cash')
        print('    - Monthly signal: 12-month trailing return of each asset')
        print('    - Absolute momentum: if SPY 12m < risk-free → go to TLT or cash')
        print('    - Relative momentum: rank assets by 12m return, hold top 1-2')
        print('    - Why first? 2000-2026 live track record. Simple. 1 trade/month.')
        print('    - Backtest feasibility: needs only monthly close prices (already')
        print('      approximable from SPY daily cache). Can be coded in <50 lines.')

    print('─'*65)
    return rec


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--exp', choices=['A','B'], help='Run only one experiment')
    args = ap.parse_args()

    print('\n' + '='*65)
    print('  PIVOT BACKTEST SESSION — Experiments A & B')
    print('='*65)

    print('\nLoading shared data...')
    data = load_shared_data()

    results = {}
    res_a = res_b = res_c = None

    if args.exp is None or args.exp == 'A':
        res_a = run_experiment_a(data)
        results['A'] = res_a

    if args.exp is None or args.exp == 'B':
        res_b = run_experiment_b(data)
        results['B'] = res_b

    if res_a and res_b:
        res_c = run_experiment_c(data, res_a, res_b)
        if res_c:
            results['C'] = res_c
        rec = print_final_verdict(res_a, res_b, res_c)
        results['recommendation'] = rec

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = RESULTS_DIR / f'pivot_experiments_{ts}.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f'\nResults saved: {out}')
