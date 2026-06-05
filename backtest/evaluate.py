"""
§2 pass/fail gate — the referee for all strategy variants.

A strategy PASSES only if ALL of these hold on the OUT-OF-SAMPLE, REALISTIC slice:
  1. Total return > SPY buy-and-hold over the same window
  2. Sharpe > SPY buy-and-hold Sharpe
  3. Max drawdown <= 1.5× SPY max drawdown over the window
  4. Profit factor > 1.3 AND trade count >= 100

Writes a JSON result to backtest/results/<strategy>_<timestamp>.json.
Prints a full scorecard to stdout.

Usage:
    python -m backtest.evaluate orb 2021-01-01 2026-01-01
    # or from the /backtest slash command
"""
from __future__ import annotations
import sys
import json
import itertools
from datetime import datetime
from pathlib import Path

from .engine import BacktestEngine
from .data import load_bars, load_spy, detect_feed
from .costs import FRICTIONLESS, REALISTIC_5, REALISTIC_10
from .metrics import scorecard, print_scorecard, total_return, sharpe, max_drawdown

RESULTS_DIR = Path(__file__).parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

# ── Pass criteria ─────────────────────────────────────────────────────────────

PASS_CRITERIA = {
    'profit_factor_min': 1.3,
    'trade_count_min': 100,
    'max_dd_multiplier': 1.5,
}


def _spy_benchmark(spy_bars: list[dict]) -> dict:
    """Returns SPY buy-and-hold metrics over the given daily bars."""
    if not spy_bars:
        return {'total_return': 0, 'sharpe': 0, 'max_drawdown': 0}
    start_price = spy_bars[0]['c']
    equity = [start_price]
    for b in spy_bars[1:]:
        equity.append(b['c'])
    # Normalise to 1.0 start
    base = equity[0]
    norm = [e / base for e in equity]
    return {
        'total_return': total_return(norm),
        'sharpe': sharpe(norm),
        'max_drawdown': max_drawdown(norm),
    }


def _check_pass(oos_sc: dict, spy_metrics: dict) -> tuple[bool, list[str]]:
    failures = []
    # 1. Return
    if oos_sc['total_return'] <= spy_metrics['total_return']:
        failures.append(
            f"Return {oos_sc['total_return']:+.1%} ≤ SPY {spy_metrics['total_return']:+.1%}"
        )
    # 2. Sharpe
    if oos_sc['sharpe'] <= spy_metrics['sharpe']:
        failures.append(
            f"Sharpe {oos_sc['sharpe']:.2f} ≤ SPY {spy_metrics['sharpe']:.2f}"
        )
    # 3. Drawdown
    dd_limit = spy_metrics['max_drawdown'] * PASS_CRITERIA['max_dd_multiplier']
    if oos_sc['max_drawdown'] > dd_limit:
        failures.append(
            f"Max DD {oos_sc['max_drawdown']:.1%} > 1.5× SPY {spy_metrics['max_drawdown']:.1%} = {dd_limit:.1%}"
        )
    # 4. Profit factor & trade count
    if oos_sc['profit_factor'] < PASS_CRITERIA['profit_factor_min']:
        failures.append(
            f"Profit factor {oos_sc['profit_factor']:.2f} < {PASS_CRITERIA['profit_factor_min']}"
        )
    if oos_sc['trade_count'] < PASS_CRITERIA['trade_count_min']:
        failures.append(
            f"Trade count {oos_sc['trade_count']} < {PASS_CRITERIA['trade_count_min']}"
        )
    return len(failures) == 0, failures


# ── Parameter sweep ───────────────────────────────────────────────────────────

def _sweep_params(strategy_class, param_grid: dict) -> list[dict]:
    """Return list of all param combinations from a grid dict."""
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


# ── Main evaluation ───────────────────────────────────────────────────────────

