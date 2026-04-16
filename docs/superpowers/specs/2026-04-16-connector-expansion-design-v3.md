# Connector Expansion Design — v3
**Date:** 2026-04-16
**Revised:** 2026-04-16
**Project:** CivicRecords AI
**Status:** Pending final approval — ready for implementation planning
**Spec ref:** UNIFIED-SPEC.md §11.4–11.5
**Supersedes:** `2026-04-16-connector-expansion-design-v2.md`

**Revision history:**
- v1 — initial design doc
- v2 — Alembic downgrade, 429 retry, response_format, recursive JSONB walk, §2.5/§2.6 renumbering, 5xx rationale, discover() mime_type hint
- v3 — Tier 1: ODBC SQL injection guard, bearer token masking, connection-string error scrubbing, test-connection endpoint spec, CSV/XML pagination restriction, OAuth2 expires_in fallback, pagination_params schema. Tier 2: read-only verb contract, close() lifecycle, discriminated union registration, XML/CSV test cases, audit-entry existence assertion, OAuth2 reactive 401 refresh, response size limit, write-only API boundary, retry on health_check, since_field format, OAuth2 scope wire format. Tier 3: plan-level notes.

---

## 1. Scope

### In this sprint
- `RestApiConnector` — generic REST connector (API key, Bearer/OAuth2, Basic auth)
- `OdbcConnector` — tabular data source via pyodbc (production) / sqlite3 adapter (tests)
- DB migration: `last_sync_cursor VARCHAR NULL` + `last_sync_at TIMESTAMPTZ NULL` on `data_sources`
- `test-connection` endpoint extended to handle `rest_api` and `odbc` source types (see §2.7)
- Frontend wizard Step 2 branching updated for new connector types
- `connectors/retry.py` — shared HTTP retry utility (§2.5)

### Out of scope (deferred)
- GIS REST API (Esri ArcGIS) — separate sprint
- Vendor SDK (Axon Evidence, CAD systems) — separate sprint
- SharePoint — use `RestApiConnector` with OAuth2 config; no custom connector needed
- Binary / multipart REST responses — v1 restricts to `json`, `xml`, `csv`; binary blobs require a future `response_format: "binary"` mode

### Plan-level notes (Tier 3 — resolved in implementation plan, not spec)
- `backend/tests/test_retry.py` must be included in the test plan
- After migration upgrade(), existing `data_sources` rows retain NULL for both new columns; existing connectors trigger a full re-sync on next run (expected, not a bug)
- Structured error logging format for failed `fetch()` calls: `error_class`, `record_id`, `status_code`, `retry_count` — specify in plan
- Celery `soft_time_limit` / `time_limit` must be set explicitly in the plan, accounting for `max_records = 10_000` worst case
- ODBC schema evolution (changing table columns) is admin-managed in v1; `SELECT *` will silently produce different JSON — document in USER-MANUAL
- A `docs/superpowers/specs/INDEX.md` pointing to the current active spec version is recommended

---

## 2. Protocol Implementation

Both connectors extend `BaseConnector` and implement the 4-method universal protocol:
`authenticate()` / `discover()` / `fetch()` / `health_check()`

### 2.1 `_ensure_authenticated()` guard

Every protocol method (`discover`, `fetch`, `health_check`) calls `_ensure_authenticated()` as its first line. This method calls `authenticate()` if `self._authenticated` is False. Callers are never required to call `authenticate()` manually before using the connector.

### 2.2 Connector contract invariants

These invariants apply to ALL connectors, present and future:

**Read-only verbs:** `discover()` and `fetch()` MUST use only GET or HEAD. POST/PUT/PATCH/DELETE are prohibited, even on "read" endpoints that require a POST body. If a vendor API requires POST to retrieve records, that is a vendor-specific adapter problem, not a connector-level solution.

**Write-only credentials at the API boundary:** `api_key`, `client_secret`, `password`, `token` (RestApiConfig) and `connection_string` (ODBCConfig) are write-only. They MUST NOT be returned in any GET API response under any circumstance — not even masked. The field is omitted entirely from serialized responses.

**Connection lifecycle:** Every connector that allocates a stateful connection in `authenticate()` (TCP socket, ODBC connection handle, etc.) MUST implement `close()` to release it. The sync runner MUST call `close()` in a `finally` block. Connectors that do not hold a stateful connection may implement `close()` as a no-op. The base class provides a default no-op `close()` so connectors only override when needed.

