"""Structured logging configuration."""
import logging
import sys
from pathlib import Path
import structlog


def setup_logging(log_level: str = "INFO", log_dir: Path = None) -> None:
    """
    Configure structured logging with both console and file output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (optional)
    """
    # Ensure log level is valid
    log_level = log_level.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Create handlers list
    handlers = [logging.StreamHandler(sys.stdout)]

    # Add file handler if log directory specified
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
        handlers.append(logging.FileHandler(log_file))

    # Configure standard logging without stream parameter
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        handlers=handlers,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
