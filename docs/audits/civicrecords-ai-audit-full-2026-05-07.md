# CivicRecords AI Audit Full - 2026-05-07

## 1. Executive Audit

Scope: `C:\Users\scott\OneDrive\Desktop\Claude\civicrecords-ai`, local checkout and live `origin/master`.

Mode: release-recovery gate, active cleanup branch `recovery/records-release-truth-gates`.

Local-vs-live parity: before cleanup, local `HEAD` and `origin/master` both resolved to `3b1f38c3d88050c1cf299cf8254eedf65f58a52a`.

Static audit confidence: Medium-high. Runtime sign-off confidence before fixes: Low. The repo is functionally richer than scaffold modules, but its public release story and release gate were not strong enough for the claims attached to `v1.4.10`.

Headline judgment: CivicRecords AI has substantial engineering work, but `v1.4.10` must stay provisional/do-not-promote until the new gates pass on this branch and on GitHub CI.

## 2. Audit Coverage Ledger

| Area | Status | Evidence |
| --- | --- | --- |
| Engineering | Checked | App routes, backend layout, manifests, release script, CI workflow. |
| Security/auth | Checked | `.env` tracking check, dependency audit, secret-scan gap. |
| UI/UX | Partially checked | Frontend source and Vitest suite checked; Playwright user-flow gap identified and fixed in this branch. |
| Product/PM | Checked | Public claim surfaces and v1.4.10 status checked. |
| Documentation | Checked | README, CHANGELOG, USER-MANUAL, docs index, unified spec claim drift. |
| Install/bootstrap | Partially checked | Existing release script lacked runtime install proof; fixed with new proof script. |
| Version/release | Checked | Version lockstep existed, but release-status semantics were misleading. |
| Test engineering | Checked | Docker collection reported 633 backend tests; frontend Vitest reported 36 tests passing after WSL dependency refresh. |
| Runtime QA | Partially checked | Existing release gate failed when stack was not running; gate now provisions required stack services. |

## 3. Claim Verification Matrix

| Claim | Result | Evidence |
| --- | --- | --- |
| `v1.4.10` is ready to promote | False | README and CHANGELOG already call it historical pre-gate/do-not-promote; docs index still linked installers prominently. |
| Backend count is 631 tests | Stale | Auditor-run WSL Docker collection found 633 tests collected. |
| Browser QA proves user flows | False before fix | No tracked Playwright config/spec existed; browser QA was mostly prose/static evidence. |
| Release gate proves release readiness | False before fix | `scripts/verify-release.sh` lacked frontend tests, Playwright, npm audit, secret scan, runtime install proof, and recovery claim enforcement. |
| Frontend build and unit tests pass | True after provisioning | WSL `npm ci`, `npm test -- --run`: 36 passed; `npm run build`: success. |
| No frontend vulnerabilities | False before fix, true after dependency cleanup | Unused `shadcn` pulled vulnerable `ip-address`; removing it cleared `npm audit`. |

## 4. What The Dev Team Needs To Do Now

1. Keep `v1.4.10` provisional/do-not-promote.
2. Merge only after release recovery gates pass locally and in CI.
3. Do not create another public release until Playwright, runtime install proof, security scan, docs-source enforcement, and full backend/frontend checks pass.
4. Restore/install the missing `coder-ui-qa-test` skill or update repo process docs to match the actual installed skill set.

## 5. Next-Sprint Watchlist

- Reduce the large frontend bundle through route-level splitting after recovery gates are stable.
- Reconcile generated binary docs with source-of-truth docs or remove them from mandatory release surfaces.
- Decide whether CivicRecords AI should target CivicCore v1.0.0 or stay pinned to v0.22.1 for this recovery release.

## 6. Engineering Deep Dive

Finding ENG-001

Severity: Critical. Confidence: High. Evidence type: Mixed. Status: Durable defect.

Why it matters: Release verification did not verify the release. It checked sovereignty, version strings, required docs, and ruff, but skipped core backend runtime proofs, frontend tests, browser flows, security audit, and package install.

Evidence: `scripts/verify-release.sh` before this branch lacked calls to Playwright, `npm audit`, frontend test/build, secret scan, and runtime install proof.

Blast radius: Every tag or release relying on that script.

Fix: Harden `scripts/verify-release.sh` with recovery, security, frontend, Playwright, backend, Docker, and runtime install checks.

## 7. Security And Authorization Deep Dive

Finding SEC-001

Severity: Critical. Confidence: High. Evidence type: Static. Status: Durable defect.

Why it matters: The frontend dependency tree included vulnerable `ip-address` through unused `shadcn`.

Evidence: Auditor-run `npm audit --audit-level=moderate --json` reported `GHSA-v2v4-37r5-5v8g`.

Blast radius: Frontend dependency trust and release security posture.

