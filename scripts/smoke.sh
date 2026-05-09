#!/usr/bin/env bash
# Post-deploy smoke: health → ingest → duplicate ingest → correlation query.
# Usage: BASE_URL=https://api.example.com API_KEY=... bash scripts/smoke.sh
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API_KEY="${API_KEY:?set API_KEY}"

CORR="smoke-$(date +%s)"
BODY=$(cat <<EOF
{
  "id": "evt-smoke",
  "correlationId": "${CORR}",
  "intent": "Smoke test event",
  "action": "smoke.verify",
  "status": "ok",
  "inputs": {},
  "output": {},
  "startedAt": "2026-05-09T12:00:00Z",
  "completedAt": "2026-05-09T12:00:00Z",
  "durationMs": 0,
  "attributes": {"source": "scripts/smoke.sh"}
}
EOF
)

hdr=(-H "X-API-Key: ${API_KEY}" -H "Content-Type: application/json")

echo "GET ${BASE_URL}/health"
curl -fsS "${BASE_URL}/health" | tee /dev/stderr >/dev/null

echo "POST ${BASE_URL}/v1/events (first)"
r1=$(curl -fsS -w "%{http_code}" -o /tmp/ip_smoke_1.json "${hdr[@]}" -X POST "${BASE_URL}/v1/events" -d "${BODY}")
echo "HTTP ${r1}"
test "${r1}" = "202"

echo "POST ${BASE_URL}/v1/events (duplicate)"
r2=$(curl -fsS -w "%{http_code}" -o /tmp/ip_smoke_2.json "${hdr[@]}" -X POST "${BASE_URL}/v1/events" -d "${BODY}")
echo "HTTP ${r2}"
test "${r2}" = "202"
jq -e '.duplicate == true' /tmp/ip_smoke_2.json >/dev/null

echo "GET ${BASE_URL}/v1/events/by-correlation/${CORR}"
curl -fsS "${hdr[@]}" "${BASE_URL}/v1/events/by-correlation/${CORR}" | jq -e '.items | length >= 1' >/dev/null

echo "smoke OK"
