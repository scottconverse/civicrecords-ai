import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_operational_metrics(client: AsyncClient, admin_token: str):
    """GET /analytics/operational returns metrics with expected shape."""
    resp = await client.get(
        "/analytics/operational",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "requests_by_status" in data
    assert "total_open" in data
    assert "total_closed" in data
    assert "total_overdue" in data
    assert "deadline_compliance_rate" in data
    assert "clarification_frequency" in data
    assert "top_request_topics" in data
    assert isinstance(data["requests_by_status"], dict)


@pytest.mark.asyncio
async def test_analytics_requires_auth(client: AsyncClient):
    """GET /analytics/operational returns 401 without token."""
    resp = await client.get("/analytics/operational")
    assert resp.status_code == 401
