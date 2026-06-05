"""
Walk-forward optimization.

Slides a window across the full bar history:
  - 12-month IS window: optimize params (Sharpe on REALISTIC_5)
  - 2-month OOS window: validate with best params

Stitches together all OOS segments for an honest out-of-sample equity curve.

Usage:
    from backtest.walk_forward import walk_forward
    result = walk_forward(bars_by_symbol, spy_bars, StrategyClass, param_grid)
    # result['oos_trades']      — all OOS trades concatenated
    # result['oos_equity']      — daily equity curve (stitched OOS segments)
    # result['windows']         — per-window detail
"""
from __future__ import annotations
from datetime import date
from collections import defaultdict

from .engine import BacktestEngine
from .costs import REALISTIC_5
from .metrics import scorecard, sharpe as sharpe_fn

# Window sizes in trading days
IS_DAYS  = 252   # ~12 months
OOS_DAYS =  42   # ~2 months
STEP     =  42   # advance by 2 months each iteration


def _date_index(all_dates: list[str]) -> dict[str, int]:
    return {d: i for i, d in enumerate(all_dates)}


def _filter_to_dates(bars_by_symbol: dict, date_set: set) -> dict:
    def bar_date(b) -> str:
        t = b['t']
        return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
    return {
        sym: [b for b in bars if bar_date(b) in date_set]
        for sym, bars in bars_by_symbol.items()
    }


def _build_ctx(bars_dict: dict) -> dict:
    def bar_date(b) -> str:
        t = b['t']
        return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
    syms = list(bars_dict.keys())
    dates = set(bar_date(b) for bars in bars_dict.values() for b in bars)
    return {d: {'candidates': syms} for d in dates}


def walk_forward(
    bars_by_symbol: dict,
    spy_bars: list[dict],
    strategy_class,
    param_grid: dict,
    starting_equity: float = 100_000,
    is_days: int = IS_DAYS,
    oos_days: int = OOS_DAYS,
    step_days: int = STEP,
    verbose: bool = True,
) -> dict:
    """
    Returns:
      oos_trades  : all OOS trades from all windows concatenated
      oos_equity  : per-day equity, stitched across windows (each window resumes from prev end)
      windows     : list of per-window result dicts
      trade_count : total OOS trades
    """
    # Collect all trading dates
    def bar_date(b) -> str:
        t = b['t']
        return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')

    all_dates = sorted(set(
        bar_date(b) for bars in bars_by_symbol.values() for b in bars
    ))

    if len(all_dates) < is_days + oos_days:
        raise ValueError(f'Not enough history: need {is_days + oos_days} days, have {len(all_dates)}')

    idx = _date_index(all_dates)

    all_oos_trades: list[dict] = []
    all_oos_equity: list[float] = [starting_equity]
    windows: list[dict] = []

    # Start position: begin IS at day 0, OOS after IS_DAYS
    pos = 0
    equity = starting_equity
    window_num = 0

    while pos + is_days + oos_days <= len(all_dates):
        is_dates  = set(all_dates[pos : pos + is_days])
        oos_dates = set(all_dates[pos + is_days : pos + is_days + oos_days])

        is_bars  = _filter_to_dates(bars_by_symbol, is_dates)
        oos_bars = _filter_to_dates(bars_by_symbol, oos_dates)
        is_ctx   = _build_ctx(is_bars)
        oos_ctx  = _build_ctx(oos_bars)

        # ── IS param sweep ──────────────────────────────────────────────────
        best_params = strategy_class().params()
        best_sharpe = -999.0

        param_combos = _sweep_params(param_grid)
        for params in param_combos:
            strat = strategy_class()
            strat.set_params(params)
            eng = BacktestEngine(strat, cost_model=REALISTIC_5, starting_equity=equity)
            res = eng.run(is_bars, ctx_by_date=is_ctx)
            curve = res['daily_equity'] if res['daily_equity'] else res['equity_curve']
            s = sharpe_fn(curve)
            if s > best_sharpe:
                best_sharpe = s
                best_params = dict(params)

        # ── OOS validation ──────────────────────────────────────────────────
        strat = strategy_class()
        strat.set_params(best_params)
        eng = BacktestEngine(strat, cost_model=REALISTIC_5, starting_equity=equity)
        res = eng.run(oos_bars, ctx_by_date=oos_ctx)

        oos_trades = res['trades']
        oos_curve = res['daily_equity'] if res['daily_equity'] else res['equity_curve']

        # Stitch equity: each window continues from prior end equity
        if oos_curve:
            scale = equity / oos_curve[0] if oos_curve[0] > 0 else 1.0
            for v in oos_curve[1:]:
                all_oos_equity.append(v * scale)
            equity = all_oos_equity[-1]

        sc = scorecard(oos_trades, oos_curve, len(oos_dates), label=f'WF window {window_num}')
        window_result = {
            'window': window_num,
            'is_start': min(is_dates),
            'is_end': max(is_dates),
            'oos_start': min(oos_dates),
            'oos_end': max(oos_dates),
            'best_params': best_params,
            'best_is_sharpe': round(best_sharpe, 2),
            'oos_scorecard': sc,
        }
        windows.append(window_result)
        all_oos_trades.extend(oos_trades)

        if verbose:
            oos_ret = sc['total_return']
            oos_sh  = sc['sharpe']
            print(f'  WF[{window_num:02d}] IS {min(is_dates)}→{max(is_dates)} '
                  f'| OOS {min(oos_dates)}→{max(oos_dates)} '
                  f'| params={best_params} '
                  f'| OOS return={oos_ret:+.1%} sharpe={oos_sh:.2f}')

        pos += step_days
        window_num += 1

    return {
        'oos_trades': all_oos_trades,
        'oos_equity': all_oos_equity,
        'windows': windows,
        'trade_count': len(all_oos_trades),
        'final_equity': equity,
    }


