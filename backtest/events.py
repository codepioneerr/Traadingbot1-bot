"""
Event-day classification for backtest trade splitting.

Two event types:
  Earnings day  : day of or after a company's earnings release
  Macro day     : FOMC decision / CPI release / NFP release

Detection methods:
  Earnings — two layers, both cached:
    1. Gap detection (bar data only): open vs prior close > GAP_THRESHOLD.
       Fast, no API calls, works for any symbol.
    2. Alpaca news scan: checks for earnings keywords in headlines.
       More precise but costs API calls; results cached to disk.

  Macro — hardcoded calendar for 2021-2026 (Fed/BLS dates are public and fixed).
    Covers FOMC rate decisions, CPI releases, and NFP releases.

Usage:
    from backtest.events import build_event_map, split_trades_by_event
    event_map = build_event_map(bars_by_symbol, start, end)
    buckets = split_trades_by_event(trades, event_map)
"""
from __future__ import annotations
import json
import os
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

# Gap threshold: open deviates from prior close by this fraction → flag as gap day
GAP_THRESHOLD = 0.02   # 2%

# ── Hardcoded macro calendar 2021-2026 ───────────────────────────────────────
# Sources: federalreserve.gov (FOMC), bls.gov (CPI/NFP)
# Format: 'YYYY-MM-DD'

FOMC_DATES = {
    # 2021
    '2021-01-27', '2021-03-17', '2021-04-28', '2021-06-16',
    '2021-07-28', '2021-09-22', '2021-11-03', '2021-12-15',
    # 2022
    '2022-01-26', '2022-03-16', '2022-05-04', '2022-06-15',
    '2022-07-27', '2022-09-21', '2022-11-02', '2022-12-14',
    # 2023
    '2023-02-01', '2023-03-22', '2023-05-03', '2023-06-14',
    '2023-07-26', '2023-09-20', '2023-11-01', '2023-12-13',
    # 2024
    '2024-01-31', '2024-03-20', '2024-05-01', '2024-06-12',
    '2024-07-31', '2024-09-18', '2024-11-07', '2024-12-18',
    # 2025
    '2025-01-29', '2025-03-19', '2025-05-07', '2025-06-18',
    '2025-07-30', '2025-09-17', '2025-10-29', '2025-12-10',
}

CPI_DATES = {
    # 2021
    '2021-01-13', '2021-02-10', '2021-03-10', '2021-04-13',
    '2021-05-12', '2021-06-10', '2021-07-13', '2021-08-11',
    '2021-09-14', '2021-10-13', '2021-11-10', '2021-12-10',
    # 2022
    '2022-01-12', '2022-02-10', '2022-03-10', '2022-04-12',
    '2022-05-11', '2022-06-10', '2022-07-13', '2022-08-10',
    '2022-09-13', '2022-10-13', '2022-11-10', '2022-12-13',
    # 2023
    '2023-01-12', '2023-02-14', '2023-03-14', '2023-04-12',
    '2023-05-10', '2023-06-13', '2023-07-12', '2023-08-10',
    '2023-09-13', '2023-10-12', '2023-11-14', '2023-12-12',
    # 2024
    '2024-01-11', '2024-02-13', '2024-03-12', '2024-04-10',
    '2024-05-15', '2024-06-12', '2024-07-11', '2024-08-14',
    '2024-09-11', '2024-10-10', '2024-11-13', '2024-12-11',
    # 2025
    '2025-01-15', '2025-02-12', '2025-03-12', '2025-04-10',
    '2025-05-13', '2025-06-11', '2025-07-11', '2025-08-12',
    '2025-09-10', '2025-10-15', '2025-11-12', '2025-12-10',
}

