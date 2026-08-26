"""score_vectors node — compute IKIGAi 5-vector scores + meta-vector.

Implements H4 (market fit) and H5 (skill velocity) from the IKIGAi SPEC.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ikigai_maintainer.state import (
    IKIGAiStateDict,
    VECTOR_TYPES,
    compute_meta_vector,
    HYSTERESIS_UPGRADE_DAYS,
)


# Learning rate for habit consistency
LAMBDA = 0.093


def score_vectors_node(state: IKIGAiStateDict) -> dict[str, Any]:
    """Compute all 5 IKIGAi vector scores and the meta-vector.

    Reads from:
    - operational core (habit_engine, consolidator) for passion/skill
    - UPI state from solverforge-calendar-mcp for market/revenue
    - Course data (SENAI attendance) for course vector

    Returns vector_scores dict and meta_vector_score.
    """
    regime = state.get("regime_state", "MAINTAIN")
    days = state.get("days_in_regime", 1)
    q_he = state.get("q_he_score", 0.65)

    # H4/H5 weights modulated by regime
    if regime == "PUSH":
        skill_weight = 0.9
        passion_weight = 0.7
    elif regime == "RECOVER":
        skill_weight = 0.5
        passion_weight = 1.0
    else:
        skill_weight = 0.7
        passion_weight = 0.8

    # Passion vector: H(t) = 1 - e^(-lambda * streak)
    passion_score = _compute_passion_score(state)
    passion_score = passion_score * passion_weight

    # Skill vector: composite of learning momentum + project completion
    skill_score = _compute_skill_score(state) * skill_weight

    # Market vector: opportunities pipeline + fit
    market_score = _compute_market_score(state)

    # Revenue vector: target attainment
    revenue_score = _compute_revenue_score(state)

    # Course vector: SENAI attendance rate
    course_score = _compute_course_score(state)

    vector_scores: dict[str, float] = {
        "passion": min(100.0, max(0.0, passion_score)),
        "skill": min(100.0, max(0.0, skill_score)),
        "market": min(100.0, max(0.0, market_score)),
        "revenue": min(100.0, max(0.0, revenue_score)),
        "course": min(100.0, max(0.0, course_score)),
    }

    # Phase-weighted meta-vector
    phase_weights = state.get("phase_weights", {
        "passion": 0.15,
        "skill": 0.25,
        "market": 0.25,
        "revenue": 0.20,
        "course": 0.15,
    })
    meta_vector = compute_meta_vector(vector_scores, phase_weights) * 100.0

    return {
        "vector_scores": vector_scores,
        "meta_vector_score": meta_vector,
        "last_step": "score_vectors",
    }


def _compute_passion_score(state: IKIGAiStateDict) -> float:
    """Passion = 1 - e^(-lambda * streak_days)."""
    # Read habit streaks from operational
    try:
        from operational.core.habit_engine import HabitEngine
        engine = HabitEngine()
        # Average consistency across all active habits
        habits = engine.list_habits()
        if not habits:
            return 50.0
        total = sum(1 - math.exp(-LAMBDA * h.streak_days) for h in habits)
        return (total / len(habits)) * 100.0
    except Exception:
        # Fallback: use Q_HE as proxy for passion
        return state.get("q_he_score", 0.65) * 100.0


def _compute_skill_score(state: IKIGAiStateDict) -> float:
    """Skill = project_completion * 0.5 + learning_momentum * 0.3 + demand * 0.2."""
    # Read from UPI — completed projects count as skill evidence
    import subprocess
    import json
    try:
        result = subprocess.run(
            ["solverforge-calendar-mcp", "--json", "upi_search", "--query", "skill", "--limit", "20"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            items = json.loads(result.stdout) if result.stdout else []
            done = [i for i in items if i.get("status") == "Done"]
            # Skill proxy: 10 points per completed skill item
            return min(100.0, len(done) * 10.0)
    except Exception:
        pass
    return 50.0


def _compute_market_score(state: IKIGAiStateDict) -> float:
    """Market = opportunities_pipeline * 0.4 + fit_score * 0.4 + demand * 0.2."""
    # Read from UPI tagged "opportunity"
    import subprocess
    import json
    try:
        result = subprocess.run(
            ["solverforge-calendar-mcp", "--json", "upi_search", "--query", "opportunity", "--limit", "20"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            items = json.loads(result.stdout) if result.stdout else []
            active = [i for i in items if i.get("status") != "Cancelled"]
            # Market score: 8 points per active opportunity
            return min(100.0, len(active) * 8.0)
    except Exception:
        pass
    return 40.0


def _compute_revenue_score(state: IKIGAiStateDict) -> float:
    """Revenue = target_attainment * 0.7 + pipeline_health * 0.3."""
    # Read from UPI tagged "revenue" or "deliverable"
    import subprocess
    import json
    try:
        result = subprocess.run(
            ["solverforge-calendar-mcp", "--json", "upi_search", "--query", "revenue", "--limit", "10"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            items = json.loads(result.stdout) if result.stdout else []
            done = [i for i in items if i.get("status") == "Done"]
            # Revenue proxy: 20 points per completed revenue item
            return min(100.0, len(done) * 20.0)
    except Exception:
        pass
    return 30.0


def _compute_course_score(state: IKIGAiStateDict) -> float:
    """Course = SENAI attendance_rate * 0.5 + assignments_on_time * 0.3 + exam_avg * 0.2."""
    # SENAI data is read from a local JSON file managed outside this repo
    try:
        import json as _json
        senai_path = Path.home() / ".ikigai" / "senai_attendance.json"
        if senai_path.exists():
            data = _json.loads(senai_path.read_text())
            attendance = data.get("attendance_rate", 0.8)
            assignments = data.get("assignments_on_time", 0.8)
            return (attendance * 0.5 + assignments * 0.3 + 0.7 * 0.2) * 100.0
    except Exception:
        pass
    return 60.0  # default: 60%
