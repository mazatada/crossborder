"""phase2_add_snapshot_cols_to_shipment_line

Revision ID: f08228a2cf59
Revises: 94e6a3276e70
Create Date: 2026-03-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f08228a2cf59"
down_revision: Union[str, Sequence[str], None] = "94e6a3276e70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    # ShipmentLine: add currency column
    if not _col_exists("shipment_lines", "currency"):
        op.add_column(
            "shipment_lines",
            sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        )

    # ShipmentLine: add product_snapshot JSON column
    if not _col_exists("shipment_lines", "product_snapshot"):
        op.add_column(
            "shipment_lines", sa.Column("product_snapshot", sa.JSON(), nullable=True)
        )

    # DocumentExport: add s3_key column
    if not _col_exists("document_exports", "s3_key"):
        op.add_column(
            "document_exports", sa.Column("s3_key", sa.String(512), nullable=True)
        )


def downgrade() -> None:
    if _col_exists("document_exports", "s3_key"):
        op.drop_column("document_exports", "s3_key")
    if _col_exists("shipment_lines", "product_snapshot"):
        op.drop_column("shipment_lines", "product_snapshot")
    if _col_exists("shipment_lines", "currency"):
        op.drop_column("shipment_lines", "currency")
