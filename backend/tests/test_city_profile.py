import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_profile_empty(client: AsyncClient, admin_token: str):
    """GET /city-profile returns null when no profile exists."""
    resp = await client.get(
        "/city-profile",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_create_profile(client: AsyncClient, admin_token: str):
    """POST /city-profile creates and returns profile."""
    resp = await client.post(
        "/city-profile",
        json={
            "city_name": "Springfield",
            "state": "IL",
            "county": "Sangamon",
            "population_band": "100k-250k",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["city_name"] == "Springfield"
    assert data["state"] == "IL"
    assert data["county"] == "Sangamon"
    assert data["onboarding_status"] == "complete"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, admin_token: str):
    """PATCH /city-profile updates fields."""
    # Create first
    await client.post(
        "/city-profile",
        json={"city_name": "Springfield", "state": "IL"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Update
    resp = await client.patch(
        "/city-profile",
        json={"population_band": "250k-500k", "email_platform": "exchange"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["population_band"] == "250k-500k"
    assert data["email_platform"] == "exchange"
    assert data["city_name"] == "Springfield"
