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

# Mirrors the _PROJECT_ROOT pattern used elsewhere in src/ikigai/src/agents/
# (5 parents up from src/ikigai/src/agents/ to reach the project root).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_VAULT_DIR = _PROJECT_ROOT / "vault"


@tool
def ikigai_read_strategics() -> str:
    """Load IKIGAI strategic instructions from ./vault/strategics/*.md.

    Returns the concatenated body of all strategic-tagged documents.
    Use this when you need to ground your reasoning in IKIGAI's strategic
    framework (PT-BR). Read-only — never writes.
    """
    ctx = load_strategics(_VAULT_DIR)
    return ctx.index if ctx.index else "(no strategic documents loaded)"


__all__ = ["ikigai_read_strategics"]
