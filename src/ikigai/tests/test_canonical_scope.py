"""ADR-013 canonical-scope drift detector.

This test FAILS if any production code under the IKIGAI agent / MCP / gateway
layer imports, references, instantiates, or calls any symbol listed in
ADR-013's OUT OF SCOPE table. It also asserts that ``IKIGAI_TOOLS`` in
``src/ikigai/src/agents/tools.py`` is exactly 12 entries (data-plane +
vault reads only — no algo/policy/scoring tools allowed).

Scope of the scan: ``src/ikigai/src/{agents,mcp_server,ikigai/{gateway,cli,
adapters}}``. The orchestrator layer (``vibe-ops/``) and the data-mesh layer
(``src/mesh/``) are intentionally NOT scanned here — they have their own
attribution §3 / DriftFinding tracking. This test enforces that the agent
layer is a planning assistant only.

The detector is load-bearing enforcement per ADR-013 §"Drift Detector":
running this test in CI is the canonical way to prevent future sessions
from accidentally re-introducing deleted math/kernel code.

Run::

    pytest src/ikigai/tests/test_canonical_scope.py -v
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repository root resolution
# ---------------------------------------------------------------------------
# Tests run from various cwds. Resolve the ikigai package root by walking up
# from this file's location until we find ``src/ikigai/src``.
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
        f"{THIS_FILE} — expected <repo>/src/ikigai/tests/test_canonical_scope.py"
    )


REPO_ROOT = _resolve_repo_root()
# Scope: IKIGAI agent layer + MCP server + gateway + CLI + adapters.
# Excludes vibe-ops/ (orchestrator, attribution §3) and src/mesh/ (data plane).
PROD_LAYERS = [
    IKIGAI_SRC / "agents",
    IKIGAI_SRC / "mcp_server",
    IKIGAI_SRC / "ikigai" / "gateway",
    IKIGAI_SRC / "ikigai" / "cli",
    IKIGAI_SRC / "ikigai" / "adapters",
]


# ---------------------------------------------------------------------------
# Forbidden symbols (from ADR-013 OUT OF SCOPE table)
# ---------------------------------------------------------------------------

# Import paths that MUST NOT appear in any production module.
FORBIDDEN_IMPORTS: frozenset[str] = frozenset(
    {
        # Deleted 2026-08-31 — math kernel packages
        "ikigai.core.scoring",
        "ikigai.core.heuristics",
        "ikigai.core",
        # Deleted 2026-08-31 — full-math LangGraph
        "agents.ikigai_maintainer",
        "src.agents.ikigai_maintainer",
        # Deleted 2026-08-31 — algo wrapper
        "ikigai_scorer",
        # Forbidden per attribution §3 — orchestrator math execution
        "cybernetics.daily_loop",
        "vibe_ops.cybernetics.daily_loop",
    }
)

# Function names that MUST NOT be defined or called in production code.
FORBIDDEN_FUNCTIONS: frozenset[str] = frozenset(
    {
        # Vector score computations (deleted 2026-08-31)
        "compute_meta_vector",
        "compute_qhe",
        "compute_score",
        "compute_regime",
        "compute_phase",
        "compute_passion_score",
        "compute_skill_score",
        "compute_market_score",
        "compute_revenue_score",
        "compute_course_score",
        "compute_alignment_label",
        "compute_weighted_priority",
        "rank_tasks",
        "classify_opportunity",
        "apply_hysteresis",
    }
)

# Class names that MUST NOT be instantiated or referenced.
FORBIDDEN_CLASSES: frozenset[str] = frozenset(
    {
        "IkigaiScorer",
        "QHEScorer",
        "PassionScorer",
        "RegimeClassifier",
        "PhaseDetector",
        "VectorScorer",
    }
)

# MCP tool names that MUST NOT be registered via @MCP.tool in mcp_server.
# PHASE 8.2 UPDATE: ikigai_score, ikigai_regime, ikigai_phase, ikigai_corrections,
# ikigai_checkpoint, ikigai_sync_vault, ikigai_plan_cycle were re-registered as
# vault-reading observation wrappers (no math execution). Removed from this set.
FORBIDDEN_MCP_TOOLS: frozenset[str] = frozenset()

# Production directories to scan (combined for AST walk).
SCAN_ROOTS: list[Path] = [p for p in PROD_LAYERS if p.exists()]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iter_python_files(root: Path) -> list[Path]:
    """Recursively collect .py files under ``root``, skipping __pycache__."""
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _format_violation(file: Path, line: int, kind: str, detail: str) -> str:
    return f"  {file.relative_to(REPO_ROOT)}:{line}  [{kind}]  {detail}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_forbidden_imports() -> None:
    """Production code MUST NOT import deleted math/kernel packages."""
    violations: list[str] = []
    for root in SCAN_ROOTS:
        for py_file in _iter_python_files(root):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                target: str | None = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target = alias.name
                elif isinstance(node, ast.ImportFrom):
                    target = node.module
                if target and target in FORBIDDEN_IMPORTS:
                    violations.append(
                        _format_violation(
                            py_file, node.lineno, "IMPORT", f"forbidden module: {target}"
                        )
                    )
    assert not violations, (
        "ADR-013 violation — forbidden imports detected:\n"
        + "\n".join(sorted(violations))
    )


def test_no_forbidden_function_calls_or_defs() -> None:
    """Production code MUST NOT define or call forbidden math functions."""
    violations: list[str] = []
    for root in SCAN_ROOTS:
        for py_file in _iter_python_files(root):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = _called_name(node.func)
                    if func_name in FORBIDDEN_FUNCTIONS:
                        violations.append(
                            _format_violation(
                                py_file, node.lineno, "CALL", f"forbidden function: {func_name}"
                            )
                        )
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name in FORBIDDEN_FUNCTIONS:
                        violations.append(
                            _format_violation(
                                py_file, node.lineno, "DEF", f"forbidden function: {node.name}"
                            )
                        )
    assert not violations, (
        "ADR-013 violation — forbidden functions detected:\n"
        + "\n".join(sorted(violations))
    )


def test_no_forbidden_class_references() -> None:
    """Production code MUST NOT reference forbidden math classes."""
    violations: list[str] = []
    for root in SCAN_ROOTS:
        for py_file in _iter_python_files(root):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name in FORBIDDEN_CLASSES:
                    violations.append(
                        _format_violation(
                            py_file, node.lineno, "CLASS-DEF", f"forbidden class: {node.name}"
                        )
                    )
                elif isinstance(node, ast.Name) and node.id in FORBIDDEN_CLASSES:
                    violations.append(
                        _format_violation(
                            py_file, node.lineno, "CLASS-REF", f"forbidden class: {node.id}"
                        )
                    )
    assert not violations, (
        "ADR-013 violation — forbidden class references detected:\n"
        + "\n".join(sorted(violations))
    )


def test_no_forbidden_mcp_tool_wrappers() -> None:
    """MCP server MUST NOT register forbidden math/policy tools."""
    mcp_server_dir = IKIGAI_SRC / "mcp_server"
    if not mcp_server_dir.exists():
        pytest.skip("mcp_server directory not present")
    violations: list[str] = []
    for py_file in _iter_python_files(mcp_server_dir):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        # Walk top-level definitions looking for @MCP.tool(name="<forbidden>").
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                tool_name = _extract_tool_name_from_decorator(decorator)
                if tool_name and tool_name in FORBIDDEN_MCP_TOOLS:
                    violations.append(
                        _format_violation(
                            py_file, node.lineno, "MCP-TOOL",
                            f"forbidden tool wrapper: {tool_name} (function {node.name})",
                        )
                    )
    assert not violations, (
        "ADR-013 violation — forbidden @MCP.tool wrappers detected:\n"
        + "\n".join(sorted(violations))
    )


def test_ikigai_tools_count_is_12() -> None:
    """IKIGAI_TOOLS list MUST have exactly 12 entries (data + vault reads).

    Adding any math/policy/scoring tool violates ADR-013. Removing a
    legitimate tool also breaks the agent harness. Counts both the initial
    ``IKIGAI_TOOLS = [...]`` assignment AND any ``IKIGAI_TOOLS.extend([...])``
    calls so multi-step lists are measured correctly.
    """
    tools_path = IKIGAI_SRC / "agents" / "tools.py"
    if not tools_path.exists():
        pytest.skip(f"{tools_path} not present")
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
        f"IKIGAI_TOOLS must contain exactly 12 entries per ADR-013; "
        f"found {total_count}. Adding/removing requires updating ADR-013."
    )


# ---------------------------------------------------------------------------
# AST helpers (used above)
# ---------------------------------------------------------------------------


def _called_name(func: ast.AST) -> str | None:
    """Return the bare name of a Call target, or None if it's an attribute/expr."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _extract_tool_name_from_decorator(decorator: ast.AST) -> str | None:
    """Find ``name="<tool>"`` kwarg in an @MCP.tool(...) decorator."""
    if not isinstance(decorator, ast.Call):
        return None
    for keyword in decorator.keywords:
        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return None
