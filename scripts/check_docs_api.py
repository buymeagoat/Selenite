import os
from pathlib import Path

#!/usr/bin/env python3
"""
Detect API/docs drift: if backend routes/schemas change, require API contracts to be updated.
"""
from __future__ import annotations

from pathlib import Path

def _ensure_dev_workspace() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    role_file = repo_root / '.workspace-role'
    if role_file.exists():
        role = role_file.read_text(encoding='utf-8').splitlines()[0].strip().lower()
        if role != 'dev':
            if os.getenv("SELENITE_AI_SESSION") != "1":
                return
            if os.getenv("SELENITE_ALLOW_PROD_WRITES") == "1":
                return
            raise RuntimeError('This script must be run from a dev workspace.')
_ensure_dev_workspace()

import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_TARGETS = {"docs/application_documentation/CHANGELOG.md"}
WATCHED_PREFIXES = {
    "backend/app/routes/",
    "backend/app/schemas/",
    "backend/app/models/",
}


def run(cmd: list[str]) -> list[str]:
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_changed_files() -> set[str]:
    base = f"origin/{sys.argv[1]}" if len(sys.argv) > 1 else "origin/main"
    try:
        run(["git", "fetch", "--depth=1", "origin", base.split("/")[-1]])
    except Exception:
        pass
    for diff_base in (f"{base}...HEAD", "HEAD~1..HEAD"):
        try:
            files = run(["git", "diff", "--name-only", diff_base])
            if files:
                return set(files)
        except Exception:
            continue
    return set()


def main() -> None:
    changed = get_changed_files()
    if not changed:
        print("No changed files detected; skipping docs/API check.")
        return

    touched_api = any(any(f.startswith(p) for p in WATCHED_PREFIXES) for f in changed)
    if not touched_api:
        print("No API-related changes detected; skipping docs/API requirement.")
        return

    touched_docs = any(f in DOC_TARGETS for f in changed)
    if touched_docs:
        print("API docs touched; docs/API check passed.")
        return

    missing = ", ".join(sorted(DOC_TARGETS))
    print(f"API-related changes detected without docs updates. Touch one of: {missing}")
    sys.exit(1)


if __name__ == "__main__":
    main()



