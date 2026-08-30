"""vault_write conformance: forks MUST NOT touch vault/.

Per spec Q6=I+III: enforcement is docs + grep test. vault_write (canonical Layer 1
MCP server in src/ikigai/) is the ONLY writer to vault/. Forks that need to write
vault data must go through that MCP tool, never directly.

This test enforces the constraint at the file level: any reference to vault/
paths or vault_read/vault_write imports from a fork module is a regression.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Forbidden patterns in fork modules
FORBIDDEN_PATTERNS = [
    re.compile(r"from\s+.*vault\s+import"),
    re.compile(r"import\s+.*vault"),
    re.compile(r"""["']vault/"""),
    re.compile(r"vault_read|vault_write"),
]


@pytest.mark.parametrize("fork_dir", ["src/solverforge_calendar", "src/tuiboard"])
def test_fork_does_not_reference_vault(fork_dir: str):
    """No fork module should import vault or reference vault/ paths."""
    repo_root = Path(__file__).resolve().parents[3]
    fork_path = repo_root / fork_dir
    if not fork_path.exists():
        pytest.skip(f"fork dir does not exist: {fork_path}")
    violations: list[tuple[str, int, str]] = []
    for py_file in fork_path.rglob("*.py"):
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        (str(py_file.relative_to(repo_root)), lineno, line.strip())
                    )
    assert not violations, (
        "fork module references vault (forbidden by spec Q6):\n"
        + "\n".join(f"  {f}:{ln}: {code}" for f, ln, code in violations)
    )
