"""add webhook_dlq table

Revision ID: 20251205151851
Revises: 95f75de98be3
Create Date: 2025-12-05 15:18:51

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251205151851'
down_revision = '95f75de98be3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'webhook_dlq',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('trace_id', sa.String(length=64), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_status_code', sa.Integer(), nullable=True),
        sa.Column('replayed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhook_endpoints.id'], ),
    )
    op.create_index(op.f('ix_webhook_dlq_trace_id'), 'webhook_dlq', ['trace_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_webhook_dlq_trace_id'), table_name='webhook_dlq')
    op.drop_table('webhook_dlq')
