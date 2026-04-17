# P7 — Sync Failures, Circuit Breaker, UI Polish

**Date:** 2026-04-16  
**Status:** Approved for implementation  
**Depends on:** P6a (upsert path must be live before retry is safe by construction)

---

## Problem Statement

When a connector sync partially fails — some records fetch successfully, others don't — the current runner has no persistent tracking. Failures are logged and discarded. On the next run, the runner re-discovers and re-attempts everything from the last cursor position, causing re-ingestion of already-processed records and potentially retrying the same failing record forever if the cursor never advances. There is also no circuit breaker, no admin visibility into failure state, and no UI feedback on sync status.

---

## Decision Log

### D1: `sync_failures` table (not JSONB on DataSource)
**Decision:** Dedicated `sync_failures` table. See schema below.  
**Why:** Cross-source reliability queries ("all dead-lettered records this week by error type") require SQL. JSONB makes those queries expensive and unindexable. A separate table also supports bulk operations cleanly.  
**Test link:** `test_sync_failures_table.py`

### D2: Two distinct retry layers
**Decision:** Both layers exist. They are named and distinct in the spec.

| Layer | Scope | Trigger | Backoff | Limit |
|---|---|---|---|---|
| **Task-level** | Single sync run | Transient errors (network blip, timeout) | 30s → 90s → 270s exponential | 3 retries, 10-min hard cap |
| **Record-level** | Across sync runs | Persistent failure after task exhaustion | One attempt per scheduler tick | 5 retries per sync_failures row |

**Handoff:** when task-level retries are exhausted for a given record, the runner inserts a `sync_failures` row with `status = 'retrying'`. Record-level retry picks it up on subsequent ticks.  
**Why both:** task-level handles VPN hiccups without polluting the failures table. Record-level handles auth revocations, malformed records, upstream bugs. Without task-level, every county firewall hiccup enqueues a failures row; circuit breaker trips from noise, not signal.  
**Test link:** `test_sync_runner_retry_layers.py`

### D3: Circuit breaker semantics — explicit rules

**A run counts as a full-run failure if:**
- `authenticate()` raises before `discover()` is called, OR
- `discover()` raises, OR
- Every attempted fetch (new records + record-level retries) returns an error.

**A run does NOT count as a full-run failure if:**
- `discover()` returns 0 records (nothing new — not a failure, counter unchanged).
- At least one fetch (new or retry) succeeds.
- Only record-level retries ran and some succeeded (even if new record count = 0).

**Counter behavior:**
- Full-run failure → increment `consecutive_failure_count`.
- Any successful fetch in the run → reset `consecutive_failure_count` to 0.
- Zero-work run (discover returns 0, no retries pending) → counter unchanged.

**Circuit open:** `consecutive_failure_count >= 5` → set `sync_paused = True`, `sync_paused_at = now()`, `sync_paused_reason = "Circuit open after 5 consecutive full-run failures"`. Fire circuit-open notification.

**Unpause grace period:** after admin calls `POST /datasources/{id}/unpause`, the circuit re-opens at `consecutive_failure_count >= 2` (not 5) for the first post-unpause sync window. If that sync succeeds, threshold returns to 5. If it fails twice, re-pause and notify.  
**Why:** admin who unpauses with creds still wrong sees immediate feedback (2 failures) rather than grinding through 5 again and wondering if unpause did anything.  
**Test link:** `test_circuit_breaker.py`

### D4: Per-run retry cap
**Decision:** Each sync run retries at most `retry_batch_size` (default 100) record-level failures OR runs for at most `retry_time_limit_seconds` (default 90), whichever is hit first. Remaining `retrying` rows roll to the next tick.  
**Why:** 1000 queued retries × 2s each = 33min. Next two 5-min ticks fire into a still-running worker. Queue death.  
**Config:** `retry_batch_size` and `retry_time_limit_seconds` are per-source fields (nullable, fallback to defaults). Not in UI for v1 — admin sets via direct API if needed.  
**Test link:** `test_sync_runner_retry_cap.py`

### D5: Record-level retry semantics

**404 → tombstone:** if task-level retries on a record consistently return 404, insert `sync_failures` row with `status = 'tombstone'`. Tombstone rows are not retried. Admin sees them in the failed records panel as "Record no longer exists upstream." Dismiss clears them.