def _sweep_params(param_grid: dict) -> list[dict]:
    import itertools
    keys = list(param_grid.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*param_grid.values())]


def print_walk_forward_summary(wf_result: dict) -> None:
    windows = wf_result['windows']
    trades = wf_result['oos_trades']
    equity = wf_result['oos_equity']

    from .metrics import total_return, sharpe as sharpe_fn, max_drawdown, win_rate, profit_factor

    print(f'\n{"═"*80}')
    print(f'  WALK-FORWARD SUMMARY  ({len(windows)} windows)')
    print(f'{"═"*80}')
    print(f'  {"Window":<6} {"OOS Period":<25} {"Params":<40} {"Ret":>6} {"Sharpe":>7}')
    print(f'{"─"*80}')

    for w in windows:
        sc = w['oos_scorecard']
        params_str = str(w['best_params'])[:38]
        print(f'  {w["window"]:<6} {w["oos_start"]}→{w["oos_end"]}  {params_str:<40} '
              f'{sc["total_return"]:>+5.1%} {sc["sharpe"]:>7.2f}')

    print(f'{"─"*80}')

    # Stitched OOS totals
    oos_ret = total_return(equity)
    oos_sh  = sharpe_fn(equity)
    oos_dd  = max_drawdown(equity)
    oos_wr  = win_rate(trades)
    oos_pf  = profit_factor(trades)

    print(f'  Stitched OOS  return={oos_ret:+.1%}  sharpe={oos_sh:.2f}  '
          f'maxDD={oos_dd:.1%}  WR={oos_wr:.1%}  PF={oos_pf:.2f}  trades={len(trades)}')

    # Param stability: how often does each param combo appear?
    from collections import Counter
    param_counts = Counter(str(sorted(w['best_params'].items())) for w in windows)
    print(f'\n  Param stability (most common IS-optimal params):')
    for combo, count in param_counts.most_common(5):
        print(f'    {count:>2}× {combo}')

    print(f'{"═"*80}')
