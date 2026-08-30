"""ikigai_read_vault — reads vault markdown via the vault_read backend.

Mirrors vault_write's security model (path traversal guard) — read-only.
Returns a JSON string with frontmatter, body, sha256, and mtime for downstream
parsing by the LLM.

Append-only invariant: this tool NEVER writes.
"""
from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool
from src.ikigai.src.ikigai.vault.vault_read import vault_read


def _get_vault_dir() -> Path:
    """Lazily resolve vault root at call time.

    5 parents up from src/ikigai/src/agents/ reaches the project root.
    Resolved on every call so tests can monkeypatch this function to
    point at a temp vault without polluting the project's real vault.
    """
    return Path(__file__).resolve().parent.parent.parent.parent.parent / "vault"


@tool
def ikigai_read_vault(vault_path: str) -> str:
    """Read a markdown file from vault. Returns JSON with frontmatter, body, sha256, mtime.

    Args:
        vault_path: relative path within vault/, e.g. "plans/q3/task-x.md"

    Read-only — never writes. Errors are returned as JSON for downstream parsing.
    """
    try:
        result = vault_read(_get_vault_dir(), vault_path)
    except (ValueError, FileNotFoundError) as e:
        return json.dumps({"error": str(e), "vault_path": vault_path})
    return json.dumps(result)


__all__ = ["ikigai_read_vault"]