**Dead-letter threshold:** after 5 record-level retries (tracked in `sync_failures.retry_count`), set `status = 'permanently_failed'`. No further automatic retry. Admin must explicitly retry or dismiss.

**Retry ordering:** retry `status = 'retrying'` rows first, then run `discover()` for new records. Getting old failures resolved matters more than expanding the backlog.

### D6: Partial failure cursor semantics
**Decision:** Cursor advances to the last successfully-fetched record's `last_modified` timestamp (or now() if no timestamp available), not held at the start of the run.  
Failed records are captured in `sync_failures` by `source_path`. The cursor advance ensures future `discover()` calls don't re-discover already-processed records. Failed records are retried explicitly via the record-level layer, not by rewinding the cursor.  
**Why:** all-or-nothing cursor means one poisoned record freezes the source forever and causes re-fetching of 50k records nightly. Partial advance + record-level retry is correct.

### D7: Dismiss = soft delete
**Decision:** Dismiss sets `status = 'dismissed'` with `dismissed_at` and `dismissed_by` (user ID). Hard deletes are prohibited.  
**Why:** for a civic records product, "we chose not to ingest this record" is itself a compliance artifact. The audit trail must be preserved.

### D8: Bulk actions
**Decision:** Ship in v1.  
`POST /datasources/{id}/sync-failures/retry-all?status=permanently_failed` — resets matching rows to `retrying`.  
`POST /datasources/{id}/sync-failures/dismiss-all?status=permanently_failed` — soft-deletes matching rows.  
**Why:** admin with 50 stuck records will not click Retry 50 times. Bolting this on as a hotfix is worse than shipping it now.

### D9: Notifications
**Channel:** Use existing notification infrastructure (SMTP — same as deadline notifications).  
**Recipients:** `created_by` user of the DataSource. If user is inactive (deactivated account), fall back to all users with `role >= ADMIN`.  
**Notification triggers (required):**
1. **Circuit open:** source paused after N consecutive failures. Include: source name, error summary, link to admin dashboard.
2. **Recovery:** source re-enabled AND first post-unpause sync succeeds. Include: source name, sync summary, records processed.

**Notification NOT triggered on:** individual record failures, single-run failures below circuit threshold.  
**Test link:** `test_sync_notifications.py`

### D10: 429 / Retry-After
**Decision:** `Retry-After` header in REST connector responses is honored at the task-level retry layer. If the response is 429 with `Retry-After: N`, the task waits N seconds (up to 10-min hard cap) before retrying. Capped at 600s to prevent a single task holding a worker indefinitely.  
**Why:** 429 is a transient, expected condition for rate-limited municipal APIs. It belongs in task-level, not in `sync_failures`.

### D11: Minimal sync run log
**Decision:** New `sync_run_log` table — one row per sync run, no coupling to retry logic.

```sql
sync_run_log(id, source_id, started_at, finished_at, status, 
             records_attempted, records_succeeded, records_failed, error_summary)
```

**Why:** "why did this sync run at 2:13 instead of 2:00" is otherwise unanswerable. Run log is pure observability; retry tracking stays in `sync_failures`.

### D12: CASCADE on DataSource delete
**Decision:** `sync_failures` and `sync_run_log` both have `source_id FK → data_sources.id ON DELETE CASCADE`.  
**Why:** orphaned failure rows for a deleted source are noise. Admin who deletes a source intends to remove all associated state.

### D13: `degraded` health state
**Decision:** Three health states: `healthy` (green), `degraded` (yellow), `circuit_open` (red).  

`health_status` is **computed at API response time** (not a stored field) from:
- `sync_paused = True` → `circuit_open`
- `consecutive_failure_count > 0` → `degraded`
- Active sync_failures exist (status IN ('retrying', 'permanently_failed')) → `degraded`
- else → `healthy`

The list endpoint (`GET /datasources/`) computes health_status via a single LEFT JOIN + COUNT on sync_failures, not N+1 queries:
```sql
SELECT ds.*, COUNT(sf.id) FILTER (WHERE sf.status IN ('retrying','permanently_failed')) AS active_failures
FROM data_sources ds
LEFT JOIN sync_failures sf ON sf.source_id = ds.id
GROUP BY ds.id
```
`health_status` is then derived from `sync_paused`, `consecutive_failure_count`, and `active_failures > 0`.