NFP_DATES = {
    # NFP = first Friday of each month (employment situation report)
    # 2021
    '2021-01-08', '2021-02-05', '2021-03-05', '2021-04-02',
    '2021-05-07', '2021-06-04', '2021-07-02', '2021-08-06',
    '2021-09-03', '2021-10-08', '2021-11-05', '2021-12-03',
    # 2022
    '2022-01-07', '2022-02-04', '2022-03-04', '2022-04-01',
    '2022-05-06', '2022-06-03', '2022-07-08', '2022-08-05',
    '2022-09-02', '2022-10-07', '2022-11-04', '2022-12-02',
    # 2023
    '2023-01-06', '2023-02-03', '2023-03-10', '2023-04-07',
    '2023-05-05', '2023-06-02', '2023-07-07', '2023-08-04',
    '2023-09-01', '2023-10-06', '2023-11-03', '2023-12-08',
    # 2024
    '2024-01-05', '2024-02-02', '2024-03-08', '2024-04-05',
    '2024-05-03', '2024-06-07', '2024-07-05', '2024-08-02',
    '2024-09-06', '2024-10-04', '2024-11-01', '2024-12-06',
    # 2025
    '2025-01-10', '2025-02-07', '2025-03-07', '2025-04-04',
    '2025-05-02', '2025-06-06', '2025-07-03', '2025-08-01',
    '2025-09-05', '2025-10-03', '2025-11-07', '2025-12-05',
}

MACRO_DATES: dict[str, str] = {}   # date → 'fomc' | 'cpi' | 'nfp' (first match wins)
for d in FOMC_DATES:
    MACRO_DATES[d] = 'fomc'
for d in CPI_DATES:
    if d not in MACRO_DATES:
        MACRO_DATES[d] = 'cpi'
for d in NFP_DATES:
    if d not in MACRO_DATES:
        MACRO_DATES[d] = 'nfp'

# Days where two macro events coincide get a combined label
for d in FOMC_DATES:
    if d in CPI_DATES:
        MACRO_DATES[d] = 'fomc+cpi'


# ── Gap detection ─────────────────────────────────────────────────────────────

def detect_gap_days(
    bars_by_symbol: dict,
    threshold: float = GAP_THRESHOLD,
) -> dict[str, dict[str, float]]:
    """
    Returns {symbol: {date_str: gap_pct}} for days where
    abs(open - prior_close) / prior_close >= threshold.
    """
    def bar_date(b) -> str:
        t = b['t']
        return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')

    result: dict[str, dict[str, float]] = {}

    for symbol, bars in bars_by_symbol.items():
        # Group by date, keep only first bar of each day
        daily_first: dict[str, dict] = {}
        daily_last: dict[str, float] = {}

        for b in bars:
            d = bar_date(b)
            if d not in daily_first:
                daily_first[d] = b
            daily_last[d] = b['c']

        days = sorted(daily_first.keys())
        gaps: dict[str, float] = {}

        for i in range(1, len(days)):
            today = days[i]
            yesterday = days[i - 1]
            prior_close = daily_last.get(yesterday, 0)
            today_open = daily_first[today]['o']
            if prior_close > 0:
                gap = (today_open - prior_close) / prior_close
                if abs(gap) >= threshold:
                    gaps[today] = round(gap, 4)

        result[symbol] = gaps

    return result


# ── Alpaca news-based earnings detection ─────────────────────────────────────

EARNINGS_KEYWORDS = ('adj eps', 'earnings per share', 'eps beats', 'eps misses',
                     'quarterly results', 'q1 ', 'q2 ', 'q3 ', 'q4 ',
                     'net sales', 'revenue beats', 'quarterly earnings')


