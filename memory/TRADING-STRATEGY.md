# Trading Strategy

## Mission
Beat the S&P 500 over the challenge window. Target 5-10% monthly return.
Stocks AND ETFs — no options, ever.

## Capital & Constraints
- Starting capital: ~$10,000
- Platform: Alpaca (paper trading initially)
- Instruments: Stocks AND ETFs
- PDT limit: 3 day trades per 5 rolling days (account < $25k) — CHECK BEFORE EVERY BUY

## Dynamic Position Sizing (based on VIX each morning)
| VIX Level | Mode | Max per position | Capital deployed | Max positions |
|-----------|------|-----------------|-----------------|---------------|
| < 15 | AGGRESSIVE | 25% | 85-90% | 6 |
| 15-25 | MODERATE | 20% | 75-85% | 6 |
| > 25 | DEFENSIVE | 15% | 60-75% | 4 |

Sizing mode is set at pre-market and logged in RESEARCH-LOG. Do not change mid-day.

## Core Rules
1. NO OPTIONS — ever
2. Deploy capital per today's sizing mode (see table above)
3. Max 6 positions (4 in DEFENSIVE mode)
4. Max 5 new trades per week
5. 10% trailing stop on every position as a real GTC order
6. Cut losers at -7% manually — no hoping, no averaging down
7. Tighten trail: 7% at +15%, 5% at +20%
8. Never tighten stop within 3% of current price
9. Never move a stop down
10. Follow sector momentum — bot decides sectors daily, user can override
11. Exit a sector after 2 consecutive failed trades in that sector
12. Patience > activity — zero trades can be the right answer

## Trade Mix
- Momentum / trend following
- Breakouts on news/catalysts
- Technical patterns (support/resistance)
- Fundamentals-driven swings
Use the mix that fits today's market conditions.

## Entry Checklist (document before every trade)
- Specific catalyst today?
- Sector in momentum?
- Stop level (7-10% below entry)?
- Target (minimum 2:1 R:R)?
- PDT count leaves room?
- Sizing mode % respected?

## Buy-Side Gate (all must pass or trade is skipped)
- Total positions after fill <= 6 (4 in DEFENSIVE)
- Trades this week <= 5
- Position cost <= sizing mode % of equity
- Position cost <= available cash
- daytrade_count < 3
- Catalyst documented in today's RESEARCH-LOG
- Instrument is a stock or ETF (not an option)

## Sell-Side Rules
- Unrealized loss <= -7%: close immediately
- Thesis broken intraday: close even if not at -7%
- Up +15%: tighten trailing stop to 7%
- Up +20%: tighten trailing stop to 5%
- 2 consecutive failed trades in a sector: exit all positions in that sector

## Notification Rules (Telegram)
- Pre-market: ALWAYS send sector watchlist + VIX/sizing mode
- Every trade: ALWAYS send real-time alert
- Every stop tightened: ALWAYS send alert
- Every position closed: ALWAYS send alert
- EOD summary: ALWAYS send (even on no-trade days)
- Weekly review: ALWAYS send with next-week sector outlook
