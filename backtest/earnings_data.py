"""
PEAD earnings data pipeline — Yahoo Finance via yfinance.

Downloads and caches historical earnings dates with EPS estimates and actuals
for every symbol in SP500_STABLE_POOL. No API key required.

Run once on your Mac to populate the cache:
    cd "Documents/Agentic Workflows/Trading Bot"
    pip3 install yfinance --break-system-packages
    python3 backtest/earnings_data.py

After that, load_earnings(symbol) works offline from the JSON cache.

Data source:
    yf.Ticker(symbol).get_earnings_dates(limit=40)
    Returns ~10 years of quarterly earnings with EPS Estimate and Reported EPS.

SUE formula:
    SUE = (actual_eps - estimated_eps) / abs(estimated_eps)
    Skipped when abs(estimated_eps) < 0.01 (near-zero estimates are noise).

Entry timing:
    yfinance does not reliably provide BMO/AMC flags. All events are treated
    conservatively as AMC (after-market close) to avoid look-ahead bias:
      - entry_date = 2 trading days after announcement_date
    This means for true BMO events we enter one day late. Acceptable trade-off.
"""

from __future__ import annotations
import sys, os, json, time, warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.parent
CACHE_DIR = Path(__file__).parent / 'cache' / 'earnings'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_START = '2021-01-01'
WINDOW_END   = '2027-12-31'   # open-ended: accept any date yfinance returns

# ── Core helpers ──────────────────────────────────────────────────────────────

def compute_sue(actual: float, estimated: float) -> Optional[float]:
    """
    SUE = (actual - estimated) / abs(estimated).
    Returns None when estimated is near-zero (avoids dividing by noise).
    """
    if abs(estimated) < 0.01:
        return None
    return (actual - estimated) / abs(estimated)


def _next_trading_day(date_str: str, offset: int = 1) -> str:
    """Advance date_str by `offset` weekdays (Mon–Fri). Not holiday-aware."""
    d = datetime.strptime(date_str, '%Y-%m-%d')
    added = 0
    while added < offset:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d.strftime('%Y-%m-%d')


def entry_date_for(announcement_date: str, timing: str = 'unknown') -> str:
    """
    Returns the PEAD entry date (open of first tradeable day after price reaction).

    BMO  → market reacts on announcement_date; entry = +1 trading day
    AMC  → market reacts on announcement_date+1; entry = +2 trading days
    unknown → conservative: treat as AMC
    """
    offset = 1 if timing == 'bmo' else 2
    return _next_trading_day(announcement_date, offset)


# ── yfinance fetcher ──────────────────────────────────────────────────────────

