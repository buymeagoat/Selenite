## Summary
- Describe the change and the user/admin impact in 1-2 sentences.
- Link the relevant PRODUCTION_TASKS ID(s).

## Pre-flight Checklist
- [ ] Ran `./scripts/pre-flight-check.ps1` and resolved any failures.
- [ ] Ran `./run-tests.ps1 -SkipE2E` (or stricter) and captured the outcome.
- [ ] Updated `docs/build/PRODUCTION_TASKS.md` and any manual verification docs.
- [ ] Confirmed no hardcoded IPs/credentials or debug instrumentation remain.
- [ ] Added/updated automated tests (or explained why not applicable).
- [ ] If merging to `main`: ran `./scripts/backup-verify.ps1` on the host and recorded the backup path in the PR.
- [ ] If data/storage changes: included a migration plan and rollback steps in the PR description.

## Manual Verification (if required)
- Steps taken:
  - [ ] ...
  - [ ] ...
