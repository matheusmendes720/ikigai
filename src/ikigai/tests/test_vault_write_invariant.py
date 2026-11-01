"""Invariant: the vault write path is confined to the canonical writers.

Per ADR-012 (and the attribution §7 rule it replaces), the agent layer is
the only layer allowed to write into `vault/`. The canonical write path is:

- `sys_ikigai/vault/vault_write.py` — the underlying writer
- `sys_ikigai/security/vault_write_wrapper.py` — the ADR-029 enforcement
  layer (kill switch, rate limit, actor whitelist, audit log) that every
  `vault_write` call must traverse
- `src/agents/` — the planner layer itself (its session summaries and
  reflection logs are append-only files it owns)

Any OTHER file that opens a file for writing under the vault root violates
this invariant. The drift detector (test_canonical_scope.py) provides the
parallel pattern for catching canonical-scope drift; this test provides the
analog for write-path drift.

Scope note (ADR-037): the retired `src/ikigai/src/{agents,mcp_server}`
harness dirs no longer exist, so the scan roots are the canonical
production layers that do exist.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns that signal "writing a file"
# ---------------------------------------------------------------------------

# Matches open() in write/append/update mode: open("foo", "w"), open(p, mode="a"), etc.
_RE_OPEN_WRITE = re.compile(
    r"""open\s*\([^)]*?(?:['"](?:w|a|x|w\+|a\+|r\+)['"]|mode\s*=\s*['"](?:w|a|x|w\+|a\+|r\+)['"])""",
    re.VERBOSE,
)

# Matches Path(...).write_text / .write_bytes calls
_RE_PATH_WRITE_METHODS = re.compile(
    r"""\.(?:write_text|write_bytes)\s*\(""",
)

# Matches os.replace / os.rename / Path.replace with vault paths on both sides
_RE_ATOMIC_RENAME = re.compile(
    r"""(?:os\.(?:replace|rename)|Path[A-Za-z_]*\.replace)\s*\(""",
)

# Matches with open(...) as f: blocks (variant form)
_RE_WITH_OPEN = re.compile(
    r"""with\s+open\s*\(""",
)

# ---------------------------------------------------------------------------
# Vault path patterns — anything that touches vault/
# ---------------------------------------------------------------------------

# Matches literal strings like "vault/", 'vault/', f"vault/{x}"
_RE_VAULT_STRING = re.compile(
    r"""['"](?:[^'"]*?/)?vault/[^'"]*?['"]""",
)

# Matches Path() construction with vault segments
_RE_PATH_VAULT = re.compile(
    r"""Path\s*\(\s*[^)]*?vault/[^)]*?\)""",
)

# The canonical marker used to locate the repo root. `src/contracts/common.py`
# is the single source of truth for the shared Pydantic models and is stable
# in every clone of the canonical scope.
_ROOT_MARKER = Path("src") / "contracts" / "common.py"


def _resolve_repo_root(start: Path) -> Path:
    """Walk up from `start` until the canonical contracts marker is found."""
    cur = start.resolve()
    for parent in [cur, *cur.parents]:
        if (parent / _ROOT_MARKER).is_file():
            return parent
    raise RuntimeError(f"Could not locate repo root from {start}")


def _is_allowlisted(rel_path: Path) -> bool:
    """Return True if `rel_path` belongs to a legitimate vault writer."""
    parts = rel_path.parts
    # sys_ikigai/vault/<anything>.py — the canonical writer package
    if len(parts) >= 3 and parts[:2] == ("sys_ikigai", "vault"):
        return True
    # sys_ikigai/security/vault_write_wrapper.py — the ADR-029 enforcement layer
    if parts == ("sys_ikigai", "security", "vault_write_wrapper.py"):
        return True
    # src/agents/<anything>.py — the planner layer (ADR-012 sole writer)
    if len(parts) >= 2 and parts[:2] == ("src", "agents"):
        return True
    return False


def _split_docstrings(src: str) -> tuple[str, list[str]]:
    """Return ``(code_without_docstrings, docstrings)``.

    A docstring is documentation, not an executed write target. We keep
    them separate so that a docstring which itself documents a vault WRITE
    (e.g. ``open("vault/x.md", "w")``) is still reported, while a docstring
    that merely mentions a vault path (e.g. a cache key example) is not.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src, []

    spans: list[tuple[int, int]] = []
    docs: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            spans.append((first.lineno, first.end_lineno or first.lineno))
            docs.append(first.value.value)

    if not spans:
        return src, docs

    lines = src.splitlines(keepends=True)
    for start, end in spans:
        for idx in range(start - 1, min(end, len(lines))):
            lines[idx] = "\n"
    return "".join(lines), docs


def _strip_comments_and_strings_relaxed(src: str) -> str:
    """Best-effort strip of Python comments — naive but adequate for the
    grep-test. Docstrings are blanked out here (they are scanned
    separately by ``_docstring_targets_vault``); remaining string literals
    are NOT stripped, so a real path literal feeding a write call is
    still detected."""
    code, _docs = _split_docstrings(src)
    out_lines = []
    for line in code.splitlines():
        # Strip trailing line comments
        if "#" in line:
            # Naive: '# ' introduces a comment, but '#' can also appear in
            # strings. For a drift detector this is acceptable: the cost
            # of a false negative (missing a real violation) is high;
            # the cost of a false positive (flagging a comment) is low
            # (the human reviewer just confirms the line is a comment).
            stripped = line.split("#", 1)[0]
        else:
            stripped = line
        out_lines.append(stripped)
    return "\n".join(out_lines)


def _docstring_targets_vault(doc: str) -> bool:
    """Return True if a docstring documents a write into vault/."""
    body = _strip_comments_and_strings_relaxed(doc)
    if not (_RE_VAULT_STRING.search(body) is not None or _RE_PATH_VAULT.search(body) is not None):
        return False
    return (
        _RE_OPEN_WRITE.search(body) is not None
        or _RE_PATH_WRITE_METHODS.search(body) is not None
        or _RE_ATOMIC_RENAME.search(body) is not None
        or _RE_WITH_OPEN.search(body) is not None
    )


def _file_targets_vault(src: str) -> bool:
    """Return True if `src` contains a write operation targeting vault/."""
    body = _strip_comments_and_strings_relaxed(src)
    _code, docs = _split_docstrings(src)
    if any(_docstring_targets_vault(d) for d in docs):
        return True

    has_vault_path = (
        _RE_VAULT_STRING.search(body) is not None or _RE_PATH_VAULT.search(body) is not None
    )
    if not has_vault_path:
        return False

    has_write_call = (
        _RE_OPEN_WRITE.search(body) is not None
        or _RE_PATH_WRITE_METHODS.search(body) is not None
        or _RE_ATOMIC_RENAME.search(body) is not None
        or _RE_WITH_OPEN.search(body) is not None
    )
    return has_write_call


def _scan_roots(repo_root: Path) -> list[Path]:
    """The canonical production layers that must not write into vault/."""
    return [
        repo_root / "src" / "contracts",
        repo_root / "src" / "mesh",
        repo_root / "src" / "services",
        repo_root / "src" / "transport",
        repo_root / "src" / "ikigai" / "src",
        repo_root / "src" / "life_tatics",
        repo_root / "sys_ikigai",
        repo_root / "life",
        repo_root / "interfaces" / "cli",
    ]


def test_vault_write_is_sole_writer() -> None:
    """Scan the canonical production layers for direct vault writes.

    Violations are collected and surfaced as a single assertion failure
    with the offending file paths + excerpts so a human reviewer can
    investigate.
    """
    repo_root = _resolve_repo_root(Path(__file__))

    violations: list[tuple[Path, str]] = []
    scanned = 0
    for root in _scan_roots(repo_root):
        if not root.is_dir():
            continue
        for py_file in sorted(root.rglob("*.py")):
            scanned += 1
            rel = py_file.relative_to(repo_root)
            if _is_allowlisted(rel):
                continue
            try:
                src = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if _file_targets_vault(src):
                # Extract a small excerpt for human review
                body = _strip_comments_and_strings_relaxed(src)
                excerpts: list[str] = []
                for pat in (
                    _RE_OPEN_WRITE,
                    _RE_PATH_WRITE_METHODS,
                    _RE_ATOMIC_RENAME,
                    _RE_WITH_OPEN,
                ):
                    m = pat.search(body)
                    if m:
                        start = max(0, m.start() - 40)
                        end = min(len(body), m.end() + 60)
                        excerpts.append(body[start:end].strip())
                violations.append((rel, " | ".join(excerpts) if excerpts else "<matched>"))

    assert scanned > 0, "vault write scan found no files — the scan roots are stale"
    assert not violations, (
        f"vault_write invariant violated — {len(violations)} file(s) outside "
        f"the allowlist write directly to vault/. Use `vault_write()` (the "
        f"canonical writer at sys_ikigai/vault/vault_write.py, always through "
        f"sys_ikigai/security/vault_write_wrapper.py) instead.\n\n"
        + "\n".join(f"  {p}: {ex}" for p, ex in violations)
        + f"\n\n(scanned {scanned} files)"
    )


def test_vault_module_is_allowlisted() -> None:
    """Sanity check: the allowlist itself contains the canonical writers so
    legitimate writers are not flagged. If this fails, the allowlist is
    stale and drift detector + vault_write test are inconsistent."""
    assert _is_allowlisted(Path("sys_ikigai/vault/vault_write.py"))
    assert _is_allowlisted(Path("sys_ikigai/vault/__init__.py"))
    assert _is_allowlisted(Path("sys_ikigai/vault/vault_read.py"))
    assert _is_allowlisted(Path("sys_ikigai/security/vault_write_wrapper.py"))
    assert _is_allowlisted(Path("src/agents/reflection/recursive.py"))
    # Negative: known non-allowlisted files
    assert not _is_allowlisted(Path("src/mesh/agent_propagator.py"))
    assert not _is_allowlisted(Path("src/services/sync.py"))
    assert not _is_allowlisted(Path("src/transport/mcp_server.py"))


if __name__ == "__main__":
    test_vault_write_is_sole_writer()
    test_vault_module_is_allowlisted()
    print("OK: vault_write invariant holds")
