"""
Historical bar loader — Alpaca first, pluggable source.

WARNING: Alpaca free IEX feed has partial volume and limited intraday history.
Any backtest result produced from IEX bars is INDICATIVE ONLY.
For a conclusive 5-year backtest, use the SIP feed (paid) or Polygon.
The feed used is printed in every scorecard.

Bars are cached to disk as parquet to avoid re-hitting the API.
Cache location: backtest/cache/<source>/<symbol>/<resolution>.parquet
"""
import os
import json
import time
import hashlib
import requests
from datetime import datetime, date, timedelta
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

# ── Alpaca auth ──────────────────────────────────────────────────────────────

def _alpaca_headers() -> dict:
    key = os.environ.get('ALPACA_API_KEY', '')
    secret = os.environ.get('ALPACA_SECRET_KEY', '')
    if not key or not secret:
        raise EnvironmentError(
            'ALPACA_API_KEY and ALPACA_SECRET_KEY must be set.\n'
            'Run: export ALPACA_API_KEY=... ALPACA_SECRET_KEY=...'
        )
    return {'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret}

# ── Feed detection ───────────────────────────────────────────────────────────

def detect_feed() -> str:
    """
    Returns 'sip' (paid, complete) or 'iex' (free, partial).
    SIP feed is available with a paid Alpaca subscription.
    """
    # Try a SIP-specific endpoint — if it 403s, we're on IEX
    url = 'https://data.alpaca.markets/v2/stocks/AAPL/bars'
    params = {'timeframe': '1Min', 'start': '2024-01-02', 'end': '2024-01-02', 'feed': 'sip', 'limit': 1}
    try:
        r = requests.get(url, headers=_alpaca_headers(), params=params, timeout=10)
        if r.status_code == 200:
            return 'sip'
    except Exception:
        pass
    return 'iex'

# ── Bar loading ──────────────────────────────────────────────────────────────

def load_bars(
    symbol: str,
    start: str,        # 'YYYY-MM-DD'
    end: str,          # 'YYYY-MM-DD'
    resolution: str = '1Min',
    feed: str | None = None,
    use_cache: bool = True,
) -> list[dict]:
    """
    Load minute bars for symbol over [start, end].
    Returns list of dicts: {t, o, h, l, c, v, vwap}
    Caches to parquet on disk.
    """
    if feed is None:
        feed = detect_feed()

    cache_key = hashlib.md5(f'{symbol}{start}{end}{resolution}{feed}'.encode()).hexdigest()[:12]
    cache_path = CACHE_DIR / f'{symbol}_{start}_{end}_{resolution}_{feed}_{cache_key}.json'

    if use_cache and cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    bars = _fetch_alpaca_bars(symbol, start, end, resolution, feed)

    if use_cache:
        with open(cache_path, 'w') as f:
            json.dump(bars, f)

    return bars


def _fetch_alpaca_bars(symbol, start, end, resolution, feed) -> list[dict]:
    url = f'https://data.alpaca.markets/v2/stocks/{symbol}/bars'
    headers = _alpaca_headers()
    bars = []
    page_token = None

    while True:
        params = {
            'timeframe': resolution,
            # Use UTC equivalents of 9:30–16:00 ET with a wide window; strategy filters by ET time
            'start': f'{start}T00:00:00Z',
            'end': f'{end}T23:59:59Z',
            'feed': feed,
            'limit': 10000,
            'adjustment': 'split',
        }
        if page_token:
            params['page_token'] = page_token

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for b in data.get('bars', []):
            bars.append({
                't': b['t'],
                'o': b['o'],
                'h': b['h'],
                'l': b['l'],
                'c': b['c'],
                'v': b['v'],
                'vwap': b.get('vw', b['c']),
            })

        page_token = data.get('next_page_token')
        if not page_token:
            break
        time.sleep(0.2)  # rate-limit courtesy

    return bars


def load_spy(start: str, end: str, feed: str | None = None) -> list[dict]:
    """Convenience wrapper for SPY benchmark bars."""
    return load_bars('SPY', start, end, resolution='1Day', feed=feed)


def compute_relative_volume(
    symbol: str,
    date_str: str,
    lookback_days: int = 20,
    feed: str | None = None,
) -> float:
    """
    Returns today's pre-market volume (first 30 min) / avg first-30-min vol over lookback.
    Used to build the "stocks in play" universe.
    Returns 0.0 if data unavailable.
    """
    try:
        start = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=lookback_days + 5)).strftime('%Y-%m-%d')
        bars = load_bars(symbol, start, date_str, resolution='1Min', feed=feed)
        if not bars:
            return 0.0

        from collections import defaultdict
        daily_early_vol: dict[str, int] = defaultdict(int)
        for b in bars:
            t = datetime.fromisoformat(b['t'].replace('Z', '+00:00'))
            day = t.strftime('%Y-%m-%d')
            if t.hour == 9 and t.minute < 60:
                daily_early_vol[day] += b['v']

        days = sorted(daily_early_vol.keys())
        if date_str not in daily_early_vol or len(days) < 2:
            return 0.0

        today_vol = daily_early_vol[date_str]
        prior_vols = [daily_early_vol[d] for d in days if d != date_str]
        avg = sum(prior_vols) / len(prior_vols) if prior_vols else 1
        return today_vol / avg if avg > 0 else 0.0
    except Exception:
        return 0.0
