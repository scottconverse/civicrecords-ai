"""Tests for fee estimation, waiver, and payment lifecycle (Item 6 — Debt Sprint)."""

import uuid

import pytest
from httpx import AsyncClient


async def _create_request(client: AsyncClient, token: str) -> str:
    """Helper to create a records request and return its ID."""
    resp = await client.post(
        "/requests/",
        json={
            "requester_name": "Fee Test User",
            "requester_email": "feetest@example.com",
            "description": "Fee lifecycle test request",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_fee_schedule(client: AsyncClient, token: str) -> str:
    """Helper to create a fee schedule and return its ID."""
    resp = await client.post(
        "/admin/fee-schedules",
        json={
            "jurisdiction": "CO",
            "fee_type": "per_page",
            "amount": 0.25,
            "description": "Standard per-page copy fee",
            "effective_date": "2026-01-01",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_fee_estimation(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/estimate-fees calculates from page_count * schedule rate."""
    req_id = await _create_request(client, admin_token)
    sched_id = await _create_fee_schedule(client, admin_token)

    resp = await client.post(
        f"/requests/{req_id}/estimate-fees",
        json={"page_count": 100, "fee_schedule_id": sched_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page_count"] == 100
    assert data["unit_price"] == 0.25
    assert data["total"] == 25.0
    assert data["fee_type"] == "per_page"


@pytest.mark.asyncio
async def test_fee_estimation_invalid_schedule(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/estimate-fees with bad schedule_id returns 404."""
    req_id = await _create_request(client, admin_token)

    resp = await client.post(
        f"/requests/{req_id}/estimate-fees",
        json={"page_count": 10, "fee_schedule_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_fee_waiver_create(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/fee-waiver creates a pending waiver."""
    req_id = await _create_request(client, admin_token)

    resp = await client.post(
        f"/requests/{req_id}/fee-waiver",
        json={"waiver_type": "indigency", "reason": "Requester is indigent and unable to pay fees."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["waiver_type"] == "indigency"
    assert data["status"] == "pending"
    assert data["request_id"] == req_id


@pytest.mark.asyncio
async def test_fee_waiver_invalid_type(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/fee-waiver with invalid type returns 422."""
    req_id = await _create_request(client, admin_token)

    resp = await client.post(
        f"/requests/{req_id}/fee-waiver",
        json={"waiver_type": "bribery", "reason": "Not a real waiver type"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_fee_waiver_approve(client: AsyncClient, admin_token: str):
    """PATCH /requests/{id}/fee-waiver/{wid} approves waiver and sets fee_status=waived."""
    req_id = await _create_request(client, admin_token)

    # Create waiver
    create_resp = await client.post(
        f"/requests/{req_id}/fee-waiver",
        json={"waiver_type": "public_interest", "reason": "Public interest override."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    waiver_id = create_resp.json()["id"]

    # Approve it
    resp = await client.patch(
        f"/requests/{req_id}/fee-waiver/{waiver_id}",
        json={"status": "approved", "review_notes": "Approved per policy 4.2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["review_notes"] == "Approved per policy 4.2"
