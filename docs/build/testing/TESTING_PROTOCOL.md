```markdown
# Automated Testing Protocol

Use this checklist whenever another LLM (or developer) needs to exercise Selenite's automated test suites. It assumes the repo root is `./Selenite`.

When a defect is found, always ask: “Why didn’t tests catch this?” and add/adjust a test to cover it as part of the fix.

## 0. One-Command Runner (recommended)

From a PowerShell prompt in the repo root, run:

```powershell
.\run-tests.ps1
```

This script mirrors the sections below:

- Ensures the backend virtualenv exists (creating it and installing requirements if necessary) and runs `pytest --maxfail=1 --disable-warnings --cov=app`.
- Ensures frontend dependencies are installed, then runs `npm run test:coverage` followed by `npm run coverage:summary`.
- Executes the Playwright “full” suite via `npm run e2e:full` (which launches the production backend/frontend harness automatically).
- Captures the entire console transcript and copies coverage/Playwright artifacts into `docs/memorialization/test-runs/<timestamp>-<suites>` (gitignored) for the memorialization log.

Optional switches:

| Switch | Description |
|--------|-------------|
| `-SkipBackend`, `-SkipFrontend`, `-SkipE2E` | Skip that portion of the suite (e.g., `.\run-tests.ps1 -SkipE2E`). |
| `-ForceBackendInstall`, `-ForceFrontendInstall` | Reinstall dependencies even if `.venv` / `node_modules` already exist. |

Use this script for workflows so you don't need to interpret the entire protocol. The remaining sections document the manual commands for environments where custom ordering is required. If you run tests manually (e.g., `npm run e2e:full` by itself), copy the resulting logs/coverage/Playwright report into `docs/memorialization/test-runs/<timestamp>-manual` to keep the historical record complete.

`run-tests.ps1` also ensures the production ports are free before the Playwright run by killing any process bound to `8100` (API) or `5173` (frontend). That guarantees the concurrent bootstrap script doesn't immediately crash with "port already in use" errors.

All temporary environment overrides are reverted at the end of the run, so your shell will still launch the backend in production mode afterward.

For a file-by-file inventory of tests, see `docs/build/testing/TEST_INVENTORY.md` (what each test covers and the expected “green” outcome).

### Temporary test database & storage

`run-tests.ps1` always:

1. Sets `ENVIRONMENT=testing`.
2. Points `DATABASE_URL` at a dedicated SQLite file (`selenite.test.db`) in the repo root.
3. Redirects uploads/transcripts to `storage/test-media` and `storage/test-transcripts`.
4. Deletes the temporary DB and those folders after the suites finish.

When executing suites manually, reproduce that isolation before running any tests, e.g.:

```powershell
$env:ENVIRONMENT = "testing"
$env:DATABASE_URL = "sqlite+aiosqlite:///$(Join-Path (Get-Location) 'selenite.test.db')"
$env:MEDIA_STORAGE_PATH = "$(Join-Path (Get-Location) 'storage/test-media')"
$env:TRANSCRIPT_STORAGE_PATH = "$(Join-Path (Get-Location) 'storage/test-transcripts')"
```

Before the suites start it deletes any stale `selenite.test.db` / `storage/test-*` contents, and after the run it removes the fresh artifacts so production data remains pristine. Never run tests against `selenite.db`.

### Composite summary output

`run-tests.ps1` captures the entire console transcript and ends by printing a summary table:

```
=== Composite Test Summary ===
Suite     Status Details
-----     ------ -------
Backend   PASS   pytest --cov=app
Frontend  PASS   npm run test:coverage && npm run coverage:summary
E2E       PASS   npm run e2e:full
Artifacts saved to: docs/memorialization/test-runs/20251121-145758-backend+frontend+e2e
Full transcript: docs/memorialization/test-runs/20251121-145758-backend+frontend+e2e/run-tests.log
```

Review that summary first; if anything failed, the transcript + coverage artifacts in the referenced folder provide the full context.

After cleanup, the runner executes `python scripts/check_repo_hygiene.py` to confirm the repo tree has no unexpected databases, storage directories, or leftover Playwright artifacts. If hygiene fails, the command exits non‑zero and the overall test run fails.

---

## 1. Backend (pytest + coverage)

### Environment
1. Ensure Python ≥ 3.10 is active. The repo ships with `.env.test`, which is automatically loaded by `Settings` in testing mode (see `backend/app/config.py`). Do not rename it; override values locally if needed.
2. Create/activate a virtualenv if desired.
3. Install dependencies (includes pytest, coverage, async stack, Whisper shim):
   ```bash
   cd backend
   pip install -r requirements-minimal.txt
   python -m alembic upgrade head
   python -m app.seed
   ```
   > Tip: The requirements file already pins `aiosqlite`, `pytest-asyncio`, etc. No extra flags necessary.

### Running the Suite
Execute the entire backend suite with coverage:
```bash
cd backend
pytest --maxfail=1 --disable-warnings --cov=app
```

Latest run (21 Nov 2025) finished in ~173 s with **81 % overall statement coverage**. Highlights:
- `app/routes/jobs.py` remains at 86 %; `app/routes/settings.py` and `app/routes/transcripts.py` hold at 97 % and 93 %.
- Authentication stack is uniformly green (routes + service ≈87 %); Whisper internals sit at 92 %.
- Queue internals climbed to 83 % thanks to the new defensive tests. The only sub-85 % areas left are `app/services/transcription.py` (80 %) and utility helpers like `file_validation` (78 %); tackle those when they change.

#### Notes
- **Logging/Queue:** The test-aware logging/queue configuration means no extra setup is required. The `TranscriptionJobQueue` stays dormant unless a test starts it explicitly, preventing stray “Event loop is closed” errors.
- **Warnings:** Pydantic emits a few namespace deprecation warnings; these are known and harmless. Failures should not occur unless code changes introduce regressions.
- **Runtime:** The full suite takes ~2 minutes. If your shell/CI has a default timeout, bump it (e.g., `PYTEST_ADDOPTS="--maxfail=1 --disable-warnings --cov=app"` with a 600 s job limit) to prevent spurious cancellations.
- **Artifacts:** Coverage summary prints to stdout. If you need HTML coverage, append `--cov-report=html` and collect files from `backend/htmlcov/`.
- **Traceability:** Requirement-to-test mapping lives in `docs/build/testing/TEST_MATRIX.md`.
- **Root convenience:** `pytest.ini` sets `pythonpath = backend`, so running `pytest` from the repo root works the same as `cd backend && pytest`.

---

## 2. Frontend (Vitest + coverage)

### Environment
1. Ensure Node.js 18.x is installed (Vite warns if <20 but still runs).
2. Install dependencies (includes Vitest, Playwright, `v8-to-istanbul` for coverage conversion):
   ```bash
   cd frontend
   npm install
   ```
   > This pulls `@vitest/coverage-v8@1.6.1`, which fixes the previous “Cannot find dependency '@rollup/rollup-linux-x64-gnu'” issue.

### Running the Suite
Capture unit/integration tests with coverage and emit the JSON summary:
```bash
cd frontend
npm run test:coverage
npm run coverage:summary
```

#### Notes
- **Output:** The run prints a text summary and writes raw V8 payloads into `frontend/coverage/.tmp/`. `npm run coverage:summary` converts those files into `frontend/coverage/coverage-summary.json` and prints a concise table (statements/branches/functions/lines) for documentation.
- **Warnings:** The current RTL suite is warning-free. If a new test mutates React state outside of `act(...)`, wrap it in `await act(...)` to keep the log clean.
- **Coverage:** Expect roughly 90 % statements, 92 % branches, and 69 % functions across ~160 tests. Investigate any significant drop below the watermark (≥ 60 % overall statements; ≥ 85 % shared components/hooks) before merging.
- **CI parity:** The GitHub Actions workflow now runs `npm run test:coverage` followed by `npm run coverage:summary` and uploads `frontend/coverage/coverage-summary.json` as a build artifact, so PR reviewers can verify the metrics without rerunning the suite locally.

---

## 3. End-to-End (Playwright)

> Only run when the backend + frontend servers are available (locally or via Docker).

1. Launch backend API (`ENVIRONMENT=production uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir ../backend/app`) and frontend (`npm run start:prod -- --host 127.0.0.1 --port 5173`) or let Playwright start them via `npm run e2e:full` (which builds and serves the production bundle automatically).
2. Execute Playwright suite:
   ```bash
   cd frontend
   npm run e2e:full
   ```
3. Results are stored in `frontend/playwright-report/`.

Latest CI summary and known flaky tests live in `docs/build/testing/E2E_TEST_REPORT.md`.

---

## 4. Smoke Test (Manual + automated check)

Before any hands-on validation, run the backend smoke test to ensure `/health` and `/auth/login` behave correctly (this waits for readiness and uses the seed `admin/changeme` account):

```bash
python scripts/smoke_test.py --base-url http://127.0.0.1:8100
```

Once that succeeds, follow `docs/build/testing/SMOKE_TEST.md` for the interactive flow (login → upload → monitor → download).

---

### Troubleshooting Quick Reference

| Symptom | Fix |
|--------|-----|
| `ModuleNotFoundError: aiosqlite` | `pip install -r backend/requirements-minimal.txt` |
| `Cannot find module '@rollup/rollup-linux-x64-gnu'` during Vitest | Re-run `npm install` after removing `frontend/node_modules` & `package-lock.json` |
| Need JSON coverage summary for docs/CI | Run `npm run coverage:summary` after `npm run test:coverage` to populate `frontend/coverage/coverage-summary.json` |
| Need backend specs-to-tests mapping | Refer to `docs/build/testing/TEST_MATRIX.md` for the canonical traceability matrix |
| Playwright Firefox tests hit `NS_ERROR_CONNECTION_REFUSED` | Increase Playwright server timeout or rerun; Chromium/WebKit still validate flows |

Document updated: November 21 2025.

---

## MVP Testing Watermark
All current and future Selenite-like projects must satisfy these four pillars to declare automated testing complete (excluding explicitly human-only checks):

1. **Requirements Traceability** – Every MVP requirement (components, APIs, production tasks) maps to at least one automated test. Maintain a matrix or checklist linking specs to tests before release.
2. **Layered Test Suite** – Pyramid coverage consisting of:
   - Unit tests for business logic, utils, services.
   - Integration/API tests hitting live FastAPI + database.
   - UI component tests (Vitest/RTL) for all reusable widgets/pages.
   - E2E workflows (Playwright) covering login → upload → monitor → tag/export/settings flows, plus key negative paths.
3. **Coverage & Static Quality Gates** – Minimum coverage thresholds enforced in CI (backend ≥70 % statements overall and ≥60 % for critical modules; frontend ≥60 % statements overall and ≥85 % on shared components/hooks). Linters, type-checks, and security scans must pass.
4. **Repeatable Execution Protocol** – Documented installation + execution steps (this file) that any agent can run end-to-end, with logs/artifacts saved for audit. CI mirrors the same protocol on every PR/main merge.

Only when all four pillars are satisfied—and manual UX/media reviews are complete—can an MVP be declared release-ready.

### Path to Meet the Watermark

Current focus areas (Nov 2025): traceability matrix + documentation are in place, backend coverage ≥70 %, and frontend is above the 60 % watermark. Continue hardening weak spots via this action plan:

1. **Traceability Matrix**
   - Keep `docs/build/testing/TEST_MATRIX.md` updated whenever specs or tests change. All new features must link to at least one automated test before merge.
2. **Backend Coverage ≥70%**
   - Maintain ≥70 % statements overall and ≥60 % per critical module. With transcripts/settings/startup/auth/whisper now ≥85 %, focus on `app/services/auth.py` (68 %), `app/services/job_queue.py` (72 %), and any new modules introduced by upcoming work.
   - Add focused unit tests for utility functions (export formatting, queue edge cases, search highlighters) whenever regression bugs are fixed.
3. **Frontend Coverage ≥60% / Components ≥85%**
   - Add Vitest specs for `Dashboard.tsx`, API service wrappers, and Toast context.
   - Improve assertions in existing component tests to raise branch/function coverage.
4. **CI Enforcement**
   - Update pipeline to fail if coverage drops below the thresholds and if the traceability matrix is missing entries for new specs.
```
