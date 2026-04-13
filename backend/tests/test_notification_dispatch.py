"""Integration tests: every router-dispatched event_type must produce a NotificationLog row.

Finding 1 from 2026-04-13 audit: the router dispatches event_types that had no
matching seed template, causing queue_notification() to silently no-op.  These
tests ensure every dispatch path creates an actual notification record.
"""

import pytest

from app.notifications.service import queue_notification
from app.models.notifications import NotificationLog, NotificationTemplate


# Every event_type that the requests router dispatches.
# Source: backend/app/requests/router.py (grep for queue_notification).
ROUTER_DISPATCHED_EVENT_TYPES = [
    # From update_request (PATCH) — f"request_{data.status.value}"
    "request_searching",
    "request_in_review",
    "request_clarification_needed",
    "request_assigned",
    "request_fulfilled",
    "request_closed",
    "request_drafted",
    # From dedicated endpoints (hardcoded strings)
    "request_in_review",        # submit_for_review
    "request_ready_for_release",  # mark_ready_for_release
    "request_approved",          # approve_request
    "request_drafted",           # reject_request
]

# Deduplicated set of event_types that MUST have a seed template.
REQUIRED_EVENT_TYPES = sorted(set(ROUTER_DISPATCHED_EVENT_TYPES))


@pytest.mark.asyncio
async def test_seed_templates_cover_all_dispatched_event_types(client):
    """The seed script must define a template for every router-dispatched event_type."""
    from scripts.seed_notification_templates import NOTIFICATION_TEMPLATES

    seeded_event_types = {t["event_type"] for t in NOTIFICATION_TEMPLATES}

    missing = set(REQUIRED_EVENT_TYPES) - seeded_event_types
    assert missing == set(), (
        f"Seed script is missing templates for router-dispatched event_types: {missing}"
    )


@pytest.mark.asyncio
async def test_queue_notification_creates_log_for_each_event_type(client, admin_token: str):
    """queue_notification() must create a NotificationLog row for every dispatched event_type."""
    from tests.conftest import test_session_maker
    from scripts.seed_notification_templates import NOTIFICATION_TEMPLATES
    from app.models.user import User
    from sqlalchemy import select

    # admin_token fixture creates a user; fetch it for template attribution
    async with test_session_maker() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        assert user is not None, "Test DB must have at least one user (created by admin_token fixture)"

        for tmpl_data in NOTIFICATION_TEMPLATES:
            existing = await session.execute(
                select(NotificationTemplate).where(
                    NotificationTemplate.event_type == tmpl_data["event_type"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            template = NotificationTemplate(
                event_type=tmpl_data["event_type"],
                channel=tmpl_data["channel"],
                subject_template=tmpl_data["subject_template"],
                body_template=tmpl_data["body_template"],
                is_active=True,
                created_by=user.id,
            )
            session.add(template)
        await session.commit()

    # Now dispatch each router event_type and assert a log row is created
    failed_types = []
    async with test_session_maker() as session:
        for event_type in REQUIRED_EVENT_TYPES:
            log = await queue_notification(
                session=session,
                event_type=event_type,
                recipient_email="test@city.gov",
                context_data={
                    "request_id": "REQ-001",
                    "requester_name": "Test User",
                    "city_name": "Test City",
                },
            )
            if log is None:
                failed_types.append(event_type)
            else:
                assert isinstance(log, NotificationLog)
                assert log.status == "queued"
        await session.commit()

    assert failed_types == [], (
        f"queue_notification() returned None (no template match) for: {failed_types}"
    )


@pytest.mark.asyncio
async def test_audit_export_csv_endpoint(client, admin_token: str):
    """GET /audit/export?format=csv returns CSV with correct headers."""
    resp = await client.get(
        "/audit/export?format=csv",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    lines = resp.text.strip().split("\n")
    assert len(lines) >= 1  # At least the header row
    header = lines[0]
    assert "timestamp" in header
    assert "action" in header


@pytest.mark.asyncio
async def test_audit_export_requires_auth(client):
    """GET /audit/export without token returns 401."""
    resp = await client.get("/audit/export?format=csv")
    assert resp.status_code == 401
