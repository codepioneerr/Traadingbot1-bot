# Research Log

Daily pre-market research entries. Each entry records market context, sizing mode, and trade ideas for that day.
Format: prepend new entries at the top (most recent first).

---

## 2026-07-15 — Morning Research (Wednesday) ⚠️ API STILL BLOCKED — Day 26

**Strategy:** Dual Momentum ETF Rotation | **Next rebalance:** 2026-07-31 (12 trading days)
**Overdue rebalance:** BUY IWM (June 30 missed) — signal re-confirmed via WebSearch below

### API Access Status
All outbound egress still blocked (Day 26: Jun 22 – Jul 15):
- `paper-api.alpaca.markets:443` → 403 connect_rejected (proxy policy denial)
- `api.telegram.org:443` → 403 connect_rejected
- `api.perplexity.ai:443` → 403 connect_rejected
Account data unavailable. Research conducted via WebSearch fallback.

### Account Snapshot (last known)
- **Equity:** $100,000.00 (Day 0 baseline, 2026-05-09 — API blocked 26 trading days)
- **Cash:** $100,000.00 (100% — no position taken; overdue IWM rebalance pending)
- **Positions:** 0 (awaiting API restoration)

### Market Context (via WebSearch — July 15, 2026)

**VIX:** ~16.50 (closed Jul 14 at 16.50, -3.85% day; 30d range 14.96–20.72) → **Sizing mode: MODERATE** (N/A for Dual Momentum — noted for awareness only)

**S&P 500 / Nasdaq Futures (premarket):**
- ES (S&P 500): +0.2%
- NQ (Nasdaq-100): +0.5%
- Drivers: Cool inflation data, ASML raised AI outlook, PayPal +20% on $53B acquisition rumor

**Oil:**
- **WTI:** ~$78.08/bbl
- **Brent:** ~$84.73–$85.92/bbl (1-month high, +19% from pre-conflict level)
- Context: US-Iran active military conflict — Day 3 of US airstrikes; Iran retaliated hitting 2 supertankers in Strait of Hormuz; US military escorts keeping ~8.5M bbl/day flowing

**Earnings Today (BMO):**
- ASML (+3% premarket) — beat, raised AI-driven 2026 revenue forecast
- BLK (BlackRock) — +3.8% premarket, earnings beat
- JNJ, MS, PGR, BNY, PNC, KMI, UAL, JBHT

**Economic Events Today:**
- June PPI & Core PPI (8:30 AM ET) — key inflation read post-CPI
- Fed Chair Warsh — Senate Banking Committee testimony (10:00 AM ET)
- Fed Beige Book — releasing today
- Retail Sales & Jobless Claims due Jul 16

**Premarket Movers:**
- PYPL +20% ($53B acquisition offer from Stripe/Advent at $60.50/share)
- BABA +6% (Apple Intelligence China regulatory approval)
- PNR -20.7% (slashed Q2/FY guidance, CFO resigned)
- ELV -8.3%

**S&P 500 Sector Performance (current week):**
- Best: Communications (+4.9%), Financials (+3.5%), Consumer Discretionary (+2.3%), Health Care (+2.2%)
- Worst: Utilities (-1.1%), Energy (-1.0%), Real Estate (-0.8%)

### IWM / Dual Momentum Signal Estimate (via WebSearch — NOT authoritative script)

| Rank | Ticker | Est 12M Total Return | Notes |
|------|--------|---------------------|-------|
| 1 | IWM | ~+39–41% | Current ~$294.64; 52w low $212.34; YTD +22% — best year since 1991 |
| 2 | GLD | ~+32% | Gold elevated on geopolitical/inflation bid |
| 3 | QQQ | ~+30% | Tech slightly underperforming vs SPY on oil/geopolitical pressure |
| 4 | SPY | ~+20–22% | Absolute filter: PASSES (positive) |
| 5 | TLT | Low single digit | Rate/oil uncertainty; under pressure |
| — | SHY | ~+4–5% | Cash proxy |

