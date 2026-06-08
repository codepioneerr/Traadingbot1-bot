"""
Performance metrics for the §2 scorecard.

All functions take a list of trade dicts and/or an equity curve (list of floats).
Trade dict keys: entry_price, exit_price, side, qty, exit_reason, entry_time, exit_time
"""
import math
from collections import Counter


# ── Equity-curve metrics ─────────────────────────────────────────────────────

def total_return(equity_curve: list[float]) -> float:
    """Total return as a decimal (0.15 = +15%)."""
    if len(equity_curve) < 2 or equity_curve[0] == 0:
        return 0.0
    return (equity_curve[-1] - equity_curve[0]) / equity_curve[0]


def cagr(equity_curve: list[float], trading_days: int) -> float:
    """Compound annual growth rate."""
    tr = total_return(equity_curve)
    years = trading_days / 252
    if years <= 0:
        return 0.0
    return (1 + tr) ** (1 / years) - 1


def max_drawdown(equity_curve: list[float]) -> float:
    """Maximum peak-to-trough drawdown as a positive decimal (0.15 = -15%)."""
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def daily_returns(equity_curve: list[float]) -> list[float]:
    """Day-over-day returns."""
    return [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] != 0
    ]


def sharpe(equity_curve: list[float], risk_free_annual: float = 0.04) -> float:
    """
    Annualised Sharpe ratio, assuming one point per TRADING DAY (252/year).

    IMPORTANT: pass daily_equity, NOT equity_curve.
    equity_curve is per-bar (per minute); using it here overstates the
    annualisation by sqrt(390) ≈ 19.7× and produces nonsensical results
    like Sharpe = ±80.

    Returns 0.0 if fewer than 10 daily returns are available (too noisy).
    """
    rets = daily_returns(equity_curve)
    if len(rets) < 10:                          # guard: need at least ~2 weeks
        return 0.0
    rf_daily = (1 + risk_free_annual) ** (1 / 252) - 1
    excess = [r - rf_daily for r in rets]
    mean = sum(excess) / len(excess)
    variance = sum((r - mean) ** 2 for r in excess) / (len(excess) - 1)
    std = math.sqrt(variance) if variance > 0 else 0.0
    return (mean / std) * math.sqrt(252) if std > 0 else 0.0


# ── Trade-level metrics ──────────────────────────────────────────────────────

def pnl(trade: dict) -> float:
    """Realised P&L for a single trade (signed $)."""
    side = trade.get('side', 'long')
    qty = trade.get('qty', 1)
    entry = trade['entry_price']
    exit_ = trade['exit_price']
    if side == 'long':
        return (exit_ - entry) * qty
    else:
        return (entry - exit_) * qty


def r_multiple(trade: dict) -> float | None:
    """
    R-multiple: PnL expressed in units of initial risk.
    Requires trade['stop'] to be set.
    """
    stop = trade.get('stop')
    if stop is None:
        return None
    side = trade.get('side', 'long')
    entry = trade['entry_price']
    risk_per_share = abs(entry - stop)
    if risk_per_share == 0:
        return None
    p = pnl(trade) / trade.get('qty', 1)
    return p / risk_per_share


def win_rate(trades: list[dict]) -> float:
    """Fraction of closed trades with positive P&L."""
    closed = [t for t in trades if 'exit_price' in t]
    if not closed:
        return 0.0
    wins = sum(1 for t in closed if pnl(t) > 0)
    return wins / len(closed)


def profit_factor(trades: list[dict]) -> float:
    """Gross wins / gross losses. Returns inf if no losses."""
    closed = [t for t in trades if 'exit_price' in t]
    gross_win = sum(pnl(t) for t in closed if pnl(t) > 0)
    gross_loss = abs(sum(pnl(t) for t in closed if pnl(t) < 0))
    if gross_loss == 0:
        return float('inf')
    return gross_win / gross_loss


