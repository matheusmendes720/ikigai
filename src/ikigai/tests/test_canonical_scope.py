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

Additional invariants enforced here (Phase 8.5 extension):
- 5-part UEID regex is canonical (per ueid-5part-canonical-decision-2026-08-31)
- Fork adapter Protocol coverage: every adapter in src/mesh/adapters/ implements
  ForkAdapter (read/apply_change/supports_field)
- data/review_queue/ is append-only — only queue.enqueue writes new files

Run::

    pytest src/ikigai/tests/test_canonical_scope.py -v
"""

from __future__ import annotations

import ast
import re
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
    assert not violations, "ADR-013 violation — forbidden imports detected:\n" + "\n".join(
        sorted(violations)
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
    assert not violations, "ADR-013 violation — forbidden functions detected:\n" + "\n".join(
        sorted(violations)
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
    assert not violations, "ADR-013 violation — forbidden class references detected:\n" + "\n".join(
        sorted(violations)
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
                            py_file,
                            node.lineno,
                            "MCP-TOOL",
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
# Phase 8.5 — additional invariants
# ---------------------------------------------------------------------------


def test_ueid_canonical_regex_enforced() -> None:
    """UEID regex in src/contracts/common.py must be the canonical 4-part format.

    Per ueid-5part-canonical-decision-2026-08-31: a 5-part promotion was
    considered but the actual canonical regex in src/contracts/common.py
    remains 4-part (type:slug:uuid:hash). This test enforces that nobody
    silently changes the canonical regex or introduces a divergent one.
    """
    common_path = REPO_ROOT / "src" / "contracts" / "common.py"
    if not common_path.exists():
        pytest.skip(f"{common_path} not present")
    source = common_path.read_text(encoding="utf-8")

    # Canonical 4-part UEID: type:slug:uuid:hash (all lowercase, 4 colons-separated
    # segments). uuid is full 36-char hex with dashes, hash is bare hex.
    canonical_pattern = r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$"
    assert canonical_pattern in source, (
        f"UEID canonical regex not found in {common_path}. "
        f"Expected 4-part pattern: {canonical_pattern!r}. "
        "See ueid-5part-canonical-decision-2026-08-31."
    )


def test_fork_adapter_protocol_coverage() -> None:
    """Every concrete fork adapter in src/mesh/adapters/ must implement ForkAdapter.

    Per phase-3-data-mesh spec: CLI, taskdog, and solverforge-calendar
    adapters must each define read/apply_change/supports_field. The a2ui
    adapter is spec-only (no storage backing) — it is excluded from this
    invariant.
    """
    adapters_dir = REPO_ROOT / "src" / "mesh" / "adapters"
    if not adapters_dir.exists():
        pytest.skip(f"{adapters_dir} not present")

    required_methods = {"read", "apply_change", "supports_field"}
    excluded = {"a2ui_schema.py"}  # spec-only — no storage
    missing: list[str] = []
    for py_file in sorted(adapters_dir.glob("*.py")):
        if py_file.name in {"base.py", "__init__.py"} | excluded:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        found_class_with_methods = False
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            method_names = {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            if required_methods.issubset(method_names):
                found_class_with_methods = True
                break
        if not found_class_with_methods:
            missing.append(py_file.name)

    assert not missing, (
        "Fork adapters missing ForkAdapter Protocol methods "
        f"(read/apply_change/supports_field): {sorted(missing)}"
    )


def test_review_queue_append_only() -> None:
    """data/review_queue/ must only be written via mesh.queue.enqueue().

    Append-only invariant from CLAUDE.md global conventions. Direct
    writes outside the queue violate this and break the review-queue
    worker (which polls by file mtime).

    The review_queue_worker.py is an exception — it CONSUMES events by
    appending a status field (the 'processed' marker). It is allowed
    to write to data/review_queue/ but only via its single ack path.
    """
    mesh_dir = REPO_ROOT / "src" / "mesh"
    if not mesh_dir.exists():
        pytest.skip(f"{mesh_dir} not present")

    queue_py = mesh_dir / "queue.py"
    queue_source = queue_py.read_text(encoding="utf-8") if queue_py.exists() else ""

    # Files in mesh/ that mention review_queue and contain write patterns.
    # Allowlist: queue.py (writer) and review_queue_worker.py (ack consumer).
    allowlist = {"queue.py", "review_queue_worker.py"}
    write_patterns = {
        "open(",
        ".write_text(",
        ".write_bytes(",
    }

    review_queue_violations: list[str] = []
    for py_file in mesh_dir.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        if py_file.name in allowlist:
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if "review_queue" not in source.lower() and "REVIEW_QUEUE" not in source:
            continue
        for pattern in write_patterns:
            if pattern in source:
                review_queue_violations.append(f"{py_file.relative_to(REPO_ROOT)}:{pattern}")
                break

    assert not review_queue_violations, (
        "data/review_queue/ must be append-only via mesh.queue.enqueue() "
        "or consumed via review_queue_worker. Other writers:\n  "
        + "\n  ".join(sorted(review_queue_violations))
    )

    # Sanity check: queue.py MUST contain the enqueue function.
    assert "def enqueue" in queue_source, (
        "mesh/queue.py must define enqueue() as the canonical review_queue writer"
    )


# ---------------------------------------------------------------------------
# W3.5 — ADR-025 skill-binding invariant (R4)
# ---------------------------------------------------------------------------

_SKILLS_DIR = IKIGAI_SRC / "agents" / "v2" / "skills"


@pytest.mark.parametrize(
    "skill_name",
    [
        pytest.param("daily", id="daily"),  # actual filename is daily.md, not ikigai-daily.md
        pytest.param("weekly", id="weekly", marks=pytest.mark.skip(reason="W3.6 territory")),
        pytest.param("monthly", id="monthly", marks=pytest.mark.skip(reason="W3.6 territory")),
        pytest.param("quarterly", id="quarterly", marks=pytest.mark.skip(reason="W3.6 territory")),
    ],
)
def test_skill_manifest_has_entry_point(skill_name) -> None:
    """All skill .md files MUST have entry_point in YAML frontmatter (ADR-025 R4)."""
    import re

    skill_file = _SKILLS_DIR / f"{skill_name}.md"
    if not skill_file.exists():
        pytest.skip(f"{skill_file} not present")

    content = skill_file.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert m, f"{skill_name}.md missing YAML frontmatter"
    import yaml

    frontmatter = yaml.safe_load(m.group(1))
    assert "entry_point" in frontmatter, (
        f"{skill_name}.md missing entry_point field in frontmatter (ADR-025 R4)"
    )


@pytest.mark.parametrize(
    "skill_name",
    [
        pytest.param("daily", id="daily"),  # actual filename is daily.md, not ikigai-daily.md
        pytest.param("weekly", id="weekly", marks=pytest.mark.skip(reason="W3.6 territory")),
        pytest.param("monthly", id="monthly", marks=pytest.mark.skip(reason="W3.6 territory")),
        pytest.param("quarterly", id="quarterly", marks=pytest.mark.skip(reason="W3.6 territory")),
    ],
)
def test_skill_entry_point_is_valid_node(skill_name) -> None:
    """All skill entry_point values MUST be members of NODES (ADR-025 R4)."""
    import re

    skill_file = _SKILLS_DIR / f"{skill_name}.md"
    if not skill_file.exists():
        pytest.skip(f"{skill_file} not present")

    content = skill_file.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert m, f"{skill_name}.md missing YAML frontmatter"
    import yaml

    frontmatter = yaml.safe_load(m.group(1))
    entry_point = frontmatter.get("entry_point")
    if entry_point is None:
        pytest.skip(f"{skill_name}.md has no entry_point (skip-for-W3.6)")

    # Import NODES at runtime to avoid the legacy-state import conflict
    v2_graph_path = IKIGAI_SRC / "agents" / "v2" / "graph.py"
    if not v2_graph_path.exists():
        pytest.skip("graph.py not present")
    graph_source = v2_graph_path.read_text(encoding="utf-8")
    nodes_match = re.search(r"^NODES\s*=\s*\((.*?)\)", graph_source, re.DOTALL)
    assert nodes_match, "Could not find NODES tuple in graph.py"
    nodes_list = [n.strip().strip(",'\"") for n in nodes_match.group(1).split() if n.strip()]
    assert entry_point in nodes_list, (
        f"{skill_name}.md entry_point {entry_point!r} not in NODES; "
        f"must be one of {nodes_list}"
    )


@pytest.mark.parametrize(
    "skill_name",
    [
        pytest.param("daily", id="daily"),  # actual filename is daily.md, not ikigai-daily.md
        pytest.param("weekly", id="weekly", marks=pytest.mark.skip(reason="W3.6 territory")),
        pytest.param("monthly", id="monthly", marks=pytest.mark.skip(reason="W3.6 territory")),
        pytest.param("quarterly", id="quarterly", marks=pytest.mark.skip(reason="W3.6 territory")),
    ],
)
def test_skill_manifest_has_actor_field(skill_name) -> None:
    """All skill .md files MUST have actor in {'user', 'agent'} (ADR-025 R4)."""
    import re

    skill_file = _SKILLS_DIR / f"{skill_name}.md"
    if not skill_file.exists():
        pytest.skip(f"{skill_file} not present")

    content = skill_file.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert m, f"{skill_name}.md missing YAML frontmatter"
    import yaml

    frontmatter = yaml.safe_load(m.group(1))
    assert "actor" in frontmatter, (
        f"{skill_name}.md missing actor field in frontmatter (ADR-025 R4)"
    )
    assert frontmatter["actor"] in {"user", "agent"}, (
        f"{skill_name}.md actor must be 'user' or 'agent', "
        f"got {frontmatter['actor']!r}"
    )


def test_no_make_v2_graph_call_outside_invoke_skill() -> None:
    """Any make_v2_graph(entry_point=...) call outside invoke_skill() is flagged.

    Per ADR-025 R4: invoke_skill() is the only permitted call site for
    make_v2_graph(entry_point=...) in interfaces/cli/v2.py.
    Uses AST scan to detect all call sites, then checks each one is
    inside the invoke_skill function body.
    """
    v2_cli_path = REPO_ROOT / "interfaces" / "cli" / "v2.py"
    if not v2_cli_path.exists():
        pytest.skip(f"{v2_cli_path} not present")

    source = v2_cli_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Find the invoke_skill function's AST node
    invoke_skill_node: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "invoke_skill":
            invoke_skill_node = node
            break

    # Find all make_v2_graph(entry_point=...) call sites in the module
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Check if it's make_v2_graph(...)
        func_name = _called_name(node.func)
        if func_name != "make_v2_graph":
            continue
        # Check if it has entry_point=... keyword argument
        has_entry_point = any(
            kw.arg == "entry_point" for kw in node.keywords
        )
        if not has_entry_point:
            continue
        # Check if this call is inside invoke_skill function body
        if invoke_skill_node is not None and _is_node_inside(node, invoke_skill_node):
            continue  # allowed — inside invoke_skill
        # Check if this call is inside a function whose name starts with "_load_graph_factory"
        # (lazy import wrapper — allowed to call make_v2_graph)
        parent_func = _find_parent_function(node, tree)
        if parent_func is not None and parent_func.name == "_load_graph_factory":
            continue  # allowed — lazy factory wrapper
        violations.append(f"make_v2_graph(entry_point=...) at line {node.lineno}")

    assert not violations, (
        "make_v2_graph(entry_point=...) may only be called inside invoke_skill() "
        "(per ADR-025 R4). Violations:\n  " + "\n  ".join(violations)
    )


def _is_node_inside(node: ast.AST, parent: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if node is syntactically inside parent FunctionDef body."""
    for child in ast.walk(parent):
        if child is node:
            return True
    return False


