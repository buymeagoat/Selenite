# Deployment Guide

This guide provides step-by-step instructions for deploying Selenite to a production environment.

## 🚀 Quick Production Setup

### 1. Generate Secure Credentials
```bash
# Generate a secure secret key (32+ characters)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Configure Environment

Copy `.env.production.example` to `.env` in the backend directory:

```bash
cd backend
cp .env.production.example .env
```

**CRITICAL**: Update these values in `.env`:
- `ENVIRONMENT=production`
- `SECRET_KEY=<paste-your-generated-key>`
- `DATABASE_URL=postgresql+asyncpg://user:password@localhost/selenite`
- `CORS_ORIGINS=https://yourdomain.com`
- Storage paths to absolute paths (e.g., `/var/lib/selenite/media`)

### 3. Validate Configuration

```bash
# Test that production config is valid
cd backend
python -c "from app.config import settings; print(f'Environment: {settings.environment}'); print(f'Valid: {settings.is_production}')"
```

**Expected**: Should complete without errors. If you see validation errors about SECRET_KEY or CORS_ORIGINS, fix them before proceeding.

### 4. Setup Database

```bash
cd backend
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
alembic upgrade head
```

### 5. Check Health

```bash
# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, check health
curl http://localhost:8100/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "healthy",
  "models": "available"
}
```

