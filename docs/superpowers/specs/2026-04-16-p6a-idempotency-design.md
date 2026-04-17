# P6a — Idempotency Contract Split + data_key + UNIQUE Migration

**Date:** 2026-04-16  
**Status:** Approved for implementation  
**Ships before:** P6b, P7 (correctness fix, not a feature)  
**Severity:** Sev-2 data integrity — REST/ODBC sources currently create duplicate documents on every sync.

---

## Problem Statement

The existing idempotency contract (`(source_id, file_hash)`) works only for binary file connectors. `RestApiConnector.fetch()` hashes raw `response.content` bytes with no envelope extraction or key normalization. `OdbcConnector.fetch()` serializes with `json.dumps(..., default=str)` — no `sort_keys`, no exclusion of timestamp columns. The same logical record produces a different hash on each fetch, defeating the dedup check. The planned UNIQUE constraint on `(source_id, file_hash)` would be inert for structured sources.

---

## Decision Log

### D1: Split idempotency contract
**Decision:** Two contracts, not one.
- **Binary connectors** (file_system, imap_email, manual_drop): dedup by `(source_id, file_hash)`. Same content bytes = same document. UNIQUE constraint enforces it.
- **Structured data connectors** (rest_api, odbc): dedup by `(source_id, source_path)`. Record identity = primary key. `file_hash` = change detector only. If hash matches existing doc → skip. If hash differs → update (content changed upstream). UNIQUE constraint on `(source_id, source_path)`.

**Why:** Content-hash-for-identity works when the file IS the content. Structured records separate identity (primary key / URL) from content (fields that change). This is the standard CDC/ETL pattern (Airbyte, Fivetran, Debezium).

**Test:** `test_pipeline_idempotency.py` — linked proof.

