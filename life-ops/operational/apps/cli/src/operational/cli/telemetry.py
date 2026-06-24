"""Telemetry layer for the PAV CLI — structured logging, request IDs, and spans.

Design
======
Every CLI invocation gets a **request ID** (UUID4 short-form) that propagates
through all log messages for that call.  Output is always structured JSON
(when --json-log) or human-readable Rich text (default) — never mixed.

Three severity levels
--------------------
  TRACE  — entry / exit of every command handler (hideable with --quiet)
  INFO   — business-level events: entity created, query returned N rows, etc.
  ERROR  — caught exceptions with full traceback (always written to log)

Log destination hierarchy
------------------------
  1. --log-file <path>   → append to rotating JSON log (default: None / disabled)
  2. STDERR              → human-readable lines when not --json-log
  3. STDOUT              → never used for logs (only for command output)

Each log record
--------------
::

    {
        "timestamp": "2026-06-23T14:07:02.123Z",
        "level": "INFO",
        "request_id": "a1b2c3d4",
        "command": "pav habit create",
        "event": "entity.created",
        "entity_type": "habit",
        "entity_id": "hab_meditar_01",
        "duration_ms": 12.4,
        "extra": { ... },
        "error": null
    }

Usage in a command
------------------
::

    from operational.cli.telemetry import get_logger, trace_command

    log = get_logger("habit_cmd")

    def create(...):
        with trace_command(log, "habit.create", entity_type="habit"):
            # your logic
            log.info("entity.created", entity_id=habit.id, extra={"category": cat})
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Generator
from functools import wraps

import structlog

# ─── Log levels ─────────────────────────────────────────────────────────────────

class Level(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO  = "INFO"
    WARN  = "WARN"
    ERROR = "ERROR"
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

# Module-level state
_log_level: Level = Level.INFO
_json_log:  bool   = False
_log_file:  Path | None = None
_quiet:     bool   = False

# Map Level enum → Python stdlib int for logger.setLevel()
_LEVEL_TO_INT: dict[Level, int] = {
    Level.TRACE: 5,
    Level.DEBUG: 10,
    Level.INFO:  20,
}

# The structlog logger (configured once)
_logger: structlog.stdlib.BoundLogger | None = None


# ─── Internal helpers ────────────────────────────────────────────────────────────

def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _request_id() -> str:
    """Short 8-char hex request ID for display."""
    return uuid.uuid4().hex[:8]


# ─── Logger bootstrap ────────────────────────────────────────────────────────────

def _configure_logger() -> None:
    """Build the structlog processor chain and attach handlers."""
    global _logger

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if _json_log:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
                pad_level=True,
            )
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _logger = structlog.get_logger("pav")


def configure(
    level: Level = Level.INFO,
    *,
    json_log:  bool = False,
    log_file:  str | Path | None = None,
    quiet:     bool = False,
) -> None:
    """Call once at CLI startup (before any command runs)."""
    global _log_level, _json_log, _log_file, _quiet
    _log_level = level
    _json_log  = json_log
    _log_file  = Path(log_file) if log_file else None
    _quiet     = quiet

    _configure_logger()

    # Route structlog through Python stdlib logging so we can attach handlers.
    # All PAV logs land on the 'pav' logger name.
    pav_logger = logging.getLogger("pav")
    pav_logger.setLevel(_LEVEL_TO_INT[_log_level])
    pav_logger.handlers.clear()

    # stderr for interactive use
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(_LEVEL_TO_INT[_log_level])
    pav_logger.addHandler(handler)

    if _log_file:
        _log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(_log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        file_handler.setLevel(_LEVEL_TO_INT[_log_level])
        pav_logger.addHandler(file_handler)

    _info("log_configured", extra={"level": _log_level.value, "json": _json_log, "log_file": str(_log_file or "")})


# ─── Public API ─────────────────────────────────────────────────────────────────

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound logger that includes the 'command' context."""
    if _logger is None:
        _configure_logger()
    base = _logger.bind() if _logger else structlog.get_logger(name)
    return base.bind(component=name)


def _info(event: str, **kwargs: Any) -> None:
    if _logger and _log_level in (Level.DEBUG, Level.INFO):
        _logger.info(event, **kwargs)


def _error(event: str, **kwargs: Any) -> None:
    if _logger:
        _logger.error(event, **kwargs)


# ─── Per-invocation context ──────────────────────────────────────────────────────

class InvocationContext:
    """Holds request-scoped telemetry data, passed through `trace_command`."""

    __slots__ = ("request_id", "command", "started_at", "extra")

    def __init__(self, command: str, request_id: str | None = None):
        self.request_id = request_id or _request_id()
        self.command    = command
        self.started_at = time.monotonic()
        self.extra: dict[str, Any] = {}

    def emit(self, level: Level, event: str, **kwargs: Any) -> None:
        """Write a structured log event with common fields."""
        if _quiet and level == Level.TRACE:
            return
        if _logger is None:
            return
        elapsed_ms = (time.monotonic() - self.started_at) * 1000
        # Build flat record
        record: dict[str, Any] = {
            "timestamp":   _timestamp(),
            "level":       level.value,
            "request_id":  self.request_id,
            "command":     self.command,
            "event":       event,
            "duration_ms": round(elapsed_ms, 2),
        }
        record.update(self.extra)
        record.update(kwargs)
        # Ensure error key always exists
        if "error" not in record:
            record["error"] = None

        if level == Level.ERROR:
            _logger.error(**record)
        elif level == Level.WARN:
            _logger.warning(**record)
        elif level == Level.TRACE and not _quiet:
            _logger.debug(**record)
        else:
            _logger.info(**record)

    def trace(self, event: str, **kwargs: Any) -> None:
        self.emit(Level.TRACE, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self.emit(Level.INFO, event, **kwargs)

    def warn(self, event: str, **kwargs: Any) -> None:
        self.emit(Level.WARN, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self.emit(Level.ERROR, event, **kwargs)


@contextmanager
def trace_command(
    log:  structlog.stdlib.BoundLogger,
    event: str,
    **initial_kwargs: Any,
) -> Generator[InvocationContext, None, None]:
    """Context manager: emit entry/exit TRACE events and capture duration.

    Usage::

        with trace_command(get_logger("my_cmd"), "my_cmd.run") as ctx:
            ctx.info("entity.created", entity_id="hab_01")
            # ... do work ...
    """
    command = initial_kwargs.get("command", event)
    ctx = InvocationContext(command=command)
    ctx.extra.update(initial_kwargs)

    ctx.trace("command.started")
    try:
        yield ctx
        ctx.trace("command.completed")
    except Exception as exc:
        ctx.error(
            "command.failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


# ─── Decorator for Typer commands ──────────────────────────────────────────────

def logged_command(
    command_name: str,
    *,
    entity_type: str | None = None,
):
    """Decorator that wraps a Typer command with TRACE entry/exit telemetry.

    Applied at the function level inside each command module — keeps each
    module readable and self-contained.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = InvocationContext(command=f"pav {command_name}")
            ctx.extra["entity_type"] = entity_type
            ctx.trace("command.started")
            try:
                result = fn(*args, **kwargs)
                ctx.trace("command.completed")
                return result
            except Exception as exc:
                ctx.error(
                    "command.failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    exc_info=exc,
                )
                raise
        return wrapper
    return decorator