**No credential logging:** Credential field values must never appear in log lines at any level (DEBUG, INFO, WARNING, ERROR). The ODBC connector error-scrubbing requirement (§2.4) extends this to exception messages.

### 2.3 RestApiConnector

**`authenticate()`**
- Validates required config fields are present.
- For OAuth2: exchanges `client_id` / `client_secret` at `token_url` via POST with `grant_type=client_credentials` and `scope` (if set) as the `scope` form parameter per RFC 6749 §4.4.2. Stores access token in `self._token` (in-memory only, never persisted). Records `self._token_expiry` from the `expires_in` response field — see §2.6 for fallback behavior.
- For API key / Bearer / Basic: sets `self._authenticated = True` immediately.
- Returns `bool`.

**`discover()`**
1. Calls `_ensure_authenticated()`.
2. Builds the request URL from `base_url + endpoint_path`.
3. Appends `since_field` query parameter if `last_sync_cursor` is set. The `last_sync_cursor` value format for `since_field`-based sync is ISO 8601 UTC (e.g., `"2026-04-16T00:00:00Z"`). For `pagination_style: "cursor"`-based sync, `last_sync_cursor` stores the vendor-provided opaque next-token string.
4. Paginates according to `pagination_style` using `pagination_params` keys (see §3.1 sub-table). For `none`, fetches one page only.
5. **`max_records` guard:** regardless of `pagination_style`, stops and logs a `WARNING` when total discovered record count reaches `max_records` (default `10_000`). Log message: `"Discovery capped at {max_records} records — check pagination_style config"`.
6. For each item in each page response, emits one `DiscoveredRecord`:
   - `source_path` = value at `record_id_field` JSON path
   - `filename` = synthesized from response metadata (e.g., `"record_{id}.json"`)
   - `mime_type` = hint derived from `response_format` (`"application/json"` / `"application/xml"` / `"text/csv"`). Discovery-stage hint only; authoritative `mime_type` is set on `FetchedDocument` at fetch time.
7. After all pages consumed (or `max_records` hit), updates `data_sources.last_sync_cursor` and `last_sync_at` **only on full successful completion** (see §2.9).
8. Returns `list[DiscoveredRecord]`.

**`fetch(record: DiscoveredRecord)`**
1. Calls `_ensure_authenticated()`.
2. Constructs the fetch URL: if `source_path` is an absolute URL, uses it directly; otherwise appends to `base_url`.
3. GETs the record through the retry utility (§2.5). Response body is checked against `max_response_bytes` limit before reading (see §2.8).
4. Returns `FetchedDocument` with `content = response_body_bytes` and `mime_type` derived from `response_format`.

**`health_check()`**
1. Calls `_ensure_authenticated()`.
2. Sends `HEAD` request to `base_url` through the retry utility (§2.5) — 429s on health check are retried per policy.
3. **405 fallback:** if the response is `405 Method Not Allowed`, retries immediately with `GET` (this is a fallback for a 405, not a 429 retry — does not consume retry budget). Many municipal vendor APIs (Tyler Munis, Accela) do not implement HEAD and return 405.
4. Records latency.
5. Returns `HealthCheckResult`.

### 2.4 OdbcConnector

**Identifier validation — SQL injection guard (Tier 1)**

`{schema_name}`, `{table_name}`, `{pk_column}`, `{modified_column}` are interpolated into SQL as identifiers. Bind parameters cannot bind identifiers. An admin who enters `table_name = "foo; DROP TABLE users; --"` gets SQL execution.

**Validation rule:** Every identifier field in `ODBCConfig` is validated at model instantiation with the regex `^[A-Za-z_][A-Za-z0-9_]*$`. Schema-qualified identifiers (`schema_name.table_name`) each component is validated independently. The validator is a Pydantic `@field_validator` so validation fires on deserialization — the config cannot be stored with an invalid identifier.

Defense-in-depth: the same validation is re-applied at query construction time before any identifier is interpolated. If a value passes Pydantic validation but fails the runtime check (should not be possible, but this is defense), raise immediately and log at ERROR.

**Error-message scrubbing — connection-string leakage (Tier 1)**

