"""Database seeding script."""

import asyncio
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.utils.security import hash_password
from sqlalchemy import select


async def seed_database():
    """Seed the database with initial data."""
    print("Seeding database...")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if admin user already exists
        result = await db.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()

        if admin_user:
            print("Admin user already exists.")
        else:
            # Create admin user
            admin_user = User(
                username="admin",
                email="admin@selenite.local",
                hashed_password=hash_password("changeme"),
            )
            db.add(admin_user)
            await db.commit()
            print("Created admin user (username: admin, password: changeme)")

    print("Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
