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
from .data import load_bars, load_spy, load_crypto_bars, detect_feed, UNIVERSES, build_daily_scanner, SP500_INSTITUTIONAL_POOL
from .costs import FRICTIONLESS, REALISTIC_5, REALISTIC_10
from .metrics import scorecard, print_scorecard, total_return, sharpe, max_drawdown
from .regime import build_regime_map

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

def _compute_rvol_map(bars_by_symbol: dict, lookback_days: int = 20) -> dict:
    """
    Compute relative volume for each (date, symbol) from already-loaded bars.
    RVOL = first-30-min session volume today / avg of prior N days.
    Returns {date_str: {symbol: rvol_float}}.
    No extra API calls — uses the bar data already in memory.
    """
    from collections import defaultdict
    from datetime import datetime, timedelta, timezone

    # Accumulate early-session (9:30–10:00 ET) volume per symbol per day
    sym_daily_vol: dict[str, dict[str, int]] = {}
    for sym, bars in bars_by_symbol.items():
        daily: dict[str, int] = defaultdict(int)
        for b in bars:
            try:
                t_str = b['t']
                t = datetime.fromisoformat(t_str.replace('Z', '+00:00')) if isinstance(t_str, str) else t_str
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                # Approximate ET (handles DST: EDT = UTC-4, EST = UTC-5)
                m = t.month
                if 3 < m < 11 or (m == 3 and t.day >= 8) or (m == 11 and t.day < 7):
                    et = t + timedelta(hours=-4)
                else:
                    et = t + timedelta(hours=-5)
                day = et.strftime('%Y-%m-%d')
                # First 30 min of session: 9:30 to just before 10:00 ET
                if et.hour == 9 and et.minute >= 30:
                    daily[day] += b['v']
            except Exception:
                continue
        sym_daily_vol[sym] = dict(daily)

    # Build RVOL: today / rolling avg of prior lookback_days
    rvol_by_date: dict[str, dict[str, float]] = defaultdict(dict)
    for sym, daily in sym_daily_vol.items():
        sorted_dates = sorted(daily)
        for i, date_str in enumerate(sorted_dates):
            prior = [daily[d] for d in sorted_dates[max(0, i - lookback_days):i]]
            if not prior:
                rvol_by_date[date_str][sym] = 0.0
                continue
            avg = sum(prior) / len(prior)
            rvol_by_date[date_str][sym] = daily[date_str] / avg if avg > 0 else 0.0

    return dict(rvol_by_date)


