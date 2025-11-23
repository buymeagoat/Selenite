#!/usr/bin/env python3
"""
Lightweight migrations sanity check: ensure alembic versions folder exists and is non-empty.
"""
from __future__ import annotations

import sys
from pathlib import Path

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
