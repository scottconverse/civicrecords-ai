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

**Dead-letter threshold (M5 — time-bounded):** `permanently_failed` when `retry_count >= 5` OR `(now() - first_failed_at) > 7 days`, whichever comes first. At daily sync cadence, count-only would allow stuck retries for 5 days; with weekly sources that's 35+ days. Time bound prevents indefinite accumulation regardless of cadence.  
**Why both conditions:** count-only is too slow for high-frequency sources; time-only is too aggressive for low-frequency sources. AND of both is wrong (must exhaust both). OR of both (first to fire) is correct.

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
**Rate limiting (M7):** Multiple sources hitting circuit-open simultaneously (e.g., shared auth server outage) must not produce N emails per admin in 5 minutes. Batch notifications within a 5-minute window: if multiple sources go circuit-open within the same window, send a single "Multiple sources paused" digest instead of N individual emails. Implementation: use a `notification_batch_key` and dedup by `(recipient, event_type, window_start)`.  
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

### D13b: Pipeline failure classification (H8)
When `ingest_structured_record()` fails (not the connector), error type determines handling:

| Error class | Handling | Rationale |
|---|---|---|
| `sqlalchemy.exc.IntegrityError` | Immediately `permanently_failed` (skip task-level retry) | Code bug — retrying won't fix a constraint violation. Needs dev attention. |
| `IOError`, `OSError` (disk full, filesystem) | Task-level retry | Infrastructure issue — transient |
| `httpx.TimeoutException`, `httpx.ConnectError` (Ollama down) | Task-level retry | Service availability — transient |
| `asyncio.TimeoutError` | Task-level retry | Transient |
| Any other unexpected exception | Task-level retry (up to 3), then `sync_failures` as `retrying` | Default conservative behavior |

**Rationale:** "pipeline errors are handled identically to connector fetch errors" is too coarse. An `IntegrityError` retried 3× wastes worker time and produces misleading retry-count metrics. A disk-full error may resolve in seconds. Classify at the exception type level.  
**Test link:** `test_sync_runner_pipeline_failures.py`

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

### "Sync Now" button — real completion tracking (M6 — backoff + longer timeout)
1. Click → POST `/datasources/{id}/ingest` → record `triggered_at = Date.now()`. Button transitions to "Syncing…" (spinner, disabled).
2. Poll `GET /datasources/{id}` with exponential backoff: 5s → 10s → 20s → 30s (cap at 30s). Compare `last_sync_at` against `triggered_at`. If `last_sync_at > triggered_at` OR `last_sync_status` changed → sync complete.
3. On completion: refresh card, button returns to "Sync Now", toast: "Sync complete — N records processed" or "Sync failed — check failed records."
4. Poll timeout: 15 minutes (not 5 — large ODBC tables or slow REST APIs can exceed 5 minutes legitimately). Display elapsed time: "Syncing for 7m 23s…" (client-side timer). At 15min: toast "Sync is taking longer than expected — check back shortly," reset button. Do NOT assume sync failed.
5. De-bounce: button disabled for 3s after click to prevent double-queue.
6. **Automated test (H3 — required, not manual QA):** Component-level test with mocked `useSyncNow` hook and mocked `fetch` returning controlled `last_sync_at` updates at simulated intervals. Test: button transitions to "Syncing…" on click; remains disabled during polling; returns to "Sync Now" after mocked completion; shows correct toast. Use `jest.useFakeTimers()` or equivalent to control polling intervals without real time passing. This prevents polling logic refactors from silently breaking the button state contract.

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

