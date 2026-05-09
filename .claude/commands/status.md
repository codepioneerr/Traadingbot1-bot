You are running a quick account status check for the trading bot.

Pull current state from Alpaca:
  bash scripts/alpaca.sh account
  bash scripts/alpaca.sh positions
  bash scripts/alpaca.sh orders open

Then read:
- tail of memory/TRADE-LOG.md (to find today's sizing mode and weekly trade count)
- today's entry in memory/RESEARCH-LOG.md if it exists

Display a concise snapshot:

---
STATUS — <today's date>

Portfolio equity:  $X,XXX.XX
Cash:              $X,XXX.XX (XX% idle)
Day P&L:           ±$XX.XX (±X.XX%)   [vs yesterday's EOD snapshot]
Phase P&L:         ±$XX.XX (±X.XX%)   [vs $10,000 starting capital]

Sizing mode:       [AGGRESSIVE / MODERATE / DEFENSIVE]
Weekly trades:     N/5
Day trades used:   N/3 (PDT)

Open positions (N/6 max):
  SYMBOL   type     shares   entry $X.XX   now $X.XX   ±X.X%   stop $X.XX
  ...

Open orders:
  SYMBOL   type   qty   [details]
  ...      (none if empty)
---

Keep output short and scannable. No prose, just data.
