# Automation “Agents” Plan

This repo uses CI jobs as “agents” to shoulder hygiene, docs, testing, and security. Each job has one responsibility and reports back to PRs.

## Gateways
- Hygiene: `scripts/check_repo_hygiene.py` against `repo-hygiene-policy.json`.
- Docs/API: detect backend route/schema changes; require API docs/client updates.
- OpenAPI: generate `docs/openapi.json` from routers; fail CI if out of date.
- Security: secrets scan; dependency audit/license allowlist; static security lint on changed files.
- Tests: unit/component/integration; rerun flakies once; publish summary.
- Quality: bundle-size budget (check_bundle_size.py after build), accessibility smoke (axe/playwright), perf smoke on critical endpoints, optional i18n missing-strings check.
- Migrations: ensure schema/migrations are clean/in sync.
- Memorialization: require changelog/docs note when code changes.

## Implementation Blueprint
- Pre-commit: secrets, format/lint, hygiene, quick type check, optional changed-tests.
- CI (separate workflows):
  - `hygiene.yml` runs the hygiene script.
  - `docs-api.yml` regenerates OpenAPI (`docs/openapi.json`) and fails if out of date; checks API/docs drift.
  - `coverage-report.yml` posts frontend coverage summary on PRs.
  - `report.yml` posts bundle size on PRs.
  - `nightly-audit.yml` runs daily audits (pip/npm) and a perf probe.
  - `security.yml` runs gitleaks + pip-audit + npm audit (high+).
  - `tests.yml` runs test suites; retries flakies once.
  - `quality.yml` runs build + bundle budget (placeholder for accessibility/perf smokes).
  - `migrations.yml` ensures migrations are applied/clean.
  - `memorialization.yml` enforces changelog/docs note + PR template completion.
- Nightly/weekly: dep audit, flaky detection report, coverage/bundle trend report.

## Defaults and Budgets
- Bundle budget: 4 MB total for the frontend build (override with BUNDLE_MAX_BYTES).
- Perf probe: GET /health (or PERF_PROBE_URL) with 200 ms budget by default.
- Tool versions: Python 3.10, Node 20.
- Accessibility smokes: target Dashboard and Transcript pages (add more as needed).

## Branch Protection (set these as required)
- hygiene
- docs_api
- memorialization
- migrations
- tests
- security
- quality
- bundle-report (job in report workflow)
- coverage (job in coverage-report workflow)

## Developer/Author Flow
1) Run pre-commit; fix issues locally.
2) Add a short memorialization note (changelog or docs) for any code change.
3) Fill PR template (tests/docs/hygiene/security/migrations).
4) CI agents run; PR blocks on failures.

## Next Steps to Wire Up
- Add GH Actions workflows mirroring the agents above.
- Add a small `ensure_memorialization.py` to fail CI when code changes lack a note.
- Add bundle/accessibility/perf smoke scripts under `scripts/`.
- Make CI checks required in branch protection.
