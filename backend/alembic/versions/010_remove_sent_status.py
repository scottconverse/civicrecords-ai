"""remove sent value from request_status enum

Revision ID: 010_remove_sent
Revises: 009_fee_waivers
Create Date: 2026-04-13

Removes the legacy 'sent' value from the request_status PostgreSQL ENUM type.

Background
----------
The 'sent' value was created in migration 005 as part of the original enum and
was documented in the model as "legacy alias for fulfilled". The staff workbench
"Mark Fulfilled" button in RequestDetail.tsx had been wired to POST to
/requests/{id}/sent — a route that does not exist — so every click 404'd and no
records ever transitioned into the 'sent' state via the UI.

Pre-check on the local dev database (2026-04-13):
    records_requests where status='sent'                   : 0
    request_timeline where event_type='request_sent'       : 0
    notification_log via templates event_type='request_sent': 0
    audit_log details LIKE %sent% AND resource_type=request: 0

The defensive UPDATE below is preserved for other operators whose installs may
have non-zero rows from earlier code paths or manual SQL — even though our local
count was zero, this migration ships to every install.

PostgreSQL has no DROP VALUE for enums, so we use the rename-recreate dance.
The column default ('received'::request_status) must be dropped before the type
swap because defaults bind to the type, then restored after.
"""
from typing import Sequence, Union
from alembic import op


# revision identifiers
revision: str = '010_remove_sent'
down_revision: Union[str, None] = '009_fee_waivers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Defensive: move any existing 'sent' rows to 'fulfilled' before type swap.
    #    No-op on installs where the broken UI never produced 'sent' rows.
    op.execute("UPDATE records_requests SET status = 'fulfilled' WHERE status = 'sent'")

    # 2. Drop the column default — it is bound to the old enum type and would
    #    block the ALTER COLUMN TYPE below.
    op.execute("ALTER TABLE records_requests ALTER COLUMN status DROP DEFAULT")

    # 3. Rename the existing enum out of the way.
    op.execute("ALTER TYPE request_status RENAME TO request_status_old")

    # 4. Create the new enum without 'sent'. Order matches the Python enum
    #    declaration in backend/app/models/request.py for clarity, though
    #    application code does not depend on enum sort order.
    op.execute("""
        CREATE TYPE request_status AS ENUM (
            'received',
            'clarification_needed',
            'assigned',
            'searching',
            'in_review',
            'ready_for_release',
            'drafted',
            'approved',
            'fulfilled',
            'closed'
        )
    """)

    # 5. Convert the column from old type to new type. NOT NULL is preserved
    #    automatically by ALTER COLUMN TYPE.
    op.execute("""
        ALTER TABLE records_requests
            ALTER COLUMN status TYPE request_status
            USING status::text::request_status
    """)

    # 6. Restore the default with the new type.
    op.execute("ALTER TABLE records_requests ALTER COLUMN status SET DEFAULT 'received'::request_status")

    # 7. Drop the old enum type.
    op.execute("DROP TYPE request_status_old")


def downgrade() -> None:
    # Intentional no-op. PostgreSQL allows ALTER TYPE ... ADD VALUE to put 'sent'
    # back into the enum, but the upgrade's defensive UPDATE collapsed any rows
    # with status='sent' into status='fulfilled' and that mapping cannot be
    # reversed — the original 'sent' rows are indistinguishable from genuine
    # 'fulfilled' rows after the merge. Reintroducing the enum value without
    # restoring the original data would create a misleading half-downgrade, so
    # the downgrade does nothing. This matches the pattern in migration 008
    # (extend_request_status_enum), which also documented its downgrade as a
    # no-op for the same destructive-data reason.
    pass
