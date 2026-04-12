import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_templates_empty(client: AsyncClient, admin_token: str):
    """GET /notifications/templates returns empty list when none exist."""
    resp = await client.get(
        "/notifications/templates",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_template(client: AsyncClient, admin_token: str):
    """POST /notifications/templates creates template."""
    resp = await client.post(
        "/notifications/templates",
        json={
            "event_type": "request_received",
            "channel": "email",
            "subject_template": "Your request {{request_id}} has been received",
            "body_template": "Dear {{requester_name}}, we received your request.",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_type"] == "request_received"
    assert data["channel"] == "email"
    assert data["is_active"] is True
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_notifications_requires_auth(client: AsyncClient):
    """GET /notifications/templates returns 401 without token."""
    resp = await client.get("/notifications/templates")
    assert resp.status_code == 401
