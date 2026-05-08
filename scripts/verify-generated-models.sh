#!/usr/bin/env bash
# Regenerate app/generated and fail if checked-in output drifts.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"

python3 scripts/generate_spec_models.py
ruff format app/generated

if git rev-parse --verify HEAD >/dev/null 2>&1; then
  git diff --exit-code -- app/generated
  if [[ -n "$(git ls-files --others --exclude-standard -- app/generated)" ]]; then
    echo "verify-generated-models: untracked files in app/generated after generation" >&2
    git ls-files --others --exclude-standard -- app/generated >&2
    exit 1
  fi
else
  echo "verify-generated-models: no git HEAD yet, skipped drift check (generation succeeded)"
fi

echo "OK: generated API models match intentproof-spec"
