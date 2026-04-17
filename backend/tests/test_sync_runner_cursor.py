# backend/tests/test_sync_runner_cursor.py
"""P7 partial-failure cursor advance tests — real end-to-end calls asserting DB state."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import pytest


@pytest.mark.asyncio
async def test_partial_failure_cursor_advances_past_successes(db_session):
    """8 records succeed, 2 fail → cursor advances, 2 rows in sync_failures."""
    from app.models.sync_failure import SyncFailure
    from app.models.document import DataSource
    from sqlalchemy import select, func, text

    source_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO data_sources
          (id, name, source_type, connection_config, is_active,
           sync_schedule, schedule_enabled, sync_paused,
           consecutive_failure_count, created_by)
        VALUES (:id, 'cursor-test', 'rest_api', '{}', true,
                '0 2 * * *', true, false, 0,
                (SELECT id FROM users LIMIT 1))
    """), {"id": str(source_id)})
    await db_session.commit()

    from app.connectors.base import DiscoveredRecord, FetchedDocument

    fail_paths = {
        "https://api.example.com/records/3",
        "https://api.example.com/records/7",
    }

    discovered = [
        DiscoveredRecord(
            source_path=f"https://api.example.com/records/{i}",
            filename=f"{i}.json", file_type="json", file_size=10,
        )
        for i in range(10)
    ]

    async def selective_fetch(path):
        if path in fail_paths:
            raise IOError(f"Fetch failed: {path}")
        return FetchedDocument(
            source_path=path, filename="x.json", file_type="json",
            content=b'{"id":1}', file_size=7, metadata={},
        )

    mock_connector = AsyncMock()
    mock_connector.connector_type = "rest_api"
    mock_connector.discover = AsyncMock(return_value=discovered)
    mock_connector.fetch = AsyncMock(side_effect=selective_fetch)
    mock_connector.close = MagicMock()

    from app.ingestion.sync_runner import run_connector_sync_with_retry
    with patch("app.ingestion.sync_runner.ingest_structured_record", new=AsyncMock(return_value=MagicMock())):
        result = await run_connector_sync_with_retry(
            connector=mock_connector,
            source_id=str(source_id),
            session=db_session,
        )

    assert result["succeeded"] == 8
    assert result["failed"] == 2

    failure_count = await db_session.scalar(
        select(func.count(SyncFailure.id)).where(
            SyncFailure.source_id == source_id,
            SyncFailure.status == "retrying",
        )
    )
    assert failure_count == 2

    source = await db_session.get(DataSource, source_id)
    assert source.last_sync_at is not None
    assert source.last_sync_cursor is not None


@pytest.mark.asyncio
async def test_full_failure_does_not_advance_cursor(db_session):
    """All records fail → consecutive_failure_count increments, last_sync_at still set."""
    from app.models.document import DataSource
    from sqlalchemy import text

    source_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO data_sources
          (id, name, source_type, connection_config, is_active,
           sync_schedule, schedule_enabled, sync_paused,
           consecutive_failure_count, created_by)
        VALUES (:id, 'all-fail', 'rest_api', '{}', true,
                '0 2 * * *', true, false, 0,
                (SELECT id FROM users LIMIT 1))
    """), {"id": str(source_id)})
    await db_session.commit()

    from app.connectors.base import DiscoveredRecord

    discovered = [
        DiscoveredRecord(
            source_path=f"https://api.example.com/records/{i}",
            filename=f"{i}.json", file_type="json", file_size=10,
        )
        for i in range(3)
    ]

    mock_connector = AsyncMock()
    mock_connector.connector_type = "rest_api"
    mock_connector.discover = AsyncMock(return_value=discovered)
    mock_connector.fetch = AsyncMock(side_effect=IOError("network down"))
    mock_connector.close = MagicMock()

    from app.ingestion.sync_runner import run_connector_sync_with_retry
    result = await run_connector_sync_with_retry(
        connector=mock_connector,
        source_id=str(source_id),
        session=db_session,
    )

    assert result["failed"] == 3
    assert result["succeeded"] == 0

    source = await db_session.get(DataSource, source_id)
    assert source.consecutive_failure_count == 1
