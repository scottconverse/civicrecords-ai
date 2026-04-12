import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_timeline_empty(client: AsyncClient, admin_token: str):
    """GET /requests/{id}/timeline returns empty list for new request."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Timeline Test", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.get(
        f"/requests/{req_id}/timeline",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_add_timeline_event(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/timeline creates event and returns it."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Timeline Add", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.post(
        f"/requests/{req_id}/timeline",
        json={
            "event_type": "note",
            "description": "Initial review started",
            "internal_note": "Staff only note",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_type"] == "note"
    assert data["description"] == "Initial review started"
    assert data["internal_note"] == "Staff only note"
    assert data["request_id"] == req_id
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_timeline_requires_auth(client: AsyncClient, admin_token: str):
    """GET /requests/{id}/timeline returns 401 without token."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Auth Test", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.get(f"/requests/{req_id}/timeline")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_timeline_not_found(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/timeline returns 404 for nonexistent request."""
    resp = await client.post(
        f"/requests/{uuid.uuid4()}/timeline",
        json={"event_type": "note", "description": "Should fail"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
