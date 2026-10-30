"""Paperclip — CostGate unit tests (M173-paperclip-cost-gate).

Five focused tests covering the auto-throttle gate's contract:

* ``test_cost_gate_allows_when_no_file`` — no ``data/cost-today.json`` →
  ``allowed=True`` (fail-open).
* ``test_cost_gate_allows_under_threshold`` — file shows ``$2.00``,
  threshold ``$5.00`` → ``allowed=True``.
* ``test_cost_gate_blocks_over_threshold`` — file shows ``$7.50``,
  threshold ``$5.00`` → ``allowed=False``, reason contains ``"exceeds"``.
* ``test_cost_gate_handles_malformed_json`` — file with garbage text →
  ``allowed=True`` (fail-open).
* ``test_cost_gate_threshold_from_env`` — ``monkeypatch.setenv(
  "PAPERCLIP_COST_THRESHOLD_USD", "10.00")`` → gate reflects env.

Tests use ``tmp_path`` + write a ``cost-today.json`` into it; the path
is injected via ``CostGate(cost_file=tmp_path/"cost-today.json")`` so the
real ``data/`` tree is not touched.

Companion to ``policy.py`` and the wire-up in ``nodes/implement.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.ikigai.src.agents.paperclip.policy import (
    DEFAULT_THRESHOLD_USD,
    ENV_THRESHOLD,
    CostGate,
)


def test_cost_gate_allows_when_no_file(tmp_path: Path) -> None:
    """When ``cost-today.json`` does not exist, the gate is open (fail-open).

    Rationale: the M7 cost-dashboard daemon may not be running in every
    env (CI, ephemeral containers, dev machines). Breaking the Paperclip
    graph because a sidecar service is offline is the wrong default.
    """
    cost_file = tmp_path / "cost-today.json"
    assert not cost_file.exists()  # sanity check on fixture

    gate = CostGate(cost_file=cost_file)
    allowed, reason = gate.check()

    assert allowed is True, f"expected fail-open when no file, got reason: {reason}"
    assert "not found" in reason.lower() or "no cost" in reason.lower()


def test_cost_gate_allows_under_threshold(tmp_path: Path) -> None:
    """A file reporting $2.00 with default $5.00 threshold is allowed."""
    cost_file = tmp_path / "cost-today.json"
    cost_file.write_text(
        json.dumps(
            {
                "total_usd": 2.00,
                "by_agent": {"claude": 1.50, "pi": 0.50},
            }
        ),
        encoding="utf-8",
    )

    gate = CostGate(cost_file=cost_file)
    allowed, reason = gate.check()

    assert allowed is True, f"expected under-threshold allowance, got reason: {reason}"
    # Reason should reflect the under-threshold state.
    assert "2.00" in reason or "under" in reason.lower()


def test_cost_gate_blocks_over_threshold(tmp_path: Path) -> None:
    """A file reporting $7.50 with default $5.00 threshold is blocked.

    The reason string MUST contain the word ``"exceeds"`` so downstream
    code (TUI, log scrapers) can pattern-match on it.
    """
    cost_file = tmp_path / "cost-today.json"
    cost_file.write_text(
        json.dumps(
            {
                "total_usd": 7.50,
                "by_agent": {"claude": 5.50, "pi": 2.00},
            }
        ),
        encoding="utf-8",
    )

    gate = CostGate(cost_file=cost_file)
    allowed, reason = gate.check()

    assert allowed is False, f"expected over-threshold block, got reason: {reason}"
    assert "exceeds" in reason, f"reason should contain 'exceeds', got: {reason}"
    assert "7.50" in reason, f"reason should echo the total, got: {reason}"
    assert "5.00" in reason, f"reason should echo the threshold, got: {reason}"


def test_cost_gate_handles_malformed_json(tmp_path: Path) -> None:
    """A garbage file is treated as fail-open (allowed=True).

    The cost-dashboard daemon may write a partial file if interrupted;
    we should not break the Paperclip graph because of a parse error.
    """
    cost_file = tmp_path / "cost-today.json"
    cost_file.write_text("not valid json {[(", encoding="utf-8")

    gate = CostGate(cost_file=cost_file)
    allowed, reason = gate.check()

    assert allowed is True, f"expected fail-open on malformed JSON, got reason: {reason}"
    assert "malformed" in reason.lower() or "allowing" in reason.lower()


def test_cost_gate_threshold_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``PAPERCLIP_COST_THRESHOLD_USD`` env var overrides the default $5.00.

    Setting it to ``"10.00"`` should bump the gate's ``threshold_usd``
    to ``10.0``. The fixture writes a $7.50 spend — under the new
    threshold so the gate is open; with the default threshold it would
    be closed. This proves the env var was actually consulted.
    """
    cost_file = tmp_path / "cost-today.json"
    cost_file.write_text(
        json.dumps({"total_usd": 7.50, "by_agent": {"claude": 7.50}}),
        encoding="utf-8",
    )

    monkeypatch.setenv(ENV_THRESHOLD, "10.00")
    gate = CostGate(cost_file=cost_file)

    # The env value is reflected in the instance attribute.
    assert gate.threshold_usd == 10.00, (
        f"expected threshold_usd=10.00 from env, got {gate.threshold_usd}"
    )
    assert gate.threshold_usd != DEFAULT_THRESHOLD_USD

    # And the check respects it: $7.50 < $10.00 → allowed.
    allowed, _ = gate.check()
    assert allowed is True, "expected allowance at $7.50 with $10.00 threshold"
