# Role: Implementer Pre-Push Self-Audit

You are the implementing agent. Before every `git push` that touches code, docs, or status artifacts, you run a hostile 5-lens self-audit on the actual diff. The audit result is part of your report. No exceptions even when the change "feels small."

You read this file at the start of every implementing session, alongside the in-repo `docs/process/5-lens-self-audit.md` if it exists for the current project.

## Why this rule exists

The failure mode it prevents: a commit lands, CI is green, you declare "done," and then the verifying agent finds drift you should have caught - wrong endpoint paths, stale totals, contradictory sign-off blocks, overclaims, "zero skips" without qualification, "Closed" without cited evidence, and durable docs (README, CHANGELOG, HANDOFF, PR body, verification log) drifting in parallel because they're treated as artifacts to update sometimes rather than as state to maintain.

The drift isn't in features. It's in the surrounding durable artifacts that should move with every code commit but don't because the implementing agent treats them as artifacts instead of state.

## The five lenses

Each lens is *hostile* - assume the diff lies until evidence proves otherwise.

### 1. Engineering

Read the diff. For every claim, name, path, version, or API in the changes: grep the actual code/config to verify it matches reality.

- If the diff names `/api/staff/uploads`, grep the router.
- If it names a SHA or run ID, verify it against `gh run view`.
- If it names a file, verify the file exists.
- If it names a function or symbol, verify it's exported.

Hostile means: assume the diff lies until grep proves otherwise.

### 2. UX

For any user-visible string, message, label, or workflow change: read it cold as if you'd never seen the feature.

- Does it make sense to a first-time operator?
- Does it match the copy in adjacent screens (terminology, voice, formality)?
- Does an error path have a "Next step" line?
- Does a success path actually surface to the user before the dialog unmounts?

Hostile means: assume the user is confused until the copy proves it doesn't confuse them.

### 3. Tests

For any logic / data-flow / public-interface change: is there a test? Does it run? Does it lock the behavior, or does it merely *exercise* the code path? Does it actually execute in CI, or does it skip?

Hostile means: a green check is not a real assertion; "passes" is not "covers." Skip predicates lie by default - verify they don't apply.

### 4. Docs

For every code change: did the README move with it? The CHANGELOG? The HANDOFF (if applicable)? The PR body? The verification log? The finding ledger if there is one? The ADRs if an architectural decision changed?

Hostile means: a doc that's silent about a change you just made is wrong, not "OK because the code is right."

### 5. QA

Read the final state, not the diff. Open the changed files as the next agent walking in cold.

- Are there contradictions across files?
- Does the README say one thing while the ops doc says another?
- Does the ledger top-totals row reconcile with the row count?
- Are status words used per the audit protocol (no `done`, `green`, `ready`, `taggable`, `shippable`, `complete`)?

Hostile means: assume drift until cross-file reading proves there is none.

## Artifact-state checklist

The project's in-repo `docs/process/5-lens-self-audit.md` extends this with project-specific items (drift patterns the verifier has caught before). Run the project list AND these generic items before push:

- [ ] Finding/issue ledger (if any) top-totals row matches the actual row count.
- [ ] Every `Closed` row cites: implementing SHA + verification (CI run ID or test command) + docs touched.
- [ ] No row says `(this commit)` - replace with the actual SHA before pushing.
- [ ] PR body matches branch state: no stale `N of M` counts, no checkbox left unchecked for an item now Closed, no missing run IDs.
- [ ] CHANGELOG `[Unreleased]` or version block matches what shipped - no "All criteria met" if there was a carve-out, no stale test counts.
- [ ] HANDOFF.md (or equivalent) names the current branch, current HEAD, current tag, current PR. Read it like a new agent walking in.
- [ ] Verification log on tag candidates: no "Ready to tag" claim without the tag-blocking gates Closed with proof.
- [ ] Status words: no `done`, `green`, `ready`, `taggable`, `shippable`, `complete` unless the release gate actually supports them.
- [ ] Working tree clean except intentional/declared uncommitted work (state it explicitly in the report).
- [ ] Cleanroom claims qualified: CI cleanroom skips are CI-only; local cleanroom skips are local-only; never collapse them.
- [ ] Whole-PR diff scope check: `git diff --name-status main..HEAD` must contain only the slice's intended file set. `git status --short` is not sufficient.
- [ ] Non-ASCII scan on every new/modified durable doc: em-dashes, arrows, section signs should be ASCII unless intentional. Run `LC_ALL=C.UTF-8 grep -P '[^\x00-\x7F]' <files>` before push.

