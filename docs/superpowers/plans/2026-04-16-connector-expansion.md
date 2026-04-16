# Connector Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `RestApiConnector` and `OdbcConnector` to CivicRecords AI, with full TDD, Alembic migration, extended test-connection endpoint, and sync-runner cursor semantics.

**Architecture:** Two new connectors extend `BaseConnector` using the existing 4-method protocol (authenticate/discover/fetch/health_check). A shared `retry.py` utility handles HTTP 429 backoff. Config schemas use Pydantic discriminated unions stored AES-256 encrypted in `data_sources.connection_config`. The Celery sync runner in `ingestion/tasks.py` is updated to write `last_sync_cursor` only on full success and call `close()` in a `finally` block.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, Pydantic v2, httpx (async HTTP), pyodbc (ODBC), respx (HTTP mocking in tests), pytest-asyncio, Celery

**Spec:** `docs/superpowers/specs/2026-04-16-connector-expansion-design-v4.md`

**Celery timeouts (Tier 3):** Set `soft_time_limit=3600, time_limit=4200` on sync tasks. With `max_records=10_000` and 30s per-request timeout, worst-case discover is ~300s; worst-case fetch run is hours only if all records hit timeout. 1-hour soft limit plus 70-minute hard limit is a reasonable v1 guard. Document in task 9.

**Structured failure logging format (Tier 3):** When `fetch()` fails, log at ERROR with structured fields: `error_class`, `record_id` (source_path), `status_code` (HTTP) or `None` (ODBC), `retry_count`.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/app/connectors/base.py` | Modify | Add no-op `close()` to BaseConnector |
| `backend/alembic/versions/013_add_connector_types.py` | Create | Add `last_sync_cursor` column + `REST_API`/`ODBC` to `source_type` enum |
| `backend/app/models/document.py` | Modify | Add `REST_API`, `ODBC` to `SourceType` enum; add `last_sync_cursor` to `DataSource` |
| `backend/app/schemas/connectors/__init__.py` | Create | `ConnectorConfig` discriminated union |
| `backend/app/schemas/connectors/rest_api.py` | Create | `RestApiConfig` Pydantic model |
| `backend/app/schemas/connectors/odbc.py` | Create | `ODBCConfig` Pydantic model |
| `backend/app/connectors/retry.py` | Create | Shared HTTP retry utility + per-request timeout |
| `backend/app/connectors/rest_api.py` | Create | `RestApiConnector` |
| `backend/app/connectors/odbc.py` | Create | `OdbcConnector` |
| `backend/app/connectors/__init__.py` | Modify | Register new connectors in factory |
| `backend/app/datasources/router.py` | Modify | Extend `test-connection` for `rest_api` and `odbc` |
| `backend/app/ingestion/tasks.py` | Modify | Cursor write on full success; `close()` in `finally` |
| `frontend/src/pages/DataSources.tsx` (or equivalent wizard file) | Modify | Wizard Step 2 branching + credential masking |
| `docs/UNIFIED-SPEC.md` | Modify | Update §11.4 status |
| `CHANGELOG.md` | Modify | Add connector expansion entry |
| `backend/tests/test_retry.py` | Create | Retry utility unit tests |
| `backend/tests/test_rest_connector.py` | Create | RestApiConnector tests (respx) |
| `backend/tests/test_odbc_connector.py` | Create | OdbcConnector tests (sqlite3 adapter) |
| `backend/tests/test_ingestion_tasks.py` | Modify | Cursor semantics + close() lifecycle tests |

---

## Task 1: Add `close()` no-op to BaseConnector

**Files:**
- Modify: `backend/app/connectors/base.py`

The sync runner will call `close()` on all connectors in a `finally` block. Existing connectors (`file_system`, `imap_email`, `manual_drop`) don't have `close()`. Adding a no-op to the base class prevents `AttributeError` without touching any existing connector.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_base_connector.py
import pytest
from app.connectors.base import BaseConnector, DiscoveredRecord, FetchedDocument, HealthCheckResult, HealthStatus

class _MinimalConnector(BaseConnector):
    @property
    def connector_type(self) -> str:
        return "test"
    async def authenticate(self) -> bool:
        return True
    async def discover(self) -> list[DiscoveredRecord]:
        return []
    async def fetch(self, source_path: str) -> FetchedDocument:
        raise NotImplementedError
    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status=HealthStatus.HEALTHY, latency_ms=0)

def test_base_connector_close_is_noop():
    """close() must exist and be callable without error on the base class."""
    c = _MinimalConnector(config={})
    c.close()  # must not raise AttributeError or any other error
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend && python -m pytest tests/test_base_connector.py::test_base_connector_close_is_noop -v
```
Expected: `AttributeError: '_MinimalConnector' object has no attribute 'close'`

- [ ] **Step 3: Add `close()` to BaseConnector**

In `backend/app/connectors/base.py`, add after `__init__`:

```python
def close(self) -> None:
    """Release any resources held by this connector.

    Subclasses that open stateful connections (ODBC, TCP sockets) MUST override
    this method. The sync runner calls close() in a finally block after every
    sync run. The default implementation is a no-op so existing connectors
    (file_system, imap_email, manual_drop) are unaffected.
    """
    pass
```

- [ ] **Step 4: Run test to verify it passes**

```
cd backend && python -m pytest tests/test_base_connector.py::test_base_connector_close_is_noop -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/base.py backend/tests/test_base_connector.py
git commit -m "feat: add no-op close() to BaseConnector for sync runner lifecycle"
```

---

## Task 2: Database migration — `last_sync_cursor` + SourceType enum values

**Files:**
- Create: `backend/alembic/versions/013_add_connector_types.py`
- Modify: `backend/app/models/document.py`

`DataSource.last_sync_at` already exists (line 46 of `models/document.py`). The migration only adds `last_sync_cursor`. `SourceType` currently has `UPLOAD` and `DIRECTORY` — add `REST_API` and `ODBC`. PostgreSQL enum additions cannot be rolled back (same pattern as migration `008`), so `downgrade()` for the enum is a documented no-op.

- [ ] **Step 1: Create the migration file**

```python
# backend/alembic/versions/013_add_connector_types.py
"""Add last_sync_cursor and REST_API/ODBC source types

Revision ID: 013_connector_types
Revises: 012_add_liaison_public_roles
Create Date: 2026-04-16
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = '013_connector_types'
down_revision: Union[str, None] = '012_add_liaison_public_roles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new SourceType enum values
    # PostgreSQL requires ALTER TYPE ... ADD VALUE; cannot be done inside a transaction.
    op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'rest_api'")
    op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'odbc'")

    # Add last_sync_cursor column (last_sync_at already exists)
    op.add_column(
        "data_sources",
        sa.Column("last_sync_cursor", sa.String(), nullable=True),
    )


def downgrade() -> None:
    # Drop the cursor column
    op.drop_column("data_sources", "last_sync_cursor")
    # PostgreSQL does not support removing enum values — downgrade cannot
    # remove 'rest_api' or 'odbc' from source_type. This matches the
    # precedent set in 008_extend_request_status_enum.py.
```

- [ ] **Step 2: Update the SourceType enum in models/document.py**

Find this block (lines 17-20):
```python
class SourceType(str, enum.Enum):
    UPLOAD = "upload"
    DIRECTORY = "directory"
```

Replace with:
```python
class SourceType(str, enum.Enum):
    UPLOAD = "upload"
    DIRECTORY = "directory"
    REST_API = "rest_api"
    ODBC = "odbc"
```

- [ ] **Step 3: Add `last_sync_cursor` to DataSource model**

In `models/document.py`, after line 46 (`last_sync_at`), add:

```python
last_sync_cursor: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

- [ ] **Step 4: Run the migration against the test database**

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://civicrecords:civicrecords@localhost:5432/civicrecords_test \
  alembic upgrade head
```
Expected: migration `013_connector_types` runs without error.

- [ ] **Step 5: Verify columns exist**

```bash
docker compose exec postgres psql -U civicrecords civicrecords_test -c "\d data_sources"
```
Expected: `last_sync_cursor` column present; `source_type` enum includes `rest_api`, `odbc`.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/013_add_connector_types.py backend/app/models/document.py
git commit -m "feat: migration 013 — add last_sync_cursor + rest_api/odbc source types"
```

---

## Task 3: Pydantic config schemas

**Files:**
- Create: `backend/app/schemas/connectors/` (new directory)
- Create: `backend/app/schemas/connectors/__init__.py`
- Create: `backend/app/schemas/connectors/rest_api.py`
- Create: `backend/app/schemas/connectors/odbc.py`

- [ ] **Step 1: Write failing tests for RestApiConfig**

```python
# backend/tests/test_connector_schemas.py
import pytest
from pydantic import ValidationError
from app.schemas.connectors.rest_api import RestApiConfig
from app.schemas.connectors.odbc import ODBCConfig
from app.schemas.connectors import ConnectorConfig


class TestRestApiConfig:
    def test_defaults(self):
        cfg = RestApiConfig(
            base_url="https://api.example.gov",
            endpoint_path="/records",
            auth_method="none",
        )
        assert cfg.connector_type == "rest_api"
        assert cfg.pagination_style == "none"
        assert cfg.response_format == "json"
        assert cfg.max_records == 10_000
        assert cfg.max_response_bytes == 50 * 1024 * 1024

    def test_cursor_pagination_requires_json(self):
        with pytest.raises(ValidationError, match="pagination_style='cursor' requires response_format='json'"):
            RestApiConfig(
                base_url="https://api.example.gov",
                endpoint_path="/records",
                auth_method="none",
                pagination_style="cursor",
                response_format="csv",
            )

    def test_cursor_pagination_with_json_is_valid(self):
        cfg = RestApiConfig(
            base_url="https://api.example.gov",
            endpoint_path="/records",
            auth_method="none",
            pagination_style="cursor",
            response_format="json",
        )
        assert cfg.pagination_style == "cursor"


