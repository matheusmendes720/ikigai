"""B6.7 vault_write MCP tool — only vault writer per attribution §7.
B7.1 vault_read MCP tool — read-side mirror of vault_write.

Precedent: src/ikigai/src/mcp_server/tools_mesh.py (handlers are sync,
return JSON strings, errors returned as {"error": "..."}).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

# Aliases so public functions below (also named vault_read / vault_write)
# do not shadow the impl imports.
from ikigai.vault.vault_read import (
    vault_read as _vault_read_impl,
)
from ikigai.vault.vault_write import (
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
    actor: Annotated[str, "Actor performing the write: user/agent/system"] = "user",
) -> str:
    """Write markdown file to vault. ONLY vault writer per attribution §7.

    Per spec 2026-09-03-sonho-tree-hybrid-design §vault_write actor parameter.
    Records actor in audit log for drift invariant (g).

    Rejects paths outside vault/, absolute paths, empty writes.
    Uses VaultLock for cross-platform concurrency safety.
    Atomic via tmp-file + atomic rename (B6.4 Windows-safe pattern).
    """
    if actor not in ("user", "agent", "system"):
        return json.dumps(
            {"error": f"actor must be one of ['user', 'agent', 'system'], got {actor!r}", "code": -32602}
        )
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

    # Append audit log entry (drift invariant g: every vault_write audit log includes actor + timestamp + path)
    try:
        audit_path = (vault_root / vault_path).parent / ".vault_audit.log"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(f"{ts} actor={actor} path={vault_path}\n")
    except Exception:
        # Audit log write failure must NOT fail the vault write (already succeeded)
        pass

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
