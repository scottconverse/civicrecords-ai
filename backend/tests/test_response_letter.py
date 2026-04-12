import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_generate_response_letter(client: AsyncClient, admin_token: str):
    """POST /requests/{id}/response-letter generates a draft letter."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Letter Test", "description": "Request for budget records"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]
    resp = await client.post(
        f"/requests/{req_id}/response-letter",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["request_id"] == req_id
    assert data["status"] == "draft"
    assert data["generated_content"] is not None
    assert len(data["generated_content"]) > 0
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_get_response_letter(client: AsyncClient, admin_token: str):
    """GET /requests/{id}/response-letter returns the latest letter."""
    create = await client.post(
        "/requests/",
        json={"requester_name": "Get Letter", "description": "Request for permits"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    req_id = create.json()["id"]

    # Generate a letter first
    await client.post(
        f"/requests/{req_id}/response-letter",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Now retrieve it
    resp = await client.get(
        f"/requests/{req_id}/response-letter",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == req_id
    assert data["status"] == "draft"
    assert "generated_content" in data
