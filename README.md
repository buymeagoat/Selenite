# Selenite 🌙

> Personal audio/video transcription application powered by OpenAI Whisper

Selenite is a self-hosted, privacy-focused transcription service that runs entirely on your local machine. Convert speech to text using state-of-the-art AI models without sending your files to external services.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)

## ✨ Features

- **🔒 Local Processing**: All transcription happens on your device - complete privacy
- **🎯 Multiple Models**: Choose from 5 Whisper models (tiny to large-v3) - balance speed vs. accuracy
- **🌍 90+ Languages**: Supports automatic language detection and translation
- **👥 Speaker Diarization**: Identify different speakers in conversations
- **⏱️ Timestamps**: Add precise timestamps to transcripts
- **🏷️ Tag Organization**: Organize jobs with custom colored tags
- **🔍 Search & Filter**: Quickly find jobs by name, status, date, or tags
- **📊 Real-time Progress**: Watch transcription progress update live
- **📱 Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **🎨 Modern UI**: Clean, intuitive interface with dark mode support

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** and **Node.js 18+**
- **FFmpeg** for audio processing
- **8GB+ RAM** (16GB recommended for larger models)
- **10GB+ storage** for application and models

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/Selenite.git
cd Selenite
```

2. **Backend setup**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

3. **Frontend setup**:
```bash
cd ../frontend
npm install
```

4. **Start the application (production stack only)**:

The fastest way—especially for AI assistants—is to run the automated bootstrap script from the repository root:

```powershell
# PowerShell (Windows)
cd Selenite
.\bootstrap.ps1
```

This script:
- Kills stray python/node processes and unlocks log files.
- Installs backend + frontend dependencies.
- Starts the FastAPI server with `ENVIRONMENT=production`, `ALLOW_LOCALHOST_CORS=1`, and file logging disabled (to avoid Windows log-lock issues).
- Builds the frontend and serves it via `npm run start:prod` (Vite preview) on `http://127.0.0.1:5173`.

If you need to run the commands manually (Linux/macOS):

```bash
# Terminal 1 – Backend API
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-minimal.txt
export DISABLE_FILE_LOGS=1
export ENVIRONMENT=production
export ALLOW_LOCALHOST_CORS=1
uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir app

# Terminal 2 – Frontend (production preview)
cd frontend
npm install
npm run start:prod -- --host 127.0.0.1 --port 5173
```

> We no longer maintain a separate “dev server.” Everything runs with production settings to mirror the actual deployment.

5. **Open in browser**: Navigate to `http://localhost:5173`

Default credentials: `admin` / (your configured password)

## 📖 Documentation

- **[User Guide](docs/USER_GUIDE.md)**: Complete guide for end users
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Production deployment instructions
- **[API Contracts](docs/API_CONTRACTS.md)**: REST API reference
- **[Component Specs](docs/COMPONENT_SPECS.md)**: Frontend component specifications
- **[Development Plan](DEVELOPMENT_PLAN.md)**: Project roadmap and architecture

## 🏗️ Architecture

### Tech Stack

**Backend**:
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM
- **OpenAI Whisper** - Speech recognition models
- **Pydantic** - Data validation
- **SQLite** - Default database (PostgreSQL supported)

**Frontend**:
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Vitest** - Testing framework
- **lucide-react** - Icon library

### Project Structure

```
Selenite/
├── backend/
│   ├── app/
│   │   ├── routes/          # API endpoints
│   │   ├── services/        # Business logic
│   │   ├── models/          # Database models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── tests/           # Backend tests (129 tests)
│   ├── storage/             # Media and transcript storage
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   ├── types/           # TypeScript types
│   │   └── tests/           # Frontend tests (104 tests)
│   ├── Dockerfile
│   └── package.json
├── models/                  # Whisper model files
├── docs/                    # Documentation
├── docker-compose.yml
└── README.md
```

## 🎯 Usage

### Creating a Transcription Job

1. Click the **+** button on the dashboard
2. Upload your audio/video file (drag & drop or browse)
3. Choose a Whisper model:
   - **tiny**: Fastest, lowest quality (~1GB RAM)
   - **small**: Good balance (~2GB RAM)
   - **medium**: Best for most use cases (~5GB RAM) [Default]
   - **large-v3**: Highest accuracy (~10GB RAM)
4. Select language (or auto-detect)
5. Enable options: speaker detection, timestamps, translation
6. Add tags for organization (optional)
7. Click **Start Transcription**

### Managing Jobs

- **View Jobs**: All jobs appear on the dashboard
- **Search**: Type filename to filter results
- **Filter**: By status, date range, or tags
- **View Details**: Click any job card to see full transcript
- **Download**: Export as SRT, VTT, or TXT
- **Restart**: Re-run failed jobs
- **Delete**: Remove jobs and files

### Settings

