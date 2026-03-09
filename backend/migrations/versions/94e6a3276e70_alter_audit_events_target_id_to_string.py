"""alter_audit_events_target_id_to_string

Revision ID: 94e6a3276e70
Revises: d2522fdabd36
Create Date: 2026-03-04 12:45:43.639882

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "94e6a3276e70"
down_revision: Union[str, Sequence[str], None] = "d2522fdabd36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard: check if target_id column exists; if not, skip (table was created
    # with TEXT type already via CREATE_TABLE_SQL in audit.py).
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("audit_events")]
    if "target_id" not in columns:
        # Column doesn't exist – nothing to alter
        return
    # Use batch_alter_table to support SQLite as well as PostgreSQL
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.alter_column(
            "target_id",
            existing_type=sa.BigInteger(),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    # Need to cast back if downgrading on Postgres.
    # For simplicity, using basic alter_column. In SQLite this might drop/recreate.
    with op.batch_alter_table("audit_events") as batch_op:
        # PostgreSQL might require postgresql_using="target_id::bigint" if there are non-numeric strings
        # but for downgrade we assume they are numeric strings if we revert.
        batch_op.alter_column(
            "target_id",
            existing_type=sa.Text(),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )
