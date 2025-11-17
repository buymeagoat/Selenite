# Quick Reference Guide - Build Execution

## Overview
This guide provides quick reference for executing the Selenite build process. Refer to DEVELOPMENT_PLAN.md for complete details.

---

## Pre-Flight Checklist

Before starting any build increment:
- [ ] Git status clean (all changes committed)
- [ ] Backend virtual environment activated
- [ ] All tests passing from previous increment
- [ ] Development servers running (if testing integration)

---

## Build Increment Quick Reference

### Increment 1: Project Scaffolding & Database
**Files to create**: `backend/app/models/*.py`, `backend/alembic/versions/001_*.py`, `backend/tests/test_database.py`
**Test command**: `pytest tests/test_database.py -v`
**Commit**: `[Setup] Initialize project structure with database models and migrations`

### Increment 2: Authentication System
**Files to create**: `backend/app/utils/security.py`, `backend/app/routes/auth.py`, `backend/app/services/auth.py`, `backend/tests/test_auth.py`
**Test command**: `pytest tests/test_auth.py -v`
**Commit**: `[Backend/Auth] Implement JWT authentication with login endpoint`

### Increment 3: Job Creation Without Transcription
**Files to create**: `backend/app/utils/file_handling.py`, `backend/app/routes/jobs.py`, `backend/tests/test_jobs.py`
**Test command**: `pytest tests/test_jobs.py::test_create_job_success -v`
**Commit**: `[Backend/Jobs] Add job creation endpoint with file upload handling`

### Increment 4: Job Listing & Retrieval
**Files to modify**: `backend/app/routes/jobs.py`
**Test command**: `pytest tests/test_jobs.py::test_list_jobs -v`
**Commit**: `[Backend/Jobs] Add job listing and detail retrieval endpoints`

### Increment 5: Real Transcription Engine
**Files to create**: `backend/app/services/transcription.py`, `backend/app/services/job_queue.py`, `backend/tests/test_transcription.py`
**Test command**: `pytest tests/test_transcription.py -v`
**Commit**: `[Backend/Transcription] Implement Whisper transcription with job queue`

### Increment 6: Export Formats
**Files to create**: `backend/app/services/export.py`, `backend/tests/test_export.py`
**Test command**: `pytest tests/test_export.py -v`
**Commit**: `[Backend/Export] Add transcript export in 6 formats`

### Increment 7: Tag System
**Files to create**: `backend/app/routes/tags.py`, `backend/tests/test_tags.py`
**Test command**: `pytest tests/test_tags.py -v`
**Commit**: `[Backend/Tags] Implement tag management and job-tag associations`

### Increment 8: Search Functionality
**Files to create**: `backend/app/services/search.py`, `backend/tests/test_search.py`
**Test command**: `pytest tests/test_search.py -v`
**Commit**: `[Backend/Search] Add full-text search across job metadata and transcripts`

### Increment 9: Settings & System Control
**Files to create**: `backend/app/routes/system.py`, `backend/tests/test_settings.py`
**Test command**: `pytest tests/test_settings.py -v`
**Commit**: `[Backend/Settings] Add user settings and system control endpoints`

### Increment 10: Frontend Foundation
**Files to create**: `frontend/src/pages/Login.jsx`, `frontend/src/context/AuthContext.jsx`, `frontend/tests/Login.test.jsx`
**Test command**: `npm test`
**Commit**: `[Frontend/Setup] Initialize React app with authentication flow`

### Increment 11: Dashboard Layout & Job Cards
**Files to create**: `frontend/src/components/jobs/JobCard.jsx`, `frontend/src/pages/Dashboard.jsx`
**Test command**: `npm test`
**Commit**: `[Frontend/Dashboard] Add job listing dashboard with cards and status indicators`

### Increment 12: New Job Modal
**Files to create**: `frontend/src/components/modals/NewJobModal.jsx`, `frontend/src/components/upload/FileDropzone.jsx`
**Test command**: `npm test`
**Commit**: `[Frontend/Upload] Add new job modal with file upload interface`