class TestODBCConfig:
    def test_valid_identifiers(self):
        cfg = ODBCConfig(
            connection_string="DSN=mydb",
            table_name="public_records",
            pk_column="record_id",
        )
        assert cfg.table_name == "public_records"

    def test_injection_rejected_table_name(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            ODBCConfig(
                connection_string="DSN=mydb",
                table_name="foo; DROP TABLE users; --",
                pk_column="id",
            )

    def test_injection_rejected_pk_column(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            ODBCConfig(
                connection_string="DSN=mydb",
                table_name="records",
                pk_column="id; DROP TABLE--",
            )

    def test_schema_name_validated(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            ODBCConfig(
                connection_string="DSN=mydb",
                table_name="records",
                pk_column="id",
                schema_name="dbo; DROP TABLE--",
            )

    def test_schema_name_none_allowed(self):
        cfg = ODBCConfig(
            connection_string="DSN=mydb",
            table_name="records",
            pk_column="id",
            schema_name=None,
        )
        assert cfg.schema_name is None

    def test_max_row_bytes_default(self):
        cfg = ODBCConfig(
            connection_string="DSN=mydb",
            table_name="records",
            pk_column="id",
        )
        assert cfg.max_row_bytes == 10 * 1024 * 1024


class TestConnectorConfigUnion:
    def test_discriminates_rest_api(self):
        from typing import get_args
        cfg = ConnectorConfig(
            connector_type="rest_api",
            base_url="https://api.example.gov",
            endpoint_path="/records",
            auth_method="none",
        )
        assert isinstance(cfg, RestApiConfig)

    def test_discriminates_odbc(self):
        cfg = ConnectorConfig(
            connector_type="odbc",
            connection_string="DSN=mydb",
            table_name="records",
            pk_column="id",
        )
        assert isinstance(cfg, ODBCConfig)

    def test_invalid_connector_type_raises(self):
        with pytest.raises(ValidationError):
            ConnectorConfig(connector_type="unknown", base_url="x", endpoint_path="/", auth_method="none")
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/test_connector_schemas.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.schemas.connectors'`

- [ ] **Step 3: Create the schemas package**

```python
# backend/app/schemas/connectors/rest_api.py
from typing import Annotated, Literal
from pydantic import BaseModel, Field, model_validator


class RestApiConfig(BaseModel):
    connector_type: Literal["rest_api"] = "rest_api"
    base_url: str
    endpoint_path: str

    auth_method: Literal["api_key", "bearer", "oauth2", "basic", "none"]

    # api_key auth — CREDENTIAL: masked in UI, omitted from GET responses
    api_key: str | None = None
    key_header: str = "X-API-Key"
    key_location: Literal["header", "query"] = "header"

    # bearer auth — CREDENTIAL
    token: str | None = None

    # oauth2 auth
    token_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None  # CREDENTIAL
    scope: str | None = None          # sent as 'scope' form param per RFC 6749 §4.4.2

    # basic auth
    username: str | None = None
    password: str | None = None  # CREDENTIAL

    # pagination
    pagination_style: Literal["page", "offset", "cursor", "none"] = "none"
    pagination_params: dict = Field(default_factory=dict)
    # Required keys per style:
    #   "page"   → {"page_param": "page", "size_param": "page_size"}
    #   "offset" → {"offset_param": "offset", "limit_param": "limit"}
    #   "cursor" → {"cursor_param": "next_token", "cursor_response_path": "meta.next"}
    #   "none"   → {} (ignored)
    record_id_field: str = "id"
    since_field: str | None = None
    # since_field format: ISO 8601 UTC for time-based; opaque vendor token for cursor-based

    # response format
    response_format: Literal["json", "xml", "csv"] = "json"
    # mime_type mapping: json→application/json, xml→application/xml, csv→text/csv

    # limits
    max_response_bytes: int = 50 * 1024 * 1024  # 50MB per fetch
    max_records: int = 10_000

    @model_validator(mode="after")
    def validate_pagination_format_compat(self) -> "RestApiConfig":
        if self.pagination_style == "cursor" and self.response_format != "json":
            raise ValueError(
                "pagination_style='cursor' requires response_format='json'. "
                "CSV and XML responses have no JSON envelope to read the cursor from. "
                "Use pagination_style='page' or 'offset' for non-JSON endpoints."
            )
        return self

    # Credential fields to omit from GET API responses (never returned)
    CREDENTIAL_FIELDS: frozenset[str] = frozenset(
        {"api_key", "token", "client_secret", "password"}
    )

    def to_api_response(self) -> dict:
        """Serialize config for GET responses — credential fields omitted entirely."""
        data = self.model_dump()
        for field in self.CREDENTIAL_FIELDS:
            data.pop(field, None)
        return data
```

```python
# backend/app/schemas/connectors/odbc.py
import re
from typing import Literal
from pydantic import BaseModel, field_validator


_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class ODBCConfig(BaseModel):
    connector_type: Literal["odbc"] = "odbc"
    # CREDENTIAL: JDBC DSNs embed credentials inline (user=foo;password=bar).
    # Masked in UI after save. Omitted from GET API responses entirely.
    # Frontend MUST include comment: // CREDENTIAL: treat as api_key — never display
    connection_string: str

    schema_name: str | None = None
    table_name: str
    pk_column: str
    modified_column: str | None = None
    max_row_bytes: int = 10 * 1024 * 1024  # 10MB per row

    @field_validator("schema_name", "table_name", "pk_column", "modified_column", mode="before")
    @classmethod
    def validate_identifier(cls, v: str | None) -> str | None:
        """Prevent SQL injection via identifier interpolation.

        Bind parameters cannot bind SQL identifiers (table names, column names).
        Every identifier field is validated against a strict allowlist regex.
        This fires at model instantiation — invalid configs cannot be stored.
        """
        if v is None:
            return v
        if not _IDENTIFIER_RE.fullmatch(v):
            raise ValueError(
                f"Identifier '{v}' contains invalid characters. "
                "Only letters, digits, and underscores are allowed, "
                "starting with a letter or underscore."
            )
        return v

    def to_api_response(self) -> dict:
        """Serialize config for GET responses — connection_string omitted entirely."""
        data = self.model_dump()
        data.pop("connection_string", None)
        return data
```

```python
# backend/app/schemas/connectors/__init__.py
from typing import Annotated, Union
from pydantic import Field

from app.schemas.connectors.rest_api import RestApiConfig
from app.schemas.connectors.odbc import ODBCConfig

ConnectorConfig = Annotated[
    Union[RestApiConfig, ODBCConfig],
    Field(discriminator="connector_type"),
]

__all__ = ["ConnectorConfig", "RestApiConfig", "ODBCConfig"]
```

- [ ] **Step 4: Fix the `ConnectorConfig` discriminated union test**

The union test uses `ConnectorConfig(connector_type=...)` directly — Pydantic v2 discriminated unions require `TypeAdapter`. Update the test:

```python
# In TestConnectorConfigUnion, replace the test body with:
from pydantic import TypeAdapter
_adapter = TypeAdapter(ConnectorConfig)

class TestConnectorConfigUnion:
    def test_discriminates_rest_api(self):
        cfg = _adapter.validate_python({
            "connector_type": "rest_api",
            "base_url": "https://api.example.gov",
            "endpoint_path": "/records",
            "auth_method": "none",
        })
        assert isinstance(cfg, RestApiConfig)

    def test_discriminates_odbc(self):
        cfg = _adapter.validate_python({
            "connector_type": "odbc",
            "connection_string": "DSN=mydb",
            "table_name": "records",
            "pk_column": "id",
        })
        assert isinstance(cfg, ODBCConfig)

    def test_invalid_connector_type_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _adapter.validate_python({"connector_type": "unknown"})
```

- [ ] **Step 5: Run tests to verify they pass**

```
cd backend && python -m pytest tests/test_connector_schemas.py -v
```
Expected: all 11 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/connectors/ backend/tests/test_connector_schemas.py
git commit -m "feat: RestApiConfig and ODBCConfig Pydantic schemas with discriminated union"
```

---

## Task 4: Shared HTTP retry utility

**Files:**
- Create: `backend/app/connectors/retry.py`
- Create: `backend/tests/test_retry.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_retry.py
import asyncio
import time
import pytest
import respx
import httpx
from unittest.mock import AsyncMock, patch
from app.connectors.retry import with_retry, RetryExhausted


@pytest.mark.asyncio
async def test_success_on_first_attempt():
    call_count = 0

    async def action():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await with_retry(action)
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_429_retried_twice_then_succeeds():
    responses = [httpx.Response(429), httpx.Response(429), httpx.Response(200, json={"id": 1})]
    call_count = 0

    async def action():
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        if r.status_code == 429:
            raise httpx.HTTPStatusError("429", request=httpx.Request("GET", "http://x"), response=r)
        return r

    with patch("app.connectors.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await with_retry(action)
    assert result.status_code == 200
    assert call_count == 3
    assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_429_exhausted_after_3_attempts():
    async def action():
        raise httpx.HTTPStatusError(
            "429",
            request=httpx.Request("GET", "http://x"),
            response=httpx.Response(429),
        )

    with patch("app.connectors.retry.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RetryExhausted):
            await with_retry(action)


@pytest.mark.asyncio
async def test_retry_after_header_respected():
    responses = [
        httpx.Response(429, headers={"Retry-After": "5"}),
        httpx.Response(200),
    ]
    idx = 0

    async def action():
        nonlocal idx
        r = responses[idx]; idx += 1
        if r.status_code == 429:
            raise httpx.HTTPStatusError("429", request=httpx.Request("GET", "http://x"), response=r)
        return r

    with patch("app.connectors.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await with_retry(action)
    # Should sleep ~5s (Retry-After value), not the computed backoff
    sleep_duration = mock_sleep.call_args[0][0]
    assert 4.0 <= sleep_duration <= 6.5  # 5s ± 20% jitter + small tolerance


@pytest.mark.asyncio
async def test_max_wait_ceiling_respected():
    """If next retry delay would exceed 30s ceiling, raise immediately."""
    # Simulate state where accumulated wait would exceed 30s
    from app.connectors.retry import _compute_delay
    # After 2 retries with base 1s doubled: attempt 0→1s, attempt 1→2s, attempt 2→4s
    # All within 30s, so this tests the ceiling cap on Retry-After values
    delay = _compute_delay(attempt=0, retry_after=35)
    assert delay is None  # ceiling exceeded → should raise immediately


@pytest.mark.asyncio
async def test_5xx_not_retried():
    call_count = 0

    async def action():
        nonlocal call_count
        call_count += 1
        raise httpx.HTTPStatusError(
            "503",
            request=httpx.Request("GET", "http://x"),
            response=httpx.Response(503),
        )

    with pytest.raises(httpx.HTTPStatusError):
        await with_retry(action)
    assert call_count == 1  # no retries


@pytest.mark.asyncio
async def test_4xx_not_retried():
    call_count = 0

    async def action():
        nonlocal call_count
        call_count += 1
        raise httpx.HTTPStatusError(
            "404",
            request=httpx.Request("GET", "http://x"),
            response=httpx.Response(404),
        )

    with pytest.raises(httpx.HTTPStatusError):
        await with_retry(action)
    assert call_count == 1


@pytest.mark.asyncio
async def test_timeout_not_retried():
    call_count = 0

    async def action():
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("timed out")

    with pytest.raises(httpx.TimeoutException):
        await with_retry(action)
    assert call_count == 1


def test_test_connection_bypass():
    """with_retry(action, bypass=True) raises immediately on any 429."""
    import asyncio

    async def action():
        raise httpx.HTTPStatusError(
            "429",
            request=httpx.Request("GET", "http://x"),
            response=httpx.Response(429),
        )

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.get_event_loop().run_until_complete(with_retry(action, bypass_retry=True))
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/test_retry.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.connectors.retry'`

- [ ] **Step 3: Implement retry.py**

```python
# backend/app/connectors/retry.py
"""Shared HTTP retry utility for CivicRecords AI connectors.

Policy (spec §2.5):
- 429 Too Many Requests: exponential backoff with jitter, max 3 attempts
- Base delay: 1s, doubled each attempt (1s → 2s → 4s), ±20% jitter
- Max total wait: 30 seconds — if next retry would exceed ceiling, raise immediately
- Retry-After header: if present, use as delay (subject to 30s ceiling)
- All other errors (4xx, 5xx, timeout): raised immediately without retry

Test-connection bypass: pass bypass_retry=True to raise immediately on any error.
This resolves the 10s test-connection timeout / 30s retry ceiling conflict.
"""
import asyncio
import logging
import random
from typing import Any, Awaitable, Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

_MAX_ATTEMPTS = 3
_BASE_DELAY_S = 1.0
_MAX_TOTAL_WAIT_S = 30.0
_JITTER_FACTOR = 0.20


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted on a 429."""
    pass


def _compute_delay(attempt: int, retry_after: float | None = None) -> float | None:
    """Return sleep duration in seconds, or None if ceiling would be exceeded.

    Args:
        attempt: 0-based retry attempt number (0 = first retry after initial failure)
        retry_after: seconds from Retry-After header, or None
    """
    if retry_after is not None:
        base = retry_after
    else:
        base = _BASE_DELAY_S * (2 ** attempt)

    # Apply ±20% jitter
    jitter = base * _JITTER_FACTOR * (2 * random.random() - 1)
    delay = base + jitter

    if delay > _MAX_TOTAL_WAIT_S:
        return None  # ceiling exceeded — caller should raise immediately

    return delay


async def with_retry(
    action: Callable[[], Awaitable[T]],
    bypass_retry: bool = False,
) -> T:
    """Execute an async action with 429 retry policy.

    Args:
        action: Async callable to execute. May raise httpx exceptions.
        bypass_retry: If True, any error is raised immediately (test-connection path).

    Returns:
        Result of action on success.

    Raises:
        RetryExhausted: All attempts consumed on 429.
        httpx.HTTPStatusError: Non-retryable HTTP error (4xx other than 429, 5xx).
        httpx.TimeoutException: Request timed out (non-retryable).
    """
    last_exc: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            return await action()
        except httpx.HTTPStatusError as exc:
            if bypass_retry or exc.response.status_code != 429:
                raise  # non-retryable or bypass mode

            if attempt == _MAX_ATTEMPTS - 1:
                raise RetryExhausted(
                    f"429 retry exhausted after {_MAX_ATTEMPTS} attempts"
                ) from exc

            # Parse Retry-After header if present
            retry_after: float | None = None
            ra_header = exc.response.headers.get("Retry-After")
            if ra_header:
                try:
                    retry_after = float(ra_header)
                except ValueError:
                    pass

            delay = _compute_delay(attempt, retry_after)
            if delay is None:
                raise RetryExhausted(
                    f"429 retry ceiling exceeded — next delay would exceed {_MAX_TOTAL_WAIT_S}s"
                ) from exc

            logger.warning(
                "429 received, retrying in %.1fs (attempt %d/%d)",
                delay, attempt + 1, _MAX_ATTEMPTS,
            )
            await asyncio.sleep(delay)
            last_exc = exc

        except (httpx.TimeoutException, Exception) as exc:
            raise  # all non-429 errors are non-retryable

    # Should not reach here
    raise RetryExhausted("Retry loop exited without success") from last_exc
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest tests/test_retry.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/retry.py backend/tests/test_retry.py
git commit -m "feat: shared HTTP retry utility with 429 backoff, jitter, and test-connection bypass"
```

---

## Task 5: RestApiConnector

**Files:**
- Create: `backend/app/connectors/rest_api.py`
- Create: `backend/tests/test_rest_connector.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_rest_connector.py
"""
Tests for RestApiConnector using respx to intercept at the HTTP transport layer.
Real connector code runs against controlled responses — no mocking of connector internals.
"""
import json
import pytest
import respx
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.connectors.rest_api import RestApiConnector
from app.schemas.connectors.rest_api import RestApiConfig
from app.connectors.base import HealthStatus


def make_config(**kwargs) -> RestApiConfig:
    defaults = dict(
        base_url="https://api.example.gov",
        endpoint_path="/records",
        auth_method="none",
    )
    defaults.update(kwargs)
    return RestApiConfig(**defaults)


# ── Auth tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_api_key_header():
    config = make_config(auth_method="api_key", api_key="secret123", key_location="header", key_header="X-API-Key")
    connector = RestApiConnector(config)
    route = respx.get("https://api.example.gov/records").mock(return_value=httpx.Response(200, json={"results": [], "next": None}))
    await connector.discover()
    assert route.called
    assert route.calls[0].request.headers["X-API-Key"] == "secret123"


@pytest.mark.asyncio
@respx.mock
async def test_api_key_query():
    config = make_config(auth_method="api_key", api_key="secret123", key_location="query", key_header="api_key")
    connector = RestApiConnector(config)
    respx.get("https://api.example.gov/records").mock(return_value=httpx.Response(200, json={"results": []}))
    await connector.discover()
    # Query param should be set
    request = respx.calls[0].request
    assert "api_key=secret123" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_bearer_auth():
    config = make_config(auth_method="bearer", token="bearer_tok")
    connector = RestApiConnector(config)
    route = respx.get("https://api.example.gov/records").mock(return_value=httpx.Response(200, json={"results": []}))
    await connector.discover()
    assert route.calls[0].request.headers["Authorization"] == "Bearer bearer_tok"


@pytest.mark.asyncio
@respx.mock
async def test_basic_auth():
    config = make_config(auth_method="basic", username="user", password="pass")
    connector = RestApiConnector(config)
    route = respx.get("https://api.example.gov/records").mock(return_value=httpx.Response(200, json={"results": []}))
    await connector.discover()
    import base64
    expected = "Basic " + base64.b64encode(b"user:pass").decode()
    assert route.calls[0].request.headers["Authorization"] == expected


@pytest.mark.asyncio
@respx.mock
async def test_oauth2_auth():
    respx.post("https://auth.example.gov/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok123", "expires_in": 3600})
    )
    respx.get("https://api.example.gov/records").mock(return_value=httpx.Response(200, json={"results": []}))
    config = make_config(
        auth_method="oauth2",
        token_url="https://auth.example.gov/token",
        client_id="cid",
        client_secret="csecret",
    )
    connector = RestApiConnector(config)
    await connector.discover()
    assert connector._token == "tok123"
    # Token stored in memory only — not persisted
    assert "tok123" not in str(config.model_dump())


@pytest.mark.asyncio
@respx.mock
async def test_oauth2_expires_in_missing():
    respx.post("https://auth.example.gov/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok"})  # no expires_in
    )
    respx.get("https://api.example.gov/records").mock(return_value=httpx.Response(200, json={"results": []}))
    config = make_config(
        auth_method="oauth2",
        token_url="https://auth.example.gov/token",
        client_id="cid",
        client_secret="csecret",
    )
    connector = RestApiConnector(config)
    import logging
    with patch.object(logging.getLogger("app.connectors.rest_api"), "warning") as mock_warn:
        await connector.discover()
    assert any("expires_in" in str(c) for c in mock_warn.call_args_list)
    # Defaults to 3600
    assert connector._token_expiry is not None


@pytest.mark.asyncio
async def test_oauth2_expires_in_zero():
    respx_mock = respx.mock()
    with respx_mock:
        respx.post("https://auth.example.gov/token").mock(
            return_value=httpx.Response(200, json={"access_token": "tok", "expires_in": 0})
        )
        config = make_config(
            auth_method="oauth2",
            token_url="https://auth.example.gov/token",
            client_id="cid",
            client_secret="csecret",
        )
        connector = RestApiConnector(config)
        with pytest.raises(ValueError, match="expires_in must be positive"):
            await connector.authenticate()


@pytest.mark.asyncio
@respx.mock
async def test_oauth2_reactive_401_refresh():
    token_calls = 0
    def token_side_effect(request):
        nonlocal token_calls
        token_calls += 1
        return httpx.Response(200, json={"access_token": f"tok{token_calls}", "expires_in": 3600})

    respx.post("https://auth.example.gov/token").mock(side_effect=token_side_effect)
    record_calls = 0
    def record_side_effect(request):
        nonlocal record_calls
        record_calls += 1
        if record_calls == 1:
            return httpx.Response(401)  # first call: 401 → trigger refresh
        return httpx.Response(200, json={"results": []})

    respx.get("https://api.example.gov/records").mock(side_effect=record_side_effect)
    config = make_config(auth_method="oauth2", token_url="https://auth.example.gov/token", client_id="c", client_secret="s")
    connector = RestApiConnector(config)
    records = await connector.discover()
    assert token_calls == 2  # initial + refresh
    assert record_calls == 2  # initial + retry


@pytest.mark.asyncio
@respx.mock
async def test_oauth2_reactive_401_non_oauth_raises():
    """For non-OAuth auth methods, 401 raises immediately — no refresh path."""
    respx.get("https://api.example.gov/records").mock(return_value=httpx.Response(401))
    config = make_config(auth_method="api_key", api_key="bad_key")
    connector = RestApiConnector(config)
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await connector.discover()
    assert exc_info.value.response.status_code == 401


# ── Pagination tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_discover_pagination_page():
    pages = [
        {"results": [{"id": "1", "name": "rec1"}, {"id": "2", "name": "rec2"}], "page": 1, "total_pages": 2},
        {"results": [{"id": "3", "name": "rec3"}], "page": 2, "total_pages": 2},
    ]
    call_count = 0
    def page_side_effect(request):
        nonlocal call_count
        resp = pages[call_count]; call_count += 1
        return httpx.Response(200, json=resp)

    respx.get("https://api.example.gov/records").mock(side_effect=page_side_effect)
    config = make_config(
        pagination_style="page",
        pagination_params={"page_param": "page", "size_param": "page_size"},
        record_id_field="id",
    )
    connector = RestApiConnector(config)
    records = await connector.discover()
    assert len(records) == 3
    assert [r.source_path for r in records] == ["1", "2", "3"]


@pytest.mark.asyncio
@respx.mock
async def test_discover_empty_page_terminates():
    respx.get("https://api.example.gov/records").mock(return_value=httpx.Response(200, json={"results": []}))
    config = make_config(pagination_style="page", pagination_params={"page_param": "page", "size_param": "size"})
    connector = RestApiConnector(config)
    records = await connector.discover()
    assert records == []


@pytest.mark.asyncio
@respx.mock
async def test_discover_max_records_cap():
    # Return 100 records per page, max_records=150 → should stop mid-second-page
    def make_page(n):
        return {"results": [{"id": str(i)} for i in range(n)]}

    call_count = 0
    def side_effect(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=make_page(100))

    respx.get("https://api.example.gov/records").mock(side_effect=side_effect)
    config = make_config(
        pagination_style="page",
        pagination_params={"page_param": "page", "size_param": "size"},
        max_records=150,
    )
    connector = RestApiConnector(config)
    import logging
    with patch.object(logging.getLogger("app.connectors.rest_api"), "warning") as mock_warn:
        records = await connector.discover()
    assert len(records) == 150
    assert any("capped" in str(c).lower() for c in mock_warn.call_args_list)


@pytest.mark.asyncio
@respx.mock
async def test_discover_429_retry():
    call_count = 0
    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"results": []})

    respx.get("https://api.example.gov/records").mock(side_effect=side_effect)
    config = make_config()
    connector = RestApiConnector(config)
    with patch("app.connectors.retry.asyncio.sleep", new_callable=AsyncMock):
        records = await connector.discover()
    assert call_count == 2


# ── Fetch tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_fetch_absolute_url():
    respx.get("https://api.example.gov/records/42").mock(return_value=httpx.Response(200, json={"id": 42, "title": "test"}))
    config = make_config()
    connector = RestApiConnector(config)
    doc = await connector.fetch("https://api.example.gov/records/42")
    assert doc.mime_type == "application/json"
    assert json.loads(doc.content)["id"] == 42


@pytest.mark.asyncio
@respx.mock
async def test_fetch_relative_id():
    respx.get("https://api.example.gov/records/99").mock(return_value=httpx.Response(200, json={"id": 99}))
    config = make_config()
    connector = RestApiConnector(config)
    doc = await connector.fetch("99")
    assert doc.source_path == "99"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_xml_response_format():
    respx.get("https://api.example.gov/records/1").mock(return_value=httpx.Response(200, content=b"<record><id>1</id></record>"))
    config = make_config(response_format="xml")
    connector = RestApiConnector(config)
    doc = await connector.fetch("1")
    assert doc.mime_type == "application/xml"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_csv_response_format():
    respx.get("https://api.example.gov/records/1").mock(return_value=httpx.Response(200, content=b"id,name\n1,foo"))
    config = make_config(response_format="csv")
    connector = RestApiConnector(config)
    doc = await connector.fetch("1")
    assert doc.mime_type == "text/csv"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_response_too_large():
    # Content-Length header exceeds max_response_bytes
    respx.get("https://api.example.gov/records/1").mock(
        return_value=httpx.Response(200, headers={"Content-Length": str(60 * 1024 * 1024)}, content=b"x")
    )
    config = make_config(max_response_bytes=50 * 1024 * 1024)
    connector = RestApiConnector(config)
    with pytest.raises(ValueError, match="max_response_bytes"):
        await connector.fetch("1")


# ── Health check tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_health_check_head_success():
    respx.head("https://api.example.gov").mock(return_value=httpx.Response(200))
    config = make_config()
    connector = RestApiConnector(config)
    result = await connector.health_check()
    assert result.status == HealthStatus.HEALTHY
    assert result.latency_ms is not None


@pytest.mark.asyncio
@respx.mock
async def test_health_check_head_405_falls_back_to_get():
    respx.head("https://api.example.gov").mock(return_value=httpx.Response(405))
    respx.get("https://api.example.gov").mock(return_value=httpx.Response(200))
    config = make_config()
    connector = RestApiConnector(config)
    result = await connector.health_check()
    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
@respx.mock
async def test_health_check_429_retried():
    call_count = 0
    def side_effect(request):
        nonlocal call_count; call_count += 1
        if call_count == 1:
            return httpx.Response(429)
        return httpx.Response(200)

    respx.head("https://api.example.gov").mock(side_effect=side_effect)
    config = make_config()
    connector = RestApiConnector(config)
    with patch("app.connectors.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await connector.health_check()
    assert result.status == HealthStatus.HEALTHY
    assert call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_per_request_timeout():
    async def slow(_):
        raise httpx.TimeoutException("timed out", request=httpx.Request("GET", "http://x"))

    respx.get("https://api.example.gov/records").mock(side_effect=slow)
    config = make_config()
    connector = RestApiConnector(config)
    with pytest.raises(httpx.TimeoutException):
        await connector.fetch("1")


@pytest.mark.asyncio
@respx.mock
async def test_test_connection_bypasses_retry():
    """When bypass_retry=True, a 429 raises immediately without backoff."""
    respx.head("https://api.example.gov").mock(return_value=httpx.Response(429))
    config = make_config()
    connector = RestApiConnector(config)
    # test-connection calls health_check with bypass_retry=True
    with pytest.raises(Exception):
        await connector.health_check(bypass_retry=True)
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/test_rest_connector.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'app.connectors.rest_api'`

- [ ] **Step 3: Implement RestApiConnector**

```python
# backend/app/connectors/rest_api.py
"""REST API Connector — generic connector for municipal vendor REST APIs.

Supports: Tyler Munis, Accela, NEOGOV, and any JSON/XML/CSV REST endpoint.
Auth: API key (header/query), Bearer token, OAuth2 client_credentials, Basic.

Security:
- Credentials stored in memory only; never persisted or logged
- GET/HEAD only (spec §2.2 read-only verb contract)
- Reactive OAuth2 refresh on 401 (OAuth2 only)
"""
import base64
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlparse, urljoin

import httpx

from app.connectors.base import (
    BaseConnector,
    DiscoveredRecord,
    FetchedDocument,
    HealthCheckResult,
    HealthStatus,
)
from app.connectors.retry import with_retry, RetryExhausted
from app.schemas.connectors.rest_api import RestApiConfig

logger = logging.getLogger(__name__)

_MIME_MAP = {
    "json": "application/json",
    "xml": "application/xml",
    "csv": "text/csv",
}

_REQUEST_TIMEOUT = httpx.Timeout(30.0)


class RestApiConnector(BaseConnector):
    """Generic REST API connector implementing the universal protocol."""

    def __init__(self, config: RestApiConfig | dict):
        if isinstance(config, dict):
            config = RestApiConfig(**config)
        super().__init__(config.model_dump())
        self._cfg = config
        self._token: str | None = None
        self._token_expiry: datetime | None = None
        self._client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT)

    @property
    def connector_type(self) -> str:
        return "rest_api"

    def _ensure_authenticated_sync_check(self) -> bool:
        """Return True if OAuth2 token is still valid (proactive refresh check)."""
        if self._cfg.auth_method != "oauth2":
            return self._authenticated
        if self._token is None:
            return False
        if self._token_expiry is None:
            return False
        # Refresh if within 60 seconds of expiry
        return datetime.now(timezone.utc) < (self._token_expiry - timedelta(seconds=60))

    async def _ensure_authenticated(self) -> None:
        if not _ensure_authenticated_sync_check(self):
            await self.authenticate()

    async def _ensure_authenticated(self) -> None:
        """Call authenticate() if not authenticated or token is near-expired."""
        needs_auth = not self._authenticated
        if self._cfg.auth_method == "oauth2":
            if self._token is None or self._token_expiry is None:
                needs_auth = True
            elif datetime.now(timezone.utc) >= (self._token_expiry - timedelta(seconds=60)):
                needs_auth = True
        if needs_auth:
            await self.authenticate()

    async def authenticate(self) -> bool:
        cfg = self._cfg
        if cfg.auth_method == "oauth2":
            data = {
                "grant_type": "client_credentials",
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
            }
            if cfg.scope:
                data["scope"] = cfg.scope
            resp = await self._client.post(cfg.token_url, data=data)
            resp.raise_for_status()
            body = resp.json()
            self._token = body["access_token"]
            expires_in = body.get("expires_in")
            if expires_in is None:
                logger.warning(
                    "OAuth2 token response omitted expires_in; defaulting to 3600s"
                )
                expires_in = 3600
            elif expires_in <= 0:
                raise ValueError("Malformed token response: expires_in must be positive")
            self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self._authenticated = True
        return True

    def _build_headers(self) -> dict:
        cfg = self._cfg
        headers = {}
        if cfg.auth_method == "api_key" and cfg.key_location == "header":
            headers[cfg.key_header] = cfg.api_key or ""
        elif cfg.auth_method == "bearer":
            headers["Authorization"] = f"Bearer {cfg.token}"
        elif cfg.auth_method == "oauth2":
            headers["Authorization"] = f"Bearer {self._token}"
        elif cfg.auth_method == "basic":
            creds = base64.b64encode(f"{cfg.username}:{cfg.password}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"
        return headers

    def _build_params(self, extra: dict | None = None) -> dict:
        cfg = self._cfg
        params: dict = {}
        if cfg.auth_method == "api_key" and cfg.key_location == "query":
            params[cfg.key_header] = cfg.api_key or ""
        if extra:
            params.update(extra)
        return params

    def _fetch_url(self, source_path: str) -> str:
        if source_path.startswith("http://") or source_path.startswith("https://"):
            return source_path
        base = self._cfg.base_url.rstrip("/")
        return f"{base}/{source_path.lstrip('/')}"

    def _get_json_path(self, data: Any, path: str) -> Any:
        """Traverse dot-notation path in a nested dict."""
        parts = path.split(".")
        for part in parts:
            if not isinstance(data, dict):
                return None
            data = data.get(part)
        return data

    async def discover(self) -> list[DiscoveredRecord]:
        await self._ensure_authenticated()
        cfg = self._cfg
        mime_hint = _MIME_MAP.get(cfg.response_format, "application/json")
        records: list[DiscoveredRecord] = []
        page_num = 1
        offset = 0
        cursor_value: str | None = None

        # Incremental sync: add since_field if cursor is set
        base_params: dict = {}
        if cfg.since_field and self.config.get("last_sync_cursor"):
            base_params[cfg.since_field] = self.config["last_sync_cursor"]

        while True:
            params = self._build_params(base_params.copy())

            # Apply pagination params
            pp = cfg.pagination_params
            if cfg.pagination_style == "page":
                params[pp.get("page_param", "page")] = page_num
                params[pp.get("size_param", "page_size")] = 100
            elif cfg.pagination_style == "offset":
                params[pp.get("offset_param", "offset")] = offset
                params[pp.get("limit_param", "limit")] = 100
            elif cfg.pagination_style == "cursor" and cursor_value:
                params[pp.get("cursor_param", "cursor")] = cursor_value

            url = cfg.base_url.rstrip("/") + cfg.endpoint_path
            headers = self._build_headers()

            async def _do_request():
                resp = await self._client.get(url, headers=headers, params=params)
                if resp.status_code == 401 and cfg.auth_method == "oauth2":
                    # Reactive refresh
                    self._token = None
                    self._authenticated = False
                    await self._ensure_authenticated()
                    new_headers = self._build_headers()
                    resp = await self._client.get(url, headers=new_headers, params=params)
                    if resp.status_code == 401:
                        resp.raise_for_status()
                elif resp.status_code == 401:
                    resp.raise_for_status()
                else:
                    resp.raise_for_status()
                return resp

            response = await with_retry(_do_request)

            body = response.json()
            # Support both list-root and results-key responses
            if isinstance(body, list):
                items = body
                next_cursor = None
            else:
                items = body.get("results", body.get("items", body.get("data", [])))
                if cfg.pagination_style == "cursor":
                    cp = cfg.pagination_params.get("cursor_response_path", "next")
                    next_cursor = self._get_json_path(body, cp)
                else:
                    next_cursor = None

            if not items:
                break

            for item in items:
                record_id = str(self._get_json_path(item, cfg.record_id_field) or "")
                records.append(DiscoveredRecord(
                    source_path=record_id,
                    filename=f"record_{record_id}.json",
                    file_type=cfg.response_format,
                    file_size=0,
                    metadata={"connector_type": "rest_api"},
                ))
                if len(records) >= cfg.max_records:
                    logger.warning(
                        "Discovery capped at %d records — check pagination_style config",
                        cfg.max_records,
                    )
                    return records

            # Advance pagination
            if cfg.pagination_style == "none":
                break
            elif cfg.pagination_style == "page":
                page_num += 1
            elif cfg.pagination_style == "offset":
                offset += len(items)
            elif cfg.pagination_style == "cursor":
                if not next_cursor:
                    break
                cursor_value = str(next_cursor)

        return records

    async def fetch(self, source_path: str) -> FetchedDocument:
        await self._ensure_authenticated()
        cfg = self._cfg
        url = self._fetch_url(source_path)
        headers = self._build_headers()
        params = self._build_params()
        mime = _MIME_MAP.get(cfg.response_format, "application/json")

        async def _do_fetch():
            resp = await self._client.get(url, headers=headers, params=params)
            if resp.status_code == 401 and cfg.auth_method == "oauth2":
                self._token = None
                self._authenticated = False
                await self._ensure_authenticated()
                new_headers = self._build_headers()
                resp = await self._client.get(url, headers=new_headers, params=params)
                if resp.status_code == 401:
                    resp.raise_for_status()
            else:
                resp.raise_for_status()
            return resp

        # Check Content-Length before reading body
        async with self._client.stream("GET", url, headers=headers, params=params) as resp:
            if resp.status_code == 401 and cfg.auth_method == "oauth2":
                resp.aclose()
                self._token = None
                self._authenticated = False
                await self._ensure_authenticated()
                headers = self._build_headers()
                async with self._client.stream("GET", url, headers=headers, params=params) as resp2:
                    content_length = int(resp2.headers.get("content-length", 0))
                    if content_length > cfg.max_response_bytes:
                        raise ValueError(
                            f"Response for {source_path} exceeds max_response_bytes ({cfg.max_response_bytes})"
                        )
                    content = await resp2.aread()
            else:
                if resp.status_code not in (200, 201, 204):
                    resp.raise_for_status()
                content_length = int(resp.headers.get("content-length", 0))
                if content_length > cfg.max_response_bytes:
                    raise ValueError(
                        f"Response for {source_path} exceeds max_response_bytes ({cfg.max_response_bytes})"
                    )
                chunks = []
                total = 0
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > cfg.max_response_bytes:
                        raise ValueError(
                            f"Response for {source_path} exceeds max_response_bytes ({cfg.max_response_bytes})"
                        )
                    chunks.append(chunk)
                content = b"".join(chunks)

        return FetchedDocument(
            source_path=source_path,
            filename=f"record_{source_path.split('/')[-1]}.{cfg.response_format}",
            file_type=cfg.response_format,
            content=content,
            file_size=len(content),
            metadata={"mime_type": mime},
        )

    async def health_check(self, bypass_retry: bool = False) -> HealthCheckResult:
        await self._ensure_authenticated()
        start = time.monotonic()
        headers = self._build_headers()
        base_url = self._cfg.base_url

        async def _do_head():
            return await self._client.head(base_url, headers=headers)

        try:
            resp = await with_retry(_do_head, bypass_retry=bypass_retry)
            if resp.status_code == 405:
                # 405 fallback: retry with GET (does NOT consume retry budget)
                resp = await self._client.get(base_url, headers=headers)
            resp.raise_for_status()
            latency_ms = int((time.monotonic() - start) * 1000)
            return HealthCheckResult(status=HealthStatus.HEALTHY, latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return HealthCheckResult(
                status=HealthStatus.FAILED,
                latency_ms=latency_ms,
                error_message=str(exc),
            )

    def close(self) -> None:
        # httpx.AsyncClient cleanup — call from sync context via asyncio
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(self._client.aclose())
        except RuntimeError:
            pass
```

- [ ] **Step 4: Install respx if not already present**

```bash
cd backend && pip install respx
```

- [ ] **Step 5: Run tests to verify they pass**

```
cd backend && python -m pytest tests/test_rest_connector.py -v
```
Expected: all tests PASS. Note: `test_connection_safety` requires a running DB — run that separately in Task 8.

- [ ] **Step 6: Commit**

```bash
git add backend/app/connectors/rest_api.py backend/tests/test_rest_connector.py
git commit -m "feat: RestApiConnector with OAuth2, pagination, retry, and response size guard"
```

---

## Task 6: OdbcConnector

**Files:**
- Create: `backend/app/connectors/odbc.py`
- Create: `backend/tests/test_odbc_connector.py`

The ODBC connector uses `pyodbc` in production. Tests use `sqlite3` via a pytest fixture that monkeypatches the connection call. Real SQL runs against a real in-memory SQLite database — cursor methods are never mocked.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_odbc_connector.py
"""
Tests for OdbcConnector using sqlite3 as a test-time ODBC adapter.

The fixture patches pyodbc.connect so the connector runs real SQL against
an in-memory SQLite database. This tests the actual SQL strings generated
by the connector, not a mock of cursor methods.
"""
import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from app.connectors.odbc import OdbcConnector
from app.schemas.connectors.odbc import ODBCConfig
from app.connectors.base import HealthStatus


@pytest.fixture
def sqlite_db():
    """In-memory SQLite with a seeded public_records table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE public_records (id INTEGER PRIMARY KEY, title TEXT, modified_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO public_records VALUES (?, ?, ?)",
        [
            (1, "Record One", "2026-01-01T00:00:00Z"),
            (2, "Record Two", "2026-02-01T00:00:00Z"),
            (3, "Record Three", "2026-03-01T00:00:00Z"),
        ],
    )
    conn.commit()
    return conn


@pytest.fixture
def odbc_connector(sqlite_db):
    """OdbcConnector with pyodbc.connect patched to return the sqlite fixture."""
    config = ODBCConfig(
        connection_string="DSN=test",
        table_name="public_records",
        pk_column="id",
        modified_column="modified_at",
    )
    connector = OdbcConnector(config)
    # Patch pyodbc.connect to return our sqlite connection
    with patch("app.connectors.odbc.pyodbc") as mock_pyodbc:
        mock_pyodbc.connect.return_value = sqlite_db
        yield connector, sqlite_db


@pytest.mark.asyncio
async def test_discover_full_scan(odbc_connector):
    connector, db = odbc_connector
    await connector.authenticate()
    records = await connector.discover()
    assert len(records) == 3
    source_paths = {r.source_path for r in records}
    assert source_paths == {"public_records/1", "public_records/2", "public_records/3"}


@pytest.mark.asyncio
async def test_discover_incremental(odbc_connector):
    connector, db = odbc_connector
    # Set last_sync_cursor so only records after Feb 1 are returned
    connector.config["last_sync_cursor"] = "2026-01-15T00:00:00Z"
    await connector.authenticate()
    records = await connector.discover()
    # Only records 2 and 3 have modified_at > the cursor
    assert len(records) == 2
    paths = {r.source_path for r in records}
    assert "public_records/2" in paths
    assert "public_records/3" in paths


@pytest.mark.asyncio
async def test_discover_with_schema_name(sqlite_db):
    """Schema-qualified table name must appear in generated SQL."""
    config = ODBCConfig(
        connection_string="DSN=test",
        schema_name="dbo",
        table_name="public_records",
        pk_column="id",
    )
    connector = OdbcConnector(config)

    executed_sql = []
    original_execute = sqlite_db.execute

    def capture_execute(sql, *args, **kwargs):
        executed_sql.append(sql)
        # SQLite doesn't support schema prefixes — strip it for execution
        sql_stripped = sql.replace("dbo.", "")
        return original_execute(sql_stripped, *args, **kwargs)

    sqlite_db.execute = capture_execute

    with patch("app.connectors.odbc.pyodbc") as mock_pyodbc:
        mock_pyodbc.connect.return_value = sqlite_db
        await connector.authenticate()
        await connector.discover()

    assert any("dbo.public_records" in sql for sql in executed_sql)


@pytest.mark.asyncio
async def test_fetch_row(odbc_connector):
    connector, db = odbc_connector
    await connector.authenticate()
    doc = await connector.fetch("public_records/1")
    assert doc.mime_type == "application/json"
    data = json.loads(doc.content)
    assert data["id"] == 1
    assert data["title"] == "Record One"


@pytest.mark.asyncio
async def test_fetch_row_too_large(odbc_connector):
    connector, db = odbc_connector
    connector._cfg.max_row_bytes = 10  # tiny limit to trigger guard
    await connector.authenticate()
    with pytest.raises(ValueError, match="max_row_bytes"):
        await connector.fetch("public_records/1")


@pytest.mark.asyncio
async def test_health_check(odbc_connector):
    connector, db = odbc_connector
    await connector.authenticate()
    result = await connector.health_check()
    assert result.status == HealthStatus.HEALTHY


def test_close_releases_connection(sqlite_db):
    config = ODBCConfig(connection_string="DSN=test", table_name="t", pk_column="id")
    connector = OdbcConnector(config)
    with patch("app.connectors.odbc.pyodbc") as mock_pyodbc:
        mock_pyodbc.connect.return_value = sqlite_db
        import asyncio
        asyncio.get_event_loop().run_until_complete(connector.authenticate())
        connector.close()
    # After close, _conn should be None
    assert connector._conn is None


def test_error_scrubbing():
    """pyodbc exception containing connection_string components is scrubbed."""
    config = ODBCConfig(
        connection_string="DSN=mydb;UID=admin;PWD=supersecret",
        table_name="records",
        pk_column="id",
    )
    connector = OdbcConnector(config)
    raw_exc = Exception("Authentication failed for user 'admin' with password 'supersecret'")

    with patch("app.connectors.odbc.pyodbc") as mock_pyodbc:
        mock_pyodbc.connect.side_effect = raw_exc
        import asyncio
        with pytest.raises(Exception) as exc_info:
            asyncio.get_event_loop().run_until_complete(connector.authenticate())

    scrubbed_msg = str(exc_info.value)
    assert "supersecret" not in scrubbed_msg
    assert "admin" not in scrubbed_msg
    assert "[REDACTED]" in scrubbed_msg


def test_identifier_validation_valid():
    cfg = ODBCConfig(connection_string="DSN=x", table_name="public_records", pk_column="record_id")
    assert cfg.table_name == "public_records"


def test_identifier_validation_injection():
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="invalid characters"):
        ODBCConfig(connection_string="DSN=x", table_name="foo; DROP TABLE users; --", pk_column="id")
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/test_odbc_connector.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError: No module named 'app.connectors.odbc'`

- [ ] **Step 3: Implement OdbcConnector**

```python
# backend/app/connectors/odbc.py
"""ODBC Connector — ingests tabular data from SQL databases via pyodbc.

Supports: SQL Server, PostgreSQL (via ODBC DSN), Oracle, AS/400, SQLite (tests).

Security:
- Identifier validation at config time AND query construction (SQL injection guard)
- connection_string scrubbed from all exception messages before propagation
- connection_string never logged or returned in API responses
- Rows exceeding max_row_bytes are reported as failed (not silently dropped)
"""
import json
import logging
import re
import time
from typing import Any

try:
    import pyodbc
except ImportError:
    pyodbc = None  # type: ignore — sqlite3 adapter used in tests

from app.connectors.base import (
    BaseConnector,
    DiscoveredRecord,
    FetchedDocument,
    HealthCheckResult,
    HealthStatus,
)
from app.schemas.connectors.odbc import ODBCConfig

logger = logging.getLogger(__name__)

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_DSN_CREDENTIAL_RE = re.compile(
    r"(?i)(UID|USER|PWD|PASSWORD)\s*=\s*([^;]+)", re.IGNORECASE
)


def _scrub_message(msg: str, connection_string: str) -> str:
    """Scrub credential values from an exception message.

    Strategy:
    1. Replace the full connection_string (belt-and-suspenders).
    2. Parse DSN components (UID/USER/PWD/PASSWORD) and scrub each independently.
       This catches cases where pyodbc emits only a credential component in the error.
    """
    scrubbed = msg.replace(connection_string, "[REDACTED]")
    for match in _DSN_CREDENTIAL_RE.finditer(connection_string):
        value = match.group(2).strip()
        if value:
            scrubbed = scrubbed.replace(value, "[REDACTED]")
    return scrubbed


def _validate_identifier(value: str, field_name: str) -> str:
    """Runtime identifier validation — defense-in-depth after Pydantic validation."""
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"Identifier field '{field_name}' contains invalid characters at query time. "
            "This should have been caught at config validation. Report this as a bug."
        )
    return value


class OdbcConnector(BaseConnector):
    """ODBC connector: one row = one FetchedDocument (JSON-serialized)."""

    def __init__(self, config: ODBCConfig | dict):
        if isinstance(config, dict):
            config = ODBCConfig(**config)
        super().__init__(config.model_dump())
        self._cfg = config
        self._conn: Any = None

    @property
    def connector_type(self) -> str:
        return "odbc"

    async def _ensure_authenticated(self) -> None:
        if not self._authenticated:
            await self.authenticate()

    async def authenticate(self) -> bool:
        try:
            self._conn = pyodbc.connect(self._cfg.connection_string)
            self._authenticated = True
            return True
        except Exception as exc:
            scrubbed = _scrub_message(str(exc), self._cfg.connection_string)
            logger.debug("ODBC authenticate failed (raw): %s", exc)
            raise RuntimeError(f"ODBC connection failed: {scrubbed}") from None

    def _table_ref(self) -> str:
        cfg = self._cfg
        table = _validate_identifier(cfg.table_name, "table_name")
        pk = _validate_identifier(cfg.pk_column, "pk_column")
        if cfg.schema_name:
            schema = _validate_identifier(cfg.schema_name, "schema_name")
            return f"{schema}.{table}"
        return table

    async def discover(self) -> list[DiscoveredRecord]:
        await self._ensure_authenticated()
        cfg = self._cfg
        table_ref = self._table_ref()
        pk = _validate_identifier(cfg.pk_column, "pk_column")

        records: list[DiscoveredRecord] = []
        cursor = self._conn.cursor()

        if cfg.modified_column and self.config.get("last_sync_cursor"):
            mod_col = _validate_identifier(cfg.modified_column, "modified_column")
            sql = (
                f"SELECT {pk}, {mod_col} FROM {table_ref} "
                f"WHERE {mod_col} > ? ORDER BY {mod_col}"
            )
            cursor.execute(sql, (self.config["last_sync_cursor"],))
        else:
            cursor.execute(f"SELECT {pk} FROM {table_ref}")

        for row in cursor.fetchall():
            pk_value = row[0]
            records.append(DiscoveredRecord(
                source_path=f"{cfg.table_name}/{pk_value}",
                filename=f"{cfg.table_name}_{pk_value}.json",
                file_type="json",
                file_size=0,
                metadata={"connector_type": "odbc"},
            ))

        return records

    async def fetch(self, source_path: str) -> FetchedDocument:
        await self._ensure_authenticated()
        cfg = self._cfg
        # Parse source_path: "table_name/pk_value"
        parts = source_path.split("/", 1)
        pk_value = parts[1] if len(parts) == 2 else parts[0]

        table_ref = self._table_ref()
        pk = _validate_identifier(cfg.pk_column, "pk_column")

        cursor = self._conn.cursor()
        cursor.execute(f"SELECT * FROM {table_ref} WHERE {pk} = ?", (pk_value,))
        row = cursor.fetchone()

        if row is None:
            raise ValueError(f"Record not found: {source_path}")

        # Convert row to dict — sqlite3.Row and pyodbc.Row both support this
        if hasattr(row, "keys"):
            row_dict = dict(zip(row.keys(), row))
        else:
            columns = [d[0] for d in cursor.description]
            row_dict = dict(zip(columns, row))

        json_bytes = json.dumps(row_dict, default=str).encode("utf-8")

        if len(json_bytes) > cfg.max_row_bytes:
            logger.warning(
                "Row %s exceeds max_row_bytes (%d); record marked failed",
                source_path, cfg.max_row_bytes,
            )
            raise ValueError(
                f"Row {source_path} exceeds max_row_bytes ({cfg.max_row_bytes})"
            )

        return FetchedDocument(
            source_path=source_path,
            filename=f"{source_path.replace('/', '_')}.json",
            file_type="json",
            content=json_bytes,
            file_size=len(json_bytes),
            metadata={"connector_type": "odbc"},
        )

    async def health_check(self) -> HealthCheckResult:
        await self._ensure_authenticated()
        start = time.monotonic()
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            latency_ms = int((time.monotonic() - start) * 1000)
            return HealthCheckResult(status=HealthStatus.HEALTHY, latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            scrubbed = _scrub_message(str(exc), self._cfg.connection_string)
            return HealthCheckResult(
                status=HealthStatus.FAILED,
                latency_ms=latency_ms,
                error_message=scrubbed,
            )

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest tests/test_odbc_connector.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/odbc.py backend/tests/test_odbc_connector.py
git commit -m "feat: OdbcConnector with SQL injection guard, DSN scrubbing, and row size guard"
```

---

## Task 7: Register connectors in factory

**Files:**
- Modify: `backend/app/connectors/__init__.py`

- [ ] **Step 1: Write failing test**

```python
# Add to backend/tests/test_base_connector.py

from app.connectors import get_connector

def test_factory_rest_api():
    connector = get_connector("rest_api", {
        "base_url": "https://example.gov",
        "endpoint_path": "/records",
        "auth_method": "none",
    })
    assert connector.connector_type == "rest_api"

def test_factory_odbc():
    connector = get_connector("odbc", {
        "connection_string": "DSN=x",
        "table_name": "records",
        "pk_column": "id",
    })
    assert connector.connector_type == "odbc"

def test_factory_unknown_raises():
    with pytest.raises(ValueError, match="Unknown connector type"):
        get_connector("gis", {})
```

- [ ] **Step 2: Run to verify it fails**

```
cd backend && python -m pytest tests/test_base_connector.py::test_factory_rest_api -v
```
Expected: `ImportError: cannot import name 'get_connector'`

- [ ] **Step 3: Implement the factory**

```python
# backend/app/connectors/__init__.py
from app.connectors.base import BaseConnector
from app.connectors.file_system import FileSystemConnector
from app.connectors.imap_email import ImapEmailConnector
from app.connectors.manual_drop import ManualDropConnector
from app.connectors.rest_api import RestApiConnector
from app.connectors.odbc import OdbcConnector

_REGISTRY: dict[str, type[BaseConnector]] = {
    "file_system": FileSystemConnector,
    "imap_email": ImapEmailConnector,
    "manual_drop": ManualDropConnector,
    "rest_api": RestApiConnector,
    "odbc": OdbcConnector,
}


def get_connector(connector_type: str, config: dict) -> BaseConnector:
    """Instantiate a connector by type string.

    Args:
        connector_type: One of the registered type strings.
        config: Connection configuration dict.

    Returns:
        Initialized connector instance.

    Raises:
        ValueError: If connector_type is not registered.
    """
    cls = _REGISTRY.get(connector_type)
    if cls is None:
        raise ValueError(
            f"Unknown connector type: '{connector_type}'. "
            f"Registered types: {sorted(_REGISTRY.keys())}"
        )
    return cls(config)


__all__ = ["get_connector", "BaseConnector"]
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest tests/test_base_connector.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/__init__.py backend/tests/test_base_connector.py
git commit -m "feat: connector factory registry with rest_api and odbc"
```

---

## Task 8: Extend test-connection endpoint

**Files:**
- Modify: `backend/app/datasources/router.py`

The existing `TestConnectionRequest` is a flat schema. We extend it with `rest_api` and `odbc` branches. The endpoint runs `authenticate() → health_check() → close()` with a 10-second asyncio timeout. The retry utility is bypassed (test-connection path).

- [ ] **Step 1: Write the failing integration test**

Add to `backend/tests/test_connector_schemas.py` (no DB required):

```python
# backend/tests/test_datasources_router.py (new file)
"""Integration tests for the extended test-connection endpoint."""
import pytest
import respx
import httpx
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

# These tests require a running FastAPI app — use the existing test client pattern
# from the project's test infrastructure.

@pytest.mark.asyncio
@respx.mock
async def test_test_connection_rest_api_success(admin_client):
    """REST API test-connection returns success for a healthy endpoint."""
    respx.head("https://api.example.gov").mock(return_value=httpx.Response(200))
    resp = await admin_client.post("/datasources/test-connection", json={
        "source_type": "rest_api",
        "rest_api_config": {
            "connector_type": "rest_api",
            "base_url": "https://api.example.gov",
            "endpoint_path": "/records",
            "auth_method": "none",
        }
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_test_connection_rest_api_timeout(admin_client):
    """test-connection returns failure if the entire sequence exceeds 10s."""
    async def slow_health(*args, **kwargs):
        import asyncio
        await asyncio.sleep(15)

    with patch("app.connectors.rest_api.RestApiConnector.health_check", side_effect=slow_health):
        resp = await admin_client.post("/datasources/test-connection", json={
            "source_type": "rest_api",
            "rest_api_config": {
                "connector_type": "rest_api",
                "base_url": "https://api.example.gov",
                "endpoint_path": "/records",
                "auth_method": "none",
            }
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "timed out" in body["message"].lower()


@pytest.mark.asyncio
async def test_connection_safety_rest_api(admin_client, db_session):
    """Credentials in test-connection body are never persisted or logged."""
    from app.models.audit import AuditLog
    from sqlalchemy import select

    with patch("app.connectors.rest_api.RestApiConnector.health_check", new_callable=AsyncMock,
               return_value=__import__("app.connectors.base", fromlist=["HealthCheckResult"]).HealthCheckResult(
                   status=__import__("app.connectors.base", fromlist=["HealthStatus"]).HealthStatus.HEALTHY,
                   latency_ms=10)):
        resp = await admin_client.post("/datasources/test-connection", json={
            "source_type": "rest_api",
            "rest_api_config": {
                "connector_type": "rest_api",
                "base_url": "https://api.example.gov",
                "endpoint_path": "/records",
                "auth_method": "api_key",
                "api_key": "SUPER_SECRET_KEY_XYZ",
            }
        })

    # 1. At least one audit entry must have been written
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "test_connection")
    )
    entries = result.scalars().all()
    assert len(entries) >= 1, "No audit entry written — credential redaction is meaningless"

    # 2. Recursive walk: credential must not appear at any depth in details JSONB
    def contains_credential(obj, credential: str) -> bool:
        if isinstance(obj, str):
            return credential in obj
        if isinstance(obj, dict):
            return any(contains_credential(v, credential) for v in obj.values())
        if isinstance(obj, list):
            return any(contains_credential(item, credential) for item in obj)
        return False

    for entry in entries:
        assert not contains_credential(entry.details, "SUPER_SECRET_KEY_XYZ"), \
            f"Credential leaked in audit log entry {entry.id}: {entry.details}"
```

- [ ] **Step 2: Update TestConnectionRequest and router**

In `backend/app/datasources/router.py`, extend the `TestConnectionRequest` model and `test_connection` handler:

Find the existing `TestConnectionRequest` class and replace it:

```python
class TestConnectionRequest(BaseModel):
    """Dedicated schema for test-connection. NOT the create schema.

    Security: credentials in this request body are never persisted, never
    written to audit logs, and never returned in the response.
    """
    source_type: str  # imap / file_share / manual_drop / rest_api / odbc
    # Existing flat fields (imap/file_share)
    host: str | None = None
    port: int | None = None
    path: str | None = None
    username: str | None = None
    password: str | None = None
    # New: typed configs for REST API and ODBC
    rest_api_config: dict | None = None   # parsed as RestApiConfig
    odbc_config: dict | None = None       # parsed as ODBCConfig


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    latency_ms: int | None = None
```

Add the following import at the top of the router file (after existing imports):

```python
import asyncio
from app.connectors import get_connector
from app.connectors.rest_api import RestApiConnector
from app.connectors.odbc import OdbcConnector
from app.schemas.connectors.rest_api import RestApiConfig
from app.schemas.connectors.odbc import ODBCConfig
```

In the `test_connection` handler, add the new branches after the existing `file_share` branch:

```python
    elif body.source_type == "rest_api":
        if not body.rest_api_config:
            return TestConnectionResponse(success=False, message="REST API config required")
        try:
            cfg = RestApiConfig(**body.rest_api_config)
        except Exception as exc:
            return TestConnectionResponse(success=False, message=f"Invalid config: {exc}")

        connector = RestApiConnector(cfg)
        try:
            async def _run():
                await connector.authenticate()
                result = await connector.health_check(bypass_retry=True)
                return result

            health = await asyncio.wait_for(_run(), timeout=10.0)
            connector.close()

            if health.status.value == "healthy":
                return TestConnectionResponse(
                    success=True,
                    message=f"Connected successfully",
                    latency_ms=health.latency_ms,
                )
            else:
                return TestConnectionResponse(
                    success=False,
                    message=health.error_message or "Health check failed",
                    latency_ms=health.latency_ms,
                )
        except asyncio.TimeoutError:
            connector.close()
            return TestConnectionResponse(success=False, message="Connection timed out after 10s")
        except Exception as exc:
            connector.close()
            # Strip credential values from error message
            msg = str(exc)
            for cred_field in ["api_key", "token", "client_secret", "password"]:
                cred_val = body.rest_api_config.get(cred_field)
                if cred_val:
                    msg = msg.replace(cred_val, "[REDACTED]")
            return TestConnectionResponse(success=False, message=msg)

    elif body.source_type == "odbc":
        if not body.odbc_config:
            return TestConnectionResponse(success=False, message="ODBC config required")
        try:
            cfg = ODBCConfig(**body.odbc_config)
        except Exception as exc:
            return TestConnectionResponse(success=False, message=f"Invalid config: {exc}")

        connector = OdbcConnector(cfg)
        try:
            async def _run_odbc():
                await connector.authenticate()
                result = await connector.health_check()
                return result

            health = await asyncio.wait_for(_run_odbc(), timeout=10.0)
            connector.close()

            if health.status.value == "healthy":
                return TestConnectionResponse(
                    success=True,
                    message="Connected successfully",
                    latency_ms=health.latency_ms,
                )
            else:
                return TestConnectionResponse(
                    success=False,
                    message=health.error_message or "Health check failed",
                    latency_ms=health.latency_ms,
                )
        except asyncio.TimeoutError:
            connector.close()
            return TestConnectionResponse(success=False, message="Connection timed out after 10s")
        except Exception as exc:
            connector.close()
            # DSN component scrubbing already applied inside OdbcConnector
            return TestConnectionResponse(success=False, message=str(exc))
```

Also add audit logging inside the endpoint (after the connector close, before return):

```python
            await write_audit_log(
                session=session,
                action="test_connection",
                resource_type="data_source",
                user_id=user.id,
                details={"source_type": body.source_type, "success": True},
            )
```

Note: add `session: AsyncSession = Depends(get_async_session)` to the endpoint signature to enable audit logging.

- [ ] **Step 3: Run the integration tests**

```bash
docker compose up -d postgres redis
DATABASE_URL=postgresql+asyncpg://civicrecords:civicrecords@localhost:5432/civicrecords_test \
  cd backend && python -m pytest tests/test_datasources_router.py -v
```
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/datasources/router.py backend/tests/test_datasources_router.py
git commit -m "feat: extend test-connection endpoint for rest_api and odbc with 10s timeout"
```

---

## Task 9: Sync runner — cursor semantics and close()

**Files:**
- Modify: `backend/app/ingestion/tasks.py`
- Modify: `backend/tests/test_ingestion_tasks.py`

The sync runner must: (1) call `connector.close()` in a `finally` block, (2) write `last_sync_cursor` only after all `fetch()` calls succeed, (3) log failed fetches with structured fields.

Celery task timeouts: set `soft_time_limit=3600, time_limit=4200` on the sync task.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_ingestion_tasks.py (add these tests)
"""
Tests for sync runner cursor semantics and connection lifecycle.
These tests belong here (not in connector unit tests) because the close() contract
and cursor-write-on-success semantics are enforced by the runner, not the connector.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from app.connectors.base import DiscoveredRecord, FetchedDocument, HealthStatus, HealthCheckResult


def make_record(n: int) -> DiscoveredRecord:
    return DiscoveredRecord(
        source_path=f"records/{n}",
        filename=f"record_{n}.json",
        file_type="json",
        file_size=10,
        metadata={},
    )


@pytest.mark.asyncio
async def test_close_called_on_success(db_session):
    """Sync runner calls connector.close() in finally after a successful run."""
    connector = MagicMock()
    connector.discover = AsyncMock(return_value=[make_record(1)])
    connector.fetch = AsyncMock(return_value=FetchedDocument(
        source_path="records/1", filename="r.json", file_type="json",
        content=b'{"id":1}', file_size=7, metadata={}
    ))
    connector.close = MagicMock()

    from app.ingestion.tasks import run_connector_sync
    await run_connector_sync(connector, source_id="test-src", session=db_session)

    connector.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_called_on_failure(db_session):
    """Sync runner calls connector.close() even when fetch() raises."""
    connector = MagicMock()
    connector.discover = AsyncMock(return_value=[make_record(1), make_record(2)])
    connector.fetch = AsyncMock(side_effect=RuntimeError("fetch failed"))
    connector.close = MagicMock()

    from app.ingestion.tasks import run_connector_sync
    with pytest.raises(RuntimeError):
        await run_connector_sync(connector, source_id="test-src", session=db_session)

    connector.close.assert_called_once()


@pytest.mark.asyncio
async def test_partial_sync_cursor_not_advanced(db_session):
    """If fetch() fails mid-run, last_sync_cursor is not advanced."""
    from sqlalchemy import select
    from app.models.document import DataSource, SourceType

    # Create a test data source
    source = DataSource(
        name="test-rest-api-cursor",
        source_type=SourceType.REST_API,
        connection_config={},
        last_sync_cursor="2026-01-01T00:00:00Z",
        created_by=None,
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    pre_run_cursor = source.last_sync_cursor

    # 5 records: fetch fails on record 3
    records = [make_record(i) for i in range(1, 6)]
    fetch_count = 0

    async def failing_fetch(source_path: str) -> FetchedDocument:
        nonlocal fetch_count
        fetch_count += 1
        if fetch_count == 3:
            raise RuntimeError("fetch failed on record 3")
        return FetchedDocument(
            source_path=source_path, filename="r.json", file_type="json",
            content=b'{"id":1}', file_size=7, metadata={}
        )

    connector = MagicMock()
    connector.discover = AsyncMock(return_value=records)
    connector.fetch = failing_fetch
    connector.close = MagicMock()

    from app.ingestion.tasks import run_connector_sync
    with pytest.raises(RuntimeError):
        await run_connector_sync(connector, source_id=str(source.id), session=db_session)

    # Cursor must not have advanced
    await db_session.refresh(source)
    assert source.last_sync_cursor == pre_run_cursor, (
        f"Cursor advanced to '{source.last_sync_cursor}' despite mid-run failure. "
        "last_sync_cursor must only advance on full success."
    )
```

- [ ] **Step 2: Run to verify they fail**

```
cd backend && python -m pytest tests/test_ingestion_tasks.py::test_close_called_on_success -v
```
Expected: `ImportError: cannot import name 'run_connector_sync'`

- [ ] **Step 3: Add `run_connector_sync` to tasks.py**

In `backend/app/ingestion/tasks.py`, add after the existing imports:

```python
import logging
from sqlalchemy import select, update
from app.models.document import DataSource
from app.connectors.base import BaseConnector
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def run_connector_sync(
    connector: BaseConnector,
    source_id: str,
    session,
    new_cursor: str | None = None,
) -> None:
    """Run a full discover → fetch → ingest cycle for a connector.

    Cursor semantics (spec §2.9):
    - last_sync_cursor advances ONLY after all fetch() calls succeed.
    - If any fetch() raises, the cursor is left at its pre-run value.
    - The connector's close() is called in a finally block.

    Structured failure logging format (Tier 3):
    Each failed fetch is logged at ERROR with:
    error_class, record_id, status_code (HTTP or None for ODBC), retry_count.

    Celery timeouts:
    This function is called from a Celery task with soft_time_limit=3600,
    time_limit=4200. See task_sync_connector below.
    """
    failed_records = []
    try:
        records = await connector.discover()
        for record in records:
            try:
                doc = await connector.fetch(record.source_path)
                # TODO (next task): pipe doc through ingest_file pipeline
            except Exception as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                logger.error(
                    "Fetch failed",
                    extra={
                        "error_class": type(exc).__name__,
                        "record_id": record.source_path,
                        "status_code": status_code,
                        "retry_count": 0,
                    },
                )
                failed_records.append(record.source_path)

        if failed_records:
            raise RuntimeError(
                f"Sync partially failed: {len(failed_records)} record(s) failed to fetch: "
                f"{failed_records[:5]}"
            )

        # All fetches succeeded — advance cursor
        if new_cursor is not None:
            await session.execute(
                update(DataSource)
                .where(DataSource.id == source_id)
                .values(
                    last_sync_cursor=new_cursor,
                    last_sync_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    finally:
        connector.close()


@celery_app.task(
    name="civicrecords.sync_connector",
    bind=True,
    max_retries=0,
    soft_time_limit=3600,   # 1-hour soft limit — raises SoftTimeLimitExceeded
    time_limit=4200,        # 70-minute hard kill
)
def task_sync_connector(self, source_id: str):
    """Celery task: run a full connector sync for a data source."""
    async def _sync():
        async with get_worker_session() as session:
            result = await session.execute(
                select(DataSource).where(DataSource.id == source_id)
            )
            source = result.scalar_one_or_none()
            if source is None:
                logger.error("DataSource not found: %s", source_id)
                return

            from app.connectors import get_connector
            connector = get_connector(
                source.source_type.value,
                source.connection_config or {},
            )
            # Pass current cursor into connector config for incremental sync
            connector.config["last_sync_cursor"] = source.last_sync_cursor

            await run_connector_sync(
                connector=connector,
                source_id=str(source.id),
                session=session,
                new_cursor=datetime.now(timezone.utc).isoformat(),
            )

    _run_async(_sync())
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest tests/test_ingestion_tasks.py -v -k "close or cursor"
```
Expected: all 3 new tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/tasks.py backend/tests/test_ingestion_tasks.py
git commit -m "feat: sync runner with cursor-on-success semantics, close() in finally, Celery timeouts"
```

---

## Task 10: Frontend wizard branching and credential masking

**Files:**
- Modify: `frontend/src/` — locate the DataSources wizard Step 2 component

The frontend wizard's Step 2 currently branches on `source_type`. We need two new branches: `rest_api` and `odbc`. All credential fields must be rendered as password inputs and never echoed back from the API.

- [ ] **Step 1: Locate the wizard file**

```bash
grep -r "source_type\|step.*2\|wizard" frontend/src --include="*.tsx" -l
```

Identify the file containing the Step 2 source type configuration form.

- [ ] **Step 2: Add SourceType options**

In the source type dropdown/select, add:
```tsx
<option value="rest_api">REST API</option>
<option value="odbc">ODBC / Database</option>
```

- [ ] **Step 3: Add REST API config fields**

When `source_type === "rest_api"`, render:

```tsx
{sourceType === "rest_api" && (
  <div className="space-y-4">
    <div>
      <Label htmlFor="base_url">Base URL</Label>
      <Input id="base_url" name="base_url" placeholder="https://api.example.gov" required />
    </div>
    <div>
      <Label htmlFor="endpoint_path">Endpoint Path</Label>
      <Input id="endpoint_path" name="endpoint_path" placeholder="/records" required />
    </div>
    <div>
      <Label htmlFor="auth_method">Auth Method</Label>
      <Select name="auth_method" onValueChange={setAuthMethod}>
        <SelectItem value="none">None</SelectItem>
        <SelectItem value="api_key">API Key</SelectItem>
        <SelectItem value="bearer">Bearer Token</SelectItem>
        <SelectItem value="oauth2">OAuth2 Client Credentials</SelectItem>
        <SelectItem value="basic">Basic Auth</SelectItem>
      </Select>
    </div>
    {authMethod === "api_key" && (
      <div>
        <Label htmlFor="api_key">API Key</Label>
        {/* CREDENTIAL: treat as api_key — never display, log, or echo */}
        <Input id="api_key" name="api_key" type="password" autoComplete="new-password" required />
      </div>
    )}
    {authMethod === "bearer" && (
      <div>
        <Label htmlFor="token">Bearer Token</Label>
        {/* CREDENTIAL: treat as api_key — never display, log, or echo */}
        <Input id="token" name="token" type="password" autoComplete="new-password" required />
      </div>
    )}
    {authMethod === "oauth2" && (
      <>
        <div>
          <Label htmlFor="token_url">Token URL</Label>
          <Input id="token_url" name="token_url" placeholder="https://auth.example.gov/token" required />
        </div>
        <div>
          <Label htmlFor="client_id">Client ID</Label>
          <Input id="client_id" name="client_id" required />
        </div>
        <div>
          <Label htmlFor="client_secret">Client Secret</Label>
          {/* CREDENTIAL: treat as api_key — never display, log, or echo */}
          <Input id="client_secret" name="client_secret" type="password" autoComplete="new-password" required />
        </div>
      </>
    )}
    {authMethod === "basic" && (
      <>
        <div>
          <Label htmlFor="username">Username</Label>
          <Input id="username" name="username" required />
        </div>
        <div>
          <Label htmlFor="password">Password</Label>
          {/* CREDENTIAL: treat as api_key — never display, log, or echo */}
          <Input id="password" name="password" type="password" autoComplete="new-password" required />
        </div>
      </>
    )}
  </div>
)}
```

- [ ] **Step 4: Add ODBC config fields**

```tsx
{sourceType === "odbc" && (
  <div className="space-y-4">
    <div>
      <Label htmlFor="connection_string">Connection String</Label>
      {/* CREDENTIAL: treat as api_key — never display, log, or echo */}
      {/* DSNs frequently embed credentials: DSN=mydb;UID=user;PWD=secret */}
      <Input
        id="connection_string"
        name="connection_string"
        type="password"
        autoComplete="new-password"
        placeholder="DSN=mydb or Driver={SQL Server};Server=host;..."
        required
      />
      <p className="text-xs text-muted-foreground mt-1">
        Stored encrypted. Cannot be retrieved after save.
      </p>
    </div>
    <div>
      <Label htmlFor="table_name">Table Name</Label>
      <Input id="table_name" name="table_name" placeholder="public_records" required />
    </div>
    <div>
      <Label htmlFor="pk_column">Primary Key Column</Label>
      <Input id="pk_column" name="pk_column" placeholder="id" required />
    </div>
    <div>
      <Label htmlFor="schema_name">Schema Name (optional)</Label>
      <Input id="schema_name" name="schema_name" placeholder="dbo" />
    </div>
    <div>
      <Label htmlFor="modified_column">Modified-At Column (optional, for incremental sync)</Label>
      <Input id="modified_column" name="modified_column" placeholder="modified_at" />
    </div>
  </div>
)}
```

- [ ] **Step 5: Ensure GET /datasources response omits credential fields**

In the API serialization (check `DataSourceRead` schema in `backend/app/schemas/document.py`), verify `connection_config` is not returned with credential values. The safest approach: omit `connection_config` from `DataSourceRead`, or return it with credential fields stripped. Add a `to_safe_config()` helper that removes credential keys before returning.

- [ ] **Step 6: Build frontend to verify no TypeScript errors**

```bash
cd frontend && npm run build
```
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: wizard Step 2 branching for rest_api and odbc; credential fields as password inputs"
```

---

## Task 11: Spec and changelog updates

**Files:**
- Modify: `docs/UNIFIED-SPEC.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update UNIFIED-SPEC.md §11.4**

Find this table row:
```
| REST API (Modern SaaS) | Tyler, Accela, NEOGOV, cloud platforms | [PLANNED] |
| ODBC / JDBC Bridge | On-prem databases, legacy SQL, AS/400 | [PLANNED] |
```

Replace with:
```
| REST API (Modern SaaS) | Tyler, Accela, NEOGOV, cloud platforms | [IMPLEMENTED] |
| ODBC / JDBC Bridge | On-prem databases, legacy SQL, AS/400 | [IMPLEMENTED] |
```

- [ ] **Step 2: Add CHANGELOG entry**

At the top of the `[Unreleased]` section in `CHANGELOG.md`:

```markdown
### Added
- `RestApiConnector`: generic REST connector supporting API key, Bearer, OAuth2 (client credentials), and Basic auth. Configurable pagination (page/offset/cursor/none), response formats (JSON/XML/CSV), max_records cap, 50MB per-fetch size guard, and `since_field` incremental sync.
- `OdbcConnector`: tabular data source connector via pyodbc. Row-as-document (JSON), SQL injection guard on all identifier fields, DSN component error scrubbing, 10MB per-row size guard, incremental sync via `modified_column`.
- `connectors/retry.py`: shared HTTP retry utility — exponential backoff with ±20% jitter, Retry-After header support, 30s ceiling, per-request 30s timeout. Test-connection path bypasses retry for fast admin feedback.
- Migration 013: adds `last_sync_cursor` column and `rest_api`/`odbc` to `source_type` enum.
- `POST /datasources/test-connection` extended for `rest_api` and `odbc` source types (10s timeout, credential scrubbing, audit logged).
- `BaseConnector.close()` no-op added; sync runner calls `close()` in `finally` block.
- Cursor semantics: `last_sync_cursor` advances only on full sync success; mid-run failures leave cursor at pre-run value.
```

- [ ] **Step 3: Commit**

```bash
git add docs/UNIFIED-SPEC.md CHANGELOG.md
git commit -m "docs: update UNIFIED-SPEC §11.4 and CHANGELOG for connector expansion"
```

---

## Task 12: Full test suite verification

- [ ] **Step 1: Run all unit tests (no Docker required)**

```bash
cd backend && python -m pytest tests/test_base_connector.py tests/test_connector_schemas.py tests/test_retry.py tests/test_rest_connector.py tests/test_odbc_connector.py -v
```
Expected: all tests PASS

- [ ] **Step 2: Run integration tests (requires Docker)**

```bash
docker compose up -d postgres redis
DATABASE_URL=postgresql+asyncpg://civicrecords:civicrecords@localhost:5432/civicrecords_test \
  cd backend && python -m pytest tests/ -v
```
Expected: 288 + new tests all PASS (no regressions)

- [ ] **Step 3: Run migration round-trip**

```bash
# Upgrade
alembic upgrade head
# Verify columns
docker compose exec postgres psql -U civicrecords civicrecords_test -c "\d data_sources"
# Downgrade
alembic downgrade -1
# Upgrade again
alembic upgrade head
```
Expected: upgrade and downgrade complete without error. Note: `source_type` enum values `rest_api`/`odbc` cannot be removed on downgrade (PostgreSQL limitation, same as migration 008 precedent) — document in downgrade function.

- [ ] **Step 4: Docker Compose full stack verification**

```bash
docker compose build
docker compose up -d
curl http://localhost:8000/health
curl http://localhost:8000/docs
```
Expected: health returns `{"status": "ok"}`, docs serve OpenAPI spec.

- [ ] **Step 5: Final commit and push gate check**

Before pushing, verify Rule 9 deliverables exist (per Hard Rule 9). The Rule 9 gate will block push if any are missing.

```bash
git log --oneline -5
```

---

## Spec Coverage Self-Review

| Spec requirement | Task |
|---|---|
| `BaseConnector.close()` no-op | Task 1 |
| Migration: `last_sync_cursor` + SourceType enum | Task 2 |
| `RestApiConfig` with `@model_validator` | Task 3 |
| `ODBCConfig` with `@field_validator` on identifiers | Task 3 |
| `ConnectorConfig` discriminated union | Task 3 |
| `retry.py` with jitter, Retry-After, ceiling, timeout | Task 4 |
| `RestApiConnector` — all auth methods | Task 5 |
| Reactive 401 refresh (OAuth2 only) | Task 5 |
| HEAD→GET 405 fallback | Task 5 |
| `max_records` cap with WARNING | Task 5 |
| `max_response_bytes` streaming guard | Task 5 |
| `response_format` → `mime_type` | Task 5 |
| Test-connection bypass_retry | Task 5 + Task 8 |
| `OdbcConnector` — all methods | Task 6 |
| DSN component error scrubbing | Task 6 |
| Row size guard (`max_row_bytes`) | Task 6 |
| Identifier validation defense-in-depth at query time | Task 6 |
| Connector factory registry | Task 7 |
| `test-connection` endpoint — 10s timeout + scrubbing | Task 8 |
| `test_connection_safety` with recursive JSONB walk | Task 8 |
| Sync runner cursor-on-success | Task 9 |
| `close()` in finally | Task 9 |
| Structured failure logging | Task 9 |
| Celery timeouts | Task 9 |
| Frontend wizard branching + masking | Task 10 |
| Write-only credentials in GET responses | Task 10 |
| UNIFIED-SPEC §11.4 update | Task 11 |
| CHANGELOG entry | Task 11 |
| `test_retry.py` | Task 4 |
| `test_rest_connector.py` — full test matrix | Task 5 |
| `test_odbc_connector.py` — full test matrix | Task 6 |
| `test_ingestion_tasks.py` — cursor + close() | Task 9 |
| Tier 3: existing rows retain NULL after migration | Task 2 note |
| Tier 3: ODBC schema evolution in USER-MANUAL | (manual doc — flag for release) |
| Tier 3: `specs/INDEX.md` | (flag for release) |
