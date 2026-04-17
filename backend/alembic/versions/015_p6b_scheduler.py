"""P6b: schedule_enabled, schedule_minutes -> sync_schedule conversion, drop schedule_minutes

Revision ID: 015_p6b_scheduler
Revises: 014_p6a_idempotency
Create Date: 2026-04-16

NOTE: As of 2026-04-16, no production rows have schedule_minutes set
(the UI never exposed this field). The conversion loop will process 0 rows
in a clean deployment. Verify before running on any deployment with schedule_minutes data.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = '015_p6b_scheduler'
down_revision: Union[str, None] = '014_p6a_idempotency'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALLOWLIST = {
    5:    "*/5 * * * *",
    10:   "*/10 * * * *",
    15:   "*/15 * * * *",
    20:   "*/20 * * * *",
    30:   "*/30 * * * *",
    60:   "0 * * * *",
    120:  "0 */2 * * *",
    180:  "0 */3 * * *",
    240:  "0 */4 * * *",
    360:  "0 */6 * * *",
    480:  "0 */8 * * *",
    720:  "0 */12 * * *",
    1440: "0 2 * * *",
}


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column(
        "data_sources",
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.create_check_constraint(
        "chk_sync_schedule_nonempty",
        "data_sources",
        "sync_schedule IS NULL OR length(trim(sync_schedule)) > 0",
    )

    op.create_table(
        "_migration_015_report",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("source_name", sa.String(255)),
        sa.Column("schedule_minutes", sa.Integer()),
        sa.Column("action", sa.String(20)),
        sa.Column("cron_expression", sa.String(50), nullable=True),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    rows = conn.execute(
        text("SELECT id, name, schedule_minutes FROM data_sources WHERE schedule_minutes IS NOT NULL")
    ).fetchall()

    for row in rows:
        source_id, name, minutes = str(row[0]), row[1], row[2]
        if minutes in _ALLOWLIST:
            cron = _ALLOWLIST[minutes]
            conn.execute(
                text("UPDATE data_sources SET sync_schedule = :cron WHERE id = :id"),
                {"cron": cron, "id": source_id},
            )
            conn.execute(
                text("""INSERT INTO _migration_015_report
                         (source_id, source_name, schedule_minutes, action, cron_expression, note)
                         VALUES (:sid, :name, :min, 'converted', :cron, 'Clean conversion')"""),
                {"sid": source_id, "name": name, "min": minutes, "cron": cron},
            )
            print(
                f"MIGRATION REPORT: Source {source_id} ('{name}'): "
                f"schedule_minutes={minutes} -> sync_schedule='{cron}'"
            )
        else:
            conn.execute(
                text("""UPDATE data_sources
                         SET sync_schedule = NULL, schedule_enabled = false
                         WHERE id = :id"""),
                {"id": source_id},
            )
            note = (
                f"schedule_minutes={minutes} has no clean cron equivalent. "
                f"Example: */45 fires at :00 and :45 only (15-min gap at hour boundary). "
                f"Admin action required: set a schedule manually in DataSources UI."
            )
            conn.execute(
                text("""INSERT INTO _migration_015_report
                         (source_id, source_name, schedule_minutes, action, cron_expression, note)
                         VALUES (:sid, :name, :min, 'nulled', NULL, :note)"""),
                {"sid": source_id, "name": name, "min": minutes, "note": note},
            )
            print(
                f"MIGRATION REPORT: Source {source_id} ('{name}'): "
                f"schedule_minutes={minutes} has no clean cron equivalent. "
                f"sync_schedule set to NULL, schedule_enabled set to False. "
                f"Admin action required."
            )

    op.drop_column("data_sources", "schedule_minutes")

    for col_def in [
        sa.Column("consecutive_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_message", sa.String(500), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sync_paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_paused_reason", sa.String(200), nullable=True),
        sa.Column("retry_batch_size", sa.Integer(), nullable=True),
        sa.Column("retry_time_limit_seconds", sa.Integer(), nullable=True),
    ]:
        op.add_column("data_sources", col_def)


def downgrade() -> None:
    for col in [
        "retry_time_limit_seconds", "retry_batch_size", "sync_paused_reason",
        "sync_paused_at", "sync_paused", "last_error_at", "last_error_message",
        "consecutive_failure_count",
    ]:
        op.drop_column("data_sources", col)
    op.add_column(
        "data_sources",
        sa.Column("schedule_minutes", sa.Integer(), nullable=True),
    )
    op.drop_table("_migration_015_report")
    op.drop_constraint("chk_sync_schedule_nonempty", "data_sources", type_="check")
    op.drop_column("data_sources", "schedule_enabled")
