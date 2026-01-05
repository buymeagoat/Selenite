#!/usr/bin/env python3
from __future__ import annotations

"""
Lightweight migrations sanity check: ensure alembic versions folder exists and is non-empty.
"""

import os
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
VERSIONS = REPO_ROOT / "backend" / "alembic" / "versions"


def main() -> None:
    if not VERSIONS.exists():
        print(f"Missing migrations folder: {VERSIONS}")
        sys.exit(1)
    files = [p for p in VERSIONS.glob("*.py") if p.is_file()]
    if not files:
        print(f"No migration files found in {VERSIONS}")
        sys.exit(1)
    print(f"Found {len(files)} migration files; migrations check passed.")


if __name__ == "__main__":
    main()



