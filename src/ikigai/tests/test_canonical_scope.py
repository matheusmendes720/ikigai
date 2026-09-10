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
from datetime import datetime
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
#
# V5-E (2026-09-07 "Opção B-A — radical-máxima") DELETED these 7 observation
# wrappers from server.py (they re-read PAV-written vault artifacts, no
# math execution). Drift net now forbids re-registration — if any of these
# tool names reappear inside an ``@MCP.tool(...)`` decorator, the suite
# FAILS at ``test_no_forbidden_mcp_tool_wrappers``.
FORBIDDEN_MCP_TOOLS: frozenset[str] = frozenset(
    {
        "ikigai_score",
        "ikigai_regime",
        "ikigai_phase",
        "ikigai_corrections",
        "ikigai_plan_cycle",
        "ikigai_checkpoint",
        "ikigai_sync_vault",
    }
)

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


# Module-level constants that MUST NOT be defined in production code.
# Per ADR-013 (planner-only invariant) the agent layer MUST NOT carry any
# algorithm parameters (PAE weights, QHE coefficients, regime thresholds,
# scoring tunables). After V5-D/V5-F radical cleanup all such constants
# were deleted from the agent layer; this guard prevents re-introduction.
#
# Match rule: UPPER_SNAKE_CASE names whose body contains an algorithm /
# scoring / regime / heuristic keyword. This is deliberately broader than
# the FORBIDDEN_FUNCTIONS list — it catches *parameters* not just code.
_ALGO_CONSTANT_KEYWORDS: frozenset[str] = frozenset(
    {
        "PAE",
        "QHE",
        "REGIME",
        "VECTOR",
        "SCORE",
        "SCORING",
        "WEIGHT",
        "HEURISTIC",
        "THRESHOLD",
        "ALIGNMENT",
        "PHASE",
        "CYCLE",
        "RANK",
    }
)
# Algorithm-typed suffixes that mark a numeric/tunable constant.
_ALGO_CONSTANT_SUFFIXES: tuple[str, ...] = (
    "_WEIGHT",
    "_THRESHOLD",
    "_COEFFICIENT",
    "_SCORE",
    "_FACTOR",
    "_RATIO",
    "_DECAY",
    "_EPSILON",
    "_ALPHA",
    "_BETA",
    "_GAMMA",
    "_DELTA",
)


def test_no_algorithm_constants_in_agent_code() -> None:
    """Production code MUST NOT define algorithm-parameter constants (ADR-013).

    Catches module-level ``FOO_BAR = <number>`` assignments whose name
    matches an algorithm/score/regime keyword OR ends with a tunable
    suffix (``_WEIGHT``, ``_THRESHOLD``, ``_COEFFICIENT``…). The
    canonical invariant (l) per ADR-019 R7 / W3.2.
    """
    import re as _re

    violations: list[str] = []
    # Match NAME = <numeric-or-bool-or-call> at module top-level only —
    # we use ast.Assign nodes restricted to tree.body so nested function
    # bodies are ignored (those are private constants, not exposed policy).
    for root in PROD_LAYERS:
        if not root.exists():
            continue
        for py_file in _iter_python_files(root):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if not (
                        isinstance(target, ast.Name)
                        and target.id.isupper()
                        and "_" in target.id
                    ):
                        continue
                    # Skip typing constructs — `Foo = Literal["..."]` is a
                    # TYPE ALIAS for state labels (e.g. REGIME_STATES =
                    # Literal["PUSH","MAINTAIN",...]) not an algorithm
                    # tunable. Skip `TypedDict`/`Optional`/`Union` aliases too.
                    if _is_typing_alias(node.value):
                        continue
                    name = target.id
                    name_upper = name.upper()
                    # Keyword check (case-insensitive substring on tokens)
                    if any(
                        kw in name_upper
                        for kw in (
                            "PAE",
                            "QHE",
                            "REGIME",
                            "VECTOR",
                            "HEURISTIC",
                            "ALIGNMENT",
                            "PHASE",
                            "CYCLE",
                            "RANK",
                            "SCORE",
                            "SCORING",
                        )
                    ):
                        violations.append(
                            _format_violation(
                                py_file,
                                node.lineno,
                                "CONSTANT-KEYWORD",
                                f"forbidden algorithm-constant name: {name}",
                            )
                        )
                        continue
                    # Suffix check (e.g. _WEIGHT, _THRESHOLD)
                    if any(name.endswith(suf) for suf in _ALGO_CONSTANT_SUFFIXES):
                        # Only flag if the RHS is a numeric/bool literal —
                        # exclude string constants (those are usually labels).
                        value = node.value
                        if isinstance(value, (ast.Constant,)):
                            if isinstance(value.value, (int, float, bool)):
                                violations.append(
                                    _format_violation(
                                        py_file,
                                        node.lineno,
                                        "CONSTANT-TUNABLE",
                                        f"forbidden tunable constant: {name}",
                                    )
                                )
    assert not violations, (
        "ADR-013 violation — forbidden algorithm constants detected:\n"
        + "\n".join(sorted(violations))
    )


