"""
Full analysis suite for the ORB strategy.

Runs:
  1. Standard evaluate.py gate (OOS vs SPY) — per asset class × OR timeframe
  2. Walk-forward optimization (rolling 12m IS / 2m OOS)
  3. Regime filter (VIX + ADX)
  4. Monte Carlo (10,000 shuffles)
  5. Slippage sensitivity (0–20 bps)
  6. Random forest feature importance

Usage:
    python -m backtest.analysis orb 2021-01-04 2026-01-03
    python -m backtest.analysis orb 2021-01-04 2026-01-03 --quick   # skip walk-forward
"""
from __future__ import annotations
import sys
import json
from datetime import datetime
from pathlib import Path

from .data import load_bars, load_spy, load_crypto_bars, detect_feed
from .engine import BacktestEngine
from .costs import FRICTIONLESS, REALISTIC_5, REALISTIC_10
from .metrics import scorecard, print_scorecard, total_return, sharpe as sharpe_fn, max_drawdown
from .evaluate import _spy_benchmark, _check_pass, RESULTS_DIR
from .walk_forward import walk_forward, print_walk_forward_summary
from .regime import build_regime_map, print_regime_table
from .monte_carlo import monte_carlo, print_mc_summary
from .sensitivity import slippage_sensitivity, print_sensitivity_table, SLIPPAGE_LEVELS
from .features import extract_features, train_importance, print_importance_table
from .events import build_event_map, print_event_table

RESULTS_DIR.mkdir(exist_ok=True)


def _sweep_params(param_grid: dict) -> list[dict]:
    import itertools
    keys = list(param_grid.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*param_grid.values())]

# ── Universe definitions ─────────────────────────────────────────────────────

UNIVERSES = {
    'large_cap': ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'META', 'AMZN', 'GOOGL', 'AMD', 'NFLX'],
    'small_cap': ['SIRI', 'AMC', 'SPCE', 'MVIS', 'CLOV', 'WKHS', 'GOEV', 'NKLA'],
    'etf':       ['QQQ', 'SPY', 'IWM', 'XLK', 'ARKK', 'SOXL', 'GLD', 'TLT'],
    'crypto':    ['BTC/USD', 'ETH/USD'],
}

OR_WINDOWS = [1, 5, 15]   # minutes — each tested separately

# ── Helper: load all bars for a universe ─────────────────────────────────────

def _load_universe(universe_name: str, symbols: list[str], start: str, end: str, feed: str) -> dict:
    bars = {}
    for sym in symbols:
        try:
            if universe_name == 'crypto':
                b = load_crypto_bars(sym, start, end, resolution='1Min')
            else:
                b = load_bars(sym, start, end, resolution='1Min', feed=feed)
            if b:
                bars[sym] = b
                print(f'    {sym}: {len(b):,} bars')
            else:
                print(f'    {sym}: 0 bars (skipped)')
        except Exception as e:
            print(f'    {sym}: FAILED ({e})')
    return bars


def _build_ctx(bars_dict: dict) -> dict:
    def bar_date(b) -> str:
        t = b['t']
        return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
    syms = list(bars_dict.keys())
    dates = set(bar_date(b) for bars in bars_dict.values() for b in bars)
    return {d: {'candidates': syms} for d in dates}


def _filter_bars(bars_dict: dict, date_set: set) -> dict:
    def bar_date(b) -> str:
        t = b['t']
        return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
    return {sym: [b for b in bars if bar_date(b) in date_set] for sym, bars in bars_dict.items()}


def _bar_date(b) -> str:
    t = b['t']
    return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')


# ── Grid cell runner ──────────────────────────────────────────────────────────

def run_grid_cell(
    universe_name: str,
    bars_by_symbol: dict,
    oos_bars: dict,
    oos_ctx: dict,
    oos_trading_days: int,
    spy_metrics: dict,
    strategy_class,
    best_params: dict,
    or_window: int,
    starting_equity: float = 100_000,
) -> dict:
    """Run one (universe, OR window) cell and return scorecard."""
    from .strategies.orb import ORBStrategy

    params = dict(best_params)
    params['or_minutes'] = or_window

    strat = strategy_class()
    strat.set_params(params)
    eng = BacktestEngine(strat, cost_model=REALISTIC_5, starting_equity=starting_equity)
    res = eng.run(oos_bars, ctx_by_date=oos_ctx)
    curve = res['daily_equity'] if res['daily_equity'] else res['equity_curve']
    sc = scorecard(res['trades'], curve, oos_trading_days,
                   label=f'{universe_name} OR={or_window}m')
    passed, failures = _check_pass(sc, spy_metrics)
    sc['verdict'] = 'PASS' if passed else 'FAIL'
    sc['failures'] = failures
    sc['or_window'] = or_window
    sc['universe'] = universe_name
    sc['trades_raw'] = res['trades']
    sc['equity_curve'] = curve
    return sc


