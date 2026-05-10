#!/usr/bin/env python3
"""POST a minimal ExecutionEvent with urllib and print the HTTP status code (stdlib only)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from http_utils import require_http_base


def main() -> None:
    base = require_http_base(os.environ.get("INTENTPROOF_API_BASE", "http://127.0.0.1:8000"))
    api_key = os.environ.get("INTENTPROOF_API_KEY")
    if not api_key:
        sys.stderr.write("Set INTENTPROOF_API_KEY.\n")
        sys.exit(1)

    payload = {
        "id": "evt-direct-1",
        "correlationId": "corr-direct-1",
        "intent": "Direct POST smoke",
        "action": "demo.direct_post",
        "status": "ok",
        "inputs": {},
        "output": {"sent": True},
        "startedAt": "2026-05-09T12:00:00Z",
        "completedAt": "2026-05-09T12:00:00Z",
        "durationMs": 0,
        "attributes": {"channel": "urllib-example"},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        urllib.parse.urljoin(base + "/", "v1/events"),
        data=data,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
    except urllib.error.URLError as e:
        sys.stderr.write(f"{e.reason}\n")
        sys.exit(1)
    print(code)
    if code >= 400:
        sys.exit(1)


if __name__ == "__main__":
    main()
