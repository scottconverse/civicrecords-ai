"""Tests for onboarding LLM-guided interview (Item 7 — Debt Sprint).

The interview endpoint generates questions — it does NOT update the profile.
Profile updates happen via the frontend calling PATCH /city-profile.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_interview_returns_next_question(client: AsyncClient, admin_token: str):
    """POST /onboarding/interview returns a question and target field."""
    with patch("app.onboarding.router.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Welcome! What's the name of your city?"

        resp = await client.post(
            "/onboarding/interview",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "question" in data
        assert data["target_field"] is not None
        assert data["all_complete"] is False
        assert isinstance(data["completed_fields"], list)


@pytest.mark.asyncio
async def test_interview_skips_completed_fields(client: AsyncClient, admin_token: str):
    """Interview skips fields that already have values in the profile."""
    # Create a city profile with city_name filled
    await client.post(
        "/city-profile",
        json={"city_name": "Springfield", "state": "CO"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    with patch("app.onboarding.router.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "What county is Springfield in?"

        resp = await client.post(
            "/onboarding/interview",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # city_name and state should be in completed_fields
        assert "city_name" in data["completed_fields"]
        assert "state" in data["completed_fields"]
        # target_field should NOT be city_name or state (already filled)
        assert data["target_field"] not in ("city_name", "state")


@pytest.mark.asyncio
async def test_interview_requires_admin(client: AsyncClient):
    """POST /onboarding/interview without admin auth returns 401."""
    resp = await client.post("/onboarding/interview", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_interview_falls_back_on_llm_failure(client: AsyncClient, admin_token: str):
    """Interview returns default question when LLM fails."""
    with patch("app.onboarding.router.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = RuntimeError("Ollama unavailable")

        resp = await client.post(
            "/onboarding/interview",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should still return a question (the default fallback)
        assert len(data["question"]) > 0
        assert data["target_field"] is not None
