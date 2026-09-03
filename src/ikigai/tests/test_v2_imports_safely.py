"""Phase 8.1 — v2 import safety tests.

Verifies that agents/v2/ imports cleanly, has no forbidden imports,
and does not pollute the live agents/ namespace.
"""

from __future__ import annotations

import ast
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
NODES_DIR = V2_DIR / "nodes"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iter_python_files(root: Path) -> list[Path]:
    """Recursively collect .py files under root, skipping __pycache__."""
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


# ---------------------------------------------------------------------------
# Forbidden imports to check
# ---------------------------------------------------------------------------

FORBIDDEN_IMPORTS = frozenset(
    {
        "ikigai.core.scoring",
        "ikigai.core.heuristics",
        "ikigai.core",
        "agents.ikigai_maintainer",
        "src.agents.ikigai_maintainer",
        "ikigai_scorer",
        "cybernetics.daily_loop",
        "vibe_ops.cybernetics.daily_loop",
    }
)

FORBIDDEN_FUNCTIONS = frozenset(
    {
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


def _called_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_v2_graph_imports_cleanly() -> None:
    """graph.py imports without ImportError."""
    # Use the factory function name as used in v2/graph.py
    import sys

    v2_src = IKIGAI_SRC.parent.parent / "src" / "ikigai" / "src"
    if str(v2_src) not in sys.path:
        sys.path.insert(0, str(v2_src))
    try:
        from agents.v2.graph import make_v2_graph

        assert callable(make_v2_graph), "make_v2_graph must be callable"
    except ImportError as exc:
        pytest.fail(f"Failed to import make_v2_graph: {exc}")


def test_v2_state_imports_cleanly() -> None:
    """state.py imports without ImportError."""
    import sys

    v2_src = IKIGAI_SRC.parent.parent / "src" / "ikigai" / "src"
    if str(v2_src) not in sys.path:
        sys.path.insert(0, str(v2_src))
    try:
        from agents.v2.state import IKIGAiStateDict

        assert IKIGAiStateDict is not None
    except ImportError as exc:
        pytest.fail(f"Failed to import IKIGAiStateDict: {exc}")


def test_v2_all_nodes_import() -> None:
    """Each of the 9 node files imports without ImportError."""
    import sys

    v2_src = IKIGAI_SRC.parent.parent / "src" / "ikigai" / "src"
    if str(v2_src) not in sys.path:
        sys.path.insert(0, str(v2_src))

    node_names = [
        "observe",
        "reflect",
        "plan",
        "decompose",
        "score_vectors",
        "heuristics",
        "balance",
        "commit",
        "error",
    ]
    for name in node_names:
        try:
            mod = __import__(f"agents.v2.nodes.{name}", fromlist=[name])
            assert hasattr(mod, f"{name}_node"), f"{name}_node not found in module"
        except ImportError as exc:
            pytest.fail(f"Failed to import {name}_node: {exc}")


def test_v2_no_forbidden_imports() -> None:
    """No file under agents/v2/ imports a forbidden module."""
    violations: list[str] = []
    for py_file in _iter_python_files(V2_DIR):
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
                    f"{py_file.relative_to(IKIGAI_SRC.parent.parent)}:{node.lineno}  "
                    f"forbidden import: {target}"
                )
    assert not violations, "Forbidden imports detected in agents/v2/:\n" + "\n".join(violations)


def test_v2_no_forbidden_function_calls_or_defs() -> None:
    """No file under agents/v2/ defines or calls a forbidden function."""
    violations: list[str] = []
    for py_file in _iter_python_files(V2_DIR):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn_name = _called_name(node.func)
                if fn_name in FORBIDDEN_FUNCTIONS:
                    violations.append(
                        f"{py_file.relative_to(IKIGAI_SRC.parent.parent)}:{node.lineno}  "
                        f"forbidden call: {fn_name}"
                    )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in FORBIDDEN_FUNCTIONS:
                    violations.append(
                        f"{py_file.relative_to(IKIGAI_SRC.parent.parent)}:{node.lineno}  "
                        f"forbidden def: {node.name}"
                    )
    assert not violations, "Forbidden functions detected in agents/v2/:\n" + "\n".join(violations)


def test_v2_legacy_reference_files_not_imported_by_live_code() -> None:
    """Live agents/tools.py does not import v2 legacy reference files."""
    tools_path = IKIGAI_SRC / "agents" / "tools.py"
    if not tools_path.exists():
        pytest.skip("tools.py not present")

    source = tools_path.read_text(encoding="utf-8")
    for name in ("tools_legacy_reference", "harness_legacy_reference"):
        assert name not in source, (
            f"Live agents/tools.py must not reference '{name}' — "
            f"use of legacy reference file would pull forbidden code into runtime"
        )
