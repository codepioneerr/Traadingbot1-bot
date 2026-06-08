"""
Survivorship-bias-aware S&P 500 pool for ORB backtesting, 2021-01-04 to 2026-01-03.

All names below were continuously in the S&P 500 throughout the full window.
Excluded: any ticker added AFTER 2021-01-04, any ticker removed BEFORE 2026-01-03,
any ticker whose price fell below $10 for an extended period, and low-liquidity names
with ADV < 5M shares/day.

Source for membership verification:
  github.com/fja05680/sp500 (MIT license, updated Jan 2026)
  "S&P 500 Historical Components & Changes(01-17-2026).csv"

For production use, load membership directly from that CSV to get exact point-in-time
constituents per year-start — this list is a manually curated conservative subset.

Caveats:
- ~10-15 names at the margin may have been added/removed and re-added; when in doubt
  they are excluded here. Run against the fja05680 CSV to verify any specific ticker.
- Ticker changes: FB→META (Oct 2022) handled by using META throughout.
- GE is excluded (complex spin-offs 2023-2024 changed what "GE" means).
- INTC is included — still in S&P 500 throughout despite stock weakness 2024.
"""

SP500_STABLE_POOL = [
    # ── Technology (high-beta, high-ADV — best candidates for ORB scanner) ───
    'AAPL',   # Apple — in S&P 500 since 1982
    'MSFT',   # Microsoft — in S&P 500 since 1994
    'NVDA',   # Nvidia — in S&P 500 since 2001
    'AMD',    # Advanced Micro Devices
    'AVGO',   # Broadcom
    'QCOM',   # Qualcomm
    'TXN',    # Texas Instruments
    'AMAT',   # Applied Materials
    'MU',     # Micron Technology
    'LRCX',   # Lam Research
    'KLAC',   # KLA Corp
    'ADI',    # Analog Devices
    'MCHP',   # Microchip Technology
    'INTC',   # Intel (still in S&P 500 throughout; price > $10 throughout)
    'CSCO',   # Cisco Systems — in S&P 500 since 1993
    'ORCL',   # Oracle
    'IBM',    # IBM — in S&P 500 since 1979
    'ACN',    # Accenture
    'CTSH',   # Cognizant
    'FISV',   # Fiserv

    # ── Communication Services ──────────────────────────────────────────────
    'META',   # Meta (was FB — same company, ticker changed Oct 2022)
    'GOOGL',  # Alphabet Class A
    'GOOG',   # Alphabet Class C
    'NFLX',   # Netflix
    'CMCSA',  # Comcast
    'T',      # AT&T (price ~$17-27 throughout; ADV 100M+ shares/day)
    'VZ',     # Verizon
    'TMUS',   # T-Mobile

    # ── Consumer Discretionary ──────────────────────────────────────────────
    'AMZN',   # Amazon — in S&P 500 since 2005
    'TSLA',   # Tesla — added Dec 21 2020; in S&P 500 from day 1 of our window
    'HD',     # Home Depot — in S&P 500 since 1988
    'LOW',    # Lowe's
    'MCD',    # McDonald's
    'NKE',    # Nike — in S&P 500 since 1988
    'SBUX',   # Starbucks
    'TJX',    # TJX Companies
    'TGT',    # Target
    'BKNG',   # Booking Holdings

    # ── Consumer Staples ────────────────────────────────────────────────────
    'PG',     # Procter & Gamble
    'KO',     # Coca-Cola
    'PEP',    # PepsiCo
    'WMT',    # Walmart
    'COST',   # Costco
    'CL',     # Colgate-Palmolive
    'MDLZ',   # Mondelez

    # ── Financials ──────────────────────────────────────────────────────────
    'JPM',    # JPMorgan Chase — in S&P 500 throughout
    'BAC',    # Bank of America
    'WFC',    # Wells Fargo
    'GS',     # Goldman Sachs
    'MS',     # Morgan Stanley
    'C',      # Citigroup
    'AXP',    # American Express
    'BLK',    # BlackRock
    'SCHW',   # Charles Schwab
    'COF',    # Capital One
    'USB',    # US Bancorp
    'PGR',    # Progressive
    'MMC',    # Marsh McLennan
    'CB',     # Chubb
    'TRV',    # Travelers

    # ── Healthcare ──────────────────────────────────────────────────────────
    'UNH',    # UnitedHealth Group
    'LLY',    # Eli Lilly
    'JNJ',    # Johnson & Johnson
    'ABBV',   # AbbVie
    'MRK',    # Merck
    'ABT',    # Abbott Laboratories
    'TMO',    # Thermo Fisher Scientific
    'DHR',    # Danaher
    'BMY',    # Bristol-Myers Squibb
    'AMGN',   # Amgen
    'GILD',   # Gilead Sciences
    'ISRG',   # Intuitive Surgical
    'CI',     # Cigna
    'HUM',    # Humana
    'CVS',    # CVS Health
    'MDT',    # Medtronic

    # ── Industrials ─────────────────────────────────────────────────────────
    'HON',    # Honeywell
    'RTX',    # Raytheon Technologies (now RTX Corp)
    'CAT',    # Caterpillar
    'DE',     # Deere & Company
    'LMT',    # Lockheed Martin
    'UPS',    # United Parcel Service
    'FDX',    # FedEx
    'EMR',    # Emerson Electric
    'ETN',    # Eaton
    'BA',     # Boeing (still in S&P 500 throughout, despite issues)
    'NOC',    # Northrop Grumman

    # ── Energy ──────────────────────────────────────────────────────────────
    'XOM',    # Exxon Mobil
    'CVX',    # Chevron
    'COP',    # ConocoPhillips
    'EOG',    # EOG Resources
    'MPC',    # Marathon Petroleum
    'PSX',    # Phillips 66
    'OXY',    # Occidental Petroleum
    'SLB',    # SLB (Schlumberger)

    # ── Materials ───────────────────────────────────────────────────────────
    'LIN',    # Linde
    'APD',    # Air Products
    'SHW',    # Sherwin-Williams

    # ── Real Estate (REITs — lower ORB relevance but valid S&P 500 members) ─
    'AMT',    # American Tower
    'PLD',    # Prologis
    'EQIX',   # Equinix

    # ── Utilities (lower ORB relevance — rarely gap > 1%) ──────────────────
    'NEE',    # NextEra Energy
]