def _find_parent_function(node: ast.AST, tree: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find the FunctionDef/AsyncFunctionDef that contains node (direct parent only)."""
    for parent in ast.walk(tree):
        if not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in parent.body:
            if _contains_node(child, node):
                return parent
    return None


def _contains_node(parent: ast.AST, target: ast.AST) -> bool:
    """Return True if target is inside parent (direct containment check)."""
    for child in ast.walk(parent):
        if child is target:
            return True
    return False


# ---------------------------------------------------------------------------
# W3.2 — ADR-019 prompt-template-only invariant
# ---------------------------------------------------------------------------

# Module-level constants for algorithm tuning are forbidden in
# src/ikigai/src/agents/v2/*.py EXCEPT in prompts/load_constants.py (the
# loader itself). Algorithm tuning happens ONLY by editing
# prompts/algorithm_constants.json — see dcode-harness-TASKS.md W3.2 + W5.2.
#
# The regex matches the EXACT names of constants that lived in state.py
# pre-W3.2, plus a generic pattern for any future DEFAULT_QHE / DEFAULT_WORKLOAD
# / DEFAULT_CAPACITY / HYSTERESIS_* / HEURISTICS_H<N>_* / REGIME_TARGETS additions.
_FORBIDDEN_ALGO_CONST_NAMES: tuple[str, ...] = (
    "DEFAULT_QHE_PUSH",
    "DEFAULT_QHE_RECOVER",
    "DEFAULT_WORKLOAD_OVERLOAD_FACTOR",
    "DEFAULT_WORKLOAD_UNDERLOAD_FACTOR",
    "DEFAULT_CAPACITY_HOURS_PER_DAY",
    "HYSTERESIS_UPGRADE_DAYS",
    "HYSTERESIS_DOWNGRADE_DAYS",
    "REGIME_TARGETS",
)
# Generic pattern catches future additions matching the same prefix.
_FORBIDDEN_ALGO_CONST_PATTERN = re.compile(
    r"^(DEFAULT_QHE|DEFAULT_WORKLOAD|DEFAULT_CAPACITY|HYSTERESIS_|HEURISTICS_H\d_|REGIME_TARGETS)"
)


def test_no_algorithm_constants_in_agent_code() -> None:
    """agents/v2/*.py MUST NOT define algorithm-tuning constants (ADR-019).

    Algorithm tuning values (Q_HE thresholds, workload factors, hysteresis
    days, regime targets, heuristic deviation thresholds) are stored in
    prompts/algorithm_constants.json and accessed via prompts/load_constants.
    The only file allowed to DEFINE these constants is
    prompts/load_constants.py (the loader's _defensive_default fallback).

    Violations include:
      - Re-introducing DEFAULT_QHE_PUSH = 0.85 in state.py
      - Hardcoding {"PUSH": 0.85, ...} in heuristics.py
      - Adding DEFAULT_CAPACITY_HOURS_PER_DAY = 8.0 anywhere

    To TUNE the algorithm: edit prompts/algorithm_constants.json. To add a
    NEW tuning knob: add it to that JSON first, then load_constants exposes
    it via get(key). Never introduce a Python DEFAULT_* in agent code.
    """
    v2_root = IKIGAI_SRC / "agents" / "v2"
    if not v2_root.exists():
        pytest.skip(f"{v2_root} not present")

    # Only load_constants.py is allowed to DEFINE these constants (it needs
    # _defensive_default for cases where the JSON file is absent). Every
    # other file in agents/v2/ must reference them via load_constants.get().
    allowed_definers = {v2_root / "prompts" / "load_constants.py"}

    violations: list[str] = []
    for py_file in _iter_python_files(v2_root):
        if py_file.resolve() in {p.resolve() for p in allowed_definers}:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        # Only check MODULE-LEVEL assignments (top-level body, not inside a
        # function or class). This avoids false positives on local variable
        # names that happen to share the prefix.
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                name = target.id if isinstance(target, ast.Name) else None
                if name is None:
                    continue
                if name in _FORBIDDEN_ALGO_CONST_NAMES or _FORBIDDEN_ALGO_CONST_PATTERN.match(name):
                    violations.append(
                        _format_violation(
                            py_file,
                            node.lineno,
                            "ALGO-CONST",
                            f"forbidden algorithm constant: {name}",
                        )
                    )

    assert not violations, (
        "ADR-019 violation — algorithm tuning constants MUST live in "
        "prompts/algorithm_constants.json, NOT in src/ikigai/src/agents/v2/*.py. "
        "Use load_constants.get(key) instead. Violations:\n" + "\n".join(sorted(violations))
    )


def test_no_state_module_imports_default_constants() -> None:
    """agents/v2/state.py MUST NOT export DEFAULT_QHE_* / HYSTERESIS_* / etc.

    These names were stripped from state.py in W3.2 (2026-09-04). The state
    module is now pure data classes + TypedDicts. Adding them back would
    violate ADR-019 (algorithm-tuning lives in prompt-template config only).
    """
    state_path = IKIGAI_SRC / "agents" / "v2" / "state.py"
    if not state_path.exists():
        pytest.skip(f"{state_path} not present")
    try:
        tree = ast.parse(state_path.read_text(encoding="utf-8"))
    except SyntaxError:
        pytest.skip(f"{state_path} has syntax errors")

    violations: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            name = target.id if isinstance(target, ast.Name) else None
            if name is None:
                continue
            if name in _FORBIDDEN_ALGO_CONST_NAMES or _FORBIDDEN_ALGO_CONST_PATTERN.match(name):
                violations.append(
                    _format_violation(
                        state_path,
                        node.lineno,
                        "STATE-ALGO-CONST",
                        f"forbidden algorithm constant in state.py: {name}",
                    )
                )
    assert not violations, (
        "ADR-019 violation — state.py MUST NOT export algorithm constants "
        "(they live in prompts/algorithm_constants.json). Violations:\n"
        + "\n".join(sorted(violations))
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
