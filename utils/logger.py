"""Structured logging utilities with Rich console output."""
import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

_console = Console(stderr=True)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure root logger with Rich handler and optional file handler.

    Args:
        log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
        log_file: Optional path to write log output to a file.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [
        RichHandler(
            console=_console,
            rich_tracebacks=True,
            markup=True,
            show_path=False,
        )
    ]

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger instance.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` configured through :func:`setup_logging`.
    """
    return logging.getLogger(name)
