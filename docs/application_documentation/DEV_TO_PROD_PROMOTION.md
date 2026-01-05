# Dev-to-Prod Promotion Log

This log tracks every dev change intended for production promotion. It is the single source of truth for what should (and should not) be merged into prod.

## Workflow
0) **Prod health pre-check**: confirm prod is clean (`git status -sb`) and core checks pass before touching dev promotion. If prod is dirty, commit the prod fixes first, record the reason in the promotion log, then re-run the pre-check.
1) Add a new entry before starting dev work.
2) Update the entry as changes land (files, tests, manual checks).
3) When AI + human agree the dev milestone is complete, mark dev as **temporarily canonical** and set prod to **writeable** for promotion.
4) Run `scripts/diff-dev-prod.ps1` to confirm file deltas match the entry.
5) Perform a **prod readiness pass**: verify each change is safe/compatible for prod (ports, paths, env flags, dev-only scripts/docs/artifacts) and tailor or exclude as needed.
6) Verify migrations are idempotent and do not reset admin/user configuration unless explicitly required.
7) Run `./scripts/backup-verify.ps1` on prod and record the backup path.
8) Capture config via `./scripts/capture-config.ps1` if `.env*` is not in the backup; record the path.
9) Capture a **pre-upgrade schema snapshot** via `./scripts/capture-schema.ps1 -Label pre-upgrade` and record the path.
10) Rehearse the upgrade: restore the backup into `scratch/restore/prod-rehearsal` and run migrations against it. Stop if rehearsal fails.
11) Capture a **post-upgrade schema snapshot** via `./scripts/capture-schema.ps1 -Label post-upgrade` and record the path.
12) Clean up the rehearsal restore path (e.g., `scratch/restore/prod-rehearsal`) to keep repo hygiene green after artifacts are captured.
13) Record the rollback steps (stop services -> restore backup -> restart -> re-verify) in the entry notes.
14) Promote changes into prod and run the prod commit gates up through smoke checks.
15) Provide the manual verification checklist; human verifies prod functionality. Record the checklist + evidence paths in the entry notes.
16) After manual verification, mark prod **provisional** and dev **provisional** until prod commit gates complete.
17) Mark the entry **Approved** once manual verification is complete.
18) Mark the entry **Promoted** after the prod merge/deploy.
19) Once prod commit gates pass, mark prod **canonical** and dev **writeable** (status change only; do not clear data unless explicitly mandated).
20) Record all state transitions (timestamps + who) in the entry notes.

## Required Entry Fields
Each promotion entry must include:
- Backup path (prod).
- Config capture path (if `.env*` not included in backup).
- Schema snapshot paths (pre/post).
- Rollback steps.
- Manual verification checklist + evidence paths.
- State transitions (timestamp + who).

## Status Legend
- **Pending**: work in progress or awaiting checks.
- **Approved**: verified and ready to promote.
- **Promoted**: applied to prod.
- **Dev-only**: must never be promoted.

## Pending Promotion
| ID | Summary | Status | Owner | Notes |
| --- | --- | --- | --- | --- |
| 2026-01-02-multi-user | Multi-user auth, admin user management, per-user settings, audit logging, job scoping | Pending | Codex | `run-tests.ps1 -SkipE2E` passed 20260105-150330; manual UI verification in dev pending |
| 2026-01-02-dashboard-tests | Fix Dashboard test settings mocks (`max_concurrent_jobs`) | Pending | Codex | Blocked by test run |
| 2026-01-04-commit-gates | Commit gate guardrails + dev/prod diff tooling updates | Pending | Codex | `scripts/diff-dev-prod.ps1` optimized; COMMIT_GATES.md added |
| 2026-01-05-promotion-hardening | Promotion safeguards: workspace state, data inventory, schema snapshot/config capture, manual verification checklist | Pending | Codex | New promotion process codified; ready to promote with next milestone |

## Dev-only (Do Not Promote)
| ID | Summary | Status | Owner | Notes |
| --- | --- | --- | --- | --- |
| 2026-01-02-dev-separation | Dev-only port isolation + repo safeguards (8201/5174, script defaults, dev-only docs) | Dev-only | Codex | Keeps dev isolated from prod |

