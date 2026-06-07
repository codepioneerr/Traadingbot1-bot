"""
Dual Momentum — Data Download + Full Backtest Runner
=====================================================

Step 1 (run once, requires internet):
    python3 backtest/run_dual_momentum.py --download

Step 2 (offline, uses cached data):
    python3 backtest/run_dual_momentum.py

The downloader fetches 22 years of daily prices for the 6-asset universe
from Yahoo Finance (via yfinance) and caches to backtest/cache/dual_momentum/.
Subsequent runs load from cache — no internet needed.

Universe: SPY, QQQ, IWM, TLT, GLD, SHY
Period:   2003-01-01 → 2026-01-01  (extra warm-up years for 12-month lookback)
"""
from __future__ import annotations

import sys
import json
import math
import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backtest.strategies.dual_momentum import (
    UNIVERSE, SAFE_ASSET, run_backtest
)
from backtest.run_pead import RESULTS_DIR

UNIVERSE_ALL = UNIVERSE + [SAFE_ASSET]   # ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'SHY']
DM_CACHE_DIR = ROOT / 'backtest' / 'cache' / 'dual_momentum'
DM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_START = '2003-01-01'    # 2 extra years of warm-up before backtest start
DOWNLOAD_END   = '2026-06-01'    # includes recent data through session date


# ── Data download (internet required) ────────────────────────────────────────

def download_all(refresh: bool = False) -> bool:
    """
    Download daily close prices for all 6 ETFs via yfinance.
    Returns True if all downloads succeeded.
    """
    try:
        import yfinance as yf
        import warnings
        warnings.filterwarnings('ignore')
    except ImportError:
        print('ERROR: yfinance not installed. Run: pip3 install yfinance --break-system-packages')
        return False

    print(f'\nDownloading {len(UNIVERSE_ALL)} ETFs from Yahoo Finance ({DOWNLOAD_START} → {DOWNLOAD_END})')

    ok = True
    for sym in UNIVERSE_ALL:
        cache_path = DM_CACHE_DIR / f'{sym}.json'
        if cache_path.exists() and not refresh:
            bars = json.loads(cache_path.read_text())
            print(f'  {sym:<6}: cached ({len(bars)} bars)')
            continue

        try:
            t   = yf.Ticker(sym)
            df  = t.history(start=DOWNLOAD_START, end=DOWNLOAD_END, auto_adjust=True)
            if df.empty:
                raise ValueError('empty DataFrame')

            bars = [
                {'t': str(idx.date()), 'c': round(float(row['Close']), 6)}
                for idx, row in df.iterrows()
            ]
            cache_path.write_text(json.dumps(bars, indent=2))
            print(f'  {sym:<6}: {len(bars)} bars  '
                  f'({bars[0]["t"]} → {bars[-1]["t"]})')
        except Exception as e:
            print(f'  {sym:<6}: FAILED — {e}')
            ok = False

    if ok:
        print(f'\n✅  All downloads complete. Cache: {DM_CACHE_DIR}\n')
    else:
        print(f'\n⚠️  Some downloads failed. Retry with --download --refresh\n')
    return ok


# ── Data loading from cache ───────────────────────────────────────────────────

def load_all() -> dict[str, list[dict]]:
    """Load cached daily bars for all 6 ETFs. Raises if any is missing."""
    result: dict[str, list[dict]] = {}
    missing = []
    for sym in UNIVERSE_ALL:
        path = DM_CACHE_DIR / f'{sym}.json'
        if not path.exists():
            missing.append(sym)
            continue
        result[sym] = json.loads(path.read_text())

    if missing:
        print(f'\n❌  Missing data for: {missing}')
        print(f'   Run first: python3 backtest/run_dual_momentum.py --download\n')
        sys.exit(1)

    return result


# ── SPY buy-and-hold benchmark ────────────────────────────────────────────────

