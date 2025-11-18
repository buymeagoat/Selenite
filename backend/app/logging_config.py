"""Structured logging configuration for the application."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

from app.config import settings


def setup_logging() -> None:
    """Configure structured logging with rotation and appropriate levels."""

    # Create logs directory if it doesn't exist
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)

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
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG" if settings.is_development else "INFO",
                "formatter": "detailed" if settings.is_development else "simple",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": str(log_dir / "selenite.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(log_dir / "error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "app": {
                "level": settings.log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING" if settings.is_production else "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console", "file", "error_file"],
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
