"""
Dual Momentum — Antonacci (2014)
=================================

A two-filter monthly rotation strategy:

  Step 1 — Absolute Momentum:
    If SPY 12-month price return < 0%: hold SHY (safe haven / cash proxy).
    Otherwise proceed to Step 2.

  Step 2 — Relative Momentum:
    Rank [SPY, QQQ, IWM, TLT, GLD] by 12-month price return.
    Hold the top-ranked asset for the next month.

Rebalance on the last trading day of each month.
No trade if the top asset is unchanged (avoids unnecessary turnover).

Reference: Gary Antonacci, "Dual Momentum Investing" (2014).
Published CAGR: ~10–12% (2000–2014), Max DD: ~15–17%.
"""
from __future__ import annotations

UNIVERSE   = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD']   # ranked assets
SAFE_ASSET = 'SHY'                                    # absolute-momentum fallback
LOOKBACK   = 12                                       # months


def compute_12m_return(monthly_closes: list[float], idx: int) -> float | None:
    """Price return from 12 months ago to current month (no dividends)."""
    if idx < LOOKBACK or monthly_closes[idx - LOOKBACK] <= 0:
        return None
    return monthly_closes[idx] / monthly_closes[idx - LOOKBACK] - 1


def get_monthly_signal(
    monthly_by_sym: dict[str, list[float]],
    idx: int,
) -> str | None:
    """
    Returns the asset to hold for the NEXT month, or None if insufficient history.

    monthly_by_sym: {symbol: [monthly close prices in chronological order]}
    idx: current month index (0 = oldest month in data)
    """
    if idx < LOOKBACK:
        return None

    # ── Step 1: Absolute momentum ─────────────────────────────────────────────
    spy_ret = compute_12m_return(monthly_by_sym['SPY'], idx)
    if spy_ret is None or spy_ret < 0.0:
        return SAFE_ASSET

    # ── Step 2: Relative momentum ─────────────────────────────────────────────
    rets: dict[str, float] = {}
    for sym in UNIVERSE:
        r = compute_12m_return(monthly_by_sym[sym], idx)
        if r is not None:
            rets[sym] = r

    if not rets:
        return SAFE_ASSET

    return max(rets, key=rets.get)


