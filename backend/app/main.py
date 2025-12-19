"""FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
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
from app.routes import diagnostics as diagnostics_module
from app.routes import model_registry as model_registry_module
from app.routes import file_browser as file_browser_module
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
diagnostics_router = diagnostics_module.router
model_registry_router = model_registry_module.router
file_browser_router = file_browser_module.router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting Selenite application")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"CORS origins: {settings.cors_origins_list}")
    logger.info(f"CORS origin regex: {settings.cors_origin_regex}")

    # Run startup validation checks
    from app.startup_checks import run_startup_checks

    await run_startup_checks()

    # Initialize database and check migrations
    from app.database import engine, AsyncSessionLocal
    from app.migrations_utils import check_migration_status
    from app.services.provider_manager import ProviderManager

    current_rev, head_rev = await check_migration_status(engine)
    logger.info(f"Database migration status: {current_rev} (head: {head_rev})")

    if current_rev != head_rev and settings.is_production:
        logger.warning(
            "Database migrations are not up to date. "
            "Run 'alembic upgrade head' before starting in production."
        )

    # Prime the provider manager cache so availability endpoints surface registry entries immediately
    try:
        async with AsyncSessionLocal() as session:
            await ProviderManager.refresh(session)
    except Exception as exc:
        logger.warning("Provider catalog refresh failed during startup: %s", exc)

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


# Belt-and-suspenders CORS guardrail: always reflect Origin (when present) so browsers get CORS headers even on errors.
@app.middleware("http")
async def ensure_cors_headers(request, call_next):
    origin = request.headers.get("origin")
    method = request.method.upper()
    if method == "OPTIONS":
        from fastapi.responses import Response

        resp = Response(status_code=200)
    else:
        try:
            resp = await call_next(request)
        except HTTPException:
            # Let FastAPI render HTTPException statuses cleanly
            raise
        except Exception:  # noqa: B902
            from fastapi.responses import PlainTextResponse

            # Preserve stack in server logs while still sending CORS headers
            logger.exception("Request failed: %s %s", request.method, request.url)
            resp = PlainTextResponse("Internal Server Error", status_code=500)

    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Methods"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = (
            request.headers.get("access-control-request-headers", "*") or "*"
        )
        resp.headers["Vary"] = "Origin"
    return resp


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware
if not settings.is_testing:
    app.add_middleware(
        RateLimitMiddleware,
        exclude_paths=[
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/settings",
            "/system/info",
            "/system/availability",
            "/system/detect",
            "/system/health",
            "/auth/login",
            "/auth/password",
        ],
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
app.include_router(diagnostics_router)
app.include_router(model_registry_router)
app.include_router(file_browser_router)


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

    # Check registered models
    from app.services.provider_manager import ProviderManager

    snapshot = ProviderManager.get_snapshot()
    models_available = bool(snapshot["asr"])

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "0.1.0",
        "environment": settings.environment,
        "database": db_status,
        "models": "available" if models_available else "missing",
    }
