"""extend request_status enum with new values

Revision ID: 008_extend_status
Revises: 787207afc66a
Create Date: 2026-04-12
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers
revision: str = '008_extend_status'
down_revision: Union[str, None] = '787207afc66a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new values to the request_status PostgreSQL ENUM type
    # PostgreSQL requires ALTER TYPE ... ADD VALUE for each new value
    op.execute("ALTER TYPE request_status ADD VALUE IF NOT EXISTS 'clarification_needed'")
    op.execute("ALTER TYPE request_status ADD VALUE IF NOT EXISTS 'assigned'")
    op.execute("ALTER TYPE request_status ADD VALUE IF NOT EXISTS 'ready_for_release'")
    op.execute("ALTER TYPE request_status ADD VALUE IF NOT EXISTS 'fulfilled'")
    op.execute("ALTER TYPE request_status ADD VALUE IF NOT EXISTS 'closed'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an ENUM type
    # To downgrade, you would need to recreate the type, which is destructive
    pass