def r_distribution(trades: list[dict]) -> dict:
    """Mean, median, and percentiles of R-multiples."""
    rs = [r for t in trades if (r := r_multiple(t)) is not None]
    if not rs:
        return {'mean': 0, 'median': 0, 'p25': 0, 'p75': 0, 'count': 0}
    rs.sort()
    n = len(rs)
    return {
        'mean': sum(rs) / n,
        'median': rs[n // 2],
        'p25': rs[n // 4],
        'p75': rs[3 * n // 4],
        'count': n,
    }


def exit_reason_breakdown(trades: list[dict]) -> dict:
    """Count exits by reason: target | momentum-trail | failed-breakout | eod-flat | stop"""
    reasons = [t.get('exit_reason', 'unknown') for t in trades if 'exit_reason' in t]
    return dict(Counter(reasons))


# ── Full scorecard ────────────────────────────────────────────────────────────

def scorecard(
    trades: list[dict],
    equity_curve: list[float],
    trading_days: int,
    label: str = '',
) -> dict:
    return {
        'label': label,
        'trade_count': len(trades),
        'total_return': total_return(equity_curve),
        'cagr': cagr(equity_curve, trading_days),
        'sharpe': sharpe(equity_curve),
        'max_drawdown': max_drawdown(equity_curve),
        'win_rate': win_rate(trades),
        'profit_factor': profit_factor(trades),
        'r_distribution': r_distribution(trades),
        'exit_reasons': exit_reason_breakdown(trades),
    }


def annual_sharpe_breakdown(
    daily_equity: list,
    active_dates: list,
    all_dates: list,
    trades: list,
    starting_equity: float = 100_000,
) -> dict:
    """
    Year-by-year performance breakdown.

    daily_equity  : one equity snapshot per date in active_dates (engine output).
                    On days the strategy sat flat, equity is carried forward so
                    Sharpe annualisation uses the correct 252-day denominator.
    active_dates  : sorted list of dates the engine processed (sparse subset of all_dates).
    all_dates     : every trading date in the full backtest window.
    trades        : closed trade list from engine (for per-year trade stats).
    starting_equity: initial capital (used to anchor the carry-forward on day 0).

    Returns {year_str: {sharpe, total_return, trade_count, win_rate, profit_factor}}.
    """
    from collections import defaultdict

    if not daily_equity or not active_dates:
        return {}

    # Map active date → recorded equity
    date_to_eq: dict = {}
    for i, d in enumerate(active_dates[: len(daily_equity)]):
        date_to_eq[d] = daily_equity[i]

    # Reconstruct full daily equity — carry forward on flat days
    full_eq:    list = []
    full_dates: list = []
    last_eq = starting_equity
    for d in all_dates:
        eq = date_to_eq.get(d, last_eq)
        full_eq.append(eq)
        full_dates.append(d)
        last_eq = eq

    # Group equity by calendar year
    year_eq: dict = defaultdict(list)
    for i, d in enumerate(full_dates):
        year_eq[d[:4]].append(full_eq[i])

    # Group trades by exit year
    year_trades: dict = defaultdict(list)
    for t in trades:
        yr = (t.get('exit_time') or t.get('entry_time', '2000'))[:4]
        year_trades[yr].append(t)

    result: dict = {}
    for year in sorted(year_eq):
        curve = year_eq[year]
        if len(curve) < 10:
            continue
        s  = sharpe(curve)
        tr = (curve[-1] / curve[0] - 1.0) if curve[0] > 0 else 0.0
        yt = year_trades.get(year, [])
        result[year] = {
            'sharpe':        round(s,  2),
            'total_return':  round(tr, 4),
            'trade_count':   len(yt),
            'win_rate':      round(win_rate(yt),      3) if yt else 0.0,
            'profit_factor': round(profit_factor(yt), 2) if yt else 0.0,
        }

    return result


def print_annual_breakdown(annual: dict) -> None:
    """Pretty-print the output of annual_sharpe_breakdown()."""
    print(f'\n{"─"*65}')
    print(f'  {"Year":<6} {"Sharpe":>7} {"Return":>8} {"Trades":>7} {"WinRate":>8} {"PF":>6}')
    print(f'{"─"*65}')
    for year, m in sorted(annual.items()):
        icon = '✅' if m['sharpe'] > 0 else '❌'
        print(
            f'  {year:<6} {m["sharpe"]:>7.2f} {m["total_return"]:>+8.1%}'
            f' {m["trade_count"]:>7} {m["win_rate"]:>8.1%} {m["profit_factor"]:>6.2f}  {icon}'
        )
    print(f'{"─"*65}')


def print_scorecard(sc: dict) -> None:
    label = sc.get('label', '')
    print(f'\n{"═"*60}')
    if label:
        print(f'  {label}')
        print(f'{"═"*60}')
    print(f"  Total return   : {sc['total_return']:+.1%}")
    print(f"  CAGR           : {sc['cagr']:+.1%}")
    print(f"  Sharpe         : {sc['sharpe']:.2f}")
    print(f"  Max drawdown   : {sc['max_drawdown']:.1%}")
    print(f"  Win rate       : {sc['win_rate']:.1%}")
    print(f"  Profit factor  : {sc['profit_factor']:.2f}")
    print(f"  Trade count    : {sc['trade_count']}")
    rd = sc['r_distribution']
    print(f"  R-multiple     : mean={rd['mean']:.2f}  median={rd['median']:.2f}  p25={rd['p25']:.2f}  p75={rd['p75']:.2f}")
    er = sc['exit_reasons']
    if er:
        print(f"  Exit reasons   :", '  '.join(f'{k}:{v}' for k, v in sorted(er.items())))
    print(f'{"═"*60}')
