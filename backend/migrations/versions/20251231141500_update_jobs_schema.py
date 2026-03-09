"""update jobs schema for runtime fields

Revision ID: 20251231141500
Revises: 20251205182731
Create Date: 2025-12-31 14:15:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251231141500"
down_revision = "20251205182731"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "jobs",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "jobs",
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("payload_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("result_json", sa.JSON(), nullable=True),
    )

    op.alter_column(
        "jobs",
        "id",
        existing_type=sa.String(length=40),
        type_=sa.BigInteger(),
        nullable=False,
        postgresql_using="id::bigint",
    )
    op.execute("CREATE SEQUENCE IF NOT EXISTS jobs_id_seq")
    op.execute("ALTER SEQUENCE jobs_id_seq OWNED BY jobs.id")
    op.execute("ALTER TABLE jobs ALTER COLUMN id SET DEFAULT nextval('jobs_id_seq')")


def downgrade():
    op.execute("ALTER TABLE jobs ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS jobs_id_seq")
    op.alter_column(
        "jobs",
        "id",
        existing_type=sa.BigInteger(),
        type_=sa.String(length=40),
        nullable=False,
    )
    op.drop_column("jobs", "result_json")
    op.drop_column("jobs", "payload_json")
    op.drop_column("jobs", "next_run_at")
    op.drop_column("jobs", "attempts")
