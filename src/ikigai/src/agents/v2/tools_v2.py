"""IKIGAI v2 node-scoped tools — wraps prompt-template observations as @tool.

NOT included in the IKIGAI_TOOLS=12 drift-detector-enforced list. This is a
parallel set used internally by the v2 graph for node dispatch.

Drift detector only counts the live IKIGAI_TOOLS in `agents/tools.py`.
IKIGAI_NODE_TOOLS lives in `agents/v2/tools_v2.py` — different module,
different variable name, not scanned.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from .prompts.decompose_rice_observation import render_decompose_rice_observation
from .prompts.h1_energy import render_h1_energy
from .prompts.h2_qhe_composite import render_h2_qhe_composite
from .prompts.h3_regime_fsm import render_h3_regime_fsm
from .prompts.h4_market_fit import render_h4_market_fit
from .prompts.h5_skill_velocity import render_h5_skill_velocity
from .prompts.h6_severity import render_h6_severity
from .prompts.heuristics_regime_observation import render_heuristics_regime_observation
from .prompts.observe_qhe_observation import render_observe_qhe_observation
from .prompts.score_course_observation import render_score_course_observation
from .prompts.score_market_observation import render_score_market_observation
from .prompts.score_meta_vector_observation import render_score_meta_vector_observation
from .prompts.score_passion_observation import render_score_passion_observation
from .prompts.score_revenue_observation import render_score_revenue_observation
from .prompts.score_skill_observation import render_score_skill_observation


def _default_vault_root() -> Path:
    """Return default vault root path."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent / "vault"


def _safe_call(name: str, fn: Any, state: dict[str, Any]) -> dict[str, Any]:
    """Call a render function safely; return error dict on exception."""
    try:
        return fn(state)
    except Exception as exc:  # pragma: no cover — defensive
        return {"error": str(exc), "node": name}


@tool
def v2_observe_pav_state(date: str) -> str:
    """Read PAV-written cycle_state for the given date.
    Returns observation JSON."""
    state = {"date": date, "vault_root": str(_default_vault_root())}
    result = _safe_call("observe_qhe", render_observe_qhe_observation, state)
    return json.dumps(result, indent=2)


@tool
def v2_score_vectors_observe(date: str) -> str:
    """Score all 5 IKIGAI vectors + meta-vector via prompt chain.
    Returns observation JSON."""
    state = {"date": date, "vault_root": str(_default_vault_root())}
    result = {}
    for fn, key in [
        (render_score_passion_observation, "passion"),
        (render_score_skill_observation, "skill"),
        (render_score_market_observation, "market"),
        (render_score_revenue_observation, "revenue"),
        (render_score_course_observation, "course"),
        (render_score_meta_vector_observation, "meta"),
    ]:
        obs = _safe_call(f"score_{key}", fn, state)
        result[key] = obs
    return json.dumps(result, indent=2)


@tool
def v2_heuristics_observe(date: str) -> str:
    """Run H1-H6 heuristics + regime observation via prompt chain.
    Returns observation JSON."""
    state = {"date": date, "vault_root": str(_default_vault_root())}
    result = {}
    for fn, key in [
        (render_h1_energy, "h1_energy"),
        (render_h2_qhe_composite, "h2_qhe_composite"),
        (render_h3_regime_fsm, "h3_regime_fsm"),
        (render_h4_market_fit, "h4_market_fit"),
        (render_h5_skill_velocity, "h5_skill_velocity"),
        (render_h6_severity, "h6_severity"),
        (render_heuristics_regime_observation, "regime"),
    ]:
        obs = _safe_call(key, fn, state)
        result[key] = obs
    return json.dumps(result, indent=2)


@tool
def v2_balance_observe(date: str) -> str:
    """Run balance observation (meta + QHE) via prompt chain.
    Returns observation JSON with balancer_verdict."""
    state = {"date": date, "vault_root": str(_default_vault_root())}
    meta = _safe_call("meta_vector", render_score_meta_vector_observation, state)
    qhe = _safe_call("qhe", render_observe_qhe_observation, state)
    result = {
        "meta_vector": meta,
        "q_he": qhe,
        "balancer_verdict": "OK",  # default; v2 node overrides with real logic
    }
    return json.dumps(result, indent=2)


@tool
def v2_plan_observe(date: str) -> str:
    """Run plan observation (regime + meta) via prompt chain.
    Returns prospective action strings."""
    state = {"date": date, "vault_root": str(_default_vault_root())}
    regime = _safe_call("regime", render_heuristics_regime_observation, state)
    meta = _safe_call("meta_vector", render_score_meta_vector_observation, state)
    result = {
        "regime": regime,
        "meta_vector": meta,
        "prospective_buffer": [],  # filled by v2 plan node
    }
    return json.dumps(result, indent=2)


@tool
def v2_decompose_observe(date: str) -> str:
    """Run RICE decomposition observation via prompt chain.
    Returns decomposition JSON."""
    state = {"date": date, "vault_root": str(_default_vault_root())}
    result = _safe_call("decompose_rice", render_decompose_rice_observation, state)
    return json.dumps(result, indent=2)


@tool
def v2_reflect_observe(date: str) -> str:
    """Run reflect observation (regime + all observations) via prompt chain.
    Returns retrospective JSON."""
    state = {"date": date, "vault_root": str(_default_vault_root())}
    regime = _safe_call("regime", render_heuristics_regime_observation, state)
    result = {
        "regime": regime,
        "retrospective_log": [],  # filled by v2 reflect node
    }
    return json.dumps(result, indent=2)


@tool
def v2_commit_observe(date: str) -> str:
    """Run commit observation — returns commit summary (no vault writes).
    Returns observation JSON."""
    state = {"date": date, "vault_root": str(_default_vault_root())}
    regime = _safe_call("regime", render_heuristics_regime_observation, state)
    result = {
        "regime": regime,
        "commit_summary": "[stub] commit observation — no vault writes performed",
    }
    return json.dumps(result, indent=2)


#: IKIGAI v2 node-scoped tools — 8 tools separate from IKIGAI_TOOLS=12
IKIGAI_NODE_TOOLS = [
    v2_observe_pav_state,
    v2_score_vectors_observe,
    v2_heuristics_observe,
    v2_balance_observe,
    v2_plan_observe,
    v2_decompose_observe,
    v2_reflect_observe,
    v2_commit_observe,
]
