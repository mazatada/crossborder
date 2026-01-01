"""add hs_classifications table

Revision ID: 20251205182731
Revises: 20251205151851
Create Date: 2025-12-05 18:27:31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251205182731'
down_revision = '20251205151851'
branch_labels = None
depends_on = None


def upgrade():
    """hs_classificationsテーブルを作成"""
    op.create_table(
        'hs_classifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.String(length=128), nullable=True),
        sa.Column('trace_id', sa.String(length=64), nullable=False),
        
        # 入力データ
        sa.Column('product_name', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('origin_country', sa.String(length=2), nullable=True),
        sa.Column('ingredients', sa.JSON(), nullable=True),
        sa.Column('process', sa.JSON(), nullable=True),
        
        # 分類結果
        sa.Column('hs_candidates', sa.JSON(), nullable=False),
        sa.Column('final_hs_code', sa.String(length=16), nullable=False),
        sa.Column('required_uom', sa.String(length=8), nullable=False),
        sa.Column('review_required', sa.Boolean(), nullable=False, server_default='false'),
        
        # 拡張フィールド
        sa.Column('duty_rate', sa.JSON(), nullable=True),
        sa.Column('risk_flags', sa.JSON(), nullable=True),
        sa.Column('quota_applicability', sa.String(length=64), nullable=True),
        sa.Column('explanations', sa.JSON(), nullable=True),
        
        # メタデータ
        sa.Column('classification_method', sa.String(length=32), nullable=True, server_default='rule_based'),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('cache_hit', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('rules_version', sa.String(length=16), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # インデックス作成
    op.create_index('ix_hs_classifications_trace_id', 'hs_classifications', ['trace_id'])
    op.create_index('ix_hs_classifications_product_id', 'hs_classifications', ['product_id'])
    op.create_index('ix_hs_classifications_final_hs_code', 'hs_classifications', ['final_hs_code'])
    op.create_index('ix_hs_classifications_category', 'hs_classifications', ['category'])
    op.create_index('ix_hs_classifications_review_required', 'hs_classifications', ['review_required'])


def downgrade():
    """hs_classificationsテーブルを削除"""
    op.drop_index('ix_hs_classifications_review_required', table_name='hs_classifications')
    op.drop_index('ix_hs_classifications_category', table_name='hs_classifications')
    op.drop_index('ix_hs_classifications_final_hs_code', table_name='hs_classifications')
    op.drop_index('ix_hs_classifications_product_id', table_name='hs_classifications')
    op.drop_index('ix_hs_classifications_trace_id', table_name='hs_classifications')
    op.drop_table('hs_classifications')
