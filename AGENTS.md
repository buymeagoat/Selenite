# Purpose
Defines the operating charter for AI collaborators (e.g., Codex) in this repository. Portable across projects; reference at session start.

Quick-start (keep it blunt and precise):
- Read `docs/AI_COLLAB_CHARTER.md` **and** `docs/build/PRODUCTION_TASKS.md` at session start; follow the execution order.
- Push back with blunt honesty; do not soften. Restate more clearly and guide instead of pausing for overwhelm.
- Always surface assumptions/uncertainty and challenge risky/unclear ideas.
- Honor admin gating; no auto-downloads; admin installs models; only expose installed backends; fall back rather than fail when missing.
- Manual checkpoint after substantial changes (system probe, ASR/diar work, model plumbing): stop and ask for admin review.
- Use runbooks: `bootstrap.ps1` to start; `run-tests.ps1` to validate changes.
- Before modifying or committing code, run `./scripts/pre-flight-check.ps1` (and resolve failures) so authentication, secrets, and logging guardrails stay enforced.
- Keep temporary debug artifacts (HTML/PowerShell, etc.) in the gitignored `scratch/` folder at repo root; never ship hardcoded IPs, credentials, or diagnostic pages via the production build.
- Execution order each turn: 1) restate request, 2) check ambiguity, 3) surface assumptions/uncertainty, 4) act.
- When a bug/regression appears, first ask “why didn’t tests catch this?” and add/adjust a test to cover it as part of the fix.