# Tickers known to have been ADDED after 2021-01-04 — do NOT include in historical pool
SP500_ADDED_AFTER_2021 = [
    'UBER',   # Added Dec 2023
    'ABNB',   # Added Dec 2021
    'DASH',   # Added Dec 2023
    'RIVN',   # Added Dec 2023
    'FTNT',   # Added Oct 2021
    'CRWD',   # Added 2023
    'CEG',    # Constellation Energy — IPO / spun from EXC Jun 2022
    'KVUE',   # Kenvue — spun from JNJ 2023
    'SOLV',   # Solventum — spun from MMM 2024
    'GEV',    # GE Vernova — spun from GE 2024
    'GEHC',   # GE HealthCare — spun from GE 2023
]

if __name__ == '__main__':
    print(f"SP500_STABLE_POOL: {len(SP500_STABLE_POOL)} symbols")
    print(f"Sectors represented: Tech, Comms, Discretionary, Staples, Financials,")
    print(f"  Healthcare, Industrials, Energy, Materials, Real Estate, Utilities")
    print()
    print("To get exact point-in-time membership for any date:")
    print("  pip install pandas")
    print("  # Download: github.com/fja05680/sp500")
    print("  # File: 'S&P 500 Historical Components & Changes(01-17-2026).csv'")
    print("  # Use sp500_by_date.ipynb to query membership on any specific date")
