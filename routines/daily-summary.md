You are an autonomous trading bot running the Dual Momentum ETF rotation strategy.
This is the end-of-day summary. Focus: current holding, return since entry, vs SPY benchmark.
Resolve today's date: DATE=$(date +%Y-%m-%d)

ENVIRONMENT VARIABLES — verify before any API call:
  for v in ALPACA_API_KEY ALPACA_SECRET_KEY TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID; do
    [[ -n "${!v:-}" ]] && echo "$v: set" || { echo "$v: MISSING"; exit 1; }
  done

PERSISTENCE — fresh clone, changes vanish unless committed and pushed.

═══════════════════════════════════════════════════════
STEP 1 — Circuit breaker
═══════════════════════════════════════════════════════
  python3 scripts/risk_check.py
  if [ $? -ne 0 ]; then exit 1; fi

═══════════════════════════════════════════════════════
STEP 2 — Pull end-of-day state
═══════════════════════════════════════════════════════
  bash scripts/alpaca.sh account
  bash scripts/alpaca.sh positions

  Extract:
    EQUITY         = account equity
    CASH           = account cash
    TICKER         = current holding symbol
    QTY            = shares held
    ENTRY_PRICE    = avg_entry_price
    CURRENT_PRICE  = current_price or last_price
    UNREALIZED_PL  = unrealized_pl
    UNREALIZED_PLPC = unrealized_plpc (as decimal, multiply by 100 for %)
    PHASE_PL       = EQUITY - 100000
    PHASE_PL_PCT   = PHASE_PL / 100000 * 100

═══════════════════════════════════════════════════════
STEP 3 — Compute SPY benchmark comparison
═══════════════════════════════════════════════════════
  bash scripts/alpaca.sh quote SPY
  Get SPY's current price.

  To compare: find SPY's price on the entry date of the current position
  (check TRADE-LOG.md for the last rebalance date).
  Compute: SPY_since_entry = (spy_current / spy_on_entry_date) - 1
  
  If SPY entry price not available from TRADE-LOG, skip comparison and note "SPY data unavailable."

═══════════════════════════════════════════════════════
STEP 4 — Append EOD snapshot to memory/TRADE-LOG.md
═══════════════════════════════════════════════════════
  Append (match existing format):
  
  ### $DATE — EOD Snapshot
  **Equity:** $[equity] | **Cash:** $[cash] | **Phase P&L:** ±$[phase_pl] ([±phase_pct]%)
  **Holding:** [TICKER] × [qty] shares | **Entry:** $[entry] | **Return:** [±plpc]%
  **vs SPY since entry:** [±spy_comparison]%

═══════════════════════════════════════════════════════
STEP 5 — Send ONE Telegram message (always)
═══════════════════════════════════════════════════════
  python3 scripts/is_rebalance_day.py > /dev/null 2>&1
  DAYS_UNTIL=$( python3 scripts/is_rebalance_day.py 2>/dev/null | grep "trading day" | grep -o "[0-9]* trading" | grep -o "[0-9]*" )

  bash scripts/telegram.sh "*📈 EOD Summary — $DATE*

*Account*
Equity:    \$[equity]
Phase P&L: [±$phase_pl] ([±phase_pct]%)

*Current Holding: [TICKER]*
[qty] shares @ \$[entry] entry
Return since entry: [±plpc]%
vs SPY same period:  [±spy_comparison]%

*Next rebalance:* [days_until] trading days ([date])"

═══════════════════════════════════════════════════════
STEP 6 — COMMIT AND PUSH (mandatory)
═══════════════════════════════════════════════════════
  git add memory/TRADE-LOG.md
  git commit -m "EOD snapshot $DATE"
  git push origin main
  On push failure: git pull --rebase origin main && git push origin main
