"""
PEAD Backtest Runner
====================
Run a full IS/OOS evaluation of the PEAD strategy over the S&P 500 pool.

Data sources:
  - Minute bars: backtest/cache/<SYM>_2021-01-04_2026-01-03_1Min_sip_*.pkl
  - Earnings:    backtest/cache/earnings/<SYM>.json
  - SPY daily:   backtest/cache/SPY_2021-01-04_2026-01-03_1Day_sip_*.json
  - VIXY daily:  backtest/cache/VIXY_2021-01-04_2026-01-03_1Day_sip_*.json

Usage:
    python3 backtest/run_pead.py
    python3 backtest/run_pead.py --oos-start 2024-01-01
    python3 backtest/run_pead.py --short-cost 15   # flat bps for all trades
"""
from __future__ import annotations

import sys
import os
import json
import pickle
import argparse
import math
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backtest.costs import CostModel, REALISTIC_5
from backtest.engine import BacktestEngine
from backtest.strategies.pead import PEADStrategy, compute_pead_signals
from backtest.earnings_data import load_all_earnings
from backtest.regime import build_regime_map
from backtest.metrics import (
    total_return, sharpe, max_drawdown, profit_factor, win_rate, scorecard
)
from backtest.sp500_pool import SP500_STABLE_POOL

CACHE_DIR = ROOT / 'backtest' / 'cache'
RESULTS_DIR = ROOT / 'backtest' / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

# ── Cost models ───────────────────────────────────────────────────────────────
# REALISTIC_5 = 5bps slippage + 0.1% spread per side
# For shorts: add ~10bps locate/borrow fee.
# The engine doesn't support per-direction costs so we apply 15bps flat to
# all trades. This is conservative (penalises longs slightly more than needed)
# and is noted in the report.
COST_SHORT_PENALTY_BPS = 10.0
REALISTIC_FLAT_15 = CostModel(
    slippage_bps=15.0,   # 15bps flat to approximate 5bps long + 15bps short blended
    spread_pct=0.001,
)


# ── Data loading helpers ──────────────────────────────────────────────────────

def _load_pkl_or_json(pattern_glob: str) -> list[dict]:
    """Load first matching file — pkl or json."""
    matches = sorted(CACHE_DIR.glob(pattern_glob))
    if not matches:
        return []
    path = matches[0]
    if path.suffix == '.pkl':
        with open(path, 'rb') as f:
            return pickle.load(f)
    with open(path) as f:
        return json.load(f)


DAILY_CACHE_DIR = CACHE_DIR / 'daily'   # pre-aggregated daily JSON files


def load_minute_bars(symbol: str) -> list[dict]:
    """Load full 5-year minute bars from pkl cache (preferred) or json."""
    bars = _load_pkl_or_json(f'{symbol}_2021-01-04_2026-01-03_1Min_sip_*.pkl')
    if not bars:
        bars = _load_pkl_or_json(f'{symbol}_2021-01-04_2026-01-03_1Min_sip_*.json')
    return bars


def _bar_date(t) -> str:
    if isinstance(t, str):
        return t[:10]
    return t.strftime('%Y-%m-%d')


def aggregate_to_daily(minute_bars: list[dict]) -> list[dict]:
    """
    Collapse minute bars to OHLCV daily bars.
    Uses the exchange session (any bar on date d contributes to day d's OHLC).
    t field is set to YYYY-MM-DD (string).
    """
    by_day: dict[str, dict] = {}
    for b in minute_bars:
        d = _bar_date(b['t'])
        if d not in by_day:
            by_day[d] = {'t': d, 'o': b['o'], 'h': b['h'], 'l': b['l'],
                         'c': b['c'], 'v': b.get('v', 0)}
        else:
            rec = by_day[d]
            rec['h'] = max(rec['h'], b['h'])
            rec['l'] = min(rec['l'], b['l'])
            rec['c'] = b['c']               # last bar close
            rec['v'] += b.get('v', 0)
    return sorted(by_day.values(), key=lambda x: x['t'])


