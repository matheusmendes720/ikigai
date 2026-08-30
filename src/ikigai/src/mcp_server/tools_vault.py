"""B6.7 vault_write MCP tool — only vault writer per attribution §7.
B7.1 vault_read MCP tool — read-side mirror of vault_write.

Precedent: src/ikigai/src/mcp_server/tools_mesh.py (handlers are sync,
return JSON strings, errors returned as {"error": "..."}).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

# Aliases so public functions below (also named vault_read / vault_write)
# do not shadow the impl imports.
from src.ikigai.src.ikigai.vault.vault_read import (  # type: ignore[import-not-found]
    vault_read as _vault_read_impl,
)
from src.ikigai.src.ikigai.vault.vault_write import (  # type: ignore[import-not-found]
    vault_write as _vault_write_impl,
)


def _resolve_vault_root() -> Path:
    """Vault root resolution: walk up from this file to find vault/.

    src/ikigai/src/mcp_server/tools_vault.py → parents[4] = life/ (project root)
    Path ancestors of tools_vault.py (depth from file):
      [0] = mcp_server/  [1] = src/ (ikigai's src)
      [2] = ikigai/      [3] = src/ (project src)
      [4] = life/       (project root, where vault/ lives)
    """
    vault_root = Path(__file__).resolve().parents[4] / "vault"
    # Fallback for tests/CI: cwd
    if not vault_root.exists():
        vault_root = Path.cwd() / "vault"
    return vault_root


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
        vault_root = _resolve_vault_root()
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


def vault_read(
    vault_path: Annotated[str, "Relative path within vault/, e.g. 'plans/q3/task-x.md'"],
) -> str:
    """Read markdown file from vault. Read-side mirror of vault_write (B7.1).

    Rejects paths outside vault/, absolute paths. Uses VaultLock for
    cross-platform concurrency safety. Read-only — never writes.
    Returns JSON with parsed frontmatter, body, sha256, mtime.
    """
    try:
        vault_root = _resolve_vault_root()
        result = _vault_read_impl(
            vault_root=vault_root,
            vault_path=vault_path,
        )
    except ValueError as e:
        return json.dumps({"error": str(e), "code": -32602})
    except FileNotFoundError as e:
        return json.dumps({"error": str(e), "code": -32602})
    except Exception as e:
        return json.dumps({"error": f"vault read failed: {e}", "code": -32603})

    return json.dumps(result, indent=2)


__all__ = ["vault_read", "vault_write"]
