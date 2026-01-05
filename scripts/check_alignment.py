#!/usr/bin/env python
"""
Verify alignment invariants (registry paths, storage directories, legacy folders).
Exits with non-zero status when drift is detected.
"""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
import sys
from pathlib import Path


def _ensure_dev_workspace() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    role_file = repo_root / ".workspace-role"
    if role_file.exists():
        role = role_file.read_text(encoding="utf-8").splitlines()[0].strip().lower()
        if role != "dev":
            if os.getenv("SELENITE_AI_SESSION") != "1":
                return
            if os.getenv("SELENITE_ALLOW_PROD_WRITES") == "1":
                return
            raise RuntimeError("This script must be run from a dev workspace.")


_ensure_dev_workspace()

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import BACKEND_ROOT, PROJECT_ROOT, settings  # type: ignore  # noqa
from app.database import AsyncSessionLocal  # type: ignore  # noqa
from app.utils.alignment import AlignmentChecker, format_issues, gather_alignment_issues  # type: ignore  # noqa


def _backend_python() -> Path:
    if platform.system() == "Windows":
        return BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    return BACKEND_DIR / ".venv" / "bin" / "python"


def _ensure_migrations_current() -> None:
    backend_python = _backend_python()
    if not backend_python.exists():
        raise RuntimeError(
            f"Backend virtualenv python not found at {backend_python}. "
            "Create the venv first (cd backend; python -m venv .venv; "
            " .\\.venv\\Scripts\\activate) and install requirements."
        )

    cmd = [str(backend_python), "-m", "alembic", "upgrade", "head"]
    try:
        subprocess.run(cmd, cwd=BACKEND_DIR, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Failed to bring the database schema up to date via Alembic.\n"
            "Run 'python -m alembic upgrade head' inside backend/.venv manually and inspect the error above."
        ) from exc


async def _run() -> int:
    checker = AlignmentChecker(
        model_root=Path(settings.model_storage_path),
        storage_root=(PROJECT_ROOT / "storage"),
        backend_root=BACKEND_ROOT,
        project_root=PROJECT_ROOT,
        media_path=Path(settings.media_storage_path),
        transcript_path=Path(settings.transcript_storage_path),
        allow_test_storage=settings.is_testing,
    )

    async with AsyncSessionLocal() as session:
        issues = await gather_alignment_issues(session=session, checker=checker)

    if issues:
        print("Alignment check failed:")
        print(format_issues(issues))
        print("\nResolve the issues above (or run migration scripts) before shipping changes.", file=sys.stderr)
        return 1

    print("Alignment check passed: registry paths, storage, and filesystem are canonical.")
    return 0


def main() -> None:
    try:
        _ensure_migrations_current()
        exit_code = asyncio.run(_run())
    except KeyboardInterrupt:
        exit_code = 130
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()



