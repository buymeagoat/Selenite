# Purpose
Defines the operating charter for AI collaborators (e.g., Codex) in this repository. Portable across projects; reference at session start.

Quick-start (keep it blunt and precise):
- Read `docs/AI_COLLAB_CHARTER.md` **and** `docs/build/PRODUCTION_TASKS.md` at session start; follow the execution order.
- Push back with blunt honesty; do not soften. Restate more clearly and guide instead of pausing for overwhelm.
- Always surface assumptions/uncertainty and challenge risky/unclear ideas.
- Honor admin gating; no auto-downloads; admin installs models; only expose installed backends; fall back rather than fail when missing.
- Manual checkpoint after substantial changes (system probe, ASR/diar work, model plumbing): stop and ask for admin review.
- Use runbooks: `scripts/bootstrap.ps1` to start; `scripts/run-tests.ps1` to validate changes.
- Never run `git clean -fd` directly; use `scripts/protected-clean.ps1 -DryRun` first and only proceed when it reports zero protected paths.
- Before modifying or committing code, run `./scripts/pre-flight-check.ps1` (and resolve failures) so authentication, secrets, and logging guardrails stay enforced.
- Keep temporary debug artifacts (HTML/PowerShell, etc.) in the gitignored `scratch/` folder at repo root; never ship hardcoded IPs, credentials, or diagnostic pages via the production build.
- Keep the repo root clean: only canonical directories (`backend/`, `docs/`, `frontend/`, `logs/`, `scratch/`, `scripts/`, etc.) belong there. Any logs or dumps must live inside `logs/` (e.g., `logs/frontend/`), and any experiments/notes belong under `scratch/`. Do not drop files like `pip_freeze.txt` or `playwright-report/` at the root.
- Change cascade: any application change must include aligned updates to tests and database checks (migrations + startup guards). If a CRUD change is made, add/adjust tests and ensure startup heals missing DB structures or fails with a clear error.
- Execution order each turn: 1) restate request, 2) check ambiguity, 3) surface assumptions/uncertainty, 4) act.
- When a bug/regression appears, first ask "why didn't tests catch this?" and add/adjust a test to cover it as part of the fix.
- **VS Code Python Configuration**: Never modify `.vscode/settings.json` without validating Python extension behavior. Required settings to prevent environment loops: `python.interpreter.infoVisibility: "never"`, `python.analysis.autoSearchPaths: false`, `python.analysis.diagnosticMode: "openFilesOnly"`, `python.globalModuleInstallation: false`. Test after changes: reload workspace and verify "Configuring a Python Environment" does not appear.
- Admin validation scope: the admin can only verify via the UI. Do not request code-level or DB reviews; ship changes, specify what to click in the UI, and expect feedback only from UI behavior.