# ── Comparison table ─────────────────────────────────────────────────────────

def _print_grid_table(grid_results: dict[tuple, dict], spy_metrics: dict) -> None:
    """
    grid_results keyed by (universe_name, or_window).
    """
    print(f'\n{"═"*100}')
    print(f'  GRID RESULTS: Return / Sharpe / MaxDD / PF / Trades / Verdict  (OOS realistic 5bps vs SPY)')
    print(f'  SPY benchmark: return={spy_metrics["total_return"]:+.1%}  sharpe={spy_metrics["sharpe"]:.2f}  maxDD={spy_metrics["max_drawdown"]:.1%}')
    print(f'{"─"*100}')
    header = f'  {"Universe":<12} {"OR":>5}  {"Return":>8} {"Sharpe":>7} {"MaxDD":>7} {"PF":>6} {"WR":>6} {"Trades":>7}  {"Verdict"}'
    print(header)
    print(f'{"─"*100}')

    for universe in UNIVERSES:
        for or_w in OR_WINDOWS:
            sc = grid_results.get((universe, or_w))
            if sc is None:
                continue
            verdict = sc.get('verdict', '?')
            icon = '✅' if verdict == 'PASS' else '❌'
            print(f'  {universe:<12} {or_w:>3}m  '
                  f'{sc["total_return"]:>+7.1%} '
                  f'{sc["sharpe"]:>7.2f} '
                  f'{sc["max_drawdown"]:>6.1%} '
                  f'{sc["profit_factor"]:>6.2f} '
                  f'{sc["win_rate"]:>5.1%} '
                  f'{sc["trade_count"]:>7}  '
                  f'{icon} {verdict}')

    print(f'{"═"*100}')


# ── Main entry point ──────────────────────────────────────────────────────────