`pyodbc` exceptions routinely include the DSN in the message. All exceptions raised inside the ODBC connector MUST be caught, the `connection_string` value scrubbed from the message via `str(exc).replace(self.config["connection_string"], "[REDACTED]")`, and only the scrubbed message exposed to callers, API responses, UI toasts, and log lines at INFO or WARNING. The raw exception (with credential) is retained only at DEBUG level, server-side, behind a config flag (`LOG_LEVEL=DEBUG`).

**`authenticate()`**
- Calls `pyodbc.connect(connection_string)` (or sqlite3 adapter in tests).
- Stores connection as `self._conn`.
- Returns `bool`. On failure, scrubs connection_string from exception before re-raising.

**`discover()`**
1. Calls `_ensure_authenticated()`.
2. Builds table reference: `{schema_name}.{table_name}` if `schema_name` is set, otherwise `{table_name}`. Both components validated (§2.4 identifier guard).
3. If `modified_column` is set and `last_sync_cursor` is set:
   `SELECT {pk_column}, {modified_column} FROM {table_ref} WHERE {modified_column} > ? ORDER BY {modified_column}`
   with `last_sync_cursor` as a bind parameter. The value placeholder `?` is a bound parameter — safe.
4. If `modified_column` is None or `last_sync_cursor` is None: full table scan (no WHERE clause).
5. Emits one `DiscoveredRecord` per row:
   - `source_path` = `"{table_name}/{pk_value}"`
   - `filename` = `"{table_name}_{pk_value}.json"`
   - `mime_type` = `"application/json"` (ODBC rows always serialize to JSON)
6. Updates cursor **only on full successful completion** (see §2.9).
7. Returns `list[DiscoveredRecord]`.

**`fetch(record: DiscoveredRecord)`**
1. Calls `_ensure_authenticated()`.
2. Parses `source_path` to extract table name and PK value.
3. Executes `SELECT * FROM {table_ref} WHERE {pk_column} = ?` (`?` is a bound parameter).
4. Serializes row to JSON bytes (`json.dumps(dict(row))`).
5. Returns `FetchedDocument` with `content = json_bytes`, `mime_type = "application/json"`.

**`health_check()`**
1. Calls `_ensure_authenticated()`.
2. Executes `SELECT 1`.
3. Returns `HealthCheckResult`.

**`close()`**
- Closes `self._conn` if open. Called by sync runner in a `finally` block.

### 2.5 429 retry policy

Implemented in `connectors/retry.py`. Used by all HTTP-based connectors. Must not be re-implemented per connector.

On any `429 Too Many Requests` response:
- **Max attempts:** 3 (initial + 2 retries)
- **Base delay:** 1s, doubled each attempt (1s → 2s → 4s)
- **Jitter:** ±20% random jitter on each delay
- **Max total wait:** 30 seconds — if next retry would exceed ceiling, raise immediately
- **`Retry-After` header:** if present, use its value (seconds) as delay, subject to 30s ceiling
- **Non-retriable:** 4xx other than 429 raise immediately. 5xx raise immediately — sync runs are idempotent and a transient infrastructure failure is absorbed by the next scheduled run; retrying in-process would extend the failure window without improving the outcome.

### 2.6 OAuth2 token refresh

**Proactive refresh:** `_ensure_authenticated()` checks `self._token_expiry` before returning. If expired or within 60 seconds of expiry, re-authenticates transparently.

**`expires_in` fallback:** If the token exchange response omits `expires_in`, default to `3600` seconds and log `WARNING: "OAuth2 token response omitted expires_in; defaulting to 3600s"`. If `expires_in` is zero or negative, raise `ValueError("Malformed token response: expires_in must be positive")` — do not silently default, as this indicates a misconfigured token server.

**Reactive refresh on 401:** If `discover()` or `fetch()` receives a `401 Unauthorized` response, the token may have been revoked server-side before expiry. On 401: invalidate `self._token`, set `self._authenticated = False`, call `_ensure_authenticated()` to re-authenticate, retry the request once. A second 401 on the retry raises immediately without further retry.

**Token storage:** In-memory instance variables only. Never written to the database or logs.

### 2.7 `test-connection` endpoint behavior (NEW)

The `POST /datasources/test-connection` endpoint, when extended for `rest_api` and `odbc`, runs the following sequence:

1. Instantiate the connector from the request body (credentials are NOT persisted per existing spec §11.5).
2. Call `authenticate()`.
3. Call `health_check()`.
4. Call `close()`.
5. Return `TestConnectionResponse(success=True/False, message=..., latency_ms=...)`.

