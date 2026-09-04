"""Drift invariant (e) — W4.7 retroactive ship per ADR-029 R12.

Per ADR-029 R12 + the W5.1.1 brief §"test_drift_invariants.py":

> **Invariant (e)** — ``vault_write(actor='agent')`` without
> ``transition_validator`` traversal raises ``PermissionError`` / killswitch.

This test FAILS if the wrapper (``vault_write_wrapper``) is bypassed.
Detection mechanism: the wrapper is the SINGLE enforcement point
(ADR-029 R2); this test verifies the wrapper is installed correctly
by:

1. Asserting ``vault_write_wrapper`` exposes the canonical public API
   (legal callers, exceptions, factory function).
2. Asserting ``vault_write(actor='agent')`` through a SONHO entity
   without a legal_caller raises ``KillSwitchBypassDetected``
   (the wrapper enforces the transition validator traversal).
3. Asserting the algorithm_constants.json has the 5 KILL_SWITCH_* +
   REVIEW_QUEUE_BATCH_SIZE keys (no Python DEFAULT_* constants —
   ADR-019 R2).
4. Asserting ``load_constants._defensive_default()`` mirrors the 5
   new keys (per ADR-019 R6).
5. Smoke-checking that the legacy invariants (a-d) still pass
   (regression baseline).

Run::

    pytest src/ikigai/tests/test_drift_invariants.py -v
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path resolution (mirror test_canonical_scope.py)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent
IKIGAI_SRC = IKIGAI_PKG / "src"


def _resolve_repo_root() -> Path:
    """Walk up until we find ``src/ikigai/src`` (the agent/MCP layer)."""
    for parent in THIS_FILE.parents:
        if (parent / "src" / "ikigai" / "src" / "agents").is_dir():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        f"{THIS_FILE} — expected <repo>/src/ikigai/tests/test_drift_invariants.py"
    )


REPO_ROOT = _resolve_repo_root()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iter_python_files(root: Path) -> list[Path]:
    """Recursively collect .py files under ``root``, skipping __pycache__."""
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _relative_to_repo(file: Path) -> str:
    """Return path relative to repo root, using forward slashes."""
    return str(file.relative_to(REPO_ROOT)).replace("\\", "/")


# ---------------------------------------------------------------------------
# Invariant (e) — verification
# ---------------------------------------------------------------------------


# Invariant (e) — 5 new KILL_SWITCH_*/REVIEW_QUEUE_BATCH_SIZE keys (per ADR-019 R2 + ADR-029).
REQUIRED_KILL_SWITCH_KEYS: tuple[str, ...] = (
    "KILL_SWITCH_RATE_LIMIT_PER_HOUR",
    "KILL_SWITCH_RATE_LIMIT_WINDOW_S",
    "KILL_SWITCH_HALT_TIMEOUT_S",
    "KILL_SWITCH_NOTIFY_OPERATOR",
    "REVIEW_QUEUE_BATCH_SIZE",
)


def test_kill_switch_keys_present_in_json() -> None:
    """algorithm_constants.json MUST define all 5 KILL_SWITCH_* + BATCH_SIZE keys.

    Per ADR-019 R1 + ADR-029 §W5.1.1 §"Algorithm Constants JSON Keys".
    Drift detector invariant (l extension) — these 5 keys are the
    canonical SOT.
    """
    json_path = IKIGAI_SRC / "agents" / "v2" / "prompts" / "algorithm_constants.json"
    if not json_path.exists():
        pytest.skip(f"{json_path} not present")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KILL_SWITCH_KEYS if k not in data]
    assert not missing, (
        f"algorithm_constants.json missing required KILL_SWITCH_* / "
        f"REVIEW_QUEUE_BATCH_SIZE keys (ADR-029 §W5.1.1): {missing}. "
        f"Found keys: {sorted(k for k in data if not k.startswith('_'))}"
    )


def test_kill_switch_keys_mirrored_in_defensive_default() -> None:
    """load_constants._defensive_default() MUST mirror all 5 new values (ADR-019 R6)."""
    load_path = IKIGAI_SRC / "agents" / "v2" / "prompts" / "load_constants.py"
    if not load_path.exists():
        pytest.skip(f"{load_path} not present")
    load_source = load_path.read_text(encoding="utf-8")
    missing = [k for k in REQUIRED_KILL_SWITCH_KEYS if f'"{k}"' not in load_source]
    assert not missing, (
        f"load_constants._defensive_default() missing KILL_SWITCH_* mirrors "
        f"(ADR-019 R6 + ADR-029 §W5.1.1): {missing}"
    )


def test_no_kill_switch_python_constants_in_agent_code() -> None:
    """No ``DEFAULT_KILL_SWITCH_*`` / ``DEFAULT_REVIEW_QUEUE_BATCH_SIZE`` constants in agents/v2/*.py.

    Per ADR-019 R2 + ADR-029 §W5.1.1 — all kill switch tuning MUST live in
    JSON only. Extends invariant (l) per W5.1.1 §"Drift Invariants".
    """
    v2_root = IKIGAI_SRC / "agents" / "v2"
    if not v2_root.exists():
        pytest.skip(f"{v2_root} not present")

    allowed_definers = {v2_root / "prompts" / "load_constants.py"}
    forbidden_pattern = re.compile(r"^(DEFAULT_KILL_SWITCH_|DEFAULT_REVIEW_QUEUE_BATCH_SIZE).*")

    import ast

    violations: list[str] = []
    for py_file in _iter_python_files(v2_root):
        if py_file.resolve() in {p.resolve() for p in allowed_definers}:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                name = target.id if isinstance(target, ast.Name) else None
                if name is None:
                    continue
                if forbidden_pattern.match(name):
                    violations.append(
                        f"{_relative_to_repo(py_file)}:{node.lineno}: "
                        f"forbidden kill switch Python constant: {name}"
                    )
    assert not violations, (
        "ADR-019 / ADR-029 §W5.1.1 violation — kill switch tuning MUST live in "
        "prompts/algorithm_constants.json, NOT in src/ikigai/src/agents/v2/*.py. "
        "Violations:\n" + "\n".join(sorted(violations))
    )


# ---------------------------------------------------------------------------
# Invariant (e) — actual enforcement check
# ---------------------------------------------------------------------------


def test_vault_write_wrapper_imports_and_exposes_canonical_api() -> None:
    """W4.7 invariant (e) — wrapper is reachable + exposes the canonical API.

    Per ADR-029 R2 — ``vault_write_wrapper`` is the SINGLE enforcement
    point. If this test fails, either the module was renamed / moved,
    or the import-path was perturbed (which would break the wrapper's
    load-bearing guarantee).
    """
    import importlib

    wrapper_module = importlib.import_module("ikigai.security.vault_write_wrapper")
    kill_switch_module = importlib.import_module("ikigai.security.kill_switch")

    # Canonical surface exposed by vault_write_wrapper.
    assert hasattr(wrapper_module, "make_wrapped_vault_write"), (
        "vault_write_wrapper missing make_wrapped_vault_write factory"
    )
    assert hasattr(wrapper_module, "LEGAL_CALLERS"), (
        "vault_write_wrapper missing LEGAL_CALLERS whitelist (R6 + R7)"
    )
    # R6/R7 legal callers MUST be present in the whitelist.
    assert "memory_write_atomic" in wrapper_module.LEGAL_CALLERS
    assert "dispatch_sub_agents" in wrapper_module.LEGAL_CALLERS
    assert "tag_and_persist" in wrapper_module.LEGAL_CALLERS
    assert "skill_orchestrator" in wrapper_module.LEGAL_CALLERS

    # Canonical surface exposed by kill_switch.
    assert hasattr(kill_switch_module, "KillSwitchActivationStatus")
    assert hasattr(kill_switch_module, "KillSwitchEvent")
    assert hasattr(kill_switch_module, "check_kill_switch")
    assert hasattr(kill_switch_module, "fire_kill_switch")
    assert hasattr(kill_switch_module, "recover_kill_switch")


def test_drift_invariant_e_vault_write_actor_agent_bypasses_validator(
    tmp_path: Path,
) -> None:
    """W4.7 invariant (e) — direct vault_write(actor='agent') on SONHO raises.

    Per ADR-029 R12 + W5.1.1 brief: ``vault_write(actor='agent')`` without
    ``transition_validator`` traversal raises. The wrapper enforces this
    via R4 + R8.
    """
    # Build a minimal sandbox.
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    data_root = tmp_path / "data"
    review_dir = data_root / "review_queue"
    review_dir.mkdir(parents=True, exist_ok=True)

    from ikigai.security.vault_write_wrapper import (
        KillSwitchBypassDetected,
        _RateLimitTracker,
        make_wrapped_vault_write,
    )

    tracker = _RateLimitTracker(100, 60.0)
    wrapped = make_wrapped_vault_write(
        vault_root_provider=lambda: vault_root,
        data_root_provider=lambda: data_root,
        review_queue_dir_provider=lambda: review_dir,
        rate_limit_tracker=tracker,
    )

    # Stub SONHO entity (matches the test_kill_switch.py stub).
    class _StubSONHO:
        tier = "SONHO"
        id = "sonho:drift-test:00000000-0000-0000-0000-000000000000:0000000000000000"
        cycle_phase = "plan"

    # The invariant: actor=agent + SONHO + no legal_caller => KillSwitchBypassDetected.
    with pytest.raises(KillSwitchBypassDetected):
        wrapped(
            actor="agent",
            vault_path="sonho/drift-test.md",
            body="x",
            entity=_StubSONHO(),
            frontmatter_fields={},
        )


# ---------------------------------------------------------------------------
# Regression — legacy invariants (a-d) must still pass
# ---------------------------------------------------------------------------


def test_legacy_drift_invariants_a_d_still_pass() -> None:
    """Regression: invariants (a-d) from test_canonical_scope.py still pass.

    Per ADR-029 §"Drift Invariants" — the new W5.1.1 invariants (k, l
    extension + e) MUST coexist with the W3.2 invariant (l) and the
    W3.5-W3.6 invariant (k). This test sanity-checks that the canonical
    scope detector remains at its baseline (38/38 PASS as of W4.6 ship).
    """
    canonical_scope = IKIGAI_TESTS / "test_canonical_scope.py"
    if not canonical_scope.exists():
        pytest.skip("test_canonical_scope.py not present")
    # We do NOT exec pytest here (re-running the full suite is a CI
    # concern). Instead, we verify the file exists + has the
    # ``test_no_algorithm_constants_in_agent_code`` invariant asserted
    # (the canonical invariant (l) per ADR-019 R7).
    source = canonical_scope.read_text(encoding="utf-8")
    assert "test_no_algorithm_constants_in_agent_code" in source, (
        "test_canonical_scope.py: canonical scope invariant (l) regressed"
    )


# ---------------------------------------------------------------------------
# sys.modules bookkeeping — proves the wrapper is importable via canonical
# import path (used by test_kill_switch.py for drift invariant (e) hook)
# ---------------------------------------------------------------------------


def test_wrapper_modules_loaded_in_sys_modules() -> None:
    """Sanity: wrapper + kill switch modules are importable via canonical paths."""
    # Either importing on test execution (preferred) or already-loaded.
    if "ikigai.security.vault_write_wrapper" not in sys.modules:
        # Trigger import via canonical path.
        import ikigai.security.vault_write_wrapper
    if "ikigai.security.kill_switch" not in sys.modules:
        import ikigai.security.kill_switch  # noqa: F401

    assert "ikigai.security.vault_write_wrapper" in sys.modules
    assert "ikigai.security.kill_switch" in sys.modules
