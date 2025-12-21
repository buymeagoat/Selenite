# Manual Testing Checklist - 2025-12-12 (Admin & Runtime)

> **Archive Notice (2025-12-18 16:35 CT)**  
> Manual checkpoint closed after core bring-up, settings, and registry rescans were validated. Remaining unchecked items were deferred so we can pivot to the UI/UX remediation plan. See `docs/build/PRODUCTION_TASKS.md` (UI/UX polish work block) for follow-up actions.

Purpose: Verify recent changes (script relocation, curated provider seeding, rate-limit tweaks, logging enablement, settings endpoints) via manual steps. Update/append results as you test. Keep this as a living memorialization artifact for future checkpoints.

## Preconditions
- Use `./scripts/restart-selenite.ps1` (or `./scripts/start-selenite.ps1`) to launch. Confirm backend logs write to `backend/logs/selenite-*.log` (DISABLE_FILE_LOGS=0).
- Run from repo root; ensure `.venv` exists and DB is at head (alembic current: `20251210_seed_curated_providers`).
- Models folder: `backend/models/` exists; no weights required for availability tests.

## Core Bring-up
- [x] Restart succeeds (no PowerShell errors) and two windows open (backend on 8100, frontend on 5173).
- [x] Backend log shows startup complete; no `-advertisehosts` in CORS origins; job queue started.
- [x] Smoke test (run by restart script) passes; health returns 200.
- [x] Alignment guard: from repo root, run `python scripts/check_alignment.py` and confirm it reports `0 issues` against the live DB/filesystem`. (2025-12-13 18:45 CT — `Alignment check passed: registry paths, storage, and filesystem are canonical.`)

## Admin Settings & Rate Limits
- [x] Navigate to Admin → Settings over Tailscale (`http://100.x.x.x:5173`); `/settings` loads without 500/429.
- [x] Save settings (time zones, defaults) → success toast appears; no errors in backend log.
- [x] Confirm `/settings` endpoint returns 200 via UI reload; backend log has no rate-limit errors.

## Model Registry & Availability
- [x] Admin → Model Registry: "Rescan availability" completes; availability warnings (missing deps/weights) render. (2025-12-18 15:40 CT — toast + backend `/system/availability` call succeeded, warnings listed.)
- [x] Curated providers/weights are visible (disabled until weights exist); no errors in console/backend log. (2025-12-21)

## Script Relocation Sanity
- [ ] Running `./scripts/restart-selenite.ps1` works (no missing file errors).
- [ ] `./scripts/view-logs.ps1 -Lines 50` shows latest backend log (timestamped file).

## Logging & Storage
- [ ] New log files present under `backend/logs/selenite-*.log` for this session.
- [ ] Confirm storage paths in use: `storage/media`, `storage/transcripts` (not `backend/storage`).

## Job Flow Smoke
- [ ] Create a small job via UI; completes or fails with clear error (note diarizer status if attempted).
- [ ] Job card + modal load; no 500s when viewing transcripts.

## Regression Guards
- [ ] Auth: login/logout works over Tailscale and localhost.
- [ ] System info panel loads (Admin → System); no CORS or rate-limit errors.
- [ ] Settings save is not blocked by rate limiting (no 429 in backend log). 

## Notes / Findings
- [ ] Record any failures or warnings here with timestamps and log snippets.

## Archive Status
- Core checkpoints completed through "Model Registry & Availability" (rescan).
- Remaining steps deferred on 2025-12-18 and will be revisited after the UI/UX remediation work block recorded in `docs/build/PRODUCTION_TASKS.md`.
