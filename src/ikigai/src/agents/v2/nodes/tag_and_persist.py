"""tag_and_persist node — write the proposed_entity to vault (M89).

Direct invocation of wrap_vault_write from proposal_executor (lazy proxy).
Bypasses the deleted mcp_bridge.ikigai_tag_and_persist wrapper (M12).

Falls back to error_channel write on any exception (vault_write is
the canonical write path so failures should surface, not crash).
"""

from __future__ import annotations

import logging
from typing import Any

from ..state import IKIGAiStateDict

logger = logging.getLogger(__name__)


def tag_and_persist_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Persist proposed_entity to vault via wrap_vault_write (M89).

    Reads from state:
    - proposed_entity: BasePlanContract (Sonho/Objetivo/Meta/Projeto/Entrega/Tarefa)
    - vault_path: relative path under vault root
    - actor: "user" | "agent" | "system"

    Writes to state:
    - persisted: True on success
    - last_step: "tag_and_persist"
    - error_channel: list of error messages (graceful failure mode)
    """
    proposed = state.get("proposed_entity")
    vault_path = state.get("vault_path")
    actor = state.get("actor", "agent")

    if proposed is None or not vault_path:
        return {
            "persisted": False,
            "last_step": "tag_and_persist",
            "error_channel": ["tag_and_persist: missing proposed_entity or vault_path in state"],
        }

    # M89: lazy-import via proposal_executor (consolidates the
    # wrap_vault_write wiring in one module, easier to patch in tests).
    try:
        from v2.nodes.proposal_executor import wrap_vault_write
    except ImportError as exc:
        return {
            "persisted": False,
            "last_step": "tag_and_persist",
            "error_channel": [f"proposal_executor.wrap_vault_write import failed: {exc}"],
        }

    try:
        # Serialize proposed_entity for vault storage
        if hasattr(proposed, "model_dump"):
            fields = proposed.model_dump()
        elif isinstance(proposed, dict):
            fields = dict(proposed)
        else:
            fields = {"raw": str(proposed)}

        result = wrap_vault_write(
            actor=actor,
            vault_path=vault_path,
            fields=fields,
            rationale=state.get("user_request", "")[:200],
        )

        # wrap_vault_write returns ExecutionReport-like; normalize.
        ok = bool(getattr(result, "ok", False)) or (isinstance(result, dict) and result.get("ok"))
        err = (
            getattr(result, "error", None)
            or (result.get("error") if isinstance(result, dict) else None)
            or ""
        )

        return {
            "persisted": ok,
            "vault_path": vault_path,
            "actor": actor,
            "last_step": "tag_and_persist",
            "error_channel": [] if ok else [f"vault_write failed: {err or 'unknown'}"],
        }
    except Exception as exc:
        logger.warning("tag_and_persist failed: %s", exc)
        return {
            "persisted": False,
            "vault_path": vault_path,
            "actor": actor,
            "last_step": "tag_and_persist",
            "error_channel": [f"{type(exc).__name__}: {exc}"],
        }