def _is_typing_alias(value_node: ast.AST) -> bool:
    """Return True iff the RHS is a typing-construct that should not be
    classified as an algorithm constant.

    Catches:
      - ``Literal[...]`` (state labels for FSMs — REGIME_STATES, PHASE_STATES, ...)
      - ``Optional[...]``, ``Union[...]``, ``List[...]``, ``Dict[...]``, ``Tuple[...]``
      - ``TypedDict`` (inline class definition is handled separately, not via Assign)
      - direct name references to ``Literal``/``Optional``/``Union`` regardless of subscript
    """
    typing_names = {"Literal", "Optional", "Union", "List", "Dict", "Tuple", "Set", "FrozenSet"}
    # Bare reference: VECTOR_TYPES = Literal
    if isinstance(value_node, ast.Name) and value_node.id in typing_names:
        return True
    # Subscripted: VECTOR_TYPES = Literal["..."]  |  REGIME = Optional[int]
    if isinstance(value_node, ast.Subscript):
        sub = value_node.value
        if isinstance(sub, ast.Name) and sub.id in typing_names:
            return True
    return False


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


def test_ueid_4part_in_sys_ikigai_entities() -> None:
    """UEID in sys_ikigai/entities/ueid.py MUST also be 4-part (B1 fix 2026-09-10).

    Prior to B1 fix, sys_ikigai/entities/ueid.py used a 5-part regex that
    diverged from the canonical 4-part pattern in src/contracts/common.py.
    This caused validation failures when the v2 graph (4-part) emitted
    UEIDs that flowed into agent_consumer.py / tools_mesh.py — they
    imported the 5-part type and rejected everything.

    Per ADR-014 + ueid-5part-canonical-decision-2026-08-31, the canonical
    format is 4-part. sys_ikigai/entities/ueid.py MUST match. This test
    enforces that nobody silently regresses it back to 5-part.
    """
    sys_ueid_path = REPO_ROOT / "sys_ikigai" / "entities" / "ueid.py"
    if not sys_ueid_path.exists():
        pytest.skip(f"{sys_ueid_path} not present")
    source = sys_ueid_path.read_text(encoding="utf-8")

    canonical_pattern = r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$"
    assert canonical_pattern in source, (
        f"sys_ikigai/entities/ueid.py must use 4-part UEID regex per ADR-014. "
        f"Expected pattern: {canonical_pattern!r}. "
        f"Found in {sys_ueid_path}. "
        "B1 fix 2026-09-10: see memory/ikigai-v2-deep-dive-bugs-2026-09-10.md"
    )


