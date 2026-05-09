"""Optional Amazon SQS notification after successful append-only ingest.

Uses a **transactional outbox** (``proof_ingest_outbox``) in the same database
transaction as ``execution_events`` inserts, then a publisher calls
``SendMessage`` and marks ``published_at``. Fail-open: ingest still returns
**202** if SQS is down; use :func:`publish_pending_outbox` to retry.

Envelope fields include ``schema_version``, ``type``, ``message_id``, ``tenant_id``,
``execution_event_row_id``. Workers must load full payloads from Postgres by row id;
SQS is not canonical storage.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ENVELOPE_SCHEMA_VERSION = 1
MESSAGE_TYPE = "intentproof.proof.ingested"


def build_proof_ingested_envelope(
    *,
    tenant_id: str,
    record_id: int,
    event_hash: str,
    correlation_id: str | None,
    action: str,
    message_id: str | None = None,
) -> dict[str, Any]:
    """Versioned SQS body; workers load full event from Postgres by row id + tenant."""
    return {
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "type": MESSAGE_TYPE,
        "message_id": message_id or str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "execution_event_row_id": record_id,
        "event_hash": event_hash,
        "correlation_id": correlation_id,
        "action": action,
    }


def envelope_to_json_bytes(envelope: dict[str, Any]) -> str:
    return json.dumps(envelope, separators=(",", ":"), sort_keys=True)


def should_enqueue_to_outbox() -> bool:
    from app.config import get_settings

    return bool(get_settings().sqs_queue_url)


def _sqs_client():
    from app.config import get_settings

    settings = get_settings()
    kwargs: dict[str, Any] = {}
    if settings.aws_region:
        kwargs["region_name"] = settings.aws_region
    return boto3.client("sqs", **kwargs)


def send_envelope_to_sqs(message_body: str) -> None:
    from app.config import get_settings

    settings = get_settings()
    queue_url = settings.sqs_queue_url
    if not queue_url:
        return
    sqs = _sqs_client()
    sqs.send_message(QueueUrl=queue_url, MessageBody=message_body)


def publish_outbox_row(db: Session, outbox_id: int) -> bool:
    """Send one unpublished outbox row to SQS; mark ``published_at`` on success.

    Returns True if published or already published; False on failure (row updated).
    """
    from app.config import get_settings
    from app.models import ProofIngestOutbox

    settings = get_settings()
    if not settings.sqs_queue_url:
        return True

    row = db.get(ProofIngestOutbox, outbox_id)
    if row is None:
        logger.error("Outbox row missing id=%s", outbox_id)
        return False
    if row.published_at is not None:
        return True

    try:
        send_envelope_to_sqs(row.payload_json)
    except Exception as exc:
        row.publish_attempts = int(row.publish_attempts) + 1
        row.last_error = str(exc)[:4096]
        logger.exception(
            "Outbox publish failed (tenant=%s outbox=%s execution_event=%s)",
            row.tenant_id,
            outbox_id,
            row.execution_event_id,
        )
        db.commit()
        return False

    row.published_at = datetime.now(UTC)
    row.last_error = None
    db.commit()
    return True


def publish_pending_outbox(db: Session, *, limit: int = 100) -> int:
    """Publish up to ``limit`` rows with ``published_at IS NULL``. Returns count attempted."""
    from app.models import ProofIngestOutbox

    if not should_enqueue_to_outbox():
        return 0

    rows = db.scalars(
        select(ProofIngestOutbox)
        .where(ProofIngestOutbox.published_at.is_(None))
        .order_by(ProofIngestOutbox.id.asc())
        .limit(limit)
    ).all()

    n = 0
    for row in rows:
        if publish_outbox_row(db, row.id):
            n += 1
    return n
