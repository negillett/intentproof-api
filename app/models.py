from sqlalchemy import JSON, DateTime, String, UniqueConstraint, func
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
