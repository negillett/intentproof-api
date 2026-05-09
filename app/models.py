from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ExecutionEventRecord(Base):
    __tablename__ = "execution_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_hash", name="uq_execution_events_tenant_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(256), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(256), nullable=False)
    raw_event: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProofIngestOutbox(Base):
    """Transactional outbox for SQS handoff (same DB transaction as execution_events insert).

    Rows exist only when ``INTENTPROOF_SQS_QUEUE_URL`` is configured at ingest time.
    """

    __tablename__ = "proof_ingest_outbox"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    execution_event_id: Mapped[int] = mapped_column(
        ForeignKey("execution_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publish_attempts: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