### D2: `data_key` on RestApiConfig — optional, null means hash root object
**Decision:** Optional field (`str | None = None`). `null` = hash the entire parsed response object. Admin explicitly sets a dotted path for APIs with envelope wrappers.  
**Why optional (not required):** APIs that return the logical record at root (no envelope) don't need configuration. Forcing a value for these creates friction with no benefit. The pollution-detection warning at test-connection time (D8) catches misconfiguration before it reaches production — that's the guardrail, not mandatory field entry.  
**Why not left blank by default and forgotten:** test-connection's double-fetch pollution check is the enforcement mechanism. If hashes differ, the wizard surfaces a warning and the differing key names — admin knows exactly what to set `data_key` to. Without that check, a blank field is dangerous. With it, blank-and-stable is correct.  
**Syntax:** Dotted-path only (`"data"`, `"response.record"`, `"result.fields"`). No JSONPath — complexity trap with no marginal benefit for real municipal APIs.  
**`_extract_dotted()` contract (fully specified — see M2 below):** path not found → raise `KeyError` with descriptive message (not silently return None — ambiguous between "no envelope" and "bad path"). Value is null → treat as the record (hash null). Value is a list → each element is a separate record (see array semantics below). Path segment traverses a non-dict → raise `TypeError`.  
**Array semantics:** If `data_key` resolves to a list, each element is a separate record. `discover()` walks the list; each element's identity field (`cfg.id_field`) becomes its `source_path` segment. Document this semantics explicitly: "if `data_key` resolves to an array, each element is a record."  
**Array ordering within records:** `json.dumps(..., sort_keys=True)` sorts dict keys but preserves list order. If an upstream API returns list-valued fields in inconsistent order across fetches, hashes will differ. Decision: preserve list order as-is. Admin is responsible for stable upstream list ordering for list-valued fields. Document as Known Limitation — not a correctness bug (we can't canonicalize arbitrary nested lists without semantic knowledge of the field).  
**`envelope_excludes`:** Carve in `RestApiConfig` as `list[str] = []`. Not implemented in v1. Migration path for APIs that scatter metadata across top-level fields. Reserve, don't build.

### D3: source_path construction rules — frozen at GA
**Rules (version 1.0.0, never change without migration):**

**REST_API:**  
`source_path = f"{cfg.base_url.rstrip('/')}{cfg.endpoint_path}/{urllib.parse.quote(str(record_id), safe='')}"`  
- Absolute URL. Only the record-ID segment is URL-encoded.
- Query params excluded (pagination, not identity).
- Max 2048 chars. Enforced server-side at save and test-connection. Reject at validation with explicit error.
- Record ID extracted from each list-endpoint response element using `cfg.id_field` (see RestApiConfig).

**ODBC:**  
`source_path = f"{cfg.table_name}/{urllib.parse.quote(str(pk_value), safe='')}"`  
- `table_name` used as-is from config (admin includes schema prefix if needed, e.g., `public.contracts`).
- `pk_value` URL-percent-encoded — handles special chars including `/`.
- **Fetch decode (required, currently missing):** `OdbcConnector.fetch()` must `urllib.parse.unquote()` the PK segment extracted from `source_path` before passing to SQL parameter binding. Current code at `odbc.py:192` does `pk_value = parts[1]` and uses it directly — finds nothing for PKs containing encoded chars. Fix: `pk_value = urllib.parse.unquote(parts[1])`.
- Compound PKs: not supported in v1. **Known Gap** — document for v1.2.
- Max 2048 chars. Same enforcement.

**REST fetch decode:** `RestApiConnector.fetch()` uses `source_path` directly as the GET URL — the URL-encoded record ID is part of the path, so no decode is needed before the HTTP call. Server handles percent-decoding. No change required.

**Current bug:** Both connectors construct `source_path` without URL-encoding the variable segment. This P6a fixes ODBC construction (encode) + ODBC fetch (decode), and REST construction (encode).

### D4: Upstream identity change = new document
**Decision:** If a REST API re-keys a record (URL changes after API version bump) or an ODBC PK changes, the old `source_path` → orphaned document. New `source_path` → new document. This is correct v1 behavior — do not add fuzzy matching.  
**Document explicitly** to prevent a future dev from "fixing" it with fuzzy matching that introduces its own failure modes.

### D5: Deletion detection is a Known Gap
**Decision:** Not in scope for P6a or P7.  
If `discover()` returns fewer records than last sync, missing records are not detected.  
**Known Gap label:** `§17.x Known Gap — Deletion Detection`. Flag for v1.2.

### D6: Behavioral change — downstream update semantics
**Decision:** With source-path identity, content-changed re-fetches produce UPDATE, not INSERT.  
Any downstream logic watching `created_at` to trigger processing (e.g., notification dispatch, chunking jobs) must also watch `updated_at`.  
**Action:** Audit all existing consumers of the documents table before P6a ships.  
Current known consumers: ingestion pipeline (chunking/embedding). No external consumers identified as of 2026-04-16.

### D7: Existing structured-source data
**Decision:** As of 2026-04-16, no REST/ODBC sources are in production (pre-GA). State explicitly in migration. If any rows exist with `source_type IN ('rest_api', 'odbc')`, migration must dedupe by `MAX(ingested_at)` per `(source_id, source_path)` before adding UNIQUE constraint.

### D8: Test-time envelope-pollution detection
**Decision:** `POST /datasources/test-connection` calls `fetch()` twice (500ms apart) for REST sources, canonicalizes both with current `data_key`, compares hashes. If they differ, returns a structured warning:
```json
{
  "success": true,
  "warning": "non_deterministic_response",
  "warning_message": "Response contains non-deterministic fields. Detected hash mismatch between two fetches with current data_key. Differing top-level keys: ['fetched_at', 'request_id']. Refine data_key or use envelope_excludes.",
  "differing_keys": ["fetched_at", "request_id"]
}
```
Success is still returned (connection works), warning surfaces alongside.  
This converts a silent production bug into a test-time guardrail.

---

## Architecture

### New ingestion path: `ingest_structured_record()`

New function in `backend/app/ingestion/pipeline.py`, called by REST/ODBC sync runner only:

```
ingest_structured_record(session, source_id, source_path, content_bytes, filename, metadata)
  1. Compute file_hash = sha256(content_bytes)
  2. SELECT ... FOR UPDATE: look up Document by (source_id, source_path), lock the row.
     (Prevents concurrent workers from racing on the same record — see H5 below.)
  3. If found AND file_hash matches → return existing doc (no-op, content unchanged)
  4. If found AND file_hash differs → UPDATE semantics (see chunk/embedding lifecycle below)
  5. If not found → INSERT new doc, chunk, embed
  6. Commit (releases FOR UPDATE lock)
```

**Chunk and embedding lifecycle on UPDATE (H4):**  
When content has changed (step 4 above):
1. DELETE all existing `Chunk` rows for this document in the same transaction.
2. DELETE all existing embedding vectors for this document in the same transaction (pgvector entries referencing the document).
3. UPDATE the `Document` row: `file_hash`, `file_size`, `updated_at`, `ingestion_status = pending`.
4. COMMIT the delete+update atomically — no orphaned embeddings, no stale search results.
5. Post-commit: re-chunk and re-embed asynchronously (same Celery task path as new docs).

If re-chunking succeeds but re-embedding fails midway (e.g., Ollama down): the document exists in the DB with correct content, partial embeddings in the index. On next sync tick, `file_hash` will match → no-op. The partial embedding is a known gap — full transactional embedding is not feasible without Ollama saga support. Document as Known Limitation. Mitigation: if Ollama is down, the admin should re-trigger ingestion after Ollama recovers.

If re-chunk/embed fails after the DB commit: document is updated in DB, stale embeddings deleted, new embeddings missing. Next sync: hash matches → no retry. Manual re-ingest (`POST /datasources/documents/{id}/re-ingest`) is the recovery path.

**Why DELETE before re-embed, not update-in-place:** stale embeddings silently linger in the vector index after content change, producing incorrect search results. This is a correctness bug for a product whose value proposition is accurate civic records search.

**Concurrency safety (H5):** `SELECT ... FOR UPDATE` on the existing document row before comparing hashes prevents two concurrent sync workers from both detecting a content change and racing to update. Last-write-wins without the lock produces non-deterministic chunk counts in the index. With the lock: one worker holds, the other waits and then finds a matching hash (no-op). This requires the session to be in a transaction before the SELECT.

Existing `ingest_file()` / `ingest_file_from_bytes()` unchanged. Binary connectors continue using `(source_id, file_hash)` path.

### Canonical serialization

**RestApiConnector.fetch():**
```python
raw = await self._make_request("GET", source_path)
parsed = raw.json()
record = _extract_dotted(parsed, cfg.data_key)  # None data_key → parsed
canonical = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
content = canonical.encode("utf-8")
```

**OdbcConnector.fetch():**
```python
row_dict = dict(zip(col_names, row))
row_dict.pop(cfg.modified_column, None)  # exclude change-detection column
canonical = json.dumps(row_dict, sort_keys=True, ensure_ascii=False, default=str)
content = canonical.encode("utf-8")
```

### Schema changes

**RestApiConfig** (new field):
```python
data_key: str | None = None          # dotted path to logical record in response
id_field: str = "id"                 # which field in each list element is the record ID
envelope_excludes: list[str] = []    # v2 placeholder — not used in v1
```

**DataSource:** no new fields in P6a.

### Migration (014_p6a_idempotency.py)

PostgreSQL partial indexes cannot use subqueries in WHERE. The documents table needs a `connector_type` column (denormalized from `data_sources.source_type`) to support type-scoped partial indexes.

```sql
-- 1. Add connector_type to documents (denormalized, set during ingestion)
ALTER TABLE documents ADD COLUMN connector_type VARCHAR(20);

-- 2. Backfill connector_type from data_sources
UPDATE documents d
SET connector_type = ds.source_type
FROM data_sources ds
WHERE d.source_id = ds.id;

-- 3. Backfill: for structured sources, dedupe by source_path — keep MAX(ingested_at)
DELETE FROM documents d1
WHERE d1.connector_type IN ('rest_api', 'odbc')
  AND EXISTS (
    SELECT 1 FROM documents d2
    WHERE d2.source_id = d1.source_id
      AND d2.source_path = d1.source_path
      AND d2.ingested_at > d1.ingested_at
  );

-- 4. Add partial UNIQUE indexes — type-scoped, non-overlapping
CREATE UNIQUE INDEX uq_documents_binary_hash
  ON documents (source_id, file_hash)
  WHERE connector_type NOT IN ('rest_api', 'odbc');

CREATE UNIQUE INDEX uq_documents_structured_path
  ON documents (source_id, source_path)
  WHERE connector_type IN ('rest_api', 'odbc');

-- 5. Add updated_at to documents (required for upsert semantics)
ALTER TABLE documents ADD COLUMN updated_at TIMESTAMPTZ;

-- 6. Enforce source_path max length
ALTER TABLE documents ADD CONSTRAINT chk_source_path_length
  CHECK (length(source_path) <= 2048);
```

**Going forward:** `ingest_file_from_bytes()` and `ingest_structured_record()` both set `connector_type` at insert time from the parent DataSource's `source_type`. The Document ORM model gets `connector_type: String(20)` as a non-nullable field with default `NULL` (nullable for legacy rows, required for new rows).

---

## Wizard UX (DataSources wizard Step 2 — REST source)

`data_key` field in the connection wizard:
- Label: **Record path** (not "data_key" — admin-facing language)
- Placeholder: `e.g., data or response.record — leave blank if API returns the record at root`
- Default suggestion: `data` (populated on focus if empty, can be cleared)
- **Live canonical preview:** after test-connection succeeds, show a collapsible panel: "This is what will be hashed for each record:" → formatted JSON of the extracted canonical record (first record from the response, `data_key` applied, `sort_keys=True` pretty-printed).
- **Pollution warning banner:** if test-connection returns `warning: non_deterministic_response`, surface as a yellow banner above the test-connection result, not buried in JSON.

---

## Test Plan

All tests written before any implementation code. Tests marked with `[FIRST]` must pass before migration runs.

| Test | File::Function | Description |
|---|---|---|
| [FIRST] REST determinism — envelope | `test_pipeline_idempotency.py::test_rest_envelope_timestamp_same_document` | Same logical record, two fetches with differing `fetched_at` in envelope → 1 document row |
| [FIRST] REST determinism — key order | `test_pipeline_idempotency.py::test_rest_key_order_same_document` | Same logical record, JSON keys in different order → 1 document row |
| [FIRST] ODBC determinism — modified_column | `test_pipeline_idempotency.py::test_odbc_modified_column_excluded` | Same row, `modified_column` ticks → 1 document row |
| [FIRST] ODBC determinism — column order | `test_pipeline_idempotency.py::test_odbc_column_order_same_document` | Column order from cursor changes → 1 document row |
| UNIQUE race — structured | `test_pipeline_idempotency.py::test_concurrent_structured_insert_race` | Two workers insert same `(source_id, source_path)` simultaneously → 1 document, `IntegrityError` handled gracefully |
| UNIQUE race — binary | `test_pipeline_idempotency.py::test_concurrent_binary_insert_race` | Two workers insert same `(source_id, file_hash)` simultaneously → 1 document, `IntegrityError` handled gracefully |
| UPDATE concurrent race | `test_pipeline_idempotency.py::test_concurrent_update_select_for_update` | Two workers detect same source_path with different hash → SELECT FOR UPDATE serializes; one wins, other finds matching hash and no-ops |
| UPDATE chunk lifecycle | `test_pipeline_idempotency.py::test_update_deletes_old_chunks_before_reembed` | Same source_path, content changes → old Chunk rows deleted, Document updated, re-chunking triggered; no stale chunks in DB |
| UPDATE embedding lifecycle | `test_pipeline_idempotency.py::test_update_deletes_old_embeddings_before_reembed` | Same as above; old pgvector entries for document deleted before re-embed |
| Migration — connector_type backfill + doc dedup | `test_migration_014.py::test_connector_type_backfill` | Seed DB with representative REST/ODBC docs (including dupes), prove connector_type set correctly and dedup keeps MAX(ingested_at) |
| Pollution detection — differs | `test_datasources_router.py::test_test_connection_pollution_warning` | `test-connection` with two differing fetches → `warning: non_deterministic_response` + differing_keys |
| Pollution detection — stable | `test_datasources_router.py::test_test_connection_no_pollution_warning` | `test-connection` with two identical fetches → no warning |
| data_key dotted path | `test_rest_connector.py::test_data_key_nested_extraction` | `data_key = "response.record"` extracts correctly from nested response |
| data_key missing path | `test_rest_connector.py::test_data_key_missing_raises_key_error` | `data_key = "missing.path"` → `KeyError` with descriptive message |
| data_key array | `test_rest_connector.py::test_data_key_array_each_element_is_record` | `data_key` resolves to list → each element is its own DiscoveredRecord |
| ODBC source_path encode + decode roundtrip | `test_odbc_connector.py::test_source_path_encode_decode_special_chars` | `pk_value` containing `/`, space, `%` → encoded in source_path, unquoted in fetch(), SQL finds row |
| REST source_path URL-encoding | `test_rest_connector.py::test_source_path_record_id_encoded` | Record ID containing `/` → encoded in source_path, GET request uses encoded URL |
| source_path max length | `test_datasources_router.py::test_source_path_max_length_rejected` | source_path > 2048 chars → rejected at validation |
| Update semantics | `test_pipeline_idempotency.py::test_structured_record_content_change_updates_document` | Same source_path, different content → document updated, `updated_at` set, no duplicate row |
| Skip semantics | `test_pipeline_idempotency.py::test_structured_record_same_hash_is_noop` | Same source_path, same content hash → document unchanged, `updated_at` not set |
