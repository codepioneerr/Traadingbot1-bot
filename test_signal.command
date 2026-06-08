#!/bin/bash
cd "$(dirname "$0")"
echo "=== Testing dual_momentum_signal.py ==="
python3 scripts/dual_momentum_signal.py
echo ""
echo "Exit code: $?"
read -p "Press Enter to close..."
