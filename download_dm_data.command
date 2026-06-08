#!/bin/bash
# Dual Momentum Data Downloader
# Double-click this file in Finder to run in Terminal

cd "$(dirname "$0")"
echo "=== Dual Momentum Data Download ==="
echo "Working directory: $(pwd)"

# Install yfinance if needed
pip3 install yfinance --break-system-packages -q 2>/dev/null || \
pip3 install yfinance -q 2>/dev/null || true

# Run the download
python3 backtest/run_dual_momentum.py --download

echo ""
echo "=== Done! Now run the backtest: ==="
echo "python3 backtest/run_dual_momentum.py"
echo ""
read -p "Press Enter to close..."
