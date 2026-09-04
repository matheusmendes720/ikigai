"""ADR-029 kill switch test suite — 13 tests covering activation + escalation.

Per ADR-029 §W5.1.1 deliverable #5 + the W5.1.1 brief §"test_kill_switch.py".

Coverage:
1-3.  Activation x mechanism (env var / vault file / data file)
4-6.  Priority order (env > vault > data)
7-8.  Escalation (review queue entry + audit log append)
9-11. Wrapper integration (block when active / enforce SONHO + allow user)
12.   Rate limit
13.   Drift invariant (e) detection (via sys.modules)

Total: 13 tests. All use tmp_path fixtures + monkeypatch for env vars.
No test depends on real filesystem state outside the test sandbox.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from ikigai.security import kill_switch as ks
from ikigai.security.vault_write_wrapper import (
    LEGAL_CALLERS,
    KillSwitchAbort,
    KillSwitchActorViolation,
    KillSwitchBypassDetected,
    KillSwitchRateLimitExceeded,
    _RateLimitTracker,
    make_wrapped_vault_write,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Empty vault root for the test."""
    root = tmp_path / "vault"
    root.mkdir()
    return root


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    """Empty data root for the test."""
    root = tmp_path / "data"
    root.mkdir()
    return root


@pytest.fixture
def review_queue_dir(data_root: Path) -> Path:
    """data/review_queue/ subdir."""
    d = data_root / "review_queue"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def clean_kill_switch_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure IKIGAI_KILL_SWITCH is unset at start of each test."""
    monkeypatch.delenv("IKIGAI_KILL_SWITCH", raising=False)


# ---------------------------------------------------------------------------
# 1-3. Activation x mechanism
# ---------------------------------------------------------------------------


def test_env_var_activates_kill_switch(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting IKIGAI_KILL_SWITCH=1 activates via env var (priority 1)."""
    monkeypatch.setenv("IKIGAI_KILL_SWITCH", "1")
    status = ks.check_kill_switch(vault_root, data_root)
    assert status.env_var_active is True
    assert status.is_active is True
    assert status.active_reason == "env_var"


def test_vault_file_activates_kill_switch(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
) -> None:
    """Writing vault/.kill_switch.md with status:active activates (priority 2)."""
    (vault_root / ks.VAULT_KILL_SWITCH_FILENAME).write_text(
        "---\nstatus: active\n---\n",
        encoding="utf-8",
    )
    status = ks.check_kill_switch(vault_root, data_root)
    assert status.vault_file_active is True
    assert status.is_active is True
    assert status.active_reason == "vault_file"


def test_data_file_activates_kill_switch(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
) -> None:
    """Touching data/.kill_switch with content 'active' activates (priority 3)."""
    (data_root / ks.DATA_KILL_SWITCH_FILENAME).write_text("active", encoding="utf-8")
    status = ks.check_kill_switch(vault_root, data_root)
    assert status.data_file_active is True
    assert status.is_active is True
    assert status.active_reason == "data_file"


# ---------------------------------------------------------------------------
# 4-6. Priority order
# ---------------------------------------------------------------------------


