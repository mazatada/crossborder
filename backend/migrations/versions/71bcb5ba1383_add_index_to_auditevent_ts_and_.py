"""Add index to AuditEvent.ts and WebhookDLQ.expires_at

Revision ID: 71bcb5ba1383
Revises: 30a2774040a4
Create Date: 2026-03-02 12:30:17.982471

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '71bcb5ba1383'
down_revision: Union[str, Sequence[str], None] = '30a2774040a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_audit_events_ts', 'audit_events', ['ts'], unique=False)
    op.create_index('ix_webhook_dlq_expires_at', 'webhook_dlq', ['expires_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_webhook_dlq_expires_at', table_name='webhook_dlq')
    op.drop_index('ix_audit_events_ts', table_name='audit_events')
