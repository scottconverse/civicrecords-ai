# Browser QA - CivicCore v1.0.1 Migration (v1.5.0)

Date: 2026-05-10

## Scope

This run validates that the existing user-facing CivicRecords AI shell still renders after migrating the backend package dependency from CivicCore v0.22.1 to CivicCore v1.0.1 and bumping CivicRecords AI to v1.5.0.

## Harness Status

No dedicated `scripts/browser-qa*` or `scripts/cdp*` harness exists in this repository for the requested public intake, staff login, audit-verify, and search walkthroughs. The required PF9 inventory returned no harness files.

Because no dedicated browser-QA screenshot harness exists, this evidence uses the repository's enforced Playwright e2e suite from `frontend/e2e/civicrecords-user-flows.spec.ts`. The Playwright suite is mock-labeled and runs at both desktop and mobile widths. It does not capture screenshots on passing runs because `frontend/playwright.config.ts` is configured with `screenshot: "only-on-failure"`.

## Verified Flows

- Desktop staff shell: dashboard loads, service status cards render, and the skip link receives keyboard focus.
- Mobile staff shell: dashboard loads and the primary navigation dialog opens and closes.
- Desktop resident public request: empty submission shows actionable validation, valid submission succeeds, and the tracking ID renders.
- Mobile resident public request: same validation and success path as desktop.

## Command

```bash
cd frontend
npm run test:e2e
```

## Result

```text
4 passed
```

## Caveats

- This is mock-labeled browser evidence, not an external deployment proof.
- The repository currently has no dedicated screenshot harness for the requested v1.5.0 migration walkthrough. Add a dedicated browser-QA harness before the next product-readiness claim that requires saved desktop/mobile screenshots for public intake, staff admin login, audit verification, and search.
- Empty-database or Ollama-missing search failures remain out of scope for this migration and are tracked separately by the audit packet.
