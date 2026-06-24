"""Black-box logging infrastructure.

This module:
- Configures a file-based logger (logs/crash_report.log) that captures
  the FULL traceback for any unhandled exception.
- Exposes a simple ``logger`` global that controllers can use to record
  info, warnings, and exceptions.
- The Rich console (stdout) is left clean for user-facing output.

Per the spec: "Caixa-preta de avião" — the user sees a beautiful Rich
error panel, the developer gets the full traceback saved to disk.
"""
from __future__ import annotations

import logging
import os

LOG_DIR: str = "logs"
LOG_FILE: str = os.path.join(LOG_DIR, "crash_report.log")

# Module-level logger singleton
logger: logging.Logger = logging.getLogger("app_engine")


def configure_logging(log_dir: str = LOG_DIR) -> logging.Logger:
    """Set up the file-based black-box logger.

    Idempotent: calling multiple times will not duplicate handlers.
    """
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError:
            pass  # If we can't create the log dir, we'll just log to nothing

    logger.setLevel(logging.DEBUG)
    # Avoid duplicate handlers
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        file_handler = logging.FileHandler(
            os.path.join(log_dir, "crash_report.log"),
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except OSError:
        # Cannot open log file — silently degrade (logging is best-effort)
        pass

    return logger


def log_event(mensagem: str, **metadados: object) -> None:
    """Convenience: log an info event with structured metadata."""
    msg = f"{mensagem} | {metadados}" if metadados else mensagem
    logger.info(msg)


def log_error(mensagem: str, *, exc: BaseException | None = None) -> None:
    """Log an error event. If ``exc`` is given, log the full traceback."""
    if exc is not None:
        logger.exception(f"{mensagem} | exc={type(exc).__name__}: {exc}")
    else:
        logger.error(mensagem)


# Auto-configure on import so loggers are always available
configure_logging()


__all__ = [
    "LOG_DIR",
    "LOG_FILE",
    "configure_logging",
    "log_error",
    "log_event",
    "logger",
]
