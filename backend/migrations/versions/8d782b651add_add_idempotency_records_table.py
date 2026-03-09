"""add_idempotency_records_table

Revision ID: 8d782b651add
Revises: f08228a2cf59
Create Date: 2026-03-09 05:26:06.333644

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8d782b651add"
down_revision: Union[str, Sequence[str], None] = "f08228a2cf59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- New table: idempotency_records ---
    # init_db() で既に作成されている場合があるので、存在確認する
    from alembic import op as _op

    conn = _op.get_bind()
    result = conn.execute(
        sa.text("SELECT to_regclass('public.idempotency_records')")
    ).scalar()
    if result is None:
        op.create_table(
            "idempotency_records",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("scope", sa.String(length=128), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("response_code", sa.Integer(), nullable=True),
            sa.Column("response_body", sa.JSON(), nullable=True),
            sa.Column("resource_type", sa.String(length=64), nullable=True),
            sa.Column("resource_id", sa.String(length=128), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "scope", "idempotency_key", name="uq_idempotency_scope_key"
            ),
        )
        op.create_index(
            op.f("ix_idempotency_records_scope"), "idempotency_records", ["scope"]
        )

    # --- Type changes from PR review (Pre-4 corrections) ---
    # NOTE: DOUBLE_PRECISION → Numeric(12, 2) は小数点以下2桁を超える値を切り捨てます。
    # 本番適用前に既存データの範囲を確認してください：
    #   SELECT MAX(unit_price), MAX(unit_price - ROUND(unit_price::numeric, 2)) FROM shipment_lines;
    op.alter_column(
        "media_blobs",
        "size",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "shipment_lines",
        "unit_price",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        type_=sa.Numeric(precision=12, scale=2),
        existing_nullable=False,
    )
    op.alter_column(
        "shipment_lines",
        "line_value",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        type_=sa.Numeric(precision=12, scale=2),
        existing_nullable=False,
    )
    op.alter_column(
        "shipments",
        "total_value",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        type_=sa.Numeric(precision=12, scale=2),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema.

    WARNING: ダウングレード時の注意事項
    - Numeric(12,2) → DOUBLE_PRECISION: 精度が変わりますが実用上は問題ありません。
    - BigInteger → INTEGER: 2GB (2,147,483,647) を超えるレコードが存在する場合、
      オーバーフローエラーが発生します。事前確認クエリ:
        SELECT COUNT(*) FROM media_blobs WHERE size > 2147483647;
    """
    op.alter_column(
        "shipments",
        "total_value",
        existing_type=sa.Numeric(precision=12, scale=2),
        type_=sa.DOUBLE_PRECISION(precision=53),
        existing_nullable=False,
    )
    op.alter_column(
        "shipment_lines",
        "line_value",
        existing_type=sa.Numeric(precision=12, scale=2),
        type_=sa.DOUBLE_PRECISION(precision=53),
        existing_nullable=False,
    )
    op.alter_column(
        "shipment_lines",
        "unit_price",
        existing_type=sa.Numeric(precision=12, scale=2),
        type_=sa.DOUBLE_PRECISION(precision=53),
        existing_nullable=False,
    )
    op.alter_column(
        "media_blobs",
        "size",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
    op.drop_index(
        op.f("ix_idempotency_records_scope"), table_name="idempotency_records"
    )
    op.drop_table("idempotency_records")
