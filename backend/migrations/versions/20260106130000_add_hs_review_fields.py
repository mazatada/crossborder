"""add hs review fields

Revision ID: 20260106130000
Revises: 20251231141500
Create Date: 2026-01-06 13:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260106130000"
down_revision = "20251231141500"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "hs_classifications",
        sa.Column("duty_rate_override", sa.JSON(), nullable=True),
    )
    op.add_column(
        "hs_classifications",
        sa.Column("status", sa.String(length=16), nullable=True, server_default="classified"),
    )
    op.add_column(
        "hs_classifications",
        sa.Column("final_source", sa.String(length=32), nullable=True, server_default="system"),
    )
    op.add_column(
        "hs_classifications",
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "hs_classifications",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "hs_classifications",
        sa.Column("review_comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "hs_classifications",
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_column("hs_classifications", "updated_at")
    op.drop_column("hs_classifications", "review_comment")
    op.drop_column("hs_classifications", "reviewed_at")
    op.drop_column("hs_classifications", "reviewed_by")
    op.drop_column("hs_classifications", "final_source")
    op.drop_column("hs_classifications", "status")
    op.drop_column("hs_classifications", "duty_rate_override")
