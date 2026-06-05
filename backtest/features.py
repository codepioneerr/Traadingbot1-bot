"""
Feature extraction and random-forest importance for ORB trades.

Features per trade:
  vix_regime   : 0=low, 1=normal, 2=high  (from VIXY proxy)
  rel_volume   : today's first-bar vol / 20d avg (proxy from bar data)
  gap_pct      : (entry_open - prev_close) / prev_close
  time_of_day  : minutes since 9:30 ET at entry
  day_of_week  : 0=Mon … 4=Fri
  or_width_pct : OR width / entry price (from stop/target geometry)
  sector       : encoded integer (large_cap=0, small_cap=1, etf=2, crypto=3)

Target: trade_outcome — 1 if PnL > 0, 0 otherwise.

Usage:
    from backtest.features import extract_features, train_importance
    X, y, feature_names = extract_features(trades, regime_map, bars_by_symbol)
    importances = train_importance(X, y, feature_names)
"""
from __future__ import annotations
import math
from datetime import datetime, timezone, timedelta


# ── Sector lookup ─────────────────────────────────────────────────────────────

SECTOR_MAP: dict[str, int] = {
    # Large-cap tech
    'AAPL': 0, 'NVDA': 0, 'MSFT': 0, 'TSLA': 0, 'META': 0,
    'AMZN': 0, 'GOOGL': 0, 'AMD': 0, 'NFLX': 0, 'ORCL': 0,
    # Small-cap / meme
    'SIRI': 1, 'AMC': 1, 'BBBY': 1, 'SPCE': 1, 'MVIS': 1,
    'CLOV': 1, 'WKHS': 1, 'RIDE': 1, 'GOEV': 1, 'NKLA': 1,
    # ETFs
    'QQQ': 2, 'SPY': 2, 'IWM': 2, 'XLK': 2, 'ARKK': 2,
    'SOXL': 2, 'TQQQ': 2, 'UVXY': 2, 'GLD': 2, 'TLT': 2,
    # Crypto
    'BTC/USD': 3, 'ETH/USD': 3, 'SOL/USD': 3,
}

VIX_REGIME_INT = {'low': 0, 'normal': 1, 'high': 2, 'unknown': 1}


def _parse_time(s) -> datetime | None:
    if isinstance(s, datetime):
        return s
    if isinstance(s, str):
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00'))
        except Exception:
            return None
    return None