**Timeout:** The entire sequence MUST complete within 10 seconds. If it does not, return `TestConnectionResponse(success=False, message="Connection timed out after 10s")`. This prevents the wizard from hanging on dead endpoints.

**Error exposure:** Error messages returned to the caller MUST NOT contain credential values. For ODBC, apply the same connection-string scrubbing as §2.4. For REST, strip `api_key`, `token`, `client_secret`, `password` from any exception message before returning.

### 2.8 Response size limit (NEW)

REST responses exceeding `max_response_bytes` (default `50 * 1024 * 1024` = 50MB) are refused at the response boundary — before the body is fully read into memory. Implementation: use `httpx`'s streaming response and check `Content-Length` header; if absent, read in chunks and abort when cumulative size exceeds the limit.

When the limit is hit: log `WARNING: "Response for {source_path} exceeds max_response_bytes ({limit}); record marked failed"` and report the record to the sync runner as failed (not silently dropped). The sync runner's failure handling applies (cursor not advanced per §2.9).

### 2.9 Cursor semantics — partial sync failure

`last_sync_cursor` and `last_sync_at` on `data_sources` advance **only after full successful completion** of a sync run.

If `fetch()` fails on any record mid-run, the cursor is **not advanced**. The next sync run starts from the same cursor position. Records may be re-processed (idempotent ingestion handles duplicates), but no records are silently skipped.

This semantics decision is enforced at the sync runner level (`ingestion/tasks.py`). The connector is stateless with respect to cursor writes.

---

## 3. Config Schemas

### 3.1 `RestApiConfig`

```python
class RestApiConfig(BaseModel):
    connector_type: Literal["rest_api"]
    base_url: str
    endpoint_path: str                          # e.g., "/api/v1/records"
    auth_method: Literal["api_key", "bearer", "oauth2", "basic", "none"]

    # api_key auth
    api_key: str | None = None                  # credential — masked in UI, omitted from GET responses
    key_header: str = "X-API-Key"
    key_location: Literal["header", "query"] = "header"

    # bearer auth
    token: str | None = None                    # credential — masked in UI, omitted from GET responses

    # oauth2 auth
    token_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None           # credential — masked in UI, omitted from GET responses
    scope: str | None = None                   # sent as 'scope' form param per RFC 6749 §4.4.2

    # basic auth
    username: str | None = None
    password: str | None = None                # credential — masked in UI, omitted from GET responses

    # pagination
    pagination_style: Literal["page", "offset", "cursor", "none"] = "none"
    pagination_params: dict = {}
    # Required keys per pagination_style:
    #   "page"   → {"page_param": "page", "size_param": "page_size"}
    #   "offset" → {"offset_param": "offset", "limit_param": "limit"}
    #   "cursor" → {"cursor_param": "next_token", "cursor_response_path": "meta.next"}
    #              (cursor_response_path is a dot-notation JSON path into the response envelope)
    #   "none"   → {} (ignored)
    # "cursor" pagination_style requires response_format == "json" (cursor value is read
    # from the JSON response envelope). Non-JSON responses may use "page" or "offset" only
    # (pagination params are query-string-only; response body is not parsed for pagination).
    record_id_field: str = "id"
    since_field: str | None = None
    # since_field value format: ISO 8601 UTC timestamp for time-based sync
    # (e.g., "2026-04-16T00:00:00Z"); opaque vendor token for cursor-based sync.

    # response format
    response_format: Literal["json", "xml", "csv"] = "json"
    # "json": mime_type = "application/json"
    # "xml":  mime_type = "application/xml"
    # "csv":  mime_type = "text/csv"
    # Binary / multipart out of scope for v1.
    # Validation: cursor pagination_style requires json (enforced by @model_validator).

    # safety cap
    max_response_bytes: int = 50 * 1024 * 1024  # 50MB
    max_records: int = 10_000

    @model_validator(mode="after")
    def validate_pagination_format_compat(self) -> "RestApiConfig":
        if self.pagination_style == "cursor" and self.response_format != "json":
            raise ValueError(
                "pagination_style='cursor' requires response_format='json'; "
                "CSV and XML responses do not have a JSON envelope to read the cursor from. "
                "Use pagination_style='page' or 'offset' for non-JSON endpoints."
            )
        return self
```

### 3.2 `ODBCConfig`

