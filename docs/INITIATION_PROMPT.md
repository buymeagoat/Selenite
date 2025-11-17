# Selenite Build Initiation Prompt

## Purpose
Use this prompt when opening the Selenite workspace in VS Code to provide GitHub Copilot with complete context for continuing development.

---

## Copy This Prompt

```
I'm working on Selenite, a personal audio/video transcription application. This is a ground-up rebuild focused on simplicity and elegance.

PROJECT CONTEXT:
- Single-user desktop application for transcribing audio/video files
- Backend: FastAPI (Python 3.11+) with SQLAlchemy + SQLite
- Frontend: React 18 + Vite with Tailwind CSS
- Transcription: OpenAI Whisper (local models in /models directory)
- UI Theme: Pine forest color palette (deep greens, sage, earth tones)

DEVELOPMENT APPROACH:
- Iterative test-driven development (20 build increments)
- Write tests FIRST, then implement to pass tests
- Quality gates: tests pass, code formatted, manually verified, documented
- Atomic commits: One feature per commit with format "[Component] Description"
- Coverage requirements: Backend >80%, Frontend >70%

KEY DOCUMENTS:
- DEVELOPMENT_PLAN.md: Complete blueprint with 20 build increments
- docs/API_CONTRACTS.md: All 30+ API endpoints fully specified
- docs/COMPONENT_SPECS.md: All 24 React components with props/states
- docs/PRE_BUILD_VERIFICATION.md: Senior developer approval and assessment
- docs/QUICK_REFERENCE.md: Commands, troubleshooting, progress tracking

CURRENT STATUS:
- Currently on: Build Increment 11 (Dashboard Layout & Job Cards)
- Last completed: Build Increment 10 - Frontend Foundation
  - Initialized Vite + React 18 + TypeScript
  - Configured Tailwind CSS with pine forest theme
  - Implemented AuthContext and ProtectedRoute
  - Created Login page with routing
  - Built Navbar component with user dropdown
  - Added 3 test suites (Login, ProtectedRoute, Navbar)
  - Installed dependencies: react-router-dom, axios, vitest, testing-library
  - Frontend foundation complete, ready for API integration
- Next task: Build Dashboard with JobCard components and status indicators
- Files being worked on: Ready to begin Increment 11

QUALITY GATE CHECKLIST:
Before committing any increment, verify:
- [ ] All tests pass (pytest -v or npm test)
- [ ] Code formatted (black/ruff for backend, eslint for frontend)
- [ ] Manual smoke test completed successfully
- [ ] Documentation updated (inline comments, README if needed)
- [ ] No console errors or warnings
- [ ] Commit message follows format: [Component] Description

IMMEDIATE REQUEST:
[State what you need help with - implementing a specific increment, debugging a test, refactoring code, etc.]

Please help me with the current task, following the test-driven approach and quality standards defined in the project documents.
```

---

## How to Use This Prompt

### When Starting a New Session

1. **Open Selenite workspace** in VS Code
2. **Review progress**: Check which increment you're on
3. **Update status section**: Fill in current status, last completed, next task
4. **Copy and paste** the entire prompt into GitHub Copilot chat
5. **State your immediate request**: What you need help with right now

### Example Usage - Starting Fresh

```
I'm working on Selenite, a personal audio/video transcription application...

CURRENT STATUS:
- Currently on: Build Increment 1 (Project Scaffolding)
- Last completed: Pre-build documentation
- Next task: Initialize backend project structure and create database models
- Files being worked on: None yet - starting fresh

IMMEDIATE REQUEST:
Let's begin Build Increment 1. Please help me:
1. Create the backend directory structure
2. Initialize pyproject.toml with dependencies
3. Create SQLAlchemy models (User, Job, Tag, Transcript)
4. Set up Alembic for migrations
5. Write initial database tests

Follow the test-driven approach: write tests first, then implement.
```

### Example Usage - Continuing Work

```
I'm working on Selenite, a personal audio/video transcription application...

CURRENT STATUS:
- Currently on: Build Increment 5 (Real Transcription Engine)
- Last completed: Increment 4 - Job listing and retrieval endpoints
- Next task: Implement Whisper transcription service with job queue
- Files being worked on: 
  - backend/app/services/transcription.py
  - backend/app/services/job_queue.py
  - backend/tests/test_transcription.py

IMMEDIATE REQUEST:
I'm implementing the transcription service. I have the basic Whisper integration working, but I need help with:
1. Implementing the job queue with 3-worker concurrency limit
2. Adding progress tracking that updates the database
3. Writing tests for concurrent job processing

The test test_concurrent_job_limit is currently failing. Can you help me debug it?
```

