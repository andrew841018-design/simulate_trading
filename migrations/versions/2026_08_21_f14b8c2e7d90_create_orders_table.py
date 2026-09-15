"""create orders table

Revision ID: f14b8c2e7d90
Revises: c6c622f0b972
Create Date: 2026-08-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f14b8c2e7d90"
down_revision: str | Sequence[str] | None = "c6c622f0b972"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the orders table."""
    op.create_table("orders", 
    sa.Column("order_id", sa.Text(), nullable=False),
    sa.Column("account_id", sa.Text(), nullable=False),
    sa.Column("action", sa.Text(), nullable=False),
    sa.Column("order_type", sa.Text(), nullable=False),
    sa.Column("quantity", sa.Integer(), nullable=False),
    sa.Column("fill_quantity", sa.Integer(), nullable=False,server_default="0"),
    sa.Column("symbol", sa.Text(), nullable=False),
    sa.Column("price", sa.Numeric(12, 2), nullable=False),
    sa.Column("status", sa.Text(), nullable=False,server_default="OPEN"),
    sa.Column("version", sa.Integer(), nullable=False,server_default="1"),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,server_default=sa.func.now()),
    sa.CheckConstraint("symbol IS NOT NULL AND symbol <> ''", name="check_symbol_not_empty"),
    sa.CheckConstraint("quantity > 0", name="check_quantity_non_negative"),
    sa.CheckConstraint(
        "char_length(symbol) BETWEEN 1 AND 32",
        name="check_symbol_length_valid",
    ),
    sa.CheckConstraint("fill_quantity >= 0", name="check_fill_quantity_non_negative"),
    sa.CheckConstraint("price > 0", name="check_price_non_negative"),
    sa.CheckConstraint("order_type IN ('LIMIT')", name="check_order_type_valid"),
    sa.CheckConstraint("action IN ('BUY', 'SELL')", name="check_action_valid"),
    sa.CheckConstraint("status IN ('PARTIAL_FILLED', 'FILLED', 'CANCELLED','OPEN')", name="check_status_valid"),
    sa.CheckConstraint("version > 0", name="check_version_non_negative"),
    sa.CheckConstraint("fill_quantity <= quantity", name="check_fill_quantity_not_exceed_quantity"),
    sa.CheckConstraint("char_length(order_id) > 0", name="check_order_id_not_null"),
    sa.CheckConstraint("char_length(account_id) > 0", name="check_account_id_not_null"),
    sa.CheckConstraint(
    """
    (
        status = 'PARTIAL_FILLED' AND fill_quantity < quantity AND fill_quantity > 0
    )
    OR
    (
        status = 'FILLED' AND fill_quantity = quantity
    )
    OR
    (
        status = 'CANCELLED' AND fill_quantity < quantity
    )
    OR
    (
        status = 'OPEN' AND fill_quantity = 0
    )
    """,name="check_status_fill_quantity_valid"
    ),
    sa.ForeignKeyConstraint(["account_id"], ["accounts.account_id"], name="fk_orders_account_id_accounts",ondelete="RESTRICT"),
    sa.PrimaryKeyConstraint("order_id", name="pk_orders")
    )
    op.create_index("idx_orders_account_status", "orders", ["account_id", "status"])


def downgrade() -> None:
    """Drop the orders table."""
    op.drop_index("idx_orders_account_status", table_name="orders")
    op.drop_table("orders")
