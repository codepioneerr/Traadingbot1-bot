"""
Slippage sensitivity analysis.

Runs the same strategy + params across multiple slippage levels and plots
the degradation curve — showing the bps breakeven point where the strategy
stops being profitable.

Slippage levels tested: 0, 5, 10, 15, 20 bps per side.

Usage:
    from backtest.sensitivity import slippage_sensitivity, print_sensitivity_table
    result = slippage_sensitivity(bars_by_symbol, strategy, params, oos_dates)
    print_sensitivity_table(result, spy_return=0.12)
"""
from __future__ import annotations
from .engine import BacktestEngine
from .costs import CostModel
from .metrics import scorecard, total_return, sharpe as sharpe_fn, profit_factor


SLIPPAGE_LEVELS = [0, 5, 10, 15, 20]   # bps per side


def slippage_sensitivity(
    bars_by_symbol: dict,
    strategy_class,
    best_params: dict,
    ctx_by_date: dict | None = None,
    starting_equity: float = 100_000,
    trading_days: int = 252,
    spread_pct: float = 0.001,
) -> dict:
    """
    Run strategy across slippage levels. Returns per-level scorecards.
    """
    results: dict[str, dict] = {}

    for bps in SLIPPAGE_LEVELS:
        cost_model = CostModel(slippage_bps=float(bps), spread_pct=spread_pct)
        strat = strategy_class()
        strat.set_params(best_params)
        eng = BacktestEngine(strat, cost_model=cost_model, starting_equity=starting_equity)
        res = eng.run(bars_by_symbol, ctx_by_date=ctx_by_date)
        curve = res['daily_equity'] if res['daily_equity'] else res['equity_curve']
        sc = scorecard(res['trades'], curve, trading_days, label=f'{bps}bps')
        results[f'{bps}bps'] = sc

    return results


def print_sensitivity_table(results: dict, spy_return: float | None = None) -> None:
    print(f'\n{"═"*72}')
    print(f'  SLIPPAGE SENSITIVITY  (bps per side, spread=0.1% constant)')
    print(f'{"─"*72}')
    print(f'  {"Slippage":>10}  {"Return":>8}  {"CAGR":>7}  {"Sharpe":>7}  {"PF":>6}  {"Trades":>7}  {"Status"}')
    print(f'{"─"*72}')

    for bps in SLIPPAGE_LEVELS:
        label = f'{bps}bps'
        sc = results.get(label, {})
        ret = sc.get('total_return', 0)
        cg = sc.get('cagr', 0)
        sh = sc.get('sharpe', 0)
        pf = sc.get('profit_factor', 0)
        tc = sc.get('trade_count', 0)
        # Status: profitable vs SPY if provided, else vs 0
        if spy_return is not None:
            status = '✓ beats SPY' if ret > spy_return else ('≈ SPY' if abs(ret - spy_return) < 0.01 else '✗ below SPY')
        else:
            status = '✓ profitable' if ret > 0 else '✗ losing'
        print(f'  {label:>10}  {ret:>+7.1%}  {cg:>+6.1%}  {sh:>7.2f}  {pf:>6.2f}  {tc:>7}  {status}')

    # Find breakeven bps (first level where return drops below 0)
    breakeven = None
    for bps in SLIPPAGE_LEVELS:
        sc = results.get(f'{bps}bps', {})
        if sc.get('total_return', 0) <= 0:
            breakeven = bps
            break

    print(f'{"─"*72}')
    if breakeven is not None:
        print(f'  ⚠️  Strategy goes unprofitable at {breakeven} bps/side')
    else:
        print(f'  ✓ Strategy profitable across all tested slippage levels (0–{SLIPPAGE_LEVELS[-1]} bps)')
    print(f'{"═"*72}')