```python
class ODBCConfig(BaseModel):
    connector_type: Literal["odbc"]
    connection_string: str      # CREDENTIAL — masked in UI, omitted from GET responses, never logged
                                # JDBC DSNs frequently embed credentials inline (user=foo;password=bar).
                                # Frontend code MUST flag with comment: "# CREDENTIAL — do not display"

    schema_name: str | None = None
    table_name: str
    pk_column: str
    modified_column: str | None = None

    @field_validator("schema_name", "table_name", "pk_column", "modified_column", mode="before")
    @classmethod
    def validate_identifier(cls, v: str | None) -> str | None:
        """Prevent SQL injection via identifier interpolation.

        Bind parameters cannot bind SQL identifiers (table names, column names).
        Every identifier field is validated against a strict allowlist regex.
        """
        if v is None:
            return v
        import re
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
            raise ValueError(
                f"Identifier '{v}' contains invalid characters. "
                "Only letters, digits, and underscores are allowed, "
                "and the identifier must start with a letter or underscore."
            )
        return v
```

### 3.3 `ConnectorConfig` discriminated union

```python
# schemas/connectors/__init__.py
from typing import Annotated, Union
from pydantic import Field

ConnectorConfig = Annotated[
    Union[RestApiConfig, ODBCConfig],
    Field(discriminator="connector_type")
]
```

All router endpoints that accept connector configuration use `ConnectorConfig` as the payload type. This ensures Pydantic dispatches validation to the correct model and returns field-level errors for misconfigured connectors, rather than a generic "invalid config" error.

### 3.4 UI masking and API write-only requirement

The following fields are **write-only at the API boundary**:
- `api_key`, `token`, `client_secret`, `password` (RestApiConfig)
- `connection_string` (ODBCConfig)

**In the wizard:** displayed as `••••••••` after save. No reveal button.

**In GET API responses:** these fields are **omitted entirely** — not masked, not returned as `null`, not present in the JSON. A city IT admin must re-enter credentials to update them; they cannot be read back through the API under any circumstance.

**In frontend code:** `connection_string` MUST be marked with an inline comment: `// CREDENTIAL: treat as api_key — never display, log, or echo`.

---

## 4. Database Migration

One migration covers REST, ODBC, and future IMAP incremental sync.

`last_sync_cursor` stores an opaque string (ISO 8601 UTC for time-based sync; vendor token for cursor-based). No semantic parsing at the DB layer.

After `upgrade()`, existing `data_sources` rows have NULL for both columns. Existing connectors trigger a full re-sync on next run — expected behavior, not a bug.

### 4.1 Alembic migration (upgrade + downgrade)

```python
def upgrade() -> None:
    op.add_column("data_sources",
        sa.Column("last_sync_cursor", sa.String(), nullable=True))
    op.add_column("data_sources",
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column("data_sources", "last_sync_at")
    op.drop_column("data_sources", "last_sync_cursor")
```

---

## 5. Test Strategy

### 5.1 `test_rest_connector.py` — using `respx`

`respx` intercepts at the HTTP transport layer. Real connector code runs against controlled responses.

Required test cases:
- `test_api_key_header` — key sent in correct header
- `test_api_key_query` — key sent as query parameter
- `test_bearer_auth`
- `test_oauth2_auth` — token exchange, in-memory storage, proactive refresh on expiry
- `test_oauth2_reactive_401_refresh` — 401 mid-discover triggers one re-auth + retry; second 401 raises
- `test_oauth2_expires_in_missing` — response omits `expires_in`; defaults to 3600, logs WARNING
- `test_oauth2_expires_in_zero` — raises ValueError
- `test_basic_auth`
- `test_discover_pagination_page`
- `test_discover_pagination_cursor`
- `test_discover_pagination_offset`
- `test_discover_max_records_cap` — WARNING logged, discovery stops at `max_records`
- `test_discover_429_retry` — retries with backoff; `Retry-After` header respected
- `test_discover_empty_page_terminates`
- `test_fetch_absolute_url`
- `test_fetch_relative_id`
- `test_fetch_xml_response_format` — asserts `FetchedDocument.mime_type == "application/xml"`
- `test_fetch_csv_response_format` — asserts `FetchedDocument.mime_type == "text/csv"`
- `test_fetch_response_too_large` — response exceeds `max_response_bytes`; record reported as failed
- `test_health_check_head_success`
- `test_health_check_head_405_falls_back_to_get`
- `test_health_check_429_retried` — 429 on HEAD is retried per §2.5 policy
- `test_cursor_pagination_requires_json` — `pagination_style="cursor"` + `response_format="csv"` raises ValueError at config instantiation
- `test_connection_safety` — calls test-connection path; asserts:
  1. `len(audit_entries) >= 1` — at least one `AuditLog` entry was written (vacuous pass on empty list is a bug)
  2. `data_sources.connection_config` is byte-for-byte unchanged in DB
  3. No credential value (`api_key`, `token`, `client_secret`, `password`) appears as a substring of any string value at any depth in any `AuditLog.details` JSONB entry. The check MUST recursively walk all nested dicts, lists, and string values — a flat `.get("api_key")` check is explicitly prohibited.

