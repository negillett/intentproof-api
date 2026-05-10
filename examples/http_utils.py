"""Shared helpers for runnable API examples (trusted-operator configuration only)."""

from __future__ import annotations

import sys
import urllib.parse


def require_http_base(raw: str) -> str:
    """Require http(s) with a hostname; return scheme + netloc + optional path prefix.

    The path may be empty (API at host root) or a non-root prefix such as
    ``/mytenant/api`` when the service is deployed behind a reverse proxy path. Query
    strings and fragments are rejected. Embedded HTTP userinfo (``user:pass@``) is
    rejected to avoid leaking credentials via URLs. Trailing slashes on the path are
    normalized away (except the root path).
    """
    base = raw.strip()
    if not base:
        sys.stderr.write("INTENTPROOF_API_BASE must not be empty.\n")
        sys.exit(1)
    if "://" in base:
        scheme = base.split("://", 1)[0].lower()
        if scheme not in ("http", "https"):
            sys.stderr.write("INTENTPROOF_API_BASE must use http:// or https://\n")
            sys.exit(1)
    else:
        base = "http://" + base
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in ("http", "https"):
        sys.stderr.write("INTENTPROOF_API_BASE must use http or https.\n")
        sys.exit(1)
    if not parsed.hostname:
        sys.stderr.write("INTENTPROOF_API_BASE must include a hostname.\n")
        sys.exit(1)
    if (parsed.username not in (None, "")) or (parsed.password not in (None, "")):
        sys.stderr.write(
            "INTENTPROOF_API_BASE must not include username/password; use headers instead.\n"
        )
        sys.exit(1)
    if parsed.query or parsed.fragment:
        sys.stderr.write(
            "INTENTPROOF_API_BASE must not include a query string or fragment; "
            "use the origin and optional path only.\n"
        )
        sys.exit(1)

    path = parsed.path or ""
    path_out = "" if path in ("", "/") else path.rstrip("/")

    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path_out, "", ""))
