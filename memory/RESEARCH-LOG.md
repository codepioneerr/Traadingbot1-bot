# Research Log

Daily pre-market research entries. Each entry records market context, sizing mode, and trade ideas for that day.
Format: prepend new entries at the top (most recent first).

---

## 2026-07-07 — Morning Routine (Tuesday) ⚠️ API STILL BLOCKED — Day 18

**Strategy:** Dual Momentum ETF Rotation | **Next rebalance:** 2026-07-31 (18 trading days)
**Overdue rebalance:** BUY IWM (Jun 30 missed, pending API restoration)
**API Status:** Alpaca, Perplexity, Telegram — ALL BLOCKED (403 connect_rejected via proxy egress policy, Day 18: Jun 22–Jul 7)

### Account State
Could not retrieve — Alpaca API blocked. Last known: $100,000.00 (Day 0 baseline, 2026-05-09). No positions held.

### Market Context (WebSearch fallback)
- **VIX:** 15.88 → MODERATE (irrelevant to this strategy — 100% equity, no VIX sizing)
- **S&P 500 futures:** −0.25% (chip stocks pressured by Samsung Q2 disappointment, Asian selloff)
- **WTI crude:** $68.99/bbl (+0.64%); **Brent:** ~$72/bbl (near 4-month lows; OPEC raising quotas)
- **10-year Treasury yield:** ~4.49% (rising on Persian Gulf shipping attack reports)
- **S&P 500 close (Jul 6):** 7,537.43 (+0.72%); **Dow:** 53,055.91 (record close)
- **Notable movers:** Rivian +7%+ (Q2 deliveries beat), TeraWulf +16%+ (Anthropic 20-yr data center deal)
- **Upcoming events:** PepsiCo earnings (Thu), Delta Air Lines (Fri), EIA crude inventories, Consumer Credit

### Dual Momentum Signal (WebSearch estimate — NOT authoritative; run `dual_momentum_signal.py` on API restore)
SPY 12-month return: **+24.27%** → Absolute filter PASSES (equity momentum positive)

| Rank | Ticker | Est. 12M Return |
|------|--------|----------------|
| 1 | IWM | +34.78% |
| 2 | QQQ | +29.86% |
| 3 | GLD | ~+22–32% (conflicting sources) |
| 4 | SPY | +24.27% |
| 5 | TLT | +2.09% |
| 6 | SHY | ~+4–5% (cash proxy) |

**Preliminary signal: BUY IWM** — consistent with prior weeks. Must re-verify with authoritative script before executing.

### Sizing Mode
N/A — Dual Momentum uses 100% equity in one asset. No VIX-based sizing. No intraday stops.

### Trade Ideas
None — strategy is monthly-only (next rebalance: 2026-07-31). No intraday action warranted.
Overdue IWM buy (from Jun 30) must be executed ASAP on API restoration — verify signal first.

### Decision
**NO TRADE** — not a rebalance day. Strategy holds cash until API restored + rebalance confirmed.

### Action Required (human) — Day 18 ESCALATION
Whitelist in remote execution environment egress policy:
- `paper-api.alpaca.markets` (Alpaca trading + data)
- `api.perplexity.ai` (research)
- `api.telegram.org` (alerts)
- Yahoo Finance hosts (`query1.finance.yahoo.com`, `query2.finance.yahoo.com`)
The overdue IWM rebalance has now been pending 5 trading days since Jun 30.

---

## 2026-07-06 — Pre-Market (Monday) ⚠️ API STILL BLOCKED — Day 16

**Status:** API BLOCKED — Day 16 of blockage (Jun 22–Jul 6). Alpaca, Perplexity, Telegram all blocked by proxy egress (HTTP 000). WebSearch fallback used. Proxy status endpoint shows no relay failures but CONNECT to all external APIs continues to fail.

**Strategy:** Dual Momentum ETF Rotation (Antonacci)
**Today's action:** NONE — not a rebalance day (next: July 31, 19 trading days away)
**Overdue rebalance:** BUY IWM (Jun 30 missed, still pending API restoration)

### Account State
- Cannot retrieve via API (blocked). Last known: $100,000.00 equity, 0 positions (Day 0 baseline, 2026-05-09).
- Sizing mode: N/A — Dual Momentum uses 100% equity in single asset, no VIX-based sizing.

### Market Context (WebSearch fallback)

