#!/usr/bin/env python3
"""
Run alembic upgrade head against a temporary SQLite database to ensure migrations apply cleanly.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"


def main() -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///./ci-migrations.db"
    env["ENVIRONMENT"] = "testing"
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            check=True,
        )
    finally:
        db_path = BACKEND_DIR / "ci-migrations.db"
        if db_path.exists():
            db_path.unlink()
    print("Alembic upgrade head succeeded.")


if __name__ == "__main__":
    main()
