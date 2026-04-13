"""Tests for user edit and deactivate (Item 3 — Staff Workbench Debt Sprint)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_user_full_name(client: AsyncClient, admin_token: str):
    """PATCH /admin/users/{id} updates full_name."""
    # Create a user to edit
    create_resp = await client.post(
        "/admin/users",
        json={"email": "edit-test@city.gov", "password": "Test1234!", "full_name": "Original Name", "role": "staff"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Update full_name
    resp = await client.patch(
        f"/admin/users/{user_id}",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_deactivate_user(client: AsyncClient, admin_token: str):
    """PATCH /admin/users/{id} with is_active=false deactivates a user."""
    create_resp = await client.post(
        "/admin/users",
        json={"email": "deactivate-test@city.gov", "password": "Test1234!", "full_name": "Deactivate Me", "role": "staff"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/admin/users/{user_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_requires_admin(client: AsyncClient):
    """PATCH /admin/users/{id} without admin token returns 401."""
    import uuid
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/admin/users/{fake_id}",
        json={"full_name": "Should Fail"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_cannot_self_demote(client: AsyncClient, admin_token: str):
    """Admin cannot change their own role (self-demotion prevention)."""
    # Get admin's own user ID
    users_resp = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert users_resp.status_code == 200
    users = users_resp.json()
    admin_user = next(u for u in users if u["role"] == "admin")

    # Try to change own role
    resp = await client.patch(
        f"/admin/users/{admin_user['id']}",
        json={"role": "staff"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "Cannot change your own role" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_cannot_self_deactivate(client: AsyncClient, admin_token: str):
    """Admin cannot deactivate their own account."""
    users_resp = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_user = next(u for u in users_resp.json() if u["role"] == "admin")

    resp = await client.patch(
        f"/admin/users/{admin_user['id']}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "Cannot deactivate your own account" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_user_invalid_role(client: AsyncClient, admin_token: str):
    """PATCH with invalid role returns 422."""
    create_resp = await client.post(
        "/admin/users",
        json={"email": "role-test@city.gov", "password": "Test1234!", "full_name": "Role Test", "role": "staff"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/admin/users/{user_id}",
        json={"role": "superuser"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422
    assert "Invalid role" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_nonexistent_user(client: AsyncClient, admin_token: str):
    """PATCH on nonexistent user returns 404."""
    import uuid
    resp = await client.patch(
        f"/admin/users/{uuid.uuid4()}",
        json={"full_name": "Ghost"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
