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
- `users.last_seen_at`: idle-session tracking for timeout enforcement.
- `user_settings`: per-user defaults and preferences.
- `jobs`: transcription jobs and progress metadata.
- `transcripts`: export metadata.
- `tags`, `job_tags`: tag catalog + assignment.
- `feedback_submissions`: feedback + admin messages (folders/read state/threading/outbound metadata).
- `feedback_attachments`: feedback and admin message attachments.
- `audit_logs`: admin/user audit events.
- `model_providers`, `model_sets`, `model_entries`: model registry data.
- `system_preferences`, `settings`: global defaults and system-wide config.
- `system_preferences.session_timeout_minutes`: idle timeout window (minutes).
- `system_preferences.allow_self_signup`, `require_signup_verification`, `require_signup_captcha`: self-service signup gates.
- `system_preferences.signup_captcha_provider`, `signup_captcha_site_key`: CAPTCHA provider/site-key used by `/auth/signup` and admin UI; provider currently `turnstile` only.
- `system_preferences.password_min_length`, `password_require_uppercase`, `password_require_lowercase`, `password_require_number`, `password_require_special`: password policy enforced at signup and password change.
- `system_preferences.auth_token_not_before`: restart/administrator session invalidation watermark.

## Storage Paths
- `storage/media/` (uploaded source media)
- `storage/transcripts/` (generated transcripts)
- `storage/exports/` (bulk exports/zip bundles)
- `storage/feedback/` (feedback/message attachments; per-submission subfolders)
- `storage/backups/` (verified backups + restore manifests)
- `logs/` (runtime logs; never delete without explicit archival policy)
- `backend/models/` (installed models; never delete)

## Configuration & State
- `.env*` (runtime configuration)
- `.workspace-role` (dev/prod identity)
- `.workspace-state.json` (writeable/provisional/canonical state)
- `TURNSTILE_SITE_KEY` (required when `require_signup_captcha` is true and provider is `turnstile`)
- `TURNSTILE_SECRET_KEY` (server-side verify key for Turnstile)
- `RESEND_API_KEY` (optional; email delivery for future verification flows)

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
