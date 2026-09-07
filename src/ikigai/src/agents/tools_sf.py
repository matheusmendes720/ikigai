"""Solverforge Calendar fork tools (Rust CLI subprocess wrapper).

Per user scope (ADR-013): 2 fork tools that wrap solverforge-calendar-cli
(subprocess-based). Both raise ConnectionError on non-zero exit (which
the reliability decorators retry); FileNotFoundError is caught and
returned as a friendly message (binary may not be installed locally).

Exposes (re-exported by tools.py):
- ``solverforge_list_events`` — list upcoming events (default 7 days)
- ``solverforge_create_event`` — create event (title + date + time)

Companion modules:
- ``tools_tuiboard`` — SolidJS MCP fork (4 tools)
- ``tools_taskdog`` — taskdog CLI fork (4 tools)
- ``tools`` — IKIGAI_TOOLS list (12 entries) + re-exports

Architectural reference:
- ADR-013 — planner-only; these are the 10 external data tools (12 total
  with 2 vault reads added in B7.3)
- W3.6 — side-effect tools gated by invoke_skill() outputs check

Drift invariants enforced:
- test_canonical_scope :: test_ikigai_tools_count_is_12
  (counted via AST on tools.py)
"""

from __future__ import annotations

import os
import subprocess

from langchain_core.tools import tool

from .reliability import (
    CircuitBreakerConfig,
    RetryConfig,
    circuit_breaker,
    invalidate_session_cache,
    retry_with_backoff,
)

# Solverforge CLI path (configurable via env var)
_SOLVERFORGE_CLI = os.environ.get("SOLVERFORGE_CLI", "solverforge-calendar-cli.exe")

# Retry config for solverforge
_solverforge_retry_config = RetryConfig(
    max_attempts=3,
    initial_backoff_s=0.5,
    max_backoff_s=8.0,
    backoff_multiplier=2.0,
    jitter=True,
)

_solverforge_cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    reset_timeout_s=30.0,
)


@tool
@circuit_breaker("solverforge", _solverforge_cb_config)
@retry_with_backoff(
    name="solverforge_list_events",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_solverforge_retry_config,
)
def solverforge_list_events(days: int = 7) -> str:
    """List upcoming calendar events from solverforge.

    Args:
        days: Number of days to look ahead. Defaults to 7.

    Returns:
        Formatted list of upcoming events or error message.
    """
    try:
        result = subprocess.run(
            [_SOLVERFORGE_CLI, "events", "list", "--days", str(days)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"solverforge error: {result.stderr}")
        return result.stdout
    except FileNotFoundError as e:
        # Binary missing — return friendly message instead of crashing agent.invoke().
        return f"⚠️ solverforge unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("solverforge")
        raise
    except Exception as e:
        return f"⚠️ solverforge unavailable: {e}"


@tool
@circuit_breaker("solverforge", _solverforge_cb_config)
@retry_with_backoff(
    name="solverforge_create_event",
    retryable_exceptions=(subprocess.TimeoutExpired, FileNotFoundError, ConnectionError, OSError),
    config=_solverforge_retry_config,
)
def solverforge_create_event(title: str, date: str, time: str = "09:00") -> str:
    """Create a calendar event in solverforge.

    Args:
        title: Event title.
        date: Event date (YYYY-MM-DD).
        time: Event time (HH:MM). Defaults to "09:00".

    Returns:
        Confirmation message or error.
    """
    try:
        result = subprocess.run(
            [
                _SOLVERFORGE_CLI,
                "events",
                "create",
                "--title",
                title,
                "--date",
                date,
                "--time",
                time,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConnectionError(f"solverforge error: {result.stderr}")
        return result.stdout
    except FileNotFoundError as e:
        # Binary missing — return friendly message instead of crashing agent.invoke().
        return f"⚠️ solverforge unavailable (binary not found): {e}"
    except (subprocess.TimeoutExpired, ConnectionError, OSError):
        invalidate_session_cache("solverforge")
        raise
    except Exception as e:
        return f"⚠️ solverforge unavailable: {e}"


__all__ = [
    "solverforge_create_event",
    "solverforge_list_events",
]
