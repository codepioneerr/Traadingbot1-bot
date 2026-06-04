# Trading Strategy

## Mission
Beat the S&P 500 over the challenge window. Target 5-10% monthly return.
Stocks AND ETFs — no options, ever.

## Capital & Constraints
- Starting capital: $100,000 (Alpaca paper default)
- Platform: Alpaca (paper trading initially)
- Instruments: Stocks AND ETFs
- PDT rule: **conditional on live equity, checked every run**
  - Equity **≥ $25,000** (current): NO day-trade cap — trade freely within other limits
  - Equity **< $25,000**: max 3 day trades per rolling 5 days — enforce `daytrade_count < 3`

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
- PDT count leaves room? (only applies if equity < $25k)
- Sizing mode % respected?

## Buy-Side Gate (all must pass or trade is skipped)
- Total positions after fill <= 6 (4 in DEFENSIVE)
- Trades this week <= 5
- Position cost <= sizing mode % of equity
- Position cost <= available cash
- If equity < $25,000: daytrade_count < 3 (PDT cap — else no cap)
- Catalyst documented in today's RESEARCH-LOG
- Instrument is a stock or ETF (not an option)

## Sell-Side Rules
- Unrealized loss <= -7%: close immediately
- Thesis broken intraday: close even if not at -7%
- Up +15%: tighten trailing stop to 7%
- Up +20%: tighten trailing stop to 5%
- 2 consecutive failed trades in a sector: exit all positions in that sector

## ORB Strategy (Opening Range Breakout) — PENDING BACKTEST VALIDATION

> ⚠️ This strategy is NOT live yet. It deploys only after `backtest/results/` shows PASS on the out-of-sample realistic pass. See `backtest/evaluate.py`.

### Evidence basis
QuantConnect replication of Zarattini "stocks in play" study: Sharpe ~2.4 vs ~0.84 SPY, beat benchmark in ~68% of param combos. Edge is in **universe selection** (high relative-volume names with catalysts), not the OR pattern itself. ORB on S&P index has degraded to ~nothing.

### Universe ("stocks in play")
- Pre-market: rank candidates by relative volume (today vs N-day avg) + require a catalyst (news/earnings/gap)
- Feed from morning Perplexity research — keep universe wide (dozens of names)

### Opening range
- Default OR window: first 5 minutes (9:30–9:35 ET)
- Record OR high (ORH), OR low (ORL), OR width = ORH − ORL
- OR window is a tunable param (1-min, 5-min, 15-min tested in backtest)

### Entry
- Long: bar closes above ORH with volume pick-up and price above VWAP
- Short: bar closes below ORL with volume pick-up and price below VWAP
- One position per symbol; size by VIX sizing table; spread < 0.5% of price

### Stops
- Primary stop: opposite side of OR (ORL for longs, ORH for shorts), or ATR-based if OR is tight
- Catastrophic backstop: -7% hard cut (seatbelt — OR stop should fire first)

### Targets & exits
1. **15:55 ET EOD flat** — no overnight holds (biggest stagnation fix)
2. **VWAP/momentum break** — exit runner if price closes below VWAP (longs) / above VWAP (shorts) for N consecutive bars, or breaks 9-EMA
3. **Failed-breakout re-entry** — if price falls back into OR box for M bars, exit immediately
4. **Measured move** — take partial (1/2) at ORH + OR_width (longs); trail remainder by rules 2–3
5. **-7% catastrophic backstop** (rare fallback)

Every close records an **exit-reason** in TRADE-LOG: `target | momentum-trail | failed-breakout | eod-flat | stop`

## Notification Rules (Telegram)
- Pre-market: ALWAYS send sector watchlist + VIX/sizing mode
- Every trade: ALWAYS send real-time alert
- Every stop tightened: ALWAYS send alert
- Every position closed: ALWAYS send alert
- EOD summary: ALWAYS send (even on no-trade days)
- Weekly review: ALWAYS send with next-week sector outlook
