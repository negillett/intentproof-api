"""initial execution_events table

Revision ID: 20260509_0001
Revises:
Create Date: 2026-05-09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260509_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=256), nullable=True),
        sa.Column("action", sa.String(length=256), nullable=False),
        sa.Column("raw_event", sa.JSON(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "event_hash", name="uq_execution_events_tenant_hash"),
    )
    op.create_index(
        op.f("ix_execution_events_correlation_id"),
        "execution_events",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_execution_events_tenant_id"),
        "execution_events",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_execution_events_tenant_id"), table_name="execution_events")
    op.drop_index(op.f("ix_execution_events_correlation_id"), table_name="execution_events")
    op.drop_table("execution_events")
