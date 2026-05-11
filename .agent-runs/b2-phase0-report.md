# Phase 0 Preflight Audit - CivicSuite/civicrecords-ai

Result: 3/6 checks passed

## workflow YAML parse - PASS
  PASS .github\workflows\ci.yml
  PASS .github\workflows\release-preflight.yml
  PASS .github\workflows\release.yml

## workflow recent run health - FAIL
  Release: 2/3 failed
  CI: 0/5 failed
  pages build and deployment: 0/2 failed
  FAIL - workflows with >=60% failure rate: Release (2/3)

Accepted Phase 0 review decision: historical v1.5.0 recovery runs dominate the
3-run heuristic. The latest Release run is green, so no bundled Phase 0
infrastructure-fix PR is required for this finding.

## referenced scripts exist - FAIL
  FAIL - missing or empty: scripts/generate_openapi.py

Accepted Phase 0 review decision: preflight v0.1 strips the container
working-directory context. The real script exists at
backend/scripts/generate_openapi.py and CI runs it from inside the backend
container as scripts/generate_openapi.py.

## local verify-release.sh on fresh state - PASS
  --run-local not set; skipping local execution. When --run-local is set, this
  check wipes docker state, synthesizes a CI-shape .env, and runs the verifier.

## cross-platform reality check - FAIL
  FAIL
  release.yml: ubuntu-latest job with Inno Setup compile (Windows-only)

Accepted Phase 0 review decision: preflight v0.1 scans the whole workflow file
instead of job scope. Inno Setup is correctly inside the windows-latest
build-windows-installer job.

## diagnostic instrumentation on failure - PASS
  PASS - script dumps container logs somewhere

## scope decision

CivicClerk is excluded from the B2 sprint. Phase 0 grep found no
JWT_SECRET/FIRST_ADMIN_PASSWORD runtime surface in civicclerk's Docker Compose
stack; it only found different CivicClerk-specific optional secrets.
