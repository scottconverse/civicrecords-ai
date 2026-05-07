# CivicRecords AI Release Recovery Status

Date: 2026-05-07

## Public Claim Freeze

CivicRecords AI `v1.4.10` is a historical, provisional, do-not-promote release. It must not be described as product-ready, production-ready, or fully complete until a new release earns that status through the recovery gates below.

Existing tags remain part of the public record, but release status is provisional until revalidated.

## Gates Required To Re-Earn Release Status

- Real Playwright user-flow tests at desktop and mobile widths.
- Runtime install proof from a freshly built wheel in an isolated virtual environment.
- Full backend test collection and execution with collected/pass count checked.
- Frontend unit tests and production build.
- `npm audit --audit-level=moderate`.
- Tracked-file secret scan.
- Documentation-source enforcement for public readiness claims.
- Explicit mock-vs-production labeling in QA evidence.
- Release-gate audit with no unresolved Blocker or Critical findings.

## Mock-vs-Production Label

Current Playwright evidence is `MOCK-LABELED`: browser user flows use deterministic local API mocks and prove rendered user behavior, routing, validation, success, and keyboard shell behavior. It is not external deployment proof.

Runtime install evidence is `LOCAL-RUNTIME`: the backend package is built, installed into a fresh virtual environment, imported, and queried through FastAPI `TestClient`.

Docker evidence is `LOCAL-COMPOSE`: the local Docker Compose stack is provisioned and checked by the release gate.