### 5.2 `test_odbc_connector.py` — using sqlite3 adapter

A pytest fixture swaps `pyodbc.connect` for `sqlite3.connect`. Real SQL executes against in-memory SQLite. Mocking cursor methods is explicitly avoided.

Required test cases:
- `test_identifier_validation_valid` — valid identifiers pass
- `test_identifier_validation_injection` — `"foo; DROP TABLE"` raises ValueError at ODBCConfig instantiation
- `test_identifier_validation_schema_dot_table` — schema-qualified identifiers validated component-wise
- `test_discover_full_scan`
- `test_discover_incremental`
- `test_discover_with_schema_name` — `{schema}.{table}` in generated SQL
- `test_fetch_row` — correct JSON serialization
- `test_health_check`
- `test_close_called_on_success` — sync runner calls `close()` in finally block
- `test_close_called_on_failure` — `close()` called even when `fetch()` raises
- `test_error_scrubbing` — exception from pyodbc containing connection_string is scrubbed before propagation
- `test_connection_safety` — same as REST variant:
  1. `len(audit_entries) >= 1`
  2. `connection_config` unchanged in DB
  3. `connection_string` value does not appear at any depth in `AuditLog.details` JSONB (recursive walk, same shared helper as REST variant)

### 5.3 Cursor semantics test — `test_ingestion_tasks.py`

`test_partial_sync_cursor_not_advanced` belongs in `test_ingestion_tasks.py`, not the connector unit tests, because cursor writes happen in the sync runner.

The test must:
1. Run `discover()` — returns N records.
2. Simulate `fetch()` failure on record `N/2`.
3. Assert `data_sources.last_sync_cursor` equals the pre-run value.
4. Assert records `N/2 + 1` through `N` are not marked as ingested.

---

## 6. Wiring Checklist

- [ ] `backend/app/connectors/retry.py` — shared HTTP retry utility (§2.5)
- [ ] `backend/tests/test_retry.py` — unit tests for retry utility (backoff, jitter, Retry-After, ceiling)
- [ ] `backend/app/connectors/rest_api.py` — RestApiConnector
- [ ] `backend/app/connectors/odbc.py` — OdbcConnector (with identifier validation + error scrubbing)
- [ ] `backend/app/connectors/__init__.py` — register both types in connector factory
- [ ] `backend/app/schemas/connectors/__init__.py` — `ConnectorConfig` discriminated union (§3.3)
- [ ] `backend/app/schemas/connectors/rest_api.py` — RestApiConfig (with `@model_validator`)
- [ ] `backend/app/schemas/connectors/odbc.py` — ODBCConfig (with `@field_validator`)
- [ ] `backend/app/datasources/router.py` — extend `test-connection` per §2.7 (10s timeout, credential scrubbing)
- [ ] `backend/alembic/versions/` — migration with upgrade() + downgrade() (§4.1)
- [ ] `backend/app/ingestion/tasks.py` — cursor write only on full success; call `close()` in finally
- [ ] `frontend/` — wizard Step 2 branching; mask `token`, `api_key`, `client_secret`, `password`, `connection_string`; omit all from GET serialization; inline `# CREDENTIAL` comment on `connection_string`
- [ ] `backend/tests/test_rest_connector.py`
- [ ] `backend/tests/test_odbc_connector.py`
- [ ] `backend/tests/test_ingestion_tasks.py` — partial sync failure cursor test (§5.3)
- [ ] `docs/UNIFIED-SPEC.md` — update §11.4 REST API and ODBC/JDBC from [PLANNED] to [IMPLEMENTED]
- [ ] `CHANGELOG.md` — entry for connector expansion
