#!/usr/bin/env python3
"""
Dual Momentum Signal Calculator
================================
Computes the monthly rebalance signal for the Dual Momentum ETF rotation strategy.

Signal logic:
  Step 1 — Absolute filter:
    If SPY 12-month return (252 trading days) < 0%: signal = SHY
  Step 2 — Relative ranking:
    Rank [SPY, QQQ, IWM, TLT, GLD] by 252-day return. Signal = #1 ranked.

Output (stdout, machine-readable):
  SIGNAL: QQQ
  SPY_12M: +18.4%
  QQQ_12M: +24.1%
  ...
  ABSOLUTE_FILTER: PASS (SPY positive)
  RANKED: QQQ > GLD > SPY > IWM > SHY > TLT

Exit codes:
  0 = success, signal written to stdout
  1 = data error (download failed, insufficient history, etc.)

Usage:
  python3 scripts/dual_momentum_signal.py
"""

import sys
import time
import warnings
warnings.filterwarnings('ignore')

RISK_ASSETS  = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD']
SAFE_ASSET   = 'SHY'
ALL_ASSETS   = RISK_ASSETS + [SAFE_ASSET]
LOOKBACK     = 252          # trading days ≈ 12 months
DOWNLOAD_DAYS = 280         # 252 + buffer for weekends/holidays
SLEEP_SEC    = 2.0          # courtesy sleep between ticker downloads


def download_closes(ticker: str, days: int = DOWNLOAD_DAYS) -> list[float]:
    """
    Download the most recent `days` trading days of closing prices.
    Returns a list of floats (oldest → newest) or raises on failure.
    Uses yfinance with auto_adjust=True (includes dividend reinvestment).
    """
    import yfinance as yf
    t = yf.Ticker(ticker)
    df = t.history(period=f'{days + 30}d', auto_adjust=True)
    if df is None or df.empty:
        raise ValueError(f'No data returned for {ticker}')
    closes = df['Close'].dropna().tolist()
    if len(closes) < LOOKBACK + 2:
        raise ValueError(
            f'{ticker}: only {len(closes)} bars, need {LOOKBACK + 2}'
        )
    return closes


def compute_12m_return(closes: list[float]) -> float:
    """
    12-month return using 252-day lookback.
    Returns decimal (e.g. 0.184 = +18.4%).
    """
    if len(closes) < LOOKBACK + 1:
        raise ValueError(f'Insufficient history: {len(closes)} bars')
    current  = closes[-1]
    past_252 = closes[-(LOOKBACK + 1)]
    if past_252 <= 0:
        raise ValueError('Zero or negative past price')
    return current / past_252 - 1


def main() -> int:
    # ── Download all tickers ──────────────────────────────────────────────────
    closes_by_sym: dict[str, list[float]] = {}
    errors: list[str] = []

    for i, sym in enumerate(ALL_ASSETS):
        try:
            closes_by_sym[sym] = download_closes(sym)
            if i < len(ALL_ASSETS) - 1:
                time.sleep(SLEEP_SEC)
        except Exception as e:
            errors.append(f'{sym}: {e}')

    if errors:
        print(f'ERROR: data download failed for: {", ".join(errors)}', file=sys.stderr)
        return 1

    # ── Compute 12-month returns ──────────────────────────────────────────────
    returns: dict[str, float] = {}
    for sym, closes in closes_by_sym.items():
        try:
            returns[sym] = compute_12m_return(closes)
        except Exception as e:
            print(f'ERROR computing return for {sym}: {e}', file=sys.stderr)
            return 1

    # ── Apply signal logic ────────────────────────────────────────────────────
    spy_ret = returns['SPY']

    if spy_ret < 0.0:
        signal        = SAFE_ASSET
        abs_filter    = 'TRIGGERED (SPY negative — holding SHY)'
    else:
        # Rank risk assets by 12m return, highest first
        ranked = sorted(RISK_ASSETS, key=lambda s: returns[s], reverse=True)
        signal     = ranked[0]
        abs_filter = 'PASS (SPY positive)'
        # Build full ranking including SHY for display
        all_ranked = sorted(ALL_ASSETS, key=lambda s: returns[s], reverse=True)

    # ── Full ranking for display (all 6 assets, descending) ──────────────────
    all_ranked = sorted(ALL_ASSETS, key=lambda s: returns[s], reverse=True)

    # ── Output ────────────────────────────────────────────────────────────────
    print(f'SIGNAL: {signal}')
    print()
    for sym in ALL_ASSETS:
        r = returns[sym]
        sign = '+' if r >= 0 else ''
        print(f'{sym}_12M: {sign}{r*100:.1f}%')
    print()
    print(f'ABSOLUTE_FILTER: {abs_filter}')
    print(f'RANKED: {" > ".join(all_ranked)}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
