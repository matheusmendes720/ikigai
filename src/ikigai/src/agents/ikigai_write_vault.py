"""ikigai_write_vault — writes vault markdown via the vault_write backend.

Mirrors ikigai_read_vault's path resolution pattern. Wraps
``sys_ikigai.vault.vault_write.vault_write()`` with three modes:

- ``append`` (default) — read existing file, append body, merge frontmatter
  (new keys override existing). If file does not exist, behaves like create.
- ``create`` — fail if file already exists; otherwise write new content +
  frontmatter.
- ``update`` — replace the entire file (frontmatter + body) with the new
  content. No merge with existing.

Security model mirrors ``vault_write``:

- Rejects absolute paths
- Rejects paths that resolve outside ``vault_root`` (path traversal blocked)
- Append-only invariant preserved (each write is logged to ``.vault_audit.log``)

CRITICAL: this tool writes to vault but should NEVER auto-execute on its own —
must be invoked by an agent that the user has approved. The ``actor=agent``
parameter on the backend marks the write for the audit trail.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from sys_ikigai.vault.vault_read import vault_read
from sys_ikigai.vault.vault_write import vault_write


def _get_vault_dir() -> Path:
    """Lazily resolve vault root at call time.

    5 parents up from ``src/ikigai/src/agents/`` reaches the project root.
    Resolved on every call so tests can monkeypatch this function to
    point at a temp vault without polluting the project's real vault.
    """
    return Path(__file__).resolve().parent.parent.parent.parent.parent / "vault"


_VALID_MODES: tuple[str, ...] = ("append", "create", "update")


@tool
def ikigai_write_vault(
    vault_path: str,
    content: str,
    frontmatter: dict[str, Any] | None = None,
    mode: str = "append",
) -> str:
    """Write markdown to vault. Returns JSON with ok/path/sha256/mtime on success.

    Args:
        vault_path: relative path within vault/, e.g. "plans/q3/task-x.md"
        content: markdown body content (the section below frontmatter)
        frontmatter: optional dict of YAML frontmatter key/values
        mode: "append" (default — merge with existing), "create" (fail if
            exists), or "update" (replace entire file)

    Returns:
        JSON string. On success: ``{"ok": true, "path": ..., "sha256": ...,
        "mtime": <float>}``. On failure: ``{"ok": false, "error": ...,
        "vault_path": ...}``.

    Security: this tool MUST only be invoked by an agent that the user has
    approved. It does not auto-execute. Each call records ``actor=agent``
    in the vault audit log.
    """
    if mode not in _VALID_MODES:
        return json.dumps({
            "ok": False,
            "error": f"invalid mode {mode!r}; must be one of {list(_VALID_MODES)}",
            "vault_path": vault_path,
        })

    vault_root = _get_vault_dir()
    fm_input: dict[str, Any] = frontmatter or {}

    try:
        # "create" mode: fail if file already exists (pre-check; backend
        # would overwrite, but we want explicit "create" semantics).
        if mode == "create":
            target = (vault_root / vault_path).resolve()
            if target.exists():
                return json.dumps({
                    "ok": False,
                    "error": f"file already exists: {vault_path!r}",
                    "vault_path": vault_path,
                })

        # "append" mode: read existing, append body, merge frontmatter.
        # If file does not exist, treat as a fresh write (same as create).
        if mode == "append":
            try:
                existing = vault_read(vault_root, vault_path)
            except FileNotFoundError:
                existing = None

            if existing is not None:
                existing_body = (existing.get("body") or "").rstrip()
                new_body = (content or "").rstrip()
                # Merge frontmatter: new keys win over existing keys.
                merged_fm = {**(existing.get("frontmatter") or {}), **fm_input}
                # Concatenate bodies with a blank-line separator.
                if existing_body and new_body:
                    combined_body = existing_body + "\n\n" + new_body
                else:
                    combined_body = existing_body + new_body
                fm_to_write = merged_fm
                body_to_write = combined_body
            else:
                fm_to_write = fm_input
                body_to_write = content
        else:
            # "create" or "update": use provided content + frontmatter as-is.
            fm_to_write = fm_input
            body_to_write = content

        # Call backend. actor="agent" marks this as an agent-driven write in
        # the vault audit log (drift invariant g).
        result = vault_write(
            vault_root=vault_root,
            vault_path=vault_path,
            frontmatter_fields=fm_to_write,
            body=body_to_write,
            actor="agent",
        )

        # Compute mtime of the freshly-written file (backend does not return it).
        target_path = vault_root / vault_path
        mtime = target_path.stat().st_mtime if target_path.exists() else 0.0

        return json.dumps({
            "ok": True,
            "path": vault_path,
            "sha256": result["sha256"],
            "mtime": mtime,
        })
    except ValueError as e:
        return json.dumps({"ok": False, "error": str(e), "vault_path": vault_path})
    except Exception as e:  # pragma: no cover — defensive guard
        return json.dumps({
            "ok": False,
            "error": f"unexpected error: {type(e).__name__}: {e}",
            "vault_path": vault_path,
        })


__all__ = ["ikigai_write_vault"]