**SPY 12m: ~+20-22% → Absolute filter PASSES**
**Preliminary Signal: BUY IWM** (26th consecutive session with same preliminary reading)
*Must re-verify with `python3 scripts/dual_momentum_signal.py` before any trade, once API restored.*

### Overdue Rebalance Note
June 30 rebalance missed (Day 8 of blockage). As soon as Alpaca API is accessible, run `dual_momentum_signal.py` — if IWM still #1, BUY IWM immediately (overdue rebalance, not a new discretionary trade). Do not wait for July 31.

### Risk Factors
- **US-Iran active military conflict (Day 3):** Straight of Hormuz partially disrupted; crude +19% from pre-conflict levels; inflationary, risk-off
- **PPI data (today):** Post-CPI hot print could revive rate hike fears despite June CPI beat
- **Fed Chair Warsh testimony (10 AM ET):** Hawkish surprise could pressure both equities and TLT
- **Oil elevated at $78-85/bbl:** Energy input costs rising broadly; consumer staples and transportation headwind
- **IWM near all-time high ($302.72):** Small caps sensitive to domestic risk-off; geopolitical escalation could drive pullback from ATH
- **Stripe/PayPal deal uncertainty:** M&A speculation, may not close; if denied, sharp reversal

### Decision
**NO TRADE** — not a rebalance day. Strategy permits no intraday or discretionary action between monthly rebalances. APIs still blocked regardless — no trades possible. Next rebalance: 2026-07-31.

---

## 2026-07-14 — Morning Research (Tuesday, Day 25 of API blockage) ⚠️ OVERDUE REBALANCE PENDING

**Strategy:** Dual Momentum ETF Rotation | **Next rebalance:** 2026-07-31 (12 trading days)
**Overdue rebalance:** BUY IWM (June 30 missed) — signal re-confirmed via WebSearch below

### API Access Status
All outbound egress confirmed blocked (Day 25: Jun 22–Jul 14):
- `paper-api.alpaca.markets:443` → 403 connect_rejected (proxy policy denial)
- `api.telegram.org:443` → 403 connect_rejected
- `api.perplexity.ai:443` → 403 connect_rejected
Research conducted via WebSearch fallback.

### Market Context (via WebSearch)

**VIX:** 15.35 (−3.09% intraday, range 14.96–16.06) → **Sizing mode: MODERATE** (VIX 15–25)

**S&P 500 / Futures:**
- Pre-CPI: flat to −0.2%, traders cautious ahead of 8:30am ET print
- Post-CPI: dovish surprise should be a positive catalyst at open

**CPI June 2026 (Released 8:30am ET today — MASSIVE DOVISH BEAT):**

| Metric | Expected | Actual |
|--------|----------|--------|
| Headline MoM | −0.2% | **−0.4%** |
| Headline YoY | 3.8% | **3.5%** |
| Core MoM | +0.2% | **0.0%** |
| Core YoY | 2.9% | **2.6%** |

Energy fell 5.7% in June (US-Iran interim deal → gasoline plunged). Largest single-month headline drop since April 2020. Core flat MoM — the number the Fed watches most closely. Rate-cut odds for Jul 28–29 FOMC meeting surging.

**Oil:** WTI ~$79.50/bbl (+2% today) — bouncing off lows post-Iran deal. Still elevated but war premium removed.

**Key Events Today:**
- CPI June 2026 print (above — major dovish beat)
- Fed Chair Warsh testifying before House Financial Services Committee (first Humphrey-Hawkins appearance as Chair) — "hinge point in history"; watch for any pushback on rate cuts
- Big bank Q2 earnings: JPM ($6.14 EPS vs $5.85 exp; $58.02B rev vs $50.19B exp — huge beat), WFC, GS, BAC, C — broadly beating

