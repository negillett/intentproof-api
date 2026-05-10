#!/usr/bin/env python3
"""POST one wrapped execution via intentproof-sdk-python HttpExporter (flat wire JSON).

Install the SDK (pick one):

  pip install -e ../intentproof-sdk-python    # sibling checkout (typical ~/src layout)
  pip install intentproof-sdk                  # PyPI

Optional: set INTENTPROOF_SDK_PYTHON_ROOT to a checkout root — prepends that repo's src/
to sys.path so Python loads that tree first (still requires dependencies installed, e.g.
pip install -e "$INTENTPROOF_SDK_PYTHON_ROOT").

Uses only public SDK APIs: ExecutionEvent via model_dump plus JSON shaping aligned with
the SDK's HTTP/wire conventions (same rules as intentproof-sdk-python MemoryExporter).

Environment: INTENTPROOF_API_BASE (optional), INTENTPROOF_API_KEY (required).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from http_utils import require_http_base


def _maybe_prepend_sdk_src() -> None:
    root = os.environ.get("INTENTPROOF_SDK_PYTHON_ROOT")
    if not root:
        return
    src = Path(root).resolve() / "src"
    if not (src / "intentproof").is_dir():
        sys.stderr.write(
            "INTENTPROOF_SDK_PYTHON_ROOT must point at intentproof-sdk-python "
            "(expected intentproof package under src/).\n"
        )
        sys.exit(1)
    sys.path.insert(0, str(src))


def main() -> None:
    _maybe_prepend_sdk_src()

    from intentproof import create_intent_proof_client
    from intentproof.exporters import HttpExporter
    from intentproof.types import ExecutionEvent, IntentProofConfig

    def execution_event_to_api_json(event: ExecutionEvent) -> dict[str, Any]:
        """CamelCase ExecutionEvent dict for POST /v1/events (public model_dump only)."""
        data = event.model_dump(by_alias=True, mode="json", exclude_none=True)
        dm = data.get("durationMs")
        if dm is not None:
            data["durationMs"] = int(dm)
        st = data["status"]
        if st == "ok" and "output" not in data:
            data["output"] = None
        elif st != "ok" and data.get("output") is None:
            data.pop("output", None)
        if not data.get("attributes"):
            data.pop("attributes", None)
        return data

    def flat_execution_event_body(event: ExecutionEvent) -> str:
        """Flat JSON for POST /v1/events (not HttpExporter's default envelope)."""
        return json.dumps(execution_event_to_api_json(event), separators=(",", ":"))

    base = require_http_base(os.environ.get("INTENTPROOF_API_BASE", "http://127.0.0.1:8000"))
    api_key = os.environ.get("INTENTPROOF_API_KEY")
    if not api_key:
        sys.stderr.write("Set INTENTPROOF_API_KEY.\n")
        sys.exit(1)

    client = create_intent_proof_client(
        IntentProofConfig(
            exporters=[
                HttpExporter(
                    url=urllib.parse.urljoin(base + "/", "v1/events"),
                    headers={"X-API-Key": api_key},
                    body=flat_execution_event_body,
                    await_each=True,
                )
            ]
        )
    )

    demo = client.wrap(
        intent="Prove ingest from SDK",
        action="demo.ingest",
        correlation_id="corr-from-sdk",
        fn=lambda: {"ok": True},
    )
    demo()


if __name__ == "__main__":
    main()
