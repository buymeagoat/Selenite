# Manual Verification Checklist (Promotion)

Use this checklist for every dev→prod promotion. Record results and evidence paths
in `docs/build/DEV_TO_PROD_PROMOTION.md`.

## Core Runtime
- Login as admin succeeds (email + password).
- Dashboard loads with jobs list.
- New job submission works (upload + start).
- Job transitions: queued → processing → completed.
- Transcript view opens and displays content.
- Export download works (txt or preferred format).

## Admin Controls
- Admin console loads.
- Model registry shows expected providers/weights.
- User management tab loads (if enabled).

## Settings & Defaults
- Global defaults display correctly.
- Per-user defaults (if enabled) show expected values.
- Overridden settings behavior matches admin flags.

## Data Integrity
- Existing jobs are still visible.
- Existing tags remain.
- Existing settings remain.

## Evidence
- Note any deviations.
- Record log locations and screenshots if used.
