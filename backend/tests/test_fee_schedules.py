import pytest
from httpx import AsyncClient


FEE_SCHEDULE_PAYLOAD = {
    "jurisdiction": "Springfield",
    "fee_type": "per_page",
    "amount": 0.25,
    "description": "Standard per-page copy fee",
    "effective_date": "2026-01-01",
}


@pytest.mark.asyncio
async def test_create_fee_schedule(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/admin/fee-schedules",
        json=FEE_SCHEDULE_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["jurisdiction"] == "Springfield"
    assert data["fee_type"] == "per_page"
    assert data["amount"] == 0.25
    assert data["description"] == "Standard per-page copy fee"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_fee_schedule_requires_admin(client: AsyncClient, staff_token: str):
    resp = await client.post(
        "/admin/fee-schedules",
        json=FEE_SCHEDULE_PAYLOAD,
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_fee_schedules(client: AsyncClient, admin_token: str):
    # Create two schedules first
    for fee_type in ("per_page", "flat"):
        await client.post(
            "/admin/fee-schedules",
            json={**FEE_SCHEDULE_PAYLOAD, "fee_type": fee_type},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    resp = await client.get(
        "/admin/fee-schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_update_fee_schedule(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/admin/fee-schedules",
        json=FEE_SCHEDULE_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    schedule_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/admin/fee-schedules/{schedule_id}",
        json={"amount": 0.50, "description": "Updated fee"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 0.50
    assert data["description"] == "Updated fee"
    # Unchanged fields preserved
    assert data["fee_type"] == "per_page"
    assert data["jurisdiction"] == "Springfield"


@pytest.mark.asyncio
async def test_delete_fee_schedule(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/admin/fee-schedules",
        json=FEE_SCHEDULE_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    schedule_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/admin/fee-schedules/{schedule_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204

    # Confirm it's gone
    list_resp = await client.get(
        "/admin/fee-schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    ids = [s["id"] for s in list_resp.json()]
    assert schedule_id not in ids
