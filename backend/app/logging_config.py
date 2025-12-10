"""Structured logging configuration for the application."""

import logging
import logging.config
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings


def setup_logging() -> None:
    """Configure structured logging with rotation and appropriate levels."""

    # Create logs directory if it doesn't exist
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)

    # Determine handler sets based on environment
    extra_handlers: list[str] = []
    # File logging is required for diagnosis; only disable during automated tests.
    disable_file_handlers = settings.is_testing
    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG" if settings.is_development else "INFO",
            "formatter": "detailed" if settings.is_development else "simple",
            "stream": sys.stdout,
        },
    }

    if not disable_file_handlers:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        info_log = log_dir / f"selenite-{timestamp}.log"
        error_log = log_dir / f"error-{timestamp}.log"
        handlers.update(
            {
                "file": {
                    "class": "logging.FileHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "filename": str(info_log),
                    "encoding": "utf-8",
                },
                "error_file": {
                    "class": "logging.FileHandler",
                    "level": "ERROR",
                    "formatter": "detailed",
                    "filename": str(error_log),
                    "encoding": "utf-8",
                },
            }
        )
        extra_handlers = ["file", "error_file"]

    handler_names = ["console"] + extra_handlers

    # Base logging configuration
    log_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "%(levelname)s - %(message)s",
            },
            "json": (
                {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(filename)s %(lineno)d %(message)s",
                }
                if settings.is_production
                else {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                }
            ),
        },
        "handlers": handlers,
        "loggers": {
            "app": {
                "level": settings.log_level,
                "handlers": handler_names,
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": handler_names,
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": handler_names,
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING" if (settings.is_production or settings.is_testing) else "INFO",
                "handlers": handler_names,
                "propagate": False,
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": handler_names,
        },
    }

    # Apply logging configuration
    logging.config.dictConfig(log_config)

    # Get logger and log startup message
    logger = logging.getLogger("app")
    logger.info(
        f"Logging initialized - Environment: {settings.environment}, "
        f"Level: {settings.log_level}"
    )

    if settings.is_development:
        logger.debug("Running in development mode with verbose logging")
    elif settings.is_production:
        logger.info("Running in production mode")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"app.{name}")
