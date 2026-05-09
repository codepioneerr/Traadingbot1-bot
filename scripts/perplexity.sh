#!/usr/bin/env bash
# Perplexity API wrapper
# Usage: perplexity.sh "<query>"
# Returns the model's text response to stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

for v in PERPLEXITY_API_KEY PERPLEXITY_MODEL; do
  if [[ -z "${!v:-}" ]]; then
    echo "ERROR: $v not set in environment" >&2
    exit 1
  fi
done

query="${1:?Usage: perplexity.sh \"<query>\"}"

payload=$(python3 -c "
import json, sys
q = sys.argv[1]
print(json.dumps({
    'model': '${PERPLEXITY_MODEL}',
    'messages': [
        {'role': 'system', 'content': 'Be precise and concise. Return factual, up-to-date information.'},
        {'role': 'user', 'content': q}
    ],
    'max_tokens': 1024
}))
" "$query")

response=$(curl -s -X POST \
  -H "Authorization: Bearer ${PERPLEXITY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$payload" \
  "https://api.perplexity.ai/chat/completions")

# Extract the text content; fall back to raw response if jq not available
if command -v jq &>/dev/null; then
  echo "$response" | jq -r '.choices[0].message.content // "ERROR: unexpected response"'
else
  echo "$response" | python3 -c "
import json, sys
data = json.load(sys.stdin)
try:
    print(data['choices'][0]['message']['content'])
except (KeyError, IndexError):
    print('ERROR: unexpected response:', json.dumps(data))
"
fi
