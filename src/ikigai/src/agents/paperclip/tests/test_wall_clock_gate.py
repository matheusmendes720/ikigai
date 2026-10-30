"""Paperclip — WallClockGate unit tests (M175-paperclip-wall-clock-gate).

Five focused tests covering the wall-clock auto-throttle gate's contract:

* ``test_wall_clock_gate_allows_when_no_start_time`` — ``task_started_at=None``
  (or empty) → ``allowed=True`` (fail-open for older clients / replayed
  checkpoints).
* ``test_wall_clock_gate_allows_under_threshold`` — start=now-30min,
  threshold=3600 → ``allowed=True``.
* ``test_wall_clock_gate_blocks_over_threshold`` — start=now-2h,
  threshold=3600 → ``allowed=False``, reason contains ``"exceeds"``.
* ``test_wall_clock_gate_handles_malformed_iso`` — start="not-an-iso-string"
  → ``allowed=True`` (fail-open).
* ``test_wall_clock_gate_threshold_from_env`` —
  ``monkeypatch.setenv("PAPERCLIP_WALL_CLOCK_THRESHOLD_S", "1800")`` →
  threshold reflects env; 45min elapsed → blocked.

Tests use explicit ``now_iso`` for time-determinism (avoids
``datetime.now()`` which is non-deterministic across test runs).
``monkeypatch.setenv`` is used for the env-override test, per project
convention.

Companion to ``policy.py`` and the wire-up in ``nodes/implement.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from src.ikigai.src.agents.paperclip.policy import (
    DEFAULT_THRESHOLD_S,
    ENV_WALL_CLOCK_THRESHOLD,
    WallClockGate,
)


def _now_iso() -> str:
    """Return a stable, round-to-second ISO 8601 UTC timestamp for tests.

    Sub-second precision is intentionally avoided so that
    ``start + threshold`` comparisons don't drift across slow test runs.
    """
    now = datetime.now(UTC).replace(microsecond=0)
    return now.isoformat()


def test_wall_clock_gate_allows_when_no_start_time() -> None:
    """When ``task_started_at`` is None or empty, the gate is open (fail-open).

    Rationale: older callers (pre-M175) and replayed checkpoints may not
    carry the timestamp. Breaking the Paperclip graph because a field is
    missing is the wrong default — same invariant as ``CostGate`` on
    missing cost data (M173).
    """
    gate_none = WallClockGate(task_started_at=None, now_iso=_now_iso())
    allowed_none, reason_none = gate_none.check()
    assert allowed_none is True, f"expected fail-open on None, got reason: {reason_none}"
    assert "no start time" in reason_none.lower()

    gate_empty = WallClockGate(task_started_at="", now_iso=_now_iso())
    allowed_empty, reason_empty = gate_empty.check()
    assert allowed_empty is True, f"expected fail-open on empty string, got reason: {reason_empty}"
    assert "no start time" in reason_empty.lower()


def test_wall_clock_gate_allows_under_threshold() -> None:
    """A task that started 30min ago with default 3600s threshold is allowed."""
    now = datetime.now(UTC).replace(microsecond=0)
    started = (now - timedelta(minutes=30)).isoformat()

    gate = WallClockGate(task_started_at=started, now_iso=now.isoformat())
    allowed, reason = gate.check()

    assert allowed is True, f"expected under-threshold allowance, got reason: {reason}"
    assert "under" in reason.lower()
    assert "30.0" in reason or "1800.0" in reason  # 30 min = 1800s


def test_wall_clock_gate_blocks_over_threshold() -> None:
    """A task that started 2h ago with default 3600s threshold is blocked.

    The reason string MUST contain the word ``"exceeds"`` so downstream
    code (TUI, log scrapers) can pattern-match on it. The reason also
    echoes elapsed + threshold values.
    """
    now = datetime.now(UTC).replace(microsecond=0)
    started = (now - timedelta(hours=2)).isoformat()  # 7200s ago

    gate = WallClockGate(task_started_at=started, now_iso=now.isoformat())
    allowed, reason = gate.check()

    assert allowed is False, f"expected over-threshold block, got reason: {reason}"
    assert "exceeds" in reason, f"reason should contain 'exceeds', got: {reason}"
    assert "7200" in reason, f"reason should echo elapsed (7200), got: {reason}"
    assert "3600" in reason, f"reason should echo threshold (3600), got: {reason}"


def test_wall_clock_gate_handles_malformed_iso() -> None:
    """Garbage in ``task_started_at`` is treated as fail-open (allowed=True).

    Rationale: ISO 8601 parsing failures must not break the graph. This
    matches the test_cost_gate_handles_malformed_json invariant for
    malformed cost data.
    """
    gate = WallClockGate(task_started_at="not-an-iso-string", now_iso=_now_iso())
    allowed, reason = gate.check()

    assert allowed is True, f"expected fail-open on malformed ISO, got reason: {reason}"
    assert "malformed" in reason.lower() or "allowing" in reason.lower()


def test_wall_clock_gate_threshold_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """``PAPERCLIP_WALL_CLOCK_THRESHOLD_S`` env var overrides the default 3600s.

    Setting it to ``"1800"`` (30min) should bump the gate's ``threshold_seconds``
    to ``1800``. The fixture starts the task 45min ago (2700s) — over the new
    threshold so the gate is closed; with the default 3600s threshold it would
    be open. This proves the env var was actually consulted.
    """
    now = datetime.now(UTC).replace(microsecond=0)
    started = (now - timedelta(minutes=45)).isoformat()  # 2700s ago

    monkeypatch.setenv(ENV_WALL_CLOCK_THRESHOLD, "1800")
    gate = WallClockGate(task_started_at=started, now_iso=now.isoformat())

    # The env value is reflected in the instance attribute.
    assert gate.threshold_seconds == 1800, (
        f"expected threshold_seconds=1800 from env, got {gate.threshold_seconds}"
    )
    assert gate.threshold_seconds != DEFAULT_THRESHOLD_S

    # And the check respects it: 2700s elapsed >= 1800s threshold → blocked.
    allowed, reason = gate.check()
    assert allowed is False, "expected block at 2700s with 1800s threshold"
    assert "exceeds" in reason
