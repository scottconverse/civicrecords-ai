"""Add fee_waivers table.

Revision ID: 009_fee_waivers
Revises: 008_extend_status
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "009_fee_waivers"
down_revision = "008_extend_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fee_waivers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("records_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("waiver_type", sa.String(50), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requested_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_notes", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fee_waivers_request_id", "fee_waivers", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_fee_waivers_request_id")
    op.drop_table("fee_waivers")