**Indices / Futures (premarket):**
- S&P 500 futures: +0.4% premarket
- Nasdaq-100 futures: +1.1% (tech rebound; SpaceX Nasdaq-100 inclusion Tuesday)
- Dow Jones: record close 52,900.07 last week
- Markets positive after July 4 holiday weekend

**VIX:** ~15.97 (MODERATE — 52-week range 13.38–35.30) *(for reference only; not used in Dual Momentum sizing)*

**Oil:**
- WTI: ~$68–69/bbl (down; Saudi exports recovering toward pre-conflict levels)
- Brent: ~$71–72/bbl

**Sectors (YTD 2026):**
- Best: XLK Technology +33%, XLE Energy +21%, XLI Industrials +20%, XLF Financials +1.53% today, XLV Healthcare +2.63% today
- Mixed: Semis split — equipment makers (Lam, AMAT, KLA) +4% today; but MU −5.5%, INTC −5.3%, AMD −4.3% (profit-taking)
- Worst: Enterprise software (SaaSpocalypse; S&P 500 Software Index −19% in Feb 2026)

**Economic Calendar (this week + near-term):**
- Tuesday Jul 7: SpaceX joins Nasdaq-100 (sell-the-news risk)
- Wednesday Jul 8: FOMC Meeting Minutes (key — watch for rate hike signals)
- July 14: CPI release; July 15: PPI release
- July 28–29: FOMC meeting (9 officials expect ≥1 rate hike by end of 2026; current rate 3.50–3.75%)
- June jobs: initial claims 215K (below 221K expected) → dovish read

### Dual Momentum Signal — WebSearch Estimate (authoritative script blocked)

**12-Month Trailing Returns (estimated from current prices / search data):**

| Rank | Ticker | ~12M Return | Notes |
|------|--------|-------------|-------|
| 1 | IWM | +38.72% | Authoritative data — Yahoo Finance via agent |
| 2 | QQQ | ~+30–33% | Estimated (XLK proxy +33% YTD; QQQ slightly lower) |
| 3 | GLD | +22.27% | Authoritative data — Yahoo Finance via agent |
| 4 | SPY | +19.10% | Authoritative data — Yahoo Finance via agent |
| 5 | TLT | +2.09% | Authoritative data — Yahoo Finance via agent |
| 6 | SHY | ~+3–5% | Estimated (short-duration, near cash return) |

**Absolute filter:** SPY 12-month return +19.10% → PASSES (>0%)
**Signal:** IWM #1 → BUY IWM (consistent with Jun 29–Jul 5 estimates of ~+41–42%; actual authoritative 12m is +38.72%)
**Authoritative script:** Cannot run (`dual_momentum_signal.py` needs yfinance/Yahoo Finance, also blocked)

### Trade Decision
**NO TRADE — not a rebalance day.** Monthly rebalance is July 31.
- Overdue Jun 30 rebalance (BUY IWM) still pending API restoration.
- Even if APIs were accessible today, the strategy does not permit trading outside of rebalance dates.
- Signal confidence: HIGH — IWM leading by a wide margin (+38.72% vs. QQQ ~+30-33%). Ranking unlikely to change by July 31.

### Risk Factors
- FOMC Minutes (Jul 8) could roil bonds/equities if hawkish surprise
- SpaceX Nasdaq-100 inclusion (Jul 7) is a sell-the-news risk for QQQ/tech
- CPI July 14 — any upside surprise could trigger rate-hike pricing and weigh on small-caps (IWM)
- IWM near 52-week high ($302.72); some technical resistance
- API blockage: 16 consecutive trading days with zero account access or trade execution

### Action Required (human)
Whitelist `paper-api.alpaca.markets`, `api.perplexity.ai`, `api.telegram.org`, and Yahoo Finance hosts in the remote execution environment's egress policy. The June 30 rebalance is now 4 trading days overdue — the account remains in cash, missing IWM's +19% YTD gain. The next opportunity to execute is when APIs are restored OR at the July 31 regular rebalance (whichever comes first).

---

## 2026-07-03 — Pre-Market (Friday) — MARKET CLOSED (Holiday)

**Status:** API BLOCKED — Day 14 of blockage (Jun 22–Jul 3). Alpaca, Perplexity, Telegram all blocked by proxy egress (403 connect_rejected). WebSearch fallback used.

**Market Status:** US stock markets (NYSE, Nasdaq) FULLY CLOSED today — July 4 (Independence Day) falls on Saturday, so the holiday is observed on Friday July 3. The half-day close was Thursday July 2 at 1 PM ET. Markets reopen Monday July 6.

### Market Context (via WebSearch — data as of July 2 close)

