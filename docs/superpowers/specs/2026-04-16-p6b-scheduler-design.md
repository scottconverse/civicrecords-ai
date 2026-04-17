# P6b — Cron Scheduler Rewrite + Schedule UI States

**Date:** 2026-04-16  
**Status:** Approved for implementation  
**Depends on:** P6a (ships after)  
**Replaces:** `schedule_minutes` interval-based drift scheduler

---

## Problem Statement

The current scheduler (`check_scheduled_sources`) checks `(now - last_ingestion_at) > timedelta(minutes=schedule_minutes)` every 5 minutes. This is interval-based and drifts — a 24-hour sync doesn't run "nightly at 2am," it runs "24 hours after whenever the last run finished." Municipal admins think in clock time. Rate-limited APIs and compliance audit trails ("when did we last pull from X?") require predictable, clock-anchored scheduling. The `sync_schedule` cron field exists in the model but has never been read.

---

## Decision Log

### D1: Switch to cron-based scheduling via `croniter`
**Decision:** `sync_schedule` (String(50), cron expression) is the single scheduling field. `schedule_minutes` is dropped.  
**Why:** `croniter` (Apache 2.0 licensed) parses standard cron expressions and computes next/previous run times in UTC. Cron expressions match how admins think: "nightly at 2am" = `0 2 * * *`. No drift.  
**Scheduler behavior:** `check_scheduled_sources` (fires every 5 min) evaluates each active, non-paused source with a non-null `sync_schedule`. For each: `croniter(expr, last_sync_at or epoch, hash_use_datetime=True).get_prev(datetime)` — if the previous scheduled slot is after `last_sync_at`, the source is overdue → trigger.

### D2: Minimum interval validation — rolling week sampling
**Decision:** Reject any cron expression where the minimum interval across a rolling 7-day window is < 5 minutes.  
**Why:** `*/1 0 * * *` looks like "once per minute in hour 0 only" but fires 60 times between midnight and 1am. Checking only `get_next()` from now misses this. Sample the full week.  
**Implementation:**
```python
def min_interval_minutes(expr: str) -> int:
    it = croniter(expr, datetime.now(UTC))
    prev = it.get_next(datetime)
    min_gap = float("inf")
    for _ in range(2016):  # 7 days × 288 ticks/day at 5-min granularity
        nxt = it.get_next(datetime)
        gap = (nxt - prev).total_seconds() / 60
        min_gap = min(min_gap, gap)
        prev = nxt
    return int(min_gap)
```
Validation: `min_interval_minutes(expr) < 5` → reject with message "Schedule fires more frequently than every 5 minutes. Minimum allowed interval is 5 minutes."  
Validated server-side at `DataSourceCreate`, `DataSourceUpdate`, and `test-connection`.

### D3: `schedule_enabled` boolean — preserve expression across toggle
**Decision:** New boolean field `schedule_enabled` (default `True`) on DataSource.  
When `schedule_enabled = False`: scheduler ignores `sync_schedule` even if set. Source is "Manual only."  
**Why:** Don't null `sync_schedule` on disable — admin loses their configured expression and must re-enter it on re-enable. `schedule_enabled = False` preserves the field; re-enabling pre-fills the UI.  
**UI toggle:** "Enable automatic sync" checkbox. When unchecked, schedule picker is hidden but field is preserved in form state. Saved as `schedule_enabled = False`.

### D4: `schedule_minutes` migration
**Decision:** Migration converts any non-null `schedule_minutes` values to approximate cron expressions before dropping the column. Convert via: 15→`*/15 * * * *`, 30→`*/30 * * * *`, 60→`0 * * * *`, 360→`0 */6 * * *`, 720→`0 */12 * * *`, 1440→`0 2 * * *` (anchored to 2am, not midnight, as a reasonable default). Any other value: convert to `*/{N} * * * *` if N < 60, else `0 */{H} * * *` where H = N/60 rounded. If the resulting expression fails min-interval validation, set `sync_schedule = NULL` and `schedule_enabled = False`.  
As of 2026-04-16, no production rows have `schedule_minutes` set (UI never exposed it). State this in the migration comment so reviewers can verify.

