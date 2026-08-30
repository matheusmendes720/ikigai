"""vault_write — ONLY vault writer per attribution report §7.

Wraps VaultLock + atomic file write for safe concurrent markdown writes.
All vault writes (deep agent, native CLI, forks) MUST go through this
function (exposed as `vault_write` MCP tool).

Security:
  - Rejects absolute paths
  - Rejects paths that resolve outside vault_root (path traversal blocked)
  - Rejects empty body + empty frontmatter (no-op protection)

Concurrency:
  - VaultLock (existing) for cross-platform file locking

Atomicity:
  - Writes to a tmp file via frontmatter.dumps() (NOT frontmatter.dump(),
    which only does f.write() — NOT atomic), then os.replace()s to target.
    os.replace() is atomic on POSIX and silently replaces an existing target
    on Windows; Path.rename() calls os.rename(), which on Windows raises
    FileExistsError if the target exists. This pattern matches save_state()
    at sync.py:198-202 (B6.4 lesson).

NOTE: function is SYNC (NOT async). MCP handlers in this repo are sync —
they return JSON strings, never await anything.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

import frontmatter

from .lock import VaultLock


def vault_write(
    vault_root: Path,
    vault_path: str,
    frontmatter_fields: dict[str, Any],
    body: str,
) -> dict[str, Any]:
    """Write markdown file to vault. ONLY writer per attribution §7.

    Args:
        vault_root: vault root directory (anchor for path resolution)
        vault_path: relative path within vault/, e.g. "plans/q3/task-x.md"
        frontmatter_fields: dict of YAML frontmatter key/values
        body: markdown body below frontmatter

    Returns:
        {written: bool, vault_path: str, sha256: str}

    Raises:
        ValueError: if vault_path is absolute, escapes vault_root,
                    or body+frontmatter both empty
    """
    # No-op protection
    if not frontmatter_fields and not body.strip():
        raise ValueError("empty body and frontmatter rejected (no-op)")

    # Security: reject absolute paths
    if Path(vault_path).is_absolute():
        raise ValueError(f"absolute path rejected: {vault_path!r}")

    # Security: resolve and check it's inside vault_root
    target = (vault_root / vault_path).resolve()
    vault_root_resolved = vault_root.resolve()
    try:
        target.relative_to(vault_root_resolved)
    except ValueError as exc:
        raise ValueError(
            f"path {vault_path!r} resolves outside vault root"
        ) from exc

    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = vault_root / ".vault.lock"

    # Serialize post to string (uses frontmatter.dumps, NOT frontmatter.dump
    # which only does f.write — NOT atomic).
    post = frontmatter.Post(content=body, **frontmatter_fields)
    body_str = frontmatter.dumps(post)

    with VaultLock(lock_path):
        # Atomic write: write to tmp file in same dir, then os.replace.
        # Same dir guarantees os.replace is atomic on POSIX (rename within
        # same filesystem) and silently replaces on Windows. Cross-dir
        # rename can fail on Windows if target dir is on a different
        # drive — vault_root is the parent of target, so this is safe.
        fd, tmp_path = tempfile.mkstemp(
            prefix=".tmp_vault_write_", dir=str(vault_root)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(body_str)
                # frontmatter.dumps() ends with a newline already, but be
                # defensive — never leave a file without trailing newline.
                if not body_str.endswith("\n"):
                    f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        except Exception:
            # Clean up tmp file on any failure (write error, fsync error,
            # os.replace error). Without this, a failed write would leave
            # the tmp file behind.
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise

    sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
    return {
        "written": True,
        "vault_path": vault_path,
        "sha256": sha256,
    }


__all__ = ["vault_write"]
