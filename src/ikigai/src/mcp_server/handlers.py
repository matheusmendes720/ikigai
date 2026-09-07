"""IKIGAI MCP server tool handlers — logic layer (T10.X split).

This module owns the **logic bodies** for the IKIGAI MCP server's
tool handlers. The ``server.py`` module keeps the FastMCP instance +
the ``@MCP.tool(...)`` decorator wrappers.

Companion modules:
- ``server.py`` — FastMCP instance + @MCP.tool decorator wrappers
- ``tracing`` — init_mcp_tracing + traced_tool_dispatch
- ``tools_mesh`` / ``tools_vault`` / ``taskdog_tools`` — sub-tool modules

Architectural reference:
- ADR-013 — Planner-only
- ADR-012 — vault_write is sole vault writer
- ADR-031 — Investigation Queue tools live in their own module

V5-E (2026-09-07 "Opção B-A — radical-máxima") removed the 5 doomed
observation handlers (``_handle_ikigai_checkpoint``, ``_handle_ikigai_regime``,
``_handle_ikigai_phase``, ``_handle_ikigai_corrections``,
``_handle_ikigai_plan_cycle``) + 4 orphan helpers
(``_db_path``, ``_vault_root``, ``_extract_frontmatter_field``,
``_read_checkpoint``) — all read PAV-written vault artifacts and were
reclassified as anti-patterns per ADR-013 (planner-only). Only
``_handle_ikigai_decompose`` survives — it traverses the vault
hierarchy for a Dream UEID.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# UEID decompose handler (only surviving handler post-V5-E)
# ---------------------------------------------------------------------------
def _decompose_ueid(ueid: str) -> dict[str, Any]:
    """Traverse the vault hierarchy for a given Dream UEID.

    Vault root: {repo}/data/matheus/
    Structure: dreams/ → objectives/ → projects/ → tasks/
    """
    import frontmatter

    repo_root = Path(__file__).parent.parent.parent  # .../src/ikigai/src/mcp_server/ → src/ikigai/
    vault_root = repo_root / "data" / "matheus"

    def _slug_from_ueid(ueid: str) -> str:
        """Extract slug from UEID like ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609."""
        parts = ueid.split(":")
        return parts[2] if len(parts) >= 3 else ""

    def _read_entity(dir_name: str, slug: str) -> list[dict[str, Any]]:
        """Read all frontmatter records from a vault subdirectory."""
        entity_dir = vault_root / dir_name
        results: list[dict[str, Any]] = []
        if not entity_dir.is_dir():
            return results
        for md_file in entity_dir.iterdir():
            if not md_file.suffix == ".md":
                continue
            try:
                post = frontmatter.loads(md_file.read_text(encoding="utf-8"))
                results.append(
                    {
                        "file": str(md_file.relative_to(vault_root)),
                        "ueid": post.metadata.get("ueid", ""),
                        "title": post.metadata.get("title", md_file.stem),
                        "status": post.metadata.get("status", "UNKNOWN"),
                        "slug": post.metadata.get("slug", md_file.stem),
                        "parent_ueid": post.metadata.get("parent_ueid"),
                        "related_ueids": post.metadata.get("related_ueids", []),
                    }
                )
            except Exception:
                pass
        return results

    dream_slug = _slug_from_ueid(ueid)
    dream_file = vault_root / "dreams" / f"{dream_slug}.md"

    # Read dream
    dream_data = {}
    if dream_file.exists():
        try:
            post = frontmatter.loads(dream_file.read_text(encoding="utf-8"))
            dream_data = {
                "file": f"dreams/{dream_slug}.md",
                "ueid": post.metadata.get("ueid", ueid),
                "title": post.metadata.get("title", dream_slug),
                "status": post.metadata.get("status", "UNKNOWN"),
                "slug": post.metadata.get("slug", dream_slug),
            }
        except Exception:
            pass

    # Read all objectives / projects
    objectives = _read_entity("objectives", dream_slug)
    projects = _read_entity("projects", dream_slug)

    # Filter objectives to those whose parent_ueid or related_ueids match this dream
    dream_objectives = [
        o for o in objectives if o.get("parent_ueid") == ueid or ueid in o.get("related_ueids", [])
    ]
    dream_projects = [
        p for p in projects if p.get("parent_ueid") in [o.get("ueid") for o in dream_objectives]
    ]

    return {
        "dream": dream_data,
        "goals": [],
        "objectives": dream_objectives,
        "projects": dream_projects,
        "tasks": [],
    }


def _handle_ikigai_decompose(arguments: dict[str, Any]) -> str:
    """Traverse the vault hierarchy for a given Dream UEID (active handler)."""
    ueid = arguments.get("dream_ueid", "")
    if not ueid:
        return json.dumps({"error": "dream_ueid required"})
    return json.dumps(_decompose_ueid(ueid), indent=2)


__all__ = [
    "_decompose_ueid",
    "_handle_ikigai_decompose",
]
