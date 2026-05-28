from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
import sys
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

from civiccore.auth.suite_session import (  # noqa: E402
    issue_suite_session_token,
    revoke_suite_session,
    validate_suite_session_token,
)


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
