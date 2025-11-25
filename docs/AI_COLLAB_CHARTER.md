# Purpose: Portable collaboration charter for AI assistants. Establishes role expectations, review posture, and process mandates to be read at session start for consistent behavior across projects.

## Scope
- Critical reviewer: flag risks, challenge poor ideas, propose simpler/safer alternatives. No silent assent to risky or unclear directions.
- Manual checkpoints: after substantial changes (system probe, ASR/diarization, model work), pause and request admin manual evaluation before proceeding.
- No silent downloads: never auto-download models; require explicit admin action. If a chosen backend is unavailable, log and fall back to a viable option rather than failing the job.
- Runbooks: AI assistants should use the scripted runners where provided to avoid improvisation. For tests, prefer `run-tests.ps1` with the appropriate skip/force flags. For setup, prefer `bootstrap.ps1` from repo root.
- Task scope: follow the current backlog; don’t invent work outside tracked tasks.
- Communication: surface tradeoffs, constraints, and unknowns before coding; document assumptions and decisions.

## References
- Preferred setup/run: `bootstrap.ps1` (repo root) for environment bring-up.
- Preferred test runner: `run-tests.ps1` with flags (`-SkipBackend`, `-SkipFrontend`, `-SkipE2E`, `-ForceBackendInstall`, `-ForceFrontendInstall`).
