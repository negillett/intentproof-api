from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.generated import IntentProofExecutionEventV1


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


ExecutionEventIn = IntentProofExecutionEventV1


class IngestEventResponse(BaseModel):
    accepted: bool = True
    duplicate: bool = False
    tenant_id: str
    event_id: str
    correlation_id: str | None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StoredEventOut(BaseModel):
    tenant_id: str
    event_hash: str
    correlation_id: str | None
    event_type: str
    received_at: datetime
    raw_event: dict[str, Any]


class CorrelationQueryResponse(BaseModel):
    tenant_id: str
    correlation_id: str
    items: list[StoredEventOut]
    next_cursor: str | None = None
