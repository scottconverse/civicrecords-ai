# AGENTS.md

This project uses Agent Pipeline for Codex.

## Project Orientation

- Purpose: TODO
- Primary users: TODO
- Stack: TODO
- Test command: TODO
- Lint/static command: TODO

## Order Of Operations

1. Read this file and the active manifest before editing.
2. Keep work inside the manifest's `allowed_paths`.
3. Treat `forbidden_paths` as absolute unless the human director amends the manifest.
4. Run the policy checks and project tests named by the manifest before claiming a stage is ready for verification.
5. If a slice changes `.github/workflows/*.yml` or `.github/workflows/*.yaml`, name the workflow files in the plan before editing, apply `.pipelines/templates/workflow-cost-directives.md`, run `scripts/policy/run_all.py --run <run-id>`, and record workflow-cost evidence in the run artifacts.

## Non-Negotiables

- Do not skip tests.
- Do not silently expand scope.
- Do not rewrite durable release/audit evidence unless the manifest explicitly authorizes it.
- Do not use status words such as done, complete, ready, shippable, or taggable without evidence from the project's release gate.
- Do not add or modify GitHub Actions workflows without satisfying the workflow-cost directives. Unresolved workflow-cost violations are release risks and block completion.

## GitHub Actions Workflow-Cost Directives

The canonical directive list lives at `.pipelines/templates/workflow-cost-directives.md`.
Do not copy or edit the list here. If that file and this file disagree, the
canonical directive file wins.

## Pipeline Files

- `.pipelines/` contains the local pipeline definitions and role files.
- `scripts/policy/` contains deterministic policy checks.
- `.agent-runs/` contains per-run artifacts and is gitignored by default.

## Custom Project Rules

TODO: add project-specific conventions, branch policy, documentation requirements, UI/QA gates, security constraints, and release rules.
