#!/usr/bin/env python3
"""Drain unpublished ``proof_ingest_outbox`` rows to SQS (cron / manual replay).

Requires ``INTENTPROOF_SQS_QUEUE_URL`` (and database URL) like the API process.

Usage (from repo root)::

    INTENTPROOF_DATABASE_URL=... INTENTPROOF_SQS_QUEUE_URL=... \\
      python scripts/publish_outbox.py
"""

from __future__ import annotations

from app.db import get_engine
from app.verification_queue import publish_pending_outbox
from sqlalchemy.orm import sessionmaker


def main() -> int:
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        n = publish_pending_outbox(session, limit=500)
        print(f"outbox_publish_success_count={n}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
