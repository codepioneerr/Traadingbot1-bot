# Backtest Infrastructure

## Active Strategy: Dual Momentum ETF Rotation

**Verdict: ✅ PASS** — June 7, 2026

### Quick Run

```bash
# Download data once (requires internet, ~30 seconds)
python3 backtest/run_dual_momentum.py --download

# Run full backtest
python3 backtest/run_dual_momentum.py
```

### Summary Results (2005–2026)

| Metric | Value | vs SPY |
|--------|-------|--------|
| CAGR | +11.30% | +0.70% alpha |
| Sharpe | 0.687 | vs 0.578 |
| Max Drawdown | 32.9% | vs 52.9% |
| OOS Sharpe (2023–2026) | **2.03** | — |
| OOS Return (2023–2026) | **+166.9%** | — |

Replicates Antonacci (2014): CAGR matches published ~10-12%. Max DD higher (32.9% vs ~17%) due to 2022 QQQ bear market post-dating the book.

### Files

| File | Purpose |
|------|---------|
| `strategies/dual_momentum.py` | Signal logic + run_backtest() |
| `run_dual_momentum.py` | Data download + full reporter |
| `cache/dual_momentum/` | Cached 20-year daily prices (yfinance) |
| `results/dual_momentum_*.json` | Saved backtest result |

---

## Deprecated Strategies

### ORB (Opening Range Breakout)
- Tested: June 2026 | Result: ❌ FAIL
- OOS PF 0.59, WR 46.2%, total return −7.2% (2021–2026, realistic 5bps costs)
- Every year negative. No edge in institutional S&P 500 universe.
- Code: `strategies/orb.py`, `evaluate.py`

### PEAD (Post-Earnings Announcement Drift) — full family
- Tested: June 2026 | Result: ❌ FAIL / INSUFFICIENT SAMPLE
- Baseline OOS PF 0.994, Sharpe −1.178. Long-side PF 0.849 (WR 35%).
- Short-only OOS: 8 trades — statistically insufficient.
- High-conv longs (SUE ≥ 15/25%): 0–4 OOS trades — statistically insufficient.
- 1-Day Momentum: OOS PF 1.175, Sharpe −2.11 — FAILED gate.
- Overreaction Fade: OOS PF 0.721, 6 trades — INSUFFICIENT SAMPLE.
- Root cause: 92-symbol earnings universe too small for statistical inference.
- Code: `strategies/pead*.py`, `strategies/earnings_momentum_1d.py`, `strategies/overreaction_fade.py`

---

## Pass/Fail Gate (all strategies)

| Condition | Threshold |
|-----------|-----------|
| OOS Sharpe | > 0.3 (monthly strategies: lower bar, fewer data points) |
| OOS Return | > 0% |
| Max Drawdown | < 35% |
| CAGR | ≥ SPY CAGR × 0.8 |

Dual Momentum clears all four. OOS Sharpe of 2.03 is exceptional — the 2023-2026 period has been highly trend-friendly for momentum.

---

## Engine Notes

- `engine.py`: event-driven, processes chronological bar stream, fills at bar close
- Daily bar OHLC approximation: use `bar['l'] ≤ target` (hit low), `bar['h'] ≥ stop` (hit stop)
- Dual Momentum uses a standalone simulation (not BacktestEngine) — monthly rebalancing with entry at close, no intraday logic needed
- IS/OOS split: enforce strict chronological boundary, no data leakage
