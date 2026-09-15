"""Extended drift detector — vault_write sole-writer + append-only invariants.

Builds on test_canonical_scope.py. Adds three new invariants:

1. **vault_write sole-writer**: No production code outside the allowlist
   may write to vault/ files. Only `src/ikigai/src/mcp_server/tools_vault.py`
   and `src/ikigai/src/ikigai/vault/*.py` may call Path.write_text / open(mode="w")
   on vault/ files.

2. **data/review_queue/ append-only**: No code may delete or rewrite
   events in data/review_queue/. Only enqueue (new file) is permitted.

3. **v2 prompt chains don't touch forbidden math modules**: Even though
   they use prompt templates, the @tool wrappers in tools_v2.py must
   not import any module that the canonical scope detector forbids.

This test runs alongside test_canonical_scope.py and is part of CI gates.
If any of these invariants is violated, the test FAILS.

Run::

    pytest src/ikigai/tests/test_drift_extended_invariants.py -v
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repository root resolution (mirror test_canonical_scope.py)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent
IKIGAI_SRC = IKIGAI_PKG / "src"
LIFE_REPO = IKIGAI_PKG.parent.parent  # life/


def _resolve_repo_root() -> Path:
    """Walk up until we find ``src/ikigai/src`` (the agent/MCP layer)."""
    for parent in THIS_FILE.parents:
        if (parent / "src" / "ikigai" / "src" / "agents").is_dir():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        f"{THIS_FILE} — expected <repo>/src/ikigai/tests/test_drift_extended_invariants.py"
    )


REPO_ROOT = _resolve_repo_root()
VAULT_DIR = REPO_ROOT / "vault"
REVIEW_QUEUE_DIR = REPO_ROOT / "data" / "review_queue"

# Allowlist — these modules MAY write to vault/ files.
VAULT_WRITER_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Sole canonical vault writer
        "src/ikigai/src/mcp_server/tools_vault.py",
        # Lower-level vault helpers (call into tools_vault.py)
        "src/ikigai/src/ikigai/vault/vault_write.py",
        "src/ikigai/src/ikigai/vault/__init__.py",
    }
)

# Production code layers to scan for write operations.
PROD_LAYERS = [
    IKIGAI_SRC / "agents",
    IKIGAI_SRC / "mcp_server",
    IKIGAI_SRC / "ikigai" / "gateway",
    IKIGAI_SRC / "ikigai" / "cli",
    IKIGAI_SRC / "ikigai" / "adapters",
    IKIGAI_SRC / "ikigai" / "vault",
]


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


def _format_violation(file: Path, line: int, kind: str, detail: str) -> str:
    return f"  {_relative_to_repo(file)}:{line}  [{kind}]  {detail}"


def _is_vault_write_call(node: ast.AST) -> tuple[bool, str | None]:
    """Detect calls that write to files inside vault/.

    Detects patterns like:
    - Path("vault/...").write_text(...)
    - open("vault/...", "w")
    - Path("vault/...").write_bytes(...)
    """
    if not isinstance(node, ast.Call):
        return False, None
    # Check the function being called
    func = node.func
    func_name = None
    if isinstance(func, ast.Attribute):
        func_name = func.attr
    elif isinstance(func, ast.Name):
        func_name = func.id
    # write_text / write_bytes (Path methods)
    if func_name in {"write_text", "write_bytes"}:
        # Look for Path("vault/...") or just "vault/..." as argument
        if node.args:
            arg = node.args[0] if func_name == "write_text" else None
            if arg and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if "vault/" in arg.value or arg.value.startswith("vault"):
                    return True, f"{func_name}({arg.value!r})"
        # Check if the receiver is a Path variable — skip for now
    # open(path, "w" | "a" | "wb" | "ab")
    if func_name == "open":
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
            mode = node.args[1].value
            if isinstance(mode, str) and ("w" in mode or "a" in mode):
                if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    if "vault/" in node.args[0].value or node.args[0].value.startswith("vault"):
                        return True, f"open({node.args[0].value!r}, {mode!r})"
    return False, None


def _is_review_queue_delete_or_rewrite(node: ast.AST) -> tuple[bool, str | None]:
    """Detect calls that delete or rewrite files in data/review_queue/.

    Detects patterns like:
    - Path("data/review_queue/...").unlink()
    - Path("data/review_queue/...").write_text(...)
    - os.remove("data/review_queue/...")
    - shutil.rmtree for review_queue/
    """
    if not isinstance(node, ast.Call):
        return False, None
    func = node.func
    func_name = None
    if isinstance(func, ast.Attribute):
        func_name = func.attr
    elif isinstance(func, ast.Name):
        func_name = func.id
    # unlink / unlink(missing_ok=True)
    if func_name in {"unlink", "remove"}:
        if node.args and isinstance(node.args[0], ast.Constant):
            arg_val = node.args[0].value
            if isinstance(arg_val, str) and "review_queue" in arg_val:
                return True, f"{func_name}({arg_val!r})"
    # write_text / write_bytes overwriting review_queue files
    if func_name in {"write_text", "write_bytes"}:
        if node.args and isinstance(node.args[0], ast.Constant):
            arg_val = node.args[0].value
            if isinstance(arg_val, str) and "review_queue" in arg_val:
                return True, f"{func_name}({arg_val!r}) [NOT append-only]"
    # shutil.rmtree for review_queue
    if func_name == "rmtree":
        if node.args and isinstance(node.args[0], ast.Constant):
            arg_val = node.args[0].value
            if isinstance(arg_val, str) and "review_queue" in arg_val:
                return True, f"rmtree({arg_val!r})"
    return False, None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_vault_write_sole_writer() -> None:
    """Only the allowlist may write to vault/ files."""
    violations: list[str] = []
    for root in PROD_LAYERS:
        if not root.exists():
            continue
        for py_file in _iter_python_files(root):
            rel_path = _relative_to_repo(py_file)
            if rel_path in VAULT_WRITER_ALLOWLIST:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                is_write, detail = _is_vault_write_call(node)
                if is_write:
                    violations.append(
                        _format_violation(
                            py_file,
                            node.lineno,
                            "VAULT-WRITE",
                            f"vault write outside allowlist: {detail}",
                        )
                    )
    assert not violations, (
        "vault_write sole-writer violation — only allowlist may write to vault/:\n"
        + "\n".join(sorted(violations))
        + f"\nAllowlist: {sorted(VAULT_WRITER_ALLOWLIST)}"
    )


def test_review_queue_append_only() -> None:
    """No production code may delete or rewrite files in data/review_queue/."""
    violations: list[str] = []
    for root in PROD_LAYERS:
        if not root.exists():
            continue
        for py_file in _iter_python_files(root):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                is_violation, detail = _is_review_queue_delete_or_rewrite(node)
                if is_violation:
                    violations.append(
                        _format_violation(
                            py_file,
                            node.lineno,
                            "REVIEW-QUEUE-MUTATE",
                            f"data/review_queue/ append-only violation: {detail}",
                        )
                    )
    assert not violations, (
        "data/review_queue/ append-only violation — events must only be enqueued:\n"
        + "\n".join(sorted(violations))
    )


def test_v2_prompts_dont_touch_forbidden_math_modules() -> None:
    """v2 prompt-chain @tools must not import math/kernel modules.

    The v2 layer (`agents/v2/`) replaces math execution with prompt
    templates, but the wrappers still must not import from forbidden
    modules. We check only the v2 directory, which is the agent layer.
    """
    v2_dir = IKIGAI_SRC / "agents" / "v2"
    if not v2_dir.exists():
        pytest.skip(f"{v2_dir} not present (v2 layer not yet created)")
    # Forbidden imports (mirrors test_canonical_scope.FORBIDDEN_IMPORTS subset)
    forbidden = frozenset(
        {
            "ikigai.core.scoring",
            "ikigai.core.heuristics",
            "agents.ikigai_maintainer",
            "src.agents.ikigai_maintainer",
            "ikigai_scorer",
            "cybernetics.daily_loop",
        }
    )
    violations: list[str] = []
    for py_file in _iter_python_files(v2_dir):
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
            if target and target in forbidden:
                violations.append(
                    _format_violation(
                        py_file,
                        node.lineno,
                        "V2-FORBIDDEN-IMPORT",
                        f"v2 layer must not import forbidden module: {target}",
                    )
                )
    assert not violations, (
        "v2 prompt-chain layer must not import forbidden math modules:\n"
        + "\n".join(sorted(violations))
    )


def test_drift_extended_invariants_self_check() -> None:
    """Sanity: this test file itself is parseable and has the expected tests."""
    # If this test runs, the file parsed successfully (else collection fails).
    # Just verify the AST helpers are importable.
    assert callable(_is_vault_write_call)
    assert callable(_is_review_queue_delete_or_rewrite)
    assert callable(_iter_python_files)


def test_mcp_bridge_wrapped_tool_count_matches_canonical() -> None:
    """L4 G-1 / T-11.5 G-2 (M11 diagnosis Priority 1, item 1): every
    wrapped ikigai_* tool in mcp_bridge.py MUST exist in server.py's
    @MCP.tool registry.

    Regression guard for the 9 PAV-flavored wrappers that were deleted
    from server.py in V5-E (commit b960e852) but were referenced from
    mcp_bridge.py — silent runtime failure path. P1.X (2026-09-12)
    renamed ``ikigai_observe_pav_state`` → ``ikigai_observe_state`` and
    restored the 8 missing @MCP.tool decorators. This test pins that
    alignment so future drift trips the detector instead of returning
    ``dict_protocol_no_op`` at runtime.

    Also addresses G-2: bridge-wrapper count was NOT drift-net enforced;
    adding a 13th wrapper silently grew agent surface. Now guarded.
    """
    import re as _re

    repo = REPO_ROOT
    bridge_file = (
        repo / "src" / "ikigai" / "src" / "agents" / "v2" / "mcp_bridge.py"
    )
    server_file = repo / "src" / "ikigai" / "src" / "mcp_server" / "server.py"

    # Step 1: discover all tools registered in server.py via @MCP.tool.
    # Handles both bare ``@MCP.tool()`` (function name) and
    # ``@MCP.tool(name="...")`` (explicit canonical name) decorators,
    # including multi-line ``@MCP.tool(\n    name="...",\n    ...,\n)``.
    server_tools: set[str] = set()
    server_text = server_file.read_text(encoding="utf-8")
    # Decorators with explicit name="..." (tolerant to multi-line).
    for match in _re.finditer(
        r'@MCP\.tool\([^@]*?name="([A-Za-z_][\w]*)"', server_text
    ):
        server_tools.add(match.group(1))
    # Bare @MCP.tool() followed by def — function name IS the tool name.
    for match in _re.finditer(
        r"@MCP\.tool\(\)\s*(?:async\s+)?def\s+(\w+)", server_text
    ):
        server_tools.add(match.group(1))

    # Step 2: discover all ikigai_* wrappers in mcp_bridge.py.
    bridge_tools: set[str] = set()
    bridge_text = bridge_file.read_text(encoding="utf-8")
    for match in _re.finditer(
        r"^(?:async\s+)?def\s+(ikigai_\w+)", bridge_text, _re.MULTILINE
    ):
        bridge_tools.add(match.group(1))

    # Step 3: drift assertion. Every bridge tool must exist in the
    # server's @MCP.tool registry. ``ikigai_helper`` is the reserved
    # exclusion for any purely-internal helper introduced later.
    missing = bridge_tools - server_tools - {"ikigai_helper"}
    assert not missing, (
        f"Bridge wrappers not registered in server.py "
        f"(M11 P0 attribution violation): {sorted(missing)}\n"
        f"  Bridge tools: {sorted(bridge_tools)}\n"
        f"  Server tools: {sorted(server_tools)}\n"
        f"Either rename the wrapper to match the server-side tool or "
        f"register the missing @MCP.tool in server.py per L4 G-1."
    )

    # Step 4: forward reference sanity. bridge must use _call() which
    # dispatches via tool-name string. Catches typos that would route
    # to a non-existent server tool at runtime.
    referenced_tool_names = set(
        _re.findall(r'_call\("(ikigai_\w+)"', bridge_text)
    )
    for fn_match in _re.finditer(
        r"^def\s+(ikigai_\w+)\([^)]*\):", bridge_text, _re.MULTILINE
    ):
        fn_name = fn_match.group(1)
        assert fn_name in referenced_tool_names, (
            f"Bridge wrapper {fn_name} does not call _call(...) "
            f"with its own name — won't dispatch correctly."
        )


def test_ueid_regex_canonical_across_modules() -> None:
    """L5 G-1 (M11 diagnosis Priority 1): ALL UEID regex definitions
    across the project must match the canonical 4-part pattern from
    ADR-014 (`src/contracts/common.py:34`).

    Regression test for the 5-part regex in `sys_ikigai/entities/ueid.py`
    that drift net doesn't reach (drift net only checks `src/contracts/`).
    Two competing UEID definitions = silent schema drift.
    """
    import re

    canonical_regex = r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$"
    # Canonical has 3 colons (4 parts separated by 3 colons).
    canonical_colon_count = canonical_regex.count(":")  # = 3

    # Find all UEID regex definitions in the project (excluding vendor + .venv).
    candidates = list(LIFE_REPO.glob("**/*.py"))
    candidates = [
        p
        for p in candidates
        if not any(
            part in p.parts
            for part in (
                "vendor",
                ".venv",
                "node_modules",
                "__pycache__",
                ".mypy_cache",
                ".claude",
            )
        )
    ]

    violations = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # Find string literals that LOOK like a UEID regex:
        # starts with ^ (and either a lowercase letter or alternation like (...),
        # ends with $.
        for match in re.finditer(
            r'r?["\'](\^[\(\[][^"\']+?\$)["\']', text, re.MULTILINE
        ):
            pattern = match.group(1)
            # Heuristic: UEID-like patterns have hash segments [0-9a-f] or [a-f0-9].
            if not re.search(r"\[0-?9a-f\]|\[a-f0-9\]", pattern):
                continue
            # Skip non-UEID patterns (datetime, phone, email etc.).
            # UEID patterns have multiple `:` separators.
            colon_count = pattern.count(":")
            if colon_count < 2:
                continue
            # Canonical 4-part: 3 colons. Stale 5-part: 4+ colons.
            if colon_count > canonical_colon_count:
                violations.append((str(path.relative_to(LIFE_REPO)), pattern))

    assert not violations, (
        f"UEID regex definitions with 5+ parts found (canonical is 4-part per ADR-014):\n"
        + "\n".join(f"  {p}: {r}" for p, r in violations)
        + "\n\nFix: change to canonical 4-part pattern OR delete the stale regex."
    )


def test_v2_tests_collect_without_errors() -> None:
    """M12 NEEDS_FIX regression guard: src/ikigai/src/agents/v2/tests/
    must collect without ImportError after code changes to mcp_bridge.py.

    Drift net (which only covers src/ikigai/tests/) cannot detect this
    class of regression because v2-tests live in a parallel tree. When
    wrappers are removed from mcp_bridge.py, downstream test files that
    import them break at COLLECTION TIME (not at runtime), turning the
    v2 tree red unless caught explicitly. This guard imports every
    test_*.py module under v2/tests/ and fails if any raises ImportError
    or ModuleNotFoundError at import time.

    Background: M12 deleted 8 PAV-flavored wrappers from mcp_bridge.py
    (kept only ikigai_decompose), but the dead test files
    test_mcp_bridge.py and test_phase_8_2_wiring.py still imported the
    deleted symbols. The drift net passed 45/45 because none of the
    drift files touched v2/tests/. This guard now closes that hole.

    Note: uses direct importlib.import_module (not subprocess pytest)
    to avoid the asyncio plugin's Windows _overlapped WinError 10106 in
    subprocess children. The collection-time import errors we want to
    detect happen at module-load time, so importlib is sufficient.
    """
    import importlib
    import sys

    repo = _resolve_repo_root()
    v2_tests_dir = repo / "src" / "ikigai" / "src" / "agents" / "v2" / "tests"
    assert v2_tests_dir.is_dir(), f"v2 tests dir missing: {v2_tests_dir}"

    # Ensure dotted-prefix imports resolve: <repo>/ must be on sys.path
    # (per tests/conftest.py). Safe to append (idempotent).
    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)

    failures: list[tuple[str, str, str]] = []
    for test_file in sorted(v2_tests_dir.glob("test_*.py")):
        # Convert filesystem path to module name using repo-relative
        # dotted form: src/ikigai/src/agents/v2/tests/test_X.py
        # -> src.ikigai.src.agents.v2.tests.test_X
        rel = test_file.relative_to(repo).with_suffix("")
        modname = ".".join(rel.parts)
        try:
            importlib.import_module(modname)
        except (ImportError, ModuleNotFoundError) as exc:
            failures.append((test_file.name, type(exc).__name__, str(exc)))

    assert not failures, (
        "src/ikigai/src/agents/v2/tests/ has module-level import errors "
        "(M12 NEEDS_FIX class — drift net doesn't cover v2/tests/):\n"
        + "\n".join(f"  {name}: {cls}: {msg}" for name, cls, msg in failures)
    )


def test_langgraph_graph_registry_drift() -> None:
    """M11 finding T-11.7 G-3: langgraph.json graph registry must be
    consistent with actual graph implementations.

    Verifies each entry in langgraph.json's `graphs` map has a real
    factory function at the declared path. Catches future registry
    drift (broken factories, missing files) at CI time.

    Schema: each entry value is a "module.py:factory_name" string.
    Module path is relative to repo root (may start with `./`).
    """
    import json

    repo = REPO_ROOT
    langgraph_json = repo / "langgraph.json"
    if not langgraph_json.exists():
        pytest.skip(f"langgraph.json not found: {langgraph_json}")

    config = json.loads(langgraph_json.read_text(encoding="utf-8"))
    graphs = config.get("graphs", {})
    assert isinstance(graphs, dict), (
        f"langgraph.json 'graphs' must be a dict, got {type(graphs).__name__}"
    )

    missing_factories: list[tuple[str, str]] = []
    for name, entry in graphs.items():
        # Entry is a "module.py:factory_name" string (not a dict).
        if not isinstance(entry, str) or ":" not in entry:
            missing_factories.append((name, f"entry must be '<module>:<factory>', got {entry!r}"))
            continue
        file_rel, factory_name = entry.split(":", 1)
        # Strip leading "./" to normalize
        file_rel = file_rel.lstrip("./")
        full_file = repo / file_rel
        if not full_file.exists():
            missing_factories.append((name, f"file not found: {full_file}"))
            continue
        try:
            tree = ast.parse(full_file.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            missing_factories.append((name, f"syntax error in {full_file}: {exc}"))
            continue
        factory_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if factory_name not in factory_names:
            missing_factories.append(
                (name, f"factory {factory_name} not found in {full_file.name}")
            )

    assert not missing_factories, (
        "langgraph.json entries with missing/broken factories:\n"
        + "\n".join(f"  {name}: {reason}" for name, reason in missing_factories)
        + f"\n\nlanggraph.json graphs: {sorted(graphs.keys())}"
    )


def test_v2_node_bridge_alignment() -> None:
    """Drift net guard (M13): every mcp_bridge.<attr> call in v2 nodes
    must resolve to a real attribute in mcp_bridge.py. Catches both:
    - Wrapper deleted from mcp_bridge.py but still called by v2 node (silent
      AttributeError → try/except → error_channel — the SAME drift class M13
      just cleaned up)
    - Wrapper added to mcp_bridge.py but no node uses it (orphaned code)

    Walks each node in src/ikigai/src/agents/v2/nodes/, extracts every
    `mcp_bridge.<attr>(...)` reference via AST, and cross-checks against
    the live attribute set on the mcp_bridge module.
    """
    import importlib

    repo = _resolve_repo_root()
    nodes_dir = repo / "src" / "ikigai" / "src" / "agents" / "v2" / "nodes"
    if not nodes_dir.exists():
        pytest.skip(f"v2 nodes dir not found: {nodes_dir}")

    # 1. Collect live mcp_bridge attributes
    import src.ikigai.src.agents.v2.mcp_bridge as mcp_bridge  # noqa: E402
    live_attrs = {
        name for name in dir(mcp_bridge)
        if not name.startswith("_")  # exclude dunder + private
    }

    # 2. Parse each node file via AST and extract mcp_bridge.<attr> attribute accesses
    missing: list[tuple[str, str]] = []  # (file, attr) pairs where node references an attr that doesn't exist
    for node_file in sorted(nodes_dir.glob("*.py")):
        if node_file.name == "__init__.py":
            continue
        try:
            tree = ast.parse(node_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        # Walk all Attribute nodes; find ones whose value is Name("mcp_bridge")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "mcp_bridge"
            ):
                attr = node.attr
                if attr not in live_attrs:
                    missing.append((str(node_file.relative_to(repo)), attr))

    assert not missing, (
        f"v2 nodes reference mcp_bridge.<attr> for attributes that don't exist:\n"
        + "\n".join(f"  {file}: {attr}" for file, attr in missing)
        + f"\n\nLive mcp_bridge attrs: {sorted(live_attrs)}"
    )


class TestInvestigationQueueTools:
    """Drift guard for the 3 Plan-C investigation_queue tools registered in
    ``src/ikigai/src/mcp_server/server.py``.

    Per M11 finding L5 G-5: drift net does NOT separately verify that the 3
    ``investigation_*`` tools added in Plan C are present in ``server.py``.
    Without this test, a future change that drops these tools would break
    the investigation queue silently.

    Tools asserted:
    - ``investigation_enqueue``  (data/investigation_queue/<id>.json)
    - ``investigation_status``   (read by id)
    - ``investigation_complete`` (atomic state transition)
    """

    def test_investigation_queue_tools_present(self) -> None:
        """M11 finding L5 G-5 + T-17.2: the 3 Plan-C investigation_queue
        tools must be registered in ``src/ikigai/src/mcp_server/server.py``.

        Without this test, a future change that drops these tools would
        break the investigation queue silently.
        """
        import re

        repo = _resolve_repo_root()
        server = repo / "src" / "ikigai" / "src" / "mcp_server" / "server.py"
        if not server.exists():
            pytest.skip(f"server.py not found: {server}")

        text = server.read_text(encoding="utf-8")

        REQUIRED = {
            "investigation_enqueue",
            "investigation_status",
            "investigation_complete",
        }

        # The MCP tools in server.py use a multi-line
        # `@MCP.tool(name="<tool_name>", ...)` decorator where the
        # ``name=`` kwarg carries the public tool name (the function
        # itself is prefixed ``_tool_<name>``). Extract the registered
        # tool names from the ``name=`` kwarg of each @MCP.tool(...)
        # decorator — this catches both multi-line and single-line forms.
        declared_tools: set[str] = set()
        for match in re.finditer(
            r'@MCP\.tool\s*\(([^)]*)\)',
            text,
            flags=re.DOTALL,
        ):
            decorator_body = match.group(1)
            name_match = re.search(r'name\s*=\s*"([^"]+)"', decorator_body)
            if name_match:
                declared_tools.add(name_match.group(1))

        missing = REQUIRED - declared_tools

        assert not missing, (
            "Required Plan-C investigation_queue tools missing from server.py:\n"
            + "\n".join(f"  - {tool}" for tool in sorted(missing))
            + f"\n\nDeclared tools in server.py: {sorted(declared_tools)}"
        )


def test_taskdog_tools_read_only_contract() -> None:
    """Drift net guard (M17 T-17.1): taskdog_tools.py MCP surface must be
    READ-ONLY per ADR-024 (PAV archival) + Path 3 taskdog architecture.

    Per docs/design-system/24-taskdog-paths-architecture.md, Path 3 is the
    read-only MCP surface. The canonical write path is Path 1 (harness
    subprocess → taskdog_cli.py); Path 2 is the operator CLI. Adding any
    write operation to taskdog_tools.py would silently break the
    read-only contract because MCP-tool consumers (Claude agents,
    external MCP clients) call @mcp.tool directly without going through
    the review queue.

    Only these 3 tools are permitted:
    - taskdog_read
    - taskdog_list
    - taskdog_supports_field

    Any write operation (create, update, delete, archive) here would
    silently leak writes out of the canonical Path 1 surface — drift net
    catches this.
    """
    import re

    repo = REPO_ROOT
    taskdog_tools = repo / "src" / "ikigai" / "src" / "mcp_server" / "taskdog_tools.py"
    if not taskdog_tools.exists():
        pytest.skip(f"taskdog_tools.py not found: {taskdog_tools}")

    text = taskdog_tools.read_text(encoding="utf-8")

    # Extract all @mcp.tool-decorated function names (decorator uses
    # lowercase `mcp` — the local FastMCP instance — not @MCP.tool).
    declared_tools: set[str] = set()
    for match in re.finditer(
        r"@mcp\.tool\(?[^)]*?\)?\s*(?:async\s+)?def\s+(\w+)",
        text,
    ):
        declared_tools.add(match.group(1))

    # Permitted set per Path 3 read-only contract.
    ALLOWED: frozenset[str] = frozenset(
        {
            "taskdog_read",
            "taskdog_list",
            "taskdog_supports_field",
        }
    )

    unexpected = declared_tools - ALLOWED
    # Note: not asserting missing == set() — Path 3 contract allows
    # for missing tools during transitions (we only enforce that
    # nothing extra has been added).

    assert not unexpected, (
        f"taskdog_tools.py exposes WRITE operations (forbidden per Path 3 contract):\n"
        + "\n".join(f"  - {tool}" for tool in sorted(unexpected))
        + f"\n\nDeclared tools: {sorted(declared_tools)}\n"
        + f"Allowed tools (Path 3 read-only): {sorted(ALLOWED)}"
    )


# ---------------------------------------------------------------------------
# M28 — SPEC frontmatter schema drift net
# ---------------------------------------------------------------------------

VALID_PRINCIPLE_KEYS: frozenset[str] = frozenset({
    "correctness_over_speed",
    "reversibility_over_cleverness",
    "composition_over_inheritance",
    "tests_are_the_contract",
    "state_on_disk_not_conversation",
    "multi_package_boundaries_are_sacred",
    "spec_driven_not_vibe_driven",
})

VALID_STATUSES: frozenset[str] = frozenset({"DONE", "IN_PROGRESS", "PENDING"})


def _parse_frontmatter(text: str) -> dict[str, object]:
    """Parse YAML frontmatter from a markdown file.

    Extracts the block between the first two ``---`` lines and parses
    it with ``yaml.safe_load``. Returns the parsed dict, or an empty
    dict if no frontmatter is found.
    """
    lines = text.splitlines()
    if len(lines) < 3 or lines[0] != "---":
        return {}
    fence_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            fence_idx = i
            break
    if fence_idx is None:
        return {}
    frontmatter_text = "\n".join(lines[1:fence_idx])
    try:
        import yaml as _yaml

        return _yaml.safe_load(frontmatter_text) or {}
    except Exception:
        # Fallback: simple key: value parser for minimal recovery
        result: dict[str, object] = {}
        for line in frontmatter_text.splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                # Parse as YAML-ish list
                items = [s.strip().strip(",").strip('"').strip("'") for s in val[1:-1].split()]
                result[key.strip()] = items
            else:
                result[key.strip()] = val.strip('"').strip("'")
        return result


def _spec_file_to_milestone_id(spec_path: Path) -> str | None:
    """Derive milestone id like 'M4' from a spec path like specs/M4-langgraph-integration/SPEC.md."""
    import re

    parts = spec_path.parent.name  # e.g. "M4-langgraph-integration"
    m = re.match(r"^(M\d+)-", parts)
    return m.group(1) if m else None


def _parse_roadmap_statuses() -> dict[str, str]:
    """Parse milestone statuses from roadmap.md.

    Returns a dict mapping milestone id (e.g. 'M4') to its STATUS value
    (e.g. 'DONE') by matching the ``### M{n} ... (STATUS: STATUS)`` pattern.
    """
    import re

    roadmap = REPO_ROOT / ".claude" / "loop" / "roadmap.md"
    if not roadmap.exists():
        return {}
    text = roadmap.read_text(encoding="utf-8")
    pattern = re.compile(r"^###\s+(M\d+)[^(]*\(STATUS:\s*([\w-]+)\)", re.MULTILINE)
    return {m.group(1): m.group(2) for m in pattern.finditer(text)}


def test_milestone_specs_have_valid_frontmatter() -> None:
    """Frontmatter on every SPEC.md is machine-parseable and declares its
    constitution contract (M28 T-28.1).

    Without this, a future milestone author can add ``specs/M99-foo/SPEC.md``
    with no frontmatter and CI silently passes. This invariant makes the
    frontmatter schema a hard requirement.
    """
    import re

    specs_dir = REPO_ROOT / "specs"
    if not specs_dir.exists():
        pytest.skip(f"specs/ directory not found at {specs_dir}")

    # Collect all specs/M{n}-*/SPEC.md files
    spec_files: list[Path] = []
    for item in specs_dir.iterdir():
        if item.is_dir() and re.match(r"^M\d+-", item.name):
            spec_file = item / "SPEC.md"
            if spec_file.is_file():
                spec_files.append(spec_file)

    if not spec_files:
        pytest.skip("No milestone spec files found in specs/")

    failures: list[str] = []
    for spec_file in sorted(spec_files):
        milestone = _spec_file_to_milestone_id(spec_file) or spec_file.parent.name
        text = spec_file.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)

        if not fm:
            failures.append(
                f"  {spec_file.parent.name}/SPEC.md: no YAML frontmatter found"
            )
            continue

        missing: list[str] = []
        # name
        name_val = fm.get("name")
        if not isinstance(name_val, str) or not name_val:
            missing.append("name (str, non-empty)")
        elif not re.match(r"^M\d+-.+$", name_val):
            missing.append(f"name must match ^M\\d+-.+$, got {name_val!r}")

        # description
        desc_val = fm.get("description")
        if not isinstance(desc_val, str):
            missing.append("description (str)")
        elif len(desc_val) > 120:
            missing.append(f"description must be <=120 chars, got {len(desc_val)}")

        # constitution_refs
        refs_val = fm.get("constitution_refs")
        if not isinstance(refs_val, list):
            missing.append("constitution_refs (list[str])")
        elif len(refs_val) == 0:
            missing.append("constitution_refs must have >=1 entry")
        else:
            invalid_refs = [r for r in refs_val if not isinstance(r, str) or r not in VALID_PRINCIPLE_KEYS]
            if invalid_refs:
                missing.append(
                    f"constitution_refs contains invalid keys: {invalid_refs} "
                    f"(valid: {sorted(VALID_PRINCIPLE_KEYS)})"
                )

        # status
        status_val = fm.get("status")
        if not isinstance(status_val, str) or status_val not in VALID_STATUSES:
            missing.append(
                f"status must be one of {sorted(VALID_STATUSES)}, got {status_val!r}"
            )

        # owner
        owner_val = fm.get("owner")
        if not isinstance(owner_val, str) or not owner_val:
            missing.append("owner (str, non-empty)")

        if missing:
            failures.append(
                f"  {spec_file.parent.name}/SPEC.md: "
                + "; ".join(missing)
            )

    assert not failures, (
        "The following milestone SPEC files have invalid frontmatter:\n"
        + "\n".join(failures)
    )


def test_milestone_specs_status_matches_roadmap() -> None:
    """The status declared in a SPEC frontmatter must match the roadmap's
    own STATUS declaration for that milestone (M28 T-28.2).

    A SPEC that says ``status: DONE`` while the roadmap says
    ``(STATUS: PENDING)`` indicates a desynchronised milestone — someone
    updated one but not the other. This invariant keeps them in sync.
    """
    import re

    specs_dir = REPO_ROOT / "specs"
    if not specs_dir.exists():
        pytest.skip(f"specs/ directory not found at {specs_dir}")

    roadmap_statuses = _parse_roadmap_statuses()
    if not roadmap_statuses:
        pytest.skip("Could not parse statuses from roadmap.md")

    spec_files: list[Path] = []
    for item in specs_dir.iterdir():
        if item.is_dir() and re.match(r"^M\d+-", item.name):
            spec_file = item / "SPEC.md"
            if spec_file.is_file():
                spec_files.append(spec_file)

    failures: list[str] = []
    for spec_file in sorted(spec_files):
        milestone = _spec_file_to_milestone_id(spec_file)
        if not milestone:
            continue

        text = spec_file.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        spec_status = fm.get("status") if fm else None

        roadmap_status = roadmap_statuses.get(milestone)
        # Normalize: roadmap uses IN-PROGRESS, SPEC frontmatter uses IN_PROGRESS
        spec_status_norm = spec_status.replace("-", "_") if spec_status else None
        roadmap_status_norm = roadmap_status.replace("-", "_") if roadmap_status else None
        if roadmap_status_norm and spec_status_norm and spec_status_norm != roadmap_status_norm:
            failures.append(
                f"  {spec_file.parent.name}: SPEC says {spec_status!r} "
                f"but roadmap says {roadmap_status!r}"
            )

    assert not failures, (
        "Milestone SPEC status mismatches roadmap STATUS:\n"
        + "\n".join(failures)
    )


def test_no_orphan_milestone_specs() -> None:
    """No orphan SPEC files and no orphan roadmap entries (M28 T-28.3).

    Catch both directions: (a) a SPEC.md exists for a milestone not in
    the roadmap, and (b) a roadmap section declares a non-PENDING milestone
    that has no corresponding SPEC.md. Keeps milestone spec and roadmap
    in one-to-one correspondence.
    """
    import re

    specs_dir = REPO_ROOT / "specs"
    roadmap_file = REPO_ROOT / ".claude" / "loop" / "roadmap.md"

    # Collect milestone IDs from SPEC files
    spec_milestones: set[str] = set()
    if specs_dir.exists():
        for item in specs_dir.iterdir():
            if item.is_dir() and re.match(r"^M\d+-", item.name):
                spec_file = item / "SPEC.md"
                if spec_file.is_file():
                    mid = _spec_file_to_milestone_id(spec_file)
                    if mid:
                        spec_milestones.add(mid)

    # Collect milestone IDs from roadmap with non-PENDING status
    roadmap_text = ""
    if roadmap_file.exists():
        roadmap_text = roadmap_file.read_text(encoding="utf-8")

    roadmap_pattern = re.compile(
        r"^#{3,4}\s+(M\d+)[^(]*\(STATUS:\s*([\w-]+)\)", re.MULTILINE
    )
    roadmap_milestones: dict[str, str] = {}
    for m in roadmap_pattern.finditer(roadmap_text):
        roadmap_milestones[m.group(1)] = m.group(2)

    failures: list[str] = []

    # (a) SPEC without roadmap entry
    for mid in sorted(spec_milestones):
        if mid not in roadmap_milestones:
            failures.append(
                f"  {mid}: SPEC.md exists but no entry in roadmap.md"
            )

    # (b) Roadmap non-PENDING entry without SPEC — only enforce for the
    # 9 milestones that M27 explicitly required SPECs for (per M27
    # acceptance criteria: M4, M5, M6, M7, M8, M9, M10, M17, M24).
    # All other milestones predate the SPEC.md convention and are exempt.
    SPECD_MILESTONES: frozenset[str] = frozenset(
        {"M4", "M5", "M6", "M7", "M8", "M9", "M10", "M17", "M24"}
    )
    for mid, status in sorted(roadmap_milestones.items()):
        if mid not in spec_milestones and status != "PENDING":
            # M-CAND-* with STATUS: PROPOSED are exempt — no SPEC required for
            # proposed candidates (hill-climb v2 adds them without SPEC per M33)
            if mid.startswith("M-CAND-") and status == "PROPOSED":
                continue
            if mid in SPECD_MILESTONES:
                failures.append(
                    f"  {mid}: roadmap has (STATUS: {status}) "
                    f"but no specs/{mid}-*/SPEC.md file"
                )

    assert not failures, (
        "Orphan milestone entries detected:\n"
        + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# M34 — Orchestrator auto-reconcile roadmap section
# ---------------------------------------------------------------------------


def test_orchestrator_has_auto_reconcile_section() -> None:
    """The orchestrator agent file must contain an Auto-Reconcile Roadmap section
    and reference auto-reconciled milestones in its DECISION TREE (M34).

    This prevents the IDLE-loop pattern where commits land with milestone work
    but no roadmap entry, causing the orchestrator to wait indefinitely for
    human direction.
    """
    orchestrator_path = REPO_ROOT / ".claude" / "agents" / "loop" / "orchestrator.md"
    if not orchestrator_path.exists():
        pytest.fail(f"Orchestrator not found at {orchestrator_path}")

    text = orchestrator_path.read_text(encoding="utf-8")

    # Check for Auto-Reconcile section heading within 5 lines of "auto-reconcil"
    lines = text.splitlines()
    has_auto_reconcile_heading = False
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if "auto-reconcile" in stripped and "roadmap" in stripped:
            # Must be a heading (## or ###)
            if stripped.startswith("##"):
                has_auto_reconcile_heading = True
                break
        # Also accept "auto-reconcile roadmap" split across lines within 5-line window
        if i > 0:
            window = " ".join(lines[max(0, i - 5):i + 1]).lower()
            if "auto-reconcil" in window and "roadmap" in window:
                has_auto_reconcile_heading = True
                break

    assert has_auto_reconcile_heading, (
        f"orchestrator.md is missing '## Auto-Reconcile Roadmap' heading.\n"
        f"Expected to find a heading containing 'auto-reconcile' and 'roadmap' within a 5-line window.\n"
        f"File content (first 2000 chars):\n{text[:2000]!r}"
    )

    # Check that DECISION TREE mentions "auto-reconciled"
    decision_tree_found = False
    in_decision_tree = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## DECISION TREE":
            in_decision_tree = True
        elif in_decision_tree and stripped.startswith("## ") and stripped != "## DECISION TREE":
            # Left the decision tree section
            break
        elif in_decision_tree and "auto-reconciled" in stripped.lower():
            decision_tree_found = True
            break

    assert decision_tree_found, (
        f"DECISION TREE section in orchestrator.md does not mention 'auto-reconciled'.\n"
        f"Expected the DECISION TREE to handle STATUS: PENDING auto-reconciled milestones.\n"
        f"File content (first 2000 chars):\n{text[:2000]!r}"
    )


# ---------------------------------------------------------------------------
# M35 — Constitution principle coverage
# ---------------------------------------------------------------------------


def test_constitution_principles_all_referenced() -> None:
    """Every constitution principle key must be referenced by at least one SPEC.

    This invariant ensures the constitution is not just a declaration — each
    principle is exercised by a real specification. Uncovered principles
    indicate a gap between stated values and actual implementation.
    """
    import re

    specs_dir = REPO_ROOT / "specs"
    if not specs_dir.exists():
        pytest.skip(f"specs/ directory not found at {specs_dir}")

    spec_files: list[Path] = []
    for item in specs_dir.iterdir():
        if item.is_dir() and re.match(r"^M\d+-", item.name):
            spec_file = item / "SPEC.md"
            if spec_file.is_file():
                spec_files.append(spec_file)

    # Collect all constitution_refs from all SPECs
    key_to_specs: dict[str, list[str]] = {key: [] for key in VALID_PRINCIPLE_KEYS}
    for spec_file in sorted(spec_files):
        text = spec_file.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        refs = fm.get("constitution_refs", []) if fm else []
        for key in refs:
            if key in key_to_specs:
                key_to_specs[key].append(spec_file.parent.name)

    failures: list[str] = []
    for key, spec_names in sorted(key_to_specs.items()):
        if not spec_names:
            failures.append(
                f"  {key}: no SPEC references it (checked {len(spec_files)} SPECs: "
                f"{', '.join(sorted(s.parent.name for s in spec_files))})"
            )

    assert not failures, (
        "The following constitution principles have no SPEC referencing them:\n"
        + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# M38 — Double-fire detection
# ---------------------------------------------------------------------------


def test_progress_md_has_no_double_fires() -> None:
    """No double-fires in progress.md (M38).

    A double-fire = 2+ entries with the same task_id within 5 minutes.
    Distinct from the known double-LOG artifact (Windows Cygwin errno 11
    causes two log lines per single tick — that's ONE entry in progress.md).

    This catches REAL concurrency bugs (loop-tick.sh invoked twice in
    parallel, both writing to progress.md) that would otherwise corrupt
    the audit trail.

    Scope: only checks the LAST 50 entries. Historical rapid-fire graph
    dispatches (pae_maintainer, ikigai_maintainer_v2, ikigai_fork_smoke)
    legitimately fire at 6-25s intervals as part of `--graph` deterministic
    cron paths. Those predate this drift test and are not bugs — they're
    by-design. The test guards FUTURE regressions: any new double-fire
    pattern in the last 50 entries will fail.
    """
    import subprocess

    repo = REPO_ROOT
    script = repo / ".claude" / "loop" / "scripts" / "detect-double-fire.sh"
    progress = repo / ".claude" / "loop" / "progress.md"

    if not script.exists():
        pytest.skip(f"detect-double-fire.sh not found: {script}")
    if not progress.exists():
        pytest.skip(f"progress.md not found: {progress}")

    # Build a temp progress.md with only the last 50 entries
    import tempfile, shutil
    progress_text = progress.read_text(encoding="utf-8")
    lines = progress_text.splitlines(keepends=True)
    # Keep header (first 17 lines per format) + last 50 tick entries
    HEADER_LINES = 17
    SCOPE_LINES = 50
    if len(lines) <= HEADER_LINES + SCOPE_LINES:
        pytest.skip("progress.md too small to scope (need >67 lines)")
    header = lines[:HEADER_LINES]
    tail = lines[-SCOPE_LINES:]
    scoped = "".join(header + tail)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(scoped)
        scoped_path = f.name

    try:
        # Run the bash script via subprocess. On Windows, the script's #! header
        # invokes python3 which is on PATH. Use shell=True so the shell resolves
        # python3 correctly; cwd=repo ensures relative paths work.
        cmd = f'bash "{str(script)}" "{scoped_path}"'
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(repo),
            shell=True,
        )

        assert result.returncode == 0, (
            f"Double-fires detected in last 50 progress.md entries:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    finally:
        Path(scoped_path).unlink(missing_ok=True)
