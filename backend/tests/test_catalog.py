import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_domains(client: AsyncClient, admin_token: str):
    """GET /catalog/domains returns domain list."""
    resp = await client.get(
        "/catalog/domains",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "domains" in data
    assert isinstance(data["domains"], list)


@pytest.mark.asyncio
async def test_list_systems(client: AsyncClient, admin_token: str):
    """GET /catalog/systems returns systems list."""
    resp = await client.get(
        "/catalog/systems",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "systems" in data
    assert isinstance(data["systems"], list)
