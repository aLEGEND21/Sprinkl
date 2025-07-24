"""
Logging configuration for the Food Recommendation API.

This module provides centralized logging configuration that can be imported
and used across the application. It supports both development and production
environments with appropriate formatters and handlers.
"""

import logging
import os
import sys
from typing import Optional


class ColorFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages in development."""

    COLORS = {
        logging.DEBUG: "\033[37m",  # White
        logging.INFO: "\033[94m",  # Blue
        logging.WARNING: "\033[93m",  # Yellow
        logging.ERROR: "\033[91m",  # Red
        logging.CRITICAL: "\033[1;91m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record):
        """Format the log record with color if supported."""
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record):
        """Format the log record as JSON."""
        import json
        from datetime import datetime

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry)


def setup_logging(
    level: str = "INFO",
    environment: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Set up logging configuration for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment name ('development' or 'production')
        log_file: Optional file path for file logging
    """
    # Get configuration from environment if not provided
    environment = environment or os.getenv("ENV", "development")

    # Validate log level
    try:
        log_level = getattr(logging, level)
    except AttributeError:
        print(f"Invalid log level: {level}. Using INFO.", file=sys.stderr)
        log_level = logging.INFO

    # Remove existing handlers to avoid duplicates
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    if environment == "development":
        console_handler.setFormatter(
            ColorFormatter(
                "%(levelname)s - %(asctime)s [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    else:
        console_handler.setFormatter(JSONFormatter())
    handlers.append(console_handler)

    # File handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            handlers.append(file_handler)
        except Exception as e:
            print(
                f"Warning: Could not create file handler for {log_file}: {e}",
                file=sys.stderr,
            )

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

    # Set specific levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
