"""surface_intentions node — surface PAV-written state as user-facing suggestions.

Reads cycle_state + daily reports from vault and emits 3-5 pt-BR suggestions.
Runs AFTER commit (9th node); reads PAV state, does NOT write.
"""

from __future__ import annotations

from typing import Any

from ..prompts.surface_pav_intentions import render_surface_pav_intentions


def surface_intentions_node(state: dict[str, Any]) -> dict[str, Any]:
    """Surface PAV state as user-facing suggestions."""
    observation = render_surface_pav_intentions(state)
    suggestions = observation.get("suggestions", [])
    return {
        "user_suggestions": suggestions,
        "suggestions_count": len(suggestions),
        "suggestions_language": observation.get("language", "pt-BR"),
        "last_step": "surface_intentions",
    }
