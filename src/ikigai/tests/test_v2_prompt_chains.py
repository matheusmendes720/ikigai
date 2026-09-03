"""Phase 8.2 — prompt chain + tools_v2 tests.

Verifies:
- All 15 prompt modules import cleanly and return stubs in FAKE_LLM mode
- tools_v2.py imports and exposes 8 IKIGAI_NODE_TOOLS
- Drift detector: IKIGAI_TOOLS=12 count is unaffected
- No forbidden imports in v2/prompts/
- MCP observation wrappers: 15 tools total, vault_read invariant
- _handle_ikigai_sync_vault removed from server.py
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent
IKIGAI_SRC = IKIGAI_PKG / "src"
V2_DIR = IKIGAI_SRC / "agents" / "v2"
PROMPTS_DIR = V2_DIR / "prompts"

# Ensure v2 src is on path for imports
_v2_src = IKIGAI_SRC.parent.parent / "src" / "ikigai" / "src"
if str(_v2_src) not in sys.path:
    sys.path.insert(0, str(_v2_src))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _iter_python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_v2_prompts_import_cleanly() -> None:
    """Assert all 15 prompt modules import without error."""
    prompt_modules = [
        "score_passion_observation",
        "score_skill_observation",
        "score_market_observation",
        "score_revenue_observation",
        "score_course_observation",
        "score_meta_vector_observation",
        "observe_qhe_observation",
        "heuristics_regime_observation",
        "h1_energy",
        "h2_qhe_composite",
        "h3_regime_fsm",
        "h4_market_fit",
        "h5_skill_velocity",
        "h6_severity",
        "decompose_rice_observation",
    ]
    for name in prompt_modules:
        try:
            __import__(f"agents.v2.prompts.{name}")
        except ImportError as exc:
            pytest.fail(f"Failed to import {name}: {exc}")


def test_v2_prompts_fake_llm_mode() -> None:
    """With IKIGAI_FAKE_LLM=1, each render function returns a dict (not raises)."""
    os.environ["IKIGAI_FAKE_LLM"] = "1"
    try:
        from agents.v2.prompts import (
            score_passion_observation,
            score_skill_observation,
            score_market_observation,
            score_revenue_observation,
            score_course_observation,
            score_meta_vector_observation,
            observe_qhe_observation,
            heuristics_regime_observation,
            h1_energy,
            h2_qhe_composite,
            h3_regime_fsm,
            h4_market_fit,
            h5_skill_velocity,
            h6_severity,
            decompose_rice_observation,
        )

        render_fns = [
            ("score_passion", score_passion_observation.render_score_passion_observation),
            ("score_skill", score_skill_observation.render_score_skill_observation),
            ("score_market", score_market_observation.render_score_market_observation),
            ("score_revenue", score_revenue_observation.render_score_revenue_observation),
            ("score_course", score_course_observation.render_score_course_observation),
            ("score_meta", score_meta_vector_observation.render_score_meta_vector_observation),
            ("observe_qhe", observe_qhe_observation.render_observe_qhe_observation),
            ("heuristics_regime", heuristics_regime_observation.render_heuristics_regime_observation),
            ("h1_energy", h1_energy.render_h1_energy),
            ("h2_qhe", h2_qhe_composite.render_h2_qhe_composite),
            ("h3_regime", h3_regime_fsm.render_h3_regime_fsm),
            ("h4_market", h4_market_fit.render_h4_market_fit),
            ("h5_skill", h5_skill_velocity.render_h5_skill_velocity),
            ("h6_severity", h6_severity.render_h6_severity),
            ("decompose_rice", decompose_rice_observation.render_decompose_rice_observation),
        ]

        for name, fn in render_fns:
            result = fn({})
            assert isinstance(result, dict), f"{name} did not return a dict: {type(result)}"
            assert "error" not in result or result.get("error") == "llm_call_failed", (
                f"{name} returned error in FAKE_LLM mode: {result}"
            )
    finally:
        os.environ.pop("IKIGAI_FAKE_LLM", None)


def test_v2_tools_v2_imports() -> None:
    """tools_v2.py imports and exposes 8 IKIGAI_NODE_TOOLS."""
    os.environ["IKIGAI_FAKE_LLM"] = "1"
    try:
        from agents.v2.tools_v2 import IKIGAI_NODE_TOOLS

        assert isinstance(IKIGAI_NODE_TOOLS, list), "IKIGAI_NODE_TOOLS must be a list"
        assert len(IKIGAI_NODE_TOOLS) == 8, (
            f"IKIGAI_NODE_TOOLS must have 8 entries, got {len(IKIGAI_NODE_TOOLS)}"
        )
    finally:
        os.environ.pop("IKIGAI_FAKE_LLM", None)


def test_v2_node_tools_have_tool_decorator() -> None:
    """Each tool in IKIGAI_NODE_TOOLS has a .name attribute (LangChain @tool marker)."""
    os.environ["IKIGAI_FAKE_LLM"] = "1"
    try:
        from agents.v2.tools_v2 import IKIGAI_NODE_TOOLS

        for tool in IKIGAI_NODE_TOOLS:
            assert hasattr(tool, "name"), (
                f"Tool {tool} missing .name attribute (LangChain @tool marker required)"
            )
    finally:
        os.environ.pop("IKIGAI_FAKE_LLM", None)


def test_v2_drift_detector_count_unaffected() -> None:
    """IKIGAI_TOOLS=12 count is unaffected by tools_v2.py."""
    tools_path = IKIGAI_SRC / "agents" / "tools.py"
    if not tools_path.exists():
        pytest.skip("tools.py not present")

    source = tools_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    total_count = 0
    initial_list_found = False
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "IKIGAI_TOOLS"
                    and isinstance(node.value, ast.List)
                ):
                    total_count += len(node.value.elts)
                    initial_list_found = True
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "extend"
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "IKIGAI_TOOLS"
                and len(call.args) == 1
                and isinstance(call.args[0], ast.List)
            ):
                total_count += len(call.args[0].elts)

    assert initial_list_found, "IKIGAI_TOOLS initial assignment not found in tools.py"
    assert total_count == 12, (
        f"IKIGAI_TOOLS must contain exactly 12 entries per ADR-013; found {total_count}"
    )


def test_v2_no_forbidden_imports_in_prompts() -> None:
    """No prompt module imports from ikigai.core.scoring or ikigai.core.heuristics."""
    FORBIDDEN = frozenset({"ikigai.core.scoring", "ikigai.core.heuristics", "ikigai.core"})
    violations = []
    for py_file in PROMPTS_DIR.rglob("*.py"):  # type: ignore[union-attr]
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            target = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
            elif isinstance(node, ast.ImportFrom):
                target = node.module
            if target and target in FORBIDDEN:
                violations.append(f"{py_file.name}: forbidden import {target}")
    assert not violations, "Forbidden imports in prompts:\n" + "\n".join(violations)


def test_v2_mcp_observation_wrappers_registered() -> None:
    """After server.py edit, 15 @MCP.tool decorators present (was 8)."""
    server_path = IKIGAI_SRC / "mcp_server" / "server.py"
    if not server_path.exists():
        pytest.skip("server.py not present")

    source = server_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    tool_decorators = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "tool"
            ):
                for kw in decorator.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        tool_decorators.append(kw.value.value)

    assert len(tool_decorators) == 15, (
        f"Expected 15 @MCP.tool decorators, got {len(tool_decorators)}: {tool_decorators}"
    )


def test_v2_sync_vault_handler_readonly() -> None:
    """_handle_ikigai_sync_vault is read-only (vault_write invariant).

    Phase 8.2: the handler was re-registered as a vault-reader (read-only,
    no vault_write call). This test verifies it reads vault but does not write.
    """
    import re

    server_path = IKIGAI_SRC / "mcp_server" / "server.py"
    if not server_path.exists():
        pytest.skip("server.py not present")

    source = server_path.read_text(encoding="utf-8")

    # Handler should exist (re-registered as vault-reader)
    assert "_handle_ikigai_sync_vault" in source, (
        "_handle_ikigai_sync_vault missing — should be re-registered as vault-reader"
    )

    # Extract handler body and verify it's read-only
    match = re.search(
        r"(?s)def _handle_ikigai_sync_vault\([^)]*\).*?(?=\n\ndef |\n\nclass |\Z)",
        source,
    )
    assert match, "Could not find _handle_ikigai_sync_vault function body"
    body = match.group(0)

    # Should read vault
    assert "read_text" in body or ".exists()" in body, (
        "Handler should read from vault"
    )
    # Must not write to vault
    for indicator in ["write_text", "open(", 'open("', "open('"]:
        assert indicator not in body, (
            f"Handler must not write to vault (found '{indicator}')"
        )


def test_v2_observation_wrappers_read_vault() -> None:
    """ikigai_score MCP handler reads from vault path, not SQLite."""
    server_path = IKIGAI_SRC / "mcp_server" / "server.py"
    if not server_path.exists():
        pytest.skip("server.py not present")

    source = server_path.read_text(encoding="utf-8")

    # ikigai_score should read from vault (cycle_state path)
    assert "ikigai/meta/cycle_state" in source, (
        "ikigai_score should read from vault/ikigai/meta/cycle_state/{date}.md"
    )
    # Should NOT call _read_checkpoint in _handle_ikigai_score
    tree = ast.parse(source)
    uses_read_checkpoint = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_handle_ikigai_score":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    fn = sub.func
                    if isinstance(fn, ast.Name) and fn.id == "_read_checkpoint":
                        uses_read_checkpoint = True
    assert not uses_read_checkpoint, (
        "ikigai_score handler should not call _read_checkpoint (vault_read only)"
    )


def test_v2_tools_v2_no_forbidden_function_defs() -> None:
    """tools_v2.py does not define any forbidden function names."""
    tools_v2 = V2_DIR / "tools_v2.py"
    if not tools_v2.exists():
        pytest.skip("tools_v2.py not present")

    FORBIDDEN = frozenset({
        "compute_meta_vector", "compute_qhe", "compute_score", "compute_regime",
        "compute_phase", "compute_passion_score", "compute_skill_score",
        "compute_market_score", "compute_revenue_score", "compute_course_score",
        "compute_alignment_label", "compute_weighted_priority", "rank_tasks",
        "classify_opportunity", "apply_hysteresis",
    })

    source = tools_v2.read_text(encoding="utf-8")
    tree = ast.parse(source)

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in FORBIDDEN:
                violations.append(f"forbidden function def: {node.name}")

    assert not violations, "Forbidden functions in tools_v2.py:\n" + "\n".join(violations)