Fix: Remove unused `shadcn`; enforce `npm audit --audit-level=moderate` in release gate.

Finding SEC-002

Severity: Critical. Confidence: Medium. Evidence type: Static. Status: Needs confirmation after cleanup lands.

Why it matters: A local untracked `.env` contains real runtime values. It is ignored and not tracked, but the release process lacked a tracked-file secret scan that would block accidental commits.

Evidence: `.gitignore` ignores `.env`; `git ls-files .env` returned no tracked file; no secret-scan gate existed before this branch.

Blast radius: Credential hygiene for future commits.

Fix: Add tracked-file secret scan and fail if `.env` becomes tracked.

## 8. UI/UX Deep Dive

Finding UX-001

Severity: Critical. Confidence: High. Evidence type: Static. Status: Durable defect.

Why it matters: Public release claims referenced browser QA, but there were no tracked Playwright user-flow tests proving desktop/mobile flows.

Evidence: No `frontend/playwright.config.ts` or `frontend/e2e` specs existed before this branch.

Blast radius: Any claim that UX was browser-flow verified.

Fix: Add real Playwright tests for staff dashboard and resident request submission with desktop/mobile projects.

## 9. Product/PM Deep Dive

Finding PM-001

Severity: Blocker. Confidence: High. Evidence type: Static. Status: Durable defect.

Why it matters: Public release surfaces mixed honest do-not-promote text with strong completeness and installer promotion language.

Evidence: `docs/UNIFIED-SPEC.md` said `v1.4.10` was "substantially complete" and "well beyond a simple MVP"; docs index used "production-ready" language.

Blast radius: Public trust, city procurement expectations, and release honesty.

Fix: Freeze claims, mark `v1.4.10` provisional/do-not-promote, and gate readiness language through docs-source enforcement.

## 10. Documentation Deep Dive

Finding DOC-001

Severity: Critical. Confidence: High. Evidence type: Mixed. Status: Durable defect.

Why it matters: Test-count evidence was stale by the repo's own executable suite.

Evidence: WSL Docker `pytest --collect-only` reported 633 tests; docs claimed 631.

Blast radius: Release notes, unified spec, README trust.

Fix: Update public test-count claims or remove exact counts unless generated by a gate.

## 11. Install / Bootstrap / Seeding Deep Dive

Finding BOOT-001

Severity: Critical. Confidence: High. Evidence type: Static. Status: Durable defect.

Why it matters: There was no isolated wheel install proof in the release gate, despite release notes implying fresh install confidence.

Evidence: `scripts/verify-release.sh` did not build/install the backend package before this branch.

Blast radius: New-user install confidence.

Fix: Add `scripts/verify-runtime-install.py` and call it from the release gate.

## 12. Version And Release Consistency Deep Dive

Finding REL-001

Severity: Critical. Confidence: High. Evidence type: Static. Status: Durable defect.

Why it matters: Version lockstep existed, but semantic release status was inconsistent: a do-not-promote version was still presented as a normal download target.

Evidence: `README.md` was honest; `docs/index.html` still linked `v1.4.10` installer downloads in the primary CTA area.

Blast radius: Public release communications.

Fix: Change public CTA language to historical/provisional and require recovery status.

## 13. Test Engineering Deep Dive

Finding TEST-001

Severity: Critical. Confidence: High. Evidence type: Mixed. Status: Durable defect.

Why it matters: A release gate that does not run the frontend suite, browser flows, or dependency audit can certify a broken frontend.

Evidence: Baseline `verify-release.sh` skipped these checks; direct WSL frontend checks initially failed until `npm ci` repaired optional Rollup dependencies.

Blast radius: All frontend release claims.

Fix: Add frontend install/test/build/audit/Playwright commands to `scripts/verify-release.sh`.

## 14. Runtime QA Deep Dive

Finding QA-001

Severity: Critical. Confidence: High. Evidence type: Runtime. Status: Durable defect.

Why it matters: The release gate failed when the API stack was not already running, instead of provisioning the runtime it required.

Evidence: Auditor-run `bash scripts/verify-release.sh` failed sovereignty because API was not running/bound.

Blast radius: Local release confidence and reproducibility.

Fix: Have the release gate start the required compose stack before sovereignty checks.

## 15. Cross-Cutting Synthesis

CivicRecords AI is not a scaffold; it has substantial backend/frontend implementation and a meaningful test suite. The failure is release trust: strong public claims outran machine-enforced evidence. The recovery fix is to turn that trust layer into code: claim scanners, security scanners, Playwright flows, runtime install proof, and Docker-backed release gates.

## 16. Verification Gaps And Sign-Off Limits

This audit is not a final product-ready sign-off. It is the recovery audit for closing the obvious public-claim and release-gate defects. Final sign-off requires the updated full gate to pass locally and on GitHub CI after this branch is pushed.
