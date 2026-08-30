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

# Mirrors the _PROJECT_ROOT pattern used elsewhere in src/ikigai/src/agents/
# (5 parents up from src/ikigai/src/agents/ to reach the project root).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_VAULT_DIR = _PROJECT_ROOT / "vault"


@tool
def ikigai_read_vault(vault_path: str) -> str:
    """Read a markdown file from vault. Returns JSON with frontmatter, body, sha256, mtime.

    Args:
        vault_path: relative path within vault/, e.g. "plans/q3/task-x.md"

    Read-only — never writes. Errors are returned as JSON for downstream parsing.
    """
    try:
        result = vault_read(_VAULT_DIR, vault_path)
    except (ValueError, FileNotFoundError) as e:
        return json.dumps({"error": str(e), "vault_path": vault_path})
    return json.dumps(result)


__all__ = ["ikigai_read_vault"]
