# Selenite

Personal audio/video transcription application powered by OpenAI Whisper.

Selenite is a self-hosted, privacy-focused transcription service that runs entirely on your local machine. Convert speech to text without sending files to external services.

## Features

- Local processing (no cloud upload).
- Admin-managed ASR/diarizer registry with explicit enable/disable.
- Speaker diarization and timestamps.
- Tag-based organization with colored tags.
- Search and filter by status, date, or tags.
- Responsive UI for desktop, tablet, and mobile.
- Export formats: txt, srt, vtt, json, docx, md.

## Quick Start

### Prerequisites

- Python 3.10+ and Node.js 18+
- FFmpeg for audio processing
- 8GB+ RAM (16GB recommended for larger models)
- 10GB+ storage for application and models

> Storage is canonicalized to `./storage` (with `storage/media` and `storage/transcripts`). Any legacy `backend/storage` paths are deprecated.

### Installation

1) Clone the repository:

```bash
git clone https://github.com/buymeagoat/Selenite.git
cd Selenite
```

2) Backend setup:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

3) Frontend setup:

```bash
cd ../frontend
npm install
```

4) Start the application (Windows recommended):

```powershell
cd Selenite
.\scripts\bootstrap.ps1
```

If you run manually, mirror the production settings from `scripts/bootstrap.ps1` and keep `ENVIRONMENT=production`.

### Model Registry Workflow (Admins)

- Providers and weights are never auto-downloaded.
- Place model checkpoints under `backend/models/<set>/<weight>/...`.
- Enable weights and set defaults in the Admin UI before creating jobs.
- If no enabled weights exist, job creation is blocked with a clear admin message.

## Documentation

- User guide: `docs/application_documentation/USER_GUIDE.md`
- Deployment guide: `docs/application_documentation/DEPLOYMENT.md`
- Release runbook: `docs/application_documentation/RELEASE_RUNBOOK.md`
- Changelog: `docs/application_documentation/CHANGELOG.md`
- Diarization setup: `docs/application_documentation/PYANNOTE_SETUP.md`

## Documentation Scope (Prod vs Dev)

This repository (prod) only keeps **operations** documentation. Development, build, testing, and memorialization artifacts live in the dev repo (`Selenite-dev`).

**Prod keeps (ops-only):**
- `README.md`
- `docs/application_documentation/*`

**Dev keeps (build/test/guidance):**
- `docs/build/**`
- `docs/pre-build/**`
- `docs/memorialization/**`
- `AGENTS.md`, `docs/AI_COLLAB_CHARTER.md`
- `docs/API_CONTRACTS.md`, `docs/COMPONENT_SPECS.md`, `docs/openapi.json`

**Artifacts policy:**
- `.last_tests_run` and `docs/memorialization/**` are **dev-only** and should not be committed in prod.
- If tests are run from the prod repo, move any memorialization output to `Selenite-dev` before pushing.

## Project Structure

```
Selenite/
  backend/
    app/
    tests/
    models/
  frontend/
    src/
      components/
      pages/
      hooks/
      tests/
  storage/
  docs/
  scripts/
  docker-compose.yml
  README.md
```

## Support

- Issues: https://github.com/buymeagoat/Selenite/issues