def evaluate(
    strategy_name: str,
    start: str,
    end: str,
    is_split: float = 0.65,   # in-sample fraction
    starting_equity: float = 100_000,
    param_grid: dict | None = None,
) -> dict:
    """
    Run the full §2 evaluation:
      - Detect feed, load bars
      - Split IS/OOS
      - Optionally sweep params on IS, pick best
      - Run both passes (frictionless + realistic) on OOS
      - Print scorecard and PASS/FAIL
      - Save result to backtest/results/
    """
    feed = detect_feed()
    print(f'\n🔍 Feed detected: {feed.upper()}')
    if feed == 'iex':
        print('⚠️  WARNING: IEX feed — partial volume, limited history. Results are INDICATIVE ONLY.')

    # Load data
    print(f'📥 Loading SPY {start} → {end}...')
    spy_daily = load_spy(start, end, feed=feed)

    # Determine universe — for ORB, load a default candidate list or accept from caller
    from .strategies.orb import ORBStrategy
    strategy_map = {'orb': ORBStrategy}
    StrategyClass = strategy_map.get(strategy_name.lower())
    if StrategyClass is None:
        raise ValueError(f'Unknown strategy: {strategy_name}. Available: {list(strategy_map.keys())}')

    # For now, use SPY components as a proxy universe (replace with real scanner for production)
    # A real run should pass a curated list of high-vol symbols
    DEFAULT_UNIVERSE = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'META', 'AMZN', 'GOOGL', 'AMD', 'NFLX', 'SPY']
    print(f'📥 Loading minute bars for {len(DEFAULT_UNIVERSE)} symbols...')
    bars_by_symbol: dict[str, list[dict]] = {}
    for sym in DEFAULT_UNIVERSE:
        try:
            b = load_bars(sym, start, end, resolution='1Min', feed=feed)
            if b:
                bars_by_symbol[sym] = b
                print(f'  {sym}: {len(b)} bars')
        except Exception as e:
            print(f'  {sym}: FAILED ({e})')

    if not bars_by_symbol:
        raise RuntimeError('No bar data loaded. Check credentials and feed availability.')

    # Split timeline into IS / OOS
    def _bar_date(t) -> str:
        """Extract YYYY-MM-DD from a bar timestamp (string or datetime)."""
        if isinstance(t, str):
            return t[:10]
        return t.strftime('%Y-%m-%d')

    all_dates = sorted(set(
        _bar_date(b['t']) for bars in bars_by_symbol.values() for b in bars
    ))
    split_idx = int(len(all_dates) * is_split)
    is_dates = set(all_dates[:split_idx])
    oos_dates = set(all_dates[split_idx:])
    print(f'\n📅 In-sample  : {min(is_dates)} → {max(is_dates)} ({len(is_dates)} days)')
    print(f'📅 Out-of-sample: {min(oos_dates)} → {max(oos_dates)} ({len(oos_dates)} days)')

    def _filter_bars(bars_dict, date_set):
        return {
            sym: [b for b in bars if _bar_date(b['t']) in date_set]
            for sym, bars in bars_dict.items()
        }

    def _build_ctx(bars_dict) -> dict:
        syms = list(bars_dict.keys())
        dates = set(_bar_date(b['t']) for bars in bars_dict.values() for b in bars)
        return {d: {'candidates': syms} for d in dates}

    is_bars = _filter_bars(bars_by_symbol, is_dates)
    oos_bars = _filter_bars(bars_by_symbol, oos_dates)

    # SPY benchmark for OOS window
    oos_spy = [b for b in spy_daily if _bar_date(b['t']) in oos_dates]
    spy_metrics = _spy_benchmark(oos_spy)
    print(f'\n📊 SPY benchmark (OOS): return={spy_metrics["total_return"]:+.1%}  '
          f'sharpe={spy_metrics["sharpe"]:.2f}  maxDD={spy_metrics["max_drawdown"]:.1%}')

    # ── In-sample param sweep ──────────────────────────────────────────────────
    best_params = StrategyClass().params()  # defaults
    if param_grid:
        print(f'\n🔧 In-sample param sweep ({len(_sweep_params(StrategyClass, param_grid))} combos)...')
        is_ctx = _build_ctx(is_bars)
        best_sharpe = -999
        for params in _sweep_params(StrategyClass, param_grid):
            strat = StrategyClass()
            strat.set_params(params)
            eng = BacktestEngine(strat, cost_model=REALISTIC_5, starting_equity=starting_equity)
            res = eng.run(is_bars, ctx_by_date=is_ctx)
            curve = res['daily_equity'] if res['daily_equity'] else res['equity_curve']
            sc = scorecard(res['trades'], curve, len(is_dates), label='IS sweep')
            if sc['sharpe'] > best_sharpe:
                best_sharpe = sc['sharpe']
                best_params = params
        print(f'  Best IS params: {best_params}  (Sharpe={best_sharpe:.2f})')
        print('  ⚠️  In-sample result is OVERFIT by design — OOS is what counts.')

    # ── OOS evaluation — two passes ───────────────────────────────────────────
    results = {
        'strategy': strategy_name,
        'feed': feed,
        'start': start,
        'end': end,
        'is_end': max(is_dates),
        'oos_start': min(oos_dates),
        'best_params': best_params,
        'spy_oos': spy_metrics,
        'passes': {},
        'verdict': 'FAIL',
        'timestamp': datetime.now().isoformat(),
    }

    oos_ctx = _build_ctx(oos_bars)
    for cost_label, cost_model in [('frictionless', FRICTIONLESS), ('realistic_5bps', REALISTIC_5), ('realistic_10bps', REALISTIC_10)]:
        strat = StrategyClass()
        strat.set_params(best_params)
        eng = BacktestEngine(strat, cost_model=cost_model, starting_equity=starting_equity)
        res = eng.run(oos_bars, ctx_by_date=oos_ctx)
        # Use daily_equity for time-based metrics (Sharpe, CAGR, drawdown)
        # fall back to equity_curve if daily_equity is empty
        curve = res['daily_equity'] if res['daily_equity'] else res['equity_curve']
        sc = scorecard(res['trades'], curve, len(oos_dates), label=f'OOS {cost_label}')
        results['passes'][cost_label] = sc

    # Gate verdict — always on OOS realistic_5bps
    gate_sc = results['passes']['realistic_5bps']
    passed, failures = _check_pass(gate_sc, spy_metrics)
    results['verdict'] = 'PASS' if passed else 'FAIL'
    results['failures'] = failures

    # ── Print scorecards ──────────────────────────────────────────────────────
    print(f'\n{"━"*60}')
    print(f'  STRATEGY: {strategy_name.upper()}  |  FEED: {feed.upper()}')
    print(f'  Params: {best_params}')
    print(f'{"━"*60}')

    for label, sc in results['passes'].items():
        print_scorecard({**sc, 'label': f'OOS — {label}'})

    print(f'\n{"━"*60}')
    verdict_icon = '✅ PASS' if passed else '❌ FAIL'
    print(f'  VERDICT (OOS realistic 5bps vs SPY): {verdict_icon}')
    if failures:
        for f in failures:
            print(f'    ✗ {f}')
    print(f'{"━"*60}\n')

    # ── Save result ───────────────────────────────────────────────────────────
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_path = RESULTS_DIR / f'{strategy_name}_{ts}.json'
    with open(result_path, 'w') as fp:
        json.dump(results, fp, indent=2, default=str)
    print(f'💾 Result saved: {result_path}')

    return results


