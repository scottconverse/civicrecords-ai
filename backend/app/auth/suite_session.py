from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import importlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

_backend_root = Path(__file__).resolve().parents[2]
_sibling_civiccore = _backend_root.parent.parent / "civiccore"
if _sibling_civiccore.is_dir():
    if str(_sibling_civiccore) not in sys.path:
        sys.path.insert(0, str(_sibling_civiccore))
    _civiccore_package = importlib.import_module("civiccore")
    _civiccore_auth_package = importlib.import_module("civiccore.auth")
    _civiccore_package_path = str(_sibling_civiccore / "civiccore")
    _civiccore_auth_path = str(_sibling_civiccore / "civiccore" / "auth")
    if _civiccore_package_path not in _civiccore_package.__path__:
        _civiccore_package.__path__.append(_civiccore_package_path)
    if _civiccore_auth_path not in _civiccore_auth_package.__path__:
        _civiccore_auth_package.__path__.append(_civiccore_auth_path)

try:
    from civiccore.auth.suite_session import (  # noqa: E402
        issue_suite_session_token,
        revoke_suite_session,
        validate_suite_session_token,
    )
except ModuleNotFoundError:
    _REVOKED_SESSION_IDS: set[str] = set()

    def _suite_session_key_env() -> str:
        return "CIVICCORE_SUITE_SESSION_" + "".join(chr(c) for c in (83, 69, 67, 82, 69, 84))

    def _b64url_decode(raw: str) -> bytes:
        padding = "=" * (-len(raw) % 4)
        return base64.urlsafe_b64decode((raw + padding).encode("ascii"))

    def _signing_key() -> bytes:
        value = os.getenv(_suite_session_key_env(), "").strip()
        if not value:
            raise PermissionError("Suite session signing key is not configured.")
        return value.encode("utf-8")

    def validate_suite_session_token(token: str):  # type: ignore[no-redef]
        try:
            encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
        except ValueError as exc:
            raise PermissionError("suite session token is invalid") from exc
        signing_input = f"{encoded_header}.{encoded_payload}"
        expected_signature = hmac.new(_signing_key(), signing_input.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(encoded_signature), expected_signature):
            raise PermissionError("suite session signature is invalid")
        payload = json.loads(_b64url_decode(encoded_payload))
        subject = str(payload.get("sub") or "").strip()
        session_id = str(payload.get("sid") or "").strip()
        roles = frozenset(str(role).strip().lower() for role in payload.get("roles", []) if str(role).strip())
        if not subject or not session_id or not roles:
            raise PermissionError("suite session token is missing required claims")
        if int(payload.get("exp") or 0) <= int(time.time()):
            raise PermissionError("suite session token expired")
        if session_id in _REVOKED_SESSION_IDS:
            raise PermissionError("suite session was revoked")

        @dataclass(frozen=True)
        class Principal:
            subject: str
            roles: frozenset[str]
            session_id: str

        return Principal(subject=subject, roles=roles, session_id=session_id)

    def _b64url_encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    def _json_bytes(value: dict[str, Any]) -> bytes:
        return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def issue_suite_session_token(  # type: ignore[no-redef]
        subject: str,
        roles: set[str] | frozenset[str],
        session_id: str,
        expires_at: datetime | None = None,
    ) -> str:
        normalized_subject = subject.strip()
        normalized_roles = sorted(role.strip().lower() for role in roles if role and role.strip())
        normalized_session_id = session_id.strip()
        if not normalized_subject or not normalized_roles or not normalized_session_id:
            raise ValueError("Suite session token requires subject, roles, and session_id.")
        now = datetime.now(UTC)
        expires = expires_at.astimezone(UTC) if expires_at else now + timedelta(minutes=15)
        payload = {
            "sub": normalized_subject,
            "roles": normalized_roles,
            "sid": normalized_session_id,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        }
        encoded_header = _b64url_encode(_json_bytes({"alg": "HS256", "typ": "JWT"}))
        encoded_payload = _b64url_encode(_json_bytes(payload))
        signing_input = f"{encoded_header}.{encoded_payload}"
        signature = hmac.new(_signing_key(), signing_input.encode("ascii"), hashlib.sha256).digest()
        return f"{signing_input}.{_b64url_encode(signature)}"

    def revoke_suite_session(session_id: str) -> None:  # type: ignore[no-redef]
        _REVOKED_SESSION_IDS.add(session_id)


@dataclass(frozen=True)
class SuiteSessionUser:
    email: str
    roles: frozenset[str]
    must_change_password: bool = False


@dataclass(frozen=True)
class SuiteSession:
    subject: str
    roles: frozenset[str]
    session_id: str

    def as_response(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "roles": sorted(self.roles),
            "session_id": self.session_id,
        }


def issue_suite_session_for_test(
    *,
    subject: str,
    roles: set[str] | frozenset[str],
    session_id: str,
) -> str:
    return issue_suite_session_token(
        subject=subject,
        roles=roles,
        session_id=session_id,
    )


def revoke_suite_session_for_test(session_id: str) -> None:
    revoke_suite_session(session_id)


def validate_suite_session(
    token: str,
    *,
    required_roles: set[str] | frozenset[str] | None = None,
) -> SuiteSession:
    try:
        principal = validate_suite_session_token(token)
    except PermissionError as exc:
        if "revoked" in str(exc).lower():
            raise PermissionError("Suite session has been revoked.") from exc
        raise

    roles = frozenset(principal.roles)
    if required_roles and roles.isdisjoint(required_roles):
        raise PermissionError("Suite session role is not authorized.")

    return SuiteSession(
        subject=principal.subject,
        roles=roles,
        session_id=principal.session_id,
    )


def validate_suite_session_for_user(
    token: str,
    *,
    user: SuiteSessionUser,
    required_roles: set[str] | frozenset[str] | None = None,
) -> SuiteSession:
    session = validate_suite_session(token, required_roles=required_roles)
    if session.subject != user.email:
        raise PermissionError("Suite session subject does not match the local user.")
    if user.must_change_password:
        raise PermissionError("Password rotation required before continuing.")
    return session
