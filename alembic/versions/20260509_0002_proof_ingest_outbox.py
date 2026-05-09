"""proof_ingest_outbox transactional queue handoff

Revision ID: 20260509_0002
Revises: 20260509_0001
Create Date: 2026-05-09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260509_0002"
down_revision = "20260509_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proof_ingest_outbox",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("execution_event_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["execution_event_id"],
            ["execution_events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_proof_ingest_outbox_execution_event_id"),
        "proof_ingest_outbox",
        ["execution_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_proof_ingest_outbox_tenant_id"),
        "proof_ingest_outbox",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_proof_ingest_outbox_published_at",
        "proof_ingest_outbox",
        ["published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_proof_ingest_outbox_published_at", table_name="proof_ingest_outbox")
    op.drop_index(op.f("ix_proof_ingest_outbox_tenant_id"), table_name="proof_ingest_outbox")
    op.drop_index(
        op.f("ix_proof_ingest_outbox_execution_event_id"),
        table_name="proof_ingest_outbox",
    )
    op.drop_table("proof_ingest_outbox")
