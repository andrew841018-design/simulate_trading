"""Add the approved outbox event-type domain constraint.

Revision ID: d3f7a4c91e20
Revises: 8c2f39a71d4e
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f7a4c91e20"
down_revision: str | Sequence[str] | None = "8c2f39a71d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Restrict outbox event types to the approved v1 domain."""
    op.create_check_constraint(
        "check_outbox_event_type_domain_valid",
        "outbox_events",
        "event_type IN ("
        "'ORDER_CREATED', "
        "'ORDER_PARTIALLY_FILLED', "
        "'ORDER_FILLED', "
        "'ORDER_CANCELLED'"
        ")",
    )


def downgrade() -> None:
    """Remove the outbox event-type domain constraint."""
    op.drop_constraint(
        "check_outbox_event_type_domain_valid",
        "outbox_events",
        type_="check",
    )
