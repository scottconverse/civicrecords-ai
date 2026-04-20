"""Tests for backend.app.config startup validation (T2C bootstrap hardening).

Covers:
- FIRST_ADMIN_PASSWORD validator (placeholder, blocklist, length, valid)
- The fresh-start integration scenario: a user copies .env.example to .env
  without editing FIRST_ADMIN_PASSWORD — Settings() must fail fatally so the
  app cannot boot. This mirrors what `docker compose up` would experience.
- CONNECTOR_HOST_ALLOWLIST CSV parsing
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


_VALID_JWT = "a" * 64
_VALID_PASSWORD = "S3cure!FreshAdminPwd-2026"


# ─────────────────── FIRST_ADMIN_PASSWORD validation ───────────────────
@pytest.mark.parametrize(
    "bad_password",
    [
        # Exact placeholder from .env.example — the fresh-start scenario
        "CHANGE-ME-on-first-login",
        # Default Settings value
        "CHANGE-ME",
        # Common-blocklist entries
        "password",
        "Password",
        "admin",
        "admin123",
        "changeme",
        "12345678",
        "letmein",
        "Welcome1",
    ],
)
def test_placeholder_or_blocklist_password_fails_startup(bad_password):
    with pytest.raises((ValidationError, ValueError), match="FIRST_ADMIN_PASSWORD"):
        Settings(
            jwt_secret=_VALID_JWT,
            first_admin_password=bad_password,
            testing=False,
        )


@pytest.mark.parametrize("short_pw", ["", "a", "short", "12345", "elevenchars"])
def test_short_password_fails_startup(short_pw):
    with pytest.raises((ValidationError, ValueError), match="FIRST_ADMIN_PASSWORD"):
        Settings(
            jwt_secret=_VALID_JWT,
            first_admin_password=short_pw,
            testing=False,
        )


def test_valid_strong_password_passes():
    s = Settings(
        jwt_secret=_VALID_JWT,
        first_admin_password=_VALID_PASSWORD,
        testing=False,
    )
    assert s.first_admin_password == _VALID_PASSWORD


def test_testing_mode_bypasses_password_check():
    # The testing=True path is how the test suite skips both validators
    s = Settings(
        jwt_secret="too-short",
        first_admin_password="CHANGE-ME",
        testing=True,
    )
    assert s.testing is True


# ───────── Fresh-start integration scenario (placeholder → fatal) ─────────
def test_fresh_start_with_env_example_placeholder_fails_fatally():
    """The exact bootstrap-failure path the T2C plan requires.

    A user copies `.env.example` to `.env` without editing FIRST_ADMIN_PASSWORD.
    Settings() loads, the validator runs, and it raises — which is what
    `docker compose up` experiences when the app tries to start.
    """
    with pytest.raises((ValidationError, ValueError), match="FIRST_ADMIN_PASSWORD"):
        Settings(
            jwt_secret=_VALID_JWT,
            first_admin_password="CHANGE-ME-on-first-login",
            testing=False,
        )


# ─────────────────── CONNECTOR_HOST_ALLOWLIST parsing ───────────────────
def test_allowlist_default_is_empty():
    s = Settings(
        jwt_secret=_VALID_JWT,
        first_admin_password=_VALID_PASSWORD,
        testing=False,
    )
    assert s.connector_host_allowlist == []


def test_allowlist_accepts_native_list():
    s = Settings(
        jwt_secret=_VALID_JWT,
        first_admin_password=_VALID_PASSWORD,
        connector_host_allowlist=["10.0.0.5", "internal-api.corp"],
        testing=False,
    )
    assert s.connector_host_allowlist == ["10.0.0.5", "internal-api.corp"]


def test_allowlist_accepts_csv_string():
    # Operators can set via env: CONNECTOR_HOST_ALLOWLIST=10.0.0.5,internal-api.corp
    s = Settings(
        jwt_secret=_VALID_JWT,
        first_admin_password=_VALID_PASSWORD,
        connector_host_allowlist="10.0.0.5,internal-api.corp,db.corp",
        testing=False,
    )
    assert s.connector_host_allowlist == ["10.0.0.5", "internal-api.corp", "db.corp"]


def test_allowlist_csv_strips_whitespace_and_empties():
    s = Settings(
        jwt_secret=_VALID_JWT,
        first_admin_password=_VALID_PASSWORD,
        connector_host_allowlist=" 10.0.0.5 , , internal-api.corp ,",
        testing=False,
    )
    assert s.connector_host_allowlist == ["10.0.0.5", "internal-api.corp"]
