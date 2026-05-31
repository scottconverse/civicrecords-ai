import pytest
import httpx
from httpx import AsyncClient

from app.config import settings
from app.requests import router as requests_router


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


@pytest.mark.asyncio
async def test_response_letter_llm_timeout_falls_back_to_template(monkeypatch):
    """Slow Ollama calls must not make response-letter generation hang."""

    class FakeTimeoutClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            assert self.timeout == settings.response_letter_llm_timeout_seconds
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.TimeoutException("cold CPU model timed out")

    class FakeRequest:
        requester_name = "Cold CPU"
        id = "REQ-CPU"
        description = "Request for budget records"

        class _DateReceived:
            @staticmethod
            def strftime(_fmt):
                return "2026-05-31"

        date_received = _DateReceived()

    monkeypatch.setattr(httpx, "AsyncClient", FakeTimeoutClient)

    assert await requests_router._try_llm_generation(FakeRequest(), []) is None
