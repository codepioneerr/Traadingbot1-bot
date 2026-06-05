"""
Backtest diagnostic tool — prints why trades fire or don't per day.

Usage:
    python -m backtest.diagnose AAPL,NVDA,MSFT 2024-02-08 2024-02-29 --or-minutes 5
    python -m backtest.diagnose AAPL 2024-01-02 2024-03-31

Output per symbol per day:
  - Whether universe() would include the symbol
  - OR high/low
  - How many bars cleared vs were blocked at each condition
  - How many actual engine entries fired (with ctx)
"""
from __future__ import annotations
import sys
from collections import defaultdict
from datetime import datetime, time, timezone

from .data import load_bars, detect_feed
from .strategies.orb import ORBStrategy, _bar_et_time
from .engine import BacktestEngine
from .costs import REALISTIC_5


def diagnose(
    symbols: list[str],
    start: str,
    end: str,
    or_minutes: int = 5,
    n_vwap_bars: int = 2,
    verbose_days: int = 5,   # print detail for first N days
):
    feed = detect_feed()
    print(f'\n🔍 DIAGNOSTIC  {start} → {end}  OR={or_minutes}m  feed={feed.upper()}')
    print(f'   Symbols: {symbols}\n')

    # Load bars
    bars_by_symbol: dict[str, list[dict]] = {}
    for sym in symbols:
        try:
            b = load_bars(sym, start, end, '1Min', feed=feed)
            bars_by_symbol[sym] = b
            print(f'  {sym}: {len(b):,} bars loaded')
        except Exception as e:
            print(f'  {sym}: FAILED — {e}')

    if not bars_by_symbol:
        print('No data loaded. Check credentials.')
        return

    # ── Test 1: Run WITHOUT ctx (old broken behaviour) ────────────────────────
    strat_no_ctx = ORBStrategy(or_minutes=or_minutes, n_vwap_bars=n_vwap_bars)
    # Fresh bars for first run
    bars_no_ctx = {s: [dict(b) for b in bars] for s, bars in bars_by_symbol.items()}
    eng_no_ctx = BacktestEngine(strat_no_ctx, REALISTIC_5, 100_000)
    r_no_ctx = eng_no_ctx.run(bars_no_ctx)

    # ── Test 2: Run WITH ctx (correct behaviour) ──────────────────────────────
    def _build_ctx(bars_dict):
        syms = list(bars_dict.keys())
        def bar_date(b):
            t = b['t']
            return t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
        dates = set(bar_date(b) for bars in bars_dict.values() for b in bars)
        return {d: {'candidates': syms} for d in dates}

    bars_with_ctx = {s: [dict(b) for b in bars] for s, bars in bars_by_symbol.items()}
    ctx = _build_ctx(bars_with_ctx)
    strat_ctx = ORBStrategy(or_minutes=or_minutes, n_vwap_bars=n_vwap_bars)
    eng_ctx = BacktestEngine(strat_ctx, REALISTIC_5, 100_000)
    r_ctx = eng_ctx.run(bars_with_ctx, ctx_by_date=ctx)

    print(f'\n{"═"*70}')
    print(f'  WITHOUT ctx (old bug): {len(r_no_ctx["trades"])} trades')
    print(f'  WITH ctx (correct):    {len(r_ctx["trades"])} trades')
    print(f'{"═"*70}')
    print()

    # ── Per-day bar-level trace ───────────────────────────────────────────────
    MARKET_OPEN = time(9, 30)
    or_end_time = time(9, 30 + or_minutes)
    eod_time    = time(15, 55)

    print(f'{"─"*70}')
    print(f'  PER-DAY TRACE (symbols × dates, first {verbose_days} days shown in detail)')
    print(f'{"─"*70}')

    # Group all bars by (symbol, UTC-date)
    by_sym_day: dict[str, dict[str, list]] = {}
    for sym, bars in bars_by_symbol.items():
        daily: dict[str, list] = defaultdict(list)
        for b in bars:
            t = b['t']
            d = t[:10] if isinstance(t, str) else t.strftime('%Y-%m-%d')
            daily[d].append(b)
        by_sym_day[sym] = daily

    # Aggregate totals
    total_days = 0
    days_with_entry = 0
    total_would_enter = 0
    rejection_totals: dict[str, int] = defaultdict(int)

    all_dates = sorted(set(d for sym_daily in by_sym_day.values() for d in sym_daily))
    printed_days = 0

    for date_str in all_dates:
        day_detail_lines = []
        any_entry_this_day = False

        for sym in symbols:
            day_bars = by_sym_day.get(sym, {}).get(date_str, [])
            if not day_bars:
                continue

            total_days += 1
            or_high = or_low = None
            or_set = False
            would_enter = 0
            rejections: dict[str, int] = defaultdict(int)
            state_avg_vol = None

            # Check universe (with ctx: candidates always provided)
            universe_ok = True   # with ctx, symbol always in universe

            for b in day_bars:
                t_raw = b['t']
                t_dt  = datetime.fromisoformat(t_raw.replace('Z', '+00:00')) if isinstance(t_raw, str) else t_raw
                et    = _bar_et_time(t_dt)

                if et < MARKET_OPEN:
                    rejections['pre_market'] += 1
                    continue
                if et >= eod_time:
                    rejections['after_close'] += 1
                    continue

                # OR building
                if et <= or_end_time:
                    if or_high is None:
                        or_high, or_low = b['h'], b['l']
                    else:
                        or_high = max(or_high, b['h'])
                        or_low  = min(or_low,  b['l'])
                    or_set = True
                    continue

                if not or_set:
                    rejections['no_or_built'] += 1
                    continue

                c    = b['c']
                vwap = b.get('vwap', c)
                vol  = b['v']
                avg  = state_avg_vol if state_avg_vol is not None else vol
                vol_ok = vol > avg * 0.8
                state_avg_vol = avg

                # Long entry conditions
                if   c <= or_high: rejections['below_OR_high'] += 1
                elif c <= vwap:    rejections['below_VWAP'] += 1
                elif not vol_ok:   rejections['low_volume'] += 1
                else:
                    would_enter += 1

            for k, v in rejections.items():
                rejection_totals[k] += v

            if would_enter > 0:
                any_entry_this_day = True
                total_would_enter += would_enter

            or_str = f'{or_high:.2f}/{or_low:.2f}' if or_high else 'N/A'
            line = (f'    {sym} {date_str}: OR={or_str}  '
                    f'would_enter={would_enter}  '
                    f'blocked={{ {", ".join(f"{k}:{v}" for k,v in rejections.items() if k not in ("pre_market","after_close"))} }}')
            day_detail_lines.append(line)

        if any_entry_this_day:
            days_with_entry += 1

        if printed_days < verbose_days:
            print(f'  {date_str}:')
            for line in day_detail_lines:
                print(line)
            printed_days += 1

    print(f'\n{"─"*70}')
    print(f'  SUMMARY over {len(all_dates)} trading days, {len(symbols)} symbols')
    print(f'  Days with ≥1 would-enter signal : {days_with_entry}')
    print(f'  Total would-enter signals        : {total_would_enter}')
    print(f'  Entry rejection breakdown:')
    skip = {'pre_market', 'after_close'}
    for k, v in sorted(rejection_totals.items(), key=lambda x: -x[1]):
        if k not in skip:
            print(f'    {k:<25} {v:>8,}')
    print(f'{"─"*70}')
    print(f'\n  Root cause of 0 trades (if any): universe() returns [] when')
    print(f'  ctx_by_date is not passed → strategy never sees any symbols.')
    print(f'  Fix: always call engine.run(bars, ctx_by_date=_build_ctx(bars))')
    print(f'{"─"*70}')

    if r_ctx['trades']:
        from collections import Counter
        print(f'\n  Sample trades (first 5 with ctx):')
        for t in r_ctx['trades'][:5]:
            print(f'    {t["symbol"]} {t["entry_time"][:16]} '
                  f'{t["side"]} entry={t["entry_price"]:.2f} '
                  f'exit={t["exit_price"]:.2f} pnl={t["pnl"]:+.2f} '
                  f'reason={t["exit_reason"]}')
        reasons = Counter(t['exit_reason'] for t in r_ctx['trades'])
        print(f'\n  Exit reasons: {dict(reasons)}')


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python -m backtest.diagnose AAPL,NVDA,MSFT 2024-02-08 2024-02-29')
        print('       python -m backtest.diagnose AAPL,NVDA 2024-01-02 2024-03-31 --or-minutes 1')
        sys.exit(1)

    syms = sys.argv[1].split(',')
    start_date = sys.argv[2]
    end_date   = sys.argv[3]

    or_min = 5
    for i, arg in enumerate(sys.argv):
        if arg == '--or-minutes' and i + 1 < len(sys.argv):
            or_min = int(sys.argv[i + 1])

    diagnose(syms, start_date, end_date, or_minutes=or_min)
