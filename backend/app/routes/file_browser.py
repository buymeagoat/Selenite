"""Read-only file browser for admins, scoped to safe roots."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import PROJECT_ROOT, BACKEND_ROOT
from app.routes.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["file-browser"])

Scope = Literal["models", "root"]


@router.get("/browse")
async def browse_files(
    scope: Scope = Query(
        "models", description="Allowed scopes: models (backend/models) or root (repo root)"
    ),
    path: str | None = Query(
        None, description="Path relative to the scoped base, or absolute /backend/models/..."
    ),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")

    # Always anchor to project root; prevent traversal above it
    base_dir = PROJECT_ROOT.resolve()
    # Normalize incoming path
    if path:
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                candidate = candidate.resolve()
                candidate.relative_to(base_dir)
                target = candidate
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Path must reside within the application root.",
                )
        else:
            target = (base_dir / candidate).resolve()
    else:
        # Default starting point: project root for "root" scope, backend/models for "models" scope
        target = (BACKEND_ROOT / "models").resolve() if scope == "models" else base_dir

    try:
        target.relative_to(base_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Path traversal detected."
        )

    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path does not exist.")

    entries = []
    try:
        for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            entries.append(
                {
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "path": "/" + str(child.relative_to(base_dir).as_posix()),
                }
            )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this path."
        )

    cwd = "/" + str(target.relative_to(base_dir).as_posix())
    if cwd == "/.":
        cwd = "/"
    return {
        "scope": scope,
        "base": str(base_dir.as_posix()),
        "cwd": cwd,
        "entries": entries,
    }
