# Research Log

Daily pre-market research entries. Each entry records market context, sizing mode, and trade ideas for that day.
Format: prepend new entries at the top (most recent first).

---

## 2026-06-26 — Pre-Market (Friday)

**Status:** API BLOCKED — 5th consecutive day (Jun 22–26). Perplexity, Alpaca, Telegram all blocked by proxy egress policy (connect_rejected 403 / exit 56). Fell back to native WebSearch for market data.

**Strategy:** Dual Momentum ETF Rotation (Antonacci)
**Universe:** SPY, QQQ, IWM, TLT, GLD, SHY
**Today's action required:** NONE — NOT a rebalance day. Next rebalance: **2026-06-30 (Tuesday)** — last trading day of June. 4 calendar days away.

### API Access Status
- `paper-api.alpaca.markets:443` → 403 connect_rejected (5th day blocked)
- `api.perplexity.ai:443` → exit 56 / connection refused (blocked)
- `api.telegram.org:443` → 403 connect_rejected (blocked)
- GitHub MCP: available (used for git push)

### Account State
Could not retrieve — API blocked. Last known: no open positions (idle in cash since inception). Starting equity: $100,000.00 (baseline 2026-05-09).

### Market Context (via WebSearch fallback — June 26, 2026)
- **VIX:** 18.68 (intraday range 17.72–19.95) → **MODERATE** (15–25) — though Dual Momentum does not use VIX sizing
- **S&P 500 futures:** -0.3 to -0.37% premarket; Nasdaq-100 futures -1% — risk-off tone
- **Market tone:** Broad tech sell-off. Apple (-6.35% on price hikes), Microsoft (-3.78% on price hikes), OpenAI IPO delay reports. AI cost concern sentiment weighing on mega-cap tech.
- **Oil:** WTI below $71/bbl; Brent $74.43/bbl (down ~1.11%). Iran/IRGC attacked a Singaporean vessel near Strait of Hormuz → crude spiked ~2% then pulled back.
- **Top sectors (weekly momentum):** Technology, Industrials, Real Estate
- **Lagging sectors:** Communication Services/Tech (Communication down ~4% Monday Jun 21), Energy
- **Economic data today:** Dallas Fed Manufacturing (10:30 AM), UMich Consumer Sentiment final (June) — no PCE/NFP/FOMC today

### Sizing Mode
N/A — Dual Momentum uses 100% equity in one asset, no VIX-based sizing.

### Rebalance Calendar
- **Rebalance date: 2026-06-30 (Tuesday)** — last trading day of June, 4 days away
- On June 30: run `python3 scripts/dual_momentum_signal.py` → check SPY 12-month return → if positive, rank SPY/QQQ/IWM/TLT/GLD, hold #1
- Current account: idle in cash (no open position since inception)
- ⚠️ CRITICAL: Proxy egress must be restored before June 30 or bot cannot execute its first-ever rebalance trade

### Trade Ideas
None — Dual Momentum is monthly-only. No intraday or discretionary action warranted.

### Risk Factors
- Persistent API blockage (5 days) — critical if not resolved before June 30 rebalance
- Tech sentiment deteriorating (Apple, Microsoft, OpenAI news) — may affect QQQ momentum signal
- Geopolitical (Iran/Strait of Hormuz) — oil supply disruption risk; could benefit GLD or TLT as safe havens

### Decision
**NO TRADE** — not rebalance day. Monitor for API restoration before June 30.

### Action Required (human)
**URGENT:** Whitelist `paper-api.alpaca.markets`, `api.perplexity.ai`, and `api.telegram.org` in the Claude Code remote execution environment's egress policy. June 30 rebalance is the bot's first-ever trade — API access is required.

---

## 2026-06-25 — Pre-Market (Thursday)

**Status:** API BLOCKED — 4th consecutive day (Jun 22–25). Perplexity, Alpaca, Telegram all blocked by proxy egress policy (connect_rejected 403). Fell back to native WebSearch for market data.

**Strategy:** Dual Momentum ETF Rotation (Antonacci)
**Universe:** SPY, QQQ, IWM, TLT, GLD, SHY
**Today's action required:** NONE — NOT a rebalance day. Next rebalance: 2026-06-30 (5 days away, last trading day of June).

### API Access Status
- `paper-api.alpaca.markets:443` → 403 connect_rejected (4th day blocked)
- `api.perplexity.ai:443` → 403 connect_rejected (blocked)
- `api.telegram.org:443` → 403 connect_rejected (4th day blocked)
- GitHub MCP: available (used for git push)

### Account State
Could not retrieve — API blocked. Last known: no open positions (all prior attempts also blocked). Starting equity: $100,000.00 (baseline 2026-05-09).

### Market Context (via WebSearch fallback)
- **VIX:** ~19.13 (open), intraday range 18.04–20.34 → **MODERATE** (15–25) — though Dual Momentum does not use VIX sizing
- **S&P 500 futures:** +0.8% premarket — Micron blowout earnings (+17% premarket), AI data center demand catalyst
- **PCE inflation:** 4.1% annualized (highest since April 2023) — sticky inflation risk
- **Leading sectors:** Consumer Staples, Industrials, Materials, Energy (Iran war driving energy prices)
- **Lagging sectors:** Technology, Communications, Consumer Discretionary, Financials
- **Macro:** Iran war continues to threaten global oil supply; AI capex debate ongoing

### Sizing Mode
N/A — Dual Momentum uses 100% equity in one asset, no VIX-based sizing.

### Rebalance Calendar
- **Rebalance date: 2026-06-30 (Tuesday)** — 5 trading days away
- Signal script: `python3 scripts/dual_momentum_signal.py` — must run on June 30
- Required on June 30: SPY 12-month return check → if positive, rank SPY/QQQ/IWM/TLT/GLD, hold #1
- Current account has no open position (idle in cash since inception)
- ⚠️ CRITICAL: API egress must be restored before June 30 or bot cannot execute rebalance

### Trade Ideas
None — strategy is monthly-only, no intraday action warranted.

### Decision
**NO TRADE** — not rebalance day. Monitor for API restoration before June 30.

### Action Required (human)
**URGENT:** Whitelist `paper-api.alpaca.markets`, `api.perplexity.ai`, and `api.telegram.org` in the Claude Code remote execution environment's egress policy. June 30 rebalance is 5 days away. Without API access, the bot cannot execute its first-ever trade.

---

## 2026-06-24 — Pre-Market (Wednesday)

**Status:** API BLOCKED — same egress policy issue as 2026-06-23

**Strategy:** Dual Momentum ETF Rotation (Antonacci)
**Today's action required:** NONE — rebalance day is 2026-06-30 (6 days away)

### Market Access
- `paper-api.alpaca.markets:443` → 403 connect_rejected (proxy policy denial)
- `api.telegram.org:443` → HTTP 403
- Perplexity API not attempted (Alpaca blocked first)
- Git push via GitHub MCP: available

### Account State
Could not retrieve — API blocked. Last known: no positions as of 2026-06-23 (also blocked).

### Sizing Mode
N/A — Dual Momentum uses 100% equity in one asset, no VIX-based sizing.

### Rebalance Calendar
- Current month end: 2026-06-30 (Tuesday) = last trading day of June
- Signal to run: `python3 scripts/dual_momentum_signal.py` on 2026-06-30
- Action: close existing position (if any), open new signal asset at market open

### Decision
**NO TRADE** — not rebalance day. Strategy is monthly-only. No intraday action warranted.

### Action Required (human)
Whitelist `paper-api.alpaca.markets` and `api.telegram.org` in the remote execution environment's egress policy. Without this, the bot cannot trade or send alerts.

---