### Increment 13: Job Detail Modal
**Files to create**: `frontend/src/components/modals/JobDetailModal.jsx`, `frontend/src/components/common/AudioPlayer.jsx`
**Test command**: `npm test`
**Commit**: `[Frontend/JobDetail] Add job detail modal with media playback and actions`

### Increment 14: Search & Filters
**Files to create**: `frontend/src/components/common/SearchBar.jsx`, `frontend/src/components/jobs/JobFilters.jsx`
**Test command**: `npm test`
**Commit**: `[Frontend/Search] Add search and filtering capabilities to job list`

### Increment 15: Tag Management UI
**Files to create**: `frontend/src/components/tags/TagInput.jsx`, `frontend/src/components/tags/TagList.jsx`
**Test command**: `npm test`
**Commit**: `[Frontend/Tags] Add tag management interface with autocomplete`

### Increment 16: Settings Page
**Files to create**: `frontend/src/pages/Settings.jsx`
**Test command**: `npm test`
**Commit**: `[Frontend/Settings] Add settings page with password change and defaults`

### Increment 17: Real-time Progress Updates
**Files to create**: `frontend/src/hooks/usePolling.js`
**Test command**: `npm test`
**Commit**: `[Frontend/Progress] Add real-time job progress updates via polling`

### Increment 18: Polish & Responsive Design
**Files to modify**: Multiple components for mobile optimization
**Test command**: Manual testing on mobile/tablet/desktop
**Commit**: `[Frontend/Polish] Add mobile responsive design and UI polish`

### Increment 19: End-to-End Testing
**Status**: In progress – Playwright configured (multi-browser); smoke tests (login, new job modal, tags placeholder) passing; CI workflow active
**Files**: `playwright.config.ts`, `e2e/fixtures/auth.ts`, `e2e/login.spec.ts`, `e2e/new-job.spec.ts`, `e2e/tags.spec.ts`
**Next**: Add specs for transcription lifecycle; job detail actions; tag assign/filter; search; settings password change; cancel & restart job
**Test command**: `npm run e2e` (CI: `npm run e2e:ci`)
**Commit**: `[Testing] Extend E2E <feature>`

### Increment 20: Production Readiness
**Files to create**: `Dockerfile`, `docker-compose.yml`, `docs/DEPLOYMENT.md`
**Test command**: Build production artifacts, deploy to test environment
**Commit**: `[Deploy] Add production configuration and deployment documentation`

---

## Quality Gate Commands

### Backend Quality Checks
```powershell
# Navigate to backend
cd backend

# Run all tests with coverage
pytest -v --cov=app --cov-report=term-missing --cov-fail-under=80

# Check code formatting
black app/ tests/ --check

# Run linter
ruff app/ tests/

# Type checking (if using mypy)
mypy app/
```

### Frontend Quality Checks
```powershell
# Navigate to frontend
cd frontend

# Run all tests with coverage
npm test -- --coverage --watchAll=false

# Run linter
npm run lint

# Build check
npm run build
```

### Manual Smoke Test Template
```
1. Start backend: cd backend && python -m app.main
2. Start frontend: cd frontend && npm run dev
3. Navigate to http://localhost:5173
4. Test the feature implemented in this increment:
   - [ ] Feature works as expected
   - [ ] No console errors
   - [ ] Error states handled gracefully
   - [ ] Responsive design works
5. Document any issues found
```

---

## Commit Workflow

### Standard Commit Process
```powershell
# 1. Ensure all tests pass
pytest -v  # or npm test

# 2. Format code
black .    # or npm run lint -- --fix

# 3. Check git status
git status

# 4. Stage changes
git add -A

# 5. Commit with proper message
git commit -m "[Component] Brief description"

# 6. Push to remote (if working with remote)
git push origin develop
```

### Commit Message Examples
```
✅ Good:
[Backend/Auth] Implement JWT token generation and validation with tests
[Frontend/Login] Add login form with validation and error handling
[Database] Create initial schema migration for users and jobs tables

❌ Bad:
Fixed bug
Updated files
WIP
```

---

## Common Commands

