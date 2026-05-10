#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="$(
  INTENTPROOF_API_BASE="${INTENTPROOF_API_BASE:-http://127.0.0.1:8000}" PYTHONPATH="$SCRIPT_DIR" python3 -c \
    'from http_utils import require_http_base; import os; print(require_http_base(os.environ["INTENTPROOF_API_BASE"]))'
)"
API_KEY="${INTENTPROOF_API_KEY:?set INTENTPROOF_API_KEY}"

curl -sS -f -X POST "${BASE_URL%/}/v1/events" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "id": "evt-1",
    "correlationId": "corr-123",
    "intent": "Capture customer payment after checkout authorization",
    "action": "checkout.capture_payment",
    "status": "ok",
    "inputs": {"amount": 1000, "currency": "USD"},
    "output": {"captureId": "cap-1", "status": "succeeded"},
    "startedAt": "2026-05-09T12:00:00Z",
    "completedAt": "2026-05-09T12:00:00Z",
    "durationMs": 0,
    "attributes": {"service": "checkout-api", "env": "dev"}
  }'

echo
