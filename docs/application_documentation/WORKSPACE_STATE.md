# Workspace State Policy

This file defines how dev/prod repositories are flagged and how AI behavior is gated.

## States
- **writeable**: AI + human can make changes freely.
- **provisional**: AI changes only for commit gates (`SELENITE_ALLOW_COMMIT_GATES=1`). Human should not change the repo.
- **canonical**: AI changes only for commit gates (`SELENITE_ALLOW_COMMIT_GATES=1`). Human can change but should avoid doing so.

Only one repository can be canonical at a time.

## Allowed Changes By State
- **writeable**: feature work, refactors, docs, tests, scripts — normal development.
- **provisional**: commit-gate fixes only (lint, build, tests, migrations, docs alignment). No feature changes.
- **canonical**: same as provisional for AI; human should avoid edits unless a production emergency requires it.

Commit-gate artifacts (allowed when required):
- `.last_tests_run`
- `docs/memorialization/test-runs/` (gitignored)

## State Source of Truth
- `.workspace-state.json` in repo root (role + state + canonical owner).
- `.workspace-role` remains for dev/prod identity and must match `.workspace-state.json`.

## AI Guard Variables
- `SELENITE_AI_SESSION=1` enables AI guardrails.
- `SELENITE_ALLOW_COMMIT_GATES=1` allows AI to run commit-gate-only changes in provisional/canonical states.
- `SELENITE_ALLOW_PROD_WRITES=1` explains explicit approval for AI actions in prod.
- `SELENITE_ALLOW_STATE_CHANGES=1` allows the AI to change workspace state flags.

Human runs are not blocked by these guards.

## Scripts
- `scripts/show-workspace-state.ps1` displays the current state.
- `scripts/set-workspace-state.ps1 -State <writeable|provisional|canonical> [-Role dev|prod] [-CanonicalOwner dev|prod] [-Note "..."]` updates state.
- `scripts/capture-schema.ps1` prefers `sqlite3` if installed; otherwise it falls back to Python.

## Promotion Sequence (Canonicalization)
1) Dev milestone complete: mark dev **canonical** and prod **writeable**.
2) Verify backup + rehearsal migration/rollback plan (see COMMIT_GATES + promotion log).
3) Promote changes into prod and run dev/prod commit gates through smoke checks.
4) Human completes manual verification.
5) Mark prod **provisional** and dev **provisional** while prod commit gates finish.
6) After prod gates pass, mark prod **canonical** and dev **writeable**.

## Required Logging
- Record state transitions (timestamps + who) in `docs/build/DEV_TO_PROD_PROMOTION.md`.
- Record manual verification evidence (what was checked + artifacts/log paths).
- If a human must modify a canonical/provisional repo, record the reason and scope in the promotion log.

## Human Visibility
- Before starting work, run `scripts/show-workspace-state.ps1` and confirm the expected role/state.
- Treat canonical/provisional as read-only unless the process explicitly requires a change.

Dev reset is a status-only change. Do not clear data unless explicitly mandated by the process.