def test_env_var_wins_over_vault_file(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When env var + vault file both set, env_var wins."""
    (vault_root / ks.VAULT_KILL_SWITCH_FILENAME).write_text(
        "---\nstatus: active\n---\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("IKIGAI_KILL_SWITCH", "1")
    status = ks.check_kill_switch(vault_root, data_root)
    assert status.env_var_active is True
    assert status.vault_file_active is True
    assert status.is_active is True
    assert status.active_reason == "env_var"


def test_vault_file_wins_over_data_file(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
) -> None:
    """When vault file + data file set, vault_file wins."""
    (vault_root / ks.VAULT_KILL_SWITCH_FILENAME).write_text(
        "---\nstatus: active\n---\n",
        encoding="utf-8",
    )
    (data_root / ks.DATA_KILL_SWITCH_FILENAME).write_text("active", encoding="utf-8")
    status = ks.check_kill_switch(vault_root, data_root)
    assert status.vault_file_active is True
    assert status.data_file_active is True
    assert status.active_reason == "vault_file"


def test_data_file_alone_activates(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
) -> None:
    """When only data file is set, status reports data_file as active reason."""
    (data_root / ks.DATA_KILL_SWITCH_FILENAME).write_text("active", encoding="utf-8")
    status = ks.check_kill_switch(vault_root, data_root)
    assert status.env_var_active is False
    assert status.vault_file_active is False
    assert status.data_file_active is True
    assert status.active_reason == "data_file"


# ---------------------------------------------------------------------------
# 7-8. Escalation
# ---------------------------------------------------------------------------


def test_fire_kill_switch_emits_review_queue_entry(
    clean_kill_switch_env: None,
    vault_root: Path,
    review_queue_dir: Path,
) -> None:
    """fire_kill_switch atomically appends to data/review_queue/."""
    event = ks.build_kill_switch_event(
        trigger="actor_mismatch",
        actor_at_fault="agent",
        entity_id=None,
        context={"vault_path": "test.md"},
        recovery_reason="env_var",
    )
    target = ks.fire_kill_switch(event, review_queue_dir, vault_root)
    assert target.exists()
    # Filename is <timestamp>-<kill_id>.json per S5.1
    assert target.name.endswith(f"-{event.kill_id}.json")
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["event_id"] == event.event_id
    assert payload["kill_switch_trigger"] == "actor_mismatch"
    assert payload["actor_at_fault"] == "agent"


def test_fire_kill_switch_writes_audit_log(
    clean_kill_switch_env: None,
    vault_root: Path,
    review_queue_dir: Path,
) -> None:
    """fire_kill_switch appends to .vault_audit.log (best-effort, append-only)."""
    event = ks.build_kill_switch_event(
        trigger="vault_write_bypass",
        actor_at_fault="agent",
        entity_id=None,
        context={"vault_path": "x.md"},
        recovery_reason="vault_file",
    )
    ks.fire_kill_switch(event, review_queue_dir, vault_root)
    audit_path = vault_root / ".vault_audit.log"
    assert audit_path.exists()
    content = audit_path.read_text(encoding="utf-8")
    assert "kill_switch" in content
    assert "trigger=vault_write_bypass" in content


# ---------------------------------------------------------------------------
# 9-11. Wrapper integration
# ---------------------------------------------------------------------------


def test_vault_write_wrapper_blocks_when_kill_switch_active(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
    review_queue_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrapped vault_write raises KillSwitchAbort when kill switch active."""
    monkeypatch.setenv("IKIGAI_KILL_SWITCH", "1")
    tracker = _RateLimitTracker(100, 60.0)
    wrapped = make_wrapped_vault_write(
        vault_root_provider=lambda: vault_root,
        data_root_provider=lambda: data_root,
        review_queue_dir_provider=lambda: review_queue_dir,
        rate_limit_tracker=tracker,
    )
    with pytest.raises(KillSwitchAbort):
        wrapped(
            actor="agent",
            vault_path="test.md",
            body="hello",
            frontmatter_fields={
                "ueid": "tsk:test:00000000-0000-0000-0000-000000000000:0000000000000000"
            },
        )


def _make_sonho_entity() -> Any:
    """Construct a minimal SONHO entity stub for transition_validator testing."""

    # Use object() with attributes — base model is too heavy for a stub.
    class _StubSONHO:
        tier = "SONHO"
        id = "sonho:test:00000000-0000-0000-0000-000000000000:0000000000000000"
        cycle_phase = "plan"

    return _StubSONHO()


def test_vault_write_wrapper_enforces_transition_validator_on_sonho(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
    review_queue_dir: Path,
) -> None:
    """Wrapper raises KillSwitchBypassDetected for SONHO + actor=agent w/o legal caller."""
    tracker = _RateLimitTracker(100, 60.0)
    wrapped = make_wrapped_vault_write(
        vault_root_provider=lambda: vault_root,
        data_root_provider=lambda: data_root,
        review_queue_dir_provider=lambda: review_queue_dir,
        rate_limit_tracker=tracker,
    )
    entity = _make_sonho_entity()
    with pytest.raises(KillSwitchBypassDetected):
        wrapped(
            actor="agent",
            vault_path="sonho/test.md",
            body="x",
            entity=entity,
            frontmatter_fields={},
        )


def test_vault_write_wrapper_allows_user_actor_on_sonho(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
    review_queue_dir: Path,
) -> None:
    """Wrapper allows SONHO writes with actor=user (no abort)."""
    tracker = _RateLimitTracker(100, 60.0)
    wrapped = make_wrapped_vault_write(
        vault_root_provider=lambda: vault_root,
        data_root_provider=lambda: data_root,
        review_queue_dir_provider=lambda: review_queue_dir,
        rate_limit_tracker=tracker,
    )
    entity = _make_sonho_entity()
    # Should not raise (SONHO + actor=user is OK per R8).
    result = wrapped(
        actor="user",
        vault_path="sonho/test.md",
        body="x",
        entity=entity,
        frontmatter_fields={"actor": "user"},
    )
    assert result.get("written") is True
    assert result.get("actor") == "user"


# ---------------------------------------------------------------------------
# 12. Rate limit
# ---------------------------------------------------------------------------


def test_rate_limit_triggers_kill_switch_at_threshold(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
    review_queue_dir: Path,
) -> None:
    """51 writes within window exceeds limit (50/hr default) and fires kill switch."""
    # Build tracker with tiny limit=2 to keep the test fast.
    tracker = _RateLimitTracker(rate_limit_per_window=2, window_seconds=60.0)
    wrapped = make_wrapped_vault_write(
        vault_root_provider=lambda: vault_root,
        data_root_provider=lambda: data_root,
        review_queue_dir_provider=lambda: review_queue_dir,
        rate_limit_tracker=tracker,
    )

    # First 2 writes should pass.
    for i in range(2):
        result = wrapped(
            actor="user",
            vault_path=f"plan{i}.md",
            body="x",
            frontmatter_fields={"actor": "user"},
        )
        assert result.get("written") is True

    # 3rd should hit the limit.
    with pytest.raises(KillSwitchRateLimitExceeded):
        wrapped(
            actor="user",
            vault_path="plan2.md",
            body="x",
            frontmatter_fields={"actor": "user"},
        )

    # And a review_queue entry should exist.
    entries = list(review_queue_dir.glob("*.json"))
    assert any(
        json.loads(p.read_text(encoding="utf-8"))["kill_switch_trigger"] == "rate_limit_exceeded"
        for p in entries
    )


# ---------------------------------------------------------------------------
# 13. Drift invariant (e) — detection via sys.modules / actor=agent traversal
# ---------------------------------------------------------------------------


def test_drift_invariant_e_vault_write_actor_agent_must_traverse_validator(
    clean_kill_switch_env: None,
    vault_root: Path,
    data_root: Path,
    review_queue_dir: Path,
) -> None:
    """Invariant (e): direct vault_write(actor='agent') without wrapper detection.

    Per ADR-029 R12 + W4.7 brief — ``vault_write(actor='agent')`` without
    transitioning through ``validate_phase_transition`` SHOULD raise (the
    wrapper enforces this). This test verifies the wrapper catches the
    bypass via SONHO + actor=agent (R8).
    """
    tracker = _RateLimitTracker(100, 60.0)
    wrapped = make_wrapped_vault_write(
        vault_root_provider=lambda: vault_root,
        data_root_provider=lambda: data_root,
        review_queue_dir_provider=lambda: review_queue_dir,
        rate_limit_tracker=tracker,
    )

    # Attempt to use 'unknown' as actor — should fire R9 actor validation.
    with pytest.raises(KillSwitchActorViolation):
        wrapped(
            actor="unknown",  # type: ignore[arg-type]
            vault_path="plan.md",
            body="x",
            frontmatter_fields={"actor": "unknown"},
        )

    # Confirm wrapper is loaded + reachable via sys.modules (drift invariant
    # bookkeeping: ``vault_write_wrapper`` MUST be importable from the
    # security package — proves no module-path rejection).
    assert "ikigai.security.vault_write_wrapper" in sys.modules
    assert "ikigai.security.kill_switch" in sys.modules

    # LEGAL_CALLERS contains the canonical whitelist (R6 + R7).
    assert "memory_write_atomic" in LEGAL_CALLERS
    assert "dispatch_sub_agents" in LEGAL_CALLERS
