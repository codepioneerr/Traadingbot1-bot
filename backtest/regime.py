"""
Regime classification for backtest analysis.

Two independent axes:
  VIX regime   : low (<15) | normal (15-25) | high (>25)
  Trend regime : trending (ADX > 25) | choppy (ADX <= 25)

Both are derived from daily bar data:
  - VIX via VIXY ETF (tracks VIX futures; available on Alpaca SIP)
  - ADX computed from SPY daily H/L/C via the standard Wilder 14-period formula

Usage:
    from backtest.regime import build_regime_map
    regime_map = build_regime_map('2021-01-04', '2026-01-03', feed='sip')
    # regime_map[date_str] = {'vix_regime': 'normal', 'trend': 'trending', 'vixy': 18.3, 'adx': 27.1}
"""
from __future__ import annotations
import math
from datetime import datetime

from .data import load_bars


# ── ADX computation (Wilder 14-period) ──────────────────────────────────────

def _compute_adx(bars: list[dict], period: int = 14) -> dict[str, float]:
    """Returns {date_str: adx_value} for all bars with enough history."""
    if len(bars) < period * 2:
        return {}

    adx_map: dict[str, float] = {}

    # True range and directional movement
    trs, plus_dms, minus_dms = [], [], []
    for i in range(1, len(bars)):
        prev = bars[i - 1]
        curr = bars[i]
        high, low, close = curr['h'], curr['l'], curr['c']
        prev_close = prev['c']

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        plus_dm = max(high - prev['h'], 0) if (high - prev['h']) > (prev['l'] - low) else 0
        minus_dm = max(prev['l'] - low, 0) if (prev['l'] - low) > (high - prev['h']) else 0

        trs.append(tr)
        plus_dms.append(plus_dm)
        minus_dms.append(minus_dm)

    def _wilder_smooth(values, n):
        result = [sum(values[:n])]
        for v in values[n:]:
            result.append(result[-1] - result[-1] / n + v)
        return result

    atr14 = _wilder_smooth(trs, period)
    plus_di14 = _wilder_smooth(plus_dms, period)
    minus_di14 = _wilder_smooth(minus_dms, period)

    dx_list = []
    for i in range(len(atr14)):
        atr = atr14[i]
        if atr == 0:
            dx_list.append(0.0)
            continue
        pdi = 100 * plus_di14[i] / atr
        mdi = 100 * minus_di14[i] / atr
        dx = 100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) > 0 else 0.0
        dx_list.append(dx)

    # ADX = smoothed DX
    adx_values = _wilder_smooth(dx_list, period)
    # adx_values[i] corresponds to bars[i + period] (offset for warm-up)
    for i, adx in enumerate(adx_values):
        bar_idx = i + period  # offset for the first smoothed window
        if bar_idx < len(bars):
            date_str = bars[bar_idx]['t'][:10] if isinstance(bars[bar_idx]['t'], str) else bars[bar_idx]['t'].strftime('%Y-%m-%d')
            adx_map[date_str] = round(adx, 2)

    return adx_map


def _classify_vix(vixy_close: float) -> str:
    """
    VIXY is a VIX futures ETF. Its price decays over time (roll cost),
    so absolute thresholds are unreliable across multi-year windows.
    We classify relative to its own trailing 252-day median instead.
    Thresholds below are for raw VIXY close as a fallback initial estimate;
    build_regime_map normalises them to percentile bands.
    """
    if vixy_close < 20:
        return 'low'
    elif vixy_close < 35:
        return 'normal'
    else:
        return 'high'


