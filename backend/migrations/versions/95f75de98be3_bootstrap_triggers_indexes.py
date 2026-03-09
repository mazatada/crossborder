"""bootstrap triggers & indexes

Revision ID: 95f75de98be3
Revises: 08ff8cabbb53
Create Date: 2025-10-25 05:54:40.979796

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "95f75de98be3"
down_revision: Union[str, Sequence[str], None] = "08ff8cabbb53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
