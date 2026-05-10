#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="$(
  INTENTPROOF_API_BASE="${INTENTPROOF_API_BASE:-http://127.0.0.1:8000}" PYTHONPATH="$SCRIPT_DIR" python3 -c \
    'from http_utils import require_http_base; import os; print(require_http_base(os.environ["INTENTPROOF_API_BASE"]))'
)"
API_KEY="${INTENTPROOF_API_KEY:?set INTENTPROOF_API_KEY}"
CORRELATION_ID="${INTENTPROOF_CORRELATION_ID:-corr-123}"
LIMIT="${INTENTPROOF_QUERY_LIMIT:-100}"

ENC_ID="$(
  CORRELATION_ID="$CORRELATION_ID" python3 -c \
    'import os, urllib.parse; print(urllib.parse.quote(os.environ["CORRELATION_ID"], safe=""))'
)"

# Limit must be a single integer query param (API allows 1–500); reject ambiguous strings.
LIMIT="$(
  LIMIT="$LIMIT" python3 <<'PY'
import os
import sys

try:
    v = int(os.environ["LIMIT"], 10)
except ValueError:
    sys.stderr.write("INTENTPROOF_QUERY_LIMIT must be an integer\n")
    sys.exit(1)
if not 1 <= v <= 500:
    sys.stderr.write("INTENTPROOF_QUERY_LIMIT must be between 1 and 500\n")
    sys.exit(1)
print(v)
PY
)"

curl -sS -f "${BASE_URL%/}/v1/events/by-correlation/${ENC_ID}?limit=${LIMIT}" \
  -H "X-API-Key: ${API_KEY}"

echo
