"""create accounts table

Revision ID: c6c622f0b972
Revises: 
Create Date: 2026-08-12 17:09:08.715980

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6c622f0b972'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'accounts',
        sa.Column('account_id', sa.Text(), nullable=False),
        sa.Column('total_cash', sa.Numeric(12, 2), nullable=False),
        sa.Column('reserved_cash', sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint('total_cash >= 0', name='check_total_cash_non_negative'),
        sa.CheckConstraint('reserved_cash >= 0', name='check_reserved_cash_non_negative'),
        sa.CheckConstraint('reserved_cash <= total_cash', name='check_reserved_cash_not_exceed_total_cash'),
        sa.PrimaryKeyConstraint('account_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('accounts')
