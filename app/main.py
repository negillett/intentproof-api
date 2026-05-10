import hashlib
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_tenant_id_from_api_key
from app.config import get_settings
from app.db import Base, database_url_is_sqlite, get_db, get_engine
from app.models import ExecutionEventRecord, ProofIngestOutbox
from app.schemas import (
    CorrelationQueryResponse,
    ErrorEnvelope,
    ExecutionEventIn,
    IngestEventResponse,
    StoredEventOut,
)
from app.verification_queue import (
    build_proof_ingested_envelope,
    envelope_to_json_bytes,
    publish_outbox_row,
    should_enqueue_to_outbox,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # SQLite (tests): auto-create.
    # Postgres: apply schema with `alembic upgrade head` (Docker entrypoint or deploy).
    if database_url_is_sqlite(get_settings().database_url):
        Base.metadata.create_all(bind=get_engine())
    yield


app = FastAPI(title="IntentProof API", version="0.2.0", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and {"code", "message"} <= set(exc.detail):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    envelope = ErrorEnvelope(
        code="http_error",
        message=str(exc.detail),
        details={},
        correlation_id=request.headers.get("x-correlation-id"),
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())


@app.get("/health")
def health():
    return {"status": "ok"}


def hash_event(event: ExecutionEventIn) -> str:
    encoded = json.dumps(
        event.model_dump(mode="json"), separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@app.post("/v1/events", response_model=IngestEventResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_event(
    event: ExecutionEventIn,
    tenant_id: str = Depends(get_tenant_id_from_api_key),
    db: Session = Depends(get_db),
):
    event_hash = hash_event(event)

    existing = db.scalar(
        select(ExecutionEventRecord).where(
            ExecutionEventRecord.tenant_id == tenant_id,
            ExecutionEventRecord.event_hash == event_hash,
        )
    )
    if existing:
        return IngestEventResponse(
            accepted=True,
            duplicate=True,
            tenant_id=tenant_id,
            event_id=event.id,
            correlation_id=event.correlation_id,
            ingested_at=datetime.now(UTC),
        )

    record = ExecutionEventRecord(
        tenant_id=tenant_id,
        event_hash=event_hash,
        correlation_id=event.correlation_id,
        action=event.action,
        raw_event=event.model_dump(mode="json", by_alias=True),
    )
    db.add(record)
    db.flush()

    outbox_id: int | None = None
    if should_enqueue_to_outbox():
        envelope = build_proof_ingested_envelope(
            tenant_id=tenant_id,
            record_id=record.id,
            event_hash=event_hash,
            correlation_id=event.correlation_id,
            action=event.action,
        )
        outbox = ProofIngestOutbox(
            execution_event_id=record.id,
            tenant_id=tenant_id,
            payload_json=envelope_to_json_bytes(envelope),
            publish_attempts=0,
        )
        db.add(outbox)
        db.flush()
        outbox_id = outbox.id

    db.commit()
    db.refresh(record)

    if outbox_id is not None:
        publish_outbox_row(db, outbox_id)

    return IngestEventResponse(
        accepted=True,
        duplicate=False,
        tenant_id=tenant_id,
        event_id=event.id,
        correlation_id=event.correlation_id,
        ingested_at=datetime.now(UTC),
    )


@app.get("/v1/events/by-correlation/{correlation_id}", response_model=CorrelationQueryResponse)
def get_by_correlation(
    correlation_id: str,
    tenant_id: str = Depends(get_tenant_id_from_api_key),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    records = db.scalars(
        select(ExecutionEventRecord)
        .where(
            ExecutionEventRecord.tenant_id == tenant_id,
            ExecutionEventRecord.correlation_id == correlation_id,
        )
        .order_by(ExecutionEventRecord.id.asc())
        .limit(limit)
    ).all()

    items = [
        StoredEventOut(
            tenant_id=r.tenant_id,
            event_hash=r.event_hash,
            correlation_id=r.correlation_id,
            event_type=r.action,
            received_at=r.received_at,
            raw_event=r.raw_event,
        )
        for r in records
    ]
    return CorrelationQueryResponse(tenant_id=tenant_id, correlation_id=correlation_id, items=items)
