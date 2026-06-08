#!/bin/bash
cd "$(dirname "$0")"
echo "=== Committing Dual Momentum deployment ==="

rm -f .git/index.lock 2>/dev/null
git config user.email "nickdagod3@gmail.com"
git config user.name "Nick"

echo ""
echo "--- Testing signal script (requires internet) ---"
python3 scripts/dual_momentum_signal.py
SIG_EXIT=$?
echo "Signal script exit code: $SIG_EXIT"

echo ""
echo "--- Testing rebalance day checker ---"
python3 scripts/is_rebalance_day.py
echo ""

echo "--- Testing risk check ---"
python3 scripts/risk_check.py
echo ""

echo "--- Committing Step 1-2: docs + signal ---"
git add memory/TRADING-STRATEGY.md memory/PROJECT-CONTEXT.md scripts/dual_momentum_signal.py
git commit -m "docs: update strategy to Dual Momentum, deprecate multi-stock rules

- TRADING-STRATEGY.md: complete rewrite for Dual Momentum ETF rotation
- PROJECT-CONTEXT.md: updated phase, strategy status, key rules
- scripts/dual_momentum_signal.py: 12m momentum signal calculator" 2>&1

echo ""
echo "--- Committing Step 3: rebalance day checker ---"
git add scripts/is_rebalance_day.py
git commit -m "feat: add is_rebalance_day.py

Determines last trading day of current month using hardcoded US market
holidays 2025-2027. Exits 0 on rebalance day, 1 otherwise." 2>&1

echo ""
echo "--- Committing Step 4: circuit breaker ---"
git add scripts/risk_check.py
git commit -m "feat: add risk_check.py calibrated for monthly rotation strategy

Halts on: PAUSE-FLAG, invalid ticker, >1 position, >20% monthly drawdown.
Does NOT halt on daily/weekly P&L or position being 'down' — by design." 2>&1

echo ""
echo "--- Committing Steps 5-6: routines ---"
git add routines/market-open.md routines/pre-market.md routines/midday.md routines/daily-summary.md routines/weekly-review.md
git commit -m "feat: rewrite all routines for monthly dual momentum rebalance

market-open.md: gates on is_rebalance_day, runs signal, executes rebalance
pre-market.md: lightweight — just risk check + position status, no Perplexity
midday.md: minimal — risk check only, no stop tightening
daily-summary.md: current holding, return vs SPY benchmark
weekly-review.md: adds MTD vs SPY, signal ranking, days until rebalance" 2>&1

echo ""
echo "--- Pushing all commits ---"
git log --oneline -5
git push origin main && echo "=== Push successful ===" || echo "=== Push failed ==="

echo ""
echo "Press Enter to close..."
read
