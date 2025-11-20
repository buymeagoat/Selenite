# MVP Requirement-to-Test Matrix

Mapping of current MVP requirements to automated tests (unit, integration, or E2E). Update whenever specs or tests change.

| Requirement / Spec Item | Implementation | Automated Test(s) |
|-------------------------|----------------|-------------------|
| Navbar layout & user menu | `frontend/src/components/layout/Navbar.tsx` | `frontend/src/tests/Navbar.test.tsx` |
| Sidebar navigation (desktop) | `frontend/src/components/layout/Sidebar.tsx` | `frontend/src/tests/Sidebar.test.tsx` |
| Mobile navigation | `frontend/src/components/layout/MobileNav.tsx` | `frontend/src/tests/MobileNav.test.tsx` |
| Login form validation & auth | `frontend/src/pages/Login.tsx`, `backend/app/routes/auth.py` | `frontend/src/tests/Login.test.tsx`, `frontend/e2e/login.spec.ts`, `backend/tests/test_auth_routes.py` |
| Dashboard job list, search, filters | `frontend/src/pages/Dashboard.tsx` + components | `frontend/src/tests/JobCard.test.tsx`, `frontend/src/tests/SearchBar.test.tsx`, `frontend/src/tests/JobFilters.test.tsx`, `frontend/e2e/search.spec.ts`, `frontend/e2e/transcription.spec.ts` |
| New Job Modal & upload validation | `frontend/src/components/modals/NewJobModal.tsx`, `backend/app/routes/jobs.py` | `frontend/src/tests/NewJobModal.test.tsx`, `frontend/e2e/new-job.spec.ts`, `backend/tests/test_job_routes.py` |
| Job Detail actions (download/restart/delete) | `frontend/src/components/modals/JobDetailModal.tsx`, `backend/app/routes/jobs.py`, `backend/app/routes/exports.py` | `frontend/src/tests/JobDetailModal.test.tsx`, `frontend/e2e/jobDetail.spec.ts`, `backend/tests/test_job_actions.py`, `backend/tests/test_exports.py` |
| Tag Management (create, assign, filter) | `frontend/src/components/tags/*.tsx`, `backend/app/routes/tags.py` | `frontend/src/tests/TagInput.test.tsx`, `frontend/src/tests/TagList.test.tsx`, `frontend/e2e/tagManagement.spec.ts`, `backend/tests/test_tag_routes.py` |
| Settings page + API | `frontend/src/pages/Settings.tsx`, `backend/app/routes/settings.py` | `frontend/src/tests/Settings.test.tsx`, `frontend/e2e/settings.spec.ts`, `backend/tests/test_settings.py` |
| Toast & Auth contexts | `frontend/src/context/*.tsx` | `frontend/src/tests/ToastContext.test.tsx`, `frontend/src/tests/AuthContext.test.tsx` |
| API client utilities | `frontend/src/lib/api.ts`, `frontend/src/services/*.ts` | `frontend/src/tests/api.test.ts` (TODO – expand service coverage) |
| File handling/validation | `backend/app/utils/file_handling.py`, `backend/app/utils/file_validation.py` | `backend/tests/test_file_handling.py`, `backend/tests/test_file_validation.py` |
| Job queue & transcription lifecycle | `backend/app/services/job_queue.py`, `backend/app/services/whisper_service.py` | `backend/tests/test_transcription.py` |
| Search & highlighting | `backend/app/routes/search.py`, frontend search UI | `backend/tests/test_search.py`, `frontend/e2e/search.spec.ts` |
| Security middleware & headers | `backend/app/middleware/*` | `backend/tests/test_security.py`, `backend/tests/test_security_headers.py`, `backend/tests/test_rate_limit.py` |
| Startup/health checks | `backend/app/startup_checks.py`, `/health` endpoint | `backend/tests/test_startup_checks.py`, `backend/tests/test_auth_routes.py::test_health_check` |