def _fetch_from_yfinance(symbol: str, limit: int = 48,
                         debug: bool = False) -> list[dict]:
    """
    Download earnings dates for symbol via yfinance.
    Tries get_earnings_dates() first, then the earnings_dates property as backup.
    Returns list of raw event dicts (pre-filter, pre-SUE).

    Note: Yahoo Finance only retains consensus estimates for recent quarters
    (~8–12 quarters back from today). Events older than ~3 years will have
    NaN for 'EPS Estimate', so they are skipped. If the backtest window
    pre-dates available estimate data, SUE will be None for those events
    (they contribute to 'no estimate (skip)' in the summary).
    """
    import yfinance as yf
    import math
    warnings.filterwarnings('ignore')

    ticker = yf.Ticker(symbol)
    df = None

    # Attempt 1: get_earnings_dates method (newer yfinance)
    try:
        df = ticker.get_earnings_dates(limit=limit)
    except Exception as e:
        if debug:
            print(f'    get_earnings_dates failed: {e}')

    # Attempt 2: earnings_dates property (older yfinance or different codepath)
    if df is None or df.empty:
        try:
            df = ticker.earnings_dates
        except Exception as e:
            if debug:
                print(f'    earnings_dates property failed: {e}')

    if df is None or df.empty:
        if debug:
            print(f'    [{symbol}] no DataFrame returned from any method')
        return []

    if debug:
        print(f'    [{symbol}] raw DataFrame: {df.shape[0]} rows, '
              f'cols={list(df.columns)}, '
              f'index range: {df.index.min()} → {df.index.max()}')
        print(f'    Non-null EPS Estimate: '
              f'{df["EPS Estimate"].notna().sum() if "EPS Estimate" in df.columns else "col missing"}')
        print(f'    Non-null Reported EPS: '
              f'{df["Reported EPS"].notna().sum() if "Reported EPS" in df.columns else "col missing"}')

    events = []
    for ts, row in df.iterrows():
        try:
            date_str = ts.strftime('%Y-%m-%d')
        except Exception:
            continue

        est_raw = row.get('EPS Estimate')
        act_raw = row.get('Reported EPS')

        # Skip rows missing both values (usually future scheduled dates)
        if act_raw is None and est_raw is None:
            continue
        try:
            est_f = float(est_raw) if est_raw is not None else float('nan')
            act_f = float(act_raw) if act_raw is not None else float('nan')
        except (TypeError, ValueError):
            continue

        # Skip if actual is NaN (future / not yet reported)
        if math.isnan(act_f):
            continue

        # estimate NaN → we still record the event; SUE will be None
        events.append({
            'date':     date_str,
            'actual':   act_f,
            'estimate': est_f,     # may be NaN; handled in _process_events
        })

    if debug:
        print(f'    [{symbol}] events after NaN filter: {len(events)} '
              f'(with estimate: {sum(1 for e in events if not math.isnan(e["estimate"]))})')

    return events


def _process_events(symbol: str, raw: list[dict]) -> list[dict]:
    """
    Apply window filter and compute SUE. Returns clean event list.
    Events with NaN estimates are kept with sue=None (recorded, not traded).
    """
    import math
    events = []
    for row in raw:
        d = row['date']
        if d < WINDOW_START or d > WINDOW_END:
            continue
        act  = row['actual']
        est  = row['estimate']
        sue  = None if math.isnan(est) else compute_sue(act, est)
        events.append({
            'symbol':        symbol,
            'date':          d,
            'actual_eps':    act,
            'estimated_eps': None if math.isnan(est) else est,
            'sue':           sue,
            'timing':        'unknown',   # yfinance does not provide BMO/AMC
            'entry_date':    entry_date_for(d, 'unknown'),
        })
    return sorted(events, key=lambda e: e['date'])


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_earnings(symbol: str, use_cache: bool = True) -> list[dict]:
    """
    Fetch earnings for symbol (from cache if available).
    Saves to backtest/cache/earnings/{symbol}.json.
    """
    cache_path = CACHE_DIR / f'{symbol}.json'

    if use_cache and cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    raw    = _fetch_from_yfinance(symbol)
    events = _process_events(symbol, raw)

    with open(cache_path, 'w') as f:
        json.dump(events, f, indent=2)

    return events


def load_earnings(symbol: str) -> list[dict]:
    """Load cached earnings events for one symbol."""
    p = CACHE_DIR / f'{symbol}.json'
    if not p.exists():
        raise FileNotFoundError(
            f'No cache for {symbol}. Run:  python3 backtest/earnings_data.py'
        )
    with open(p) as f:
        return json.load(f)


def load_all_earnings(pool: list[str] | None = None) -> dict[str, list[dict]]:
    """Load all cached earnings. Returns {symbol: [events]}."""
    if pool is None:
        sys.path.insert(0, str(ROOT))
        from backtest.sp500_pool import SP500_STABLE_POOL
        pool = SP500_STABLE_POOL
    result = {}
    for sym in pool:
        try:
            result[sym] = load_earnings(sym)
        except FileNotFoundError:
            pass
    return result


# ── Download + summary ────────────────────────────────────────────────────────

