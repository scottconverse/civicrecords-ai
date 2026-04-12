import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_fees_empty(client: AsyncClient, admin_token: str):
    """GET /requests/{id}/fees returns empty list for new request."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Fee Test", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.get(
        f"/requests/{req_id}/fees",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_add_fee(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/fees creates fee line item with correct total."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Fee Add", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.post(
        f"/requests/{req_id}/fees",
        json={"description": "Copy fee", "quantity": 10, "unit_price": 0.25},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Copy fee"
    assert data["quantity"] == 10
    assert data["unit_price"] == 0.25
    assert data["total"] == 2.50
    assert data["request_id"] == req_id


@pytest.mark.asyncio
async def test_fees_requires_auth(client: AsyncClient, admin_token: str):
    """GET /requests/{id}/fees returns 401 without token."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Fee Auth", "description": "Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.get(f"/requests/{req_id}/fees")
    assert resp.status_code == 401
