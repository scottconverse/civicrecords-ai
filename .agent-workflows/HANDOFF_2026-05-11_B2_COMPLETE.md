# CivicRecords AI B2 Pre-Tag Handoff

Date: 2026-05-11
Active target: Audit punch-list B2 security-secret handling recovery
Status: Phase 2 GREEN - awaiting Scott approval before any v1.6.0 tag push

## Scope

Move `JWT_SECRET` and `FIRST_ADMIN_PASSWORD` material out of recoverable
container environment variables for CivicRecords AI. The final Phase 1B slice
also removed the `_FILE` pointer env names so the directive's literal command
matches zero container env lines.

## Landed Work

| Slice | PR | Merge SHA | Notes |
| --- | --- | --- | --- |
| Phase 1 | #74 | 902db173366359124e4d8e84f3c440df61aa62f4 | Moved raw secret material into Docker secret files. |
| Phase 1B | #76 | 5e7425dc7a226f63a4ba8a91aa76cb30491c03ef | Removed `_FILE` pointer env names and tightened verifier/test predicate. |

## Phase 2 Evidence

Rehearsal artifact:

```text
civicrecords-ai/.agent-runs/b2-phase2-rehearsal.md
```

Master HEAD:

```text
5e7425dc7a226f63a4ba8a91aa76cb30491c03ef
```

Release verifier:

```text
VERIFY-RELEASE: PASSED
```

Literal B2 acceptance command:

```bash
docker compose exec -T api env | grep -E 'JWT_SECRET|FIRST_ADMIN_PASSWORD'; echo exit=$?
```

Output:

```text
exit=1
```

Contract test:

```text
tests/test_docker_secret_contract.py::test_env_example_declares_no_b2_secret_env_names PASSED
tests/test_docker_secret_contract.py::test_compose_mounts_secrets_via_docker_secret_block PASSED
tests/test_docker_secret_contract.py::test_release_gate_uses_literal_directive_grep PASSED
3 passed in 0.04s
```

Collect-only:

```text
638 tests collected in 1.62s
```

## Tag-Move Record

| Tag | Initial SHA | Final SHA | Moves | Notes |
| --- | --- | --- | --- | --- |
| v1.6.0 | not pushed | not pushed | 0 | tag push awaiting Scott approval |

## Important Local Runtime Note

Use Git Bash from the Windows working tree for the release rehearsal on this
machine:

```text
C:\Program Files\Git\bin\bash.exe scripts/verify-release.sh
```

PowerShell's default `bash.exe` enters WSL through Docker's bind-mount path,
which changes the Compose project name and can exercise stale project-specific
images. The successful Phase 2 proof used Git Bash.

## Next Authorized Step

Stop here and ask Scott before Phase 3.

On approval, the next session should push `v1.6.0`, wait for the release
workflow, then open the umbrella release-truth PR for:

- `installer/modules.json`
- `docs/CivicSuiteUnifiedSpec.md`
- `docs/compatibility/index.md`
- `docs/release-recovery-status.md`
- `docs/release-lockstep/downstream-pins.md`
- `CHANGELOG.md`
- `scripts/verify-suite-state.py`

No tag has been pushed. No release has been created. No umbrella release-truth
PR has been opened.
