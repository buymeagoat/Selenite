"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth as auth_module
from app.routes import jobs as jobs_module
from app.routes import transcripts as transcripts_module
from app.routes import tags as tags_module
from app.services.job_queue import queue

auth_router = auth_module.router
jobs_router = jobs_module.router
transcripts_router = transcripts_module.router
tags_router = tags_module.router
job_tags_router = tags_module.job_tags_router

# Create FastAPI app
app = FastAPI(
    title="Selenite",
    description="Personal audio/video transcription application",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(transcripts_router)
app.include_router(tags_router)
app.include_router(job_tags_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
    }


@app.on_event("startup")
async def startup_event():
    """Initialize background workers for transcription queue."""
    # Expose queue via app state to avoid import duplication issues
    app.state.queue = queue
    await queue.start()


# Note: We intentionally do not stop the queue on app shutdown in tests,
# because httpx's ASGITransport manages lifespan per client context. Stopping
# here would terminate workers before background jobs complete.
