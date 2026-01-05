"""
Reset (or set) the password for a user (default: admin) in the local database.

Usage:
  python scripts/reset_admin_password.py --password NEWPASS [--username admin]

Notes:
- Idempotent: updates existing user or creates it if missing.
- Intended for local/dev recovery; does not run automatically.
"""

from __future__ import annotations


import os
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

import argparse
import asyncio
import sys

# Ensure backend is on sys.path so app.* imports work when run from anywhere
ROOT = Path(__file__).resolve().parent.parent
backend_dir = ROOT / "backend"
if backend_dir.exists() and str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.utils.security import hash_password
from sqlalchemy import select


async def reset_password(username: str, password: str) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        admin_email = "admin@selenite.local" if username == "admin" else f"{username}@selenite.local"
        if user:
            user.hashed_password = hash_password(password)
            if username == "admin":
                user.email = admin_email
                user.is_admin = True
                user.is_disabled = False
                user.force_password_reset = False
            action = "Updated"
        else:
            user = User(
                username=username,
                email=admin_email,
                hashed_password=hash_password(password),
                is_admin=True if username == "admin" else False,
                is_disabled=False,
                force_password_reset=False,
            )
            db.add(user)
            action = "Created"

        await db.commit()
        print(f"{action} user '{username}' with new password.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset a user's password.")
    parser.add_argument(
        "--username",
        default="admin",
        help="Username to reset (default: admin)",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="New password to set",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(reset_password(args.username, args.password))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - simple CLI
        print(f"Reset failed: {exc}", file=sys.stderr)
        raise



