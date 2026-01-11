# Purpose
Defines the operating charter for AI collaborators (e.g., Codex) in this repository. Portable across projects; reference at session start.

Quick-start (keep it blunt and precise):
- Read `docs/AI_COLLAB_CHARTER.md` **and** `docs/build/PRODUCTION_TASKS.md` at session start; follow the execution order.
- Push back with blunt honesty; do not soften. Restate more clearly and guide instead of pausing for overwhelm.
- Always surface assumptions/uncertainty and challenge risky/unclear ideas.
- Honor admin gating; no auto-downloads; admin installs models; only expose installed backends; fall back rather than fail when missing.
- Manual checkpoint after substantial changes (system probe, ASR/diar work, model plumbing): stop and ask for admin review, enumerating the manual tests/UX checks the admin should run to close the checkpoint with explicit step-by-step (click-by-click) instructions.
- Use runbooks: `scripts/bootstrap.ps1` to start; `scripts/run-tests.ps1` to validate changes.
- Never run `git clean -fd` directly; use `scripts/protected-clean.ps1 -DryRun` first and only proceed when it reports zero protected paths.
- Before modifying or committing code, run `./scripts/pre-flight-check.ps1` (and resolve failures) so authentication, secrets, and logging guardrails stay enforced.
- Keep temporary debug artifacts (HTML/PowerShell, etc.) in the gitignored `scratch/` folder at repo root; never ship hardcoded IPs, credentials, or diagnostic pages via the production build.
- Keep the repo root clean: only canonical directories (`backend/`, `docs/`, `frontend/`, `logs/`, `scratch/`, `scripts/`, etc.) belong there. Any logs or dumps must live inside `logs/` (e.g., `logs/frontend/`), and any experiments/notes belong under `scratch/`. Do not drop files like `pip_freeze.txt` or `playwright-report/` at the root.
- Change cascade: any application change must include aligned updates to tests and database checks (migrations + startup guards). If a CRUD change is made, add/adjust tests and ensure startup heals missing DB structures or fails with a clear error.
- Execution order each turn: 1) restate request, 2) check ambiguity, 3) surface assumptions/uncertainty, 4) act.
- End-of-phase handoff: every completion message must clearly state (a) phase/task status, (b) what was done, and (c) the next actionable steps/owner so the user never has to ask.
- If a blocker appears (e.g., locked files, missing processes), remediate it immediately (stop conflicting services, clean stray artifacts, retry) and continue without waiting for user confirmation unless the action is destructive or violates other guardrails.
- If a blocker requires user choice, propose a remedy in clear, everyday language before pausing.
- If halted by a guard/failure, pause and give a brief kid-friendly summary of what failed and why, then list the next safe options before continuing.
- **Workspace state guard**: Use `.workspace-state.json` plus `scripts/workspace-guard.ps1` before any file edit. AI sessions must set `SELENITE_AI_SESSION=1` so the guard enforces state. States: `writeable` (AI+human ok), `provisional` (AI only for commit gates), `canonical` (AI only for commit gates; human still allowed). Use `SELENITE_ALLOW_COMMIT_GATES=1` for gate-only changes and `SELENITE_ALLOW_PROD_WRITES=1` for AI edits in prod. If any tool output references the prod path while working on dev tasks, stop and correct the working directory before proceeding.
- **Data inventory**: update `docs/application_documentation/DATA_INVENTORY.md` whenever a change introduces, renames, or retires data-bearing structures (DB tables/columns, storage paths, persistent config).
- When a bug/regression appears, first ask "why didn't tests catch this?" and add/adjust a test to cover it as part of the fix.
- **Dev/prod separation**: Never overwrite or delete dev-local artifacts without explicit approval. This includes `.last_tests_run`, `.workspace-role`, `.env*`, `docs/memorialization/`, `logs/`, `scratch/`, `storage/`, `storage-dev/`, and any `/models` subtree. These may only be modified when a task explicitly calls for it.
- **VS Code Python Configuration**: Never modify `.vscode/settings.json` without validating Python extension behavior. Required settings to prevent environment loops: `python.interpreter.infoVisibility: "never"`, `python.analysis.autoSearchPaths: false`, `python.analysis.diagnosticMode: "openFilesOnly"`, `python.globalModuleInstallation: false`. Test after changes: reload workspace and verify "Configuring a Python Environment" does not appear.
- Admin validation scope: the admin can only verify via the UI. Do not request code-level or DB reviews; ship changes, specify what to click in the UI, and expect feedback only from UI behavior.
