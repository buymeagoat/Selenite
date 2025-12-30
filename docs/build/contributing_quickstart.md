# Contributing Quickstart (Agentic Flow)

Use this as the checklist to work in this repo and future apps:

## Local Flow
- Install and enable pre-commit hooks (husky is already set up):
  - Frontend: `npm run qa` (type-check, lint, tests) before pushing.
  - Backend: `python -m pytest` for relevant tests; run pre-commit to catch hygiene/secrets/lint.
- Keep tool versions aligned: Python 3.10, Node 20.
- Every code change must be memorialized (update `docs/build/CHANGELOG.md` or another allowed memo file).

## Required Files/Policies
- Hygiene policy: `repo-hygiene-policy.json` (run via `scripts/check_repo_hygiene.py`).
- OpenAPI: `docs/openapi.json` is generated; keep it fresh when API changes.
- PR template: fill Tests/Docs/Hygiene/Security/Migrations fields on every PR.

## CI Agents (must be green)
- Hygiene (`hygiene`)
- Docs/API + OpenAPI freshness (`docs_api`)
- Memorialization (`memorialization`)
- Migrations (folder + `alembic upgrade head`) (`migrations`)
- Tests (backend/frontend smokes) (`tests`)
- Security (gitleaks, pip-audit, npm audit) (`security`)
- Quality (build + bundle budget + Playwright smokes) (`quality`)
- Bundle report PR comment (`bundle-report` job in `report` workflow)
- Coverage PR comment (`coverage` job in `coverage-report` workflow)
- Nightly audit is informational only.

## Defaults
- Bundle cap: 4 MB total (override with `BUNDLE_MAX_BYTES`).
- Perf budget: `/health` 200 ms (override `PERF_PROBE_URL` / `PERF_PROBE_BUDGET_MS`).
- Accessibility smokes: Dashboard and Transcript pages.

## User Testing Loop (manual)
- Create job -> observe progress/ETA -> download transcript -> delete job. Report UX gaps; we add them to backlog/e2e smokes.