| Indicator | Value | Note |
|-----------|-------|------|
| VIX | ~16.15 | Down 2.65% from prev day; MODERATE (15–25 range) |
| S&P 500 | 7,483.24 | Essentially flat on July 2 (+0.01); Dow hit ATH (+1.14%) |
| Nasdaq-100 | — | −1.61% on July 2 (tech selloff) |
| WTI oil | ~$67.95/bbl | Near 2026 lows |
| June NFP | 57K | Massive miss vs 113K consensus; prior months revised −74K total |
| Unemployment | 4.2% | Labor force participation fell to 61.5% (lowest since Mar 2021) |

### Key Macro Events (since last entry)
- **June NFP Miss (released July 2):** Only 57K jobs vs 113K expected. Weak labor market quiets Fed rate-hike talk. Market reaction: Dow +1.14% (rotation to defensives/value), QQQ −1.61% (risk-off for growth), S&P flat.
- **Dow at all-time high:** 52,900.07 on July 2 — rotation from tech into cyclicals/value on soft jobs data.
- **Fed implications:** Weak NFP reduces probability of rate hikes; potentially positive for TLT (bonds) and GLD (gold) but not reflected yet in 12-month rankings.

### Sizing Mode
**MODERATE** — VIX 16.15 (15–25 range). Strategy is Dual Momentum (100% in single asset), VIX-based sizing is NOT applicable. Included for legacy reference only.

### Dual Momentum Signal (WebSearch estimate, NOT authoritative)
- SPY absolute filter: PASSES (12m return ~+25.67% > 0%)
- Estimated ranking: IWM (~+41.75%) > GLD/QQQ > SPY (~+25.67%) > TLT (~+4.5%)
- Preliminary signal: **IWM** — consistent across all estimates since June 22
- Authoritative signal CANNOT be run — `dual_momentum_signal.py` requires yfinance, which requires Yahoo Finance (blocked)

### Trade Ideas
None — market closed (holiday). Strategy is monthly rebalance only. Next scheduled: 2026-07-31.

**Overdue rebalance from June 30 (BUY IWM) still pending API restoration.** When APIs are unblocked, re-run `python3 scripts/dual_momentum_signal.py` before placing any order.

### Decision
**NO TRADE — market closed (holiday). APIs still blocked (Day 14).**

### Action Required
1. Whitelist `paper-api.alpaca.markets`, `api.perplexity.ai`, `api.telegram.org`, and Yahoo Finance hosts in remote execution environment egress policy.
2. On first routine run with API access restored (Monday July 6 or later): re-verify signal with authoritative script, then execute overdue IWM buy.

---

## 2026-07-02 — Pre-Market (Thursday)

**Status:** API BLOCKED — 9th trading day (Jun 22–Jul 2). Alpaca, Perplexity, Telegram all blocked by proxy egress (403). WebSearch fallback used. yfinance unavailable (module missing).

**Strategy:** Dual Momentum ETF Rotation (Antonacci)
**Universe:** SPY, QQQ, IWM, TLT, GLD, SHY
**Today's action required:** NONE — NOT a rebalance day. Next rebalance: **2026-07-31 (Friday)** — last trading day of July. 20 trading days away.

### ⚠️ MISSED REBALANCE — 2026-06-30

