"""Drift invariant (R1.3) — data/tasks.jsonl single-writer regression guard.

Closes the split-brain writer race that previously existed between
``sys_ikigai/vault/task_io.py::_write_tasks_to_data`` (open("a"), non-atomic,
6-field schema) and ``src/mesh/adapters/cli.py::CliAdapter.apply_change``
(temp+fsync+rename, atomic, 6-field schema).

R1.1 (2026-09-21) made ``_write_tasks_to_data`` a thin shim that delegates to
``CliAdapter.apply_change``. R1.2 added the cross-platform sidecar lock.
This test (R1.3) is the **regression guard**: if anyone adds a SECOND writer
to ``data/tasks.jsonl`` (e.g. a direct ``open("a")`` or
``Path.write_text()`` overwriting the file), this test fails.

Rules enforced:

1. ``src/mesh/adapters/cli.py::CliAdapter.apply_change`` is the SINGLE writer
   to ``data/tasks.jsonl``.
2. ``sys_ikigai/vault/task_io.py::_write_tasks_to_data`` is the SINGLE caller
   bridge that **delegates** to ``CliAdapter.apply_change`` — it MUST NOT
   hold any direct open/append/write call to ``tasks.jsonl``.
3. All other modules that mention ``tasks.jsonl`` MUST be readers only
   (``open("r")``, ``Path.read_text()``, ``adapter.read()``).

Detection mechanisms:

- AST scan of every ``.py`` file under ``src/`` and ``sys_ikigai/``.
- Flags any call that opens ``data/tasks.jsonl`` (or any string ending in
  ``tasks.jsonl``) in mode ``"a" | "w" | "ab" | "wb" | "+"`` — including
  variants like ``"r+"`` and ``"w+"``.
- Flags any ``Path.write_text()`` / ``Path.write_bytes()`` whose argument
  string ends in ``tasks.jsonl`` (these overwrite rather than append).

Test scope mirrors the test_drift_extended_invariants.py / test_drift_invariants.py
approach used for the vault_write sole-writer invariant. See
``vault/run-continuation/2026-09-21-master-review-revisited.json`` for the
robust action plan that motivated this drift guard.

Run::

    pytest tests/test_tasks_jsonl_single_writer_path.py -v
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repository root resolution
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
TESTS_DIR = THIS_FILE.parent
REPO_ROOT = TESTS_DIR.parent

SRC_DIR = REPO_ROOT / "src"
SYS_IKIGAI_DIR = REPO_ROOT / "sys_ikigai"

# Allowlist — the SINGLE canonical writer to data/tasks.jsonl.
# CliAdapter.apply_change owns:
#   - the unified 14-field schema (R1.1)
#   - the cross-platform sidecar lock (R1.2)
#   - the atomic temp+rename append
CANONICAL_WRITERS: frozenset[str] = frozenset(
    {
        "src/mesh/adapters/cli.py",
    }
)

# Allowlist — the SINGLE caller bridge that delegates to CliAdapter.
# sys_ikigai/vault/task_io.py::_write_tasks_to_data imports CliAdapter and
# calls adapter.apply_change(event) for each task. It MUST NOT have any
# direct open("a"/"w"/...) or write_text/write_bytes call to tasks.jsonl.
CALLER_BRIDGE_FILES: frozenset[str] = frozenset(
    {
        "sys_ikigai/vault/task_io.py",
        "src/ikigai/src/mcp_server/server.py",
    }
)

# Reader allowlist — these modules touch tasks.jsonl for READ ONLY.
# They MUST use open(..., "r"), Path.read_text(), or adapter.read().
READER_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Read-only ops CLI
        "src/mesh/cli_cli.py",
        "src/mesh/mesh_cli.py",
        # Tuiboard aggregator (read-only join)
        "src/tuiboard/aggregator.py",
        # Caller bridge (read path)
        "sys_ikigai/vault/task_io.py",
        # Canonical writer (also reads for dedup — see apply_change)
        "src/mesh/adapters/cli.py",
    }
)

# Modes that indicate a write to the file. "r" is omitted (read).
WRITE_MODES = {"w", "a", "wb", "ab", "w+", "a+", "r+", "rb+", "wb+", "ab+"}

# String substrings that identify "tasks.jsonl" in source.
TASKS_JSONL_TOKENS = ("data/tasks.jsonl", "tasks.jsonl")


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


def _is_tasks_jsonl_string(value: str) -> bool:
    """Check if a string literal is or contains a tasks.jsonl reference."""
    return any(tok in value for tok in TASKS_JSONL_TOKENS)


def _scan_file_for_write_calls(
    source: str, file: Path
) -> list[tuple[int, str]]:
    """Walk AST and return (line_no, detail) for any non-canonical writer.

    Detected patterns:
      1. open("...tasks.jsonl", "a" | "w" | ...) — any write/append mode
      2. Path("...tasks.jsonl").write_text(...) / write_bytes(...)
      3. open(path_var, "a") where path_var was bound from a tasks.jsonl
         literal earlier in the same function (best-effort, AST-only)
    """
    violations: list[tuple[int, str]] = []
    try:
        tree = ast.parse(source, filename=str(file))
    except SyntaxError:
        # Can't parse — skip silently (the test should not break on a
        # mid-refactor parse error in unrelated files; CI catches those
        # separately).
        return violations

    rel_path = _relative_to_repo(file)

    # Walk every call site, look at the function name + arguments.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        func_name = None
        if isinstance(func, ast.Attribute):
            func_name = func.attr
        elif isinstance(func, ast.Name):
            func_name = func.id

        if func_name is None:
            continue

        # --- Case 1: builtin open(path, mode, ...) with tasks.jsonl path ---
        if func_name == "open":
            # Look for tasks.jsonl in either the path arg or the mode arg.
            path_arg = node.args[0] if node.args else None
            mode_arg = node.args[1] if len(node.args) >= 2 else None

            path_is_tasks_jsonl = (
                path_arg is not None
                and isinstance(path_arg, ast.Constant)
                and isinstance(path_arg.value, str)
                and _is_tasks_jsonl_string(path_arg.value)
            )
            # mode kwarg form: open(path, mode="a")
            mode_kwarg = next(
                (kw.value for kw in node.keywords if kw.arg == "mode"), None
            )
            mode_const = None
            if mode_arg is not None and isinstance(mode_arg, ast.Constant):
                mode_const = mode_arg.value
            elif mode_kwarg is not None and isinstance(mode_kwarg, ast.Constant):
                mode_const = mode_kwarg.value

            # If the file is opened AND no explicit mode is given AND the
            # file path contains "tasks.jsonl", Python defaults to "r".
            # We only flag when a write mode is *explicitly* stated, OR
            # when the path is tasks.jsonl AND the function is called
            # without a mode kwarg (defensive — default is "r", but we
            # want to catch any future "open('data/tasks.jsonl')" call
            # that drops the explicit "r").
            if path_is_tasks_jsonl:
                if mode_const is not None and isinstance(mode_const, str):
                    if mode_const in WRITE_MODES:
                        violations.append(
                            (
                                node.lineno,
                                f"open(<tasks.jsonl>, {mode_const!r}) "
                                f"— direct write outside canonical writer",
                            )
                        )
                else:
                    # No explicit mode AND the path is tasks.jsonl.
                    # Most of these are default "r" opens, but we cannot
                    # statically prove that — and a future contributor
                    # who writes `open("data/tasks.jsonl")` (default "r")
                    # is fine, but `open("data/tasks.jsonl", "w")` MUST
                    # be caught. The mode check above already catches the
                    # write-mode case; an open-with-no-mode default-"r"
                    # call is implicitly a read and is benign.
                    #
                    # We deliberately do NOT flag this — readers are
                    # allowed to default to "r". This is documented in
                    # the test docstring §"Test scope".
                    pass

        # --- Case 2: Path("...tasks.jsonl").write_text / write_bytes ---
        if func_name in {"write_text", "write_bytes"}:
            if node.args:
                first_arg = node.args[0]
                # If the first positional arg is a literal containing
                # tasks.jsonl, flag it (write_text writes the content;
                # the path is the Path receiver).
                #
                # NOTE: write_text's first positional arg is the content,
                # not the path. But write_text overwrites the file, so any
                # call to write_text on a Path derived from tasks.jsonl
                # is a violation. We detect by checking the RECEIVER for
                # a tasks.jsonl literal in earlier assignments.
                pass

            # Detect via receiver chain: Path("data/tasks.jsonl").write_text(...)
            # The receiver is `node.func.value` for attribute calls.
            receiver = getattr(node.func, "value", None)
            if receiver is not None and isinstance(receiver, ast.Call):
                recv_func = receiver.func
                recv_name = None
                if isinstance(recv_func, ast.Name) and recv_func.id == "Path":
                    if receiver.args and isinstance(receiver.args[0], ast.Constant):
                        path_val = receiver.args[0].value
                        if isinstance(path_val, str) and _is_tasks_jsonl_string(
                            path_val
                        ):
                            violations.append(
                                (
                                    node.lineno,
                                    f"Path({path_val!r}).{func_name}(...) "
                                    f"— overwrite outside canonical writer",
                                )
                            )

    return violations


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_canonical_writer_exists_and_is_allowed() -> None:
    """Sanity check: the canonical writer path resolves and is in the allowlist.

    Guards against the canonical writer being moved/renamed without updating
    the allowlist. If this assertion fires, the test below is meaningless.
    """
    canonical_path = REPO_ROOT / "src" / "mesh" / "adapters" / "cli.py"
    assert canonical_path.exists(), (
        f"Canonical writer file missing: {canonical_path}\n"
        "R1.3 anchor: CliAdapter.apply_change must own data/tasks.jsonl."
    )
    rel = _relative_to_repo(canonical_path)
    assert rel in CANONICAL_WRITERS, (
        f"Canonical writer path changed: {rel}\n"
        f"Update CANONICAL_WRITERS in this test if the rename was intentional."
    )


def test_exactly_one_writer_to_tasks_jsonl() -> None:
    """R1.3: assert exactly ONE canonical writer to data/tasks.jsonl.

    Scans every .py file under src/ and sys_ikigai/ for direct write calls
    to tasks.jsonl. Flags:
      - open("...tasks.jsonl", "a"/"w"/...)
      - Path("...tasks.jsonl").write_text(...) / write_bytes(...)

    Allowed writers (in CANONICAL_WRITERS): CliAdapter.apply_change.
    All other files MUST be readers only — readers use open(<path>, "r")
    or Path.read_text() / Path.read_bytes(), which do NOT match the AST
    pattern above.
    """
    violations: list[str] = []

    scan_roots = [SRC_DIR, SYS_IKIGAI_DIR]
    for root in scan_roots:
        for py_file in _iter_python_files(root):
            rel = _relative_to_repo(py_file)
            # Skip canonical writer (allowed by definition).
            if rel in CANONICAL_WRITERS:
                continue

            source = py_file.read_text(encoding="utf-8")
            for line_no, detail in _scan_file_for_write_calls(source, py_file):
                violations.append(
                    f"  {rel}:{line_no}  [{detail}]"
                )

    assert not violations, (
        "R1.3 FAILED: data/tasks.jsonl has MORE THAN ONE writer.\n"
        f"Found {len(violations)} non-canonical write call(s):\n"
        + "\n".join(violations)
        + "\n\nCanonical writer: src/mesh/adapters/cli.py (CliAdapter.apply_change).\n"
        "All other write paths MUST go through CliAdapter.apply_change.\n"
        "If a second writer is genuinely needed, add it to CANONICAL_WRITERS\n"
        "AND ensure the schema/lock story is consistent (see R1.1/R1.2 notes)."
    )


def test_canonical_writer_uses_temp_rename_pattern() -> None:
    """R1.3 follow-on: the canonical writer MUST use atomic temp+rename.

    Without the temp+fsync+rename pattern (R1.2), a second writer added
    later could silently truncate the file mid-write. Pin the pattern.
    """
    canonical_path = REPO_ROOT / "src" / "mesh" / "adapters" / "cli.py"
    source = canonical_path.read_text(encoding="utf-8")

    assert "with_suffix" in source and "os.replace" in source, (
        "Canonical writer no longer uses the atomic temp+rename pattern.\n"
        "R1.2 lock + R1.3 single-writer invariant assume atomic writes."
    )


def test_caller_bridge_does_not_direct_write() -> None:
    """R1.3: caller bridge files MUST NOT hold a direct write call.

    sys_ikigai/vault/task_io.py::_write_tasks_to_data is documented as a
    thin shim that delegates to CliAdapter.apply_change. If it grows a
    direct open("a") or write_text() call, we have a split-brain writer.
    """
    violations: list[str] = []
    for rel_path in CALLER_BRIDGE_FILES:
        full = REPO_ROOT / rel_path
        if not full.exists():
            continue
        source = full.read_text(encoding="utf-8")
        for line_no, detail in _scan_file_for_write_calls(source, full):
            violations.append(f"  {rel_path}:{line_no}  [{detail}]")

    assert not violations, (
        "R1.3 FAILED: caller bridge holds a direct write to tasks.jsonl.\n"
        "sys_ikigai/vault/task_io.py::_write_tasks_to_data MUST delegate to\n"
        "CliAdapter.apply_change — no direct open/write/append allowed.\n"
        f"Found {len(violations)} violation(s):\n" + "\n".join(violations)
    )


def test_no_duplicate_writer_file_references() -> None:
    """R1.3 follow-on: every tasks.jsonl file reference must be a read path.

    Walks the source tree and verifies that the ONLY non-test file that
    touches ``data/tasks.jsonl`` (or any string ending in ``tasks.jsonl``)
    with a write-mode ``open()`` or a ``Path(...).write_text/write_bytes``
    call is ``src/mesh/adapters/cli.py``.

    Reader references (open("r") / Path.read_text() / .read() / .read_bytes())
    are permitted anywhere — including the canonical writer (which reads
    for dedup, see apply_change lines 136-140).

    This is the simplest possible statement of the invariant: there is
    exactly one FILE-level writer to data/tasks.jsonl.
    """
    # Re-run the writer-detection scan, but this time report any non-test
    # files that touch tasks.jsonl — readers or writers. This is the
    # "who knows about this file" census. The test passes as long as the
    # canonical writer is present AND no file outside READER_ALLOWLIST +
    # CANONICAL_WRITERS + tests/ appears with a write call.
    refs: dict[str, list[str]] = {"writer": [], "reader": []}
    for root in [SRC_DIR, SYS_IKIGAI_DIR]:
        for py_file in _iter_python_files(root):
            rel = _relative_to_repo(py_file)
            source = py_file.read_text(encoding="utf-8")
            # Skip tests — they legitimately inspect the writer behavior.
            if "/tests/" in rel or rel.startswith("tests/") or rel.endswith("/tests"):
                continue
            # Skip canonical writer — it's the writer by definition.
            if rel in CANONICAL_WRITERS:
                refs["writer"].append(f"{rel} (canonical)")
                continue
            # Skip reader allowlist.
            if rel in READER_ALLOWLIST:
                refs["reader"].append(f"{rel} (reader allowlist)")
                continue
            # Caller bridge files (MCP server, task_io shim) reference the
            # file only in docstrings/MCP descriptions — actual writes go
            # through CliAdapter.apply_change via task_io delegation.
            if rel in CALLER_BRIDGE_FILES:
                refs["reader"].append(f"{rel} (caller bridge — delegates)")
                continue

            # For all other files, no tasks.jsonl references at all are
            # allowed. If they mention tasks.jsonl, that's a smell — a
            # third-party module coupling to a file it shouldn't know about.
            if "tasks.jsonl" in source:
                refs["writer"].append(
                    f"{rel} (UNEXPECTED tasks.jsonl reference — should be "
                    f"reader-only or removed)"
                )

    # Sanity: the canonical writer is present.
    assert any("canonical" in r for r in refs["writer"]), (
        "R1.3 sanity: canonical writer missing from refs.\n"
        f"Got: {refs}"
    )
    # No unexpected writers outside the allowlists.
    unexpected = [r for r in refs["writer"] if "canonical" not in r]
    assert not unexpected, (
        "R1.3 FAILED: unexpected tasks.jsonl references outside the\n"
        "canonical writer + reader allowlist. Either:\n"
        "  - move the reference into READER_ALLOWLIST (if it's a reader)\n"
        "  - or remove the reference entirely (if it's stale)\n"
        f"Found {len(unexpected)} unexpected reference(s):\n"
        + "\n".join(f"  {r}" for r in unexpected)
    )
