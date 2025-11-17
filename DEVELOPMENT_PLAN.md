# Selenite Development Plan

## Project Overview

**Selenite** is a clean, focused audio/video transcription application designed for single-user personal use. It provides an elegant, responsive web interface for uploading media files, transcribing them using local Whisper models, and managing a searchable history of all transcription jobs.

### Core Philosophy
- **Simplicity First**: Strip away complexity; focus on core transcription workflow
- **Beautiful UX**: Pine forest color theme, responsive design (desktop/tablet/mobile)
- **Local Processing**: All transcription happens locally using Whisper models
- **Complete History**: Database-backed job tracking with full metadata and searchability

---

## Requirements Summary

### Primary Functions
1. **Upload**: Accept audio/video files via file selection or drag-and-drop
2. **Transcribe**: Process using local Whisper models with configurable options
3. **Organize**: Tag-based organization system with search and filtering
4. **Export**: Download transcripts in multiple formats (.txt, .md, .srt, .vtt, .json, .docx)
5. **History**: View all jobs (active, completed, failed) with full details and actions

### User Experience Requirements

#### Authentication
- Single user account: `admin` with changeable password
- Simple login screen to protect personal data

#### Home Screen (Main Dashboard)
- **Primary View**: List of all jobs (historic/active/queued)
- **Status Indicators**: Visual badges for job state (queued, processing, complete, failed)
- **Filters**: 
  - Status: All / In Progress / Complete / Failed
  - Date: Today / This Week / This Month / Custom Range / All Time
  - Tags: Filter by assigned tags
- **Search**: Full-text search across filenames, dates, and transcript content
- **Actions**: 
  - "New Transcription" button (opens modal)
  - Quick actions on each job card

#### Job Card Display
Each job shows:
- Filename
- Upload date/time
- Duration (for completed jobs)
- Status with progress bar (if processing)
- Number of speakers detected
- Assigned tags
- Quick action buttons (Play, Download, View Transcript, etc.)

#### New Transcription Flow
1. Click "+ New Transcription" button
2. Modal opens with:
   - File upload area (drag-and-drop or click to browse)
   - Model selection dropdown (tiny, base, small, medium, large)
   - Language: Auto-detect (default)
   - Options: ☑ Speaker detection, ☑ Timestamps
   - Cancel / Start Transcription buttons

#### Job Detail Modal
When clicking on a completed job, modal shows:
- Full job metadata (filename, duration, date, model used, etc.)
- Assigned tags (editable)
- Action buttons:
  - ▶️ Play Media (audio player in modal)
  - 📄 View Transcript (opens in new window/tab)
  - 📥 Download Audio/Video
  - 📥 Download Transcript (format selector: .txt, .md, .srt, .vtt, .json, .docx)
  - 🔄 Re-run Transcription (new job from same source file)
  - 🏷️ Edit Tags
  - 🗑️ Delete Job

#### Processing Display
Active jobs show:
- Progress bar (0-100%)
- Current stage: "Uploading" → "Loading Model" → "Transcribing" → "Finalizing"
- Time estimate: "~3 minutes remaining"
- Cancel button

#### Settings Page
Accessible from sidebar/nav:
- Change Password
- Default Transcription Options (model, language, speaker detection, timestamps)
- Maximum Concurrent Jobs (default: 3)
- Storage Location Display (read-only info)
- Server Controls:
  - Restart Server button
  - Shutdown Server button

### Technical Requirements

#### Processing Constraints
- **CPU Only**: No GPU acceleration assumed (for now)
- **Background Processing**: Jobs run in background; user can browse/upload while processing
- **Concurrency**: Maximum 3 jobs processing simultaneously
- **Queue Management**: Additional uploads enter queue; user can cancel/reorder
- **No File Size Limit**: Should handle any duration (short voice memos to multi-hour lectures)

#### Transcription Options
- **Model Selection**: Access existing models in `/models` directory (tiny, base, small, medium, large)
- **Language**: Auto-detect by default
- **Speaker Detection**: Enable/disable diarization (identify different speakers)
- **Timestamps**: Include word-level or segment-level timestamps in output

#### Export Formats
Must support:
- Plain text (.txt)
- Markdown (.md)
- SRT subtitles (.srt)
- WebVTT (.vtt)
- JSON (structured data with timestamps)
- Word document (.docx)

#### Organization System
- **Tags Only**: No folder hierarchy (simpler)
- **Multi-tagging**: Each job can have multiple tags
- **Tag Creation**: Create tags on-the-fly when assigning
- **Tag Management**: View all tags, rename, delete (with reassignment prompt)
- **Search Integration**: Search by tags, filter by tags

#### Mobile Support
- Responsive design adapts to screen size
- On mobile: File picker should allow selecting from Files app or Voice Memos (iOS)
- Touch-optimized controls (larger tap targets, swipe gestures)

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite (simple, file-based) with SQLAlchemy ORM
- **Transcription**: OpenAI Whisper (local models)
- **Job Queue**: Python asyncio with concurrent.futures for background processing
- **Authentication**: JWT tokens with secure password hashing (passlib + bcrypt)

### Frontend
- **Framework**: React 18+ with Vite
- **UI Library**: Tailwind CSS for styling
- **Icons**: Lucide React or similar
- **State Management**: React Context API or Zustand (lightweight)
- **HTTP Client**: Axios or native fetch
- **Routing**: React Router v6