**Why computed:** avoids cache staleness between runs. The two stored inputs (`consecutive_failure_count`, `sync_paused`) are always current; only the failures count needs the join.

---

## Schema

### `sync_failures` table (migration 016_p7_sync_failures.py)

```sql
CREATE TABLE sync_failures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    source_path TEXT NOT NULL,
    error_message TEXT,
    error_class VARCHAR(200),
    http_status_code INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'retrying',
      -- 'retrying' | 'permanently_failed' | 'tombstone' | 'dismissed'
    first_failed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_retried_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,
    dismissed_by UUID REFERENCES users(id)
);

CREATE INDEX ix_sync_failures_source_status ON sync_failures(source_id, status);
CREATE INDEX ix_sync_failures_created ON sync_failures(first_failed_at);
```

### `sync_run_log` table

```sql
CREATE TABLE sync_run_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(20),  -- 'success' | 'partial' | 'failed'
    records_attempted INTEGER DEFAULT 0,
    records_succeeded INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_summary TEXT
);

CREATE INDEX ix_sync_run_log_source ON sync_run_log(source_id, started_at DESC);
```

### DataSource new columns

```sql
ALTER TABLE data_sources ADD COLUMN consecutive_failure_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE data_sources ADD COLUMN last_error_message VARCHAR(500);
ALTER TABLE data_sources ADD COLUMN last_error_at TIMESTAMPTZ;
ALTER TABLE data_sources ADD COLUMN sync_paused BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE data_sources ADD COLUMN sync_paused_at TIMESTAMPTZ;
ALTER TABLE data_sources ADD COLUMN sync_paused_reason VARCHAR(200);
ALTER TABLE data_sources ADD COLUMN retry_batch_size INTEGER;
ALTER TABLE data_sources ADD COLUMN retry_time_limit_seconds INTEGER;
```

---

## API Endpoints

| Method | Route | Auth | Description |
|---|---|---|---|
| GET | `/datasources/{id}/sync-failures` | ADMIN | List failures. Filter: `?status=retrying\|permanently_failed\|tombstone\|dismissed`. Paginated. |
| POST | `/datasources/{id}/sync-failures/{fid}/retry` | ADMIN | Reset `permanently_failed` → `retrying`, clear `dismissed_at` |
| POST | `/datasources/{id}/sync-failures/{fid}/dismiss` | ADMIN | Soft-delete: set `status = dismissed`, `dismissed_at`, `dismissed_by` |
| POST | `/datasources/{id}/sync-failures/retry-all` | ADMIN | Bulk retry. `?status=permanently_failed` required. |
| POST | `/datasources/{id}/sync-failures/dismiss-all` | ADMIN | Bulk dismiss. `?status=permanently_failed` required. |
| POST | `/datasources/{id}/unpause` | ADMIN | Clear circuit: `sync_paused=False`, `consecutive_failure_count=0`, arm grace period (threshold=2 for next window). |
| GET | `/datasources/{id}/sync-run-log` | ADMIN | Recent sync runs. Default limit 20. |

---

## Frontend (P7 UI Polish)

### SourceCard — Option B layout

Left panel (90px, `#EBF3FA` background):
- Connector type icon (large)
- Health badge: `healthy` (green dot + "Healthy"), `degraded` (amber dot + "Degraded"), `circuit_open` (red dot + "Paused")
- Source type chip

Right panel:
- Source name (bold), source type + active/inactive
- Metadata grid (2×2): Last Sync, Next Sync, Schedule state (per D5 of P6b), Records
- Actions row: "Sync Now" button, "Edit" button

### "Sync Now" button — real completion tracking
1. Click → POST `/datasources/{id}/ingest` → button transitions to "Syncing…" (spinner, disabled)
2. Poll `GET /datasources/{id}` every 5s for `last_sync_at` to advance past the pre-click value (or `last_sync_status` to change)
3. On detection: refresh card data, button returns to "Sync Now", toast: "Sync complete — N records processed" or "Sync failed — check failed records"
4. Poll timeout: 5 minutes. If no completion detected, show toast "Sync is taking longer than expected — check back shortly" and reset button. Do NOT re-enable while sync may still be running.
5. De-bounce: button disabled for 3s after click to prevent double-queue.

### Failed Records Panel
Expandable section below each card. Card shows a count badge when `sync_failures` has active rows.