def _to_et(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        import zoneinfo
        return dt.astimezone(zoneinfo.ZoneInfo('America/New_York'))
    except Exception:
        month = dt.month
        if 3 < month < 11 or (month == 3 and dt.day >= 8) or (month == 11 and dt.day < 7):
            return dt + timedelta(hours=-4)
        return dt + timedelta(hours=-5)


def _or_width_pct(trade: dict) -> float:
    """
    Approximate OR width as a fraction of entry price using stop/target geometry.
    For a long: target ≈ entry + OR_width, stop ≈ entry - OR_half
    We use target - entry as a proxy (measured move = OR width).
    """
    entry = trade.get('entry_price', 0)
    target = trade.get('target', 0)
    stop = trade.get('stop', 0)
    if not entry or entry == 0:
        return 0.0
    if target and target > entry:
        return (target - entry) / entry   # measured move / entry
    elif stop and stop < entry:
        return (entry - stop) / entry     # stop distance / entry
    return 0.0


def _gap_pct(trade: dict, bars_by_symbol: dict) -> float:
    """
    Gap = (day open - prior close) / prior close.
    Looks up the first bar of the entry day vs last bar of prior day.
    """
    symbol = trade.get('symbol', '')
    entry_time = _parse_time(trade.get('entry_time', ''))
    if not entry_time or symbol not in bars_by_symbol:
        return 0.0

    entry_date = _to_et(entry_time).strftime('%Y-%m-%d')
    bars = bars_by_symbol[symbol]

    day_bars, prior_bars = [], []
    for b in bars:
        t = b['t']
        d = t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
        if d == entry_date:
            day_bars.append(b)
        elif d < entry_date:
            prior_bars.append(b)

    if not day_bars or not prior_bars:
        return 0.0

    day_open = day_bars[0]['o']
    prior_close = prior_bars[-1]['c']
    if prior_close == 0:
        return 0.0
    return (day_open - prior_close) / prior_close


def _rel_volume(trade: dict, bars_by_symbol: dict, lookback: int = 20) -> float:
    """
    Ratio of entry-day first-bar volume to 20d average first-bar volume.
    """
    symbol = trade.get('symbol', '')
    entry_time = _parse_time(trade.get('entry_time', ''))
    if not entry_time or symbol not in bars_by_symbol:
        return 1.0

    entry_date = _to_et(entry_time).strftime('%Y-%m-%d')
    bars = bars_by_symbol[symbol]

    from collections import defaultdict
    daily_first_vol: dict[str, int] = {}
    current_day = None
    for b in bars:
        t = b['t']
        d = t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
        if d not in daily_first_vol:
            daily_first_vol[d] = b['v']

    days_before = sorted(d for d in daily_first_vol if d < entry_date)[-lookback:]
    today_vol = daily_first_vol.get(entry_date, 0)
    if not days_before:
        return 1.0
    avg = sum(daily_first_vol[d] for d in days_before) / len(days_before)
    return today_vol / avg if avg > 0 else 1.0


def extract_features(
    trades: list[dict],
    regime_map: dict[str, dict],
    bars_by_symbol: dict,
) -> tuple:
    """
    Returns (X: list[list], y: list[int], feature_names: list[str]).
    Skips trades where features can't be computed.
    """
    feature_names = [
        'vix_regime',
        'rel_volume',
        'gap_pct',
        'time_of_day_min',
        'day_of_week',
        'or_width_pct',
        'sector',
    ]

    X, y = [], []

    for trade in trades:
        entry_time = _parse_time(trade.get('entry_time', ''))
        if not entry_time:
            continue

        entry_date = _to_et(entry_time).strftime('%Y-%m-%d')
        entry_et = _to_et(entry_time)

        reg = regime_map.get(entry_date, {})
        vix_regime = VIX_REGIME_INT.get(reg.get('vix_regime', 'unknown'), 1)

        rel_vol = _rel_volume(trade, bars_by_symbol)
        gap = _gap_pct(trade, bars_by_symbol)

        market_open_min = 9 * 60 + 30
        entry_min = entry_et.hour * 60 + entry_et.minute
        time_of_day = entry_min - market_open_min  # minutes after open

        day_of_week = entry_et.weekday()  # 0=Mon
        or_width = _or_width_pct(trade)
        sector = SECTOR_MAP.get(trade.get('symbol', ''), 0)

        pnl = trade.get('pnl', 0)
        outcome = 1 if pnl > 0 else 0

        X.append([vix_regime, rel_vol, gap, time_of_day, day_of_week, or_width, sector])
        y.append(outcome)

    return X, y, feature_names


def train_importance(
    X: list[list],
    y: list[int],
    feature_names: list[str],
    n_estimators: int = 500,
    random_state: int = 42,
) -> dict:
    """
    Train a RandomForestClassifier and return feature importances.
    Returns dict with importances, OOB accuracy, and a printed table.
    """
    if len(X) < 50:
        return {'error': f'Too few trades ({len(X)}) to train RF (need ≥ 50)'}

    try:
        from sklearn.ensemble import RandomForestClassifier
        import numpy as np

        X_arr = np.array(X, dtype=float)
        y_arr = np.array(y)

            clf = RandomForestClassifier(
            n_estimators=n_estimators,
            oob_score=True,
            max_features='sqrt',
            min_samples_leaf=max(5, len(X) // 20),  # prevent overfitting on small samples
            random_state=random_state,
            n_jobs=-1,
        )
        clf.fit(X_arr, y_arr)

        importances = {
            name: round(float(imp), 4)
            for name, imp in zip(feature_names, clf.feature_importances_)
        }
        oob = round(float(clf.oob_score_), 4)

        # OOB > 0.6 on < 500 trades is likely overfitting — note it
        overfit_warning = oob > 0.60 and len(X) < 500

        return {
            'importances': importances,
            'oob_accuracy': oob,
            'n_trades': len(X),
            'win_rate_actual': round(sum(y) / len(y), 3),
            'overfit_warning': overfit_warning,
        }

    except ImportError:
        return {'error': 'sklearn not available'}


def print_importance_table(result: dict) -> None:
    if 'error' in result:
        print(f'  Feature importance unavailable: {result["error"]}')
        return

    imp = result['importances']
    oob = result['oob_accuracy']
    n = result['n_trades']
    wr = result['win_rate_actual']

    print(f'\n{"═"*60}')
    print(f'  RANDOM FOREST FEATURE IMPORTANCE')
    warn = '  ⚠️  OOB may be inflated (< 500 trades)' if result.get('overfit_warning') else ''
    print(f'  Trades: {n}  |  OOB accuracy: {oob:.1%}  |  Actual WR: {wr:.1%}{warn}')
    print(f'{"─"*60}')
    for name, importance in sorted(imp.items(), key=lambda x: -x[1]):
        bar = '█' * int(importance * 40)
        print(f'  {name:<20} {importance:.4f}  {bar}')
    print(f'{"═"*60}')
    print(f'  (OOB accuracy ≈ 0.5 means features have little predictive power)')
