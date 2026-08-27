"""Unit tests for :mod:`operational.ui.logging_setup`.

The logging module is a "black box" of the CLI: a file-based logger
that records every event to ``logs/crash_report.log`` so the developer
can recover a full traceback if the user hits an unrecoverable error.

The contract being tested:

1. The module-level ``logger`` is a real :class:`logging.Logger` named
   ``"app_engine"`` — code can ``from operational.ui.logging_setup
   import logger`` and use it directly.
2. :func:`configure_logging` is **idempotent**: re-running it does not
   duplicate handlers, and it always returns the same global logger.
3. :func:`log_event` produces an ``INFO``-level line carrying the
   mensagem and the metadata as a dict repr.
4. :func:`log_error` with ``exc=`` writes the full traceback; without
   ``exc=`` it writes a single ``ERROR``-level line.
5. If the log dir cannot be created, the logger silently degrades
   (no exception leaks to the caller).

Tests follow strict AAA (Arrange / Act / Assert).

Windows file-handle note
------------------------
``logging.FileHandler`` opens the log file and holds the OS handle
open until ``close()`` is called or the handler is dropped. On
``tmp_path`` cleanup pytest would otherwise hit
``PermissionError: file in use``. The ``_release_file_handlers``
autouse fixture closes every handler after each test, before
``tmp_path`` is removed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterator

import pytest

from operational.ui.logging_setup import (
    LOG_DIR,
    LOG_FILE,
    configure_logging,
    log_error,
    log_event,
    logger,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_log_dir(tmp_path: Path) -> Path:
    """Return a per-test log directory that does not yet exist on disk."""
    log_dir = tmp_path / "logs"
    # Sanity: tmp_path is unique per test, so the subdir must not pre-exist.
    assert not log_dir.exists()
    return log_dir


@pytest.fixture(autouse=True)
def _release_file_handlers() -> Iterator[None]:
    """Close + drop every handler on the global logger after each test.

    Critical on Windows: ``FileHandler`` keeps the log file locked; if we
    leave the handler attached, ``tmp_path`` cleanup raises PermissionError
    and the whole session explodes.

    The fixture also restores ``logger.level`` to ``logging.NOTSET`` so
    state never leaks between tests.
    """
    try:
        yield
    finally:
        for handler in list(logger.handlers):
            try:
                handler.close()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)


# ===========================================================================
# Module-level logger
# ===========================================================================


def test_logger_is_a_real_logging_logger_instance() -> None:
    """``logger`` is a stdlib :class:`logging.Logger`, not a duck-typed stand-in."""
    # Arrange / Act / Assert
    assert isinstance(logger, logging.Logger)


def test_logger_has_expected_name_app_engine() -> None:
    """Logger name is the well-known ``app_engine`` so external config can target it."""
    # Arrange / Act / Assert
    assert logger.name == "app_engine"


# ===========================================================================
# LOG_DIR / LOG_FILE constants
# ===========================================================================


def test_log_dir_default_is_string_logs() -> None:
    """``LOG_DIR`` is the string ``"logs"`` (relative to the project root)."""
    # Arrange / Act / Assert
    assert LOG_DIR == "logs"
    assert isinstance(LOG_DIR, str)


def test_log_file_default_joins_log_dir_and_filename() -> None:
    """``LOG_FILE`` is ``<LOG_DIR>/crash_report.log``."""
    # Arrange / Act / Assert
    assert LOG_FILE == os.path.join(LOG_DIR, "crash_report.log")
    assert LOG_FILE.endswith("crash_report.log")


# ===========================================================================
# configure_logging
# ===========================================================================


def test_configure_logging_returns_the_global_logger(fresh_log_dir: Path) -> None:
    """``configure_logging`` always returns the same module-level logger."""
    # Arrange
    log_dir = str(fresh_log_dir)

    # Act
    log = configure_logging(log_dir=log_dir)

    # Assert
    assert log is logger


def test_configure_logging_creates_log_dir_if_missing(fresh_log_dir: Path) -> None:
    """If ``log_dir`` does not exist, it is created on disk."""
    # Arrange
    log_dir = str(fresh_log_dir)
    assert not fresh_log_dir.exists()

    # Act
    configure_logging(log_dir=log_dir)

    # Assert
    assert fresh_log_dir.exists()
    assert fresh_log_dir.is_dir()


def test_configure_logging_creates_log_file(fresh_log_dir: Path) -> None:
    """After ``configure_logging`` the ``crash_report.log`` file is present."""
    # Arrange
    log_dir = str(fresh_log_dir)
    expected = fresh_log_dir / "crash_report.log"

    # Act
    configure_logging(log_dir=log_dir)

    # Assert
    assert expected.exists()
    assert expected.is_file()


def test_configure_logging_is_idempotent_no_handler_duplication(
    fresh_log_dir: Path,
) -> None:
    """Calling ``configure_logging`` twice keeps the handler count constant."""
    # Arrange
    log_dir = str(fresh_log_dir)

    # Act
    log1 = configure_logging(log_dir=log_dir)
    n1 = len(log1.handlers)
    log2 = configure_logging(log_dir=log_dir)
    n2 = len(log2.handlers)

    # Assert
    assert n1 == n2
    assert n1 >= 1  # at least one FileHandler attached


# ===========================================================================
# log_event
# ===========================================================================


def test_log_event_writes_info_line_with_mensagem(fresh_log_dir: Path) -> None:
    """``log_event(msg)`` produces an ``INFO``-level line containing ``msg``."""
    # Arrange
    configure_logging(log_dir=str(fresh_log_dir))
    mensagem = "user clicked save"

    # Act
    log_event(mensagem)
    for h in logger.handlers:
        h.flush()

    # Assert
    contents = (fresh_log_dir / "crash_report.log").read_text(encoding="utf-8")
    assert mensagem in contents
    assert "INFO" in contents


def test_log_event_writes_metadata_as_dict_repr(fresh_log_dir: Path) -> None:
    """Metadata kwargs end up in the line as a Python dict repr."""
    # Arrange
    configure_logging(log_dir=str(fresh_log_dir))

    # Act
    log_event("test event", key="value", count=42)
    for h in logger.handlers:
        h.flush()

    # Assert
    contents = (fresh_log_dir / "crash_report.log").read_text(encoding="utf-8")
    assert "test event" in contents
    assert "INFO" in contents
    # The format is "<msg> | {'key': 'value', 'count': 42}"
    assert "'key': 'value'" in contents
    assert "'count': 42" in contents


# ===========================================================================
# log_error
# ===========================================================================


def test_log_error_captures_full_traceback(fresh_log_dir: Path) -> None:
    """``log_error(msg, exc=e)`` writes the traceback plus the error level."""
    # Arrange
    log = configure_logging(log_dir=str(fresh_log_dir))

    # Act
    try:
        1 / 0
    except ZeroDivisionError as exc:
        log_error("division failed", exc=exc)
    for h in log.handlers:
        h.flush()

    # Assert
    contents = (fresh_log_dir / "crash_report.log").read_text(encoding="utf-8")
    assert "division failed" in contents
    assert "ZeroDivisionError" in contents
    assert "division by zero" in contents
    # Either the level name or the traceback header must appear.
    assert "ERROR" in contents
    assert "Traceback" in contents


def test_log_error_without_exc_still_writes_error_level(fresh_log_dir: Path) -> None:
    """``log_error(msg)`` without ``exc`` writes a single ``ERROR`` line."""
    # Arrange
    log = configure_logging(log_dir=str(fresh_log_dir))

    # Act
    log_error("non-fatal warning")
    for h in log.handlers:
        h.flush()

    # Assert
    contents = (fresh_log_dir / "crash_report.log").read_text(encoding="utf-8")
    assert "non-fatal warning" in contents
    assert "ERROR" in contents
    # No traceback was requested — there should be no Traceback block.
    assert "Traceback" not in contents


# ===========================================================================
# Robustness
# ===========================================================================


def test_configure_logging_silently_degrades_on_unwritable_path() -> None:
    """If the log dir is invalid, ``configure_logging`` returns the logger anyway."""
    # Arrange
    bad_path = r"Z:\nonexistent:?<>|" + "*"  # illegal Windows path chars

    # Act — must not raise (caller is the UI and cannot recover)
    log = configure_logging(log_dir=bad_path)

    # Assert
    assert log is logger
    # Either the handler is missing (silent degradation) or the path was
    # somehow writable — both are acceptable as long as the call returned.
    assert isinstance(log.handlers, list)