**States (all required):**
- **Loading:** spinner on expand
- **Zero state:** "No failed records — this source is syncing cleanly" (gray italic)
- **Populated:** table with columns: Record path, Error, Retries, Status, First failed, Actions (Retry / Dismiss)
- **Circuit open banner:** when `sync_paused = True`, amber banner at top of panel: "⚠️ This source is paused after repeated failures. [Unpause →]"
- **Error state:** "Failed to load sync failures. Retry?" with retry button (for when GET /sync-failures itself fails)

**Bulk actions:** "Retry all permanently failed" and "Dismiss all permanently failed" buttons above table, only shown when relevant rows exist.

### `DataSourceRead` schema additions

P7 adds these fields (P6b fields `sync_schedule`, `schedule_enabled`, `next_sync_at` are already present from that sprint):
```python
last_sync_at: datetime | None
last_sync_status: str | None          # success | partial | failed
last_error_message: str | None
consecutive_failure_count: int
health_status: str                    # healthy | degraded | circuit_open (computed — see D13)
sync_paused: bool
active_failure_count: int             # count of retrying + permanently_failed rows
```

---

## Test Plan

| Test | File | Description | Linked Decision |
|---|---|---|---|
| `sync_failures` table write | `test_sync_failures.py` | Failed record → row in sync_failures with correct fields | D1 |
| Task-level exhaustion → record-level | `test_sync_runner_retry_layers.py` | Task retries 3×, then inserts sync_failures row | D2 |
| Retry ordering | `test_sync_runner_retry_layers.py` | retrying rows processed before discover() | D2 |
| Runner retry cap — N | `test_sync_runner_retry_cap.py` | 100 retrying rows, cap=10 → 10 retried, 90 stay | D4 |
| Runner retry cap — T | `test_sync_runner_retry_cap.py` | Each retry sleeps >90s total → stops mid-batch | D4 |
| Dead-letter threshold | `test_sync_failures.py` | 5 record-level retries → permanently_failed | D5 |
| 404 → tombstone | `test_sync_failures.py` | Task retries return 404 → status=tombstone | D5 |
| Cursor advance on partial | `test_sync_runner_cursor.py` | 8 succeed, 2 fail → cursor advances past 8, 2 in sync_failures | D6 |
| Dismiss = soft delete | `test_sync_failures.py` | Dismiss → status=dismissed, row not deleted, dismissed_at set | D7 |
| Bulk retry | `test_sync_failures_router.py` | retry-all resets permanently_failed rows to retrying | D8 |
| Bulk dismiss | `test_sync_failures_router.py` | dismiss-all soft-deletes permanently_failed rows | D8 |
| Circuit open — auth fail | `test_circuit_breaker.py` | authenticate() raises 5× → sync_paused=True, notification fired | D3 |
| Circuit open — all fail | `test_circuit_breaker.py` | All records fail 5 consecutive runs → circuit open | D3 |
| Circuit NOT open — zero work | `test_circuit_breaker.py` | discover() returns 0 five times → counter unchanged, no circuit open | D3 |
| Circuit NOT open — partial success | `test_circuit_breaker.py` | Mixed success/fail → counter resets to 0 | D3 |
| Circuit open — notification fired | `test_sync_notifications.py` | Circuit opens → notify() called with correct args | D9 |
| Circuit open — no first-failure notify | `test_sync_notifications.py` | Single run failure → notify() NOT called | D9 |
| Recovery notification | `test_sync_notifications.py` | Unpause + successful sync → recovery notify() called | D9 |
| Unpause grace period — re-pauses at 2 | `test_circuit_breaker.py` | Unpause, fail twice → re-paused (not 5) | D3 |
| Unpause grace period — resets at success | `test_circuit_breaker.py` | Unpause, succeed once → threshold returns to 5 | D3 |
| 429 Retry-After honored | `test_rest_connector.py` | 429 with Retry-After:30 → task waits ~30s | D10 |
| health_status = degraded | `test_datasources_router.py` | consecutive_failure_count > 0 → health_status=degraded in GET response | D13 |
| health_status = circuit_open | `test_datasources_router.py` | sync_paused=True → health_status=circuit_open | D13 |
| sync_run_log row per run | `test_sync_run_log.py` | Each sync run creates one log row with correct stats | D11 |
| CASCADE on source delete | `test_sync_failures.py` | Delete DataSource → sync_failures rows deleted, sync_run_log rows deleted | D12 |
