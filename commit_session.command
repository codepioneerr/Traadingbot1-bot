#!/bin/bash
cd "$(dirname "$0")"
echo "=== Committing trading bot session work ==="

# Remove stale git lock if present
rm -f .git/index.lock 2>/dev/null && echo "Removed index.lock"

git config user.email "nickdagod3@gmail.com"
git config user.name "Nick"

git add \
  backtest/README.md \
  backtest/run_pead.py \
  backtest/run_experiments.py \
  backtest/run_pivot.py \
  backtest/run_dual_momentum.py \
  backtest/strategies/pead_short_only.py \
  backtest/strategies/pead_highconv.py \
  backtest/strategies/earnings_momentum_1d.py \
  backtest/strategies/overreaction_fade.py \
  backtest/strategies/dual_momentum.py \
  backtest/results/pead_20260606_235805.json \
  backtest/results/pead_experiments_20260607_193715.json \
  backtest/results/pivot_experiments_20260607_195518.json \
  backtest/results/pivot_experiments_20260607_195733.json \
  backtest/results/pivot_experiments_20260607_195741.json \
  backtest/results/dual_momentum_20260607_204025.json \
  memory/TRADING-STRATEGY.md \
  2>/dev/null

git status --short

git commit -m "Strategy research session — pivot to Dual Momentum ETF Rotation

Strategies tested and deprecated:
- ORB: PF 0.59, every year negative — retired
- PEAD baseline: OOS PF 0.994, Sharpe -1.18 — failed gate
- PEAD short-only: 8 OOS trades — insufficient sample
- PEAD high-conviction: 0-4 OOS trades — insufficient sample
- 1-Day Earnings Momentum: OOS Sharpe -2.11 — failed gate
- Overreaction Fade: 6 OOS trades — insufficient sample
- Root cause: earnings universe (92 symbols) too small

New strategy: Dual Momentum ETF Rotation (Antonacci 2014)
- Universe: SPY, QQQ, IWM, TLT, GLD, SHY
- Signal: 12-month absolute + relative momentum, monthly rebalance
- Backtest 2005-2026: CAGR +11.30%, MaxDD 32.9%, Sharpe 0.687
- OOS (2023-2026): Sharpe 2.03, Return +166.9% — PASS
- Replicates Antonacci published numbers (CAGR matches, MaxDD higher due to 2022)"

echo ""
echo "Git log (last 3):"
git log --oneline -3

echo ""
git push && echo "=== Push successful ===" || echo "=== Push failed — check remote ==="

read -p "Press Enter to close..."
