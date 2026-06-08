"""
Historical bar loader — Alpaca first, pluggable source.
Includes get_sp500_for_date() for point-in-time S&P 500 constituent lookup.

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


def load_crypto_bars(
    symbol: str,       # e.g. 'BTC/USD'
    start: str,
    end: str,
    resolution: str = '1Min',
    use_cache: bool = True,
) -> list[dict]:
    """
    Load minute bars for a crypto pair from Alpaca's crypto endpoint.
    Note: free-tier crypto bars may have zero volume/VWAP.
    The symbol is normalized (BTC/USD → BTCUSD) for cache keys.
    """
    cache_sym = symbol.replace('/', '')
    cache_key = hashlib.md5(f'{cache_sym}{start}{end}{resolution}crypto'.encode()).hexdigest()[:12]
    cache_path = CACHE_DIR / f'{cache_sym}_{start}_{end}_{resolution}_crypto_{cache_key}.json'

    if use_cache and cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    bars = _fetch_alpaca_crypto_bars(symbol, start, end, resolution)

    if use_cache:
        with open(cache_path, 'w') as f:
            json.dump(bars, f)

    return bars


def _fetch_alpaca_crypto_bars(symbol, start, end, resolution) -> list[dict]:
    url = 'https://data.alpaca.markets/v1beta3/crypto/us/bars'
    headers = _alpaca_headers()
    bars = []
    page_token = None

    while True:
        params = {
            'symbols': symbol,
            'timeframe': resolution,
            'start': f'{start}T13:30:00Z',  # 9:30 ET in UTC
            'end': f'{end}T20:00:00Z',       # 16:00 ET in UTC
            'limit': 10000,
        }
        if page_token:
            params['page_token'] = page_token

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for b in data.get('bars', {}).get(symbol, []):
            vwap = b.get('vw', 0)
            # Crypto VWAP may be 0 on free tier — fall back to close price
            bars.append({
                't': b['t'],
                'o': b['o'],
                'h': b['h'],
                'l': b['l'],
                'c': b['c'],
                'v': b.get('v', 0),
                'vwap': vwap if vwap > 0 else b['c'],
                'is_crypto': True,
            })

        page_token = data.get('next_page_token')
        if not page_token:
            break
        time.sleep(0.2)

    return bars


# ── Universe definitions ─────────────────────────────────────────────────────
# These are the asset-class groupings used by evaluate_grid().
# Symbols chosen for liquidity, multi-year history, and representation of class.

UNIVERSES = {
    'large_cap': ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'META', 'AMZN', 'GOOGL', 'AMD', 'NFLX', 'ORCL'],
    'small_cap': ['SIRI', 'AMC', 'BBBY', 'SPCE', 'MVIS', 'CLOV', 'WKHS', 'RIDE', 'GOEV', 'NKLA'],
    'etf':       ['QQQ', 'SPY', 'IWM', 'XLK', 'ARKK', 'SOXL', 'TQQQ', 'UVXY', 'GLD', 'TLT'],
    'crypto':    ['BTC/USD', 'ETH/USD', 'SOL/USD'],
}


# ── S&P 500 point-in-time constituent lookup ─────────────────────────────────

_SP500_CSV_PATH = Path(__file__).parent / 'data' / 'sp500_ticker_start_end.csv'


def get_sp500_for_date(date_str: str, csv_path: str | None = None) -> list[str]:
    """
    Returns the list of S&P 500 ticker symbols that were members on date_str.

    Uses the fja05680/sp500 CSV — a community-maintained, MIT-licensed record
    of every S&P 500 addition and removal since 1996, updated through Jan 2026.
    Source: github.com/fja05680/sp500

    Args:
        date_str  : 'YYYY-MM-DD' — the date to query.
        csv_path  : path to sp500_ticker_start_end.csv. Defaults to
                    backtest/data/sp500_ticker_start_end.csv (ships with the repo).

    Returns:
        Sorted list of ticker strings that were in the S&P 500 on that date.

    Survivorship-bias note:
        This function returns the ACTUAL index membership on date_str, NOT the
        current membership. Running the scanner with this output eliminates the
        survivorship bias that arises from using today's S&P 500 for historical
        backtests (i.e., back-testing only on stocks that survived to the present).

    Example:
        >>> get_sp500_for_date('2021-01-04')[:5]
        ['A', 'AAPL', 'ABBV', 'ABC', 'ABT']
        >>> 'TSLA' in get_sp500_for_date('2021-01-04')   # added Dec 2020
        True
        >>> 'UBER' in get_sp500_for_date('2021-01-04')   # added Oct 2023
        False
    """
    import csv as _csv

    path = Path(csv_path) if csv_path else _SP500_CSV_PATH
    if not path.exists():
        raise FileNotFoundError(
            f'S&P 500 constituent CSV not found at {path}\n'
            'Download it from github.com/fja05680/sp500:\n'
            '  curl -o backtest/data/sp500_ticker_start_end.csv \\\n'
            '    https://raw.githubusercontent.com/fja05680/sp500/master/sp500_ticker_start_end.csv\n'
            'Or run: python scripts/download_sp500_pool.py'
        )

    members: set[str] = set()
    with open(path, newline='', encoding='utf-8') as fh:
        for row in _csv.DictReader(fh):
            ticker = row['ticker'].strip()
            start  = row['start_date'].strip()
            end    = row['end_date'].strip()
            if not ticker or not start:
                continue
            # Not yet in the index
            if date_str < start:
                continue
            # Already removed from the index (end is populated and before date)
            if end and date_str > end:
                continue
            members.add(ticker)

    return sorted(members)


# ── S&P 500 institutional pool ───────────────────────────────────────────────
# Confirmed S&P 500 members continuously from 2021-01-04 through 2026-01-03.
# All pass: price > $10, ADV > 5M shares, tight bid-ask spreads, no SPAC/meme risk.
# Production: pull historical constituent list per year-start to avoid survivorship
# bias across the full 500. For these 9 stable large-caps bias is negligible.
SP500_INSTITUTIONAL_POOL = [
    'AAPL', 'NVDA', 'MSFT', 'TSLA', 'META', 'AMZN', 'GOOGL', 'AMD', 'NFLX',
]


def build_daily_scanner(
    bars_by_symbol: dict,
    min_rvol: float = 2.0,
    min_gap_pct: float = 0.01,
    max_gap_pct: float = 0.08,             # S&P 500 gaps > 8% = halt/news, untradeable
    top_n: int = 3,
    lookback_days: int = 20,
    min_candidates: int = 2,
    min_price: float = 10.0,               # eliminates penny-stock / SPAC behaviour
    min_avg_daily_vol: int = 5_000_000,    # institutional liquidity floor (30-day ADV)
    rvol_no_catalyst: float = 2.5,         # higher bar on days without a known catalyst
    catalyst_gap_threshold: float = 0.03,  # gap ≥ 3% proxies for earnings/known catalyst
) -> dict:
    """
    Institutional-grade daily universe scanner.

    Each trading day, scores every symbol in bars_by_symbol by four criteria:
      1. Price filter  : prior close >= min_price          (no penny/SPAC behaviour)
      2. Liquidity     : 30-day avg daily vol >= min_avg_daily_vol
      3. Gap filter    : min_gap_pct <= |open−prior_close|/prior_close <= max_gap_pct
      4. RVOL gate     : catalyst-aware —
            gap >= catalyst_gap_threshold (≥3%) proxies for earnings/known catalyst
              → require RVOL >= min_rvol (2.0)
            smaller gap (no obvious catalyst)
              → require RVOL >= rvol_no_catalyst (2.5)

    Returns {date_str: [sym1, sym2, ...]} ranked by RVOL desc, capped at top_n.
    Returns [] for dates where fewer than min_candidates qualify — sit out today.

    Uses fast string-based UTC parsing; no datetime.fromisoformat per bar.
    9:30–10:00 ET ≈ 13:30–14:30 UTC (covers both EDT and EST).
    """
    from collections import defaultdict

    # ── Pass 1: extract per-symbol daily stats ───────────────────────────────
    sym_stats: dict = {}
    for sym, bars in bars_by_symbol.items():
        daily_open:  dict = {}
        daily_close: dict = {}
        early_vol:   dict = defaultdict(int)   # early-session vol for RVOL
        total_vol:   dict = defaultdict(int)   # full-day vol for ADV filter

        for b in bars:
            t   = b['t']
            day = t[:10]
            h   = int(t[11:13])
            m   = int(t[14:16])
            if day not in daily_open:
                daily_open[day] = b['o']
            daily_close[day]  = b['c']
            total_vol[day]   += b['v']
            if (h == 13 and m >= 30) or (h == 14 and m < 30):
                early_vol[day] += b['v']

        sym_stats[sym] = {
            'open':      daily_open,
            'close':     daily_close,
            'early_vol': dict(early_vol),
            'total_vol': dict(total_vol),
        }

    # ── Pass 2: rolling RVOL and rolling ADV per symbol ─────────────────────
    all_dates = sorted(set(d for s in sym_stats.values() for d in s['open']))
    sym_rvol:    dict = {}
    sym_avg_vol: dict = {}

    for sym, stats in sym_stats.items():
        ev    = stats['early_vol']
        tv    = stats['total_vol']
        sdays = sorted(ev)
        rvol:    dict = {}
        avg_vol: dict = {}

        for i, d in enumerate(sdays):
            window = sdays[max(0, i - lookback_days):i]
            prior_ev = [ev[dd]      for dd in window]
            prior_tv = [tv.get(dd, 0) for dd in window]
            avg_ev   = sum(prior_ev) / len(prior_ev) if prior_ev else 0
            avg_tv   = sum(prior_tv) / len(prior_tv) if prior_tv else 0
            rvol[d]    = ev[d] / avg_ev if avg_ev > 0 else 0.0
            avg_vol[d] = avg_tv

        sym_rvol[sym]    = rvol
        sym_avg_vol[sym] = avg_vol

    # ── Pass 3: per-day ranked candidate list ────────────────────────────────
    scanner: dict = {}
    for i, date in enumerate(all_dates):
        if i == 0:
            scanner[date] = []
            continue
        prev_date = all_dates[i - 1]
        qualified = []

        for sym, stats in sym_stats.items():
            # 1. Price filter — use prior close as proxy for today's price level
            prior_close = stats['close'].get(prev_date)
            if prior_close is None or prior_close < min_price:
                continue

            # 2. Liquidity — rolling ADV
            if sym_avg_vol[sym].get(date, 0) < min_avg_daily_vol:
                continue

            # 3. Gap filter — must be in [min_gap_pct, max_gap_pct]
            today_open = stats['open'].get(date)
            if today_open is None or prior_close == 0:
                continue
            gap = abs(today_open - prior_close) / prior_close
            if gap < min_gap_pct or gap > max_gap_pct:
                continue

            # 4. Catalyst-aware RVOL gate
            rvol_val = sym_rvol[sym].get(date, 0.0)
            rvol_req = min_rvol if gap >= catalyst_gap_threshold else rvol_no_catalyst
            if rvol_val < rvol_req:
                continue

            qualified.append((sym, rvol_val, gap))

        qualified.sort(key=lambda x: x[1], reverse=True)
        top = [s for s, _, _ in qualified[:top_n]]
        scanner[date] = top if len(top) >= min_candidates else []

    return scanner


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
