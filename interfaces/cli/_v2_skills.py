"""_v2_skills — skill dispatch for IKIGAI v2 graph.

Provides:
- load_skill_manifest(name): parse YAML frontmatter from skills/{name}.md
- invoke_skill(skill_name, **kwargs): dispatch make_v2_graph() with entry_point
- ensure_mcp_server_bound(): idempotent production binding

This module is lazy-imported inside v2.py command bodies to break
the circular import (v2.py ↔ agents.v2.subgraph ↔ agents.v2.nodes.proposal_executor).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Compute repo root from this file's location (interfaces/cli/_v2_skills.py)."""
    return Path(__file__).resolve().parents[2]


def load_skill_manifest(name: str) -> dict[str, Any]:
    """Parse YAML frontmatter from skills/{name}.md.

    Returns the manifest dict including `entry_point` field.
    Raises FileNotFoundError if the skill file doesn't exist.
    """
    skill_path = (
        _repo_root()
        / "src"
        / "ikigai"
        / "src"
        / "agents"
        / "v2"
        / "skills"
        / f"{name}.md"
    )
    raw = skill_path.read_text(encoding="utf-8")
    # Strip Pandoc-style YAML frontmatter (--- delimiters)
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            parsed = yaml.safe_load(raw[3:end])
            if parsed:
                return dict(parsed)
    return {}


def _build_initial_state(skill_name: str, date_str: str) -> dict[str, Any]:
    """Build a minimal IKIGAiStateDict for the given skill and date."""
    today = date.fromisoformat(date_str) if date_str else date.today()
    return {
        "cycle_id": f"ikigai-{skill_name}-{date_str}",
        "cycle_start": date_str,
        "cycle_end": date_str,
        "iteration": 0,
        "vault_root": "vault",
        "regime_state": "MAINTAIN",
        "q_he_score": 0.65,
        "days_in_regime": 3,
        "is_hysteresis_active": False,
        "phase": "BUSCA",
        "phase_iteration": 0,
        "phase_converged": False,
        "phase_weights": {
            "passion": 0.5,
            "skill": 0.5,
            "market": 0.5,
            "revenue": 0.5,
            "course": 0.5,
        },
        "vector_scores": {
            "passion": 0.7,
            "skill": 0.7,
            "market": 0.6,
            "revenue": 0.6,
            "course": 0.7,
        },
        "meta_vector_score": 0.66,
        "workload_estimate": 4.0,
        "capacity_estimate": 8.0,
        "balancer_verdict": "OK",
    }


def invoke_skill(skill_name: str, date_str: str | None = None) -> dict[str, Any]:
    """Dispatch the v2 graph for the named skill.

    Args:
        skill_name: one of "daily", "weekly", "monthly", "quarterly"
        date_str: YYYY-MM-DD string; defaults to today

    Returns:
        dict with skill name, date, and graph output dict
    """
    from src.ikigai.src.agents.v2.graph import make_v2_graph

    manifest = load_skill_manifest(skill_name)
    entry_point: str = manifest.get("entry_point", "observe")
    date_str = date_str or str(date.today())

    compiled = make_v2_graph(entry_point=entry_point)
    initial_state = _build_initial_state(skill_name, date_str)

    result = compiled.invoke(
        initial_state,
        config={"configurable": {"thread_id": f"{skill_name}-{date_str}"}},
    )

    return {
        "skill": manifest.get("name", f"ikigai-{skill_name}"),
        "date": date_str,
        entry_point: result,
    }


def ensure_mcp_server_bound() -> None:
    """Idempotently bind the production MCP server to mcp_bridge._server.

    Uses dotted-prefix setter per dual-module-identity bug class.
    Does nothing if _server is already bound.
    """
    # Import inside to avoid activating the subprocess until needed.
    # Note: mcp_client.py exports bind_server_to_gateway (NOT bind_prod_server).
    # mcp_bridge.py re-exports it as bind_prod_server, so we import from
    # mcp_bridge to get the canonical name.
    from src.ikigai.src.agents.v2 import mcp_bridge as _bridge_mod
    from src.ikigai.src.agents.v2 import mcp_client as _mcp_client_mod

    if _bridge_mod._server is not None:
        return  # already bound — idempotent

    # bind_server_to_gateway is the factory in mcp_client.py
    server = _mcp_client_mod.bind_server_to_gateway("src.mcp_server.server")
    # Dotted-prefix setter: assign to the actual module, not a local var
    _bridge_mod._server = server
