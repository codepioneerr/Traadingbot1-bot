#!/usr/bin/env python3
"""
Download 5-year 1-minute SIP bars for all SP500_STABLE_POOL symbols
that are not yet cached locally. Run this ONCE on your Mac.

Usage:
    cd "Documents/Agentic Workflows/Trading Bot"
    python scripts/download_sp500_pool.py

Requirements:
    - Alpaca SIP subscription (already have credentials in .env)
    - ~15-25 GB free disk space for all 102 symbols
    - ~90-120 minutes runtime (Alpaca rate limits ~200 req/min on basic tier)

What it does:
    1. Loads SP500_STABLE_POOL (102 symbols)
    2. Checks which already have a cached .pkl file
    3. Downloads missing symbols from Alpaca SIP feed (JSON → pkl)
    4. Saves to backtest/cache/ in the same format the backtest engine expects

After running, execute the full 102-symbol backtest:
    python run_backtest_full.py
"""

import os, sys, json, pickle, time, hashlib, requests
from pathlib import Path
from datetime import datetime

# ── Setup ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env
env_path = ROOT / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from backtest.sp500_pool import SP500_STABLE_POOL

CACHE_DIR = ROOT / 'backtest' / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

START = '2021-01-04'
END   = '2026-01-03'
FEED  = 'sip'
RESOLUTION = '1Min'

# ── Alpaca auth ───────────────────────────────────────────────────────────────
API_KEY    = os.environ.get('ALPACA_API_KEY', '')
API_SECRET = os.environ.get('ALPACA_SECRET_KEY', '')
if not API_KEY or not API_SECRET:
    sys.exit('ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env')

HEADERS = {'APCA-API-KEY-ID': API_KEY, 'APCA-API-SECRET-KEY': API_SECRET}
BASE_URL = 'https://data.alpaca.markets/v2/stocks'

# ── Download helpers ──────────────────────────────────────────────────────────

def _cache_path(sym: str) -> Path:
    key = hashlib.md5(f'{sym}{START}{END}{RESOLUTION}{FEED}'.encode()).hexdigest()[:12]
    return CACHE_DIR / f'{sym}_{START}_{END}_{RESOLUTION}_{FEED}_{key}.json'


def _pkl_path(sym: str) -> Path:
    key = hashlib.md5(f'{sym}{START}{END}{RESOLUTION}{FEED}'.encode()).hexdigest()[:12]
    return CACHE_DIR / f'{sym}_{START}_{END}_{RESOLUTION}_{FEED}_{key}.pkl'


def is_cached(sym: str) -> bool:
    return _pkl_path(sym).exists() or _cache_path(sym).exists()


def fetch_bars(sym: str) -> list[dict]:
    """Download all 1-min SIP bars for sym over [START, END]. Returns list of bar dicts."""
    url = f'{BASE_URL}/{sym}/bars'
    bars, page_token = [], None
    while True:
        params = {
            'timeframe': RESOLUTION,
            'start':     f'{START}T00:00:00Z',
            'end':       f'{END}T23:59:59Z',
            'feed':      FEED,
            'limit':     10000,
            'adjustment': 'split',
        }
        if page_token:
            params['page_token'] = page_token
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 429:
            print('  rate-limited — sleeping 60s', flush=True)
            time.sleep(60)
            continue
        resp.raise_for_status()
        data = resp.json()
        for b in data.get('bars', []):
            bars.append({'t': b['t'], 'o': b['o'], 'h': b['h'],
                         'l': b['l'], 'c': b['c'], 'v': b['v'],
                         'vwap': b.get('vw', b['c'])})
        page_token = data.get('next_page_token')
        if not page_token:
            break
        time.sleep(0.25)   # stay under 200 req/min
    return bars


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    missing = [s for s in SP500_STABLE_POOL if not is_cached(s)]
    already = len(SP500_STABLE_POOL) - len(missing)

    print(f'\n{"="*60}')
    print(f'  SP500_STABLE_POOL download')
    print(f'  Total symbols : {len(SP500_STABLE_POOL)}')
    print(f'  Already cached: {already}')
    print(f'  To download   : {len(missing)}')
    print(f'  Window        : {START} → {END}  (1Min SIP)')
    print(f'  Estimated time: ~{len(missing) * 1.5:.0f}–{len(missing) * 2:.0f} min')
    print(f'{"="*60}\n')

    if not missing:
        print('Nothing to download — all symbols already cached.')
        return

    print(f'Missing symbols:\n  {missing}\n')

    errors = []
    t0 = time.time()
    for i, sym in enumerate(missing, 1):
        print(f'[{i:3}/{len(missing)}] {sym}... ', end='', flush=True)
        try:
            bars = fetch_bars(sym)
            pkl  = _pkl_path(sym)
            with open(pkl, 'wb') as f:
                pickle.dump(bars, f, protocol=4)
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(missing) - i)
            print(f'{len(bars):,} bars → pkl  '
                  f'[{elapsed/60:.0f}m elapsed, ~{eta/60:.0f}m remaining]', flush=True)
        except Exception as e:
            print(f'FAILED: {e}', flush=True)
            errors.append((sym, str(e)))
            time.sleep(5)

    print(f'\n{"="*60}')
    print(f'  Download complete in {(time.time()-t0)/60:.1f} min')
    if errors:
        print(f'  Errors ({len(errors)}):')
        for sym, err in errors:
            print(f'    {sym}: {err}')
    else:
        print(f'  All {len(missing)} symbols downloaded successfully.')
    print(f'\n  Next step:')
    print(f'    python run_backtest_full.py')
    print(f'{"="*60}\n')


if __name__ == '__main__':
    main()
