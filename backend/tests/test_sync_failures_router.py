# backend/tests/test_sync_failures_router.py
"""P7 sync-failures API endpoint tests."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text, select, func


@pytest.mark.asyncio
async def test_retry_all_permanently_failed(client: AsyncClient, admin_token: str, db_session):
    """retry-all resets permanently_failed rows to retrying."""
    from app.models.sync_failure import SyncFailure

    source_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO data_sources (id, name, source_type, connection_config, is_active, created_by)
        VALUES (:id, 'bulk-retry', 'rest_api', '{}', true, (SELECT id FROM users LIMIT 1))
    """), {"id": str(source_id)})
    await db_session.commit()

    for i in range(3):
        db_session.add(SyncFailure(
            source_id=source_id,
            source_path=f"/records/{i}",
            error_message="err", error_class="RuntimeError",
            status="permanently_failed",
        ))
    await db_session.commit()

    resp = await client.post(
        f"/datasources/{source_id}/sync-failures/retry-all?status=permanently_failed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 3

    # Verify DB state
    db_session.expire_all()
    count = await db_session.scalar(
        select(func.count(SyncFailure.id)).where(
            SyncFailure.source_id == source_id,
            SyncFailure.status == "retrying",
        )
    )
    assert count == 3


@pytest.mark.asyncio
async def test_dismiss_all_permanently_failed(client: AsyncClient, admin_token: str, db_session):
    """dismiss-all soft-deletes permanently_failed rows (status=dismissed, dismissed_at set)."""
    from app.models.sync_failure import SyncFailure

    source_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO data_sources (id, name, source_type, connection_config, is_active, created_by)
        VALUES (:id, 'bulk-dismiss', 'rest_api', '{}', true, (SELECT id FROM users LIMIT 1))
    """), {"id": str(source_id)})
    await db_session.commit()

    for i in range(2):
        db_session.add(SyncFailure(
            source_id=source_id,
            source_path=f"/records/{i}",
            error_message="err", error_class="RuntimeError",
            status="permanently_failed",
        ))
    await db_session.commit()

    resp = await client.post(
        f"/datasources/{source_id}/sync-failures/dismiss-all?status=permanently_failed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2

    db_session.expire_all()
    rows = (await db_session.execute(
        select(SyncFailure).where(SyncFailure.source_id == source_id)
    )).scalars().all()
    assert all(r.status == "dismissed" for r in rows)
    assert all(r.dismissed_at is not None for r in rows)


@pytest.mark.asyncio
async def test_list_sync_failures_requires_auth(client: AsyncClient):
    """GET /datasources/{id}/sync-failures without auth returns 401."""
    resp = await client.get(f"/datasources/{uuid.uuid4()}/sync-failures")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unpause_source(client: AsyncClient, admin_token: str, db_session):
    """POST /datasources/{id}/unpause resets paused state."""
    from app.models.document import DataSource

    source_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO data_sources
          (id, name, source_type, connection_config, is_active, created_by,
           sync_paused, consecutive_failure_count, sync_paused_reason)
        VALUES (:id, 'unpause-test', 'rest_api', '{}', true,
                (SELECT id FROM users LIMIT 1),
                true, 5, 'Circuit open after 5 failures')
    """), {"id": str(source_id)})
    await db_session.commit()

    resp = await client.post(
        f"/datasources/{source_id}/unpause",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["grace_period"] is True

    db_session.expire_all()
    source = await db_session.get(DataSource, source_id)
    assert source.sync_paused is False
    assert source.consecutive_failure_count == 0
    assert source.sync_paused_reason is None


@pytest.mark.asyncio
async def test_list_sync_failures_filters_by_status(client: AsyncClient, admin_token: str, db_session):
    """GET /datasources/{id}/sync-failures?status=retrying returns only retrying rows."""
    from app.models.sync_failure import SyncFailure

    source_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO data_sources (id, name, source_type, connection_config, is_active, created_by)
        VALUES (:id, 'filter-test', 'rest_api', '{}', true, (SELECT id FROM users LIMIT 1))
    """), {"id": str(source_id)})
    await db_session.commit()

    db_session.add(SyncFailure(source_id=source_id, source_path="/r/1",
                               error_message="e", error_class="IOError", status="retrying"))
    db_session.add(SyncFailure(source_id=source_id, source_path="/r/2",
                               error_message="e", error_class="IOError", status="permanently_failed"))
    await db_session.commit()

    resp = await client.get(
        f"/datasources/{source_id}/sync-failures?status=retrying",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "retrying"
