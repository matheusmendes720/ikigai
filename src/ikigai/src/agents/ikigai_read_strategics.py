"""ikigai_read_strategics — loads PT-BR strategic docs as agent context.

Per attribution report §1 (2026-08-29), ./strategics/ PT-BR markdown is the
single source of truth for IKIGAI agent instructions. This tool surfaces
the loaded StrategicsContext.index as a string the LLM can read.

Append-only invariant: this tool NEVER writes.
"""
from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool
from src.ikigai.src.strategics.loader import load_strategics


def _get_vault_dir() -> Path:
    """Lazily resolve vault root at call time.

    5 parents up from src/ikigai/src/agents/ reaches the project root.
    Resolved on every call so tests can monkeypatch this function to
    point at a temp vault without polluting the project's real vault.
    """
    return Path(__file__).resolve().parent.parent.parent.parent.parent / "vault"


@tool
def ikigai_read_strategics() -> str:
    """Load IKIGAI strategic instructions from ./vault/strategics/*.md.

    Returns the concatenated body of all strategic-tagged documents.
    Use this when you need to ground your reasoning in IKIGAI's strategic
    framework (PT-BR). Read-only — never writes.
    """
    ctx = load_strategics(_get_vault_dir())
    return ctx.index if ctx.index else "(no strategic documents loaded)"


__all__ = ["ikigai_read_strategics"]
