"""Invariant: vault_write is the sole vault writer (attribution §7).

Per docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md §7:
    "vault_write is the ONLY vault writer."

The vault module (`src/ikigai/src/ikigai/vault/`) encapsulates ALL writes to
`vault/`. Any code outside the allowlist that opens/writes files under the
vault root violates this invariant.

Allowlist (the legitimate vault writers):
- src/ikigai/src/mcp_server/tools_vault.py — registers the MCP tool
- src/ikigai/src/ikigai/vault/vault_write.py — the underlying implementation
- src/ikigai/src/ikigai/vault/__init__.py — public re-exports
- src/ikigai/src/ikigai/vault/vault_read.py — read-only (no write calls)
- src/ikigai/src/ikigai/vault/path_utils.py — path resolution only

Any OTHER file in `src/ikigai/src/{agents,mcp_server,ikigai}/` that:
    (a) opens a file for writing AND
    (b) the path resolves under vault/

is a violation. The drift detector (test_canonical_scope.py) provides the
parallel pattern for catching canonical-scope drift; this test provides the
analog for write-path drift.
"""
from __future__ import annotations

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


def _resolve_repo_root(start: Path) -> Path:
    """Walk up from `start` until we find src/ikigai/src/agents — that's the
    canonical IKIGAI package root, and its parent is the repo root."""
    cur = start.resolve()
    for parent in [cur, *cur.parents]:
        if (parent / "src" / "ikigai" / "src" / "agents").is_dir():
            return parent
    raise RuntimeError(f"Could not locate repo root from {start}")


def _is_allowlisted(rel_path: Path) -> bool:
    """Return True if `rel_path` is part of the vault module or the MCP
    vault_write tool wrapper — i.e., the legitimate writers."""
    parts = rel_path.parts
    # src/ikigai/src/mcp_server/tools_vault.py
    if parts == ("src", "ikigai", "src", "mcp_server", "tools_vault.py"):
        return True
    # src/ikigai/src/ikigai/vault/<anything>.py
    if (
        len(parts) >= 5
        and parts[:4] == ("src", "ikigai", "src", "ikigai")
        and parts[4] == "vault"
    ):
        return True
    return False


def _strip_comments_and_strings_relaxed(src: str) -> str:
    """Best-effort strip of Python comments — naive but adequate for the
    grep-test. Docstrings and triple-quoted strings are NOT stripped (we
    want to catch vault write attempts even in docstring examples)."""
    out_lines = []
    for line in src.splitlines():
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


def _file_targets_vault(src: str) -> bool:
    """Return True if `src` contains a write operation targeting vault/."""
    body = _strip_comments_and_strings_relaxed(src)

    has_vault_path = (
        _RE_VAULT_STRING.search(body) is not None
        or _RE_PATH_VAULT.search(body) is not None
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


def test_vault_write_is_sole_writer() -> None:
    """Scan the IKIGAI agent/MCP/gateway surface for direct vault writes.

    Violations are collected and surfaced as a single assertion failure
    with the offending file paths + excerpts so a human reviewer can
    investigate.
    """
    repo_root = _resolve_repo_root(Path(__file__))
    ikigai_src = repo_root / "src" / "ikigai" / "src"

    # Scan the canonical-scope subtree (mirrors test_canonical_scope.py)
    scan_roots = [
        ikigai_src / "agents",
        ikigai_src / "mcp_server",
        ikigai_src / "ikigai",
    ]

    violations: list[tuple[Path, str]] = []
    scanned = 0
    for root in scan_roots:
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
                for pat in (_RE_OPEN_WRITE, _RE_PATH_WRITE_METHODS,
                            _RE_ATOMIC_RENAME, _RE_WITH_OPEN):
                    m = pat.search(body)
                    if m:
                        start = max(0, m.start() - 40)
                        end = min(len(body), m.end() + 60)
                        excerpts.append(body[start:end].strip())
                violations.append((rel, " | ".join(excerpts) if excerpts else "<matched>"))

    assert not violations, (
        f"vault_write invariant violated — {len(violations)} file(s) outside "
        f"the allowlist write directly to vault/. Use `vault_write()` (the "
        f"MCP tool wrapper at src/ikigai/src/mcp_server/tools_vault.py) or "
        f"`ikigai.vault.vault_write.vault_write()` instead.\n\n"
        + "\n".join(f"  {p}: {ex}" for p, ex in violations)
        + f"\n\n(scanned {scanned} files across {len(scan_roots)} roots)"
    )


def test_vault_module_is_allowlisted() -> None:
    """Sanity check: the allowlist itself contains the vault module so
    legitimate writers are not flagged. If this fails, the allowlist is
    stale and drift detector + vault_write test are inconsistent."""
    assert _is_allowlisted(Path("src/ikigai/src/ikigai/vault/vault_write.py"))
    assert _is_allowlisted(Path("src/ikigai/src/ikigai/vault/__init__.py"))
    assert _is_allowlisted(Path("src/ikigai/src/ikigai/vault/vault_read.py"))
    assert _is_allowlisted(Path("src/ikigai/src/mcp_server/tools_vault.py"))
    # Negative: a known non-allowlisted file
    assert not _is_allowlisted(Path("src/ikigai/src/agents/deepagents_harness.py"))
    assert not _is_allowlisted(Path("src/ikigai/src/mcp_server/server.py"))


if __name__ == "__main__":
    test_vault_write_is_sole_writer()
    test_vault_module_is_allowlisted()
    print("OK: vault_write invariant holds")
