from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "docker-compose.yml").is_file():
            return candidate
    raise AssertionError("Could not locate repository root with docker-compose.yml")


REPO_ROOT = _repo_root()


def test_compose_uses_secret_file_pointers_instead_of_secret_env_values():
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "JWT_SECRET_FILE=/run/secrets/jwt_secret" in env_example
    assert "FIRST_ADMIN_PASSWORD_FILE=/run/secrets/first_admin_password" in env_example
    assert "JWT_SECRET=" not in env_example
    assert "FIRST_ADMIN_PASSWORD=" not in env_example
    assert "secrets:" in compose
    assert "file: ${CIVICRECORDS_SECRET_DIR:-./data/secrets}/jwt_secret" in compose
    assert "file: ${CIVICRECORDS_SECRET_DIR:-./data/secrets}/first_admin_password" in compose


def test_release_gate_checks_container_env_does_not_expose_b2_secrets():
    verifier = (REPO_ROOT / "scripts" / "verify-release.sh").read_text(encoding="utf-8")

    assert "docker compose exec -T api env" in verifier
    assert "JWT_SECRET|FIRST_ADMIN_PASSWORD" in verifier
    assert "api container env hides JWT_SECRET and FIRST_ADMIN_PASSWORD" in verifier
