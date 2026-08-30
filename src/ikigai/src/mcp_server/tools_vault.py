"""B6.7 vault_write MCP tool — only vault writer per attribution §7.

Precedent: src/ikigai/src/mcp_server/tools_mesh.py (handlers are sync,
return JSON strings, errors returned as {"error": "..."}).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from src.ikigai.src.ikigai.vault.vault_write import vault_write as _vault_write_impl  # type: ignore[import-not-found]


def vault_write(
    vault_path: Annotated[str, "Relative path within vault/, e.g. 'plans/q3/task-x.md'"],
    frontmatter: Annotated[dict[str, Any], "YAML frontmatter key/values (dict)"],
    body: Annotated[str, "Markdown body below frontmatter"],
) -> str:
    """Write markdown file to vault. ONLY vault writer per attribution §7.

    Rejects paths outside vault/, absolute paths, empty writes.
    Uses VaultLock for cross-platform concurrency safety.
    Atomic via tmp-file + os.replace() (B6.4 Windows-safe pattern).
    """
    try:
        # Vault root resolution: walk up from this file to find vault/.
        # src/ikigai/src/mcp_server/tools_vault.py → parents[4] = life/ (project root)
        # Path ancestors of tools_vault.py (depth from file):
        #   [0] = mcp_server/  [1] = src/ (ikigai's src)
        #   [2] = ikigai/      [3] = src/ (project src)
        #   [4] = life/       (project root, where vault/ lives)
        vault_root = Path(__file__).resolve().parents[4] / "vault"
        # Fallback for tests/CI: env var or cwd
        if not vault_root.exists():
            vault_root = Path.cwd() / "vault"

        result = _vault_write_impl(
            vault_root=vault_root,
            vault_path=vault_path,
            frontmatter_fields=frontmatter,
            body=body,
        )
    except ValueError as e:
        return json.dumps({"error": str(e), "code": -32602})
    except Exception as e:
        return json.dumps({"error": f"vault write failed: {e}", "code": -32603})

    return json.dumps(result, indent=2)


__all__ = ["vault_write"]
