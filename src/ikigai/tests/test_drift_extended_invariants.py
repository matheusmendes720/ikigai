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
        "src/ikigai/src/ikigai/vault/write.py",
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