def test_v2_state_schema_has_b2_node_fields() -> None:
    """IKIGAiStateDict must declare all v2 node input fields (B2 fix 2026-09-10).

    Prior to B2 fix, the v2 graph nodes (observe, score_vectors,
    heuristics, balance, decompose, tag_and_persist, error) read state
    fields that didn't exist in the schema: `date`, `vectors`, `context`,
    `load`, `task_id`, `ueid`, `error_channel`. `state.get(...)` returned
    None or empty defaults, so the graph ran but produced no useful
    output. This test enforces that the schema documents every field
    nodes actually read.

    If you add a new node that reads a state field, add the field here
    to prevent silent regressions.
    """
    state_path = (
        IKIGAI_SRC / "agents" / "v2" / "state.py"
    )
    if not state_path.exists():
        pytest.skip(f"{state_path} not present")
    source = state_path.read_text(encoding="utf-8")

    required_fields = (
        # v2 node input channels (B2 fix)
        "date: NotRequired[str]",
        "vectors: NotRequired[list[float]]",
        "context: NotRequired[dict[str, Any]]",
        "load: NotRequired[float]",
        "task_id: NotRequired[str | None]",
        "ueid: NotRequired[str | None]",
        "error_channel: NotRequired[Annotated[list[str], operator.add]]",
    )
    missing = [f for f in required_fields if f not in source]
    assert not missing, (
        f"IKIGAiStateDict is missing node input fields added by B2 fix: {missing}. "
        f"Found in {state_path}. "
        "B2 fix 2026-09-10: see memory/ikigai-v2-deep-dive-bugs-2026-09-10.md"
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
# Plan C — Investigation queue drift invariant (h)
# ---------------------------------------------------------------------------


def test_investigation_queue_invariants() -> None:
    """Plan C drift invariant (h): investigation queue structural integrity.

    Asserts:
    1. data/investigation_queue/ exists or can be created (mkdir parents=True).
    2. InvestigationQueue file naming: inq-*.json only (no .tmp, no orphan).
    3. Every JSON file in data/investigation_queue/ validates as Investigation
       (Pydantic v2 strict — frozen, extra=forbid).
    4. No resurrection: terminal states (resolved, archived) cannot transition.

    Note: Audit-log append-only is enforced structurally by the queue helper
    (open(mode='a') in src/mesh/investigation_queue.py). Not re-asserted here
    to keep the drift test deterministic across platforms (Windows file ACLs
    differ from POSIX).
    """
    queue_dir = REPO_ROOT / "data" / "investigation_queue"
    # Invariant 1: directory exists
    queue_dir.mkdir(parents=True, exist_ok=True)
    assert queue_dir.is_dir()

    # Invariant 2: only inq-*.json files (plus .keep marker and audit log)
    for entry in queue_dir.iterdir():
        if entry.name in (".keep", ".investigation_audit.log"):
            continue
        if entry.suffix == ".json":
            assert entry.name.startswith("inq-"), (
                f"unexpected JSON in queue dir: {entry.name} "
                f"(must match inq-*.json or be .keep/.audit_log)"
            )
            # Invariant 3: file validates as Investigation
            from src.contracts.investigation import Investigation

            try:
                Investigation.model_validate_json(entry.read_text(encoding="utf-8"))
            except Exception as exc:
                pytest.fail(f"investigation file failed validation: {entry.name}: {exc}")
        elif ".tmp." in entry.name:
            pytest.fail(f"orphan tmp file in queue: {entry.name}")

    # Invariant 4: terminal-state transitions rejected (uses helper, not queue itself)
    import mesh.investigation_queue as iq_mod
    from mesh.investigation_queue import transition as _transition
    from src.contracts.investigation import Investigation

    # Save original QUEUE_DIR
    original_qd = iq_mod.QUEUE_DIR
    try:
        # Redirect to tmp for this check
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            iq_mod.QUEUE_DIR = Path(td)
            # Create + complete a resolved investigation
            inv = Investigation(
                inq_id="inq-drift-test",
                source="agent",
                payload="drift invariant check",
                created_at=datetime.now(),
                status="resolved",
            )
            iq_mod.enqueue(inv)
            # Try to transition resolved → archived (must fail)
            with pytest.raises(ValueError, match="invalid transition"):
                _transition("inq-drift-test", "archived", "drift-test")
    finally:
        iq_mod.QUEUE_DIR = original_qd


# ---------------------------------------------------------------------------
# W3.5 — ADR-025 skill-binding invariant (R4)
# ---------------------------------------------------------------------------

_SKILLS_DIR = IKIGAI_SRC / "agents" / "v2" / "skills"


@pytest.mark.parametrize(
    "skill_name",
    [
        pytest.param("daily", id="daily"),  # actual filename is daily.md, not ikigai-daily.md
        pytest.param("weekly", id="weekly"),
        pytest.param("monthly", id="monthly"),
        pytest.param("quarterly", id="quarterly"),
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
        pytest.param("weekly", id="weekly"),
        pytest.param("monthly", id="monthly"),
        pytest.param("quarterly", id="quarterly"),
    ],
)
def test_skill_entry_point_is_valid_node(skill_name) -> None:
    """All skill entry_point values MUST be members of VALID_ENTRY_POINTS (ADR-025 R4).

    Post V5-D: graph.py was deleted; the canonical entry-point surface
    is ``VALID_ENTRY_POINTS`` exported from
    ``src/ikigai/src/agents/v2/subagent_types.py`` (see ADR-026 R1).
    """
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

    # Import VALID_ENTRY_POINTS at runtime — canonical entry points
    # (ADR-026 R1, post V5-D).
    from src.ikigai.src.agents.v2.subagent_types import VALID_ENTRY_POINTS

    assert entry_point in VALID_ENTRY_POINTS, (
        f"{skill_name}.md entry_point {entry_point!r} not in VALID_ENTRY_POINTS; "
        f"must be one of {list(VALID_ENTRY_POINTS)}"
    )


@pytest.mark.parametrize(
    "skill_name",
    [
        pytest.param("daily", id="daily"),  # actual filename is daily.md, not ikigai-daily.md
        pytest.param("weekly", id="weekly"),
        pytest.param("monthly", id="monthly"),
        pytest.param("quarterly", id="quarterly"),
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
        f"{skill_name}.md actor must be 'user' or 'agent', got {frontmatter['actor']!r}"
    )


# ---------------------------------------------------------------------------
# W4.4 — ADR-026 sub-agent dispatch drift invariants
# ---------------------------------------------------------------------------


def test_subagent_spec_ueid_validation() -> None:
    """SubAgentSpec.sub_agent_id MUST be validated against the canonical 4-part UEID regex.

    Per ADR-014 + ADR-026 R4: sub-agent IDs are 4-part UEIDs; 5-part is
    REJECTED. The validator lives in src/ikigai/src/agents/v2/subgraph.py.
    This test scans the file for the regex pattern (defensive — exact
    text may shift, but the pattern must remain canonical).
    """
    subgraph_path = IKIGAI_SRC / "agents" / "v2" / "subgraph.py"
    if not subgraph_path.exists():
        pytest.skip(f"{subgraph_path} not present")
    source = subgraph_path.read_text(encoding="utf-8")
    canonical_pattern = r"\^\[a-z\]\{2,5\}:\[a-z0-9-\]\+:\[a-f0-9-\]\+:\[a-f0-9-\]\+\$"
    assert re.search(canonical_pattern, source), (
        f"subgraph.py must validate sub_agent_id against the canonical "
        f"4-part UEID regex (ADR-014 + ADR-026 R4). Expected pattern "
        f"matching: {canonical_pattern}"
    )


# ---------------------------------------------------------------------------
# W4.5 — ADR-027 checkpoint consumer drift invariants
# ---------------------------------------------------------------------------


def test_ikigai_checkpointer_class_exists() -> None:
    """IkigaiCheckpointer MUST exist at agents/v2/checkpoint.py (ADR-027 R13.1).

    Closes the W4.5 implementation deliverable. The checkpointer wraps
    LangGraph's SqliteSaver with WAL PRAGMAs (R8) + 2 schema-control
    tables (R1) + retention (R10). Removing the class without an ADR
    amendment violates ADR-027 R13.1.
    """
    checkpoint_path = IKIGAI_SRC / "agents" / "v2" / "checkpoint.py"
    if not checkpoint_path.exists():
        pytest.skip(f"{checkpoint_path} not present")
    source = checkpoint_path.read_text(encoding="utf-8")
    assert "class IkigaiCheckpointer" in source, (
        f"IkigaiCheckpointer class missing from {checkpoint_path}. "
        f"ADR-027 R13.1 mandates this class at the canonical path."
    )
    # Required public surface per W4.5 brief §"Critical content" item 1.
    for required_symbol in (
        "def __init__",
        "def get_saver",
        "def record_subgraph_link",
        "def get_subgraph_links",
        "def apply_retention",
        "def close",
    ):
        assert required_symbol in source, (
            f"IkigaiCheckpointer missing required method: {required_symbol}"
        )


def test_default_db_filename_matches_adrr027_r135() -> None:
    """_DEFAULT_DB_FILENAME MUST equal 'ikigai_checkpoints.db' (ADR-027 R13.5).

    The DB filename is load-bearing: graph.py:make_v2_graph() resolves
    ``<project_root>/data/{_DEFAULT_DB_FILENAME}`` when no explicit
    checkpoint_db is provided. Renaming it silently breaks the
    default location.
    """
    checkpoint_path = IKIGAI_SRC / "agents" / "v2" / "checkpoint.py"
    if not checkpoint_path.exists():
        pytest.skip(f"{checkpoint_path} not present")
    source = checkpoint_path.read_text(encoding="utf-8")
    assert "_DEFAULT_DB_FILENAME" in source
    # Match the assignment — accept any quote style
    import re

    m = re.search(r'_DEFAULT_DB_FILENAME\s*[:=]\s*["\']ikigai_checkpoints\.db["\']', source)
    assert m, (
        f"_DEFAULT_DB_FILENAME must be exactly 'ikigai_checkpoints.db' "
        f"per ADR-027 R13.5. Source: {source[:500]}"
    )


def test_subgraph_uses_build_subagent_thread_id_from_checkpoint() -> None:
    """subgraph.py MUST import + use build_subagent_thread_id from checkpoint.py.

    Closes the W4.4 reviewer's minor observation: ``_invoke_subagent``
    used ``f"subagent-{sub_agent_id}"`` (legacy format) instead of the
    canonical 4-segment hierarchical thread_id per ADR-027 R3. W4.5
    introduces ``build_subagent_thread_id`` in checkpoint.py and
    subgraph.py MUST consume it.

    The module docstring of subgraph.py still references the legacy
    format in historical context, so we strip docstrings + comments
    before doing the substring check.
    """
    import re as _re

    subgraph_path = IKIGAI_SRC / "agents" / "v2" / "subgraph.py"
    checkpoint_path = IKIGAI_SRC / "agents" / "v2" / "checkpoint.py"
    if not subgraph_path.exists() or not checkpoint_path.exists():
        pytest.skip("subgraph.py or checkpoint.py not present")
    subgraph_source = subgraph_path.read_text(encoding="utf-8")
    checkpoint_source = checkpoint_path.read_text(encoding="utf-8")
    # checkpoint.py MUST export build_subagent_thread_id
    assert "def build_subagent_thread_id" in checkpoint_source, (
        "checkpoint.py must define build_subagent_thread_id (ADR-027 R3)"
    )
    # subgraph.py MUST import it
    assert "from .checkpoint import build_subagent_thread_id" in subgraph_source, (
        "subgraph.py must import build_subagent_thread_id from checkpoint.py "
        "(W4.5 closes W4.4 reviewer minor observation)"
    )
    # Strip triple-quoted strings (docstrings) and single-line comments
    # so legacy references in historical context don't trip the check.
    code_only = _re.sub(r'"""[\s\S]*?"""', "", subgraph_source)
    code_only = _re.sub(r"'''[\s\S]*?'''", "", code_only)
    code_only = _re.sub(r"#.*", "", code_only)
    assert 'f"subagent-{sub_agent_id}"' not in code_only, (
        'Legacy `f"subagent-{sub_agent_id}"` thread_id format found in '
        "subgraph.py CODE — must be replaced with build_subagent_thread_id "
        "(ADR-027 R3, W4.4 reviewer minor observation)"
    )


# ---------------------------------------------------------------------------
# W4.6 — ADR-028 memory layer drift invariants
# ---------------------------------------------------------------------------


def test_memory_schema_version_constant_is_one() -> None:
    """memory_schema.py MUST export MEMORY_SCHEMA_VERSION = 1 (ADR-028 R11).

    Closes the W4.6 implementation deliverable. Removing the constant or
    changing its value silently breaks the schema-versioning contract
    (monotonic, lazy migration on read). Drift detector prevents
    accidental removal.
    """
    memory_schema_path = IKIGAI_SRC / "agents" / "v2" / "memory_schema.py"
    if not memory_schema_path.exists():
        pytest.skip(f"{memory_schema_path} not present")
    source = memory_schema_path.read_text(encoding="utf-8")
    # Module-level assignment — match either `MEMORY_SCHEMA_VERSION = 1` or
    # `MEMORY_SCHEMA_VERSION: int = 1` (annotation form). Strip annotations
    # to make the regex tolerant.
    m = re.search(
        r"^MEMORY_SCHEMA_VERSION\s*[:=]?\s*(?::\s*\w+\s*)?=\s*1\b",
        source,
        re.MULTILINE,
    )
    assert m, (
        f"MEMORY_SCHEMA_VERSION = 1 not found in {memory_schema_path}. "
        "ADR-028 R11 mandates schema_version=1 as the canonical initial version."
    )


def test_memory_schema_module_defines_default_db_filename() -> None:
    """memory_schema.py MUST export MEMORY_DEFAULT_DB_FILENAME = 'ikigai_memory.db' (ADR-028 R1).

    Closes the W4.6 brief §"Critical content" item 1: the canonical DB
    filename is load-bearing — it's distinct from the LangGraph
    checkpoint DB (per ADR-027 R13.5: ikigai_checkpoints.db). The
    canonical on-disk location is
    ``<repo>/data/ikigai_memory.db``.
    """
    memory_schema_path = IKIGAI_SRC / "agents" / "v2" / "memory_schema.py"
    if not memory_schema_path.exists():
        pytest.skip(f"{memory_schema_path} not present")
    source = memory_schema_path.read_text(encoding="utf-8")
    # Match either annotation form or plain assignment.
    m = re.search(
        r'^MEMORY_DEFAULT_DB_FILENAME\s*[:=]?\s*(?::\s*\w+\s*)?=\s*["\']ikigai_memory\.db["\']',
        source,
        re.MULTILINE,
    )
    assert m, (
        f"MEMORY_DEFAULT_DB_FILENAME = 'ikigai_memory.db' not found in "
        f"{memory_schema_path}. ADR-028 R1 mandates this constant as the "
        f"canonical memory DB filename (separate from ikigai_checkpoints.db per ADR-027 R13.5)."
    )


# ---------------------------------------------------------------------------
# Plan D — Meta-planner drift invariants (n, o, p)
# Added 2026-09-04 per docs/superpowers/specs/2026-09-04-meta-planner-design.md
# ---------------------------------------------------------------------------


def test_meta_plan_no_direct_vault_writes() -> None:
    """Invariant (n): meta_plan subgraph nodes NEVER call vault_write directly.

    All writes MUST route through proposal_executor → wrap_vault_write (ADR-029).
    """
    from glob import glob

    nodes = glob("src/ikigai/src/agents/v2/nodes/meta_plan/*.py")
    # If the directory doesn't exist yet, this invariant vacuously passes
    # (the absence of meta_plan nodes is itself correct).
    if not nodes:
        return

    for node in nodes:
        # Skip __init__.py
        if node.endswith("__init__.py"):
            continue
        content = open(node).read()
        # Look for direct vault_write( call without wrap_

        # Match `vault_write(` but not preceded by `wrap_` or `wrap_vault_write`
        # Heuristic: find all `vault_write(` substrings and ensure none
        # appear outside of comments/docstrings/strings we cannot easily
        # detect. Simpler: just forbid the substring `vault_write(` in node
        # code. proposal_executor lives outside meta_plan/ so this check
        # covers only the 3 subgraph nodes (classify/fetch/generate).
        if "vault_write(" in content:
            # Allow if wrapped (defensive — executor may import helper)
            assert "wrap_vault_write" in content, (
                f"{node} calls vault_write( directly. "
                "Per ADR-029 all vault writes MUST route through wrap_vault_write."
            )


def test_meta_plan_approval_required_for_writes() -> None:
    """Invariant (o): proposal_executor MUST assert approval_state == 'approved'
    before executing any write. Prevents accidental auto-execution.
    """
    # Path is relative to src/ikigai (pytest cwd). Earlier draft used a
    # repo-root relative path with redundant "src/ikigai" prefix; corrected
    # post-Plan D shipping (cf353ad).
    executor_path = (
        REPO_ROOT / "src" / "ikigai" / "src" / "agents" / "v2" / "nodes" / "proposal_executor.py"
    )
    if not executor_path.exists():
        # Pre-implementation: invariant vacuously fails so the implementer
        # knows to add the assertion when creating the file.
        pytest.fail(
            "proposal_executor.py does not exist yet. "
            "Invariant (o) requires the executor to assert "
            "state.proposal.approval_state == 'approved' before any write."
        )

    source = executor_path.read_text(encoding="utf-8")
    assert "approval_state == 'approved'" in source or (
        "approval_state" in source and "approved" in source
    ), (
        "proposal_executor.py must assert approval_state == 'approved' "
        "before performing writes. See Plan D Task B.4."
    )


def test_meta_plan_pydantic_v2_strict() -> None:
    """Invariant (p): all proposal-related models are frozen=True, extra='forbid'."""
    from src.ikigai.contracts.proposal import (
        ExecutionReport,
        FolderReadOp,
        HierarchyContext,
        HierarchyMatch,
        IntentClassification,
        MemoryRef,
        Proposal,
        ProposalOperation,
        TaskdogOp,
        Traceability,
        VaultWriteOp,
    )

    for model in [
        IntentClassification,
        Proposal,
        VaultWriteOp,
        TaskdogOp,
        ExecutionReport,
        FolderReadOp,
        MemoryRef,
        HierarchyContext,
        HierarchyMatch,
        ProposalOperation,
        Traceability,
    ]:
        config = model.model_config
        assert config.get("frozen") is True, (
            f"{model.__name__}.model_config.frozen must be True (ADR-009)"
        )
        assert config.get("extra") == "forbid", (
            f"{model.__name__}.model_config.extra must be 'forbid' (ADR-009)"
        )


def test_planning_note_template_exists() -> None:
    """Invariant (m1): planning note template file exists at canonical path.

    Repurposed 2026-09-07 from the SONHO log ritual (which gated Wave 5
    Scenario C and was dropped per
    ``algorithm-gate-dropped-2026-09-03.md``). The template at
    ``vault/ikigai/templates/sonho-log.md`` (filename retained for path
    stability — only the CONTENT was repurposed) is the canonical human→agent
    planning-change channel: frontmatter + 1 ``## Mudança`` section, 1-3
    bullets, friction ≈ zero. The agent layer consumes these when operational.
    """
    template_path = REPO_ROOT / "vault" / "ikigai" / "templates" / "sonho-log.md"
    assert template_path.exists(), (
        f"Planning note template missing at {template_path}."
    )
    content = template_path.read_text(encoding="utf-8")
    # Verify frontmatter + planning-note markers
    assert content.startswith("---"), "Planning note template must have YAML frontmatter"
    assert "type: planning_note" in content, (
        "Planning note template frontmatter must declare type=planning_note"
    )
    assert "## Mudança" in content, (
        "Planning note template missing '## Mudança' section"
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
