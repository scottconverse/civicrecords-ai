# <PROJECT_NAME> Audit Gate - Read Every Time

This is the short mandatory gate for <PROJECT_NAME> audit, <IMPLEMENTER_AGENT>/<AUDITOR_AGENT> report verification, release-gate, merge/tag-readiness, and directive-writing work. Read this file completely before answering. Do not rely on chat memory.

Long reference protocol:

`<AUDIT_PROTOCOL_PATH>`

Implementation-side rule (shared by both <IMPLEMENTER_AGENT> and <AUDITOR_AGENT>, lives in the <PROJECT_NAME> repo so it ships with the code):

`docs/process/5-lens-self-audit.md` on `main`. The protocol's section 22 ("Known drift patterns") is the running catalog of patterns audits have found; reference it by entry number when surfacing drift.

## Required Output

Every <PROJECT_NAME> verification answer is incomplete unless it includes:

1. Verdict.
2. Claim Verification Matrix.
3. Durable Artifact Reads.
4. Substantive Content Checks.
5. Drift Matrix.
6. Working Tree And Live Remote State.
7. Unreported Catches.
8. Open Caveats / Release Risks.
9. Paste-Ready Directive.
10. Recommended Next Action.

## Required Evidence

Before final answer, verify or explicitly mark unavailable:

- local git: branch, HEAD, dirty state, local-vs-origin parity;
- GitHub/PR: PR state, head SHA, merge state, body, checks;
- CI/logs/artifacts: run IDs, head SHAs, actual proof lines, artifacts when available;
- durable docs: HANDOFF, ledger, CHANGELOG/release docs/spec docs affected by the report;
- changed code/tests when the report claims behavior changed.

Do not accept green checks as proof without inspecting logs for the claimed behavior. Do not accept "file exists" as content verification.

## Directive Standard

Section 9 is mandatory. It must be paste-ready and include:

- current branch/SHA/PR context;
- exact file paths;
- searchable bad text/code;
- replacement text/code or explicit edit instructions;
- commands to run;
- proof output to paste;
- acceptance criteria;
- halt triggers;
- forbidden claims/actions;
- what remains out of scope.

If the immediate cleanup is complete or nearly complete, also include the next-phase no-wiggle directive that prevents the next predictable drift loop. Do not stop at "standing by."

## Final Self-Check

Do not send the final answer until every line is true:

- I read this gate this turn.
- I verified live git/GitHub/CI/artifacts where available.
- I read durable docs.
- I produced the 10-section packet, or the director explicitly asked for a narrow answer.
- I gave exact fixes, not vague advice.
- I included a paste-ready directive.
- If the branch is clean enough to proceed, I included the next-phase no-wiggle directive.
- I shortened narrative before shortening the directive.

If any line is false, finish the missing work before answering.
