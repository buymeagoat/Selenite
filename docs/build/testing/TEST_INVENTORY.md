# Test Inventory and Expected "Green" Outcomes

Audit-friendly list of automated tests with what they cover and what "pass/green" means. Use this with `scripts/run-tests.ps1` or manual runs to know exactly what's being validated.

## Backend (pytest)
| File | What it tests | Green outcome |
| --- | --- | --- |
| test_auth_routes.py | `/auth/login`, `/auth/password` flows | 200 on valid creds; proper 401/422 on bad creds; password change works |
| test_auth_service.py / test_auth_unit.py | Auth helpers (hash/verify, token handling) | Hash/verify consistent; invalid tokens rejected |
| test_database.py | DB session/engine wiring | Session creation works; no unexpected exceptions |
| test_export_service_unit.py | Export service formatting paths | Generates correct file formats/metadata without errors |
| test_exports.py / test_exports_route.py | `/jobs/{id}/export` endpoints | Supported formats return 200 with expected payload; bad requests fail cleanly |
| test_file_handling.py | File I/O helpers | Files save/read/delete correctly; size/mime tracking OK |
| test_file_validation.py / test_file_validation_unit.py | Upload validation (size, mime, extension) | Valid files accepted; invalid rejected with proper errors |
| test_job_actions.py | Job lifecycle actions (cancel, restart) | Allowed transitions succeed; forbidden transitions blocked |
| test_job_defaults.py | Default values on new jobs | Defaults set as expected (status, timestamps, flags) |
| test_job_queue_unit.py | Queue behavior in isolation | Enqueue/dequeue/order work; no orphan jobs |
| test_job_routes.py | `/jobs` CRUD/listing/filtering | Create/list/update/delete behave; filters applied correctly |
| test_jobs_route_unit.py | Jobs route helpers | Helper logic returns expected shapes/values |
| test_password_change.py | Password change route specifics | Success on correct old password; proper errors otherwise |
| test_rate_limit.py | Rate limiting middleware | Limits enforced; allowed requests pass |
| test_search.py | `/search` | Queries return expected matches; empty/nonexistent handled |
| test_security_headers.py / test_security.py | Security headers, auth guards | Required headers present; protected routes require auth |
| test_settings.py | `/settings` CRUD | Read/update user settings succeeds; validation enforced |
| test_capabilities.py | Capability reporting + runtime fallback logic | `/system/availability` reports viable options; runtime diarizer/model preference ordering behaves |
| test_startup_checks.py | Startup health checks | Startup passes with valid config; fails cleanly on missing deps |
| test_tag_routes.py | `/tags` CRUD and job tagging | Create/list/delete tags; tag assignments work |
| test_transcript_routes.py | `/transcripts/{job_id}` | Transcript retrieval works; missing transcript handled |
| test_transcription.py / test_transcription_service.py | Transcription service flow | Jobs progress/update correctly; outputs saved |
| test_whisper_service.py | Whisper wrapper behavior | Model invocation mocked; returns expected segments/errors |

## Frontend (Vitest/RTL)
| File | What it tests | Green outcome |
| --- | --- | --- |
| AudioPlayer.test.tsx | Audio controls (play/pause/stop/seek) | Buttons/toggles change state; seeking updates position |
| ConfirmDialog.test.tsx | Confirm/cancel dialog | Buttons invoke correct callbacks |
| Dashboard.test.tsx | Job list/search/filter UI | Jobs render; search/filter narrows results |
| FileDropzone.test.tsx | Upload dropzone validation | Accepts valid files; rejects invalid with messages |
| JobCard.test.tsx | Job card rendering/actions | Status/progress display; action buttons invoke handlers |
| JobDetailModal.test.tsx | Job detail modal UI/actions | Details render; actions fire; close works |
| JobFilters.test.tsx | Filter controls | Changing filters updates query state |
| Login.test.tsx | Login form | Valid creds trigger login; errors shown for invalid |
| Navbar.test.tsx | Nav links/auth state | Shows/hides links based on auth; nav clicks work |
| NewJobModal.test.tsx | New job creation form | Valid submission calls create; validation errors surfaced |
| ProgressBar.test.tsx | Progress display | Renders correct percentages/states |
| ProtectedRoute.test.tsx | Auth gating | Redirects unauthenticated; renders for authed users |
| SearchBar.test.tsx | Search input | Input updates propagate to parent handlers |
| Settings.test.tsx | Settings page | Loads current settings; saves updates; shows errors |
| StatusBadge.test.tsx | Status indicator | Renders correct label/color for statuses |
| TagBadge.test.tsx | Tag chip rendering | Renders label/color; click handler fires |
| TagInput.test.tsx | Tag input interactions | Adds/removes tags; validation messages as needed |
| TagList.test.tsx | Tag listing | Renders tags; selection/removal callbacks fire |
| ToastContext.test.tsx | Toast provider | Enqueue/dequeue toasts works; renders messages |
| TranscriptView.test.tsx | Transcript display/download view | Renders transcript; download/view actions work |
| usePolling.test.tsx | Polling hook | Polls on interval; stops/cleans up correctly |
| Services/jobs.test.ts | jobs API client | CRUD calls hit correct endpoints; errors handled |
| Services/settings.test.ts | settings API client | Reads/updates settings via API; error handling |
| Services/tags.test.ts | tags API client | CRUD/tag assignment calls correct endpoints |
| Services/transcripts.test.ts | transcripts API client | Fetch/export calls correct endpoints; errors handled |

## Frontend E2E (Playwright)
| File | What it tests | Green outcome |
| --- | --- | --- |
| login.spec.ts | Login/logout flow | Valid creds log in; protected pages accessible; logout returns to login |
| new-job.spec.ts | New job creation | Modal opens, file uploads, job appears in list |
| jobDetail.spec.ts | Job detail modal | Modal opens; metadata/actions visible; close works |
| flow-create-complete-export-delete.spec.ts | Full job lifecycle | Create job, observe status progression, export transcript, delete job |
| transcription.spec.ts | Transcription workflow | Queue/process/complete path with simulated transcription succeeds |
| search.spec.ts | Search/filtering | Searches narrow results; filters apply |
| tagManagement.spec.ts | Tag inventory/add/filter/remove (prod-parity) | Tags visible in settings; add tag from job detail; filter jobs by tag; remove tag updates UI |
| settings.spec.ts | Settings page (e2e) | Loads current settings; saves updates; toggles persist |
| accessibility.spec.ts | Axe accessibility scan | No critical axe violations on key pages |
| perf-smoke.spec.ts | Lightweight performance smoke | Page loads within expected thresholds |

## Smoke (scripts/smoke_test.py)
| What it tests | Green outcome |
| --- | --- |
| `/health` + login with seed admin | HTTP 200 on health; login succeeds (or clear hint to reset password) |

### How to use
- Run `.cscripts\run-tests.ps1` for the full battery; each suite must report PASS.
- For manual runs, mark green when all assertions in the file pass (test runner exit code 0) and the described behavior is observed. Suites that fail any file are non-green.***
