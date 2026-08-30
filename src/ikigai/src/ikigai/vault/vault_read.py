"""vault_read — read-side mirror of vault_write.

Mirror of vault_write's security model (path traversal guard, VaultLock).
Read-only — never writes. Exposed as `vault_read` MCP tool.

Security:
  - Rejects absolute paths
  - Rejects paths resolving outside vault_root
  - VaultLock for cross-platform concurrency safety

Concurrency:
  - VaultLock for cross-platform concurrency safety
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import frontmatter

from .lock import VaultLock


def vault_read(vault_root: Path, vault_path: str) -> dict[str, Any]:
    """Read markdown file from vault. Returns parsed frontmatter + body.

    Args:
        vault_root: vault root directory (anchor for path resolution)
        vault_path: relative path within vault/, e.g. "plans/q3/task-x.md"

    Returns:
        {frontmatter: dict, body: str, sha256: str, mtime: float}

    Raises:
        ValueError: if vault_path is absolute or resolves outside vault_root
        FileNotFoundError: if the resolved file does not exist
    """
    # Security: reject absolute paths (mirror vault_write:66-67)
    if Path(vault_path).is_absolute():
        raise ValueError(f"absolute path rejected: {vault_path!r}")

    # Security: resolve and check it's inside vault_root (mirror vault_write:70-75)
    target = (vault_root / vault_path).resolve()
    vault_root_resolved = vault_root.resolve()
    try:
        target.relative_to(vault_root_resolved)
    except ValueError as exc:
        raise ValueError(f"path {vault_path!r} resolves outside vault root") from exc

    if not target.exists():
        raise FileNotFoundError(f"vault file not found: {vault_path!r}")

    lock_path = vault_root / ".vault.lock"
    with VaultLock(lock_path):
        # frontmatter.loads() parses both frontmatter (YAML) and body
        post = frontmatter.loads(target.read_text(encoding="utf-8"))
        body = post.content
        fm_dict = dict(post.metadata)
        sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
        mtime = target.stat().st_mtime

    return {
        "frontmatter": fm_dict,
        "body": body,
        "sha256": sha256,
        "mtime": mtime,
    }


__all__ = ["vault_read"]
