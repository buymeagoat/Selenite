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

## Automated Tests

Run the full suite from the repo root:

```powershell
.\scripts\run-tests.ps1
```

Common switches: `-SkipBackend`, `-SkipFrontend`, `-SkipE2E`, `-ForceBackendInstall`, `-ForceFrontendInstall`.

## Documentation

- User guide: `docs/application_documentation/USER_GUIDE.md`
- Deployment guide: `docs/application_documentation/DEPLOYMENT.md`
- API contracts: `docs/API_CONTRACTS.md`
- Component specs: `docs/COMPONENT_SPECS.md`
- Development plan: `docs/build/DEVELOPMENT_PLAN.md`

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

## Roadmap

Future enhancements are tracked in `docs/build/PRODUCTION_TASKS.md` under "Future Enhancements (Post-MVP)".

## Support

- Issues: https://github.com/buymeagoat/Selenite/issues

