import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_messages_empty(client: AsyncClient, admin_token: str):
    """GET /requests/{id}/messages returns empty list for new request."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Msg Test", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.get(
        f"/requests/{req_id}/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_add_message(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/messages creates a message."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Msg Add", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.post(
        f"/requests/{req_id}/messages",
        json={"message_text": "Hello, we need more info.", "is_internal": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["message_text"] == "Hello, we need more info."
    assert data["is_internal"] is False
    assert data["sender_type"] == "staff"
    assert data["request_id"] == req_id


@pytest.mark.asyncio
async def test_internal_message(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/messages with is_internal=true creates internal message."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Internal Msg", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.post(
        f"/requests/{req_id}/messages",
        json={"message_text": "Staff-only discussion note.", "is_internal": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_internal"] is True
    assert data["message_text"] == "Staff-only discussion note."


@pytest.mark.asyncio
async def test_messages_requires_auth(client: AsyncClient, admin_token: str):
    """GET /requests/{id}/messages returns 401 without token."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Auth Msg", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.get(f"/requests/{req_id}/messages")
    assert resp.status_code == 401
