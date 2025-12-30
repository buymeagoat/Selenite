```markdown
# Testing Traceability Matrix

| Requirement / Spec | Implementation | Automated Test Coverage |
|--------------------|----------------|-------------------------|
| COMPONENT_SPECS: Dashboard list, search, filters | `frontend/src/pages/Dashboard.tsx` | `frontend/src/tests/Dashboard.test.tsx` (jobs load + search filtering) |
| COMPONENT_SPECS: New Job Modal workflows | `frontend/src/components/modals/NewJobModal.tsx` | `frontend/src/tests/NewJobModal.test.tsx` |
| COMPONENT_SPECS: Job detail modal actions | `frontend/src/components/modals/JobDetailModal.tsx` | `frontend/src/tests/JobDetailModal.test.tsx` |
| COMPONENT_SPECS: Tag input/tag list components | `frontend/src/components/tags/*` | `frontend/src/tests/TagInput.test.tsx`, `TagList.test.tsx`, `TagBadge.test.tsx` |
| COMPONENT_SPECS: Toast notifications | `frontend/src/context/ToastContext.tsx` | `frontend/src/tests/ToastContext.test.tsx` |
| COMPONENT_SPECS: Transcript view/download | `frontend/src/pages/TranscriptView.tsx` | `frontend/src/tests/TranscriptView.test.tsx` |
| COMPONENT_SPECS: Auth/login page | `frontend/src/pages/Login.tsx` | `frontend/src/tests/Login.test.tsx`; E2E: `frontend/e2e/tests/auth.spec.ts` |
| COMPONENT_SPECS: Protected routing/navbar | `frontend/src/components/layout/*` | `frontend/src/tests/ProtectedRoute.test.tsx`, `Navbar.test.tsx` |
| COMPONENT_SPECS: Upload/file validation | `frontend/src/components/upload/FileDropzone.tsx` | `frontend/src/tests/FileDropzone.test.tsx`; backend validation (`backend/tests/test_file_validation.py`) |
| API Spec: Auth (`/auth/login`, `/auth/password`) | `backend/app/routes/auth.py` | `backend/tests/test_auth_routes.py`, `backend/tests/test_password_change.py` |
| API Spec: Jobs CRUD (`/jobs`, `/jobs/{id}` etc.) | `backend/app/routes/jobs.py` | `backend/tests/test_job_routes.py`, `backend/tests/test_job_actions.py`, `backend/tests/test_job_defaults.py` |
| API Spec: Tag management (`/tags`, `/jobs/{id}/tags`) | `backend/app/routes/tags.py`, `backend/app/routes/jobs.py` | `backend/tests/test_tag_routes.py`, `backend/tests/test_job_routes.py::TestJobTagAssignments` |
| API Spec: Exports (`/jobs/{id}/export`) | `backend/app/routes/exports.py` | `backend/tests/test_exports_route.py`, `backend/tests/test_exports.py`, `backend/tests/test_export_service_unit.py` |
| API Spec: Transcripts (`/transcripts/{job_id}`) | `backend/app/routes/transcripts.py` | `backend/tests/test_transcript_routes.py` |
| API Spec: Search (`/search`) | `backend/app/routes/search.py` | `backend/tests/test_search.py` |
| API Spec: Settings (`/settings`) | `backend/app/routes/settings.py` | `backend/tests/test_settings.py` |
| Services: Job queue / cancellation | `backend/app/services/job_queue.py` | `backend/tests/test_job_actions.py`, `backend/tests/test_job_routes.py::TestJobLifecycleActions` |
| Services: Whisper wrapper | `backend/app/services/whisper_service.py` | `backend/tests/test_whisper_service.py`, `backend/tests/test_transcription.py` |
| Services: Export formats | `backend/app/services/export_service.py` | `backend/tests/test_export_service_unit.py`, `backend/tests/test_exports.py` |
| Middleware: Rate limiting, security headers | `backend/app/middleware/*` | `backend/tests/test_rate_limit.py`, `backend/tests/test_security_headers.py` |
| E2E: Upload -> transcribe -> export | Full stack via Playwright | `frontend/e2e/tests/jobs.spec.ts`, `frontend/e2e/tests/transcript.spec.ts` |
| Smoke/health checks | `scripts/smoke_test.py`, `/health` route | `scripts/smoke_test.py` (manual + CI), `backend/tests/test_startup_checks.py` |
```
