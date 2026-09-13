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
