#!/usr/bin/env python3
"""
Full 2021-2026 ORB backtest — run this locally.
Uses the pre-pickled bar cache (backtest/cache/*.pkl).
If pkl files are missing, run:  python scripts/pickle_cache.py

Usage:
    cd "Trading Bot"
    python run_backtest_full.py
"""
import sys, os, json, pickle, glob, time
from pathlib import Path
from collections import defaultdict

# Load credentials from .env if present
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent))
from backtest.engine import BacktestEngine
from backtest.data import load_bars, load_spy
from backtest.costs import REALISTIC_5, FRICTIONLESS
from backtest.metrics import scorecard, print_scorecard, sharpe
from backtest.evaluate import _compute_rvol_map
from backtest.regime import build_regime_map, _compute_adx, _vixy_percentile_classify
from backtest.strategies.orb import ORBStrategy

FEED = 'sip'
START = '2021-01-04'
END   = '2026-01-03'
UNIVERSE = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'META', 'AMZN', 'GOOGL', 'AMD', 'NFLX', 'SPY']
CACHE = Path(__file__).parent / 'backtest' / 'cache'

def bar_date(t):
    return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')

def _fast_rvol(all_bars, lookback=20):
    """Compute RVOL from loaded bars using fast string-based UTC parsing."""
    from collections import defaultdict
    daily_vol = defaultdict(int)
    for b in all_bars:
        t = b['t']; h = int(t[11:13]); m = int(t[14:16])
        # 9:30–10:00 ET ≈ 13:30–14:30 UTC (covers both EST and EDT)
        if (h == 13 and m >= 30) or (h == 14 and m < 30):
            daily_vol[t[:10]] += b['v']
    sdays = sorted(daily_vol)
    rvol = {}
    for i, d in enumerate(sdays):
        prior = [daily_vol[dd] for dd in sdays[max(0, i-lookback):i]]
        avg = sum(prior) / len(prior) if prior else 0
        rvol[d] = daily_vol[d] / avg if avg > 0 else 0.0
    return rvol

def _load_pkl_or_json(sym, resolution='1Min'):
    """Load from pkl if available, else json, else fetch from API."""
    pattern = f'{sym}_{START}_{END}_{resolution}_{FEED}_*.pkl'
    pkls = list(CACHE.glob(pattern))
    if pkls:
        return pickle.load(open(pkls[0], 'rb'))
    pattern = f'{sym}_{START}_{END}_{resolution}_{FEED}_*.json'
    jsons = list(CACHE.glob(pattern))
    if jsons:
        import json as _json
        return _json.load(open(jsons[0]))
    print(f'  {sym}: cache miss — fetching from API (this may take a while)...')
    return load_bars(sym, START, END, resolution=resolution, feed=FEED)

def main():
    t0 = time.time()
    print(f"\n{'='*65}")
    print(f"  ORB BACKTEST — {START} → {END}  |  feed={FEED.upper()}")
    print(f"  All 3 fixes applied: RVOL, avg_vol fallback, VIX regime gate")
    print(f"{'='*65}\n")

    # Load data
    print(f"📥 Loading SPY daily...")
    spy_daily = _load_pkl_or_json('SPY', '1Day')
    print(f"   {len(spy_daily)} days  ({time.time()-t0:.1f}s)")

    print(f"📥 Loading minute bars for {len(UNIVERSE)} symbols...")
    bars_by_symbol = {}
    rvol_by_sym = {}
    for sym in UNIVERSE:
        b = _load_pkl_or_json(sym)
        bars_by_symbol[sym] = b
        rvol_by_sym[sym] = _fast_rvol(b)
        above = sum(1 for v in rvol_by_sym[sym].values() if v >= 1.5)
        print(f"   {sym}: {len(b):,} bars, RVOL≥1.5 on {above}/1256 days  ({time.time()-t0:.1f}s)")

    # Build regime map
    print("\n📊 Building VIX regime map...")
    vixy_bars = _load_pkl_or_json('VIXY', '1Day')
    vixy_map = {b['t'][:10]: b['c'] for b in vixy_bars}
    vix_class = _vixy_percentile_classify(vixy_map)
    adx_map = _compute_adx(spy_daily)
    regime_map = {
        d: {'vix_regime': vix_class.get(d, 'unknown'), 'adx': adx_map.get(d, 0)}
        for d in set(vixy_map) | set(adx_map)
    }
    from collections import Counter
    vix_dist = Counter(v['vix_regime'] for v in regime_map.values())
    print(f"   VIX distribution: {dict(vix_dist)}")
    print(f"   High-VIX days (long entries blocked): {vix_dist.get('high',0)}")

    # Build context
    all_dates = sorted(set(bar_date(b['t']) for bars in bars_by_symbol.values() for b in bars))
    syms = list(bars_by_symbol.keys())
    ctx_by_date = {}
    for d in all_dates:
        ctx_by_date[d] = {
            'candidates': syms,
            'rel_volume': {sym: rvol_by_sym[sym].get(d, 0.0) for sym in syms},
            'regime': regime_map.get(d, {}),
        }

    days_any = sum(1 for c in ctx_by_date.values() if any(v >= 1.5 for v in c['rel_volume'].values()))
    days_all_fail = sum(1 for c in ctx_by_date.values() if all(v < 1.5 for v in c['rel_volume'].values()))
    print(f"   Days any-symbol RVOL≥1.5: {days_any}  All-fail (fallback): {days_all_fail}  Total: {len(all_dates)}")

    spy_s = sharpe([b['c'] / spy_daily[0]['c'] for b in spy_daily])
    print(f"\n📊 SPY benchmark (full window): Sharpe={spy_s:.2f}")

    # Run both cost models
    print(f"\n⏱  Total data prep: {time.time()-t0:.1f}s")
    for label, cost_model in [('FRICTIONLESS', FRICTIONLESS), ('REALISTIC 5bps', REALISTIC_5)]:
        print(f"\n🔄 Running {label}...")
        t1 = time.time()
        eng = BacktestEngine(ORBStrategy(), cost_model=cost_model, starting_equity=100_000)
        res = eng.run(bars_by_symbol, ctx_by_date=ctx_by_date)
        curve = res['daily_equity'] or [100_000]
        sc = scorecard(res['trades'], curve, len(all_dates), label=label)
        print_scorecard({**sc, 'label': f'Full {START[:4]}–{END[:4]} — {label}'})
        print(f"   ({time.time()-t1:.1f}s)")

    print(f"\n{'='*65}")
    print(f"  Total runtime: {time.time()-t0:.1f}s")
    print(f"{'='*65}\n")

if __name__ == '__main__':
    main()