def spy_benchmark(
    spy_bars: list[dict],
    start_date: str,
    end_date:   str,
    start_equity: float = 100_000.0,
) -> dict:
    """Simple SPY buy-and-hold monthly equity curve for comparison."""
    from collections import OrderedDict

    by_month: dict[str, float] = {}
    for b in spy_bars:
        t = b['t']
        m = t[:7]
        if m not in by_month or t > max(by_month.get(m+'_date', ''), t):
            by_month[m] = b['c']

    months = sorted(m for m in by_month if start_date[:7] <= m <= end_date[:7])
    if not months:
        return {}

    eq = start_equity
    curve = [eq]
    rets  = []
    prev_close = by_month.get(months[0], 0)

    for m in months[1:]:
        curr = by_month[m]
        if prev_close > 0:
            r = curr / prev_close - 1
            eq *= (1 + r)
            rets.append(r)
        curve.append(eq)
        prev_close = curr

    def _tr(c): return c[-1]/c[0] - 1 if len(c) >= 2 and c[0] > 0 else 0
    def _cagr(c, n): tr = _tr(c); return (1+tr)**(12/n)-1 if n > 0 else 0
    def _dd(c):
        pk = c[0]; dd = 0.0
        for v in c:
            if v > pk: pk = v
            if pk > 0: dd = max(dd, (pk-v)/pk)
        return dd
    def _sh(r, rf=0.02):
        if len(r)<6: return 0.0
        rfm=[((1+rf)**(1/12)-1)] * len(r)
        ex=[ri-rfm[0] for ri in r]
        mn=sum(ex)/len(ex)
        var=sum((x-mn)**2 for x in ex)/max(1,len(ex)-1)
        st=math.sqrt(var) if var > 0 else 0.0
        return (mn/st)*math.sqrt(12) if st > 0 else 0.0

    return {
        'total_return': _tr(curve),
        'cagr':         _cagr(curve, len(months)),
        'sharpe':       _sh(rets),
        'max_drawdown': _dd(curve),
        'n_months':     len(months),
        'curve':        curve,
    }


# ── Reporting helpers ─────────────────────────────────────────────────────────

def _decade_slice(active_results: list[dict], start: str, end: str) -> dict:
    """Compute metrics for a sub-period."""
    subset = [r for r in active_results if start <= r['month'] < end]
    if not subset:
        return {'n_months': 0, 'total_return': 0, 'cagr': 0,
                'sharpe': 0, 'max_drawdown': 0}

    eq = [r['equity'] for r in subset]
    rets = [r['return'] for r in subset]

    def _tr(c): return c[-1]/c[0]-1 if len(c)>=2 and c[0]>0 else 0
    def _cagr(c, n): tr=_tr(c); return (1+tr)**(12/n)-1 if n>0 else 0
    def _dd(c):
        pk=c[0]; dd=0.0
        for v in c:
            if v>pk: pk=v
            if pk>0: dd=max(dd,(pk-v)/pk)
        return dd
    def _sh(r, rf=0.02):
        if len(r)<6: return 0.0
        rfm=(1+rf)**(1/12)-1
        ex=[ri-rfm for ri in r]
        mn=sum(ex)/len(ex)
        var=sum((x-mn)**2 for x in ex)/max(1,len(ex)-1)
        st=math.sqrt(var) if var>0 else 0.0
        return (mn/st)*math.sqrt(12) if st>0 else 0.0
    def _pf(r):
        w=sum(x for x in r if x>0); l=sum(-x for x in r if x<0)
        return w/l if l>0 else (float('inf') if w>0 else 0.0)

    return {
        'n_months':     len(subset),
        'total_return': _tr(eq),
        'cagr':         _cagr(eq, len(subset)),
        'sharpe':       _sh(rets),
        'max_drawdown': _dd(eq),
        'profit_factor':_pf(rets),
        'win_rate':     sum(1 for r in rets if r>0)/max(len(rets),1),
    }