**Sectors this week (through Jul 10):**
- Best: Basic Materials +0.84%, Technology +0.76%, Consumer Discretionary +0.75%, Energy +0.66%, Financials +0.38%
- Worst: Healthcare −1.20%, Capital Goods −0.04%
- Note: Financials should surge today on bank earnings beats + CPI rate-cut catalyst

**IWM last close (Jul 13):** $295.99 | 52-week range: $212.34–$302.72

### Dual Momentum Signal Estimate (via WebSearch — NOT authoritative script)

| Rank | Ticker | ~12M Total Return | Notes |
|------|--------|-------------------|-------|
| 1 | IWM | ~+39–41% est. | Near 52-week high $302.72; SPY absolute filter passes |
| 2 | GLD | ~+32–33% est. | Gold resilient on geopolitical uncertainty |
| 3 | QQQ | ~+30–32% est. | Tech momentum intact |
| 4 | SPY | ~+20–22% est. | Absolute filter: PASSES (positive) |
| 5 | TLT | Low single-digits | Pressure from rates uncertainty |
| — | SHY | ~+4–5% est. | Cash proxy |

**Preliminary Signal: BUY IWM** (25th consecutive session with same preliminary reading)
*CPI beat reinforces IWM signal — small-caps historically outperform when rate-cut expectations surge.*
*Must re-verify with `python3 scripts/dual_momentum_signal.py` before any trade, once API restored.*

### Risk Factors
- Warsh hawkish pushback risk: if he emphasizes tariff inflation or refuses to validate July rate cut, market reverses
- US-Iran: interim deal fragile — any breakdown re-spikes oil and crushes the CPI narrative
- Earnings execution risk: bank beats are priced in → any micro-miss on guidance could cap upside
- IWM near 52-week high ($302.72) — entering at these levels when/if rebalance executes

### Today's Action
**NOT a rebalance day.** Next scheduled rebalance: 2026-07-31. No trades. No intraday action permitted by strategy.

**Overdue rebalance note:** The June 30 rebalance was missed due to API blockage. As soon as APIs are restored, run `dual_momentum_signal.py` → if IWM still #1, BUY IWM immediately. Do not wait for July 31. CPI dovish beat strengthens the case for IWM momentum continuing.

**SPY 12m: ~+20–22% → Absolute filter PASSES**
**Preliminary Signal: BUY IWM** (25th consecutive session with same preliminary reading)

### Decision
**NO TRADE** — not rebalance day. APIs blocked — no trades possible regardless. Strategy permits no intraday or discretionary action between monthly rebalances.

**Account Snapshot:** $100,000.00 (last known — Day 0 baseline, 2026-05-09; API blocked for 25 days)

## 2026-07-10 — Morning Research (Friday) ⚠️ API STILL BLOCKED — Day 22

**Strategy:** Dual Momentum ETF Rotation | **Next rebalance:** 2026-07-31 (15 trading days)
**Overdue rebalance:** BUY IWM (June 30 missed) — signal re-confirmed via WebSearch

### API Access Status
All outbound egress confirmed blocked (Day 22: Jun 22–Jul 10):
- `paper-api.alpaca.markets:443` → 403 connect_rejected (proxy policy denial, confirmed via `$HTTPS_PROXY/__agentproxy/status` at 13:05 UTC)
- `api.telegram.org:443` → blocked (no output from curl)
- `api.perplexity.ai:443` → blocked (no output from curl)
Research conducted via WebSearch fallback.

### Market Context (via WebSearch)

**VIX:** 16.07 (opened 16.58, intraday range 15.93–17.27) → **Sizing mode: MODERATE** (if applicable)

**S&P 500 / Index Futures:**
- ES (S&P 500 E-Mini): ~+0.2%
- NQ (Nasdaq-100 E-Mini): ~−0.2%
- Dow futures: +0.2%
- Markets diverging ahead of SK Hynix mega-IPO