Access via the gear icon (⚙️):
- **Account**: Change password
- **Transcription Options**: Set default model, language, and options
- **Performance**: Adjust concurrent jobs (1-5)
- **Storage**: View disk usage
- **Tags**: Create, edit, delete tags
- **System**: Restart or shutdown application

## 🧪 Testing

### Backend Tests
```bash
cd backend
source venv/bin/activate
pytest
# 129 tests covering auth, jobs, transcripts, tags, search, settings
```

### Frontend Tests
```bash
cd frontend
npm test
# 104 tests covering components, pages, hooks
```

### Test Coverage
- Backend: 129 tests, ~85% coverage
- Frontend: 104 tests across 17 files

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Environment Variables

Create `backend/.env` from `.env.example`:

```bash
# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=sqlite+aiosqlite:///./selenite.db

# Storage
MEDIA_STORAGE_PATH=./storage/media
TRANSCRIPT_STORAGE_PATH=./storage/transcripts
MODEL_STORAGE_PATH=../models

# Transcription
MAX_CONCURRENT_JOBS=3
DEFAULT_WHISPER_MODEL=medium
DEFAULT_LANGUAGE=auto

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173

# Logging
LOG_LEVEL=INFO
```

## 🛠️ Development

### Backend Development

```bash
cd backend
source .venv/bin/activate

# Run the production-configured API locally
ENVIRONMENT=production \
ALLOW_LOCALHOST_CORS=1 \
DISABLE_FILE_LOGS=1 \
uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir app

# Run tests
pytest

# Type checking
mypy app/

# Linting
ruff check app/

# Format code
black app/
```

### Frontend Tasks

```bash
cd frontend

# Production preview (build + serve on 127.0.0.1:5173)
npm run start:prod

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

### API Documentation

Start the backend and navigate to:
- **Swagger UI**: `http://localhost:8100/docs`
- **ReDoc**: `http://localhost:8100/redoc`

## 📊 Performance

### Whisper Model Benchmarks

| Model | Speed | Accuracy | RAM | Disk | Use Case |
|-------|-------|----------|-----|------|----------|
| tiny | ⚡⚡⚡⚡⚡ | ⭐⭐ | ~1GB | 75MB | Quick drafts, testing |
| small | ⚡⚡⚡⚡ | ⭐⭐⭐ | ~2GB | 244MB | Personal use, good quality |
| medium | ⚡⚡⚡ | ⭐⭐⭐⭐ | ~5GB | 769MB | **Recommended** - best balance |
| large-v2 | ⚡⚡ | ⭐⭐⭐⭐⭐ | ~10GB | 1.5GB | Professional work |
| large-v3 | ⚡ | ⭐⭐⭐⭐⭐ | ~10GB | 1.5GB | Critical accuracy needs |

### Transcription Times (1-hour audio)

- **tiny**: ~5 minutes
- **small**: ~10 minutes
- **medium**: ~25 minutes
- **large-v3**: ~60+ minutes

*Times vary based on CPU performance and system load.*

## 🔒 Security

- **Local Processing**: Files never leave your device
- **Password Protection**: Login required for all operations
- **JWT Authentication**: Secure token-based auth
- **No Telemetry**: No usage data collection
- **Open Source**: Audit the code yourself

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Write/update tests
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Development Guidelines

- Follow existing code style (Black for Python, Prettier for TypeScript)
- Write tests for new features
- Update documentation as needed
- Keep commits focused and descriptive

## 📝 Roadmap

### Completed ✅
- [x] Backend API (auth, jobs, transcripts, tags, search, settings)
- [x] Frontend UI (dashboard, modals, search, filters, tags, settings)
- [x] Real-time progress updates
- [x] Tag management system
- [x] Mobile responsive design
- [x] Docker deployment
- [x] Health check endpoint
- [x] Comprehensive documentation

### Planned 🚧
- [ ] E2E testing with Playwright
- [ ] PostgreSQL support for production
- [ ] GPU acceleration for faster transcription
- [ ] Batch upload (multiple files at once)
- [ ] Advanced speaker diarization UI
- [ ] Transcript editing interface
- [ ] Export to more formats (PDF, DOCX)
- [ ] API rate limiting
- [ ] Multi-user support with permissions
- [ ] Cloud storage integration (S3, Google Drive)

## 🐛 Known Issues

- Transcription times can be lengthy for large files with big models
- Speaker diarization accuracy depends on audio quality
- Mobile UI testing still in progress

See [GitHub Issues](https://github.com/yourusername/Selenite/issues) for full list.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI Whisper** - Speech recognition models
- **FastAPI** - Web framework
- **React** - UI library
- **Tailwind CSS** - Styling framework
- Contributors and testers who helped improve Selenite

## 📞 Support

- **Documentation**: See `docs/` directory
- **Bug Reports**: [GitHub Issues](https://github.com/yourusername/Selenite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Selenite/discussions)
- **Email**: your-email@example.com

---

**Built with ❤️ for privacy-conscious transcription**

Made by [Your Name](https://github.com/yourusername) | [Website](https://your-website.com)