### Backend Development
```powershell
# Activate virtual environment (Windows)
& .venv\Scripts\Activate.ps1

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Run backend server
python -m app.main

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test
pytest tests/test_auth.py::test_login_success -v

# Run tests with output
pytest -v -s

# Generate coverage report
pytest --cov=app --cov-report=html
```

### Frontend Development
```powershell
# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run specific test file
npm test -- JobCard.test.jsx

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Fix linting issues
npm run lint -- --fix
```

### Database Management
```powershell
# Create new migration
alembic revision --autogenerate -m "Add column to jobs table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration
alembic current

# Show migration history
alembic history

# Reset database (caution!)
# Delete selenite.db file, then:
alembic upgrade head
```

---

## Troubleshooting

### Backend Issues

**Issue**: ModuleNotFoundError
```powershell
# Solution: Ensure virtual environment is activated and dependencies installed
& .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**Issue**: Alembic migration fails
```powershell
# Solution: Check database is not locked, reset if needed
alembic downgrade -1
alembic upgrade head
```

**Issue**: Tests fail with import errors
```powershell
# Solution: Install package in editable mode
pip install -e .
```

### Frontend Issues

**Issue**: Module not found errors
```powershell
# Solution: Reinstall dependencies
Remove-Item node_modules -Recurse -Force
npm install
```

**Issue**: Port already in use
```powershell
# Solution: Kill process on port 5173
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

**Issue**: Tests fail to run
```powershell
# Solution: Clear cache and retry
npm test -- --clearCache
npm test
```

---

## Progress Tracking

### Increment Checklist
Use this to track overall progress:

- [x] Increment 1: Project Scaffolding
- [x] Increment 2: Authentication
- [x] Increment 3: Job Creation
- [x] Increment 4: Job Listing
- [x] Increment 5: Transcription (engine baseline)
- [x] Increment 6: Export
- [x] Increment 7: Tags
- [x] Increment 8: Search
- [x] Increment 9: Settings (Backend complete)
- [x] Increment 10: Frontend Foundation
- [x] Increment 11: Dashboard
- [x] Increment 12: Upload Modal
- [x] Increment 13: Detail Modal
- [x] Increment 14: Search UI
- [x] Increment 15: Tag UI
- [x] Increment 16: Settings Page
- [x] Increment 17: Progress Updates
- [x] Increment 18: Polish
- [ ] Increment 19: E2E Tests (in progress – smoke passing)
- [ ] Increment 20: Production

---

## Emergency Procedures

