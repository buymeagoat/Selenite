from pathlib import Path

#!/usr/bin/env python3
"""
Check frontend bundle size after build.
Fails if total size of dist exceeds configured threshold.
"""
from __future__ import annotations

from pathlib import Path

def _ensure_dev_workspace() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    role_file = repo_root / '.workspace-role'
    if role_file.exists():
        role = role_file.read_text(encoding='utf-8').splitlines()[0].strip().lower()
        if role != 'dev':
            raise RuntimeError('This script must be run from a dev workspace.')
_ensure_dev_workspace()

import os
import sys
from pathlib import Path

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def dir_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def main() -> None:
    max_bytes = int(os.getenv("BUNDLE_MAX_BYTES", DEFAULT_MAX_BYTES))
    if not FRONTEND_DIST.exists():
        print(f"Bundle directory not found: {FRONTEND_DIST}")
        sys.exit(1)
    size = dir_size(FRONTEND_DIST)
    if size > max_bytes:
        print(
            f"Bundle size {size/1024/1024:.2f} MB exceeds limit "
            f"{max_bytes/1024/1024:.2f} MB (set BUNDLE_MAX_BYTES to override)."
        )
        sys.exit(1)
    print(f"Bundle size {size/1024/1024:.2f} MB within limit {max_bytes/1024/1024:.2f} MB.")


if __name__ == "__main__":
    main()



