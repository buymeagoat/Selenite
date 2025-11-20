```markdown
# Automated Testing Protocol

Use this checklist whenever another LLM (or developer) needs to exercise Selenite’s automated test suites. It assumes the repo root is `./Selenite`.

---

## 1. Backend (pytest + coverage)

### Environment
1. Ensure Python ≥ 3.10 is active.
2. Create/activate a virtualenv if desired.
3. Install dependencies (includes pytest, coverage, async stack, Whisper shim):
   ```bash
   cd backend
   pip install -r requirements-minimal.txt
   ```
   > Tip: The requirements file already pins `aiosqlite`, `pytest-asyncio`, etc. No extra flags necessary.

### Running the Suite
Execute the entire backend suite with coverage:
```bash
cd backend
pytest --cov=app
```

#### Notes
- **Logging/Queue:** The test-aware logging/queue configuration means no extra setup is required. The `TranscriptionJobQueue` stays dormant unless a test starts it explicitly, preventing stray “Event loop is closed” errors.
- **Warnings:** Pydantic emits a few namespace deprecation warnings; these are known and harmless. Failures should not occur unless code changes introduce regressions.
- **Artifacts:** Coverage summary prints to stdout. If you need HTML coverage, append `--cov-report=html` and collect files from `backend/htmlcov/`.

---

## 2. Frontend (Vitest + coverage)

### Environment
1. Ensure Node.js 18.x is installed (Vite warns if <20 but still runs).
2. Install dependencies (includes Vitest, Playwright, new coverage plugin):
   ```bash
   cd frontend
   npm install
   ```
   > This pulls `@vitest/coverage-v8@1.6.1`, which fixes the previous “Cannot find dependency '@rollup/rollup-linux-x64-gnu'” issue.

### Running the Suite
Capture unit/integration tests with coverage:
```bash
cd frontend
npm run test:coverage
```

#### Notes
- **Output:** Vitest logs results to the console. For archival, redirect to `/tmp/vitest.log`:
  ```bash
  npx vitest run --coverage --reporter=basic > /tmp/vitest.log 2>&1
  tail -n 50 /tmp/vitest.log  # show summary
  ```
- **Warnings:** `src/tests/Settings.test.tsx` currently emits React `act(...)` warnings. They do not fail the run but should be cleaned up in the future.
- **Coverage:** On Linux, expect overall coverage around 60% statements / 74% branches with 142 tests passing. Investigate major gaps (services, Dashboard) if regression occurs.

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

## 4. Smoke Test (Manual)

When a human run-through is required, follow `docs/build/testing/SMOKE_TEST.md`. It covers login → upload → monitor → download.

---

### Troubleshooting Quick Reference

| Symptom | Fix |
|--------|-----|
| `ModuleNotFoundError: aiosqlite` | `pip install -r backend/requirements-minimal.txt` |
| `Cannot find module '@rollup/rollup-linux-x64-gnu'` during Vitest | Re-run `npm install` after removing `frontend/node_modules` & `package-lock.json` |
| Vitest warns about `act(...)` in `Settings.test.tsx` | Known issue; wrap state updates in `act()` when modifying tests |
| Playwright Firefox tests hit `NS_ERROR_CONNECTION_REFUSED` | Increase Playwright server timeout or rerun; Chromium/WebKit still validate flows |

Document updated: November 19 2025.

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

Current gaps: (1) no requirements-to-tests matrix, (2) backend/front-end coverage below thresholds. Action plan:

1. **Traceability Matrix**
   - Export COMPONENT_SPECS/API requirements into a table.
   - For each item link the pytest/Vitest/Playwright test (file + case name).
   - Store as `docs/build/testing/TEST_MATRIX.md` (or similar) and update whenever specs/tests change.
2. **Backend Coverage ≥70%**
   - Target low-covered modules called out in the coverage report (`app/routes/exports.py`, `app/routes/jobs.py`, `app/services/whisper_service.py`, etc.).
   - Add focused unit tests for utility functions (export formatting, queue edge cases, search highlighters).
   - Add integration tests for error paths currently untested (e.g., restart invalid job, export denied access).
3. **Frontend Coverage ≥60% / Components ≥85%**
   - Add Vitest specs for `Dashboard.tsx`, API service wrappers, and Toast context.
   - Improve assertions in existing component tests to raise branch/function coverage.
4. **CI Enforcement**
   - Update pipeline to fail if coverage drops below the thresholds and if the traceability matrix is missing entries for new specs.
```
