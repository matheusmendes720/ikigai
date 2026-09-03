"""SQLite append-only invariant for data/*.db files.

Builds on test_canonical_scope.py + test_drift_extended_invariants.py.
Enforces three invariants on production code:

1. **No DROP TABLE/INDEX in prod** — `data/ikigai_checkpoints.db` and
   `data/vibe_ops.db` schemas must remain stable. If we ever need to
   change a schema, write a migration script + add to allowlist with
   justification. PAV math is archived per attribution §3; checkpoint
   tables must not be dropped.

2. **No DELETE FROM in prod** — checkpoint state is append-only.
   Same justification as #1.

3. **SQLite writes only to data/ dir** — production `sqlite3.connect()`
   calls with literal-string paths must point under `data/` (or be
   `:memory:` for test fixtures). Runtime params (e.g., `checkpoint_db`)
   are exempt — we trust the caller.

Run::

    pytest src/ikigai/tests/test_sqlite_append_only.py -v
"""

from __future__ import annotations

import ast
from pathlib import Path

# ---------------------------------------------------------------------------
# Repository root resolution (mirror test_drift_extended_invariants.py)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
IKIGAI_TESTS = THIS_FILE.parent
IKIGAI_PKG = IKIGAI_TESTS.parent
IKIGAI_SRC = IKIGAI_PKG / "src"
LIFE_REPO = IKIGAI_PKG.parent.parent  # life/

PROD_LAYERS = [
    IKIGAI_SRC / "agents",
    IKIGAI_SRC / "mcp_server",
    IKIGAI_SRC / "ikigai" / "gateway",
    IKIGAI_SRC / "ikigai" / "cli",
    IKIGAI_SRC / "ikigai" / "adapters",
    IKIGAI_SRC / "ikigai" / "vault",
]

# Files allowed to have sqlite3.connect to non-data/ paths OR DROP/DELETE
# statements. Each entry requires explicit justification.
#
# - agents/v2/tools_legacy_reference.py: Phase 8.1 §11.1 — READ-ONLY
#   reference copy of pre-strip tools.py. Never imported.
# - agents/v2/harness_legacy_reference.py: Phase 8.1 §11.1 — same.
SQLITE_ALLOWLIST: frozenset[str] = frozenset({
    "src/ikigai/src/agents/v2/tools_legacy_reference.py",
    "src/ikigai/src/agents/v2/harness_legacy_reference.py",
})


def _iter_python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _relative_to_repo(file: Path) -> str:
    return str(file.relative_to(LIFE_REPO)).replace("\\", "/")


def _format_violation(file: Path, line: int, kind: str, detail: str) -> str:
    return f"  {_relative_to_repo(file)}:{line}  [{kind}]  {detail}"


def _scan_for_string_in_execute(tree: ast.AST, forbidden_prefix: str) -> list[tuple[int, str]]:
    """Find execute() calls whose first string-arg starts with forbidden_prefix.

    Returns list of (line_no, snippet) for each violation.
    """
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match execute(...) or executescript(...)
        func = node.func
        func_name = func.attr if isinstance(func, ast.Attribute) else None
        if func_name not in {"execute", "executescript"}:
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            if first_arg.value.strip().upper().startswith(forbidden_prefix):
                violations.append((node.lineno, first_arg.value.strip()[:80]))
    return violations


def _scan_for_sqlite_connect_to_non_data(tree: ast.AST) -> list[tuple[int, str]]:
    """Find sqlite3.connect() calls with literal-string paths NOT under data/.

    Runtime params (variables) are exempt — caller is responsible for path.
    :memory: is allowed (test fixtures).
    """
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Match sqlite3.connect(...) — func is Attribute(attr='connect') on Name(id='sqlite3')
        if not (isinstance(func, ast.Attribute) and func.attr == "connect"):
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if not (isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str)):
            continue  # runtime param — trust caller
        path_str = first_arg.value
        if path_str == ":memory:":
            continue
        # Allowed: starts with "data/" (relative path) OR is an absolute path under life/data/
        if path_str.startswith("data/") or path_str.startswith("./data/"):
            continue
        violations.append((node.lineno, path_str))
    return violations


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_drop_table_in_prod() -> None:
    """No DROP TABLE / DROP INDEX in production code.

    Schema changes must go through migration scripts + allowlist update.
    """
    violations: list[str] = []
    for root in PROD_LAYERS:
        if not root.exists():
            continue
        for py_file in _iter_python_files(root):
            rel_path = _relative_to_repo(py_file)
            if rel_path in SQLITE_ALLOWLIST:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for line_no, snippet in _scan_for_string_in_execute(tree, "DROP"):
                violations.append(
                    _format_violation(
                        py_file, line_no, "SQLITE-DROP",
                        f"DROP statement in execute() — schema must not change: {snippet!r}",
                    )
                )
    assert not violations, (
        "SQLite DROP statement detected — append-only invariant violated:\n"
        + "\n".join(sorted(violations))
        + f"\nAllowlist (update with justification if legitimate): {sorted(SQLITE_ALLOWLIST)}"
    )


def test_no_delete_from_in_prod() -> None:
    """No DELETE FROM in production code.

    Checkpoint state is append-only per attribution §3 (PAV math archived).
    """
    violations: list[str] = []
    for root in PROD_LAYERS:
        if not root.exists():
            continue
        for py_file in _iter_python_files(root):
            rel_path = _relative_to_repo(py_file)
            if rel_path in SQLITE_ALLOWLIST:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for line_no, snippet in _scan_for_string_in_execute(tree, "DELETE"):
                violations.append(
                    _format_violation(
                        py_file, line_no, "SQLITE-DELETE",
                        f"DELETE statement in execute() — checkpoints are append-only: {snippet!r}",
                    )
                )
    assert not violations, (
        "SQLite DELETE statement detected — append-only invariant violated:\n"
        + "\n".join(sorted(violations))
    )


def test_sqlite_writes_only_to_data_dir() -> None:
    """sqlite3.connect() with literal-string paths must point under data/.

    Runtime params (e.g., `checkpoint_db`) are exempt — caller controls path.
    """
    violations: list[str] = []
    for root in PROD_LAYERS:
        if not root.exists():
            continue
        for py_file in _iter_python_files(root):
            rel_path = _relative_to_repo(py_file)
            if rel_path in SQLITE_ALLOWLIST:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for line_no, path_str in _scan_for_sqlite_connect_to_non_data(tree):
                violations.append(
                    _format_violation(
                        py_file, line_no, "SQLITE-PATH",
                        f"sqlite3.connect to non-data/ path: {path_str!r}",
                    )
                )
    assert not violations, (
        "SQLite database path outside data/ — must live under data/:\n"
        + "\n".join(sorted(violations))
        + "\nEither move the DB to data/ or update SQLITE_ALLOWLIST with justification."
    )


def test_sqlite_append_only_self_check() -> None:
    """Sanity check — detectors themselves work."""
    assert PROD_LAYERS, "PROD_LAYERS must be non-empty"
    assert SQLITE_ALLOWLIST, "SQLITE_ALLOWLIST must be non-empty"
    # Each allowlist entry should actually exist on disk
    for rel_path in SQLITE_ALLOWLIST:
        full = LIFE_REPO / rel_path.replace("/", "\\") if "\\" in str(LIFE_REPO) else LIFE_REPO / rel_path
        assert full.exists(), f"SQLITE_ALLOWLIST entry missing: {rel_path}"
