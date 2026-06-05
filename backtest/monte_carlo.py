"""
Monte Carlo simulation for backtest results.

Two methods run together:
  Bootstrap (sample with replacement): tests whether the edge is a sampling
    artifact. Each simulation draws N trades from the pool with replacement.
    The actual result ranked high in this distribution = robust edge.
    A result at the 50th percentile means it's consistent with random sampling.

  Shuffle (sequence test): same trades, different order. Tests sequence risk —
    i.e., could a different draw order have produced a much worse drawdown?
    Return is invariant to shuffle; max drawdown is not.

Usage:
    from backtest.monte_carlo import monte_carlo, print_mc_summary
    mc = monte_carlo(trades, starting_equity=100_000, n_sims=10_000)
    print_mc_summary(mc, spy_return=0.12)
"""
from __future__ import annotations
import random


def _equity_from_pnl_sequence(pnl_seq: list[float], starting_equity: float) -> list[float]:
    curve = [starting_equity]
    eq = starting_equity
    for pnl in pnl_seq:
        eq += pnl
        curve.append(eq)
    return curve


def _max_drawdown(curve: list[float]) -> float:
    peak = curve[0]
    dd = 0.0
    for v in curve:
        if v > peak:
            peak = v
        d = (peak - v) / peak if peak > 0 else 0.0
        if d > dd:
            dd = d
    return dd


def monte_carlo(
    trades: list[dict],
    starting_equity: float = 100_000,
    n_sims: int = 10_000,
    ruin_threshold: float = 0.5,
    random_seed: int = 42,
) -> dict:
    """
    Runs bootstrap + shuffle simulations. Returns statistics dict.
    """
    if not trades:
        return {'error': 'No trades to simulate'}

    pnl_seq = [t.get('pnl', 0.0) for t in trades]
    n = len(pnl_seq)
    actual_final = starting_equity + sum(pnl_seq)
    actual_return = (actual_final - starting_equity) / starting_equity
    actual_dd = _max_drawdown(_equity_from_pnl_sequence(pnl_seq, starting_equity))

    rng = random.Random(random_seed)
    ruin_eq = starting_equity * ruin_threshold

    # ── Bootstrap: sample N trades with replacement ──────────────────────────
    boot_finals: list[float] = []
    boot_dds: list[float] = []
    boot_ruin = 0

    for _ in range(n_sims):
        sampled = [rng.choice(pnl_seq) for _ in range(n)]
        curve = _equity_from_pnl_sequence(sampled, starting_equity)
        final = curve[-1]
        dd = _max_drawdown(curve)
        boot_finals.append(final)
        boot_dds.append(dd)
        if min(curve) < ruin_eq:
            boot_ruin += 1

    boot_finals.sort()
    boot_dds.sort()

    # ── Shuffle: same trades, different sequence (tests drawdown path risk) ──
    shuf_dds: list[float] = []
    for _ in range(n_sims):
        shuffled = pnl_seq[:]
        rng.shuffle(shuffled)
        curve = _equity_from_pnl_sequence(shuffled, starting_equity)
        shuf_dds.append(_max_drawdown(curve))
    shuf_dds.sort()

    # Rank actual return in bootstrap distribution
    actual_boot_rank = sum(1 for f in boot_finals if f <= actual_final) / n_sims
    # Rank actual drawdown in shuffle distribution (lower = better)
    actual_dd_rank = sum(1 for d in shuf_dds if d <= actual_dd) / n_sims

    def _pct(sorted_list, p):
        idx = int(len(sorted_list) * p / 100)
        return sorted_list[min(idx, len(sorted_list) - 1)]

    return {
        'n_sims': n_sims,
        'n_trades': n,
        'starting_equity': starting_equity,
        'actual_return': round(actual_return, 4),
        'actual_max_dd': round(actual_dd, 4),
        # Bootstrap stats (return distribution)
        'bootstrap_return_rank_pct': round(actual_boot_rank * 100, 1),
        'bootstrap_ruin_probability': round(boot_ruin / n_sims, 4),
        'bootstrap_return_percentiles': {
            'p5':  round((_pct(boot_finals, 5)  - starting_equity) / starting_equity, 4),
            'p25': round((_pct(boot_finals, 25) - starting_equity) / starting_equity, 4),
            'p50': round((_pct(boot_finals, 50) - starting_equity) / starting_equity, 4),
            'p75': round((_pct(boot_finals, 75) - starting_equity) / starting_equity, 4),
            'p95': round((_pct(boot_finals, 95) - starting_equity) / starting_equity, 4),
        },
        # Shuffle stats (drawdown path risk)
        'shuffle_dd_actual_rank_pct': round(actual_dd_rank * 100, 1),
        'shuffle_dd_percentiles': {
            'p50': round(_pct(shuf_dds, 50), 4),
            'p75': round(_pct(shuf_dds, 75), 4),
            'p95': round(_pct(shuf_dds, 95), 4),
        },
    }


def print_mc_summary(mc: dict, spy_return: float | None = None) -> None:
    if 'error' in mc:
        print(f'  Monte Carlo: {mc["error"]}')
        return

    n = mc['n_sims']
    actual_r = mc['actual_return']
    actual_dd = mc['actual_max_dd']

    boot_rank = mc['bootstrap_return_rank_pct']
    boot_ruin = mc['bootstrap_ruin_probability']
    brp = mc['bootstrap_return_percentiles']

    shuf_dd_rank = mc['shuffle_dd_actual_rank_pct']
    shuf_ddp = mc['shuffle_dd_percentiles']

    print(f'\n{"═"*68}')
    print(f'  MONTE CARLO  ({n:,} simulations, {mc["n_trades"]} trades)')
    print(f'{"─"*68}')
    print(f'  Actual return   : {actual_r:+.2%}')
    print(f'  Actual max DD   : {actual_dd:.2%}')

    print(f'\n  BOOTSTRAP (sample with replacement — tests edge robustness):')
    print(f'  Return rank     : {boot_rank:.0f}th pct  ', end='')
    if boot_rank >= 75:
        print('✓ top quartile — edge appears genuine')
    elif boot_rank >= 50:
        print('neutral — consistent with random sampling')
    else:
        print('⚠️  below median — edge may be fragile')

    print(f'  Ruin prob       : {boot_ruin:.1%}  (equity < 50% of start)')
    print(f'  Return dist     : p5={brp["p5"]:+.1%}  p25={brp["p25"]:+.1%}  '
          f'p50={brp["p50"]:+.1%}  p75={brp["p75"]:+.1%}  p95={brp["p95"]:+.1%}')

    if spy_return is not None:
        beat = sum(1 for r in brp.values() if r > spy_return)
        print(f'  Beat SPY ({spy_return:+.1%}) : {beat}/5 bootstrap percentiles exceed SPY')

    print(f'\n  SHUFFLE (sequence risk — tests drawdown path variance):')
    print(f'  Actual DD rank  : {shuf_dd_rank:.0f}th pct  ', end='')
    if shuf_dd_rank <= 50:
        print('✓ below median — sequence did NOT inflate drawdown')
    else:
        print('⚠️  above median — sequence added path risk vs typical order')
    print(f'  DD distribution : median={shuf_ddp["p50"]:.1%}  p75={shuf_ddp["p75"]:.1%}  p95={shuf_ddp["p95"]:.1%}')

    print(f'{"═"*68}')
