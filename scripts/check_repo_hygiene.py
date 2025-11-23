#!/usr/bin/env python3
"""
Repository hygiene enforcement.

Run after automated test suites to ensure no duplicate storage paths, stray databases,
or leftover artifacts clog the repo.
"""

from __future__ import annotations

import sys
from pathlib import Path
import json
import subprocess
import shutil
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = REPO_ROOT / "repo-hygiene-policy.json"


def fail(messages: Iterable[str]) -> None:
    print("Repository hygiene check failed:")
    for msg in messages:
        print(f" - {msg}")
    sys.exit(1)


def _dir_is_empty(path: Path) -> bool:
    return not any(path.rglob("*"))


def load_policy() -> dict:
    try:
        return json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail([f"Hygiene policy file missing: {POLICY_FILE}"])
        raise  # unreachable


def gather_lines(cmd: list[str]) -> list[str]:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        fail([f"Command {' '.join(cmd)} failed: {result.stderr.strip()}"])
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> None:
    errors: list[str] = []
    policy = load_policy()
    policy_version = policy.get("policy_version")
    if not policy_version:
        fail(["repo-hygiene-policy.json missing 'policy_version' key"])

    # Best-effort cleanup of transient artifacts (test DBs, temp storage)
    transient_paths = [
        REPO_ROOT / "backend" / "selenite.db",
        REPO_ROOT / "backend" / "selenite.test.db",
        REPO_ROOT / "backend" / "storage",
    ]
    for path in transient_paths:
        try:
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
        except Exception:
            # Do not block hygiene on cleanup failures; the check will catch leftovers if present.
            pass

    # Clean git status if required.
    if policy.get("require_clean_git_status", False):
        dirty = gather_lines(["git", "status", "--short"])
        if dirty:
            errors.append(
                "Repository has uncommitted artifacts after tests:\n    "
                + "\n    ".join(dirty)
            )

    # Allowed databases
    allowed_dbs = { (REPO_ROOT / path).resolve() for path in policy.get("allowed_databases", []) }
    for db_path in REPO_ROOT.rglob("*.db"):
        if db_path.resolve() not in allowed_dbs:
            errors.append(f"Unexpected database file: {db_path}")

    # Storage expectations
    storage_policy = policy.get("storage", {})
    canonical_root = REPO_ROOT / storage_policy.get("canonical_root", "storage")
    allowed_subdirs = set(storage_policy.get("allowed_subdirectories", []))
    test_subdirs = set(storage_policy.get("test_subdirectories", []))
    legacy_paths = [REPO_ROOT / entry for entry in storage_policy.get("legacy_paths", [])]

    if canonical_root.exists():
        for child in canonical_root.iterdir():
            if child.is_dir():
                name = child.name
                if name not in allowed_subdirs and name not in test_subdirs:
                    errors.append(f"Unexpected directory under storage/: {child}")

    for legacy in legacy_paths:
        if legacy.exists():
            errors.append(f"Legacy storage path should not exist: {legacy}")

    # Directories that must be empty/absent
    def has_files(path: Path) -> bool:
        return any(item for item in path.rglob("*") if item.is_file())

    for rel in policy.get("must_be_empty", []):
        target = REPO_ROOT / rel
        if target.exists() and has_files(target):
            errors.append(f"Directory must be empty but contains files: {target}")

    # Generic forbidden globs
    for pattern in policy.get("forbidden_globs", []):
        for match in REPO_ROOT.glob(pattern):
            if match.exists():
                errors.append(f"Forbidden path matched policy glob '{pattern}': {match}")

    # Log directory constraints
    for entry in policy.get("log_directories", []):
        path = REPO_ROOT / entry.get("path", "")
        if not path.exists():
            continue
        max_size_mb = entry.get("max_size_mb")
        if max_size_mb is not None:
            total_bytes = sum((child.stat().st_size for child in path.rglob("*") if child.is_file()))
            size_mb = total_bytes / (1024 * 1024)
            if size_mb > max_size_mb:
                errors.append(f"Directory '{path}' exceeds size limit ({size_mb:.1f} MB > {max_size_mb} MB)")
        max_entries = entry.get("max_entry_count")
        if max_entries is not None and path.is_dir():
            entries = [child for child in path.iterdir() if child.is_dir()]
            if len(entries) > max_entries:
                errors.append(f"Directory '{path}' has {len(entries)} entries (limit {max_entries}); archive or prune.")

    if errors:
        fail(errors)

    print(f"Repository hygiene check passed (policy v{policy_version}).")


if __name__ == "__main__":
    main()