def download_all(pool: list[str] | None = None,
                 sleep_sec: float = 0.25,
                 refresh: bool = False) -> None:
    """
    Download earnings for all pool symbols and print the summary.
    Skips symbols that are already cached (unless refresh=True).
    """
    sys.path.insert(0, str(ROOT))
    from backtest.sp500_pool import SP500_STABLE_POOL
    from collections import Counter

    if pool is None:
        pool = SP500_STABLE_POOL

    print(f'\n{"="*62}')
    print(f'  PEAD Earnings Data — yfinance')
    print(f'  Symbols: {len(pool)}  |  Window: {WINDOW_START} → {WINDOW_END}')
    print(f'  Cache: backtest/cache/earnings/')
    print(f'{"="*62}\n')

    all_events: dict[str, list[dict]] = {}
    errors: list[tuple[str, str]] = []
    t0 = time.time()

    for i, sym in enumerate(pool, 1):
        cache_path = CACHE_DIR / f'{sym}.json'
        already    = cache_path.exists() and not refresh

        if already:
            try:
                events = load_earnings(sym)
                all_events[sym] = events
                # brief one-liner for cached symbols
                beats  = sum(1 for e in events if e['sue'] is not None and e['sue'] >= 0.05)
                misses = sum(1 for e in events if e['sue'] is not None and e['sue'] <= -0.05)
                dates  = [e['date'] for e in events]
                dr     = f"{min(dates)[:7]} → {max(dates)[:7]}" if dates else 'no data'
                print(f'  [{i:3}/{len(pool)}] {sym:<7}  [cache] '
                      f'{len(events):3} events  {dr}  '
                      f'beats={beats} misses={misses}', flush=True)
                continue
            except Exception as e:
                print(f'  [{i:3}/{len(pool)}] {sym:<7}  cache error: {e}', flush=True)

        try:
            events = fetch_earnings(sym, use_cache=False)
            all_events[sym] = events
            beats  = sum(1 for e in events if e['sue'] is not None and e['sue'] >= 0.05)
            misses = sum(1 for e in events if e['sue'] is not None and e['sue'] <= -0.05)
            dates  = [e['date'] for e in events]
            dr     = f"{min(dates)[:7]} → {max(dates)[:7]}" if dates else 'no data'
            print(f'  [{i:3}/{len(pool)}] {sym:<7}  [fetch] '
                  f'{len(events):3} events  {dr}  '
                  f'beats={beats} misses={misses}', flush=True)
            time.sleep(sleep_sec)
        except Exception as e:
            errors.append((sym, str(e)))
            print(f'  [{i:3}/{len(pool)}] {sym:<7}  FAILED: {e}', flush=True)

    elapsed = time.time() - t0

    # ── Aggregate summary ─────────────────────────────────────────────────────
    total_ev  = sum(len(v) for v in all_events.values())
    total_b   = sum(1 for evs in all_events.values()
                    for e in evs if e['sue'] is not None and e['sue'] >= 0.05)
    total_m   = sum(1 for evs in all_events.values()
                    for e in evs if e['sue'] is not None and e['sue'] <= -0.05)
    total_mid = sum(1 for evs in all_events.values()
                    for e in evs
                    if e['sue'] is not None and -0.05 < e['sue'] < 0.05)
    total_skip= sum(1 for evs in all_events.values()
                    for e in evs if e['sue'] is None)

    year_beats  = Counter()
    year_misses = Counter()
    year_total  = Counter()
    for evs in all_events.values():
        for e in evs:
            y = e['date'][:4]
            year_total[y] += 1
            if e['sue'] is None: continue
            if e['sue'] >= 0.05:  year_beats[y]  += 1
            if e['sue'] <= -0.05: year_misses[y] += 1

    all_years = sorted(set(list(year_beats) + list(year_misses) + list(year_total)))

    print(f'\n{"="*62}')
    print(f'  SUMMARY')
    print(f'{"="*62}')
    print(f'  Symbols with data     : {len(all_events)} / {len(pool)}')
    print(f'  Total earnings events : {total_ev}')
    print(f'  Avg events / symbol   : {total_ev / max(len(all_events), 1):.1f}')
    print(f'  SUE ≥ +0.05  (beats)  : {total_b}  ({total_b/max(total_ev,1):.0%})')
    print(f'  SUE ≤ −0.05  (misses) : {total_m}  ({total_m/max(total_ev,1):.0%})')
    print(f'  |SUE| < 0.05 (no sig) : {total_mid}  ({total_mid/max(total_ev,1):.0%})')
    print(f'  No estimate  (skip)   : {total_skip}')
    print(f'  Runtime               : {elapsed:.1f}s')

    print(f'\n  Year-by-year  (2021–2025 backtest window)')
    print(f'  {"Year":<6} {"Events":>7} {"Beats":>7} {"Misses":>7} '
          f'{"Beat%":>7} {"Signals":>8}')
    print(f'  {"─"*50}')
    for y in [str(yr) for yr in range(2021, 2026)]:
        ev = year_total.get(y, 0)
        b  = year_beats.get(y, 0)
        m  = year_misses.get(y, 0)
        bp = f'{b/ev:.0%}' if ev else '—'
        print(f'  {y:<6} {ev:>7} {b:>7} {m:>7} {bp:>7} {b+m:>8}')
    print(f'  {"─"*50}')
    tot5 = sum(year_total.get(str(y),0) for y in range(2021,2026))
    b5   = sum(year_beats.get(str(y),0)  for y in range(2021,2026))
    m5   = sum(year_misses.get(str(y),0) for y in range(2021,2026))
    print(f'  {"5yr":<6} {tot5:>7} {b5:>7} {m5:>7} '
          f'{b5/max(tot5,1):>7.0%} {b5+m5:>8}')

    if errors:
        print(f'\n  Errors ({len(errors)}):')
        for sym, msg in errors:
            print(f'    {sym}: {msg}')

    print(f'\n{"="*62}\n')


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(
        description='Download yfinance earnings data for PEAD backtest.')
    ap.add_argument('--symbols', nargs='+', metavar='SYM',
                    help='Subset of symbols (default: full SP500_STABLE_POOL)')
    ap.add_argument('--refresh', action='store_true',
                    help='Re-download even if already cached')
    ap.add_argument('--summary-only', action='store_true',
                    help='Print summary from existing cache, no downloads')
    ap.add_argument('--diagnose', metavar='SYM',
                    help='Print raw yfinance output for one symbol and exit')
    args = ap.parse_args()

    if args.diagnose:
        sym = args.diagnose.upper()
        print(f'\nDiagnosing yfinance data for {sym}...\n')
        raw = _fetch_from_yfinance(sym, limit=48, debug=True)
        print(f'\nRaw events returned (before window filter): {len(raw)}')
        for e in raw[:10]:
            print(f'  {e}')
        if len(raw) > 10:
            print(f'  ... ({len(raw)-10} more)')
        filtered = _process_events(sym, raw)
        print(f'\nAfter window filter ({WINDOW_START}→{WINDOW_END}): {len(filtered)} events')
        for e in filtered:
            print(f'  {e["date"]}  actual={e["actual_eps"]}  '
                  f'est={e["estimated_eps"]}  sue={e["sue"]}')

    elif args.summary_only:
        sys.path.insert(0, str(ROOT))
        from backtest.sp500_pool import SP500_STABLE_POOL
        pool = args.symbols or SP500_STABLE_POOL
        all_ev = {}
        for sym in pool:
            try: all_ev[sym] = load_earnings(sym)
            except FileNotFoundError: pass
        total = sum(len(v) for v in all_ev.values())
        beats = sum(1 for evs in all_ev.values()
                    for e in evs if e.get('sue') is not None and e['sue'] >= 0.05)
        misses= sum(1 for evs in all_ev.values()
                    for e in evs if e.get('sue') is not None and e['sue'] <= -0.05)
        print(f'{len(all_ev)} symbols cached | {total} total events | '
              f'{beats} beats | {misses} misses')
    else:
        download_all(pool=args.symbols, refresh=args.refresh)
