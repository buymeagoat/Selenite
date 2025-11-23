#!/usr/bin/env python3
"""
Generate OpenAPI schema from assembled routers without running full app lifespan.
Outputs to docs/openapi.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import sys
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / "backend"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_PATH))

from app.routes import auth as auth_module
from app.routes import jobs as jobs_module
from app.routes import transcripts as transcripts_module
from app.routes import tags as tags_module
from app.routes import search as search_module
from app.routes import settings as settings_module
from app.routes import exports as exports_module


def build_app() -> FastAPI:
    app = FastAPI(title="Selenite API", version="1.0.0")
    app.include_router(auth_module.router)
    app.include_router(jobs_module.router)
    app.include_router(transcripts_module.router)
    app.include_router(tags_module.router)
    app.include_router(tags_module.job_tags_router)
    app.include_router(search_module.router)
    app.include_router(settings_module.router)
    app.include_router(exports_module.router)
    return app


def main() -> None:
    app = build_app()
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description="Generated OpenAPI schema for Selenite",
    )
    out_path = Path("docs") / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"OpenAPI schema written to {out_path}")


if __name__ == "__main__":
    main()