The June 30, 2026 rebalance (bot's first-ever trade) was NOT executed. API access remained blocked throughout. No position was opened. Account remains in idle cash at $100,000 baseline. Preliminary web signal pointed to **IWM** as the June signal (#1 by ~12-month return ~+41.75%). This represents a missed opportunity; the bot should have been in IWM since June 30.

**Human action required:** No corrective trade should be placed mid-month outside the rebalance schedule. Next execution window is July 31.

### API Access Status
- `paper-api.alpaca.markets:443` → 403 connect_rejected (9th day blocked)
- `api.perplexity.ai:443` → 403 connect_rejected (9th day blocked)
- `api.telegram.org:443` → 403 connect_rejected (9th day blocked)
- `yfinance` module → not installed (signal script cannot run)
- GitHub MCP: available

### Account State
Cannot retrieve — API blocked. Last known: no open positions, $100,000.00 starting equity (baseline 2026-05-09).

### Market Context (via WebSearch — July 2, 2026)
- **VIX:** 16.59 close (Jul 1) → **MODERATE** (15–25) — N/A for Dual Momentum sizing
- **S&P 500 futures:** ES Sep −1.31%, NQ Sep −2.60% — broad tech selloff this morning
- **WTI oil:** $67.95/bbl (below $69, lowest since Feb 27) — US-Iran peace talks progressing, Strait of Hormuz shipping recovering
- **Key events today (Jul 2):**
  - ADP private payrolls: +98K (below consensus — soft labor)
  - June NFP, unemployment, hourly earnings — all due today
  - June factory orders due today
  - Fed Chair Kevin Warsh speaking at market open (closely watched)
- **Sector leaders 2026 YTD:** Energy (+22% YTD, geopolitical tailwind), Consumer Staples (defensive rotation)
- **Sector laggards:** Technology (AI capex doubt, cooling post-run), Financials (Fed pause)
- **Market tone:** Risk-off pre-market. Tech leading decline. Jobs data + Warsh comments key for direction.

### Sizing Mode
N/A — Dual Momentum uses 100% equity in one asset, no VIX-based sizing.

### Dual Momentum Signal Preview (web estimates — July 2026)
SPY 12m return estimated positive → absolute filter likely passes.

| Ticker | Est. 12-Month Return | Rank |
|--------|---------------------|------|
| IWM    | ~+41.75%            | #1 (likely) |
| GLD    | ~+32%               | #2 (est.) |
| QQQ    | ~+30%               | #3 (est.) |
| SPY    | ~+25.67%            | #4 |
| TLT    | ~+5%                | #5 (est.) |

**Preliminary July signal: IWM** — pending confirmation with live yfinance on July 31.
Note: IWM at risk if small-cap rotation reverses; today's risk-off tone and soft jobs data may pressure IWM premarket.

### Trade Ideas
None — strategy is monthly-only. No intraday or discretionary action warranted.

### Risk Factors
- Persistent API blockage (9 trading days) — critical for July 31 rebalance
- yfinance not installed — signal script cannot run without it (`pip install yfinance`)
- Fed Chair Warsh hawkish tone risk — could spike VIX, pressure equities
- Soft ADP print + potential weak NFP = risk-off momentum building
- IWM signal could shift if small-cap underperforms meaningfully before July 31

### Decision
**NO TRADE** — not rebalance day. Next window: July 31.

### Action Required (human)
1. **CRITICAL:** Restore proxy egress to `paper-api.alpaca.markets`, `api.perplexity.ai`, `api.telegram.org` before July 31.
2. **CRITICAL:** `pip install yfinance` in the environment so signal script can run.
3. Missed June 30 rebalance — bot could have been in IWM for July. No corrective action mid-month (per strategy rules).

---

## 2026-07-01 — Pre-Market (Wednesday) ⚠️ OVERDUE REBALANCE — APIS STILL BLOCKED

**Status:** API BLOCKED — 11th consecutive trading day (Jun 22–Jul 1). Alpaca, Perplexity, Telegram all blocked by proxy egress policy (connect_rejected 403). Fell back to native WebSearch for market data.

**Strategy:** Dual Momentum ETF Rotation (Antonacci)
**Universe:** SPY, QQQ, IWM, TLT, GLD, SHY
**Today's action required:** NONE TODAY — not a rebalance day. Next rebalance: **2026-07-31 (last trading day of July).**
**Overdue rebalance status:** June 30 rebalance was missed (API blocked). When APIs restore, execute overdue BUY IWM trade immediately after running authoritative `dual_momentum_signal.py`.

### API Access Status
- `paper-api.alpaca.markets:443` → 403 connect_rejected (11th day blocked)
- `api.perplexity.ai:443` → HTTP 000 (blocked, empty response despite exit 0)
- `api.telegram.org:443` → HTTP 000 (blocked)
- GitHub MCP: available (used for git push)

### Account State
Could not retrieve — API blocked. Last known: no open positions, $100,000.00 equity (baseline 2026-05-09). Account has been idle since inception due to consecutive API blockage preventing the June 30 rebalance.

### Market Context (via WebSearch fallback — July 1, 2026)
- **VIX:** 17.65 (June 30 close); June range 15.18–23.34, June avg 16.41 → **MODERATE** (15–25)
- **S&P 500 futures:** +0.72% premarket; sentiment mixed — "slipping after best quarter since 2020"
- **Q2 2026 performance:** Best quarterly return for US equities since pandemic (2020) — Nasdaq +1.52% and S&P +0.79% on final day of Q2 (June 30)
- **Oil:** WTI ~$70/bbl; Brent ~$72.25/bbl (-0.96%); Iran-US peace talks in Doha ongoing; oil -24.74% past month
- **Key catalysts today:**
  - ISM Manufacturing PMI (June data) due 10:00 AM ET today — May was 54% (highest since May 2022, expansionary)
  - ~12 earnings reports scheduled, no identified major pre-market movers
  - SpaceX joining Nasdaq-100 effective July 7 — bullish for QQQ
- **Leading sectors (Q2/recent):** Semiconductors (runaway leader), Energy, Defense, Industrials, Information Technology
- **Lagging sectors:** Commercial REITs, Consumer Discretionary, Utilities, Communications
- **Geopolitical:** Iran-US peace negotiations progressing in Doha; oil supply risk declining

### Dual Momentum Signal — Preliminary (via WebSearch, NOT authoritative script)
**Preliminary signal: IWM** — IWM ~+42% 12m, #1 rank. Must re-verify with `python3 scripts/dual_momentum_signal.py`.

### Decision
**NO TRADE** — APIs blocked; not a rebalance day.

### Action Required (human) — CRITICAL, DAY 11
Whitelist `paper-api.alpaca.markets`, `api.perplexity.ai`, `api.telegram.org` in egress policy. June 30 rebalance overdue.

---

## 2026-06-29 — Pre-Market (Monday) ⚠️ REBALANCE TOMORROW

**Status:** API BLOCKED — 6th trading day (Jun 22–29). Perplexity, Alpaca, Telegram all blocked by proxy egress policy. Fell back to native WebSearch for market data.

**Strategy:** Dual Momentum ETF Rotation (Antonacci)
**Universe:** SPY, QQQ, IWM, TLT, GLD, SHY
**Today's action required:** NONE — NOT a rebalance day. **REBALANCE IS TOMORROW: 2026-06-30 (last trading day of June).**

### API Access Status
- `paper-api.alpaca.markets:443` → error (still blocked, exit 1 / empty response)
- `api.perplexity.ai:443` → exit 56 (connection refused, still blocked)
- `api.telegram.org:443` → 403 (still blocked)
- GitHub MCP: available (used for git push)

### Account State
Could not retrieve — API blocked. Last known: no open positions (idle in cash since inception). Starting equity: $100,000.00 (baseline 2026-05-09).

### Market Context (via WebSearch fallback — June 29, 2026)
- **VIX:** ~18.41 as of last close (Jun 26); range 15.18–23.34 over past month → **MODERATE** — N/A for Dual Momentum sizing
- **S&P 500 futures:** +0.8% premarket — U.S.-Iran ceasefire talks progressing; both sides to meet Tuesday in Qatar at Tehran's request; market relief rally
- **Oil:** WTI ~$70/bbl (near $68.86–70.79 range), falling 4%+ on Iran peace progress; lowest since early March 2026
- **Key events today:**
  - Alphabet replaces Verizon in the Dow Jones (effective today, Jun 29)
  - SpaceX joining Nasdaq 100 on July 7 (confirmed)
  - Comcast spin-off announcement (+25% premarket) → Charter Communications +20%
  - Iridium (IRDM) +22% — Rocket Lab $8B acquisition announced
  - Baidu AI chip unit Kunlunxin targeting $50B HK IPO
  - Samsung + SK Group expected to announce $1.3T semiconductor/AI investment plan
- **Top sectors:** Consumer Staples, Industrials, Materials; Energy also with Iran ceasefire relief
- **Lagging sectors:** Technology, Communications, Consumer Discretionary, Financials (persistent AI capex doubt)

### Sizing Mode
N/A — Dual Momentum uses 100% equity in one asset, no VIX-based sizing.

### Rebalance Preview — June 30 Signal (web data, approximate)
**SPY absolute filter:** SPY 12m ≈ +25.67% → PASS (positive) → proceed to ranking

| Ticker | Est. 12-Month Return | Rank |
|--------|---------------------|------|
| IWM    | +41.75%             | #1 ← likely signal |
| GLD    | +32.18%             | #2 |
| QQQ    | +29.97%             | #3 |
| SPY    | +25.67%             | #4 |
| TLT    | +4.87%              | #5 |

**Preliminary signal: IWM** (US small cap) — pending confirmation via live script tomorrow.
Note: these are web-sourced estimates; actual signal must come from `python3 scripts/dual_momentum_signal.py` on June 30 with live Yahoo Finance data.

### Rebalance Calendar
- **REBALANCE DATE: TOMORROW — 2026-06-30 (Tuesday)** — last trading day of June
- Action: run `python3 scripts/dual_momentum_signal.py` → compare signal to current holding (none) → buy signal asset at market open
- Expected trade: BUY IWM (pending live confirmation); buy_qty = floor($100,000 / ask_price)
- ⚠️ CRITICAL: Proxy egress MUST be restored before June 30 market open or bot cannot execute its first-ever rebalance trade

### Trade Ideas
None for today — Dual Momentum is monthly-only. All attention on June 30 rebalance.

### Risk Factors
- API blockage (6th trading day) — if not resolved by tomorrow morning, bot cannot execute the rebalance
- IWM signal could shift if small-cap data differs on live run (use script, not web estimates)
- Iran ceasefire progress could reverse overnight — monitor
- Fed speakers / economic calendar unknown for today's session

### Decision
**NO TRADE** — not rebalance day. Tomorrow is critical.

### Action Required (human)
**URGENT:** Proxy egress to `paper-api.alpaca.markets`, `api.perplexity.ai`, and `api.telegram.org` must be whitelisted BEFORE June 30 market open. Tomorrow the bot executes its first-ever trade (likely BUY ~$100k of IWM). Without API access, the trade cannot be placed.

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

## 2026-06-30 — REBALANCE DAY (Tuesday) ⚠️ TRADE FAILED — API STILL BLOCKED

**Status:** API BLOCKED — 9th consecutive trading day (Jun 22–30). **TODAY WAS THE REBALANCE DAY** — confirmed via `python3 scripts/is_rebalance_day.py` (exit 0). The bot's first-ever trade could NOT be executed.

### API Access Status — Comprehensive Test
All outbound egress confirmed blocked by the proxy's organization policy (gateway 403 on CONNECT, not a credential issue):
- `paper-api.alpaca.markets:443` → 403 connect_rejected
- `api.perplexity.ai:443` → 403 connect_rejected
- `api.telegram.org:443` → 403 connect_rejected
- `fc.yahoo.com:443` / Yahoo Finance (via `yfinance`, installed fresh this run) → 403 connect_rejected
- Confirmed via proxy status endpoint (`$HTTPS_PROXY/__agentproxy/status`): all four hosts logged as `connect_rejected` / "gateway answered 403 to CONNECT (policy denial or upstream failure)". Per proxy README, 403s are organization egress policy denials — not to be retried or routed around.
- GitHub (git push): available — this commit went through.

### Signal — Computed via WebSearch Fallback (NOT the authoritative script — yfinance also blocked)
Could not run `scripts/dual_momentum_signal.py` (requires yfinance → Yahoo Finance, blocked). WebSearch estimate of trailing 12-month total returns as of ~June 26–30, 2026:

| Rank | Ticker | ~12M Return |
|------|--------|-------------|
| 1 | IWM | ~+42% |
| 2 | QQQ | ~+30% |
| 3 | GLD | ~+32% (QQQ/GLD order uncertain, both clearly behind IWM) |
| 4 | SPY | ~+20% |
| 5 | TLT | ~+4.5% |

SPY 12-month return positive (~+20%) → absolute filter PASSES. Preliminary signal: **BUY IWM** (consistent with the 2026-06-29 preliminary estimate). This is a web-search approximation only — the authoritative `dual_momentum_signal.py` script must be re-run once Yahoo Finance/Alpaca access is restored, before any trade is placed, since exact ranking could differ from estimate.

### Trade Outcome
**NO TRADE EXECUTED.** Account state, current holding, and order placement are all unreachable — Alpaca API fully blocked. This is the bot's first scheduled rebalance since deployment (Phase 2 start), and it has now been missed due to infrastructure (proxy egress), not a strategy decision.

### Decision
**NO TRADE — BLOCKED, NOT A SIGNAL DECISION.** As soon as API access is restored, run `python3 scripts/dual_momentum_signal.py` for the authoritative signal, then execute the BUY immediately (late rebalance, not skipped) and log/notify per `routines/market-open.md`.

### Action Required (human) — CRITICAL, ESCALATING
**9 consecutive trading days of total egress blockage (Jun 22–30).** This is no longer a "monitor" situation — the bot has now missed its actual rebalance date. Whitelist `paper-api.alpaca.markets`, `api.perplexity.ai`, `api.telegram.org`, and Yahoo Finance hosts (`*.yahoo.com`, `query1.finance.yahoo.com`, `query2.finance.yahoo.com`, `fc.yahoo.com`) in the remote execution environment's egress policy immediately. Once restored, the very next routine run should treat this as an overdue rebalance and execute on its first opportunity.

---
