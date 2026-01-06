# Commit Gates

This is the single source of truth for what must pass before a commit is allowed.

## Universal Rules
- If any gate is ambiguous, stop and ask before continuing.
- Do not bypass a failed gate unless the task explicitly says so.
- All outputs go to `docs/memorialization/` (gitignored).
- Before any edits, run `scripts/workspace-guard.ps1` and confirm `.workspace-role` is `dev`.
- **Single promotion process**: when dev reaches a milestone and both AI + human agree it is complete, dev is temporarily canonical. Run the promotion steps below to update prod. After prod is verified, prod becomes canonical and dev returns to development state (status only; do not delete data unless the process explicitly mandates it).
- **Human trigger**: the human can start this process by asking the AI to commit dev changes to prod.
- **Workspace state file**: `.workspace-state.json` is authoritative for `writeable`/`provisional`/`canonical` status. AI sessions must set `SELENITE_AI_SESSION=1` and may only proceed in `provisional`/`canonical` when running commit gates (`SELENITE_ALLOW_COMMIT_GATES=1`).
- **Reference**: see `docs/application_documentation/WORKSPACE_STATE.md` for the state machine and flag definitions.
- **Known blocker remediation**: when a documented blocker appears (e.g., repo hygiene failing due to rehearsal restores), apply the documented remedy without pausing the process.

## Dev Commit Gates (Required)
1) Pre-flight: run `./scripts/pre-flight-check.ps1` and resolve failures.
2) Repo hygiene: `python scripts/check_repo_hygiene.py` (or `run-tests.ps1` which invokes it).
3) Lint + format:
   - Backend: `black --check backend` and `ruff check backend`.
   - Frontend: `npm run lint`.
4) Type/build: `npm run build` (frontend).
5) Tests: `./scripts/run-tests.ps1 -SkipE2E` (or stricter).
6) Migrations: run `python scripts/check_migrations.py` + `python scripts/run_migrations_upgrade.py`.
7) Data inventory: update `docs/application_documentation/DATA_INVENTORY.md` for any data-bearing changes.
8) Docs alignment: update any docs touched by code changes and confirm no stale references.
9) Security scan: run the repo security checks required by `pre-flight` plus any task-specific audits.
10) Dev/prod separation: confirm no protected paths were modified unless explicitly required.
11) Promotion log prep: run `./scripts/diff-dev-prod.ps1` and update
    `docs/build/DEV_TO_PROD_PROMOTION.md` with the delta.
12) **Dev/prod separation audit (hard check)**: run
    `rg -n "Selenite-dev|/Selenite-dev|\\\\Selenite-dev|:8200|:8201|:5174" -S`
    and verify no prod artifacts reference dev paths or dev ports. Record
    results in the promotion log before continuing.

## Update Prod From Dev (Required)
0) **Prod health pre-check**: in prod, verify `git status -sb` is clean and `scripts/pre-flight-check.ps1`, `python scripts/check_migrations.py`, `python scripts/run_migrations_upgrade.py` all pass. If prod is dirty, the AI must commit the outstanding prod fixes first (with a clear process-oriented message), record the reason in the promotion log, and then re-run the pre-check.
1) Ensure dev commit is clean (all gates above satisfied).
2) Use the promotion log to apply changes to prod in a controlled, auditable order.
3) **Prod readiness pass**: review every dev change for prod compatibility (ports, paths, env flags, dev-only scripts/docs/artifacts) and tailor or exclude items so prod startup, migrations, and runbooks succeed.
3a) **Hard separation audit (required)**: in prod, run
    `rg -n "Selenite-dev|/Selenite-dev|\\\\Selenite-dev|:8200|:8201|:5174" -S` and
    verify prod uses prod ports/paths. Also verify runtime config/env values
    (`VITE_API_URL`, `VITE_API_PORT`, `SELENITE_BACKEND_PORT`) align with prod.
    Record findings and any required adjustments in the promotion log.
4) **Migration hardening check**: verify new migrations are idempotent (safe on partially applied prod DBs) and do not drop/reset user/admin configuration unless explicitly required.
5) **Pre-upgrade backup verify (prod)**: run `./scripts/backup-verify.ps1` and record the backup path.
6) **Backup scope check**: ensure the backup includes DB + storage + required config (`.env*`). If config is not included by the script, capture it via `scripts/capture-config.ps1` and record the path.
7) **Schema snapshot (pre-upgrade)**: capture a schema snapshot of the prod DB via `scripts/capture-schema.ps1 -Label pre-upgrade` and record the file path.
8) **Rehearsal migration (prod backup)**: restore the backup into `scratch/restore/prod-rehearsal` and run migrations against it. Promotion stops if rehearsal fails.
9) **Schema snapshot (post-upgrade)**: capture schema after rehearsal (and after prod upgrade) via `scripts/capture-schema.ps1 -Label post-upgrade` and record the path.
10) **Rehearsal cleanup**: remove the rehearsal restore path after artifacts are captured to keep repo hygiene green.
11) **Rollback plan confirmed**: record the rollback steps + backup path in the promotion log.
12) Run smoke checks in prod matching the dev verification snapshot.
13) **Manual verification**: use `docs/application_documentation/MANUAL_VERIFICATION_CHECKLIST.md` and record evidence paths.
14) **Canonicalization check**: confirm prod matches the verified dev snapshot (features + UI behavior). Data parity is not required; behavior parity is. Record the confirmation in the promotion log.
15) **Dev reset (post-approval)**: after explicit admin approval that prod is canonical, mark dev as back in development state. Do not clear data unless a separate, explicit step mandates it.
16) **Agentic execution**: once the human requests promotion, the AI runs all steps until a manual verification checkpoint is required. After the human confirms verification, the AI resumes and completes the remaining commit gates.
17) **Promotion log evidence**: record state transitions, manual verification checklist, schema snapshots, and artifact paths in `docs/build/DEV_TO_PROD_PROMOTION.md`.

## Prod Commit Gates (Required)
1) Pre-flight: `./scripts/pre-flight-check.ps1`.
2) Repo hygiene: `python scripts/check_repo_hygiene.py`.
3) Lint + format: as required for prod scope (backend + frontend).
4) Type/build: `npm run build` (frontend).
5) Tests: `./scripts/run-tests.ps1 -SkipE2E` (or stricter).
6) Migrations: `python scripts/check_migrations.py` + `python scripts/run_migrations_upgrade.py`.
7) Release runbook: follow `docs/build/RELEASE_RUNBOOK.md` and record evidence.
8) Backup verification: `./scripts/backup-verify.ps1` (record the backup path).
9) Memorialize artifacts: ensure all logs/test outputs are saved under
   `docs/memorialization/`.

## Artifact Expectations
- `.last_tests_run` must be updated by the test runner.
- Test artifacts must be in `docs/memorialization/test-runs/<timestamp>-<suite>/`.
- Do not delete or overwrite protected paths without explicit approval.
