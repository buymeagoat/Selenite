# Data Inventory (Living)

This document catalogs all data-bearing assets that must be preserved across dev→prod promotions.
It is a living document and must be updated for any change that introduces, renames, or retires
data structures, storage paths, or persistent configuration.

## Invariants
- Production data must never be overwritten by dev data.
- Migrations must be additive/idempotent unless a documented, approved data plan exists.
- Backup + rehearsal + rollback are mandatory before prod updates.

## Database (SQLite)
**Primary DB**: `backend/selenite.db`

Key tables (update if schema changes):
- `users`: accounts, admin flags, login identity.
- `user_settings`: per-user defaults and preferences.
- `jobs`: transcription jobs and progress metadata.
- `transcripts`: export metadata.
- `tags`, `job_tags`: tag catalog + assignment.
- `audit_logs`: admin/user audit events.
- `model_providers`, `model_sets`, `model_entries`: model registry data.
- `system_preferences`, `settings`: global defaults and system-wide config.

## Storage Paths
- `storage/media/` (uploaded source media)
- `storage/transcripts/` (generated transcripts)
- `storage/exports/` (bulk exports/zip bundles)
- `storage/backups/` (verified backups + restore manifests)
- `logs/` (runtime logs; never delete without explicit archival policy)
- `backend/models/` (installed models; never delete)

## Configuration & State
- `.env*` (runtime configuration)
- `.workspace-role` (dev/prod identity)
- `.workspace-state.json` (writeable/provisional/canonical state)

## Required Updates (When Changing Data)
If you change anything in the categories above:
1) Update this document (add/modify entries).
2) Note any migration requirements (idempotent + additive by default).
3) Note any new backup/restore considerations.

## Rollback Expectations
- A verified backup path must be recorded before promotion.
- Rehearsal migrations must succeed on a restored backup before touching prod.
- Rollback = stop services → restore backup → restart → re-verify.
- If `.env*` or other config files are not part of the backup, capture them manually and record the path in the promotion log.
- Schema snapshots must be captured pre/post upgrade and recorded in the promotion log.