def run_backtest(
    daily_by_sym: dict[str, list[dict]],  # {sym: [{'t':str, 'c':float}, ...]}
    start_date:   str = '2005-01-01',
    end_date:     str = '2026-01-01',
    start_equity: float = 100_000.0,
    slippage_bps: float = 5.0,
    spread_pct:   float = 0.001,
) -> dict:
    """
    Simulate Dual Momentum from start_date to end_date.

    Returns a result dict with monthly equity curve, trade log,
    per-month holdings, and aggregate statistics.
    """
    import math
    from collections import defaultdict

    ALL_SYMS = UNIVERSE + [SAFE_ASSET]

    # ── Aggregate to monthly last-day closes ──────────────────────────────────
    def _last_day_closes(bars: list[dict]) -> dict[str, float]:
        """Return {YYYY-MM: last_close_of_month} for all bars."""
        by_month: dict[str, tuple[str, float]] = {}
        for b in bars:
            t = b['t'] if isinstance(b['t'], str) else str(b['t'])[:10]
            m = t[:7]
            if m not in by_month or t > by_month[m][0]:
                by_month[m] = (t, b['c'])
        return {m: v[1] for m, v in by_month.items()}

    monthly_closes: dict[str, dict[str, float]] = {}
    for sym in ALL_SYMS:
        bars = daily_by_sym.get(sym, [])
        monthly_closes[sym] = _last_day_closes(bars)

    # ── Build aligned monthly timeline ────────────────────────────────────────
    # Use SPY's months as the master calendar
    all_months = sorted(
        m for m in monthly_closes.get('SPY', {})
        if start_date[:7] <= m <= end_date[:7]
    )
    # We need 12 months of history before the first holding month
    # Include warm-up months (before start_date) for lookback
    warmup_months = sorted(
        m for m in monthly_closes.get('SPY', {})
        if m < start_date[:7]
    )

    # Combined timeline: warm-up + active
    timeline = sorted(warmup_months + all_months)

    # Build per-symbol price arrays aligned to timeline
    monthly_prices: dict[str, list[float]] = {sym: [] for sym in ALL_SYMS}
    monthly_labels: list[str] = []

    for m in timeline:
        monthly_labels.append(m)
        for sym in ALL_SYMS:
            close_map = monthly_closes.get(sym, {})
            # Forward-fill if a month is missing (e.g. SHY on some months)
            if m in close_map:
                price = close_map[m]
            else:
                price = monthly_prices[sym][-1] if monthly_prices[sym] else 0.0
            monthly_prices[sym].append(price)

    # Index of first active month
    first_active = next(
        (i for i, m in enumerate(monthly_labels) if m >= start_date[:7]), 0
    )

    # ── Simulation ────────────────────────────────────────────────────────────
    factor_buy  = 1 + slippage_bps / 10_000 + spread_pct / 2
    factor_sell = 1 - slippage_bps / 10_000 - spread_pct / 2

    equity    = start_equity
    holding   = None        # current asset being held
    trades    = []
    monthly_results = []    # one entry per active month

    for i in range(first_active, len(monthly_labels)):
        month = monthly_labels[i]
        prev_i = i - 1  # previous month index for return calculation

        # Compute this month's portfolio return (before signal check)
        if holding and prev_i >= 0:
            prev_p = monthly_prices[holding][prev_i]
            curr_p = monthly_prices[holding][i]
            if prev_p > 0:
                month_ret = curr_p / prev_p - 1
                equity *= (1 + month_ret)
        elif not holding:
            month_ret = 0.0
        else:
            month_ret = 0.0

        # Signal: what to hold NEXT month (determined at END of this month)
        new_holding = get_monthly_signal(monthly_prices, i)

        # Record this month's result
        monthly_results.append({
            'month':    month,
            'equity':   equity,
            'holding':  holding,
            'signal':   new_holding,
            'return':   month_ret if holding else 0.0,
        })

        # Rebalance if holding changes
        if new_holding and new_holding != holding:
            trade_value = equity
            cost = trade_value * (slippage_bps / 10_000 + spread_pct / 2) * 2  # round-trip
            equity -= cost
            trades.append({
                'month':     month,
                'from_asset': holding or 'none',
                'to_asset':  new_holding,
                'cost':      cost,
                'equity':    equity,
            })
            holding = new_holding
        elif not holding and new_holding:
            # First entry into a position
            holding = new_holding

    # ── Metrics ───────────────────────────────────────────────────────────────
    active_results = [r for r in monthly_results if r['month'] >= start_date[:7]]

    monthly_equity = [r['equity'] for r in active_results]
    monthly_rets   = [r['return'] for r in active_results if r['return'] != 0.0 or r['holding']]

    def _total_return(eq):
        if len(eq) < 2 or eq[0] == 0: return 0.0
        return eq[-1] / eq[0] - 1

    def _cagr(eq, n_months):
        tr = _total_return(eq)
        years = n_months / 12
        if years <= 0: return 0.0
        return (1 + tr) ** (1 / years) - 1

    def _sharpe(monthly_rets_list, rf_annual=0.02):
        if len(monthly_rets_list) < 6: return 0.0
        rf_m   = (1 + rf_annual) ** (1/12) - 1
        excess = [r - rf_m for r in monthly_rets_list]
        mean   = sum(excess) / len(excess)
        var    = sum((r - mean)**2 for r in excess) / max(1, len(excess) - 1)
        std    = math.sqrt(var) if var > 0 else 0.0
        return (mean / std) * math.sqrt(12) if std > 0 else 0.0

    def _max_dd(eq):
        peak = eq[0]
        dd   = 0.0
        for v in eq:
            if v > peak: peak = v
            if peak > 0: dd = max(dd, (peak - v) / peak)
        return dd

    def _win_rate(rets):
        if not rets: return 0.0
        return sum(1 for r in rets if r > 0) / len(rets)

    def _pf(rets):
        wins   = sum(r for r in rets if r > 0)
        losses = sum(-r for r in rets if r < 0)
        return wins / losses if losses > 0 else (float('inf') if wins > 0 else 0.0)

    n_months = len(active_results)
    full_rets = [r['return'] for r in active_results]

    # Asset allocation histogram
    alloc: dict[str, int] = defaultdict(int)
    for r in active_results:
        if r['holding']:
            alloc[r['holding']] += 1

    abs_filter_months = sum(1 for r in active_results if r['signal'] == SAFE_ASSET)

    return {
        'monthly_results': monthly_results,
        'active_results':  active_results,
        'trades':          trades,
        'monthly_equity':  monthly_equity,
        'metrics': {
            'total_return':   _total_return(monthly_equity),
            'cagr':           _cagr(monthly_equity, n_months),
            'sharpe':         _sharpe(full_rets),
            'max_drawdown':   _max_dd(monthly_equity),
            'win_rate':       _win_rate(full_rets),
            'n_trades':       len(trades),
            'n_months':       n_months,
            'profit_factor':  _pf(full_rets),
        },
        'allocation':         dict(alloc),
        'abs_filter_months':  abs_filter_months,
        'start_equity':       start_equity,
        'final_equity':       monthly_equity[-1] if monthly_equity else start_equity,
    }
