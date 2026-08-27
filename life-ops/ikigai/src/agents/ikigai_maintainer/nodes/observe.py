"""observe node — read sensors and populate initial state.

Reads Q_HE from policy_engine, workload from habit_engine, and UPI state
from the solverforge-calendar-mcp via subprocess.
"""
from __future__ import annotations

import subprocess
import json
from pathlib import Path
from typing import Any

from ..state import (
    IKIGAiStateDict,
    DEFAULT_CAPACITY_HOURS_PER_DAY,
    DEFAULT_WORKLOAD_OVERLOAD_FACTOR,
    DEFAULT_WORKLOAD_UNDERLOAD_FACTOR,
    DEFAULT_QHE_PUSH,
    DEFAULT_QHE_RECOVER,
)


def observe_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Read sensors: Q_HE score, workload estimate, capacity estimate.

    Reads from:
    - operational.core.policy_engine (via direct import when available)
    - solverforge-calendar-mcp upi_list (subprocess call)

    Chat mode: if user_input is present, accumulate into messages and
    emit agent response as the new message.

    Returns dict to merge into state.
    """
    updates: dict[str, Any] = {
        "last_step": "observe",
    }

    # Chat mode — accumulate user message and emit agent response
    user_input = state.get("user_input")
    if user_input:
        # Build agent response from current computed state
        agent_response = _build_agent_response(state)
        updates["messages"] = [{"role": "user", "content": user_input}]
        updates["agent_response"] = agent_response
        updates["user_input"] = None  # clear scratchpad

    # Read Q_HE from operational policy_engine (import when available)
    q_he_score = _read_qhe_from_operational()
    workload_estimate = _read_workload_from_upi()
    capacity_estimate = DEFAULT_CAPACITY_HOURS_PER_DAY

    # Determine regime from Q_HE
    if q_he_score >= DEFAULT_QHE_PUSH:
        regime = "PUSH"
    elif q_he_score >= DEFAULT_QHE_RECOVER:
        regime = "MAINTAIN"
    else:
        regime = "RECOVER"

    # Determine balancer verdict
    workload_ratio = workload_estimate / max(capacity_estimate, 1.0)
    if q_he_score < DEFAULT_QHE_RECOVER:
        balancer = "RECOVER"
    elif workload_ratio >= DEFAULT_WORKLOAD_OVERLOAD_FACTOR:
        balancer = "OVERLOAD"
    elif workload_ratio <= DEFAULT_WORKLOAD_UNDERLOAD_FACTOR:
        balancer = "UNDERLOAD"
    else:
        balancer = "OK"

    updates.update({
        "q_he_score": q_he_score,
        "workload_estimate": workload_estimate,
        "capacity_estimate": capacity_estimate,
        "regime_state": regime,
        "balancer_verdict": balancer,
    })
    return updates


def _build_agent_response(state: IKIGAiStateDict) -> str:
    """Build a readable agent response from current IKIGAi state."""
    vs = state.get("vector_scores", {})
    lines = [
        f"🧭 Regime: {state.get('regime_state', '?')}  |  Q_HE: {state.get('q_he_score', 0):.4f}",
        f"   Phase: {state.get('phase', '?')}  |  Verdict: {state.get('balancer_verdict', '?')}",
        "",
        "📊 IKIGAi Vectors:",
    ]
    for vec, score in vs.items():
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        lines.append(f"   {vec.capitalize():12s}  [{bar}]  {score:.1f}")
    lines.append(f"   {'Meta-vector':12s}  {state.get('meta_vector_score', 0):.1f}")
    corrections = state.get("corrections", [])
    if corrections:
        lines.append(f"\n⚠️  Corrections ({len(corrections)}):")
        for c in corrections[-3:]:
            lines.append(f"   [{c.get('heuristic')}] {c.get('description', '')}")
    else:
        lines.append(f"\n✅ No corrections — system balanced")
    prospective = state.get("prospective_buffer", [])
    if prospective:
        lines.append(f"\n📋 Prospective buffer ({len(prospective)}):")
        for p in prospective[-3:]:
            lines.append(f"   • {p}")
    return "\n".join(lines)


def _read_qhe_from_operational() -> float:
    """Read current Q_HE score from operational policy_engine.

    Falls back to 0.65 (median MAINTAIN target) if unavailable.
    """
    try:
        from operational.core.policy_engine import PolicyEngine

        engine = PolicyEngine()
        eval_result = engine.evaluate()
        return eval_result.qhe
    except Exception:
        # Operational not on PYTHONPATH or evaluation fails — use default
        return 0.65


def _read_workload_from_upi() -> float:
    """Read today's task count from solverforge-calendar-mcp.

    Returns hours/day estimate based on active UPI count.
    """
    try:
        result = subprocess.run(
            [
                "solverforge-calendar-mcp",
                "--json",
                "upi_list",
                "--limit",
                "50",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            items = data if isinstance(data, list) else []
            # Estimate 1.5h per active task per day
            active = [i for i in items if i.get("status") not in ("Done", "Cancelled")]
            return len(active) * 1.5
    except Exception:
        pass
    return 2.0  # default: 2h/day estimate