def run_full_analysis(
    strategy_name: str,
    start: str,
    end: str,
    is_split: float = 0.60,        # default: 60/40 → ~3yr IS / ~2yr OOS for 5yr window
    oos_start: str | None = None,  # explicit OOS boundary, overrides is_split
    starting_equity: float = 100_000,
    quick: bool = False,
) -> dict:
    from .strategies.orb import ORBStrategy
    strategy_map = {'orb': ORBStrategy}
    StrategyClass = strategy_map.get(strategy_name.lower())
    if StrategyClass is None:
        raise ValueError(f'Unknown strategy: {strategy_name}')

    feed = detect_feed()
    print(f'\n🔍 Feed: {feed.upper()}')
    if feed == 'iex':
        print('⚠️  IEX feed — results INDICATIVE ONLY')

    # ── Shared: SPY benchmark & regime data ──────────────────────────────────
    print(f'\n📥 Loading SPY + regime data...')
    spy_daily = load_spy(start, end, feed=feed)
    regime_map = build_regime_map(start, end, feed=feed)
    print(f'   Regime map: {len(regime_map)} trading days')
    # Event map built after bar data is loaded (needs bars for gap detection)

    # ── Per-universe data load ────────────────────────────────────────────────
    all_bars: dict[str, dict] = {}   # universe_name → bars_by_symbol
    for uname, symbols in UNIVERSES.items():
        print(f'\n📥 Loading {uname} ({len(symbols)} symbols)...')
        bars = _load_universe(uname, symbols, start, end, feed)
        all_bars[uname] = bars

    # ── Build event map (earnings + macro) using large_cap bars ─────────────
    print(f'\n📥 Building event map (earnings gap detection + macro calendar)...')
    ref_bars_for_events = all_bars.get('large_cap', {})
    event_map = build_event_map(ref_bars_for_events, start, end, use_news=True)
    earnings_days = sum(1 for v in event_map.values() if v.get('is_earnings'))
    macro_days    = sum(1 for v in event_map.values() if v.get('is_macro'))
    print(f'   Earnings days: {earnings_days}  |  Macro days: {macro_days}')

    # ── Shared IS/OOS split (use large_cap as reference for dates) ───────────
    ref_bars = all_bars.get('large_cap', {})
    all_dates = sorted(set(
        _bar_date(b) for bars in ref_bars.values() for b in bars
    ))
    if not all_dates:
        raise RuntimeError('No bar data loaded for large_cap universe')

    if oos_start:
        is_dates  = set(d for d in all_dates if d < oos_start)
        oos_dates = set(d for d in all_dates if d >= oos_start)
        split_method = f'explicit boundary (OOS from {oos_start})'
    else:
        split_idx = int(len(all_dates) * is_split)
        is_dates  = set(all_dates[:split_idx])
        oos_dates = set(all_dates[split_idx:])
        split_method = f'{is_split:.0%}/{1-is_split:.0%} IS/OOS'

    if not is_dates or not oos_dates:
        raise RuntimeError('Split produced empty IS or OOS set. Check dates.')

    oos_spy   = [b for b in spy_daily if _bar_date(b) in oos_dates]
    spy_metrics = _spy_benchmark(oos_spy)

    print(f'\n📅 Split: {split_method}')
    print(f'📅 IS:    {min(is_dates)} → {max(is_dates)} ({len(is_dates)} trading days)')
    print(f'📅 OOS:   {min(oos_dates)} → {max(oos_dates)} ({len(oos_dates)} trading days)')
    print(f'📊 SPY OOS: return={spy_metrics["total_return"]:+.1%}  '
          f'sharpe={spy_metrics["sharpe"]:.2f}  maxDD={spy_metrics["max_drawdown"]:.1%}')

    # ── IS param sweep on large_cap universe ─────────────────────────────────
    ORB_PARAM_GRID = {
        'or_minutes': [1, 5, 15],
        'n_vwap_bars': [1, 2, 3],
        'atr_mult': [0.5, 0.75, 1.0],
    }

    print(f'\n🔧 IS param sweep ({len(list(_sweep_params(ORB_PARAM_GRID)))} combos on large_cap)...')
    is_ref_bars = _filter_bars(ref_bars, is_dates)
    is_ref_ctx  = _build_ctx(is_ref_bars)
    best_params = StrategyClass().params()
    best_sharpe = -999.0

    for params in _sweep_params(ORB_PARAM_GRID):
        strat = StrategyClass()
        strat.set_params(params)
        eng = BacktestEngine(strat, cost_model=REALISTIC_5, starting_equity=starting_equity)
        res = eng.run(is_ref_bars, ctx_by_date=is_ref_ctx)
        curve = res['daily_equity'] if res['daily_equity'] else res['equity_curve']
        s = sharpe_fn(curve)
        if s > best_sharpe:
            best_sharpe = s
            best_params = dict(params)

    print(f'   Best IS params: {best_params}  (Sharpe={best_sharpe:.2f})')
    print('   ⚠️  In-sample result is OVERFIT by design — OOS is what counts.')

    # ── Grid: all universes × all OR windows ─────────────────────────────────
    print(f'\n{"━"*80}')
    print(f'  RUNNING GRID: {len(UNIVERSES)} universes × {len(OR_WINDOWS)} OR windows')
    print(f'{"━"*80}')

    grid_results: dict[tuple, dict] = {}
    all_oos_trades: list[dict] = []   # large_cap + 5min OR — used for deep analyses

    for uname, bars in all_bars.items():
        oos_bars = _filter_bars(bars, oos_dates)
        oos_ctx  = _build_ctx(oos_bars)
        print(f'\n  [{uname}]')
        for or_w in OR_WINDOWS:
            sc = run_grid_cell(
                universe_name=uname,
                bars_by_symbol=bars,
                oos_bars=oos_bars,
                oos_ctx=oos_ctx,
                oos_trading_days=len(oos_dates),
                spy_metrics=spy_metrics,
                strategy_class=StrategyClass,
                best_params=best_params,
                or_window=or_w,
                starting_equity=starting_equity,
            )
            grid_results[(uname, or_w)] = sc
            verdict_icon = '✅' if sc['verdict'] == 'PASS' else '❌'
            print(f'    OR={or_w}m  return={sc["total_return"]:+.1%}  '
                  f'sharpe={sc["sharpe"]:.2f}  trades={sc["trade_count"]}  '
                  f'{verdict_icon} {sc["verdict"]}')

            # Collect primary analysis trades (large_cap + best OR window)
            if uname == 'large_cap' and or_w == best_params.get('or_minutes', 5):
                all_oos_trades = sc.get('trades_raw', [])

    _print_grid_table(grid_results, spy_metrics)

    # ── Walk-forward (large_cap, best params) ────────────────────────────────
    wf_result = None
    if not quick:
        print(f'\n{"━"*80}')
        print(f'  WALK-FORWARD OPTIMIZATION (large_cap, 12m IS / 2m OOS rolling windows)')
        print(f'{"━"*80}')
        try:
            wf_result = walk_forward(
                bars_by_symbol=ref_bars,
                spy_bars=spy_daily,
                strategy_class=StrategyClass,
                param_grid={'or_minutes': [1, 5, 15], 'n_vwap_bars': [1, 2, 3], 'atr_mult': [0.5, 0.75, 1.0]},
                starting_equity=starting_equity,
                verbose=True,
            )
            print_walk_forward_summary(wf_result)
            # Use walk-forward trades for deep analysis if more complete
            if len(wf_result['oos_trades']) > len(all_oos_trades):
                all_oos_trades = wf_result['oos_trades']
        except Exception as e:
            print(f'  Walk-forward failed: {e}')

    # ── Regime analysis ───────────────────────────────────────────────────────
    if all_oos_trades:
        print(f'\n{"━"*80}')
        print(f'  REGIME ANALYSIS  ({len(all_oos_trades)} OOS trades)')
        print(f'{"━"*80}')
        regime_sc = print_regime_table(all_oos_trades, regime_map)
    else:
        regime_sc = {}

    # ── Event-day analysis ────────────────────────────────────────────────────
    event_sc: dict = {}
    if all_oos_trades:
        print(f'\n{"━"*80}')
        print(f'  EVENT-DAY ANALYSIS  ({len(all_oos_trades)} OOS trades)')
        print(f'{"━"*80}')
        event_sc = print_event_table(all_oos_trades, event_map)

    # ── Monte Carlo ───────────────────────────────────────────────────────────
    mc_result = None
    if all_oos_trades:
        print(f'\n{"━"*80}')
        print(f'  MONTE CARLO')
        print(f'{"━"*80}')
        mc_result = monte_carlo(all_oos_trades, starting_equity=starting_equity)
        print_mc_summary(mc_result, spy_return=spy_metrics['total_return'])

    # ── Slippage sensitivity ──────────────────────────────────────────────────
    print(f'\n{"━"*80}')
    print(f'  SLIPPAGE SENSITIVITY  (large_cap, best params)')
    print(f'{"━"*80}')
    oos_ref_bars = _filter_bars(ref_bars, oos_dates)
    oos_ref_ctx  = _build_ctx(oos_ref_bars)
    sensitivity = slippage_sensitivity(
        bars_by_symbol=oos_ref_bars,
        strategy_class=StrategyClass,
        best_params=best_params,
        ctx_by_date=oos_ref_ctx,
        starting_equity=starting_equity,
        trading_days=len(oos_dates),
    )
    print_sensitivity_table(sensitivity, spy_return=spy_metrics['total_return'])

    # ── Feature importance (if enough trades) ────────────────────────────────
    fi_result = {}
    if len(all_oos_trades) >= 50:
        print(f'\n{"━"*80}')
        print(f'  RANDOM FOREST FEATURE IMPORTANCE')
        print(f'{"━"*80}')
        X, y, feature_names = extract_features(all_oos_trades, regime_map, ref_bars)
        if len(X) >= 50:
            fi_result = train_importance(X, y, feature_names)
            print_importance_table(fi_result)
        else:
            print(f'  Only {len(X)} trades with complete features — skipping RF')

    # ── Save combined result ──────────────────────────────────────────────────
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    grid_save = {
        str(k): {kk: vv for kk, vv in v.items() if kk not in ('trades_raw', 'equity_curve')}
        for k, v in grid_results.items()
    }
    combined = {
        'strategy': strategy_name,
        'feed': feed,
        'start': start,
        'end': end,
        'is_end': max(is_dates),
        'oos_start': min(oos_dates),
        'spy_oos': spy_metrics,
        'best_params_is': best_params,
        'grid': grid_save,
        'walk_forward': {
            'trade_count': wf_result['trade_count'] if wf_result else 0,
            'final_equity': wf_result['final_equity'] if wf_result else None,
            'n_windows': len(wf_result['windows']) if wf_result else 0,
        } if wf_result else None,
        'monte_carlo': mc_result,
        'event_analysis': event_sc,
        'feature_importance': fi_result,
        'sensitivity': {k: {kk: vv for kk, vv in v.items() if kk != 'exit_reasons'} for k, v in sensitivity.items()},
        'timestamp': datetime.now().isoformat(),
    }
    result_path = RESULTS_DIR / f'{strategy_name}_analysis_{ts}.json'
    with open(result_path, 'w') as fp:
        json.dump(combined, fp, indent=2, default=str)
    print(f'\n💾 Full analysis saved: {result_path}')

    return combined


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python -m backtest.analysis <strategy> <start> <end> [--oos-start YYYY-MM-DD] [--quick]')
        print('Example: python -m backtest.analysis orb 2021-01-04 2026-01-03 --oos-start 2024-01-02')
        sys.exit(1)

    quick_mode = '--quick' in sys.argv
    _oos_start = None
    for i, arg in enumerate(sys.argv):
        if arg == '--oos-start' and i + 1 < len(sys.argv):
            _oos_start = sys.argv[i + 1]

    run_full_analysis(
        strategy_name=sys.argv[1],
        start=sys.argv[2],
        oos_start=_oos_start,
        end=sys.argv[3],
        quick=quick_mode,
    )
