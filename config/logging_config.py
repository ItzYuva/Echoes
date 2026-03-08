"""
Echoes Data Pipeline — Logging Configuration

Structured logging using Python's logging module with rich formatting.
Provides coloured console output during development and structured output
that can be piped to JSON for production.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

# ──────────────────────────────────────────────
# Module-level console for shared use
# ──────────────────────────────────────────────
console = Console(stderr=True)

# ──────────────────────────────────────────────
# Log directory
# ──────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
) -> None:
    """Configure the root logger with rich console output and optional file logging.

    Args:
        level: The minimum log level to capture (default: INFO).
        log_file: Optional filename (relative to logs/) for persistent log output.
    """
    # Clear any existing handlers
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    # ── Rich console handler ──
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        markup=True,
    )
    rich_handler.setLevel(level)
    rich_fmt = logging.Formatter("%(message)s", datefmt="[%X]")
    rich_handler.setFormatter(rich_fmt)
    root.addHandler(rich_handler)

    # ── File handler (optional) ──
    if log_file:
        file_path = LOG_DIR / log_file
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_fmt = logging.Formatter(
            "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        root.addHandler(file_handler)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "prawcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for use in a module.

    Args:
        name: Typically pass ``__name__`` from the calling module.

    Returns:
        logging.Logger: Configured logger instance.
    """
    return logging.getLogger(name)
