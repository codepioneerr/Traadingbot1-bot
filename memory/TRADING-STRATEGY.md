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

## ORB Strategy (Opening Range Breakout) — DEPRECATED

> ❌ Fully backtested June 2026. Conclusion: no consistent edge on institutional S&P 500 universe. PF 0.59, win rate 46.2%, total return −7.2% over 2021–2026 with realistic 5bps costs. Every calendar year negative. Strategy is retired.

## PEAD Strategy (Post-Earnings Announcement Drift) — DEPRECATED

> ❌ Fully backtested June 2026. Both long-only (PF 0.849, WR 35%) and short-only (8 OOS trades — INSUFFICIENT SAMPLE) variants failed. Earnings universe (92 symbols) too small to reach statistical significance. Variants tested: baseline PEAD, short-only with borrow costs, high-conviction longs (SUE ≥ 15/25%), 1-day momentum, overreaction fade. All failed or had insufficient samples. Strategy family is retired.

---

## Active Strategy: Dual Momentum ETF Rotation — ✅ BACKTEST PASSED (June 2026)

> Backtest verdict: PASS. OOS Sharpe 2.03, OOS return +166.9%, max drawdown 32.9%, CAGR +11.30%. See `backtest/results/dual_momentum_*.json`.

### Reference
Gary Antonacci, "Dual Momentum Investing" (2014). Published CAGR ~10-12%, max DD ~17% (through 2013). Our 2005–2026 run matches CAGR (11.30%) and slightly exceeds max DD (32.9%) due to 2022 QQQ bear market, which post-dates Antonacci's published results.

### Universe (fixed — 6 assets only)
| Asset | Role |
|-------|------|
| SPY   | US broad equity |
| QQQ   | US tech/growth |
| IWM   | US small cap |
| TLT   | Long-term bonds |
| GLD   | Gold |
| SHY   | Cash proxy (absolute momentum fallback) |

### Signal Logic (run once per month, last trading day)
**Step 1 — Absolute Momentum:**
- Compute SPY's 12-month price return
- If SPY 12m return < 0%: hold SHY for next month. Stop.
- Otherwise: proceed to Step 2.

**Step 2 — Relative Momentum:**
- Compute 12-month price return for SPY, QQQ, IWM, TLT, GLD
- Hold the single top-ranked asset for next month
- No trade if the top asset is unchanged (avoids unnecessary turnover)

### Rebalance Schedule
- Monthly, on the last trading day of each month
- Sell current holding, buy new top-ranked asset
- ~5-6 trades per year on average (not every month triggers a change)

### Backtest Results (2005–2026, $100K starting equity)
| Metric | Dual Momentum | SPY B&H |
|--------|--------------|---------|
| Total Return | +856.1% | +737.2% |
| CAGR | +11.30% | +10.60% |
| Sharpe | 0.687 | 0.578 |
| Max Drawdown | 32.9% | 52.9% |
| Win Rate (monthly) | 59.7% | — |
| Final Equity | $956,142 | — |

**IS (2005–2022):** Return +255.4%, Sharpe 0.46, MaxDD 32.9%, PF 1.58
**OOS (2023–2026):** Return +166.9%, Sharpe 2.03, MaxDD 8.6%, PF 5.07

**Per-Decade:** 2005-10: CAGR +15.7% / 2011-15: +9.1% / 2016-20: +5.6% / 2021-26: +17.3%

**Asset allocation (months):** QQQ 34% | GLD 23% | IWM 15% | SHY 15% (cash) | TLT 9% | SPY 4%

Absolute momentum (SHY) triggered 39 months = 15% of the time.

### Costs
REALISTIC_5: 5bps slippage each way on rebalance trades only (~10 round-trips/year maximum). Annual cost drag ≈ 0.05% — negligible.

### Known Limitations
- 12-month lookback = momentum lag during sharp trend reversals (2022 QQQ: held through −32%)
- No dividends needed (yfinance auto_adjust=True handles dividend-adjusted prices)
- SHY pays interest — not captured in price return alone (conservative assumption)
- Monthly rebalancing = PDT-safe (well below 3-day-trade limit)

### Deployment Status
> ⚠️ NOT YET DEPLOYED. Three deployment steps documented below must be implemented before going live. Strategy passed backtest gate as of June 2026.

## Notification Rules (Telegram)
- Pre-market: ALWAYS send sector watchlist + VIX/sizing mode
- Every trade: ALWAYS send real-time alert
- Every stop tightened: ALWAYS send alert
- Every position closed: ALWAYS send alert
- EOD summary: ALWAYS send (even on no-trade days)
- Weekly review: ALWAYS send with next-week sector outlook
