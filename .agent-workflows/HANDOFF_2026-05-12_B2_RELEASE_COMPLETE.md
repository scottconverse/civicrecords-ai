# CivicRecords AI B2 Release Completion Handoff

Date: 2026-05-12
Scope: Audit punch-list B2 security-secret handling recovery
Status: Complete - v1.6.0 release published and suite truth reconciled

This handoff supersedes `HANDOFF_2026-05-11_B2_COMPLETE.md`, which stopped at
the pre-tag approval gate.

## Landed Work

| Slice | PR | Merge SHA | Notes |
| --- | --- | --- | --- |
| Phase 1 | #74 | `902db173366359124e4d8e84f3c440df61aa62f4` | Moved raw secret material into Docker secret files. |
| Phase 1B | #76 | `5e7425dc7a226f63a4ba8a91aa76cb30491c03ef` | Removed `_FILE` pointer env names and tightened verifier/test predicate. |
| Phase 2 artifact | #77 | `f2432c14a9afd06f7577ba090d884a0e9375cb4a` | Committed GREEN pre-tag rehearsal evidence. |
| Release workflow recovery | #78 | `fcb1f8301c95025aac5e31329acd3179055c2a26` | Removed stale `_FILE` env synthesis from release workflow. |

## Release

- Release: https://github.com/CivicSuite/civicrecords-ai/releases/tag/v1.6.0
- Release workflow run: `25719121452`
- Final tag object: `1c60fc7a7deb9671f150e4445da51fce0019d93b`
- Final tag target: `fcb1f8301c95025aac5e31329acd3179055c2a26`

## Tag-Move Record

| Tag | Initial target | Final target | Moves | Notes |
| --- | --- | --- | ---: | --- |
| v1.6.0 | `f2432c14a9afd06f7577ba090d884a0e9375cb4a` | `fcb1f8301c95025aac5e31329acd3179055c2a26` | 1 | Moved once to include PR #78, a CI-only workflow `.env` synthesis fix. Product code unchanged. |

## Asset SHA256s

```text
5d4d55edc4a030ab86068ff3ab578ea97f5e7b2a5982c90ba302752e0f1d9022  CivicRecordsAI-1.6.0-Setup.exe
```

GitHub asset digests:

```text
sha256:5d4d55edc4a030ab86068ff3ab578ea97f5e7b2a5982c90ba302752e0f1d9022  CivicRecordsAI-1.6.0-Setup.exe
sha256:d54e5b4f541035fd5a66271eedd0542a20b27dffec72ff6682bddeccd6f2d8bd  CivicRecordsAI-1.6.0-Setup.exe.sha256
sha256:0d6fa94759c939d8eb41a86ac6b389c7a88d50558cc19a42efc43dc0ced6405a  release-attestation.json
sha256:3ba1c2caea0fcc83ec6b94eb8bb1aadb2e53093a7188523af6e5dd35cbf22f97  release-attestation.json.bundle
```

## Phase 2 Acceptance Proof

```text
VERIFY-RELEASE: PASSED
[PASS] api container env hides JWT_SECRET and FIRST_ADMIN_PASSWORD (literal directive grep)
[PASS] pytest collect-only: 638 test(s)
[PASS] pytest full suite: 638 passed
RUNTIME-INSTALL-PROOF: health {'status': 'ok', 'version': '1.6.0'}
RUNTIME-INSTALL-PROOF: PASSED
```

Literal B2 command:

```bash
docker compose exec -T api env | grep -E 'JWT_SECRET|FIRST_ADMIN_PASSWORD'; echo exit=$?
```

```text
exit=1
```

## Suite Truth

- Umbrella PR: CivicSuite/civicsuite#128
- Umbrella merge SHA: `07544e01ec285a2116e63c76075d224136b8c3c0`
- `release-lockstep-gate`: passed
- Post-merge `python scripts/verify-suite-state.py --remote-only`: passed all 26 modules with CivicRecords AI at 1.6.0.

## Five-Lens Self-Audit

- Engineering: pass. Runtime secret material is file-backed, raw and `_FILE`
  secret names are absent from the container env, and v1.6.0 release truth is
  reconciled in CivicSuite.
- UX: pass. No frontend surfaces changed; operator behavior is clearer and safer
  because `docker exec env` no longer surfaces secret material or pointer names.
- Tests: pass. Release verifier, contract tests, full pytest, frontend tests,
  Playwright flow, release workflow, umbrella gate, and remote suite verifier all
  passed at the relevant phase.
- Docs: pass. CivicRecords AI docs were updated in Phase 1/1B, and CivicSuite
  release truth plus handoffs now record the release.
- QA: pass. The original predicate gap and later umbrella lifecycle gap were both
  caught by verification and fixed before final closure.
- Artifact-state: pass. v1.6.0 release assets exist with full SHA256 digests.
- Post-push propagation: pass. Suite truth PR #128 merged and remote verifier
  observes CivicRecords AI 1.6.0.

## Next Work

The next CivicSuite active target is tracked in the umbrella control plane:
Installer/macOS certification follow-up.
