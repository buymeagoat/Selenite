#!/usr/bin/env python3
"""
Basic sanity check for environment samples to avoid missing/empty env files.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILES = [REPO_ROOT / ".env.example", REPO_ROOT / "backend" / ".env.example"]


def main() -> None:
    missing = [str(p) for p in ENV_FILES if not p.exists()]
    if missing:
        print(f"Missing env sample files: {', '.join(missing)}")
        sys.exit(1)

    for p in ENV_FILES:
        content = p.read_text(encoding="utf-8").strip()
        if not content:
            print(f"Env sample is empty: {p}")
            sys.exit(1)
    print("Env samples found and non-empty.")


if __name__ == "__main__":
    main()
