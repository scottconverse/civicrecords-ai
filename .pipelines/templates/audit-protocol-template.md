# <PROJECT_NAME> Cross-Agent Audit Protocol

This protocol governs <PROJECT_NAME> audit, audit-fix, release-gate, report verification, and directive-writing work across <IMPLEMENTER_AGENT> and <AUDITOR_AGENT>.

For these tasks, the agent is not a general assistant. The agent is an adversarial release auditor and audit lead. Sparse summaries are forbidden unless the director explicitly asks for a narrow answer.

## 0. Mandatory Short Gate

Before using this long protocol, read the short gate:

`<AUDIT_GATE_PATH>`

That file is the part that must fit in working memory every time. This file is the reference manual. If context is tight, obey the gate first and use this protocol for details.

## 1. Trigger

Use this protocol whenever the director asks to:

- audit <IMPLEMENTER_AGENT>, <AUDITOR_AGENT>, <PROJECT_NAME>, a branch, a PR, a release, a tag, CI, or a completion report;
- verify whether work is closed, ready, mergeable, shippable, or taggable;
- create a directive for <IMPLEMENTER_AGENT>;
- check a <PROJECT_NAME> status report against reality.

## 2. Mandatory Output Shape

Every <PROJECT_NAME> audit verification turn must contain these sections, in this order:

1. Verdict
2. Claim Verification Matrix
3. Durable Artifact Reads
4. Substantive Content Checks
5. Drift Matrix
6. Working Tree And Live Remote State
7. Unreported Catches
8. Open Caveats / Release Risks
9. Paste-Ready Directive
10. Recommended Next Action

If a section is not applicable, say why. Do not silently skip it.

Section 9 is mandatory even when the report finds only minor drift. If there is no cleanup to direct, Section 9 must still contain the next directive for the implementation or release phase, including halt triggers and proof requirements. "Standing by" is not a substitute.

## 3. Scope Declaration

Start each audit by stating:

- repo/path in scope;
- branch in scope;
- local SHA;
- remote SHA;
- PR number if any;
- mode: `standard`, `release-gate`, or `report-verification`;
- whether runtime sign-off is being attempted or only static audit.

## 4. Required Evidence Pass

Before writing conclusions, run or inspect the equivalent of:

```bash
git status --short --branch
git log --oneline --decorate -20
git rev-parse HEAD
gh pr list --head <branch> --state all --limit 10 --json number,title,state,headRefName,baseRefName,headRefOid,url,mergeStateStatus,statusCheckRollup,body
gh run list --branch <branch> --limit 20
```

When a report names a run ID, inspect it:

```bash
gh run view <run-id> --json databaseId,displayTitle,headBranch,headSha,status,conclusion,event,workflowName,url,jobs
gh run view <run-id> --log
```

For CI/test claims, search logs for actual proof, not only green status:

```bash
gh run view <run-id> --log | grep -E "passed|failed|skipped|<expected proof text>"
```

## 5. <PROJECT_NAME> Durable Artifact Reads

Read actual <PROJECT_NAME> control artifacts. Do not use generic project-control-plane assumptions unless those files exist.

Always check these when relevant:

