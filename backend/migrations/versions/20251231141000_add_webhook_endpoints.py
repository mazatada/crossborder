"""add webhook_endpoints and order_statuses tables

Revision ID: 20251231141000
Revises: 95f75de98be3
Create Date: 2025-12-31 14:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251231141000"
down_revision = "95f75de98be3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("secret", sa.String(length=128), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "order_statuses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("customer_region", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_order_statuses_order_id"), "order_statuses", ["order_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_order_statuses_order_id"), table_name="order_statuses")
    op.drop_table("order_statuses")
    op.drop_table("webhook_endpoints")
