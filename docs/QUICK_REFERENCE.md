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
**Files to create**: `tests/e2e/*.spec.js`
**Test command**: `npm run test:e2e`
**Commit**: `[Testing] Add end-to-end test suite with Playwright`

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

- [ ] Increment 1: Project Scaffolding ✓
- [ ] Increment 2: Authentication ✓
- [ ] Increment 3: Job Creation ✓
- [ ] Increment 4: Job Listing ✓
- [ ] Increment 5: Transcription ✓
- [ ] Increment 6: Export ✓
- [ ] Increment 7: Tags ✓
- [ ] Increment 8: Search ✓
- [ ] Increment 9: Settings ✓
- [ ] Increment 10: Frontend Foundation ✓
- [ ] Increment 11: Dashboard ✓
- [ ] Increment 12: Upload Modal ✓
- [ ] Increment 13: Detail Modal ✓
- [ ] Increment 14: Search UI ✓
- [ ] Increment 15: Tag UI ✓
- [ ] Increment 16: Settings Page ✓
- [ ] Increment 17: Progress Updates ✓
- [ ] Increment 18: Polish ✓
- [ ] Increment 19: E2E Tests ✓
- [ ] Increment 20: Production ✓

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

- **DEVELOPMENT_PLAN.md**: Complete project blueprint
- **API_CONTRACTS.md**: All API endpoint specifications
- **COMPONENT_SPECS.md**: All React component specifications
- **PRE_BUILD_VERIFICATION.md**: Senior developer approval and assessment

---

**Keep this document open during development for quick reference to commands, patterns, and workflows.**
