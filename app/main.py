import hashlib
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_tenant_id_from_api_key
from app.db import Base, get_db, get_engine
from app.models import ExecutionEventRecord
from app.schemas import (
    CorrelationQueryResponse,
    ErrorEnvelope,
    ExecutionEventIn,
    IngestEventResponse,
    StoredEventOut,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=get_engine())
    yield


app = FastAPI(title="IntentProof API", version="0.1.0", lifespan=lifespan)


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
    db.commit()

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
