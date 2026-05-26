# GitHub Actions Workflow-Cost Directives

These directives are binding for every Agent Pipeline run that creates or
modifies `.github/workflows/*.yml` or `.github/workflows/*.yaml`.

1. Never add a daily cron without explicit Scott approval. Weekly is the maximum default schedule. Daily is allowed only for a specific justified need, such as security scanning or dependency drift, and the run record must prove weekly is insufficient before daily is used.
2. Every new GitHub Actions workflow must include the required concurrency block with `group: ${{ github.workflow }}-${{ github.ref }}` and `cancel-in-progress: true`, except release or tag workflows where cancellation would corrupt the release.
3. Do not duplicate `push: branches: [main]` and `pull_request: branches: [main]` for the same validation workflow.
4. Batch work-in-progress commits before pushing; squash local work-in-progress commits when doing so preserves useful history.
5. Add `paths:` filters when adding heavy workflows, including TeX, Docker, Playwright, browser installs, large language models, cleanroom, or e2e validation.
6. macOS jobs are allowed on release tags only unless Scott explicitly approves a PR-fired exception.
7. Windows jobs are allowed on PR only when truly necessary, and the run record or policy evidence must justify the cost.
8. Python version matrices are allowed on tags or weekly cron. PR CI tests one production Python version by default, currently Python 3.12.
9. Cache anything that takes more than 30 seconds to install or download.
10. Every `upload-artifact` step must set `retention-days: 7` unless the artifact is a release artifact or Scott explicitly approves longer retention.

`scripts/policy/check_actions_budget.py` mechanically enforces the directives
that can be checked from workflow YAML. Human-readable run artifacts must cover
the judgment-based directives, including why a Windows PR job, daily cron, or
longer artifact retention was justified.

