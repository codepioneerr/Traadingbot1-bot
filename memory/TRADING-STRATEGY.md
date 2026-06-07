# Trading Strategy

## STRATEGY: Dual Momentum ETF Rotation (Antonacci)
## STATUS: BACKTESTED PASS — deploying to paper account
## BACKTEST DATE: June 7, 2026

---

## Universe (fixed — 6 assets only)

| Ticker | Role |
|--------|------|
| SPY    | US broad equity |
| QQQ    | US tech/growth |
| IWM    | US small cap |
| TLT    | Long-term bonds |
| GLD    | Gold |
| SHY    | Short-term T-bills (cash/safe-haven proxy) |

These are the ONLY valid positions. Never trade stocks, options, or any other instrument.

---

## Signal (run on last trading day of each month)

**Step 1 — Absolute filter:**
Calculate SPY's 12-month return (252 trading days).
If SPY 12-month return < 0%: hold SHY. Stop — do not proceed to Step 2.

**Step 2 — Relative ranking:**
Rank SPY, QQQ, IWM, TLT, GLD by 12-month return (252 trading days).
Hold the #1 ranked asset for the next month.

Signal script: `python3 scripts/dual_momentum_signal.py`
Rebalance check: `python3 scripts/is_rebalance_day.py`

---

## Position Sizing

**100% of equity in one asset at all times.**

```
buy_qty = floor(account_equity / current_ask_price)
```

No partial positions. No diversification. No VIX-based sizing. This is by design — the strategy's risk management comes from rotating to SHY (cash) when absolute momentum is negative, not from diversification.

---

## Rebalance

On the last trading day of each month:
1. Run `python3 scripts/dual_momentum_signal.py` → get signal
2. If signal == current holding: NO TRADE. Hold as-is.
3. If signal != current holding:
   - Close current position: `bash scripts/alpaca.sh close [CURRENT_TICKER]`
   - Open new position: `bash scripts/alpaca.sh order [BUY_JSON]`
   - Log to TRADE-LOG.md
   - Send Telegram alert

Expected frequency: ~5-6 rebalances per year.

---

## Stops

**NONE.** Do not place trailing stops. Do not apply a 7% hard cut. Do not exit intraday.

This strategy holds through normal drawdowns by design. The protection comes from rotating to SHY when momentum turns negative — NOT from stop-losses.

- Max historical drawdown: 32.9% (mostly the 2022 QQQ bear market)
- A position being down -10%, -15%, -20% is expected and acceptable
- The ONLY exit is the monthly rebalance signal

Circuit breaker (extraordinary events only): `python3 scripts/risk_check.py`
See risk_check.py for the narrow set of conditions that warrant human intervention.

---

## Exits

Only on rebalance signal. Never intraday. Never on price movement alone.

---

## Performance Expectations (from 2005–2026 backtest)

| Metric | Dual Momentum | SPY B&H |
|--------|--------------|---------|
| CAGR | +11.30% | +10.60% |
| Sharpe | 0.687 | 0.578 |
| Max Drawdown | 32.9% | 52.9% |
| Win Rate (monthly) | 59.7% | — |

Do not expect the OOS Sharpe of 2.03 — that was an unusually favorable 2023-2026 period.
Realistic long-run Sharpe target: 0.6-0.8.

---

## Deprecated Strategies

### ORB (Opening Range Breakout)
❌ Tested June 2026. PF 0.59, every year negative. No edge. Retired.

### PEAD and variants (Post-Earnings Announcement Drift)
❌ Tested June 2026. Multiple variants — all failed or insufficient sample (92-symbol universe too small). Retired.

### Multi-stock momentum / active stock picking
❌ Replaced by Dual Momentum. VIX sizing table, trailing stops, 6-position limit, PDT counter — all irrelevant for this strategy.
