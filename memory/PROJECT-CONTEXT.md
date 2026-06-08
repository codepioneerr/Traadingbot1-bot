# Project Context

## What This Is

An autonomous Claude-powered trading bot managing a paper trading account on Alpaca.
Runs a monthly ETF rotation strategy (Dual Momentum — Antonacci 2014).
All notifications go to Telegram.

## Account Details

| Field | Value |
|-------|-------|
| Broker | Alpaca (paper trading) |
| Starting capital | $100,000 |
| Account type | Paper (simulated, no real money) |
| Strategy | Dual Momentum ETF Rotation |
| Rebalance frequency | Monthly (last trading day of each month) |
| Valid positions | SPY, QQQ, IWM, TLT, GLD, SHY only |
| Max open positions | 1 (always fully invested in one asset) |

## Instruments

ETFs only — the 6-asset universe above. No stocks, no options, ever.

## Current Phase

**Phase 2 — Dual Momentum Deployment** (started June 2026)

Background:
- Phase 0 (May 2026): Infrastructure, notifications, Alpaca integration
- Phase 1 (May–June 2026): Active stock picking — tested ORB and PEAD strategies. Both failed backtests. Strategy family retired.
- Phase 2 (June 2026+): Pivoted to Dual Momentum ETF rotation. Backtested 2005–2026. Passed all 4 gate conditions.

## Current Strategy Status

| Item | Status |
|------|--------|
| Backtest | ✅ PASS (June 7, 2026) — CAGR 11.3%, Sharpe 0.687, MaxDD 32.9% |
| Signal script | ✅ scripts/dual_momentum_signal.py |
| Rebalance checker | ✅ scripts/is_rebalance_day.py |
| Circuit breaker | ✅ scripts/risk_check.py |
| Routines updated | ✅ All routines rewritten for monthly rotation |
| First live trade | ⏳ Next last-trading-day-of-month |

## Key Rules for This Strategy

1. Only 6 valid tickers: SPY, QQQ, IWM, TLT, GLD, SHY
2. 100% of equity in one asset at all times
3. NO stop-losses, NO trailing stops — holds through drawdowns
4. Rebalance ONLY on signal change on last trading day of month
5. No Perplexity research needed — purely quantitative signal
6. Run risk_check.py at the top of every routine before any order logic

## Manual Pause / Reset

To halt the bot: create PAUSE-FLAG.txt with the reason.
To resume: delete PAUSE-FLAG.txt.
risk_check.py checks for this file at startup.


## Dashboard Deployment

| Component | URL | Platform |
|-----------|-----|----------|
| Frontend | https://traadingbot1-bot.vercel.app | Vercel (auto-deploy on push to main) |
| Backend API | https://tradingbot-hub-production.up.railway.app | Railway (deploy via `railway up` from dashboard/backend/) |

### Required Environment Variables

**Railway (backend):**
- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_ENDPOINT` — Alpaca paper trading credentials
- `DASHBOARD_PASSWORD` — password to protect financial endpoints (/api/account, /api/positions, etc.)
- `FRONTEND_URL` — Vercel URL for CORS allowlist (e.g. https://traadingbot1-bot.vercel.app)

**Vercel (frontend):**
- `VITE_API_URL` — Railway backend URL (https://tradingbot-hub-production.up.railway.app)
- `VITE_DASHBOARD_PASSWORD` — must match DASHBOARD_PASSWORD in Railway; set this in Vercel Settings -> Environment Variables; DO NOT commit the real value to git

### Auth Model
- Public routes (no auth): /, /health, /api/signal, /api/rebalance-status, /api/health/bot, /api/strategy, /api/status, /api/backtest, /api/quote
- Protected routes (X-Password header required): /api/account, /api/positions, /api/orders, and all write endpoints
- Frontend sends X-Password header from localStorage (set by PasswordGate on first visit)
- If VITE_DASHBOARD_PASSWORD is set in Vercel, the PasswordGate is skipped automatically

### Deploy Steps (backend)
```bash
cd dashboard/backend
railway up
```
Note: `railway up` must be run from `dashboard/backend/` — only that directory is deployed.
The scripts/ subdirectory (alpaca.sh, dual_momentum_signal.py, is_rebalance_day.py) is bundled here.
