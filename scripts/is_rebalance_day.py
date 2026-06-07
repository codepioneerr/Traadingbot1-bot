#!/usr/bin/env python3
"""
Rebalance Day Checker
=====================
Determines whether today is the last trading day of the current month —
the day on which the Dual Momentum signal is evaluated and acted on.

Logic:
  1. Get today's date
  2. Find the last calendar day of the current month
  3. Walk backward until we hit a weekday that is NOT a US market holiday
  4. If today == that date: exit 0 (rebalance day), print confirmation
  5. If today != that date: exit 1 (not rebalance day), print days until rebalance

US Market Holidays (hardcoded for 2025 and 2026):
  New Year's Day, MLK Day, Presidents Day, Good Friday, Memorial Day,
  Juneteenth, Independence Day, Labor Day, Thanksgiving, Christmas.

Usage:
  python3 scripts/is_rebalance_day.py
  if [ $? -eq 0 ]; then echo "REBALANCE TODAY"; fi
"""

import sys
from datetime import date, timedelta

# ── US Market Holiday Calendar ────────────────────────────────────────────────
# Add future years as needed. Format: date(YYYY, M, D)
US_MARKET_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas

    # 2026
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day (observed, July 4 is Saturday)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas

    # 2027
    date(2027, 1, 1),   # New Year's Day
    date(2027, 1, 18),  # MLK Day
    date(2027, 2, 15),  # Presidents Day
    date(2027, 3, 26),  # Good Friday
    date(2027, 5, 31),  # Memorial Day
    date(2027, 6, 18),  # Juneteenth (observed, June 19 is Saturday)
    date(2027, 7, 5),   # Independence Day (observed, July 4 is Sunday)
    date(2027, 9, 6),   # Labor Day
    date(2027, 11, 25), # Thanksgiving
    date(2027, 12, 24), # Christmas (observed, Dec 25 is Saturday)
}


def is_trading_day(d: date) -> bool:
    """True if d is a weekday and not a US market holiday."""
    return d.weekday() < 5 and d not in US_MARKET_HOLIDAYS


def last_trading_day_of_month(year: int, month: int) -> date:
    """
    Return the last trading day (weekday, non-holiday) of the given month.
    Walks backward from the last calendar day until a trading day is found.
    """
    # Last calendar day of the month
    if month == 12:
        last_cal = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_cal = date(year, month + 1, 1) - timedelta(days=1)

    d = last_cal
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def trading_days_between(start: date, end: date) -> int:
    """Count trading days from start (exclusive) to end (inclusive)."""
    count = 0
    d = start + timedelta(days=1)
    while d <= end:
        if is_trading_day(d):
            count += 1
        d += timedelta(days=1)
    return count


def main() -> int:
    today = date.today()
    rebalance_day = last_trading_day_of_month(today.year, today.month)

    print(f'Today          : {today.strftime("%A, %B %d, %Y")}')
    print(f'Rebalance day  : {rebalance_day.strftime("%A, %B %d, %Y")} '
          f'(last trading day of {today.strftime("%B %Y")})')

    if today == rebalance_day:
        print('\n✅ TODAY IS REBALANCE DAY')
        print('   Run: python3 scripts/dual_momentum_signal.py')
        print('   Then execute the rebalance per market-open.md')
        return 0
    elif today > rebalance_day:
        # Past end of month (shouldn't normally happen, but handle it)
        next_month_rebalance = last_trading_day_of_month(
            today.year if today.month < 12 else today.year + 1,
            today.month % 12 + 1
        )
        days_until = trading_days_between(today, next_month_rebalance)
        print(f'\n⏳ Not rebalance day.')
        print(f'   Next rebalance: {next_month_rebalance.strftime("%A, %B %d, %Y")} '
              f'({days_until} trading days away)')
        return 1
    else:
        days_until = trading_days_between(today, rebalance_day)
        if days_until == 0:
            print(f'\n⏳ Not rebalance day. Rebalance is today (non-trading day — run tomorrow).')
        else:
            print(f'\n⏳ Not rebalance day.')
            print(f'   {days_until} trading day(s) until rebalance '
                  f'({rebalance_day.strftime("%b %d")})')
        return 1


if __name__ == '__main__':
    sys.exit(main())