def _alpaca_headers() -> dict:
    key = os.environ.get('ALPACA_API_KEY', '')
    secret = os.environ.get('ALPACA_SECRET_KEY', '')
    if not key or not secret:
        return {}
    return {'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret}


def _is_earnings_headline(headline: str) -> bool:
    h = headline.lower()
    return any(kw in h for kw in EARNINGS_KEYWORDS)


def fetch_earnings_dates_from_news(
    symbol: str,
    start: str,
    end: str,
    use_cache: bool = True,
) -> set[str]:
    """
    Scans Alpaca news for a symbol, returns dates where earnings headlines appear.
    Results cached to disk.
    """
    cache_key = hashlib.md5(f'earnings_{symbol}_{start}_{end}'.encode()).hexdigest()[:10]
    cache_path = CACHE_DIR / f'earnings_{symbol}_{cache_key}.json'

    if use_cache and cache_path.exists():
        with open(cache_path) as f:
            return set(json.load(f))

    headers = _alpaca_headers()
    if not headers:
        return set()

    earnings_dates: set[str] = set()
    url = 'https://data.alpaca.markets/v1beta1/news'
    page_token = None

    try:
        while True:
            params = {
                'symbols': symbol,
                'start': f'{start}T00:00:00Z',
                'end': f'{end}T23:59:59Z',
                'limit': 50,
                'sort': 'asc',
            }
            if page_token:
                params['page_token'] = page_token

            r = requests.get(url, headers=headers, params=params, timeout=15)
            if r.status_code != 200:
                break

            data = r.json()
            for article in data.get('news', []):
                headline = article.get('headline', '')
                if _is_earnings_headline(headline):
                    created = article.get('created_at', '')[:10]
                    if created:
                        earnings_dates.add(created)

            page_token = data.get('next_page_token')
            if not page_token:
                break

    except Exception:
        pass

    if use_cache:
        with open(cache_path, 'w') as f:
            json.dump(sorted(earnings_dates), f)

    return earnings_dates


# ── Event map builder ─────────────────────────────────────────────────────────

def build_event_map(
    bars_by_symbol: dict,
    start: str,
    end: str,
    gap_threshold: float = GAP_THRESHOLD,
    use_news: bool = True,
) -> dict[str, dict]:
    """
    Returns {date_str: {
        'macro': 'fomc'|'cpi'|'nfp'|'fomc+cpi'|None,
        'earnings_symbols': [list of syms with earnings this day],
        'gap_symbols': {symbol: gap_pct},
        'is_macro': bool,
        'is_earnings': bool,   # gap OR news confirmation
    }}
    """
    event_map: dict[str, dict] = {}

    # 1. Gap detection (from bar data — no API cost)
    gap_days = detect_gap_days(bars_by_symbol, threshold=gap_threshold)

    # 2. News-based earnings (optional, with caching)
    news_earnings: dict[str, set[str]] = {}
    if use_news:
        symbols = list(bars_by_symbol.keys())
        # Only fetch for non-crypto (crypto news isn't useful for earnings)
        stock_syms = [s for s in symbols if '/' not in s]
        for sym in stock_syms:
            dates = fetch_earnings_dates_from_news(sym, start, end)
            news_earnings[sym] = dates

    # 3. Collect all dates
    all_dates: set[str] = set()
    for bars in bars_by_symbol.values():
        for b in bars:
            t = b['t']
            d = t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
            all_dates.add(d)

    for date_str in all_dates:
        macro_type = MACRO_DATES.get(date_str)

        # Gap symbols on this date
        gap_on_date = {
            sym: gaps[date_str]
            for sym, gaps in gap_days.items()
            if date_str in gaps
        }

        # Earnings symbols on this date (news OR gap > 4%)
        earnings_syms = []
        for sym, dates in news_earnings.items():
            if date_str in dates:
                earnings_syms.append(sym)

        # Also flag big gap (>4%) as earnings proxy even without news confirmation
        for sym, gap_pct in gap_on_date.items():
            if abs(gap_pct) >= 0.04 and sym not in earnings_syms:
                earnings_syms.append(sym)

        event_map[date_str] = {
            'macro': macro_type,
            'earnings_symbols': earnings_syms,
            'gap_symbols': gap_on_date,
            'is_macro': macro_type is not None,
            'is_earnings': len(earnings_syms) > 0,
        }

    return event_map


# ── Trade splitter ────────────────────────────────────────────────────────────

def classify_trade(trade: dict, event_map: dict) -> str:
    """
    Returns one of:
      'earnings_gap_up'   — entry on earnings day with positive gap
      'earnings_gap_down' — entry on earnings day with negative gap
      'earnings_flat'     — earnings day, gap below 2%
      'macro_fomc'        — FOMC decision day
      'macro_cpi'         — CPI release day
      'macro_nfp'         — NFP release day
      'macro_other'       — other macro event
      'normal'            — none of the above
    """
    entry_time = trade.get('entry_time', '')
    date_str = entry_time[:10] if entry_time else ''
    symbol = trade.get('symbol', '')

    ev = event_map.get(date_str, {})
    macro = ev.get('macro')
    earnings_syms = ev.get('earnings_symbols', [])
    gap_syms = ev.get('gap_symbols', {})

    # Macro takes priority over earnings label
    if macro:
        if 'fomc' in macro:
            return 'macro_fomc'
        if macro == 'cpi':
            return 'macro_cpi'
        if macro == 'nfp':
            return 'macro_nfp'
        return 'macro_other'

    if symbol in earnings_syms:
        gap = gap_syms.get(symbol, 0.0)
        if gap >= GAP_THRESHOLD:
            return 'earnings_gap_up'
        elif gap <= -GAP_THRESHOLD:
            return 'earnings_gap_down'
        else:
            return 'earnings_flat'

    return 'normal'


def split_trades_by_event(
    trades: list[dict],
    event_map: dict,
) -> dict[str, list[dict]]:
    """
    Returns {event_type: [trades]} for all 8 categories.
    """
    buckets: dict[str, list[dict]] = {}
    for trade in trades:
        label = classify_trade(trade, event_map)
        buckets.setdefault(label, []).append(trade)
    return buckets


# ── Print table ───────────────────────────────────────────────────────────────

EVENT_ORDER = [
    'earnings_gap_up', 'earnings_gap_down', 'earnings_flat',
    'macro_fomc', 'macro_cpi', 'macro_nfp', 'macro_other',
    'normal',
]

EVENT_LABELS = {
    'earnings_gap_up':   '📈 Earnings gap-up',
    'earnings_gap_down': '📉 Earnings gap-down',
    'earnings_flat':     '📊 Earnings (flat open)',
    'macro_fomc':        '🏦 FOMC day',
    'macro_cpi':         '📋 CPI day',
    'macro_nfp':         '💼 NFP day',
    'macro_other':       '📅 Other macro',
    'normal':            '📆 Normal day',
}


def print_event_table(trades: list[dict], event_map: dict) -> dict[str, dict]:
    """
    Print event-day breakdown table. Returns per-bucket scorecard dicts.
    """
    from .metrics import win_rate, profit_factor, r_distribution

    buckets = split_trades_by_event(trades, event_map)
    total = len(trades)

    print(f'\n{"═"*90}')
    print(f'  EVENT-DAY BREAKDOWN  ({total} trades)')
    print(f'{"─"*90}')
    print(f'  {"Event type":<25} {"Trades":>7} {"% of all":>9} {"Win%":>7} {"PF":>6} {"AvgR":>7}  {"Note"}')
    print(f'{"─"*90}')

    out: dict[str, dict] = {}

    for key in EVENT_ORDER:
        subset = buckets.get(key, [])
        if not subset:
            continue
        label = EVENT_LABELS.get(key, key)
        wr = win_rate(subset)
        pf = profit_factor(subset)
        rd = r_distribution(subset)
        avg_r = rd['mean']
        pct = len(subset) / total if total else 0

        # Flag interesting patterns
        normal_pf = profit_factor(buckets.get('normal', []))
        if key != 'normal' and pf > normal_pf * 1.2:
            note = f'⭐ edge vs normal (PF {normal_pf:.2f}→{pf:.2f})'
        elif key != 'normal' and pf < normal_pf * 0.8 and pf < 1.0:
            note = f'⚠️  avoid (PF {normal_pf:.2f}→{pf:.2f})'
        else:
            note = ''

        print(f'  {label:<25} {len(subset):>7} {pct:>8.1%}  {wr:>6.1%} {pf:>6.2f} {avg_r:>7.2f}  {note}')
        out[key] = {
            'trade_count': len(subset),
            'pct_of_all': round(pct, 3),
            'win_rate': wr,
            'profit_factor': pf,
            'r_dist': rd,
        }

    print(f'{"═"*90}')
    return out
