#!/usr/bin/env bash
# Alpaca Paper Trading API wrapper
# Usage: alpaca.sh <subcommand> [args]
# Subcommands:
#   account
#   positions
#   quote <symbol>
#   orders [open|closed|all]
#   buy <symbol> <notional>
#   trailing-stop <symbol> <qty> <trail_pct>
#   stop <symbol> <qty> <stop_price>
#   close <symbol>
#   cancel <order_id>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

for v in ALPACA_API_KEY ALPACA_SECRET_KEY ALPACA_ENDPOINT; do
  if [[ -z "${!v:-}" ]]; then
    echo "ERROR: $v not set in environment" >&2
    exit 1
  fi
done

BASE="${ALPACA_ENDPOINT%/}"
DATA_BASE="${ALPACA_DATA_ENDPOINT:-https://data.alpaca.markets}"

api() {
  local method="$1" path="$2" body="${3:-}"
  local url="${BASE}${path}"
  local args=(-s -X "$method"
    -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}"
    -H "APCA-API-SECRET-KEY: ${ALPACA_SECRET_KEY}"
    -H "Content-Type: application/json")
  [[ -n "$body" ]] && args+=(-d "$body")
  curl "${args[@]}" "$url"
}

subcommand="${1:-}"
case "$subcommand" in
  account)
    api GET /v2/account | python3 -m json.tool
    ;;
  positions)
    api GET /v2/positions | python3 -m json.tool
    ;;
  quote)
    symbol="${2:?Usage: alpaca.sh quote <symbol>}"
    curl -s \
      -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
      -H "APCA-API-SECRET-KEY: ${ALPACA_SECRET_KEY}" \
      "${DATA_BASE}/v2/stocks/${symbol}/quotes/latest" | python3 -m json.tool
    ;;

  orders)
    status="${2:-open}"
    api GET "/v2/orders?status=${status}&limit=50" | python3 -m json.tool
    ;;
  buy)
    symbol="${2:?Usage: alpaca.sh buy <symbol> <notional>}"
    notional="${3:?Usage: alpaca.sh buy <symbol> <notional>}"
    body=$(python3 -c "import json; print(json.dumps({'symbol':'${symbol}','notional':'${notional}','side':'buy','type':'market','time_in_force':'day'}))")
    api POST /v2/orders "$body" | python3 -m json.tool
    ;;
  trailing-stop)
    symbol="${2:?Usage: alpaca.sh trailing-stop <symbol> <qty> <trail_pct>}"
    qty="${3:?}"
    trail="${4:?}"
    body=$(python3 -c "import json; print(json.dumps({'symbol':'${symbol}','qty':'${qty}','side':'sell','type':'trailing_stop','trail_percent':'${trail}','time_in_force':'gtc'}))")
    api POST /v2/orders "$body" | python3 -m json.tool
    ;;
  stop)
    symbol="${2:?Usage: alpaca.sh stop <symbol> <qty> <stop_price>}"
    qty="${3:?}"
    stop_price="${4:?}"
    body=$(python3 -c "import json; print(json.dumps({'symbol':'${symbol}','qty':'${qty}','side':'sell','type':'stop','stop_price':'${stop_price}','time_in_force':'gtc'}))")
    api POST /v2/orders "$body" | python3 -m json.tool
    ;;
  close)
    symbol="${2:?Usage: alpaca.sh close <symbol>}"
    api DELETE "/v2/positions/${symbol}" | python3 -m json.tool
    ;;
  cancel)
    order_id="${2:?Usage: alpaca.sh cancel <order_id>}"
    api DELETE "/v2/orders/${order_id}" | python3 -m json.tool
    ;;
  *)
    echo "Unknown subcommand: ${subcommand:-<none>}"
    echo "Usage: alpaca.sh <account|positions|quote|orders|buy|trailing-stop|stop|close|cancel> [args]"
    exit 1
    ;;
esac