def latest_result(strategy_name: str) -> dict | None:
    """
    Returns the most recent backtest result for a strategy.
    Used by live routines to check PASS/FAIL before deploying.
    """
    pattern = f'{strategy_name}_*.json'
    results = sorted(RESULTS_DIR.glob(pattern), reverse=True)
    if not results:
        return None
    with open(results[0]) as f:
        return json.load(f)


def is_cleared_to_trade(strategy_name: str) -> tuple[bool, str]:
    """
    Returns (True, '') if latest backtest result is PASS.
    Returns (False, reason) otherwise.
    Used as a guard in live routines.
    """
    result = latest_result(strategy_name)
    if result is None:
        return False, f'No backtest result found for {strategy_name}. Run /backtest first.'
    if result.get('verdict') != 'PASS':
        failures = result.get('failures', [])
        return False, f'{strategy_name} backtest FAILED: {"; ".join(failures)}'
    return True, ''


# ── CLI entrypoint ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python -m backtest.evaluate <strategy> <start> <end>')
        print('Example: python -m backtest.evaluate orb 2021-01-01 2026-01-01')
        sys.exit(1)

    # Default param grid for ORB sweep
    ORB_PARAM_GRID = {
        'or_minutes': [1, 5, 15],
        'n_vwap_bars': [1, 2, 3],
        'atr_mult': [0.5, 0.75, 1.0],
    }

    evaluate(
        strategy_name=sys.argv[1],
        start=sys.argv[2],
        end=sys.argv[3],
        param_grid=ORB_PARAM_GRID,
    )