### Color Scheme: Pine Forest
- **Primary Dark**: Deep forest green (#1B4332, #2D6A4F)
- **Secondary**: Moss green (#40916C, #52B788)
- **Accent**: Sage/mint (#74C69D, #95D5B2)
- **Neutral Dark**: Charcoal (#2B2D42, #3D405B)
- **Neutral Light**: Warm gray/beige (#E8E9E3, #F5F3ED)
- **Background**: Off-white with slight green tint (#F8F9F5)
- **Text**: Deep brown-black (#1C1D1F)
- **Error/Warning**: Muted terracotta (#D4A574)
- **Success**: Bright sage (#6FCF97)

---

## Database Schema

### Tables

#### users
```sql
id              INTEGER PRIMARY KEY
username        TEXT UNIQUE NOT NULL
email           TEXT UNIQUE
hashed_password TEXT NOT NULL
created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
```

#### jobs
```sql
id                  TEXT PRIMARY KEY (UUID)
user_id             INTEGER NOT NULL REFERENCES users(id)
original_filename   TEXT NOT NULL
saved_filename      TEXT NOT NULL (unique storage name)
file_path           TEXT NOT NULL (full path to media file)
file_size           INTEGER (bytes)
mime_type           TEXT
duration            REAL (seconds, null until processing completes)
status              TEXT NOT NULL (queued, processing, completed, failed)
progress_percent    INTEGER DEFAULT 0
progress_stage      TEXT (uploading, loading_model, transcribing, finalizing)
estimated_time_left INTEGER (seconds, null if unknown)
model_used          TEXT (tiny, base, small, medium, large)
language_detected   TEXT
speaker_count       INTEGER
has_timestamps      BOOLEAN DEFAULT TRUE
has_speaker_labels  BOOLEAN DEFAULT TRUE
transcript_path     TEXT (path to primary transcript file)
error_message       TEXT (if status=failed)
created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
started_at          DATETIME
completed_at        DATETIME
```

#### tags
```sql
id          INTEGER PRIMARY KEY
name        TEXT UNIQUE NOT NULL
color       TEXT (hex color for UI)
created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
```

#### job_tags (junction table)
```sql
job_id  TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE
tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE
PRIMARY KEY (job_id, tag_id)
```

#### transcripts
```sql
id              INTEGER PRIMARY KEY
job_id          TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE
format          TEXT NOT NULL (txt, md, srt, vtt, json, docx)
file_path       TEXT NOT NULL
file_size       INTEGER
generated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
```

#### settings
```sql
key     TEXT PRIMARY KEY
value   TEXT NOT NULL
```

---

## API Endpoints

### Authentication
- `POST /auth/login` - Login with username/password, returns JWT token
- `POST /auth/logout` - Invalidate token
- `POST /auth/change-password` - Change password for current user
- `GET /auth/me` - Get current user info

### Jobs
- `GET /jobs` - List all jobs with filters/search
  - Query params: status, date_range, tags, search, limit, offset
- `GET /jobs/{job_id}` - Get job details with full metadata
- `POST /jobs` - Create new transcription job (upload file + options)
- `POST /jobs/{job_id}/cancel` - Cancel a queued or processing job
- `POST /jobs/{job_id}/restart` - Re-run transcription on existing file
- `DELETE /jobs/{job_id}` - Delete job and all associated files
- `GET /jobs/{job_id}/status` - Get current status and progress (for polling)

### Media & Transcripts
- `GET /media/{job_id}` - Stream/download original audio/video file
- `GET /transcripts/{job_id}` - Get primary transcript (text)
- `GET /transcripts/{job_id}/export` - Download transcript in specific format
  - Query params: format (txt, md, srt, vtt, json, docx)

### Tags
- `GET /tags` - List all tags
- `POST /tags` - Create new tag
- `PUT /tags/{tag_id}` - Update tag (rename, change color)
- `DELETE /tags/{tag_id}` - Delete tag
- `POST /jobs/{job_id}/tags` - Assign tags to job
- `DELETE /jobs/{job_id}/tags/{tag_id}` - Remove tag from job

### Search
- `GET /search` - Full-text search across jobs
  - Query params: q (query string), filters (status, tags, date_range)

### Settings
- `GET /settings` - Get all user settings
- `PUT /settings` - Update settings (default options, concurrent jobs, etc.)

### System
- `GET /health` - Health check
- `GET /models` - List available Whisper models
- `POST /system/restart` - Restart server (requires confirmation)
- `POST /system/shutdown` - Shutdown server (requires confirmation)

---

## File Structure

```
Selenite/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app initialization
│   │   ├── config.py               # Configuration management
│   │   ├── database.py             # Database setup and session management
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py             # User SQLAlchemy model
│   │   │   ├── job.py              # Job SQLAlchemy model
│   │   │   ├── tag.py              # Tag SQLAlchemy model
│   │   │   └── transcript.py       # Transcript SQLAlchemy model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py             # Pydantic schemas for users
│   │   │   ├── job.py              # Pydantic schemas for jobs
│   │   │   ├── tag.py              # Pydantic schemas for tags
│   │   │   └── auth.py             # Auth request/response schemas
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Authentication endpoints
│   │   │   ├── jobs.py             # Job management endpoints
│   │   │   ├── tags.py             # Tag management endpoints
│   │   │   ├── media.py            # Media streaming endpoints
│   │   │   ├── transcripts.py      # Transcript download endpoints
│   │   │   ├── search.py           # Search endpoints
│   │   │   └── system.py           # System control endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Authentication logic
│   │   │   ├── transcription.py    # Whisper transcription service
│   │   │   ├── job_queue.py        # Job queue management
│   │   │   ├── export.py           # Export format generators
│   │   │   └── search.py           # Search implementation
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── security.py         # Password hashing, JWT tokens
│   │   │   ├── file_handling.py    # File upload/storage utilities
│   │   │   └── progress.py         # Progress tracking utilities
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── cors.py             # CORS configuration
│   │       └── error_handler.py    # Global error handling
│   ├── alembic/
│   │   ├── versions/               # Database migrations
│   │   └── env.py
│   ├── storage/
│   │   ├── media/                  # Uploaded audio/video files
│   │   ├── transcripts/            # Generated transcript files
│   │   └── models/                 # Whisper model files (symlink to existing)
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_jobs.py
│   │   ├── test_transcription.py
│   │   └── test_export.py
│   ├── alembic.ini
│   ├── pyproject.toml              # Python dependencies
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── public/
│   │   └── favicon.ico
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── MobileNav.jsx
│   │   │   ├── modals/
│   │   │   │   ├── NewJobModal.jsx
│   │   │   │   ├── JobDetailModal.jsx
│   │   │   │   └── ConfirmDialog.jsx
│   │   │   ├── jobs/
│   │   │   │   ├── JobCard.jsx
│   │   │   │   ├── JobList.jsx
│   │   │   │   ├── JobFilters.jsx
│   │   │   │   ├── ProgressBar.jsx
│   │   │   │   └── StatusBadge.jsx
│   │   │   ├── upload/
│   │   │   │   ├── FileDropzone.jsx
│   │   │   │   └── UploadOptions.jsx
│   │   │   ├── tags/
│   │   │   │   ├── TagInput.jsx
│   │   │   │   ├── TagList.jsx
│   │   │   │   └── TagBadge.jsx
│   │   │   └── common/
│   │   │       ├── Button.jsx
│   │   │       ├── Input.jsx
│   │   │       ├── SearchBar.jsx
│   │   │       └── AudioPlayer.jsx
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Settings.jsx
│   │   │   └── TranscriptView.jsx
│   │   ├── context/
│   │   │   ├── AuthContext.jsx
│   │   │   └── JobContext.jsx
│   │   ├── services/
│   │   │   ├── api.js              # Axios instance with interceptors
│   │   │   ├── auth.js             # Auth API calls
│   │   │   ├── jobs.js             # Job API calls
│   │   │   └── tags.js             # Tag API calls
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   ├── useJobs.js
│   │   │   └── usePolling.js       # For job status updates
│   │   ├── utils/
│   │   │   ├── formatters.js       # Date, duration formatting
│   │   │   └── constants.js        # App constants
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css               # Tailwind imports + custom styles
│   ├── .env.example
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── README.md
│
├── models/                         # Symlink or copy from whisper-transcriber
│   ├── base.pt
│   ├── small.pt
│   ├── medium.pt
│   └── large-v3.pt
│
├── .gitignore
├── README.md
├── DEVELOPMENT_PLAN.md             # This file
└── docker-compose.yml              # Optional: for containerized deployment
```

---

## Implementation Phases

### Phase 1: Backend Core (Week 1)
**Goal**: Functional backend with database, auth, and basic job management

Tasks:
1. Set up project structure and dependencies
2. Configure FastAPI app with CORS middleware
3. Implement SQLAlchemy models (User, Job, Tag, Transcript)
4. Create Alembic migrations for initial schema
5. Implement authentication system:
   - Password hashing and verification
   - JWT token generation and validation
   - Auth middleware for protected routes
6. Build basic CRUD endpoints for jobs (without transcription)
7. Implement file upload handling and storage
8. Set up basic error handling and logging

**Deliverable**: Backend that can handle user login and job creation (without actual transcription)

### Phase 2: Transcription Engine (Week 1-2)
**Goal**: Working transcription pipeline with progress tracking

Tasks:
1. Implement transcription service using OpenAI Whisper
2. Set up job queue system with concurrency control (max 3 simultaneous)
3. Build progress tracking mechanism:
   - Stage updates (loading model, transcribing, finalizing)
   - Percentage completion
   - Time estimation
4. Implement job status polling endpoint
5. Add cancellation support
6. Handle errors and failed jobs gracefully
7. Test with various audio/video formats and durations

**Deliverable**: Backend that can queue, process, and track transcription jobs

### Phase 3: Export & Search (Week 2)
**Goal**: Multiple export formats and full-text search

Tasks:
1. Implement transcript export service:
   - Plain text (.txt)
   - Markdown (.md)
   - SRT subtitles (.srt)
   - WebVTT (.vtt)
   - JSON (structured with timestamps)
   - Word document (.docx)
2. Build search functionality:
   - Full-text search across filenames
   - Search transcript content
   - Filter by status, date range, tags
3. Add media streaming endpoint for audio/video playback
4. Implement tag management (CRUD)
5. Add job-tag association endpoints

**Deliverable**: Complete backend API with all features

### Phase 4: Frontend Foundation (Week 2-3)
**Goal**: Responsive UI shell with routing and authentication

Tasks:
1. Set up React + Vite project with Tailwind CSS
2. Configure routing (React Router)
3. Implement pine forest color theme
4. Build authentication flow:
   - Login page
   - Auth context with token management
   - Protected route wrapper
5. Create layout components:
   - Navbar/Sidebar (desktop)
   - Mobile navigation
6. Build reusable components:
   - Buttons, inputs, modals
   - Status badges
   - Progress bars
7. Implement responsive design (mobile/tablet/desktop)

**Deliverable**: Functional UI shell with login and navigation

### Phase 5: Job Management UI (Week 3)
**Goal**: Complete job viewing, filtering, and action capabilities

Tasks:
1. Build Dashboard page:
   - Job list with cards
   - Filters (status, date, tags)
   - Search bar with real-time search
2. Implement New Job modal:
   - File dropzone (drag-and-drop + click to browse)
   - Model selection dropdown
   - Options checkboxes (speaker detection, timestamps)
3. Build Job Detail modal:
   - Full metadata display
   - Action buttons (play, download, view, delete)
   - Tag assignment UI
   - Audio player component
4. Implement real-time progress updates:
   - Polling mechanism for active jobs
   - Progress bar and stage display
   - Time estimate
5. Add job actions:
   - Cancel processing job
   - Restart completed job
   - Delete job with confirmation

**Deliverable**: Fully functional job management interface

### Phase 6: Tags & Search UI (Week 3-4)
**Goal**: Tag management and advanced search

Tasks:
1. Build tag input component with autocomplete
2. Implement tag creation UI
3. Add tag filtering to job list
4. Build tag management section in settings
5. Implement search results view
6. Add search highlighting in transcript preview

**Deliverable**: Complete organization and search capabilities

### Phase 7: Settings & Polish (Week 4)
**Goal**: Settings page and final UX improvements

Tasks:
1. Build Settings page:
   - Change password form
   - Default transcription options
   - Concurrent jobs slider
   - Server control buttons (restart/shutdown)
2. Add loading states and animations
3. Implement error notifications (toast/snackbar)
4. Add empty states for job list
5. Polish responsive design for mobile
6. Add keyboard shortcuts (optional)
7. Performance optimization:
   - Lazy loading for job list
   - Image/media optimization
   - Code splitting

**Deliverable**: Production-ready application

### Phase 8: Testing & Deployment (Week 4)
**Goal**: Tested, documented, and deployable application

Tasks:
1. Write backend tests (pytest)
2. Write frontend tests (Vitest/React Testing Library)
3. End-to-end testing (Playwright or Cypress)
4. Create deployment documentation
5. Set up Docker configuration (optional)
6. Write user documentation
7. Performance testing with various file sizes
8. Security audit (auth, file upload validation, etc.)

**Deliverable**: Fully tested and deployable application

---

## Configuration

### Environment Variables

#### Backend (.env)
```bash
# Database
DATABASE_URL=sqlite:///./selenite.db

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# Storage
MEDIA_STORAGE_PATH=./storage/media
TRANSCRIPT_STORAGE_PATH=./storage/transcripts
MODEL_STORAGE_PATH=./storage/models

# Transcription
MAX_CONCURRENT_JOBS=3
DEFAULT_WHISPER_MODEL=medium
DEFAULT_LANGUAGE=auto

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

#### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Selenite
```

---

## Key Dependencies

### Backend (pyproject.toml)
```toml
[project]
name = "selenite"
version = "0.1.0"
description = "Personal audio/video transcription application"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "openai-whisper>=20231117",
    "torch>=2.1.0",
    "python-docx>=1.1.0",
    "aiofiles>=23.2.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
    "black>=23.10.0",
    "ruff>=0.1.0",
]
```

### Frontend (package.json)
```json
{
  "name": "selenite-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "lucide-react": "^0.294.0",
    "react-dropzone": "^14.2.3"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.3.5",
    "postcss": "^8.4.32",
    "autoprefixer": "^10.4.16"
  }
}
```

---

## Development Workflow

### Initial Setup
1. Clone repository
2. Set up backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -e ".[dev]"
   cp .env.example .env
   # Edit .env with your configuration
   alembic upgrade head  # Create database tables
   python -m app.main    # Run backend server
   ```
3. Set up frontend:
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   npm run dev  # Run development server
   ```

### Daily Development
1. Start backend: `cd backend && python -m app.main`
2. Start frontend: `cd frontend && npm run dev`
3. Access app at `http://localhost:5173`
4. Backend API at `http://localhost:8000`
5. API docs at `http://localhost:8000/docs`

### Testing
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Database Migrations
```bash
cd backend
# Create new migration after model changes
alembic revision --autogenerate -m "description of changes"
# Apply migrations
alembic upgrade head
```

---

## Design System

### Typography
- **Headings**: Inter or system font stack
- **Body**: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI"
- **Monospace**: For file names, technical data

### Spacing Scale
- xs: 0.25rem (4px)
- sm: 0.5rem (8px)
- md: 1rem (16px)
- lg: 1.5rem (24px)
- xl: 2rem (32px)
- 2xl: 3rem (48px)

### Component Patterns

#### Buttons
- **Primary**: Forest green background, white text
- **Secondary**: Outlined, forest green border
- **Danger**: Terracotta background for destructive actions
- **Ghost**: No background, hover shows light tint

#### Cards
- White/off-white background
- Subtle shadow
- Rounded corners (8px)
- Hover state: slight elevation increase

#### Modals
- Centered overlay
- Semi-transparent dark backdrop
- White card with rounded corners
- Close button (X) in top-right
- Focus trap for accessibility

#### Progress Bars
- Track: Light sage background
- Fill: Forest green
- Animated shimmer for active state
- Show percentage text

#### Status Badges
- **Queued**: Light gray
- **Processing**: Animated blue/sage
- **Complete**: Success green
- **Failed**: Muted red/terracotta
- Pill-shaped with icon

---

## Security Considerations

1. **Authentication**
   - Secure password hashing with bcrypt
   - JWT tokens with expiration
   - HttpOnly cookies (optional for token storage)
   - CSRF protection if using cookies

2. **File Upload**
   - Validate file types (audio/video only)
   - Sanitize filenames
   - Limit file size (configurable, e.g., 2GB max)
   - Store files outside web root

3. **API Security**
   - Rate limiting on login endpoint
   - CORS properly configured
   - Input validation on all endpoints
   - SQL injection prevention (SQLAlchemy ORM)

4. **System Access**
   - Require password confirmation for server restart/shutdown
   - Log all system control actions
   - Restrict file system access to storage directories only

---

## Performance Optimization

1. **Backend**
   - Use connection pooling for database
   - Implement pagination for job list
   - Stream large files instead of loading into memory
   - Cache frequently accessed data (tags, settings)
   - Index database columns used in searches

2. **Frontend**
   - Lazy load job cards (virtual scrolling for long lists)
   - Debounce search input
   - Cache job status responses briefly
   - Use React.memo for expensive components
   - Code split by route

3. **Transcription**
   - Load Whisper model once, reuse for multiple jobs
   - Process jobs in background thread pool
   - Provide estimated time based on file size and model
   - Clean up completed job files based on retention policy

---

## Future Enhancements (Post-MVP)

These features are explicitly NOT in the initial build but can be added later:

1. **Advanced Speaker Diarization**
   - Integrate pyannote.audio for better speaker detection
   - Speaker naming/labeling

2. **Transcript Editing**
   - In-browser transcript editor with versioning
   - Track changes and maintain edit history

3. **Audio Sync Playback**
   - Highlight transcript segments as audio plays
   - Click transcript to jump to that point in audio

4. **Collaboration** (if multi-user ever needed)
   - Share jobs with other users
   - Comments on transcripts

5. **Cloud Backup**
   - Optional cloud storage integration
   - Automatic backup scheduling

6. **GPU Acceleration**
   - Detect and use GPU if available
   - Significantly faster transcription

7. **API for External Access**
   - REST API for programmatic access
   - Webhook notifications

8. **Advanced Analytics**
   - Transcription statistics dashboard
   - Word frequency analysis
   - Sentiment analysis

---

## Troubleshooting Guide

### Common Issues

**Issue**: Transcription fails with "Out of memory"
- **Solution**: Use a smaller model (tiny or base) or process shorter files

**Issue**: Speaker detection not working
- **Solution**: This requires additional setup with pyannote; initially, it will be a placeholder

**Issue**: Frontend can't connect to backend
- **Solution**: Check CORS settings in backend .env, ensure backend is running

**Issue**: Jobs stuck in "processing"
- **Solution**: Check backend logs, may need to restart worker queue

**Issue**: Can't upload large files
- **Solution**: Increase file size limit in FastAPI config and nginx/reverse proxy if deployed

---

## Success Metrics

### MVP Success Criteria
- [ ] User can log in with admin account
- [ ] User can upload audio/video file via drag-and-drop or file picker
- [ ] File is queued and processed with visible progress
- [ ] Completed transcription is viewable and downloadable
- [ ] User can tag jobs and filter by tags
- [ ] Search finds jobs by filename or transcript content
- [ ] User can play audio/video from job detail modal
- [ ] User can export transcript in all 6 formats
- [ ] UI is responsive on mobile, tablet, and desktop
- [ ] Settings allow changing password and defaults
- [ ] Maximum 3 concurrent jobs enforced

### Performance Targets
- File upload: < 2 seconds for 100MB file
- Job queuing: < 500ms response time
- Transcription: 1x real-time (10-min audio → ~10-min transcription time with medium model)
- Job list loading: < 1 second for 100 jobs
- Search results: < 2 seconds for 1000 jobs

---

---

## BUILD PROCESS & METHODOLOGY

### Build Philosophy: Iterative Test-Driven Development

Every component follows this cycle:
1. **Design**: Define interface contracts (API schemas, component props)
2. **Test First**: Write tests that define expected behavior
3. **Implement**: Build the minimum code to pass tests
4. **Document**: Add inline documentation and README updates
5. **Verify**: Run tests, manual verification, commit
6. **Integrate**: Test with dependent components

### Commit Strategy

**Atomic Commits**: Each commit represents ONE fully functional, tested feature
- Commit message format: `[Component] Brief description`
- Examples:
  - `[Backend/Auth] Implement JWT token generation and validation with tests`
  - `[Frontend/Login] Add login form with validation and error handling`
  - `[Database] Create initial schema migration for users and jobs tables`

**Branch Strategy**: 
- `main` - Production-ready code only
- `develop` - Integration branch for completed features
- `feature/[name]` - Individual feature development

**Commit Checklist** (must pass before committing):
- [ ] All tests pass (backend: pytest, frontend: npm test)
- [ ] Code follows style guide (backend: black + ruff, frontend: eslint)
- [ ] Documentation updated (inline comments, README if needed)
- [ ] Manual smoke test completed
- [ ] No console errors or warnings
- [ ] Dependencies documented if added

---

## PRE-BUILD ARTIFACTS

### 1. API Contract Specification

Before writing any backend code, define complete API contracts:

#### Example: Job Creation Endpoint
```yaml
POST /jobs
Description: Create new transcription job with file upload
Authentication: Required (JWT Bearer token)

Request:
  Content-Type: multipart/form-data
  Fields:
    - file: File (required) - Audio/video file
    - model: string (optional, default: "medium") - Whisper model to use
    - language: string (optional, default: "auto") - Language code or auto-detect
    - enable_timestamps: boolean (optional, default: true)
    - enable_speaker_detection: boolean (optional, default: true)

Response 201 Created:
  {
    "job_id": "uuid-string",
    "status": "queued",
    "original_filename": "string",
    "created_at": "ISO-8601 datetime"
  }

Response 400 Bad Request:
  {
    "detail": "Invalid file format. Supported: mp3, wav, mp4, etc."
  }

Response 401 Unauthorized:
  {
    "detail": "Invalid or expired token"
  }

Response 413 Payload Too Large:
  {
    "detail": "File size exceeds maximum allowed (2GB)"
  }
```

**Action**: Create `API_CONTRACTS.md` with ALL endpoints before implementation

### 2. Component Interface Specifications

Define React component props and behavior before building:

#### Example: JobCard Component
```javascript
/**
 * JobCard - Display summary of a single transcription job
 * 
 * @component
 * @example
 * <JobCard 
 *   job={{
 *     id: "uuid",
 *     filename: "interview.mp3",
 *     status: "completed",
 *     created_at: "2025-11-15T10:30:00Z",
 *     duration: 1834,
 *     tags: [{id: 1, name: "interviews", color: "#2D6A4F"}]
 *   }}
 *   onPlay={(jobId) => console.log("Play", jobId)}
 *   onDownload={(jobId) => console.log("Download", jobId)}
 *   onView={(jobId) => console.log("View", jobId)}
 *   onDelete={(jobId) => console.log("Delete", jobId)}
 * />
 */

// Props Interface
interface JobCardProps {
  job: {
    id: string;
    original_filename: string;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    created_at: string;
    duration?: number;  // seconds, only for completed jobs
    progress_percent?: number;  // 0-100, for processing jobs
    progress_stage?: string;  // "loading_model", "transcribing", etc.
    estimated_time_left?: number;  // seconds
    tags: Array<{id: number; name: string; color: string}>;
  };
  onPlay: (jobId: string) => void;
  onDownload: (jobId: string) => void;
  onView: (jobId: string) => void;
  onDelete: (jobId: string) => void;
}

// Visual States
- Default: White card with subtle shadow
- Hover: Elevated shadow, pointer cursor
- Processing: Pulsing border, progress bar visible
- Failed: Red left border, error icon

// Responsive Breakpoints
- Mobile (<640px): Stacked layout, full-width buttons
- Tablet (640-1024px): 2-column grid
- Desktop (>1024px): 3-column grid
```

**Action**: Create `COMPONENT_SPECS.md` with ALL components before implementation

### 3. Database Migration Plan

Complete migration sequence planned before writing code:

```
Migration 001: Initial Schema
- Create users table
- Create jobs table  
- Create tags table
- Create job_tags junction table
- Create transcripts table
- Create settings table
- Add indexes on: users.username, jobs.status, jobs.user_id, tags.name

Migration 002: Add Full-Text Search (if needed later)
- Add FTS virtual table for jobs
- Add trigger to sync jobs -> FTS table

Migration 003: Add Audit Fields (if needed)
- Add created_by, updated_by to all tables
- Add soft delete support (deleted_at fields)
```

**Action**: Create `DATABASE_MIGRATIONS.md` documenting all planned schema changes

### 4. Test Case Inventory

Comprehensive test checklist created before writing tests:

#### Backend Test Cases

**Authentication (`tests/test_auth.py`)**
- [ ] `test_login_success` - Valid credentials return JWT token
- [ ] `test_login_invalid_password` - Returns 401 with error message
- [ ] `test_login_nonexistent_user` - Returns 401 with error message
- [ ] `test_token_validation` - Valid token allows access to protected route
- [ ] `test_token_expiration` - Expired token returns 401
- [ ] `test_token_invalid_signature` - Tampered token returns 401
- [ ] `test_change_password_success` - Password updated, old password invalid
- [ ] `test_change_password_wrong_current` - Returns 400 if current password wrong
- [ ] `test_logout_invalidates_token` - Token blacklisted after logout

**Job Management (`tests/test_jobs.py`)**
- [ ] `test_create_job_success` - File uploaded, job created, returns job_id
- [ ] `test_create_job_invalid_file_type` - Rejects non-media files
- [ ] `test_create_job_missing_file` - Returns 400 if no file provided
- [ ] `test_list_jobs_empty` - Returns empty array for new user
- [ ] `test_list_jobs_paginated` - Returns correct page of results
- [ ] `test_get_job_detail_success` - Returns full job metadata
- [ ] `test_get_job_detail_not_found` - Returns 404 for invalid job_id
- [ ] `test_get_job_detail_unauthorized` - Returns 403 for other user's job
- [ ] `test_cancel_job_queued` - Job status changes to cancelled
- [ ] `test_cancel_job_processing` - Processing stops, status updated
- [ ] `test_delete_job_success` - Job and files removed from database and storage
- [ ] `test_delete_job_cascade` - Associated transcripts also deleted

**Transcription (`tests/test_transcription.py`)**
- [ ] `test_transcribe_audio_success` - Audio file transcribed, text generated
- [ ] `test_transcribe_video_success` - Video file transcribed (audio extracted)
- [ ] `test_concurrent_job_limit` - Only 3 jobs process simultaneously
- [ ] `test_job_queue_ordering` - Jobs processed in FIFO order
- [ ] `test_progress_updates` - Progress percentage updates correctly
- [ ] `test_stage_transitions` - Stages progress: queued → loading → transcribing → finalizing
- [ ] `test_model_selection` - Correct Whisper model loaded based on request
- [ ] `test_language_detection` - Language auto-detected correctly
- [ ] `test_timestamp_generation` - Timestamps included in output when enabled
- [ ] `test_speaker_detection_placeholder` - Returns speaker_count: 1 (placeholder)
- [ ] `test_transcription_error_handling` - Failed jobs marked as failed with error message

**Export (`tests/test_export.py`)**
- [ ] `test_export_txt` - Plain text format generated correctly
- [ ] `test_export_md` - Markdown format with proper headings
- [ ] `test_export_srt` - SRT subtitle format with correct timecodes
- [ ] `test_export_vtt` - WebVTT format with metadata
- [ ] `test_export_json` - JSON with structured segments and timestamps
- [ ] `test_export_docx` - Word document downloadable and readable
- [ ] `test_export_nonexistent_job` - Returns 404 for invalid job_id

#### Frontend Test Cases

**Login Component (`tests/Login.test.jsx`)**
- [ ] `test_render_login_form` - Form renders with username and password fields
- [ ] `test_submit_valid_credentials` - Calls API, stores token, redirects to dashboard
- [ ] `test_submit_invalid_credentials` - Shows error message, doesn't redirect
- [ ] `test_validation_empty_fields` - Shows validation errors for empty inputs
- [ ] `test_loading_state` - Submit button disabled during API call
- [ ] `test_error_handling_network_failure` - Shows network error message

**JobCard Component (`tests/JobCard.test.jsx`)**
- [ ] `test_render_completed_job` - Shows filename, date, duration, tags
- [ ] `test_render_processing_job` - Shows progress bar, stage, time estimate
- [ ] `test_render_failed_job` - Shows error indicator, no action buttons
- [ ] `test_click_play_button` - Calls onPlay with job_id
- [ ] `test_click_download_button` - Calls onDownload with job_id
- [ ] `test_click_view_button` - Calls onView with job_id
- [ ] `test_click_delete_button` - Calls onDelete with job_id
- [ ] `test_responsive_mobile_layout` - Stacks elements on narrow screen

**NewJobModal Component (`tests/NewJobModal.test.jsx`)**
- [ ] `test_render_modal` - Modal displays with file dropzone
- [ ] `test_file_selection_via_button` - Opens file picker on button click
- [ ] `test_file_drag_drop` - Accepts dropped file, shows filename
- [ ] `test_model_selection` - Dropdown lists all available models
- [ ] `test_toggle_options` - Checkboxes toggle timestamps and speaker detection
- [ ] `test_submit_job` - Calls API with file and options, closes modal
- [ ] `test_cancel_button` - Closes modal without submitting
- [ ] `test_validation_no_file` - Shows error if submit without file

**Action**: Create `TEST_INVENTORY.md` with complete test checklist

### 5. Dependency Audit

Exact versions and justifications for all dependencies:

#### Backend Dependencies
```toml
# Core Framework
fastapi = "^0.104.1"  # Latest stable, async support, auto OpenAPI docs
uvicorn = { version = "^0.24.0", extras = ["standard"] }  # ASGI server with websocket support

# Database
sqlalchemy = "^2.0.23"  # ORM with async support, type hints
alembic = "^1.13.0"  # Database migrations
aiosqlite = "^0.19.0"  # Async SQLite driver

# Data Validation
pydantic = "^2.5.2"  # Data validation, settings management
pydantic-settings = "^2.1.0"  # Environment variable handling

# Authentication & Security
python-jose = { version = "^3.3.0", extras = ["cryptography"] }  # JWT token handling
passlib = { version = "^1.7.4", extras = ["bcrypt"] }  # Password hashing
python-multipart = "^0.0.6"  # Form data parsing for file uploads

# Transcription
openai-whisper = "^20231117"  # Whisper model for transcription
torch = "^2.1.1"  # PyTorch for Whisper (CPU version)
torchaudio = "^2.1.1"  # Audio processing for Whisper

# File Handling & Export
aiofiles = "^23.2.1"  # Async file operations
python-docx = "^1.1.0"  # Word document generation

# Development Tools
pytest = "^7.4.3"  # Testing framework
pytest-asyncio = "^0.21.1"  # Async test support
httpx = "^0.25.2"  # HTTP client for testing API
black = "^23.12.0"  # Code formatting
ruff = "^0.1.7"  # Fast linter (replaces flake8, isort)
```

#### Frontend Dependencies
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.1",
    "axios": "^1.6.2",
    "lucide-react": "^0.294.0",
    "react-dropzone": "^14.2.3",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.7",
    "tailwindcss": "^3.3.6",
    "postcss": "^8.4.32",
    "autoprefixer": "^10.4.16",
    "vitest": "^1.0.4",
    "@testing-library/react": "^14.1.2",
    "@testing-library/jest-dom": "^6.1.5",
    "eslint": "^8.55.0",
    "eslint-plugin-react": "^7.33.2"
  }
}
```

**Action**: Create `DEPENDENCY_JUSTIFICATION.md` documenting why each package is needed

---

## ITERATIVE BUILD SEQUENCE

### Build Increment 1: Project Scaffolding & Database Foundation
**Goal**: Working project structure with database initialization

**Tasks**:
1. Create directory structure (backend, frontend, tests, docs)
2. Initialize git repository with proper .gitignore
3. Set up Python virtual environment
4. Create pyproject.toml with dependencies
5. Install backend dependencies
6. Create database models (User, Job, Tag, Transcript)
7. Write Alembic initial migration
8. Apply migration, verify database created
9. Write test: `test_database_connection`
10. Document: Update README.md with setup instructions

**Test & Verify**:
```bash
cd backend
pytest tests/test_database.py -v
python -c "from app.database import engine; print('Database:', engine.url)"
```

**Commit**: `[Setup] Initialize project structure with database models and migrations`

---

### Build Increment 2: Authentication System
**Goal**: Working login with JWT token generation

**Tasks**:
1. Implement `app/utils/security.py` (password hashing, JWT functions)
2. Write tests for security utilities
3. Create `app/schemas/auth.py` (LoginRequest, TokenResponse)
4. Implement `app/services/auth.py` (authentication logic)
5. Write tests for auth service
6. Create `app/routes/auth.py` (POST /auth/login endpoint)
7. Write API integration tests
8. Seed database with default admin user
9. Test via FastAPI docs UI at /docs
10. Document: Add authentication flow diagram to docs/

**Test & Verify**:
```bash
pytest tests/test_auth.py -v
# Manual test via curl:
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme"}'
# Should return: {"access_token": "...", "token_type": "bearer"}
```

**Commit**: `[Backend/Auth] Implement JWT authentication with login endpoint`

---

### Build Increment 3: Job Creation Without Transcription
**Goal**: Upload files and create job records (transcription stubbed)

**Tasks**:
1. Create `app/utils/file_handling.py` (file validation, storage)
2. Write tests for file utilities
3. Create `app/schemas/job.py` (JobCreate, JobResponse)
4. Implement `app/routes/jobs.py` (POST /jobs endpoint)
5. Write stub transcription service (just marks job as completed immediately)
6. Add authentication middleware to protect job endpoints
7. Write integration tests for job creation
8. Test file upload via API docs UI
9. Verify files saved to storage/media/
10. Document: API examples in docs/API_EXAMPLES.md

**Test & Verify**:
```bash
pytest tests/test_jobs.py::test_create_job_success -v
# Manual test: Upload file via /docs interface, verify job created
```

**Commit**: `[Backend/Jobs] Add job creation endpoint with file upload handling`

---

### Build Increment 4: Job Listing & Retrieval
**Goal**: API endpoints to list and retrieve job details

**Tasks**:
1. Implement GET /jobs endpoint with filtering
2. Implement GET /jobs/{job_id} endpoint
3. Write tests for job listing and detail retrieval
4. Add pagination support
5. Test edge cases (empty list, non-existent job)
6. Document query parameters

**Test & Verify**:
```bash
pytest tests/test_jobs.py::test_list_jobs -v
pytest tests/test_jobs.py::test_get_job_detail -v
```

**Commit**: `[Backend/Jobs] Add job listing and detail retrieval endpoints`

---

### Build Increment 5: Real Transcription Engine
**Goal**: Actual Whisper transcription working end-to-end

**Tasks**:
1. Implement `app/services/transcription.py` (Whisper integration)
2. Write tests with small sample audio file
3. Implement `app/services/job_queue.py` (concurrency control)
4. Add progress tracking to job model
5. Implement GET /jobs/{job_id}/status for polling
6. Test with various audio formats
7. Verify concurrency limit (3 simultaneous jobs)
8. Document: Transcription process flow diagram

**Test & Verify**:
```bash
pytest tests/test_transcription.py -v
# Manual test: Upload real audio file, poll status until complete
```

**Commit**: `[Backend/Transcription] Implement Whisper transcription with job queue`

---

### Build Increment 6: Export Formats
**Goal**: Download transcripts in all supported formats

**Tasks**:
1. Implement `app/services/export.py` (format generators)
2. Write tests for each export format
3. Add GET /transcripts/{job_id}/export endpoint
4. Test each format opens correctly in respective applications
5. Document format specifications

**Test & Verify**:
```bash
pytest tests/test_export.py -v
# Manual verification: Download each format, open in appropriate app
```

**Commit**: `[Backend/Export] Add transcript export in 6 formats (txt, md, srt, vtt, json, docx)`

---

### Build Increment 7: Tag System
**Goal**: Create, assign, and filter by tags

**Tasks**:
1. Create `app/routes/tags.py` (CRUD endpoints)
2. Implement tag assignment to jobs
3. Write tests for tag operations
4. Add tag filtering to job list endpoint
5. Document tag management workflow

**Test & Verify**:
```bash
pytest tests/test_tags.py -v
```

**Commit**: `[Backend/Tags] Implement tag management and job-tag associations`

---

### Build Increment 8: Search Functionality
**Goal**: Full-text search across jobs

**Tasks**:
1. Implement `app/services/search.py`
2. Add search query parameter to GET /jobs
3. Write tests for search functionality
4. Test search performance with 100+ jobs
5. Document search syntax

**Test & Verify**:
```bash
pytest tests/test_search.py -v
```

**Commit**: `[Backend/Search] Add full-text search across job metadata and transcripts`

---

### Build Increment 9: Settings & System Control
**Goal**: User settings and system management endpoints

**Tasks**:
1. Create `app/routes/system.py`
2. Implement settings endpoints
3. Add password change functionality
4. Write tests for settings management
5. Document system control endpoints

**Test & Verify**:
```bash
pytest tests/test_settings.py -v
```

**Commit**: `[Backend/Settings] Add user settings and system control endpoints`

---

### Build Increment 10: Frontend Foundation
**Goal**: React app with routing and login page

**Tasks**:
1. Initialize Vite + React project
2. Set up Tailwind CSS with pine forest theme
3. Configure React Router
4. Implement AuthContext
5. Create Login page component
6. Create ProtectedRoute wrapper
7. Write component tests
8. Test login flow end-to-end

**Test & Verify**:
```bash
cd frontend
npm test
npm run dev
# Manual: Test login at http://localhost:5173
```

**Commit**: `[Frontend/Setup] Initialize React app with authentication flow`

---

### Build Increment 11: Dashboard Layout & Job Cards
**Goal**: Display list of jobs with proper styling

**Tasks**:
1. Create Dashboard page component
2. Implement JobCard component
3. Implement StatusBadge component
4. Implement ProgressBar component
5. Add loading and empty states
6. Write component tests
7. Test responsive design on mobile/tablet/desktop

**Test & Verify**:
```bash
npm test
# Manual: View dashboard with various job states
```

**Commit**: `[Frontend/Dashboard] Add job listing dashboard with cards and status indicators`

---

### Build Increment 12: New Job Modal
**Goal**: Upload interface for creating transcription jobs

**Tasks**:
1. Create NewJobModal component
2. Implement FileDropzone with react-dropzone
3. Add model selection and options
4. Integrate with POST /jobs API
5. Write component tests
6. Test drag-and-drop functionality
7. Test validation and error handling

**Test & Verify**:
```bash
npm test
# Manual: Upload various file types, test drag-drop
```

**Commit**: `[Frontend/Upload] Add new job modal with file upload interface`

---

### Build Increment 13: Job Detail Modal
**Goal**: View job details and perform actions

**Tasks**:
1. Create JobDetailModal component
2. Implement AudioPlayer component
3. Add tag assignment UI
4. Implement action buttons (play, download, delete)
5. Write component tests
6. Test all actions end-to-end

**Test & Verify**:
```bash
npm test
# Manual: Test all job actions
```

**Commit**: `[Frontend/JobDetail] Add job detail modal with media playback and actions`

---

### Build Increment 14: Search & Filters
**Goal**: Search and filter job list

**Tasks**:
1. Create SearchBar component
2. Create JobFilters component
3. Integrate with GET /jobs API
4. Add debounced search
5. Write component tests
6. Test filter combinations

**Test & Verify**:
```bash
npm test
# Manual: Test search and filters with various datasets
```

**Commit**: `[Frontend/Search] Add search and filtering capabilities to job list`

---

### Build Increment 15: Tag Management UI
**Goal**: Create and manage tags

**Tasks**:
1. Create TagInput component with autocomplete
2. Create TagList component
3. Add tag management section in Settings
4. Write component tests
5. Test tag creation and assignment workflow

**Test & Verify**:
```bash
npm test
# Manual: Create tags, assign to jobs, filter by tags
```

**Commit**: `[Frontend/Tags] Add tag management interface with autocomplete`

---

### Build Increment 16: Settings Page
**Goal**: User preferences and system controls

**Tasks**:
1. Create Settings page component
2. Implement change password form
3. Add default transcription options
4. Add system control buttons
5. Write component tests
6. Test all settings persist correctly

**Test & Verify**:
```bash
npm test
# Manual: Change settings, verify persistence
```

**Commit**: `[Frontend/Settings] Add settings page with password change and defaults`

---

### Build Increment 17: Real-time Progress Updates
**Goal**: Live job status updates via polling

**Tasks**:
1. Create usePolling hook
2. Integrate polling into Dashboard
3. Update progress bars in real-time
4. Add stage transitions
5. Test with multiple concurrent jobs

**Test & Verify**:
```bash
npm test
# Manual: Upload multiple jobs, watch progress update
```

**Commit**: `[Frontend/Progress] Add real-time job progress updates via polling`

---

### Build Increment 18: Polish & Responsive Design
**Goal**: Mobile-optimized, polished UI

**Tasks**:
1. Implement mobile navigation
2. Add loading animations
3. Add toast notifications for errors/success
4. Polish all hover states and transitions
5. Test on actual mobile devices
6. Fix any responsive issues

**Test & Verify**:
```bash
# Manual: Test on mobile, tablet, desktop browsers
# Use Chrome DevTools device emulation
```

**Commit**: `[Frontend/Polish] Add mobile responsive design and UI polish`

---

### Build Increment 19: End-to-End Testing
**Goal**: Comprehensive E2E test coverage

**Tasks**:
1. Set up Playwright or Cypress
2. Write E2E tests for critical user flows
3. Test full transcription workflow
4. Test error scenarios
5. Document test execution

**Test & Verify**:
```bash
npm run test:e2e
```

**Commit**: `[Testing] Add end-to-end test suite with Playwright`
**Status (Nov 17 2025)**: Framework established (Playwright multi-browser); smoke tests (login, new job modal, tags placeholder) passing locally & CI; standardized selectors; artifacts on failure enabled. Pending: transcription lifecycle, job detail actions, tag assign/filter flow, search validation, settings password change, cancel & restart scenarios.

---

### Build Increment 20: Production Readiness
**Goal**: Deployment-ready application

**Tasks**:
1. Add production environment configuration
2. Write deployment documentation
3. Create Docker configuration (optional)
4. Add health check monitoring
5. Performance testing and optimization
6. Security audit
7. Create user documentation

**Test & Verify**:
```bash
# Build production artifacts
cd frontend && npm run build
cd backend && pytest --cov
# Deploy to test environment
```

**Commit**: `[Deploy] Add production configuration and deployment documentation`

---

## VERIFICATION CHECKLIST

Before considering the build complete, verify ALL criteria:

### Functional Requirements
- [ ] User can log in with admin credentials
- [ ] User can upload audio/video files
- [ ] Files are transcribed using Whisper
- [ ] Progress updates during transcription
- [ ] Maximum 3 concurrent jobs enforced
- [ ] Completed transcripts viewable
- [ ] Transcripts downloadable in all 6 formats
- [ ] Tags can be created and assigned
- [ ] Jobs can be filtered by status, date, tags
- [ ] Search works across filenames and content
- [ ] Audio playback works in job detail modal
- [ ] Jobs can be cancelled, restarted, deleted
- [ ] Password can be changed
- [ ] Settings persist across sessions
- [ ] UI responsive on mobile, tablet, desktop

### Non-Functional Requirements
- [ ] All backend tests pass (>80% coverage)
- [ ] All frontend tests pass (>70% coverage)
- [ ] E2E tests pass for critical flows
- [ ] No console errors in browser
- [ ] API response times <500ms for non-transcription endpoints
- [ ] File upload works for files up to 1GB
- [ ] Application starts successfully from fresh install
- [ ] Documentation complete and accurate
- [ ] Code follows style guide (black, ruff, eslint)

### Security Requirements
- [ ] Passwords stored as bcrypt hashes
- [ ] JWT tokens expire after 24 hours
- [ ] Invalid tokens rejected with 401
- [ ] File type validation prevents non-media uploads
- [ ] Filenames sanitized to prevent directory traversal
- [ ] CORS configured for allowed origins only
- [ ] SQL injection prevented (using ORM)
- [ ] XSS prevention (React default escaping)

### Documentation Requirements
- [ ] README.md with setup instructions
- [ ] API documentation (auto-generated via FastAPI)
- [ ] Component documentation (JSDoc comments)
- [ ] Deployment guide
- [ ] User guide with screenshots
- [ ] Architecture decision records (ADRs) for major choices

---

## QUALITY GATES

Each build increment must pass these gates before moving to next:

### Gate 1: Tests Pass
```bash
# Backend
cd backend && pytest -v --cov=app --cov-report=term-missing
# Require: All tests pass, coverage >80%

# Frontend  
cd frontend && npm test -- --coverage
# Require: All tests pass, coverage >70%
```

### Gate 2: Code Quality
```bash
# Backend
black app/ tests/ --check
ruff app/ tests/
# Require: No formatting issues, no linting errors

# Frontend
npm run lint
# Require: No ESLint errors
```

### Gate 3: Manual Smoke Test
- Start backend server
- Start frontend dev server
- Test the specific feature implemented in this increment
- Document any issues found

### Gate 4: Documentation Updated
- Check if README needs updating
- Check if API docs need updating
- Add inline code comments if logic is complex
- Update CHANGELOG.md with changes

### Gate 5: Commit Standards
- Commit message follows format: `[Component] Description`
- Commit contains only related changes
- No commented-out code
- No debug print statements
- No unnecessary files

---

## QA GATEWAY SYSTEM

Selenite enforces quality standards through a **three-tier QA gateway** that validates code at multiple stages before it reaches production:

### Tier 1: Pre-Commit Hooks (Local, <30s)
Runs automatically on `git commit` via Husky hooks:
- **Commit Message Validation**: Enforces `[Component] Description` format; rejects temp markers (WIP, TODO)
- **Code Formatting**: Black (backend), ESLint auto-fix (frontend)
- **Linting**: Ruff (backend), ESLint (frontend)
- **Type Checking**: TypeScript strict mode
- **Fast Unit Tests**: Only tests for changed files
- **Documentation Warnings**: Alerts if API/component changes lack doc updates (non-blocking)

**Emergency Bypass**: `git commit --no-verify` or `SKIP_QA=1` environment variable (use sparingly; CI still validates)

### Tier 2: Push CI (GitHub Actions, ~5min)
Runs on every push to `main`/`develop` via `.github/workflows/qa.yml`:
- **Full Test Suites**: Backend (pytest), Frontend (Vitest)
- **Coverage Enforcement**: Backend ≥80%, Frontend ≥70% (fails build if below)
- **E2E Smoke Tests**: Critical flows (login, job creation) on Chromium
- **Security Audits**: pip-audit (backend), npm audit (frontend, moderate+ severity)
- **Artifact Collection**: Test reports, traces, and videos uploaded on failure

### Tier 3: PR CI (GitHub Actions, ~15min)
Runs on pull requests targeting `main`:
- **Multi-Browser E2E**: Chromium, Firefox, WebKit (full test suite)
- **Performance Regression**: Checks for significant slowdowns
- **Coverage Ratcheting**: Ensures coverage never decreases from base branch
- **Branch Protection**: PRs cannot merge until all checks pass

### Quality Metrics Tracked
- **Test Coverage**: Codecov integration with badges in README
- **Build Status**: GitHub Actions badges showing CI health
- **Security Vulnerabilities**: Automated dependency scanning
- **Code Quality**: Ruff/ESLint issue counts tracked over time

### Bypass Guidelines
**When to Bypass** (rare):
- Critical production hotfix needed immediately
- Temporary tooling breakage blocking development
- Experimental branch that won't be merged

**After Bypassing**:
1. Document reason in commit message or PR description
2. Create follow-up task to fix quality issues
3. Ensure fixes applied before merging to main

**Philosophy**: Shift-left testing—catch defects early when fixes are cheapest. Fast feedback loops (pre-commit <30s) prevent interrupting flow, while comprehensive CI validation ensures nothing slips through.

---

## SUCCESS CRITERIA - DEFINITION OF DONE

The project is considered **DONE** when:

1. **All 20 build increments completed and committed**
2. **All functional requirements checked off**
3. **All non-functional requirements met**
4. **All security requirements verified**
5. **All documentation complete**
6. **Application deployable to production**
7. **User can complete end-to-end workflow without developer assistance**
8. **No critical or high-severity bugs**
9. **Performance targets met** (defined in Performance Optimization section)
10. **Code reviewed** (self-review using senior developer mindset)

---

## RISK MITIGATION

### Identified Risks & Mitigations

**Risk**: Whisper transcription too slow on CPU
- **Mitigation**: Start with small model (base), document GPU setup for future
- **Test**: Transcribe 10-minute audio, verify completes in <15 minutes

**Risk**: Concurrent job handling breaks under load
- **Mitigation**: Write stress test with 10 queued jobs, verify queue processes correctly
- **Test**: `tests/test_transcription.py::test_concurrent_job_stress`

**Risk**: Large file uploads fail or timeout
- **Mitigation**: Test with 1GB file, adjust timeout settings, add chunked upload if needed
- **Test**: Upload 1GB file, verify completion

**Risk**: React state management becomes unwieldy
- **Mitigation**: Use Zustand for global state, keep component state local where possible
- **Review**: After Increment 15, assess state management complexity

**Risk**: Database migrations fail on existing data
- **Mitigation**: Write reversible migrations, test upgrade/downgrade cycle
- **Test**: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`

---

## Next Steps

1. **Pre-Build Phase** (Do BEFORE writing code):
   - [ ] Create `docs/API_CONTRACTS.md` with complete endpoint specifications
   - [ ] Create `docs/COMPONENT_SPECS.md` with all React component interfaces
   - [ ] Create `docs/DATABASE_MIGRATIONS.md` with migration plan
   - [ ] Create `docs/TEST_INVENTORY.md` with complete test checklist
   - [ ] Create `docs/DEPENDENCY_JUSTIFICATION.md` with package explanations
   - [ ] Review and sign off on all pre-build artifacts

2. **Environment Setup**:
   - [ ] Verify Python 3.11+ installed: `python --version`
   - [ ] Verify Node.js 18+ installed: `node --version`
   - [ ] Verify Git configured: `git config --list`
   - [ ] Locate Whisper models from whisper-transcriber
   - [ ] Decide: SQLite or PostgreSQL for database

3. **Begin Build Increment 1**: Project Scaffolding
   - Follow the iterative build sequence
   - Complete all tasks for increment
   - Pass all quality gates
   - Commit with proper message
   - Move to next increment

---

## Pre-Build Setup Complete ✅

All prerequisites have been verified and pre-build artifacts created:

1. **Model files**: ✅ COMPLETE
   - Whisper models copied to `D:\Dev\projects\Selenite\models`
   - Models available: tiny, base, small, medium, large-v3
   
2. **Database choice**: ✅ CONFIRMED
   - SQLite for single-user simplicity
   - Migration path to PostgreSQL documented if needed
   
3. **Deployment target**: ✅ CONFIRMED
   - Windows development environment
   - Cross-platform considerations documented
   
4. **Development environment**: ✅ VERIFIED
   - Python 3.11+ installed ✓
   - Node.js 18+ installed ✓
   - VS Code with recommended extensions ✓

5. **Build Process**: ✅ APPROVED
   - Iterative test-driven development approach ✓
   - Atomic commits per feature ✓
   - Quality gates at each increment ✓

6. **Pre-Build Artifacts**: ✅ COMPLETE
   - DEVELOPMENT_PLAN.md: Complete blueprint
   - docs/API_CONTRACTS.md: All endpoints specified
   - docs/COMPONENT_SPECS.md: All components specified
   - docs/PRE_BUILD_VERIFICATION.md: Senior developer approval
   - docs/QUICK_REFERENCE.md: Commands and troubleshooting
   - docs/INITIATION_PROMPT.md: Context prompt for Copilot sessions

---

**This document serves as the complete blueprint for building Selenite with rigorous engineering practices. Follow the 20 build increments sequentially, passing all quality gates at each step. All context, specifications, and test requirements are documented here for complete guidance.**
