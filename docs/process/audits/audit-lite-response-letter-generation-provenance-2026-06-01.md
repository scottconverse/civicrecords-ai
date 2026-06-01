# Audit Lite - Response Letter Generation Provenance
**Date:** 2026-06-01
**Scope:** Reviewed the C1 CivicRecords AI diff that exposes response-letter generation source/model and adds focused LLM success/fallback tests.
**Reviewer:** Codex (audit-lite)

## TL;DR
Ship this slice. The change makes successful Ollama response-letter drafts distinguishable from local-template fallback, which is the missing signal the city-core installer proof needs. No findings remain from this lite pass.

## Severity rollup
- Blocker: 0
- Critical: 0
- Major: 0
- Minor: 0
- Nit: 0

## Findings
None.

## What's working
- `C:\dev\Claude\civicrecords-ai-stage2-response-letter\backend\app\requests\router.py:992` now returns content/source/model from successful Ollama generation instead of an untyped string.
- `C:\dev\Claude\civicrecords-ai-stage2-response-letter\backend\app\schemas\request.py:148` exposes `generation_source` and `generation_model` without a database migration, preserving existing stored letters.
- `C:\dev\Claude\civicrecords-ai-stage2-response-letter\backend\tests\test_response_letter.py:97` proves the success path reports `ollama` and the configured model, while the existing timeout test still proves fallback returns `None`.

## Runtime
- `python -m pytest backend/tests/test_response_letter.py::test_response_letter_llm_timeout_falls_back_to_template backend/tests/test_response_letter.py::test_response_letter_llm_success_reports_generation_source -q`
- Result: 2 passed.

## Escalation recommendation
No escalation needed for this slice. The broader city-core gate remains under the independent audit-team package.
