# Audit Lite - Response Letter Timeout And Keep-Alive
**Date:** 2026-06-01
**Scope:** Reviewed the Records AI response-letter LLM timeout/keep-alive fix in `backend/app/config.py`, `backend/app/requests/router.py`, and `backend/tests/test_response_letter.py`.
**Reviewer:** Codex (audit-lite)

## TL;DR
Ship this scoped fix. The previous 8-second LLM request budget could not produce a CPU-hosted `gemma4:e4b` response letter, so the provenance gate correctly observed template fallback. The new 120-second bounded request budget plus `keep_alive=30m` keeps the anti-hang property while allowing realistic CPU generation.

## Severity rollup
- Blocker: 0
- Critical: 0
- Major: 0
- Minor: 0
- Nit: 0

## Findings

None.

## What's working
- `backend/app/config.py` keeps the response-letter call bounded at 120 seconds and adds an explicit `ollama_keep_alive` setting.
- `backend/app/requests/router.py` sends `keep_alive` in the Ollama `/api/generate` request, so prewarmed models are not immediately discarded before the installer proof path.
- `backend/tests/test_response_letter.py` now asserts successful LLM generation includes the configured keep-alive value while preserving the timeout fallback test.
- Focused verification passed: `python -m pytest backend/tests/test_response_letter.py::test_response_letter_llm_timeout_falls_back_to_template backend/tests/test_response_letter.py::test_response_letter_llm_success_reports_generation_source -q` -> 2 passed.

## Watch items

Clean-VM re-gate still has to prove the real Docker/Ollama path returns `generation_source=ollama` with `gemma4:e4b`; this audit only covers the scoped code diff and focused unit behavior.

## Escalation recommendation

No escalation needed for this scoped Records AI diff. The independent clean-VM re-gate remains the release evidence gate.
