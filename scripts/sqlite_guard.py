"""Ensure the SQLite database lives under backend/selenite.db and quarantine strays.

This script is invoked by bootstrap.ps1 and run-tests.ps1 so humans and agents
don't have to chase down duplicate databases. It never deletes data; instead it
moves unexpected copies into storage/backups with a timestamped filename.
"""

from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List


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


def _should_skip(path: Path, repo_root: Path) -> bool:
    backups = (repo_root / "storage" / "backups").resolve()
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        return True
    return backups in resolved.parents


def _find_duplicates(repo_root: Path, canonical: Path) -> List[Path]:
    duplicates: List[Path] = []
    for db_path in repo_root.rglob("selenite.db"):
        if _should_skip(db_path, repo_root):
            continue
        try:
            resolved = db_path.resolve()
        except FileNotFoundError:
            continue
        if resolved == canonical:
            continue
        duplicates.append(resolved)
    return duplicates


def enforce(repo_root: Path) -> Dict[str, List[str]]:
    repo_root = repo_root.resolve()
    canonical = (repo_root / "backend" / "selenite.db").resolve(strict=False)
    backup_root = (repo_root / "storage" / "backups")
    backup_root.mkdir(parents=True, exist_ok=True)

    duplicates = _find_duplicates(repo_root, canonical)
    actions: Dict[str, List[str]] = {"moved_to_canonical": [], "quarantined": []}

    canonical_exists = canonical.exists()
    if not canonical_exists and duplicates:
        newest = max(duplicates, key=lambda p: p.stat().st_mtime)
        canonical.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(newest), canonical)
        actions["moved_to_canonical"].append(str(newest))
        duplicates = [p for p in duplicates if p != newest]
        canonical_exists = True

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    for idx, stray in enumerate(duplicates, start=1):
        dest = backup_root / f"selenite-stray-{timestamp}-{idx}.db"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(stray), dest)
        actions["quarantined"].append(f"{stray} -> {dest}")

    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize SQLite DB location")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--enforce", action="store_true", help="Move duplicates automatically")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    canonical = (repo_root / "backend" / "selenite.db").resolve(strict=False)
    duplicates = _find_duplicates(repo_root, canonical)

    if not args.enforce:
        if duplicates:
            print("Duplicate SQLite databases detected:")
            for dup in duplicates:
                print(f" - {dup}")
            return 1
        return 0

    actions = enforce(repo_root)
    if actions["moved_to_canonical"]:
        print("Moved stray database(s) into canonical backend/selenite.db:")
        for entry in actions["moved_to_canonical"]:
            print(f" - {entry}")
    if actions["quarantined"]:
        print("Quarantined unexpected database copies under storage/backups:")
        for entry in actions["quarantined"]:
            print(f" - {entry}")
    if not actions["moved_to_canonical"] and not actions["quarantined"]:
        print("No duplicate SQLite databases found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



