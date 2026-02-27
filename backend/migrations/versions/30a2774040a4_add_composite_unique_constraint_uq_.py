"""Add composite unique constraint uq_order_status

Revision ID: 30a2774040a4
Revises: 20260106130000
Create Date: 2026-02-27 11:40:21.739728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30a2774040a4'
down_revision: Union[str, Sequence[str], None] = '20260106130000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uq_order_status', 'order_statuses', ['order_id', 'status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_order_status', 'order_statuses', type_='unique')