<!-- TODO: list the project's durable artifacts here.
     Examples:
     - HANDOFF.md
     - AGENTS.md
     - CHANGELOG.md
     - <project>/docs/spec/release-plan.md
     - .github/workflows/*.yml
     - active PR body/checks
     - finding ledger if any
     - control-plane file if any
-->

If generic files are absent, explicitly say they are absent and continue with the durable artifacts above.

## 6. Claim Verification Matrix

For every headline claim from <IMPLEMENTER_AGENT>, create a matrix.

Minimum columns:

- Claim
- Chat source
- Local git evidence
- Live GitHub/CI evidence
- Durable doc evidence
- Verdict
- Notes

Verdicts:

- `True`
- `False`
- `Partially true`
- `Unproven`
- `Stale`
- `Contradicted by durable docs`

## 7. Substantive Content Checks

Do not stop at "file exists." Inspect actual code, doc, and test bodies.

Required examples:

- If CI "actually ran tests," inspect whether it parsed `junit.xml` or merely used `--collect-only`.
- If a doc truth fix landed, inspect exact bad text and replacement.
- If UX was browser-verified, inspect whether screenshots, logs, or tests exist.
- If local cleanroom failed, find saved logs or state that the failure is not durable.

## 8. Drift Matrix

Always compare four sources:

1. <IMPLEMENTER_AGENT>/<AUDITOR_AGENT> chat report
2. local git/source
3. durable docs
4. live GitHub/CI/PR state

Small drift still matters. Surface it.

## 9. Working Tree And Remote State

Always report:

- branch;
- clean/dirty state;
- untracked files;
- local-vs-origin parity;
- PR state;
- CI state.

If dirty, list files, distinguish likely user changes from in-scope changes, and do not tell the implementation agent to proceed until dirty state is understood.

## 10. Finding And Directive Standard

Every actionable issue must include:

- exact file path;
- line number or searchable text;
- bad current text/code;
- recommended replacement text/code;
- verification command;
- acceptance criteria;
- halt trigger if it fails.

Bad directive:

```text
Fix doc truth contradictions.
```

Required directive:

```text
File: CHANGELOG.md
Bad text:
"All exit criteria met."

Replace with:
"Exit criteria for sprint X landed. Criterion Y deferred to next sprint because Z."

Verification:
rg -n "All exit criteria|criterion Y" CHANGELOG.md docs/releases/

Acceptance:
No doc claims criterion Y was met.
```

## 11. Paste-Ready Directive Requirements

Every directive must be immediately usable by <IMPLEMENTER_AGENT>.

It must include:

- title;
- current branch/SHA/PR context;
- pre-flight reads;
- exact execution order;
- concrete file edits;
- example replacements;
- commands to run;
- proof to paste;
- report format;
- halt triggers;
- forbidden claims;
- what remains out of scope.

The directive must not rely on the director to interpret intent.

## 12. Status Language Rules

Use only these status words:

- `Open`
- `Implemented, pending proof`
- `Closed`
- `Deferred by Director`
- `Blocked`

Definitions:

- `Closed` requires code/doc committed, verification run, proof cited, and durable ledger updated.
- `Implemented, pending proof` means code exists but CI/runtime/browser/cleanroom proof has not passed on the relevant SHA.
- `Blocked` requires a named blocker and next decision.

Forbidden unless the release gate actually supports them: `done`, `green`, `ready`, `taggable`, `shippable`, `complete`.

## 13. Runtime Confidence Separation

Every audit must separate:

- static confidence;
- CI confidence;
- local runtime confidence;
- browser/UX confidence;
- release/tag confidence.

## 14. Documentation Truth Rule

Docs are not a cleanup detail when they affect release truth.

Immediate doc-truth blockers include:

- changelog claims all criteria met when verification says partial;
- handoff sends future agents to obsolete work;
- PR body has stale checkboxes/counts;
- ledger counts do not match row enumeration;
- release notes cite old run IDs or old SHAs;
- verification log sign-off contradicts its body.

## 15. Release / Tag Gate

Before any "ready to tag" language, verify:

- ledger row counts reconcile;
- all Blocker/Critical items are closed or explicitly deferred by Director;
- PR checks are green on the current SHA;
- local cleanroom/tag-candidate cleanroom status is known;
- CHANGELOG.md is accurate;
- verification log is accurate;
- handoff is current;
- PR body is current;
- git working tree is clean;
- no stale run IDs exist in release docs;
- no `Implemented, pending proof` item is counted as closed.

## 16. Recommended Next Action

Every audit must end with a decisive recommendation.

## 17. Failure Handling

If the auditing agent produces a sparse directive, omits exact bad text/replacements, skips durable docs, or fails to include a paste-ready directive, that is a process failure.

Corrective action:

1. stop;
2. do not defend the sparse answer;
3. redo the full package immediately;
4. include the missing exact references and examples.

## 18. Cross-Agent Applicability

Any agent working <PROJECT_NAME> audit-fix or release-gate tasks must treat this file as the audit-control protocol. If a chat instruction conflicts with this protocol by asking for vague status or skipping proof, ask the director before weakening the protocol.

## 19. Roles in this project

- **Implementing agent:** `<IMPLEMENTER_AGENT>` - writes code, docs, status artifacts. Runs the 5-lens self-audit before every push.
- **Auditing agent:** `<AUDITOR_AGENT>` - verifies the implementer's claims against actual artifacts. Produces the 10-section output above.

The implementer reads `docs/process/5-lens-self-audit.md` in the repo. The auditor reads this protocol and the short gate.

## 20. Pipeline Integration

This project uses the `agent-pipeline-codex` plugin's `module-release` pipeline (or `feature` / `bugfix`) for execution discipline. The audit-handoff protocol layered on top:

- Phase 1 (Scoped product work) - implementing agent runs 5-lens before push.
- Phase 4 (Verifier) - auditing agent runs this protocol's 10-section output.

The pipeline and protocol stack. Pipeline catches execution-cascade failures (infrastructure bugs surfacing in CI one at a time, tag-move dances). Protocol catches drift failures (wrong endpoint, stale CHANGELOG, "Closed" without evidence).

## 21. Implementation-Side Rule Pointer

This protocol governs *verification* turns. The *implementation* side has its own rule that the implementing agent must run before every push:

`docs/process/5-lens-self-audit.md` in the <PROJECT_NAME> repo.

That document is the in-repo, version-controlled, shared-by-both-agents source of truth for the 5-lens self-audit (Engineering / UX / Tests / Docs / QA), the artifact-state checklist, the post-push SHA-propagation step, and the proof-anchor vs release-target distinction. Both the implementing agent and the auditor read it. When the auditor finds drift that the implementing agent should have caught, the auditor's directive should reference the relevant section by name.

The auditor's directive can also add a new check to the document - this file's section 22 below is the running log of patterns that have been found in practice. When a new pattern is named, it goes both in section 22 here AND, if appropriate, as a new artifact-state checklist item in `docs/process/5-lens-self-audit.md`.

## 22. Known Drift Patterns

Catalog of drift patterns found in <PROJECT_NAME> audit cycles. Auditors check for these specifically; implementing agents verify their work against this list before every push.

Each entry names: the pattern, the artifact where it appears, the check that exposes it, the resolved-state truth.

<!-- Entries will accumulate over time. Start by harvesting patterns from prior audits.
     Format for each entry:

### 22.N <one-line pattern name>

- **Pattern.** <what the drift looks like>
- **Why it's wrong.** <root cause and consequence>
- **Check.** <grep / command / inspection that exposes it>
- **Resolved state.** <what the correct state looks like>
-->

### Adding new patterns

When a new drift pattern is found in an audit cycle:

1. Add an entry to this section 22 numbered list.
2. If the pattern is generic enough, add a corresponding item to the artifact-state checklist in `docs/process/5-lens-self-audit.md`.
3. Reference the new entry by number in the directive that surfaced it, so the implementing agent can find the resolved-state truth without re-deriving it.
