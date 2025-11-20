# Selenite Backend

Personal audio/video transcription application backend built with FastAPI.

## Setup

### Prerequisites
- Python 3.10 or higher
- pip

### Installation

1. Create and activate virtual environment:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:
```powershell
pip install -r requirements-minimal.txt
```

3. Copy environment file:
```powershell
cp .env.example .env
```

4. Initialize database:
```powershell
alembic upgrade head
```

### Running the Server (production configuration only)

```powershell
$Env:DISABLE_FILE_LOGS = '1'
$Env:ENVIRONMENT = 'production'
$Env:ALLOW_LOCALHOST_CORS = '1'
uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir app
```

API documentation available at: http://localhost:8100/docs

### Running Tests

```powershell
pytest -v
```

With coverage:
```powershell
pytest --cov=app --cov-report=term-missing
```

### Code Quality

Format code:
```powershell
black app/ tests/
```

Lint code:
```powershell
ruff app/ tests/
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
├── app/
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── routes/          # API endpoints
│   ├── services/        # Business logic
│   ├── utils/           # Utility functions
│   ├── middleware/      # Custom middleware
│   ├── config.py        # Configuration
│   ├── database.py      # Database setup
│   └── main.py          # FastAPI app
├── storage/
│   ├── media/           # Uploaded audio/video files
│   └── transcripts/     # Generated transcripts
├── tests/               # Test files
└── pyproject.toml       # Dependencies
```

## Database

SQLite database with the following tables:
- `users`: User accounts
- `jobs`: Transcription jobs
- `tags`: Organization tags
- `job_tags`: Job-tag associations
- `transcripts`: Generated transcript files

### Creating Migrations

After modifying models:
```powershell
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

## Development

This project follows test-driven development:
1. Write tests first
2. Implement features to pass tests
3. Refactor while keeping tests green
4. Commit when quality gates pass

Quality gates before commit:
- All tests pass
- Code formatted (black)
- Code linted (ruff)
- Manual smoke test
- Documentation updated