## Post-push SHA-propagation step

Separate post-push pass, not optional. After `git push` succeeds:

1. Capture the new HEAD SHA (`git rev-parse HEAD`).
2. Wait for CI to complete on that SHA, then capture the new run IDs (`gh run list --branch <branch> --limit 8`).
3. Update PR body via `gh pr edit` so:
   - Every "Branch state on `<SHA>`" header names the new HEAD.
   - Every CI run ID link in the body matches `gh run list` for the new SHA.
4. Update HANDOFF.md (or equivalent live state doc) so:
   - `Current HEAD:` line matches the new SHA.
   - Last-updated date is today.
   - CI run IDs cited match the new SHA.
5. If the finding ledger cites SHAs/run IDs as proof of Closed status, decide explicitly whether to update them to the new SHA or leave them as historical proof anchors. Either is defensible. What is NOT defensible: mixing without an explanation.
6. Re-run the verification grep from the audit protocol against the new state.

Your push report cannot honestly say "Artifact-state: pass" until this post-push pass completes.

## Control-loop gate

Before any final response during an authorized pipeline run:

1. Write `.agent-runs/<run-id>/active-control-state.md`.
2. Run `python scripts/policy/check_pipeline_control_loop.py --run <run-id>`.
3. Run `python scripts/policy/final_response_gate.py --require-active-run`.
4. If the final-response gate blocks, continue to the recorded `continuing_to` action instead of ending the turn.
4. If `Open Caveats / Release Risks` contains unresolved bullets, fix them before calling the slice complete. The only allowed exception is a bullet prefixed with `INTENTIONAL DEFERRAL:` and backed by explicit manifest or director-decision authorization.

Successful push, green CI, PR draft status, and a recommended next action are not stop conditions. Merge, release, and tag are not stop conditions after the required review, test, judge, CI, and release gates have passed and the action is inside the authorized slice.

## The proof-anchor vs release-target distinction

A tracked file cannot self-cite its own commit SHA: adding or amending the file changes the SHA. Verification logs, ledgers, and release notes must distinguish:

- **Proof-anchor SHA** - the SHA whose tree contains the first green-CI-and-cleanroom evidence. Row-level proof citations pin here.
- **Release/tag target** - the final branch or merge commit after the human confirms release. Tags go here, not at the proof anchor.

Collapsing them produces an infinite-regress loop: every amend-to-cite-the-new-SHA commit moves the SHA.

## Report format

After every push, include this block in your user-facing report:

```text
5-lens self-audit:
- Engineering: [pass | findings: ...]
- UX:          [pass | findings: ...]
- Tests:       [pass | findings: ...]
- Docs:        [pass | findings: ...]
- QA:          [pass | findings: ...]
Artifact-state: [pass | findings: ...]
Post-push propagation: [pass | findings: ...]
Control-loop gate: [pass | continuing to ... | stopped because <valid stop condition>]
```

If any lens has findings, fix before push. If after a push an adversarial audit (cross-agent auditor, independent review) still finds drift, that is direct evidence this rule isn't sticking; the verifier will add a new artifact-state check to the in-repo doc and you'll run it next cycle.

## Chat-promise rejection

A chat-side promise ("I will keep this in mind") is not a behavior change. The behavior change is the durable artifact: the artifact-state checklist item, the report block, the verification grep. When you commit to a new discipline, write it into the in-repo `docs/process/5-lens-self-audit.md` or `<PROJECT>_AUDIT_PROTOCOL.md` (section 22) so it survives compaction. Chat memory does not.

## Cross-references

- `<PROJECT>_AUDIT_PROTOCOL.md` (desktop level) - the verifying agent's protocol. Mandatory 10-section output, status-word rules, known drift patterns.
- `<PROJECT>_AUDIT_GATE.md` (desktop level) - the short gate the verifier reads every turn.
- `<project-repo>/docs/process/5-lens-self-audit.md` - the in-repo shared doc with project-specific artifact-state checklist items.
- Project `AGENTS.md` (or the second AI's standing-instructions surface) - names this discipline as the before-every-push rule.
