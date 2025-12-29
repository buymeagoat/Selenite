# Portable Build & Governance Starter

## Purpose
Create a reusable blueprint for building and maintaining apps with strong guardrails, consistent workflows, and minimal manual drift. This document is a starter; we will flesh it out later when Selenite is stable.

## Audience
- Non-developers building an app with AI assistance
- Contributors who need repeatable workflows, guardrails, and documentation patterns

## Scope (What This Covers)
- Non-application tooling and process standards
- Quality gates and repository hygiene
- Documentation alignment and memorialization
- Test run capture and evidence

## Scope (What This Does NOT Cover Yet)
- Product requirements
- UI/UX design rules
- Infrastructure/hosting patterns
- Security hardening playbooks

## Core Principles
- Guardrails first: automate checks before change and before commit.
- One canonical backlog: no work happens outside the task log.
- Memorialize outcomes: test evidence is always archived.
- Root stays clean: artifacts go to explicit, approved locations only.
- Align docs to code: contracts and component specs must match reality.

## Portable Artifact Inventory (Current Selenite)
### Guardrails and QA
- `scripts/pre-flight-check.ps1` (mandatory before edits/commits)
- `scripts/run-tests.ps1` (backend + frontend + E2E + alignment + hygiene)
- `scripts/check_alignment.py` (drift detection for paths/settings)
- `scripts/check_repo_hygiene.py` + `repo-hygiene-policy.json`
- `scripts/sqlite_guard.py` (protects DB location)
- `scripts/protected-clean.ps1` (safe cleanup only)

### Runbooks / Operators
- `scripts/bootstrap.ps1`
- `scripts/start-selenite.ps1`
- `scripts/restart-selenite.ps1`
- `scripts/stop-selenite.ps1`

### Governance Docs
- `AGENTS.md` (operator rules + guardrails)
- `docs/AI_COLLAB_CHARTER.md` (behavior/decision rules)
- `docs/build/PRODUCTION_TASKS.md` (canonical backlog)
- `docs/API_CONTRACTS.md` (canonical API contract)
- `docs/COMPONENT_SPECS.md` (canonical UI component specs)

### Evidence / Memorialization
- `docs/memorialization/**` (test runs, manual checkpoints)

## Porting Checklist (High Level)
1. Copy governance docs (charter + agents + task backlog).
2. Copy guardrail scripts and hygiene policy.
3. Update paths and project names inside scripts.
4. Establish canonical artifact locations (logs, storage, scratch).
5. Run `pre-flight-check` and `run-tests` to validate setup.

## Glossary (Working Terms)
- Guardrails: checks that run before edits/commits/tests.
- Hygiene policy: allowed locations for temp/test artifacts.
- Memorialization: archived test runs and manual checkpoints.

## Next Expansion (Placeholder)
- Formal template structure
- CI wiring (GitHub Actions baseline)
- Release checklist
- Config schema validation
- Standardized debug protocol
