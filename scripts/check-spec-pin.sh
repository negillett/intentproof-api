#!/usr/bin/env bash
# Fail if this repository's declared IntentProof spec version + commit pins do not match the spec checkout.
# Usage: check-spec-pin.sh /absolute/or/relative/path/to/intentproof-spec
set -euo pipefail

spec_root_arg="${1:-}"
if [ -z "${spec_root_arg}" ]; then
  echo "check-spec-pin.sh: missing intentproof-spec checkout path (pass as \$1 or set INTENTPROOF_SPEC_ROOT for tox)." >&2
  exit 1
fi

spec_root="$(cd "${spec_root_arg}" && pwd)"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec bash "${spec_root}/scripts/check-consumer-spec-pins.sh" "${repo_root}" "${spec_root}"
