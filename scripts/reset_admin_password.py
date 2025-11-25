"""
Reset (or set) the password for a user (default: admin) in the local database.

Usage:
  python scripts/reset_admin_password.py --password NEWPASS [--username admin]

Notes:
- Idempotent: updates existing user or creates it if missing.
- Intended for local/dev recovery; does not run automatically.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

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

        if user:
            user.hashed_password = hash_password(password)
            action = "Updated"
        else:
            user = User(
                username=username,
                email=f"{username}@selenite.local",
                hashed_password=hash_password(password),
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
