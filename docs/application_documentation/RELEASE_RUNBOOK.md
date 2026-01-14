# Production Release Runbook

## Purpose
This runbook defines the required steps to ship a new feature to production without data loss. It is the source of truth for release hygiene.

## Scope
Applies to any merge into `main` that will be deployed to production. All data preservation steps are mandatory.

## Roles
- **Developer**: prepares the change, migration plan, backup verification evidence, and release notes.
- **Administrator**: performs UI verification after deployment.

## Release Gates
Before merging to `main`:
1. **PR checklist complete** (tests, docs, backup verification).
2. **Migration plan included** if data or storage changes are involved.
3. **Rollback plan included** for any schema or storage change.
4. **Backup verification evidence** recorded (path + timestamp).

## Data Change Classification
Use this to determine required migration steps:
- **No data change**: feature only; no schema/storage changes.
- **Backward-compatible data change**: additive schema changes or new tables.
- **Breaking data change**: column removal, type changes, or storage layout changes.

Breaking changes require a staged rollout or a migration that preserves old data in a new shape.

## Pre-Release Checklist (Host)
1. **Backup verification**:
   - Run `./scripts/backup-verify.ps1`.
   - Record the backup path in the release notes (`docs/application_documentation/CHANGELOG.md`).
2. **Alignment audit (prod)**:
   - Run `rg -n "Selenite-dev|5174|8201|devselenite|dev\\.selenite|DEV_" scripts docs backend frontend`.
   - Confirm `.env` ports/hosts are prod (`PORT=8100`, `FRONTEND_URL=...:5173`) and frontend allowed hosts are prod-only unless explicitly required.
3. **Staging rehearsal** (recommended for schema changes):
   - Restore the backup into `scratch/restore-<timestamp>`.
   - Run migrations against the restored DB.
   - Run smoke tests against the restored data.

## Release Steps (Production)
1. **Announce a maintenance window** if downtime is expected.
2. **Stop services**:
   - `./scripts/stop-selenite.ps1`
3. **Deploy code**:
   - Fetch `main` or the release tag.
4. **Run migrations**:
   - `alembic upgrade head`
5. **Start services**:
   - `./scripts/start-selenite.ps1`
6. **UI verification** (administrator):
   - Login works.
   - Existing jobs and tags visible.
   - New job can be created.
   - Export works.
   - HTTPS-only enforcement verified (HTTP blocked, HTTPS works).
7. **Record evidence**:
   - Update `docs/application_documentation/PRODUCTION_READY.md`.
   - Log the release in `docs/application_documentation/CHANGELOG.md`.

## Rollback Steps
Use this if production fails after release:
1. **Stop services**.
2. **Restore DB + storage from the backup snapshot**.
   - Do not overwrite `backend/models` or `logs`.
3. **Deploy previous release tag**.
4. **Start services**.
5. **Verify UI** using the same checks above.

## Evidence to Capture
- Backup path and timestamp.
- Release tag/commit.
- Migration plan and rollback plan (if data change).
- Manual verification results.

## Non-Negotiables
- Never overwrite `backend/models` or `logs`.
- Never restore data into the live repo without a verified snapshot.
- No merge to `main` without backup verification evidence.