### Example Usage - Debugging

```
I'm working on Selenite, a personal audio/video transcription application...

CURRENT STATUS:
- Currently on: Build Increment 11 (Dashboard Layout & Job Cards)
- Last completed: Increment 10 - Frontend foundation with auth
- Next task: Build JobCard component with all states
- Files being worked on: 
  - frontend/src/components/jobs/JobCard.jsx
  - frontend/src/components/jobs/StatusBadge.jsx
  - frontend/tests/JobCard.test.jsx

IMMEDIATE REQUEST:
The JobCard component is rendering, but the hover state isn't working correctly on mobile. According to COMPONENT_SPECS.md, quick action buttons should always be visible on mobile but only show on hover for desktop. Can you help me fix the responsive behavior?
```

---

## Tips for Effective Use

### 1. Always Include Current Status
Update the status section so Copilot knows exactly where you are in the build process.

### 2. Reference the Specs
Mention which document has the relevant specification:
- "According to API_CONTRACTS.md, the POST /jobs endpoint should..."
- "Per COMPONENT_SPECS.md, the JobCard component needs..."
- "DEVELOPMENT_PLAN.md says Increment 5 should include..."

### 3. Be Specific About Tests
If working on tests:
- "I need to write tests for the auth service before implementing it"
- "The test test_login_success is failing with this error..."
- "Help me write a test that verifies job queue concurrency"

### 4. Request Quality Checks
Before committing:
- "I've implemented Increment 7. Can you review against the quality gates?"
- "Run through the commit checklist with me"
- "Verify this implementation matches the API contract specification"

### 5. Ask for Next Steps
When completing an increment:
- "Increment 5 is complete and committed. What's next for Increment 6?"
- "I've passed all quality gates. Walk me through the commit process"
- "All tests passing. What should I verify manually before committing?"

---

## Progress Tracking

Keep track of completed increments here:

### Backend Increments
- [x] Increment 1: Project Scaffolding & Database
- [x] Increment 2: Authentication System
- [x] Increment 3: Job Creation Without Transcription
- [x] Increment 4: Job Listing & Retrieval
- [x] Increment 5: Real Transcription Engine (Simulated)
- [x] Increment 6: Export Formats
- [x] Increment 7: Tag System
- [x] Increment 8: Search Functionality
- [x] Increment 9: Settings & System Control ✨ BACKEND COMPLETE!

### Frontend Increments
- [x] Increment 10: Frontend Foundation
- [ ] Increment 11: Dashboard Layout & Job Cards
- [ ] Increment 12: New Job Modal
- [ ] Increment 13: Job Detail Modal
- [ ] Increment 14: Search & Filters
- [ ] Increment 15: Tag Management UI
- [ ] Increment 16: Settings Page
- [ ] Increment 17: Real-time Progress Updates
- [ ] Increment 18: Polish & Responsive Design

### Testing & Deployment
- [ ] Increment 19: End-to-End Testing
- [ ] Increment 20: Production Readiness

---

## Common Issues & Solutions

### "I forgot what I was working on"
1. Check git log: `git log --oneline -10`
2. Check last commit message for clues
3. Look at uncommitted changes: `git status`
4. Review QUICK_REFERENCE.md progress checklist

### "Tests are failing and I don't know why"
1. Paste the test output into the prompt
2. Ask: "This test is failing. What's wrong based on the test output and the specification in [DOCUMENT]?"
3. Reference the relevant spec document

### "I'm not sure if this is correct"
1. Ask: "Does this implementation match the specification in API_CONTRACTS.md for POST /jobs?"
2. Request: "Review this code against the quality gates before I commit"
3. Verify: "Run through the commit checklist with me"

### "I want to refactor something"
1. Ensure tests pass first
2. Ask: "I want to refactor [COMPONENT]. The tests currently pass. How can I refactor while keeping tests green?"
3. Make changes incrementally, running tests after each change

---

## Remember

- **Test First**: Always write tests before implementation
- **Small Steps**: Complete one increment at a time
- **Quality Gates**: Don't skip them - they ensure stability
- **Atomic Commits**: One complete feature per commit
- **Documentation**: Keep specs and README up to date

---

**Use this prompt at the start of every Copilot session to ensure consistent, high-quality development with full context.**