### D5: Three-state card schedule display
| DataSource state | Display |
|---|---|
| `sync_schedule IS NULL OR schedule_enabled = False` | **"Manual only"** (gray text, no clock icon) |
| `schedule_enabled = True` AND `sync_paused = False` | **"Next: Apr 17 at 2:00 AM"** (computed via `croniter.get_next()` from `last_sync_at`) |
| `sync_paused = True` | **"Paused — check failed records"** (amber, links to failed records panel) |

### D6: Schedule presets UI
Preset dropdown maps human labels to cron strings:

| Label | Cron |
|---|---|
| Every 15 minutes | `*/15 * * * *` |
| Every 30 minutes | `*/30 * * * *` |
| Every hour | `0 * * * *` |
| Every 6 hours | `0 */6 * * *` |
| Every 12 hours | `0 */12 * * *` |
| Nightly at 2am | `0 2 * * *` |
| Weekly (Mon 2am) | `0 2 * * 1` |
| Custom… | (reveals cron text input) |

Custom input: shows raw cron expression, inline validation on blur, min-interval error shown inline.

---

## Schema Changes

**Migration 015_p6b_scheduler.py:**

```sql
-- 1. Add schedule_enabled
ALTER TABLE data_sources ADD COLUMN schedule_enabled BOOLEAN NOT NULL DEFAULT TRUE;

-- 2. Migrate schedule_minutes → sync_schedule (see D4 logic)
UPDATE data_sources SET sync_schedule = ... WHERE schedule_minutes IS NOT NULL;

-- 3. Drop schedule_minutes
ALTER TABLE data_sources DROP COLUMN schedule_minutes;

-- 4. Add croniter-validated check constraint (basic sanity, not full validation)
-- Full validation is in Python; DB constraint prevents empty strings
ALTER TABLE data_sources ADD CONSTRAINT chk_sync_schedule_nonempty
  CHECK (sync_schedule IS NULL OR length(trim(sync_schedule)) > 0);
```

**DataSourceCreate / DataSourceUpdate:** add `sync_schedule: str | None`, `schedule_enabled: bool = True`. Remove `schedule_minutes`.  
**DataSourceRead:** add `sync_schedule`, `schedule_enabled`, remove `schedule_minutes`. Add `next_sync_at: datetime | None` (computed field, not stored — returned by API via `croniter.get_next()` at response time).

---

## Scheduler Changes (`backend/app/ingestion/scheduler.py`)

`check_scheduled_sources` rewrite:
```python
async def check_scheduled_sources():
    sources = await session.execute(
        select(DataSource).where(
            DataSource.is_active == True,
            DataSource.schedule_enabled == True,
            DataSource.sync_paused == False,
            DataSource.sync_schedule.isnot(None),
        )
    )
    triggered = 0
    for source in sources.scalars():
        anchor = source.last_sync_at or datetime(1970, 1, 1, tzinfo=UTC)
        it = croniter(source.sync_schedule, anchor, hash_use_datetime=True)
        prev_scheduled = it.get_prev(datetime)
        if prev_scheduled > anchor:
            task_ingest_source.delay(str(source.id))
            triggered += 1
    return {"checked": count, "triggered": triggered}
```

---

## Test Plan

| Test | File | Description |
|---|---|---|
| Cron trigger — overdue | `test_scheduler.py` | Source with `0 2 * * *`, `last_sync_at` = yesterday → triggered |
| Cron trigger — not due | `test_scheduler.py` | Source with `0 2 * * *`, `last_sync_at` = today at 2:01am → not triggered |
| Cron trigger — first run | `test_scheduler.py` | Source with `last_sync_at = NULL` → triggered immediately |
| Min interval — fine | `test_scheduler.py` | `0 * * * *` (hourly) → passes validation |
| Min interval — too fast | `test_scheduler.py` | `*/1 0 * * *` → rejected |
| Min interval — adversarial | `test_scheduler.py` | `*/1 0 * * *` — rolling week sampling catches it |
| schedule_enabled = False | `test_scheduler.py` | Source with valid cron but `schedule_enabled = False` → not triggered |
| sync_paused = True | `test_scheduler.py` | Source with valid cron but `sync_paused = True` → not triggered |
| Migration — schedule_minutes | `test_migration_015.py` | Representative schedule_minutes values convert correctly to cron |
| next_sync_at computed | `test_datasources_router.py` | GET /datasources/ returns correct `next_sync_at` for each state |
| Preserve on toggle | `test_datasources_router.py` | PATCH schedule_enabled=False → sync_schedule unchanged in DB |
