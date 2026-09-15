"""Add idempotency, saved-response, and atomic-outbox schema.

Revision ID: 8c2f39a71d4e
Revises: f14b8c2e7d90
Create Date: 2026-08-26
"""
from sqlalchemy.dialects.postgresql import JSONB
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c2f39a71d4e"
down_revision: str | Sequence[str] | None = "f14b8c2e7d90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the approved Day 3 idempotency and outbox schema."""
    op.create_table(
        "idempotency_requests",
        sa.Column("request_payload", JSONB(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            """
            (response_status IS NULL AND response_body IS NULL)
            OR 
            (response_status IS NOT NULL AND response_body IS NOT NULL)
            """
            , name="check_response_status_and_body_valid"),
        sa.CheckConstraint("response_status BEtween 100 and 599", name="check_response_status_valid"),
        sa.CheckConstraint("idempotency_key IS NOT NULL AND idempotency_key <> ''", name="check_idempotency_key_not_empty"),
        sa.PrimaryKeyConstraint("idempotency_key", name="idempotency_requests_pkey"),
    )
    op.create_table(
        "order_transitions",
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("status_change_version", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.Text(), nullable=True),
        sa.Column("current_status", sa.Text(), nullable=False),
        sa.Column("transition_type", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            """
            (
                status_change_version = 1
                AND previous_status IS NULL
                AND current_status = 'OPEN'
            )
            OR
            (
                status_change_version > 1
                AND previous_status IS NOT NULL
            )
            """
            , name="check_status_change_version_valid"),
        sa.CheckConstraint("transition_type IS NOT NULL AND char_length(transition_type) BETWEEN 1 AND 32", name="check_transition_type_length_valid"),
        sa.CheckConstraint("transition_type IN ('ORDER_CANCELLED', 'ORDER_PARTIALLY_FILLED', 'ORDER_FILLED','ORDER_CREATED')", name="check_transition_type_domain_valid"),
        sa.CheckConstraint("previous_status IN('OPEN', 'PARTIAL_FILLED', 'FILLED', 'CANCELLED')", name="check_previous_status_valid"),
        sa.CheckConstraint("current_status IN('OPEN', 'PARTIAL_FILLED', 'FILLED', 'CANCELLED')", name="check_current_status_valid"),
        sa.CheckConstraint("status_change_version > 0", name="check_status_change_version_non_zero"),
        sa.PrimaryKeyConstraint("order_id","status_change_version",name="order_transitions_pkey"),
        sa.ForeignKeyConstraint(["order_id"],["orders.order_id"], ondelete="RESTRICT", name="order_transitions_order_id_fkey"),

    )
    op.create_table(
        "outbox_events",
        sa.Column("outbox_id", sa.BigInteger(),sa.Identity(start=1,always=True), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_change_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("published_at IS NULL OR published_at >= created_at", name="check_published_at_valid"),
        sa.ForeignKeyConstraint(["order_id","status_change_version"],["order_transitions.order_id","order_transitions.status_change_version"], ondelete="RESTRICT", name="outbox_events_order_id_composite_fkey"),
        sa.CheckConstraint("event_id IS NOT NULL AND event_id <> ''", name="check_event_id_valid"),
        sa.UniqueConstraint("order_id","status_change_version",name="order_id_status_change_version_unique"),
        sa.UniqueConstraint("event_id",name="outbox_events_event_id_unique"),
        sa.CheckConstraint("status_change_version > 0", name="check_status_change_version_non_zero"),
        sa.CheckConstraint("event_type IS NOT NULL AND char_length(event_type) BETWEEN 1 AND 32", name="check_event_type_valid"),
        sa.PrimaryKeyConstraint("outbox_id",name="outbox_events_pkey"),
    )

def downgrade() -> None:
    """Drop the Day 3 idempotency and outbox schema."""
    op.drop_table("outbox_events")
    op.drop_table("order_transitions")
    op.drop_table("idempotency_requests")