**Key Catalyst Today — SK Hynix IPO (SKHY):**
- $26.5B raised at $149/ADS — largest-ever US listing by a foreign company (beats Alibaba's $25B in 2014)
- Debuting on Nasdaq today as a test for AI trade / HBM chip demand
- SK Hynix holds >50% of HBM market; net income Q1 2026: $26.6B; Q2 earnings Jul 22
- SpaceX ($85.7B, Jun 2026) is the only larger recent listing globally
- NQ futures slipping slightly as semiconductor momentum cools vs. earlier July

**Sector Momentum (week of Jul 6–10):**
- **Top:** Technology (weekly leader despite early-July wobble), Industrials, Real Estate; Financials and Healthcare entering "improving" quadrant
- **Avoid:** Energy, Utilities (slipped in rankings); Momentum ETF itself -6.6% in July through Thu; semis -11.4% in July
- Note: Market-wide rotation occurring — high-momentum tech/AI trade under pressure

**Economic Events Today:** No major data releases (CPI Jul 14, FOMC Jul 29)

### Dual Momentum Signal Estimate (via WebSearch — NOT authoritative script)

| Rank | Ticker | ~12M Total Return | Notes |
|------|--------|-------------------|-------|
| 1 | IWM | ~+34.78% | WebSearch data (PortfoliosLab); down slightly from ~+40% prior estimates |
| 2 | GLD | ~+32% est. | Prior confirmed; no update today |
| 3 | QQQ | ~+29–31% est. | Under early-July pressure from semis; prior est. +30.58% |
| 4 | SPY | ~+20.42% | Absolute filter: PASSES (positive) |
| 5 | TLT | <+5% est. | Rates/oil headwind |
| — | SHY | ~+4–5% est. | Cash proxy |

**Preliminary Signal: BUY IWM** (Day 22 consecutive with same reading) — absolute filter passes, IWM #1.
*IWM last known price: ~$293.48 (Jul 8 close). Must re-verify with `python3 scripts/dual_momentum_signal.py` before any trade once API restored.*

### Today's Action
**NOT a rebalance day.** Next scheduled rebalance: 2026-07-31. No trades. No intraday action permitted by strategy.

**Overdue rebalance note:** June 30 rebalance still pending API restoration. As soon as APIs are restored, run `dual_momentum_signal.py` → if IWM still #1, BUY IWM immediately. Do not wait for Jul 31.

### Risk Notes
- SK Hynix IPO (SKHY) listing today: AI trade test — success supports IWM sentiment; weak debut could amplify tech/semi rotation
- Strait of Hormuz watch: oil supply risk remains elevated from US-Iran conflict (Day 3+)
- VIX 16.07 (MODERATE) — down slightly from yesterday's 16.90; markets stabilizing
- Momentum trade broadly under pressure in early July — relevant for IWM long-term thesis monitoring
- Bond yields stubbornly high (noted in futures commentary) — headwind for growth stocks, mixed for IWM

### Decision
**NO TRADE** — not rebalance day. Strategy permits no intraday or discretionary action. API blocked anyway.

---

---

## 2026-07-09 — Morning Research (Thursday) ⚠️ API STILL BLOCKED — Day 20

**Strategy:** Dual Momentum ETF Rotation | **Next rebalance:** 2026-07-31 (16 trading days)
**Overdue rebalance:** BUY IWM (Jun 30 missed) — signal re-confirmed via WebSearch below

### API Access Status
All outbound egress confirmed blocked (Day 20: Jun 22–Jul 9):
- `paper-api.alpaca.markets:443` → 403 connect_rejected (proxy policy denial)
- `api.telegram.org:443` → 403 connect_rejected
- `api.perplexity.ai:443` → 403 connect_rejected
- `yfinance` → module not installed (signal script cannot run)
Research conducted via WebSearch fallback.

### Account State
Could not retrieve — Alpaca API blocked. Last known: $100,000.00 (Day 0 baseline, 2026-05-09). No positions held.

### Market Context (WebSearch fallback — July 9, 2026)

| Indicator | Value | Notes |
|-----------|-------|-------|
| VIX | 16.90 (+4.8%) | MODERATE — elevated on US-Iran escalation |
| S&P 500 futures | Modestly higher | 85% probability of up open (Polymarket); recovery after Wed dip |
| WTI crude | ~$74.20/bbl | Wednesday spike to $75.60–$76.12 (+7%); Brent ~$78/bbl |
| IWM last close | $293.48 (Jul 8) | 52-wk range $212.34–$302.72; flat/slightly down on week |
| Earnings | PepsiCo (PEP) beat | EPS $2.20 vs $2.19 est., rev +6.4% YoY, guidance maintained |

**Dominant catalyst:** US launched 2nd round of airstrikes on Iran early Thursday; Tehran threatened large-scale retaliation; Strait of Hormuz supply risk driving crude higher and inflation fears.

**Best sectors this week:** Energy (XLE) +2%+ (Iran/oil tailwind), Diamondback, Occidental, Valero led.
**Worst sectors this week:** Materials (−3% Wed), Technology (−2%), Semiconductors (−4.5%).

**Upcoming events:** Weekly Jobless Claims (today 8:30 AM ET) | CPI Jul 14 | PPI Jul 15 | FOMC Jul 29.

### Dual Momentum Signal Estimate (WebSearch — NOT authoritative script)

| Rank | Ticker | ~12M Total Return | Notes |
|------|--------|-------------------|-------|
| 1 | IWM | ~+39% est. | Price return: $212.34→$293.48 ≈ +38.2% + ~1.2% div; WebSearch table omitted IWM — estimated from 52-week range data |
| 2 | QQQ | +29.4% | Confirmed via WebSearch (Invesco source) |
| 3 | GLD | +24.0% | Confirmed via WebSearch |
| 4 | SPY | +19.6% | Absolute filter: PASSES (>0%) |
| 5 | TLT | +4.9% | Under pressure: rates/oil uncertainty |
| 6 | SHY | ~4–5% | Cash proxy |

**Note:** WebSearch agent's return table omitted IWM — IWM estimated from 52-week range ($212.34→$293.48) and prior authoritative estimates (+38.72% Jul 6, +34.78% Jul 7). IWM remains #1 by a wide margin (~10pp over QQQ).
**Preliminary Signal: BUY IWM** (consistent with previous 9 sessions) — absolute filter passes, IWM #1.
*Must re-verify with `python3 scripts/dual_momentum_signal.py` before any trade, once API restored.*

### Sizing Mode
N/A — Dual Momentum uses 100% equity in one asset. No VIX-based sizing. VIX 16.90 = MODERATE (noted for reference only).

### Trade Ideas
None — strategy is monthly-only (next rebalance: 2026-07-31). No intraday action warranted.
Overdue IWM buy (from Jun 30) must be executed ASAP on API restoration — verify signal first.

### Risk Notes
- US-Iran conflict escalating (Day 2 of airstrikes) — supply disruption risk, crude elevated, inflation fears
- FOMC July 29 — money markets now pricing rate hike by October due to renewed inflation
- IWM sensitivity: small caps / domestic focus; oil-driven inflation risk-off could weigh short-term
- CPI July 14 — upside surprise could reprice rates, pressure all risk assets
- IWM near recent highs ($302.72 52-week high); some technical resistance

### Decision
**NO TRADE** — not a rebalance day. Strategy permits no intraday or discretionary action.
Next rebalance: 2026-07-31 (16 trading days).

### Action Required (human) — Day 20 ESCALATION
Whitelist in remote execution environment egress policy:
- `paper-api.alpaca.markets` (Alpaca trading + data)
- `api.perplexity.ai` (research)
- `api.telegram.org` (alerts)
- Yahoo Finance hosts (`query1.finance.yahoo.com`, `query2.finance.yahoo.com`, `fc.yahoo.com`)
**20 consecutive trading days blocked.** The overdue IWM rebalance from Jun 30 is now 7 trading days overdue. The account has been sitting in cash, missing IWM's ~+40% 12-month run.

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

## 2026-07-13 — Morning Research (Monday) ⚠️ API STILL BLOCKED — Day 24

**Strategy:** Dual Momentum ETF Rotation | **Next rebalance:** 2026-07-31 (13 trading days)
**Overdue rebalance:** BUY IWM (June 30 missed) — signal re-confirmed below

### API Access Status
All outbound egress confirmed blocked (Day 24: Jun 22–Jul 13):
- `paper-api.alpaca.markets:443` → HTTP 000 (connection failed)
- `api.telegram.org:443` → HTTP 000 (connection failed)
- `api.perplexity.ai:443` → HTTP 000 (connection failed)
Proxy status: no recent relay failures, but egress policy continues to block financial/external APIs.
Research conducted via WebSearch fallback.

### Market Context (via WebSearch)

**VIX:** ~15.03 (↓ ~5.1% from Friday) → **Sizing mode: N/A (Dual Momentum — no VIX sizing)**

**S&P 500 Futures Premarket:**
- ES: ~−0.3% to −0.4% premarket
- Risk-off tone on US-Iran escalation over the weekend
- US renewed strikes near Strait of Hormuz; Iran declared ceasefire over, claimed to close the strait (contested by USCENTCOM)

**Oil / Macro Shock:**
- WTI crude: ~$73.15/bbl (+2.4%)
- Brent crude: ~$78.85–$79.12/bbl (+3.7–4.2%)
- Dominant geopolitical driver today

**Sector Rotation:**
- Top: Energy (XLE), Health Care, Consumer Staples (defensive rotation)
- Worst: Technology (XLK), Industrials, Consumer Discretionary (risk-off)

**Key Events This Week:**
- **July 14 (tomorrow):** CPI 8:30 AM ET — last major inflation read before Jul 28-29 FOMC; Fed Chair Warsh testifies to House Financial Services 10 AM ET
- **July 15:** PPI
- Q2 earnings season begins in earnest: JPM, BAC, GS, WFC, C, NFLX this week; 24% EPS growth consensus

**Earnings Today (Jul 13 pre-market):** Fastenal (FAST) — industrial bellwether

**IWM Price:** ~$295.99 premarket (prev close $297.24)

### Dual Momentum Signal (via WebSearch — NOT authoritative script)

| Rank | Ticker | ~12M Total Return | Notes |
|------|--------|-------------------|-------|
| 1 | IWM | ~+42–44% | Multiple sources; ~42.9% as of Jul 3 |
| 2 | GLD | ~+23% | Gold resilient on geopolitical risk |
| 3 | SPY | ~+22% | ~21.97% trailing 12m |
| 4 | QQQ | ~+18–20% | Tech has underperformed small caps over 12m |
| 5 | TLT | ~+3–5% | Laggard; bonds under rate/inflation pressure |

**SPY 12m: +22% → Absolute filter PASSES**
**Preliminary Signal: BUY IWM** (24th consecutive session with same preliminary reading)
*Must re-verify with `python3 scripts/dual_momentum_signal.py` before any trade, once API restored.*

### Overdue Rebalance Note
June 30 rebalance missed (Day 8 of blockage). As soon as Alpaca API is accessible, run `dual_momentum_signal.py` — if IWM still #1, BUY IWM immediately (overdue rebalance, not a new discretionary trade). Do not wait for July 31.

### Risk Factors
- US-Iran active military conflict: crude oil spike is inflationary, risk-off. CPI tomorrow makes this particularly sensitive.
- Strait of Hormuz closure (even partial/threatened): sustained oil shock could pressure broader equities
- CPI (Jul 14) surprise in either direction: hot CPI → hawkish Warsh → rate-cut expectations pared → bond/equity pressure; cold CPI → relief rally
- IWM ~$296 at premarket — small caps may underperform in geopolitical risk-off environment today

### Decision
**NO TRADE** — not a rebalance day. APIs blocked — no trades possible regardless. Strategy permits no intraday or discretionary action between monthly rebalances.

**Account Snapshot:** $100,000.00 (last known — Day 0 baseline, 2026-05-09; API blocked for 24 days)

---

## 2026-07-08 — Morning Research (Wednesday) ⚠️ API STILL BLOCKED — Day 19

**Strategy:** Dual Momentum ETF Rotation | **Next rebalance:** 2026-07-31 (17 trading days)
**Overdue rebalance:** BUY IWM (June 30 missed) — signal re-confirmed via WebSearch below

### API Access Status
All outbound egress confirmed blocked (Day 19: Jun 22–Jul 8):
- `paper-api.alpaca.markets:443` → 403 connect_rejected (proxy policy denial)
- `api.telegram.org:443` → 403 connect_rejected
- `api.perplexity.ai:443` → 403 connect_rejected
Research conducted via WebSearch fallback.

### Market Context (via WebSearch)

**VIX:** 16.36 (+5.07% intraday) → **Sizing mode: MODERATE** (if applicable)

**S&P 500 / Nasdaq Futures:**
- ES (S&P 500 E-Mini): +0.48%
- NQ (Nasdaq-100 E-Mini): +1.10%
- Note: Futures tumbled sharply early on US-Iran ceasefire collapse before partial recovery

**Oil / Macro Shock:** WTI crude +6.2% to $74.79/bbl; Brent +6.1% to $78.66/bbl — US-Iran ceasefire declared "over" by Trump after fresh strikes. This is the dominant risk driver today.

**Tech Pressure:** AI/semis under pressure — NVDA -1.7%, IBM -3.3%, PLTR -3.1%, AMZN -1.7% premarket. Samsung weak guidance cited.

**Key Economic Events Today:**
- FOMC Minutes (June meeting, first under Chair Kevin Warsh) — key rate-cut signal watch
- EIA Crude Oil Inventories (elevated importance given oil spike)
- MBA Mortgage Applications
- No CPI or jobs data today

**IWM Last Close:** ~$295.52 (Jul 7); 52-week range $212.34–$302.72; YTD outperforming S&P 500

### Dual Momentum Signal Estimate (via WebSearch — NOT authoritative script)

| Rank | Ticker | ~12M Total Return | Notes |
|------|--------|-------------------|-------|
| 1 | IWM | ~+39–40% est. | 52w low $212.34 → $295.52 = ~+39.2% price + ~1.2% div ≈ +40.4% |
| 2 | GLD | +32.18% | Confirmed via FinanceCharts |
| 3 | QQQ | +30.58% | Confirmed via FinanceCharts |
| 4 | SPY | ~+18–22% est. | Absolute filter: PASSES (positive) |
| 5 | TLT | <+5% est. | Under pressure with rates/oil uncertainty |
| — | SHY | ~+4–5% est. | Cash proxy |

**Preliminary Signal: BUY IWM** (same as previous 8 sessions) — absolute filter passes, IWM #1.
*Must re-verify with `python3 scripts/dual_momentum_signal.py` before any trade, once API restored.*

### Today's Action
**NOT a rebalance day.** Next scheduled rebalance: 2026-07-31. No trades. No intraday action permitted by strategy.

**Overdue rebalance note:** The June 30 rebalance was missed due to API blockage. As soon as APIs are restored, run `dual_momentum_signal.py` → if IWM still #1, BUY IWM immediately. Do not wait for July 31.

### Risk Notes
- US-Iran geopolitical escalation: crude oil spike is inflationary, risk-off. VIX rising.
- FOMC minutes (Warsh, first meeting): hawkish surprise could pressure both equities and TLT.
- IWM is small-cap/domestic — tends to be more sensitive to domestic risk-off shocks. Watch for IWM pullback.
- This does NOT change the monthly signal; do not exit early.

### Decision
**NO TRADE** — not rebalance day. Strategy permits no intraday or discretionary action.
