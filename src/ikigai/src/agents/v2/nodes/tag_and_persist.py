"""tag_and_persist node — persists proposed entity to vault (Plan A Task 8).

Per spec 2026-09-03-sonho-tree-hybrid-design §Architecture.
Sits between N6 plan and N8 commit in the v2 graph.

Phase 8.4: vault_write is wired via make_wrapped_vault_write().
_write is the ONLY legal vault writer (ADR-012 + ADR-029).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sys_ikigai.security.vault_write_wrapper import make_wrapped_vault_write

# Import as namespace (NOT `from ... import _resolve_vault_root`) so the
# forward-looking test's monkeypatch.setattr on the module attribute takes
# effect at call time. `from X import Y` would bind the original function
# at import time — monkeypatch would silently no-op (dual-module identity
# bug class per [[dual-module-identity-bug-class]]).
import src.ikigai.src.mcp_server.tools_vault as _tools_vault

from ..state import IKIGAiStateDict


def _vault_root_provider() -> Path:
    return _tools_vault._resolve_vault_root()


def _data_root_provider() -> Path:
    return _tools_vault._resolve_vault_root().parent / "data"


def _review_queue_dir_provider() -> Path:
    return _tools_vault._resolve_vault_root().parent / "data" / "review_queue"


_write = make_wrapped_vault_write(
    vault_root_provider=_vault_root_provider,
    data_root_provider=_data_root_provider,
    review_queue_dir_provider=_review_queue_dir_provider,
)


def tag_and_persist_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Persist proposed entity to vault via wrapped vault_write.

    _write is the ONLY legal vault writer (ADR-012 + ADR-029).

    Raises PermissionError if approval_state != "approved"
    (Phase 8.4 plan decision (e) — matches proposal_executor pattern).
    """
    # Drift gate: require approval_state == "approved" before any write.
    # Matches proposal_executor pattern (proposal_executor.py:113).
    # Must be OUTSIDE the try/except so pytest.raises can catch it.
    approval_state = state.get("approval_state")
    if approval_state != "approved":
        raise PermissionError(
            f"tag_and_persist_node refuses approval_state={approval_state!r}; "
            "must be 'approved'. See Phase 8.4 plan decision (e)."
        )

    try:
        entity = state.get("proposed_entity")
        vault_path = state.get("vault_path", "")
        actor = state.get("actor", "agent")

        if entity is None or not vault_path:
            return {
                "persisted": False,
                "error_type": "ValueError",
                "error_message": "tag_and_persist: proposed_entity and vault_path are required",
            }

        # Serialize entity to frontmatter dict.
        frontmatter_fields: dict[str, Any] = {}
        if hasattr(entity, "model_dump"):
            frontmatter_fields = entity.model_dump(mode="json")
        else:
            frontmatter_fields = dict(entity)

        result = _write(
            actor=actor,
            vault_path=vault_path,
            frontmatter_fields=frontmatter_fields,
            body="",
            legal_caller="tag_and_persist",
            entity=entity,
            vault_root=_vault_root_provider(),
        )
        return {"persisted": True, "vault_path": vault_path, "actor": actor}
    except Exception as e:
        return {"persisted": False, "error_type": type(e).__name__, "error_message": f"tag_and_persist: {e}"}
