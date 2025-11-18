"""Database migration utilities for application startup."""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger("app.migrations")


def get_alembic_config() -> Config:
    """Get Alembic configuration object.

    Returns:
        Configured Alembic Config instance
    """
    # Get path to alembic.ini (should be in backend root)
    alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(
            f"alembic.ini not found at {alembic_ini_path}. "
            "Run 'alembic init alembic' to initialize."
        )

    config = Config(str(alembic_ini_path))
    return config


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well.
    """
    from app.config import settings
    from app.database import Base
    from alembic import context

    context.configure(
        url=settings.database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def check_migration_status(engine: AsyncEngine) -> tuple[str, str]:
    """Check current database migration status.

    Args:
        engine: AsyncEngine instance

    Returns:
        Tuple of (current_revision, head_revision)
    """
    try:
        config = get_alembic_config()

        # Get current database revision
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.scalar_one_or_none()

        # Get head revision from migration files
        from alembic.script import ScriptDirectory

        script_dir = ScriptDirectory.from_config(config)
        head = script_dir.get_current_head()

        return (current or "none", head or "none")

    except Exception as e:
        logger.warning(f"Could not check migration status: {e}")
        return ("unknown", "unknown")


async def run_migrations(engine: AsyncEngine, auto: bool = False) -> None:
    """Run database migrations to latest version.

    Args:
        engine: AsyncEngine instance
        auto: If True, automatically upgrade without confirmation
    """
    try:
        config = get_alembic_config()

        # Check current status
        current, head = await check_migration_status(engine)

        if current == head:
            logger.info(f"Database is up to date (revision: {current})")
            return

        logger.info(f"Database migration needed: {current} -> {head}")

        if not auto:
            logger.warning("Auto-migration is disabled. Run 'alembic upgrade head' manually.")
            return

        # Run migrations using Alembic
        logger.info("Running database migrations...")
        command.upgrade(config, "head")
        logger.info("Database migrations completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


async def initialize_database(engine: AsyncEngine) -> None:
    """Initialize database schema if needed.

    This is useful for first-time setup or testing environments.

    Args:
        engine: AsyncEngine instance
    """
    from app.database import Base

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
