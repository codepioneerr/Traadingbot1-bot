#!/usr/bin/env bash
# Run on your Mac to send Telegram: bash scripts/send_backtest_notification.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source .env

MSG='📊 *S&P 500 Institutional Pool — Annual Breakdown*

*Pool:* AAPL NVDA MSFT TSLA META AMZN GOOGL AMD NFLX
*Filter:* price >$10 · ADV >5M · gap 1–8% · RVOL ≥2.0 (cat) / ≥2.5 (no-cat)
*Selectivity:* 4.2% — 55/1307 days qualify

*Annual results (5bps):*
| Year | Days | Win% | PF | Return |
|------|------|------|----|--------|
| 2021 | 11   | 50%  |0.48| -0.4%  |
| 2022 | 13   | 70%  |2.51| +0.6%  |
| 2023 |  7   | 74%  |2.07| +0.5%  |
| 2024 |  7   | 13%  |0.05| -0.4%  |
| 2025 | 16   | 28%  |0.24| -1.1%  |

*Frictionless:* PF=1.18 · Win=58.3% ✅ edge confirmed
*After 5bps:* PF=0.82 · Return=-0.9% ❌ costs consume it

*Root cause:* large-cap ORs are narrow (~0.5% wide). Dollar PnL per trade ≈ $100 at 20% sizing. Round-trip friction ≈ $40/trade. At 108 trades: $4,320 costs vs $2,000 gross profit.

*Fix:* expand pool to 50–200 S&P 500 names (CRSP/Sharadar for survivorship-bias-free historical lists). Code is ready — all filters and annual breakdown logic are in place. Run `python run_backtest_full.py` once you have the data.

*Note on annual Sharpe:* shows negative even for 2022/2023 (which had PF 2.07–2.51). This is a carry-forward artifact — 95% of days are flat, earning 0% vs 4% risk-free. The profit factor and win rate are the honest signal.'

python3 -c "
import json, urllib.request
payload = json.dumps({'chat_id': '$TELEGRAM_CHAT_ID', 'text': '''$MSG''', 'parse_mode': 'Markdown'}).encode()
req = urllib.request.Request('https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage',
    data=payload, headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req, timeout=15)
print('Telegram OK:', json.load(r).get('ok'))
"