def evaluate(
    strategy_name: str,
    start: str,
    end: str,
    is_split: float = 0.80,        # in-sample fraction (default: 80/20)
    oos_start: str | None = None,  # explicit OOS start date, overrides is_split
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

    # Institutionally-tradeable S&P 500 pool.
    # All confirmed S&P 500 members 2021–2026: price > $10, ADV > 5M shares,
    # tight spreads, no SPAC/meme risk. Scanner applies RVOL ≥ 2.0/2.5 + gap
    # 1–8% filter so only genuine catalyst days generate trades.
    # For a full production run, extend this list to 200+ liquid S&P 500 names.
    DEFAULT_UNIVERSE = SP500_INSTITUTIONAL_POOL
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
    if oos_start:
        # Explicit boundary: IS = everything before oos_start, OOS = oos_start onward
        is_dates  = set(d for d in all_dates if d < oos_start)
        oos_dates = set(d for d in all_dates if d >= oos_start)
        split_method = f'explicit boundary (OOS from {oos_start})'
    else:
        split_idx = int(len(all_dates) * is_split)
        is_dates  = set(all_dates[:split_idx])
        oos_dates = set(all_dates[split_idx:])
        split_method = f'{is_split:.0%} IS / {1-is_split:.0%} OOS'

    if not is_dates or not oos_dates:
        raise RuntimeError(f'Split produced empty IS or OOS. Check dates and split parameters.')

    print(f'\n📅 Split method  : {split_method}')
    print(f'📅 In-sample     : {min(is_dates)} → {max(is_dates)} ({len(is_dates)} trading days)')
    print(f'📅 Out-of-sample : {min(oos_dates)} → {max(oos_dates)} ({len(oos_dates)} trading days)')

    def _filter_bars(bars_dict, date_set):
        return {
            sym: [b for b in bars if _bar_date(b['t']) in date_set]
            for sym, bars in bars_dict.items()
        }

    def _build_ctx(bars_dict, rvol_map=None, regime_map=None, scanner=None) -> dict:
        syms = list(bars_dict.keys())
        dates = set(_bar_date(b['t']) for bars in bars_dict.values() for b in bars)
        ctx = {}
        for d in dates:
            # Scanner output is the candidates list for each day.
            # Empty list → strategy universe() gets [], returns [] → no trades.
            if scanner is not None:
                day_candidates = scanner.get(d, [])
            else:
                day_candidates = syms
            day_ctx: dict = {'candidates': day_candidates}
            if rvol_map:
                day_ctx['rel_volume'] = rvol_map.get(d, {})
            if regime_map:
                day_ctx['regime'] = regime_map.get(d, {})
            ctx[d] = day_ctx
        return ctx

    # FIX 1: Compute RVOL from already-loaded bars (no extra API calls)
    print('📊 Computing relative volume from loaded bars...')
    rvol_map = _compute_rvol_map(bars_by_symbol)

    # FIX 3: Build VIX regime map (loads VIXY daily; falls back silently if unavailable)
    print('📊 Building VIX regime map...')
    try:
        regime_map = build_regime_map(start, end, feed=feed)
        print(f'  Regime map: {len(regime_map)} dates classified')
    except Exception as e:
        print(f'  ⚠️  Regime map unavailable ({e}) — regime filter disabled')
        regime_map = {}

    # Dynamic daily scanner: RVOL ≥ 2.0 + gap ≥ 1% → top-3 "stocks in play" per day
    print('📡 Running dynamic daily scanner (RVOL ≥ 2.0, gap ≥ 1%)...')
    scanner = build_daily_scanner(bars_by_symbol, min_rvol=2.0, min_gap_pct=0.01, top_n=3, min_candidates=2)
    trade_days = sum(1 for v in scanner.values() if v)
    total_days = len(scanner)
    print(f'  {trade_days}/{total_days} days have ≥2 qualifying stocks'
          f'  ({trade_days/total_days:.0%} selectivity)')

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
        is_ctx = _build_ctx(is_bars, rvol_map, regime_map, scanner)
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

    oos_ctx = _build_ctx(oos_bars, rvol_map, regime_map, scanner)

    # Warn if the OOS window is short — Sharpe will be unreliable (< ~20 days)
    if len(oos_dates) < 20:
        print(f'  ⚠️  WARNING: OOS window is only {len(oos_dates)} trading days. '
              f'Sharpe will be 0.0 (requires ≥ 10 daily returns). '
              f'Use a longer evaluation window for reliable metrics.')

    for cost_label, cost_model in [('frictionless', FRICTIONLESS), ('realistic_5bps', REALISTIC_5), ('realistic_10bps', REALISTIC_10)]:
        strat = StrategyClass()
        strat.set_params(best_params)
        eng = BacktestEngine(strat, cost_model=cost_model, starting_equity=starting_equity)
        res = eng.run(oos_bars, ctx_by_date=oos_ctx)

        # ALWAYS use daily_equity (one point per trading day) for Sharpe/CAGR/drawdown.
        # NEVER fall back to equity_curve — it is per-bar (per minute), and passing it
        # to sharpe() overstates annualisation by sqrt(390) ≈ 19.7×, producing
        # nonsensical results like Sharpe = ±80.
        if not res['daily_equity']:
            print(f'  ⚠️  WARNING [{cost_label}]: daily_equity is empty — engine produced '
                  f'no complete trading days. Scorecard metrics will be zero.')
        curve = res['daily_equity'] if res['daily_equity'] else [starting_equity]

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
        print('Usage: python -m backtest.evaluate <strategy> <start> <end> [--oos-start YYYY-MM-DD]')
        print('Example: python -m backtest.evaluate orb 2021-01-04 2026-01-03 --oos-start 2024-01-02')
        sys.exit(1)

    # Parse optional --oos-start flag
    _oos_start = None
    for i, arg in enumerate(sys.argv):
        if arg == '--oos-start' and i + 1 < len(sys.argv):
            _oos_start = sys.argv[i + 1]

    ORB_PARAM_GRID = {
        'or_minutes': [1, 5, 15],
        'n_vwap_bars': [1, 2, 3],
        'atr_mult': [0.5, 0.75, 1.0],
    }

    evaluate(
        strategy_name=sys.argv[1],
        start=sys.argv[2],
        end=sys.argv[3],
        oos_start=_oos_start,     # explicit boundary if provided
        param_grid=ORB_PARAM_GRID,
    )