### If Tests Break
1. Don't panic - this is why we have tests
2. Read the test output carefully
3. Fix the issue (don't skip tests!)
4. Re-run tests until passing
5. Only then commit

### If You Need to Refactor
1. Ensure current tests pass
2. Make refactoring changes
3. Ensure tests still pass
4. Commit with message: `[Refactor] Description`

### If You Discover a Bug
1. Write a failing test that demonstrates the bug
2. Fix the bug
3. Verify test now passes
4. Commit with message: `[Fix] Description of bug`

---

## Reference Documents


## Playwright E2E Quick Reference

### Current Smoke Coverage
- Login authentication & dashboard load
- New Job Modal opens; file attach + model select
- Tags placeholder modal accessible

### Coverage Roadmap
1. Transcription workflow (queue→processing→completed)
2. Job detail actions (transcript view & export menu presence)
3. Tag create, assign, filter
4. Search (filename + transcript highlight validation)
5. Settings password change & re-login
6. Cancel processing job & restart completed job
7. Negative paths (invalid login, submit w/o file, cancel completed)

Use role/name selectors first; fallback to `data-testid` only where semantics insufficient.

### Scripts
```powershell
# Run all E2E tests (auto-starts Vite via webServer config)
npm run e2e
# Open UI mode (interactive)
npm run e2e:ui
# Debug single test (headed, inspector)
npm run e2e:debug -- --grep "Login Flow"
# Show last HTML report
npm run e2e:report
```

### Common Tasks
```powershell
# Update browsers (after version bump)
npx playwright install
# Generate new trace on failure (already on-first-retry)
# Set TRACE=on to force trace collection for every test
$env:TRACE='on'; npm run e2e; Remove-Item Env:TRACE
```

### Selectors Strategy
- Prefer role + accessible name (e.g., getByRole('button', { name: 'Selenite' })).
- Use data-testid only for non-semantic elements; attributes standardized as data-testid.
- Avoid brittle text selectors tied to dynamic content.

### Troubleshooting
| Symptom | Likely Cause | Fix |
| ------- | ------------ | ---- |
| Connection refused | Dev server not started | webServer auto-start; else run `npm run dev` |
| Missing browsers in CI | Install step skipped | `npx playwright install --with-deps` |
| getByTestId not found | Attribute mismatch | Ensure `data-testid` present |
| Timeout after login | App still rendering | Wait for heading `Transcriptions` before actions |
| Trace not generated | Test didn't retry | Set TRACE env or force failing scenario |

### CI Integration (Example GitHub Action)
Add workflow `.github/workflows/e2e.yml` (see repository) executing:
```yaml
steps:
   - uses: actions/checkout@v4
   - uses: actions/setup-node@v4
      with:
         node-version: 20
         cache: 'npm'
   - run: npm ci
   - run: npx playwright install --with-deps
   - run: npm run e2e:ci
```

### Environment Overrides
- Set `BASE_URL` to point tests at deployed environment (staging) instead of local Vite.
- Use `CI=true` to enable retries and non-reuse of dev server.

### Quick Health Check Before Commit
```powershell
npm test
npm run e2e -- --grep "Login Flow"
# (Optional broader E2E run)
npm run e2e
```

---

## QA Gateway Automation

### Overview
Selenite uses a **three-tier QA gateway** to enforce quality standards before code reaches production:
- **Tier 1 (Pre-commit)**: Local hooks validate commit format, code style, type-checking, and quick unit tests (<30s)
- **Tier 2 (Push CI)**: GitHub Actions runs full test suites, coverage checks, and E2E smoke tests (~5min)
- **Tier 3 (PR CI)**: Complete E2E multi-browser suite, performance checks, coverage ratcheting (~15min)

All tiers follow "shift-left" philosophy: catch defects early when fixes are cheapest.

### Installation

#### Automated Setup (Recommended)
```powershell
# Run from repository root
.\scripts\install-hooks.ps1
```

This installs both `pre-commit` and `commit-msg` hooks automatically. Run this after cloning the repo or when hooks are updated.

#### Verify Hook Installation
```powershell
# Check that hooks are installed
Test-Path .git\hooks\pre-commit
Test-Path .git\hooks\commit-msg
# Both should return: True
```

### Commands

#### Frontend QA
```powershell
cd frontend

# Full QA suite (type-check + lint + test)
npm run qa

# Quick checks only (type-check + lint, skips tests)
npm run qa:quick

# Auto-format code
npm run format

# Individual checks
npm run type-check
npm run lint
npm run test
npm run test:coverage
```

#### Backend QA
```powershell
cd backend

# Full QA suite (format + lint + test)
make qa

# Quick checks only (format + lint, skips tests)
make qa-quick

# Auto-format code
make format

# Individual checks
make lint
make test
make coverage  # Generates HTML report in htmlcov/
```

### Pre-Commit Hook Validation

The pre-commit hook runs automatically on `git commit` and performs four stages:

**Stage 1: Commit Message Format**
- Must follow: `[Component] Description` (min 10 chars after prefix)
- Example: `[Frontend/Dashboard] Add job filtering by status`
- Rejects markers: WIP, fixup, temp, test, TODO

**Stage 2: Backend Checks** (if Python files changed)
- Code formatting (black)
- Linting (ruff)
- Unit tests for changed files

**Stage 3: Frontend Checks** (if TypeScript files changed)
- Type checking (tsc)
- Linting (ESLint)
- Unit tests for changed files

**Stage 4: Documentation Warnings** (non-blocking)
- Warns if API routes changed but `docs/API_CONTRACTS.md` not updated
- Warns if components changed but `docs/COMPONENT_SPECS.md` not updated

### Bypass Mechanism (Emergency Only)

**⚠️ WARNING**: Bypassing QA checks should be rare and documented.

#### Local Bypass (Pre-commit Hook)
```powershell
# Option 1: --no-verify flag
git commit --no-verify -m "[Component] Message"

# Option 2: SKIP_QA environment variable
$env:SKIP_QA='1'
git commit -m "[Component] Message"
Remove-Item Env:SKIP_QA
```

#### CI Bypass
**NOT RECOMMENDED**: CI validation cannot be bypassed. If you push code that bypassed pre-commit hooks, CI will still validate it. If CI fails, the push will be flagged and PRs will be blocked.

#### When to Bypass
- Critical hotfix needed immediately (production outage)
- Working around temporary tooling issues
- Experimental branch that won't be merged

#### After Bypassing
1. Create follow-up task to fix quality issues
2. Document reason in commit message or PR description
3. Fix issues before merging to main branch

### CI Workflow Details

#### GitHub Actions Jobs
The `.github/workflows/qa.yml` workflow runs on every push to `main`/`develop` and all PRs:

**backend-qa**:
- Python 3.11 environment
- Code formatting check (black)
- Linting check (ruff)
- Full test suite with coverage
- Fails if coverage < 80%
- Uploads coverage to Codecov

**frontend-qa**:
- Node.js 20 environment
- Type checking (TypeScript)
- Linting check (ESLint)
- Full test suite with coverage
- Fails if coverage < 70%
- Uploads coverage to Codecov

**e2e-smoke**:
- Runs after backend-qa and frontend-qa pass
- Installs Playwright with Chromium
- Runs smoke tests tagged `@smoke`
- Uploads reports/traces on failure

**security-audit**:
- Backend: pip-audit on requirements
- Frontend: npm audit (moderate+ severity)

#### Viewing CI Results
```powershell
# Push code to trigger CI
git push origin <branch>

# View workflow runs on GitHub
# Navigate to: https://github.com/<username>/Selenite/actions
```

#### Artifacts on Failure
CI automatically uploads artifacts when tests fail:
- `backend-test-results`: pytest XML reports
- `frontend-test-results`: Vitest results
- `e2e-smoke-results`: Playwright HTML report, traces, videos

### Coverage Tracking

#### Local Coverage Reports
```powershell
# Backend (HTML report)
cd backend
make coverage
# Open htmlcov/index.html in browser

# Frontend (CLI + JSON)
cd frontend
npm run test:coverage
# View coverage/index.html
```

#### Codecov Integration
After configuring Codecov:
1. Sign up at https://codecov.io
2. Add repository and get token
3. Add `CODECOV_TOKEN` to GitHub Secrets
4. Coverage badges auto-update in README

### Troubleshooting QA Issues

#### "black check failed"
```powershell
cd backend
make format  # Auto-fixes formatting
git add -A
git commit -m "[Component] Message"
```

#### "ESLint errors detected"
```powershell
cd frontend
npm run format  # Auto-fixes linting
git add -A
git commit -m "[Component] Message"
```

#### "TypeScript type errors"
```powershell
cd frontend
npm run type-check  # Shows type errors
# Fix errors manually
git add -A
git commit -m "[Component] Message"
```

#### "Unit tests failed"
```powershell
# Run tests to see failures
npm test  # or pytest -v

# Fix failing tests
# Re-run to verify
npm test  # or pytest -v

git commit -m "[Component] Message"
```

#### "Coverage below threshold"
```powershell
# Check current coverage
npm run test:coverage  # or make coverage

# Add missing tests
# Re-run coverage check

git commit -m "[Component] Message"
```

#### "Pre-commit hook not running"
```powershell
# Reinstall hooks
cd frontend
npx husky install

# Verify hook exists and is executable
Test-Path ..\.husky\pre-commit
```

#### "CI failing but local passes"
- Check if you bypassed pre-commit hooks locally
- Ensure all dependencies installed in CI (check workflow YAML)
- Review CI logs for environment differences
- Run full QA suite locally: `npm run qa && cd ../backend && make qa`

---

**Keep this document open during development for quick reference to commands, patterns, and workflows.**