def load_daily_bars_cached(symbol: str) -> list[dict]:
    """
    Load pre-aggregated daily bars.
    Priority:
      1. backtest/cache/daily/<SYM>.json  (pre-aggregated from minute pkl)
      2. backtest/cache/<SYM>_..._1Day_sip_*.json  (native daily cache)
      3. Aggregate from minute pkl on the fly (slow, last resort)
    """
    # Priority 1: pre-aggregated daily cache (fast)
    pre = DAILY_CACHE_DIR / f'{symbol}.json'
    if pre.exists():
        with open(pre) as f:
            return json.load(f)
    # Priority 2: native Alpaca daily bar cache
    daily = _load_pkl_or_json(f'{symbol}_2021-01-04_2026-01-03_1Day_sip_*.json')
    if daily:
        return daily
    # Priority 3: aggregate from minute bars (slow)
    minute = load_minute_bars(symbol)
    if minute:
        return aggregate_to_daily(minute)
    return []


# ── Per-year P&L breakdown ────────────────────────────────────────────────────

def _year_breakdown(trades: list[dict], equity_curve: list[float]) -> dict:
    """Return {year: {pnl, trades, wins}} for each year in the trade set."""
    years: dict[str, dict] = defaultdict(lambda: {'pnl': 0.0, 'trades': 0, 'wins': 0})
    for t in trades:
        y = (t.get('entry_time') or t.get('exit_time') or '')[:4]
        if not y:
            continue
        side = t.get('side', 'long')
        entry = t['entry_price']
        exit_ = t['exit_price']
        qty   = t.get('qty', 1)
        if side == 'long':
            pnl = (exit_ - entry) * qty
        else:
            pnl = (entry - exit_) * qty
        years[y]['pnl']    += pnl
        years[y]['trades'] += 1
        if pnl > 0:
            years[y]['wins'] += 1
    return dict(years)


def _split_long_short(trades: list[dict]) -> tuple[list[dict], list[dict]]:
    longs  = [t for t in trades if t.get('side', 'long') == 'long']
    shorts = [t for t in trades if t.get('side', 'long') == 'short']
    return longs, shorts


def _safe_pf(trades: list[dict]) -> float:
    if not trades:
        return 0.0
    from backtest.metrics import profit_factor
    return profit_factor(trades)


def _safe_wr(trades: list[dict]) -> float:
    if not trades:
        return 0.0
    from backtest.metrics import win_rate
    return win_rate(trades)


def _total_pnl(trades: list[dict]) -> float:
    total = 0.0
    for t in trades:
        side  = t.get('side', 'long')
        entry = t['entry_price']
        exit_ = t['exit_price']
        qty   = t.get('qty', 1)
        total += (exit_ - entry) * qty if side == 'long' else (entry - exit_) * qty
    return total


# ── Main runner ───────────────────────────────────────────────────────────────