| Test | File::Function | Description | Decision |
|---|---|---|---|
| sync_failures table write | `test_sync_failures.py::test_failed_record_creates_sync_failure_row` | Failed record → row with correct fields | D1 |
| Task-level exhaustion → record-level | `test_sync_runner_retry_layers.py::test_task_retry_exhaustion_creates_sync_failure` | Task retries 3×, then inserts sync_failures row with status=retrying | D2 |
| Retry ordering | `test_sync_runner_retry_layers.py::test_retrying_rows_processed_before_discover` | retrying rows processed before discover() on same tick | D2 |
| Runner retry cap — N | `test_sync_runner_retry_cap.py::test_retry_cap_by_count` | 100 retrying rows, batch_size=10 → 10 retried, 90 remain | D4 |
| Runner retry cap — T | `test_sync_runner_retry_cap.py::test_retry_cap_by_time` | Retries exceed time_limit_seconds → batch stops mid-queue | D4 |
| Dead-letter — count threshold | `test_sync_failures.py::test_dead_letter_at_retry_count_5` | retry_count reaches 5 → status=permanently_failed | D5/M5 |
| Dead-letter — time threshold | `test_sync_failures.py::test_dead_letter_at_7_days` | first_failed_at > 7 days ago, retry_count < 5 → permanently_failed | D5/M5 |
| 404 → tombstone | `test_sync_failures.py::test_404_response_creates_tombstone` | Task retries return 404 → status=tombstone, not retrying | D5 |
| Cursor advance on partial | `test_sync_runner_cursor.py::test_partial_failure_cursor_advances_past_successes` | 8 succeed, 2 fail → cursor advances past 8, 2 rows in sync_failures | D6 |
| Dismiss = soft delete | `test_sync_failures.py::test_dismiss_sets_dismissed_status_not_deletes` | Dismiss → status=dismissed, row present, dismissed_at+dismissed_by set | D7 |
| Bulk retry | `test_sync_failures_router.py::test_retry_all_permanently_failed` | retry-all resets permanently_failed rows to retrying | D8 |
| Bulk dismiss | `test_sync_failures_router.py::test_dismiss_all_permanently_failed` | dismiss-all soft-deletes permanently_failed rows | D8 |
| Circuit open — auth fail | `test_circuit_breaker.py::test_circuit_opens_on_authenticate_failure` | authenticate() raises 5× → sync_paused=True | D3 |
| Circuit open — all records fail | `test_circuit_breaker.py::test_circuit_opens_when_all_fetches_fail` | All fetches fail 5 consecutive runs → circuit open | D3 |
| Circuit NOT open — zero work (M8) | `test_circuit_breaker.py::test_zero_records_discovered_does_not_increment_counter` | discover() returns 0 five times → counter=0, no circuit open | D3 |
| Circuit NOT open — retry-only success | `test_circuit_breaker.py::test_retry_success_with_zero_new_records_resets_counter` | 0 new records, retrying rows succeed → counter resets to 0, NOT full-run failure | D3/M8 |
| Circuit NOT open — partial success | `test_circuit_breaker.py::test_partial_success_resets_counter` | Mix of success and failure in same run → counter resets to 0 | D3 |
| Circuit open → notification | `test_sync_notifications.py::test_circuit_open_fires_notification` | Circuit opens → notify() called with source name, error summary | D9 |
| No first-failure notification | `test_sync_notifications.py::test_single_failure_does_not_notify` | Single run failure (count=1) → notify() NOT called | D9 |
| Recovery notification | `test_sync_notifications.py::test_recovery_notification_on_first_successful_sync_after_unpause` | Unpause + successful sync → recovery notify() called | D9 |
| Notification rate limit | `test_sync_notifications.py::test_multiple_circuit_opens_batched_to_digest` | 3 sources circuit-open within 5-min window → 1 digest email, not 3 | D9/M7 |
| Unpause grace — re-pauses at 2 | `test_circuit_breaker.py::test_unpause_grace_period_threshold_is_2` | Unpause, fail twice → sync_paused=True (threshold 2, not 5) | D3 |
| Unpause grace — resets after success | `test_circuit_breaker.py::test_unpause_grace_period_resets_after_success` | Unpause, succeed once → threshold returns to 5 | D3 |
| 429 Retry-After honored | `test_rest_connector.py::test_429_retry_after_header_honored` | 429 with Retry-After:30 → task waits ~30s before retry | D10 |
| health_status = degraded | `test_datasources_router.py::test_health_status_degraded_on_failure_count` | consecutive_failure_count > 0 → health_status=degraded | D13 |
| health_status = degraded (failures) | `test_datasources_router.py::test_health_status_degraded_on_active_sync_failures` | active sync_failures rows → health_status=degraded even with count=0 | D13 |
| health_status = circuit_open | `test_datasources_router.py::test_health_status_circuit_open_when_paused` | sync_paused=True → health_status=circuit_open | D13 |
| sync_run_log per run | `test_sync_run_log.py::test_each_sync_creates_one_run_log_row` | Each sync run → one log row with correct stats | D11 |
| CASCADE on delete | `test_sync_failures.py::test_cascade_delete_removes_failures_and_run_log` | Delete DataSource → sync_failures + sync_run_log rows cascade-deleted | D12 |
| Pipeline IntegrityError → permanently_failed | `test_sync_runner_pipeline_failures.py::test_integrity_error_skips_task_retry` | ingest_structured_record raises IntegrityError → immediately permanently_failed, no task retry | D13b |
| Pipeline transient → task retry | `test_sync_runner_pipeline_failures.py::test_ioerror_triggers_task_retry` | ingest_structured_record raises IOError → task-level retry | D13b |
| Sync Now button — component (H3) | `DataSourceCard.test.tsx::test_sync_now_button_stays_disabled_until_completion` | Click → "Syncing…" + disabled; mock returns updated last_sync_at → button resets, toast shown | D-UI-1 |
| Sync Now button — polling elapsed display | `DataSourceCard.test.tsx::test_sync_now_shows_elapsed_time_during_sync` | After 7min (fake timer) → button shows "Syncing for 7m…" | D-UI-1 |