---

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Building](#building)
- [Running](#running)
- [Docker Deployment](#docker-deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2
- **CPU**: 4+ cores recommended (Whisper model inference is CPU-intensive)
- **RAM**: 8GB minimum, 16GB+ recommended for large models
- **Storage**: 10GB minimum for application + models, SSD recommended
- **Python**: 3.10 or 3.11
- **Node.js**: 18.x or 20.x
- **FFmpeg**: Required for audio processing

### Software Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm ffmpeg

# macOS (with Homebrew)
brew install python@3.11 node ffmpeg

# Windows (with Chocolatey)
choco install python311 nodejs ffmpeg
```

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/Selenite.git
cd Selenite
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download Whisper models (optional, can be done via UI)
python -c "import whisper; whisper.load_model('medium')"
```

### 3. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install
```

## Configuration

### Backend Configuration

1. **Copy environment template**:
```bash
cd backend
cp .env.example .env
```

2. **Edit `.env` file** with production values:
```bash
# Generate a secure secret key
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
echo "SECRET_KEY=$SECRET_KEY" >> .env

# Configure database (SQLite default, or use PostgreSQL)
DATABASE_URL=sqlite+aiosqlite:///./selenite.db
# For PostgreSQL: postgresql+asyncpg://user:password@localhost/selenite

# Storage paths (absolute paths recommended for production)
MEDIA_STORAGE_PATH=/var/selenite/media
TRANSCRIPT_STORAGE_PATH=/var/selenite/transcripts
MODEL_STORAGE_PATH=/var/selenite/models

# Performance tuning
MAX_CONCURRENT_JOBS=3  # Adjust based on CPU cores
DEFAULT_WHISPER_MODEL=medium  # or small, large-v3

# Server configuration
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Logging
LOG_LEVEL=INFO  # Use ERROR for production if high volume
```

3. **Create storage directories**:
```bash
sudo mkdir -p /var/selenite/{media,transcripts,models}
sudo chown -R $USER:$USER /var/selenite
```

4. **Initialize database**:
```bash
# Database tables are created automatically on first run
# To verify, run:
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

### Frontend Configuration

1. **Create `.env.production` file**:
```bash
cd frontend
cat > .env.production << EOF
VITE_API_URL=https://api.your-domain.com
EOF
```

2. **Update API base URL** (if not using environment variable):
Edit `frontend/src/config.ts`:
```typescript
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.your-domain.com';
```

## Building

### Backend
No build step required for Python backend. Skip to [Running](#running).

### Frontend
```bash
cd frontend

# Build production bundle
npm run build

# Output will be in frontend/dist/
# Preview production build locally (optional)
npm run preview
```

## Running

### Local Production Run (single-thread stack)

Use the bootstrap script to mimic the deployment configuration on a workstation:

```powershell
cd D:\Dev\projects\Selenite
.\bootstrap.ps1
```

If you need a manual run (Linux/macOS):

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-minimal.txt
python -m alembic upgrade head
python -m app.seed
export DISABLE_FILE_LOGS=1
export ENVIRONMENT=production
export ALLOW_LOCALHOST_CORS=1
uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir app

# Frontend
cd frontend
npm install
npm run start:prod -- --host 127.0.0.1 --port 5173

# Smoke test from repo root to verify backend readiness
python scripts/smoke_test.py --base-url http://127.0.0.1:8100 --health-timeout 90
```

### Production Mode

#### Backend with Gunicorn (Linux/macOS)
```bash
cd backend
source venv/bin/activate

# Install Gunicorn
pip install gunicorn

# Run with Uvicorn workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300 \
  --access-logfile /var/log/selenite/access.log \
  --error-logfile /var/log/selenite/error.log
```

#### Frontend with Nginx
1. **Copy build files**:
```bash
sudo mkdir -p /var/www/selenite
sudo cp -r frontend/dist/* /var/www/selenite/
```

2. **Configure Nginx** (`/etc/nginx/sites-available/selenite`):
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    root /var/www/selenite;
    index index.html;

    # Frontend (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api {
        proxy_pass http://localhost:8100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for transcription jobs
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

3. **Enable site and reload**:
```bash
sudo ln -s /etc/nginx/sites-available/selenite /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

4. **Setup SSL with Let's Encrypt** (recommended):
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

#### Systemd Service (Backend)
Create `/etc/systemd/system/selenite-backend.service`:
```ini
[Unit]
Description=Selenite Transcription Backend
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/selenite/backend
Environment="PATH=/opt/selenite/backend/venv/bin"
ExecStart=/opt/selenite/backend/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable selenite-backend
sudo systemctl start selenite-backend
sudo systemctl status selenite-backend
```

## Docker Deployment

### Using Docker Compose (Recommended)
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

See `docker-compose.yml` in the root directory for configuration.

### Manual Docker Build
```bash
# Build backend
docker build -t selenite-backend -f backend/Dockerfile backend/

# Build frontend
docker build -t selenite-frontend -f frontend/Dockerfile frontend/

# Run backend
docker run -d \
  --name selenite-backend \
  -p 8000:8000 \
  -v $(pwd)/storage:/app/storage \
  -v $(pwd)/models:/app/models \
  --env-file backend/.env \
  selenite-backend

# Run frontend
docker run -d \
  --name selenite-frontend \
  -p 80:80 \
  selenite-frontend
```

## Monitoring

### Health Checks
The backend exposes a health check endpoint:
```bash
curl http://localhost:8100/health
# Expected response: {"status":"healthy","version":"1.0.0"}
```

### Uptime Monitoring
Configure external monitoring services (UptimeRobot, Pingdom, etc.) to poll:
- Frontend: `https://your-domain.com`
- Backend health: `https://api.your-domain.com/health`
- Interval: 5 minutes
- Alert on: 3 consecutive failures

### Log Monitoring
```bash
# Backend logs (if using systemd)
journalctl -u selenite-backend -f

# Nginx access logs
tail -f /var/log/nginx/access.log

# Nginx error logs
tail -f /var/log/nginx/error.log

# Application logs (if configured)
tail -f /var/log/selenite/error.log
```

### Resource Monitoring
```bash
# CPU and memory usage
htop

# Disk usage
df -h
du -sh /var/selenite/*

# Active connections
netstat -tuln | grep :8000
```

### Prometheus + Grafana (Advanced)
1. Install Prometheus and Grafana
2. Add `prometheus-fastapi-instrumentator` to backend:
```bash
pip install prometheus-fastapi-instrumentator
```
3. Instrument FastAPI app in `backend/app/main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```
4. Configure Prometheus to scrape `http://localhost:8100/metrics`
5. Import Grafana dashboards for FastAPI metrics

## Troubleshooting

### Backend Issues

**Database Connection Errors**:
```bash
# Verify database file permissions
ls -la selenite.db

# Check SQLite integrity
sqlite3 selenite.db "PRAGMA integrity_check;"

# For PostgreSQL, check connection
psql -h localhost -U selenite -d selenite -c "SELECT 1;"
```

**Transcription Failures**:
```bash
# Verify FFmpeg installation
ffmpeg -version

# Check model files exist
ls -lh models/*.pt

# Test Whisper manually
python -c "import whisper; model = whisper.load_model('medium'); print('OK')"
```

**Worker Process Crashes**:
```bash
# Check system memory
free -h

# Reduce concurrent jobs in .env
MAX_CONCURRENT_JOBS=1

# Check for OOM kills
dmesg | grep -i "out of memory"
```

### Frontend Issues

**API Connection Failures**:
- Verify `VITE_API_URL` in `.env.production`
- Check CORS configuration in backend `.env`
- Inspect browser console for network errors
- Test API directly: `curl https://api.your-domain.com/health`

**Build Errors**:
```bash
# Clear cache and rebuild
rm -rf node_modules package-lock.json
npm install
npm run build
```

**Routing Issues (404 on refresh)**:
- Ensure Nginx `try_files` directive is configured for SPA routing
- Verify `index.html` is at web root: `/var/www/selenite/index.html`

### Docker Issues

**Container Won't Start**:
```bash
# Check logs
docker logs selenite-backend
docker logs selenite-frontend

# Verify port availability
sudo netstat -tuln | grep :8000

# Check resource limits
docker stats
```

**Volume Permission Errors**:
```bash
# Fix ownership
sudo chown -R 1000:1000 ./storage ./models

# Or run container as root (not recommended)
docker run --user root ...
```

## Performance Tuning

### Backend Optimization
- **Workers**: Set to `(2 * CPU_cores) + 1` for Gunicorn
- **Max Concurrent Jobs**: Start with `CPU_cores - 1`, adjust based on RAM
- **Model Selection**: `tiny` (fastest), `small` (good), `medium` (best quality), `large-v3` (high accuracy, very slow)
- **Database**: Use PostgreSQL for production instead of SQLite for better concurrency

### Frontend Optimization
- Enable Gzip/Brotli compression in Nginx
- Configure CDN for static assets
- Implement service worker for offline support
- Enable HTTP/2 in Nginx

### Storage Optimization
```bash
# Set up automatic cleanup of old transcriptions
# Add to crontab: crontab -e
0 2 * * * find /var/selenite/media -type f -mtime +30 -delete
0 2 * * * find /var/selenite/transcripts -type f -mtime +90 -delete
```

## Security Hardening

1. **Change default admin password immediately** after first login
2. **Enable HTTPS** with Let's Encrypt certificates (see Nginx section)
3. **Configure firewall**:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```
4. **Restrict backend access**: Backend should only be accessible via Nginx proxy, not directly exposed
5. **Regular updates**:
```bash
# Backend dependencies
pip install --upgrade -r requirements.txt

# Frontend dependencies
npm update
```
6. **Backup strategy**:
```bash
# Backup script example
#!/bin/bash
tar -czf /backups/selenite-$(date +%Y%m%d).tar.gz \
  /var/selenite/media \
  /var/selenite/transcripts \
  /opt/selenite/backend/selenite.db
```

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple backend instances behind a load balancer
- Use shared storage (NFS, S3) for media/transcript files
- Migrate to PostgreSQL with connection pooling
- Implement Redis for job queue management

### Vertical Scaling
- Increase RAM for larger Whisper models
- Add GPU support for faster transcription (CUDA-enabled GPsU)
- Use NVMe SSDs for storage

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/yourusername/Selenite/issues
- **Documentation**: See `docs/` directory
- **User Guide**: See `USER_GUIDE.md`

---

**Deployment Checklist**:
- [ ] Environment variables configured (`.env`)
- [ ] Storage directories created with proper permissions
- [ ] Database initialized
- [ ] Frontend built (`npm run build`)
- [ ] Nginx configured and SSL enabled
- [ ] Systemd service running
- [ ] Health check endpoint responding
- [ ] Monitoring configured
- [ ] Backups scheduled
- [ ] Default admin password changed
- [ ] Firewall rules applied