def run_pead(
    oos_start: str = '2024-01-01',
    starting_equity: float = 100_000.0,
    short_cost_bps: float = 15.0,
) -> dict:
    """
    Full PEAD evaluation.
    Returns dict with all metrics; also prints a scorecard.
    """
    FULL_START = '2021-01-01'
    FULL_END   = '2026-01-03'

    print(f'\n{"="*65}')
    print(f'  PEAD BASELINE BACKTEST  —  OOS from {oos_start}')
    print(f'  Cost model: REALISTIC_5 long  |  FLAT_{short_cost_bps:.0f}bps all trades')
    print(f'{"="*65}\n')

    # ── 1. Load earnings ──────────────────────────────────────────────────────
    print('Loading earnings data...')
    earnings_by_sym = load_all_earnings(SP500_STABLE_POOL)
    print(f'  {len(earnings_by_sym)} symbols with earnings cache')

    # ── 2. Load daily bars for all available symbols ──────────────────────────
    print('Loading daily bars (from pkl/json cache, aggregating where needed)...')
    daily_bars_by_sym: dict[str, list[dict]] = {}
    for sym in SP500_STABLE_POOL:
        bars = load_daily_bars_cached(sym)
        if bars:
            daily_bars_by_sym[sym] = bars

    print(f'  {len(daily_bars_by_sym)} symbols with daily bar data')

    # Pool: symbols with BOTH earnings and daily bars
    usable = set(earnings_by_sym) & set(daily_bars_by_sym)
    print(f'  {len(usable)} symbols usable for backtest\n')

    earnings_by_sym   = {s: v for s, v in earnings_by_sym.items()   if s in usable}
    daily_bars_by_sym = {s: v for s, v in daily_bars_by_sym.items() if s in usable}

    # ── 3. All trading dates ──────────────────────────────────────────────────
    all_trading_dates = sorted(set(
        b['t'] for bars in daily_bars_by_sym.values() for b in bars
        if FULL_START <= b['t'] <= FULL_END
    ))
    print(f'Trading calendar: {all_trading_dates[0]} → {all_trading_dates[-1]} '
          f'({len(all_trading_dates)} days)')

    # ── 4. Regime map (VIX) ───────────────────────────────────────────────────
    print('Building VIX regime map...')
    try:
        # Load VIXY and SPY daily from cache
        vixy_bars = _load_pkl_or_json('VIXY_2021-01-04_2026-01-03_1Day_sip_*.json')
        spy_bars  = _load_pkl_or_json('SPY_2021-01-04_2026-01-03_1Day_sip_*.json')
        from backtest.regime import _vixy_percentile_classify, _compute_adx
        vixy_map = {b['t'][:10]: b['c'] for b in vixy_bars}
        vix_regime_by_date = _vixy_percentile_classify(vixy_map) if vixy_map else {}
        adx_map = _compute_adx(spy_bars) if spy_bars else {}
        regime_map: dict[str, dict] = {}
        all_regime_dates = set(vixy_map) | set(adx_map)
        for d in all_regime_dates:
            vix_label = vix_regime_by_date.get(d, 'unknown')
            adx       = adx_map.get(d, 0.0)
            regime_map[d] = {
                'vix_regime': vix_label,
                'trend': 'trending' if adx >= 25 else 'choppy',
                'vixy': vixy_map.get(d, 0.0),
                'adx':  adx,
            }
        print(f'  {len(regime_map)} dates classified  '
              f'(high={sum(1 for v in regime_map.values() if v["vix_regime"]=="high")} '
              f'normal={sum(1 for v in regime_map.values() if v["vix_regime"]=="normal")} '
              f'low={sum(1 for v in regime_map.values() if v["vix_regime"]=="low")})')
    except Exception as e:
        print(f'  WARNING: regime map failed ({e}) — VIX filter disabled')
        regime_map = {}

    # ── 5. Compute PEAD signals (full window) ─────────────────────────────────
    print('Computing PEAD signals...')
    all_signals = compute_pead_signals(
        earnings_by_sym=earnings_by_sym,
        daily_bars_by_sym=daily_bars_by_sym,
        regime_map=regime_map,
    )
    total_signals = sum(len(v) for v in all_signals.values())
    total_longs   = sum(1 for v in all_signals.values() for _, s in v if s == 'long')
    total_shorts  = sum(1 for v in all_signals.values() for _, s in v if s == 'short')
    print(f'  {total_signals} total signals  '
          f'({total_longs} longs, {total_shorts} shorts)  '
          f'across {len(all_signals)} entry dates')

    # ── 6. IS / OOS split ─────────────────────────────────────────────────────
    is_dates  = set(d for d in all_trading_dates if d < oos_start)
    oos_dates = set(d for d in all_trading_dates if d >= oos_start)
    print(f'\nIS  : {min(is_dates)} → {max(is_dates)} ({len(is_dates)} days)')
    print(f'OOS : {min(oos_dates)} → {max(oos_dates)} ({len(oos_dates)} days)')

    def _filter_bars(bars_dict: dict, date_set: set) -> dict:
        return {
            sym: [b for b in bars if b['t'] in date_set]
            for sym, bars in bars_dict.items()
        }

    def _filter_signals(signals: dict, date_set: set) -> dict:
        return {d: v for d, v in signals.items() if d in date_set}

    is_bars      = _filter_bars(daily_bars_by_sym, is_dates)
    oos_bars     = _filter_bars(daily_bars_by_sym, oos_dates)
    is_signals   = _filter_signals(all_signals, is_dates)
    oos_signals  = _filter_signals(all_signals, oos_dates)
    is_dates_list  = sorted(is_dates)
    oos_dates_list = sorted(oos_dates)

    is_sig_count  = sum(len(v) for v in is_signals.values())
    oos_sig_count = sum(len(v) for v in oos_signals.values())
    print(f'IS  signals: {is_sig_count}   OOS signals: {oos_sig_count}')

    # ── 7. Cost model ─────────────────────────────────────────────────────────
    # Apply flat {short_cost_bps}bps to all trades (approximates 5bps long +
    # 5bps + 10bps locate for short). Conservative but simple.
    cost_model = CostModel(slippage_bps=short_cost_bps, spread_pct=0.001)

    # ── 8. Run IS (reference only, not gated) ─────────────────────────────────
    print(f'\nRunning IS engine...')
    is_strat = PEADStrategy(is_signals, is_dates_list)
    is_eng   = BacktestEngine(is_strat, cost_model=cost_model,
                               starting_equity=starting_equity)
    is_res   = is_eng.run(is_bars)
    is_curve = is_res['daily_equity'] or [starting_equity]
    is_trades = is_res['trades']
    print(f'  IS trades: {len(is_trades)}')

    # ── 9. Run OOS ────────────────────────────────────────────────────────────
    print(f'Running OOS engine...')
    oos_strat = PEADStrategy(oos_signals, oos_dates_list)
    oos_eng   = BacktestEngine(oos_strat, cost_model=cost_model,
                                starting_equity=starting_equity)
    oos_res   = oos_eng.run(oos_bars)
    oos_curve = oos_res['daily_equity'] or [starting_equity]
    oos_trades = oos_res['trades']
    print(f'  OOS trades: {len(oos_trades)}')

    # ── 10. Compute metrics ───────────────────────────────────────────────────
    def _pf(trades: list[dict]) -> float:
        from backtest.metrics import profit_factor as _pf_fn
        return _pf_fn(trades) if trades else 0.0

    def _wr(trades: list[dict]) -> float:
        from backtest.metrics import win_rate as _wr_fn
        return _wr_fn(trades) if trades else 0.0

    oos_tr  = total_return(oos_curve)
    oos_sh  = sharpe(oos_curve)
    oos_dd  = max_drawdown(oos_curve)
    oos_pf  = _pf(oos_trades)
    oos_wr  = _wr(oos_trades)

    # Long/short split
    oos_longs, oos_shorts = _split_long_short(oos_trades)
    long_pf  = _pf(oos_longs)
    short_pf = _pf(oos_shorts)
    long_wr  = _wr(oos_longs)
    short_wr = _wr(oos_shorts)

    # Per-year breakdown (on OOS trades, which may span 2024–2025)
    year_data = _year_breakdown(oos_trades, oos_curve)

    # Also compute IS metrics for reference
    is_pf = _pf(is_trades)
    is_tr = total_return(is_curve)

    # ── 11. Print scorecard ───────────────────────────────────────────────────
    print(f'\n{"━"*65}')
    print(f'  PEAD BASELINE — OOS SCORECARD  (cost: flat {short_cost_bps:.0f}bps + 0.1% spread)')
    print(f'{"━"*65}')
    print(f'  Profit Factor   : {oos_pf:.3f}')
    print(f'  Sharpe Ratio    : {oos_sh:.3f}')
    print(f'  Win Rate        : {oos_wr:.1%}')
    print(f'  Total Return    : {oos_tr:+.2%}')
    print(f'  Max Drawdown    : {oos_dd:.2%}')
    print(f'  Total Trades    : {len(oos_trades)}')
    print(f'  Total $PnL      : ${_total_pnl(oos_trades):+,.0f}')
    print(f'{"━"*65}')
    print(f'  Long-only  : {len(oos_longs):>4} trades | PF {long_pf:.3f} | WR {long_wr:.1%}')
    print(f'  Short-only : {len(oos_shorts):>4} trades | PF {short_pf:.3f} | WR {short_wr:.1%}')
    print(f'{"━"*65}')

    print(f'\n  Per-Year P&L Breakdown (OOS window):')
    print(f'  {"Year":<6} {"Trades":>7} {"Wins":>5} {"WR%":>6} {"$PnL":>12}')
    print(f'  {"─"*42}')
    for yr in sorted(year_data):
        if yr < oos_start[:4]:
            continue
        yd = year_data[yr]
        wr_y = yd['wins'] / yd['trades'] if yd['trades'] else 0
        print(f'  {yr:<6} {yd["trades"]:>7} {yd["wins"]:>5} {wr_y:>6.1%} '
              f'{yd["pnl"]:>12,.0f}')
    print(f'  {"─"*42}')

    print(f'\n  IS reference (not gated):')
    print(f'  IS Profit Factor: {is_pf:.3f}')
    print(f'  IS Total Return : {is_tr:+.2%}')
    print(f'  IS Trade count  : {len(is_trades)}')

    # ── 12. Decision gate ─────────────────────────────────────────────────────
    gate_pf     = oos_pf > 1.0
    gate_sharpe = oos_sh > 0.5
    # "No single year catastrophically negative" — check all OOS years
    worst_year_pnl = min((year_data[y]['pnl'] for y in year_data
                          if y >= oos_start[:4]), default=0)
    worst_year_ret = worst_year_pnl / starting_equity
    gate_year   = worst_year_ret >= -0.15

    passed = gate_pf and gate_sharpe and gate_year

    print(f'\n{"━"*65}')
    print(f'  DECISION GATE')
    print(f'{"━"*65}')
    print(f'  OOS PF > 1.0           : {"✅ PASS" if gate_pf else "❌ FAIL"}  '
          f'({oos_pf:.3f})')
    print(f'  OOS Sharpe > 0.5       : {"✅ PASS" if gate_sharpe else "❌ FAIL"}  '
          f'({oos_sh:.3f})')
    print(f'  No year < −15%         : {"✅ PASS" if gate_year else "❌ FAIL"}  '
          f'(worst year: {worst_year_ret:+.1%})')
    print(f'{"━"*65}')

    if passed:
        print(f'\n  ✅ PEAD PASSED — proceed to Track 2')
    else:
        fails = []
        if not gate_pf:     fails.append(f'PF={oos_pf:.3f} ≤ 1.0')
        if not gate_sharpe: fails.append(f'Sharpe={oos_sh:.3f} ≤ 0.5')
        if not gate_year:   fails.append(f'Worst year {worst_year_ret:+.1%} < −15%')
        print(f'\n  ❌ PEAD FAILED — {"; ".join(fails)}')
        print(f'     STOP: do not implement Track 2 or Track 3.')

    print(f'{"━"*65}\n')

    # ── 13. Save result ───────────────────────────────────────────────────────
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    result = {
        'strategy': 'pead',
        'oos_start': oos_start,
        'cost_bps': short_cost_bps,
        'verdict': 'PASS' if passed else 'FAIL',
        'oos': {
            'profit_factor': oos_pf,
            'sharpe':        oos_sh,
            'win_rate':      oos_wr,
            'total_return':  oos_tr,
            'max_drawdown':  oos_dd,
            'trade_count':   len(oos_trades),
            'long_pf':       long_pf, 'long_wr': long_wr, 'long_count': len(oos_longs),
            'short_pf':      short_pf,'short_wr': short_wr,'short_count':len(oos_shorts),
        },
        'is': {
            'profit_factor': is_pf,
            'total_return':  is_tr,
            'trade_count':   len(is_trades),
        },
        'per_year_oos': {y: year_data[y] for y in sorted(year_data) if y >= oos_start[:4]},
        'gate': {'pf': gate_pf, 'sharpe': gate_sharpe, 'year': gate_year},
        'timestamp': datetime.now().isoformat(),
    }

    out_path = RESULTS_DIR / f'pead_{ts}.json'
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f'Result saved: {out_path}\n')

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='PEAD baseline backtest')
    ap.add_argument('--oos-start', default='2024-01-01',
                    help='OOS window start date (YYYY-MM-DD). Default: 2024-01-01')
    ap.add_argument('--short-cost', type=float, default=15.0,
                    help='Flat bps applied to all trades (approx short locate cost). Default: 15')
    ap.add_argument('--equity', type=float, default=100_000,
                    help='Starting equity. Default: 100000')
    args = ap.parse_args()

    run_pead(
        oos_start=args.oos_start,
        starting_equity=args.equity,
        short_cost_bps=args.short_cost,
    )