def print_report(result: dict, spy_bench: dict, start_eq: float):
    m   = result['metrics']
    ar  = result['active_results']
    alloc = result['allocation']
    total_months = m['n_months']

    print(f'\n{"="*65}')
    print(f'  DUAL MOMENTUM — FULL BACKTEST RESULTS (2005–2026)')
    print(f'{"="*65}\n')

    print(f'  {"Metric":<30} {"Dual Momentum":>16} {"SPY B&H":>12}')
    print(f'  {"─"*60}')
    print(f'  {"Total Return":<30} {m["total_return"]:>+15.1%} {spy_bench.get("total_return",0):>+11.1%}')
    print(f'  {"CAGR":<30} {m["cagr"]:>+15.2%} {spy_bench.get("cagr",0):>+11.2%}')
    print(f'  {"Sharpe Ratio":<30} {m["sharpe"]:>15.3f} {spy_bench.get("sharpe",0):>11.3f}')
    print(f'  {"Max Drawdown":<30} {m["max_drawdown"]:>15.1%} {spy_bench.get("max_drawdown",0):>11.1%}')
    print(f'  {"Win Rate (months)":<30} {m["win_rate"]:>15.1%}')
    print(f'  {"Rebalances":<30} {m["n_trades"]:>15}')
    print(f'  {"Months (total)":<30} {total_months:>15}')
    print(f'  {"Final Equity":<30} ${result["final_equity"]:>15,.0f}')
    print(f'  {"─"*60}')

    # Per-decade
    print(f'\n  Per-Decade Breakdown:')
    print(f'  {"Period":<14} {"Months":>7} {"CAGR":>8} {"Sharpe":>8} {"MaxDD":>8} {"PF":>7}')
    print(f'  {"─"*58}')
    for label, s, e in [
        ('2005–2010', '2005-01', '2011-01'),
        ('2011–2015', '2011-01', '2016-01'),
        ('2016–2020', '2016-01', '2021-01'),
        ('2021–2026', '2021-01', '2027-01'),
    ]:
        d = _decade_slice(ar, s, e)
        if d['n_months'] == 0:
            continue
        pf_str = f'{d["profit_factor"]:.2f}' if d['profit_factor'] < 99 else 'inf'
        print(f'  {label:<14} {d["n_months"]:>7} {d["cagr"]:>+7.1%} '
              f'{d["sharpe"]:>8.2f} {d["max_drawdown"]:>7.1%} {pf_str:>7}')
    print(f'  {"─"*58}')

    # IS / OOS split
    IS_END  = '2023-01'
    OOS_START_ = '2023-01'

    is_d  = _decade_slice(ar, '2005-01', IS_END)
    oos_d = _decade_slice(ar, OOS_START_, '2027-01')

    print(f'\n  IS / OOS Split:')
    print(f'  {"Period":<20} {"Months":>7} {"Return":>9} {"Sharpe":>8} {"MaxDD":>8} {"PF":>7}')
    print(f'  {"─"*62}')
    for lbl, d in [('IS  (2005–2022)', is_d), ('OOS (2023–2026)', oos_d)]:
        pf_str = f'{d["profit_factor"]:.2f}' if d['profit_factor'] < 99 else 'inf'
        print(f'  {lbl:<20} {d["n_months"]:>7} {d["total_return"]:>+8.1%} '
              f'{d["sharpe"]:>8.2f} {d["max_drawdown"]:>7.1%} {pf_str:>7}')
    print(f'  {"─"*62}')

    # Asset allocation
    print(f'\n  Asset Allocation (months held):')
    for sym in UNIVERSE + [SAFE_ASSET]:
        n = alloc.get(sym, 0)
        pct = n / total_months if total_months else 0
        bar_w = int(pct * 30)
        print(f'  {sym:<6}: {n:>4} months ({pct:>4.0%})  {"█"*bar_w}')
    print(f'  Absolute filter triggered: {result["abs_filter_months"]} months '
          f'({result["abs_filter_months"]/max(total_months,1):.0%} of time in SHY)')

    # Pass/Fail gate
    spy_cagr = spy_bench.get('cagr', 0)
    oos_ret  = oos_d['total_return']
    oos_sh   = oos_d['sharpe']
    dd       = m['max_drawdown']
    dm_cagr  = m['cagr']

    gate_oos_sharpe = oos_sh > 0.3
    gate_oos_return = oos_ret > 0.0
    gate_dd         = dd < 0.35
    gate_cagr       = dm_cagr >= spy_cagr * 0.8

    passed = gate_oos_sharpe and gate_oos_return and gate_dd and gate_cagr

    print(f'\n{"="*65}')
    print(f'  PASS / FAIL GATE')
    print(f'{"="*65}')
    print(f'  OOS Sharpe > 0.3          : {"✅" if gate_oos_sharpe else "❌"} ({oos_sh:.3f})')
    print(f'  OOS Total Return > 0%     : {"✅" if gate_oos_return else "❌"} ({oos_ret:+.1%})')
    print(f'  Max Drawdown < 35%        : {"✅" if gate_dd else "❌"} ({dd:.1%})')
    print(f'  CAGR ≥ SPY×0.8 ({spy_cagr*0.8:+.1%}): {"✅" if gate_cagr else "❌"} ({dm_cagr:+.2%})')

    print(f'\n  VERDICT: {"✅ PASS" if passed else "❌ FAIL"}')
    if not passed:
        fails = []
        if not gate_oos_sharpe: fails.append(f'OOS Sharpe {oos_sh:.3f} ≤ 0.3')
        if not gate_oos_return: fails.append(f'OOS return {oos_ret:+.1%} ≤ 0%')
        if not gate_dd:         fails.append(f'Max DD {dd:.1%} ≥ 35%')
        if not gate_cagr:       fails.append(f'CAGR {dm_cagr:+.2%} < SPY×0.8 ({spy_cagr*0.8:+.2%})')
        for f in fails:
            print(f'    ✗ {f}')

    print(f'{"="*65}')

    # Sanity check vs Antonacci published numbers
    print(f'\n  REPLICATION CHECK (vs Antonacci published ~10–12% CAGR, ~15–17% Max DD):')
    cagr_ok = 0.06 <= dm_cagr <= 0.18
    dd_ok   = dd < 0.30
    print(f'  CAGR {dm_cagr:+.1%}   {"✅ in range [6–18%]" if cagr_ok else "⚠️  OUT OF RANGE — check data/costs"}')
    print(f'  MaxDD {dd:.1%}  {"✅ in range [<30%]"  if dd_ok else  "⚠️  OUT OF RANGE — check 2008 crash data"}')
    if not cagr_ok or not dd_ok:
        print(f'  ⚠️  Numbers diverge from published results — review data quality before concluding FAIL.')

    return passed, oos_d, is_d


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Dual Momentum ETF backtest')
    ap.add_argument('--download', action='store_true',
                    help='Download price data from Yahoo Finance (requires internet)')
    ap.add_argument('--refresh',  action='store_true',
                    help='Re-download even if cached (use with --download)')
    ap.add_argument('--start', default='2005-01-01')
    ap.add_argument('--end',   default='2026-01-01')
    args = ap.parse_args()

    if args.download:
        ok = download_all(refresh=args.refresh)
        if not ok:
            sys.exit(1)
        print('Data ready. Now run without --download to backtest.')
        sys.exit(0)

    # Load data
    print('Loading cached ETF data...')
    daily_by_sym = load_all()
    for sym, bars in daily_by_sym.items():
        print(f'  {sym:<6}: {len(bars)} daily bars  ({bars[0]["t"]} → {bars[-1]["t"]})')

    # Run strategy backtest
    print(f'\nRunning Dual Momentum backtest {args.start} → {args.end}...')
    result = run_backtest(
        daily_by_sym=daily_by_sym,
        start_date=args.start,
        end_date=args.end,
    )

    # SPY benchmark
    spy_bench = spy_benchmark(daily_by_sym['SPY'], args.start, args.end)

    # Print full report
    passed, oos_metrics, is_metrics = print_report(result, spy_bench, 100_000)

    # Save result
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = RESULTS_DIR / f'dual_momentum_{ts}.json'
    save_data = {
        'strategy': 'dual_momentum',
        'start': args.start, 'end': args.end,
        'verdict': 'PASS' if passed else 'FAIL',
        'metrics': {k: float(v) if isinstance(v, float) else v
                    for k, v in result['metrics'].items()},
        'spy_benchmark': {k: float(v) if isinstance(v, (int,float)) else v
                          for k, v in spy_bench.items() if k != 'curve'},
        'oos': {k: float(v) if isinstance(v, (int,float)) else v
                for k, v in oos_metrics.items()},
        'is':  {k: float(v) if isinstance(v, (int,float)) else v
                for k, v in is_metrics.items()},
        'allocation': result['allocation'],
        'abs_filter_months': result['abs_filter_months'],
        'n_trades': result['metrics']['n_trades'],
        'timestamp': datetime.now().isoformat(),
    }
    out.write_text(json.dumps(save_data, indent=2))
    print(f'\nResult saved: {out}')
