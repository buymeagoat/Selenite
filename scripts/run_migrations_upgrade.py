#!/usr/bin/env python3
from __future__ import annotations

"""
Run alembic upgrade head against a temporary SQLite database to ensure migrations apply cleanly.
"""

import os
import subprocess
import sys
from pathlib import Path


def _ensure_dev_workspace() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    role_file = repo_root / ".workspace-role"
    if role_file.exists():
        role = role_file.read_text(encoding="utf-8").splitlines()[0].strip().lower()
        if role != "dev":
            allow_prod = os.getenv("SELENITE_ALLOW_PROD_WRITES") == "1"
            allow_gates = os.getenv("SELENITE_ALLOW_COMMIT_GATES") == "1"
            if not (allow_prod and allow_gates):
                raise RuntimeError("This script must be run from a dev workspace.")


_ensure_dev_workspace()

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"


def main() -> None:
    env = os.environ.copy()
    db_path = BACKEND_DIR / "ci-migrations.db"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    env["ENVIRONMENT"] = "testing"
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            check=True,
        )
    finally:
        if db_path.exists():
            db_path.unlink()
    print("Alembic upgrade head succeeded.")


if __name__ == "__main__":
    main()



