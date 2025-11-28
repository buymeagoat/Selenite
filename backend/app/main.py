"""FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.routes import auth as auth_module
from app.routes import jobs as jobs_module
from app.routes import transcripts as transcripts_module
from app.routes import tags as tags_module
from app.routes import search as search_module
from app.routes import settings as settings_module
from app.routes import exports as exports_module
from app.routes import system as system_module
from app.services.job_queue import queue, resume_queued_jobs
from app.services.system_probe import SystemProbeService

# Initialize logging
setup_logging()
logger = logging.getLogger("app.main")

auth_router = auth_module.router
jobs_router = jobs_module.router
transcripts_router = transcripts_module.router
tags_router = tags_module.router
job_tags_router = tags_module.job_tags_router
search_router = search_module.router
settings_router = settings_module.router
exports_router = exports_module.router
system_router = system_module.router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting Selenite application")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"CORS origins: {settings.cors_origins_list}")

    # Run startup validation checks
    from app.startup_checks import run_startup_checks

    await run_startup_checks()

    # Initialize database and check migrations
    from app.database import engine
    from app.migrations_utils import check_migration_status

    current_rev, head_rev = await check_migration_status(engine)
    logger.info(f"Database migration status: {current_rev} (head: {head_rev})")

    if current_rev != head_rev and settings.is_production:
        logger.warning(
            "Database migrations are not up to date. "
            "Run 'alembic upgrade head' before starting in production."
        )

    # Expose queue via app state; only auto-start outside of unit tests
    app.state.queue = queue
    force_queue_start = os.getenv("FORCE_QUEUE_START") == "1"
    if settings.is_testing and not force_queue_start:
        logger.info("Testing mode detected; job queue will be started by tests as needed")
    else:
        await queue.start()
        resumed = await resume_queued_jobs(queue)
        if resumed:
            logger.info("Job queue started and resumed %s queued job(s)", resumed)
        else:
            logger.info("Job queue started")

    # Prime the system probe cache so the admin UI has data immediately
    try:
        SystemProbeService.refresh_probe()
    except Exception as exc:
        logger.warning("System probe failed during startup: %s", exc)

    yield

    # Shutdown
    logger.info("Shutting down Selenite application")


# Create FastAPI app
app = FastAPI(
    title="Selenite",
    description="Personal audio/video transcription application",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware
if not settings.is_testing:
    app.add_middleware(
        RateLimitMiddleware, exclude_paths=["/health", "/docs", "/openapi.json", "/redoc"]
    )

# Include routers
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(transcripts_router)
app.include_router(tags_router)
app.include_router(job_tags_router)
app.include_router(search_router)
app.include_router(settings_router)
app.include_router(exports_router)
app.include_router(system_router)


@app.get("/health")
async def health_check():
    """Health check endpoint with system status."""
    from app.database import engine
    from sqlalchemy import text

    # Check database connectivity
    db_status = "unknown"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # Check model directory
    from pathlib import Path

    model_path = Path(settings.model_storage_path)
    models_available = model_path.exists() and any(model_path.glob("*.pt"))

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "0.1.0",
        "environment": settings.environment,
        "database": db_status,
        "models": "available" if models_available else "missing",
    }
