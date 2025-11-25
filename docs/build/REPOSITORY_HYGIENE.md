# Repository Hygiene Directive

Our repository is the canonical reflection of the product. Everything that is tracked must be intentional, necessary to build or operate Selenite, and owned by a maintainer. Everything transient—artifacts, caches, generated logs, temporary databases—belongs outside of git and must be aggressively removed or ignored so contributors never inherit surprise state. Environment defaults must point to the same canonical locations so code and tests never fork paths silently. Automated guardrails (scripts, CI jobs, and local hooks) must fail fast when the repo drifts, and cleanup steps need to run as part of every workflow. Hygiene is ultimately about predictability: a deterministic, reproducible workspace that every engineer can trust.

## Common Hygiene Failures & Mitigations

| Failure mode | Typical cause | Mitigation |
|--------------|---------------|------------|
| **Duplicate assets** (e.g., media/transcript directories or SQLite DBs living in multiple paths) | Divergent environment variables between scripts (bootstrap vs. tests), ad-hoc commands that ignore project defaults | Define a single canonical path in code, set it explicitly in every script, and audit env overrides in CI (fail if new paths appear). |
| **Orphaned build/test artifacts** (dist folders, playwright reports, coverage dumps) | Test scripts don’t clean up after themselves; gitignore misses new patterns | Make cleanup part of the test runner (before/after hooks), extend `.gitignore`, and run `git status --short` in CI to fail if artifacts remain. |
| **Stale or oversized logs/memorialization archives** | Every run appends files without rotation; no retention policy | Rotate logs with size/age caps, archive or purge memorialization folders on a schedule, and add automation that warns when thresholds are exceeded. |
| **Drift between documentation and scripts** | README/env samples updated but bootstrap/run-tests aren’t, or vice versa | Treat documentation as contracts—when an env var changes, update README + scripts in the same PR and add a CI check comparing values. |
| **Hidden dependency caches (node_modules, models, venvs)** show up in git | Manual copying, mistaken `git add -A`, or missing gitignore entries | Ensure `.gitignore` covers dependency trees, and run a hygiene script in CI to flag newly tracked large binaries before merge. |
| **Temporary debugging files** (`*.log`, `tmp.sql`, scratch notebooks) creep into the tree | Developers leave scratch files in repo root, and git can’t distinguish them | Encourage using `/tmp` or `docs/memorialization/` for long-lived artifacts, and keep a `.git/info/exclude` template referenced in onboarding. |

Adopting these habits keeps the repository deterministic for everyone and prevents the “duplicate storage” scenario from repeating elsewhere. Continuous hygiene checks should now be part of any workflow (local scripts or CI) that manipulates the tree.

## Policy Maintenance Workflow

- The authoritative rules live in `repo-hygiene-policy.json`. Every pull request that introduces a new directory, artifact, or retention rule **must** update this file and bump `policy_version`.
- Current policy version: **1.0.0** (see JSON header). Update the version string and `last_updated` timestamp whenever the policy changes.
- The hygiene script (`scripts/check_repo_hygiene.py`) reads the policy; CI and Husky invoke it automatically. A PR that fails the check cannot merge.
- Add a note to your PR description summarizing the policy change (“policy_version ➜ 1.1.0 – allow storage/export-assets”).
- A quarterly “Repository Hygiene Audit” task exists in `docs/build/PRODUCTION_TASKS.md` to review the policy and prune `logs/` and `docs/memorialization/` as needed.
- Contributors should never bypass the hygiene hook; if an emergency disable is required (`SKIP_QA=1`), leave a follow-up task to re-enable and fix the underlying issue.
