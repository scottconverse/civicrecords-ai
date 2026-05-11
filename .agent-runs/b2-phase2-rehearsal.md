# CivicRecords AI B2 Phase 2 Rehearsal

Date: 2026-05-11
Branch: master
Phase 1 PR: #74
Phase 1 merge SHA: 902db173366359124e4d8e84f3c440df61aa62f4
Status: RED - halt at Phase 2 review gate

## Goal

Run a fresh-state local rehearsal for the B2 Docker secret extraction sprint before
any v1.6.0 tag push:

- `install.sh`
- `docker compose up`
- `docker exec <records-api> env | grep -E "JWT_SECRET|FIRST_ADMIN_PASSWORD"`
- release artifact SHA256 capture

## Completed Evidence

The Phase 1 release verifier passed on the merged code before this rehearsal:

```text
RECOVERY-GATES: PASSED
SECRET-SCAN: PASSED (509 tracked file(s) scanned)
[PASS] compose runtime provisioned
[PASS] api container env hides JWT_SECRET and FIRST_ADMIN_PASSWORD
[PASS] sovereignty guard passed
[PASS] pytest collect-only: 637 test(s)
[PASS] pytest full suite: 637 passed
[PASS] frontend vitest
[PASS] frontend production build
[PASS] Playwright user-flow tests
[PASS] runtime install proof
VERIFY-RELEASE: PASSED
```

GitHub CI also passed on PR #74:

```text
Run: 25688368816
Backend (pytest via docker compose): pass
T2C bootstrap-failure smoke test: pass
Frontend (vitest + build): pass
Release recovery gates: pass
ruff (lint): pass
```

## Artifact SHA256

Local backend release artifacts produced by the runtime install proof:

```text
781c30b664087b16b62e425d1f1ae51eba8130b289857ec3c38bf0a49aa2276c  civicrecords_ai-1.6.0-py3-none-any.whl
1479aa7a7c6fb0f3a566d56f56ace2e3efdff27d31bda97e504c107ccc242cf7  civicrecords_ai-1.6.0.tar.gz
```

## Phase 2 Blocker 1: install.sh Hardware Gate

`install.sh` cannot complete on this local host because
`scripts/detect_hardware.sh` exits non-zero below the Tier 5 32 GB RAM floor.

Probe output:

```text
=== CivicRecords AI Hardware Detection ===

CPU: AMD Ryzen 7 5800H with Radeon Graphics
Platform: Unknown AMD processor - defaulting to CPU inference
ROCm not installed - will use CPU inference
For GPU acceleration, run: amdgpu-install --usecase=rocm

NPU: XDNA driver not loaded (install kernel 6.11+ and amdxdna driver for NPU access)

RAM: 14 GB total
ERROR: CivicRecords AI requires a minimum of 32 GB RAM (Tier 5 target-profile baseline). Found: 14 GB
       No Gemma 4 tag is supportable below this floor. Aborting hardware gate.
       This matches scripts/detect_hardware.ps1 behavior on Windows (exits 1 below 32 GB).
```

Decision needed: run Phase 2 on a host that satisfies the Tier 5 hardware gate, or
authorize a bounded installer rehearsal mode that exercises B2 secret handling
without bypassing the production hardware gate.

## Phase 2 Blocker 2: Literal B2 Env-Grep Criterion Still Fails

The sprint directive's primary B2 acceptance command was:

```bash
docker exec <records-api> env | grep -E "JWT_SECRET|FIRST_ADMIN_PASSWORD"
```

Expected result: zero lines.

Observed result against the running API container from the successful release
verifier:

```text
FIRST_ADMIN_PASSWORD_FILE=/run/secrets/first_admin_password
JWT_SECRET_FILE=/run/secrets/jwt_secret
```

Assessment:

- Phase 1 hides the raw secret values from container env.
- Phase 1 does not satisfy the stricter literal criterion because the `_FILE`
  pointer variable names still contain `JWT_SECRET` and `FIRST_ADMIN_PASSWORD`.
- The verifier currently checks only direct value env vars with
  `grep -E '^(JWT_SECRET|FIRST_ADMIN_PASSWORD)='`, so it passed while the
  directive's broader grep would fail.

Recommended fix before tag:

- Remove `JWT_SECRET_FILE` and `FIRST_ADMIN_PASSWORD_FILE` from container env.
- Teach `backend/app/config.py` to default to the Docker secret paths
  `/run/secrets/jwt_secret` and `/run/secrets/first_admin_password` when direct
  legacy env vars are absent.
- Keep local/non-container unit-test configurability with explicit constructor
  fields or alternate non-secret-named settings only if needed.
- Update `scripts/verify-release.sh` and the contract test to use the literal
  acceptance command from this rehearsal.

## Phase 2 Gate Result

Phase 2 is not approved for tag push.

Next action: open a follow-up Phase 1B PR to satisfy the exact env-grep
criterion, then rerun Phase 2 rehearsal.