def _vixy_percentile_classify(vixy_map: dict[str, float]) -> dict[str, str]:
    """
    Classify VIX regime by tercile of VIXY's own 252-day rolling distribution,
    removing ETF decay bias. Bottom third = low, top third = high.
    """
    import statistics
    dates = sorted(vixy_map)
    result: dict[str, str] = {}
    for i, d in enumerate(dates):
        window = [vixy_map[dd] for dd in dates[max(0, i - 251):i + 1]]
        v = vixy_map[d]
        if len(window) < 20:
            result[d] = _classify_vix(v)   # fall back if window too short
            continue
        s = sorted(window)
        p33 = s[len(s) // 3]
        p67 = s[2 * len(s) // 3]
        if v <= p33:
            result[d] = 'low'
        elif v <= p67:
            result[d] = 'normal'
        else:
            result[d] = 'high'
    return result


def build_regime_map(
    start: str,
    end: str,
    feed: str | None = None,
    adx_period: int = 14,
    adx_trend_threshold: float = 25.0,
) -> dict[str, dict]:
    """
    Returns a per-date regime dict covering [start, end].
    Falls back gracefully if VIXY data is unavailable.
    """
    # Load VIXY for VIX proxy (daily)
    try:
        vixy_bars = load_bars('VIXY', start, end, resolution='1Day', feed=feed)
    except Exception:
        vixy_bars = []

    # Load SPY daily for ADX
    try:
        spy_bars = load_bars('SPY', start, end, resolution='1Day', feed=feed)
    except Exception:
        spy_bars = []

    # Build VIXY lookup and classify by rolling percentile (removes decay bias)
    vixy_map: dict[str, float] = {}
    for b in vixy_bars:
        date_str = b['t'][:10] if isinstance(b['t'], str) else b['t'].strftime('%Y-%m-%d')
        vixy_map[date_str] = b['c']
    vix_regime_by_date = _vixy_percentile_classify(vixy_map) if vixy_map else {}

    # Build ADX lookup
    adx_map = _compute_adx(spy_bars, period=adx_period) if spy_bars else {}

    # Collect all dates
    all_dates: set[str] = set()
    for b in vixy_bars:
        d = b['t'][:10] if isinstance(b['t'], str) else b['t'].strftime('%Y-%m-%d')
        all_dates.add(d)
    for b in spy_bars:
        d = b['t'][:10] if isinstance(b['t'], str) else b['t'].strftime('%Y-%m-%d')
        all_dates.add(d)

    regime_map: dict[str, dict] = {}
    for date_str in all_dates:
        vixy_close = vixy_map.get(date_str, 0.0)
        adx = adx_map.get(date_str, 0.0)
        # Use rolling-percentile classification (decay-resistant) when available
        vix_label = vix_regime_by_date.get(date_str,
                        _classify_vix(vixy_close) if vixy_close > 0 else 'unknown')
        regime_map[date_str] = {
            'vix_regime': vix_label,
            'trend': 'trending' if adx >= adx_trend_threshold else 'choppy',
            'vixy': vixy_close,
            'adx': adx,
        }

    return regime_map


def split_trades_by_regime(
    trades: list[dict],
    regime_map: dict[str, dict],
) -> dict[str, list[dict]]:
    """
    Returns a dict of regime_label → [trades in that regime].
    Labels: 'low_trending', 'low_choppy', 'normal_trending', etc.
    """
    buckets: dict[str, list[dict]] = {}
    for trade in trades:
        entry_time = trade.get('entry_time', '')
        date_str = entry_time[:10] if entry_time else ''
        reg = regime_map.get(date_str, {})
        vix_label = reg.get('vix_regime', 'unknown')
        trend_label = reg.get('trend', 'unknown')
        key = f'{vix_label}_{trend_label}'
        buckets.setdefault(key, []).append(trade)
    return buckets


def print_regime_table(
    trades: list[dict],
    regime_map: dict[str, dict],
    equity_by_regime: dict[str, list[float]] | None = None,
) -> dict[str, dict]:
    """
    Print a regime comparison table and return per-regime scorecard dicts.
    """
    from .metrics import win_rate, profit_factor, r_distribution, scorecard

    buckets = split_trades_by_regime(trades, regime_map)
    VIX_ORDER = ['low', 'normal', 'high', 'unknown']
    TREND_ORDER = ['trending', 'choppy', 'unknown']

    print(f'\n{"─"*80}')
    print(f'  REGIME BREAKDOWN')
    print(f'{"─"*80}')
    print(f'  {"Regime":<25} {"Trades":>7} {"Win%":>7} {"PF":>6} {"AvgR":>7} {"Note"}')
    print(f'{"─"*80}')

    out: dict[str, dict] = {}
    for vix_l in VIX_ORDER:
        for trend_l in TREND_ORDER:
            key = f'{vix_l}_{trend_l}'
            subset = buckets.get(key, [])
            if not subset:
                continue
            wr = win_rate(subset)
            pf = profit_factor(subset)
            rd = r_distribution(subset)
            avg_r = rd['mean']
            note = '⭐ edge' if pf > 1.3 and wr > 0.5 else ('⚠️ weak' if pf < 1.0 else '')
            print(f'  {key:<25} {len(subset):>7} {wr:>6.1%} {pf:>6.2f} {avg_r:>7.2f}  {note}')
            out[key] = {'trade_count': len(subset), 'win_rate': wr, 'profit_factor': pf, 'r_dist': rd}

    print(f'{"─"*80}')
    return out
