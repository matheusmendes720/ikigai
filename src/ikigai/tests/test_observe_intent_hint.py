"""Tests for observe-node intent detection (Plan D Task D.1).

The observe node must emit a `plan_intent_hint` (str) when user_input
matches planning keywords (level high/medium via classify_intent), and
None (or absent) when user_input is empty or level is low.

This file follows the `from agents.v2.X import Y` style used by the rest
of the ikigai test suite (see test_v2_daily_skill.py header). The plan
brief's `from src.ikigai.agents.v2...` style is non-resolvable because
the actual on-disk layout is `<repo>/src/ikigai/src/agents/v2/...` (the
inner `src/` is what makes the bare `agents` package importable; see
conftest.py for the multi-tree path setup).
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — match test_v2_daily_skill.py so `from agents.v2.X` resolves.
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_IKIGAI_SRC = _THIS.parent.parent / "src"  # <repo>/src/ikigai/src/
if str(_IKIGAI_SRC) not in sys.path:
    sys.path.append(str(_IKIGAI_SRC))


def test_observe_emits_plan_intent_hint_for_high_keyword():
    state = {"user_input": "quero focar em X essa semana", "cycle_start": "2026-09-04"}
    from agents.v2.nodes.observe import observe_node

    updates = observe_node(state)
    assert "plan_intent_hint" in updates
    assert updates["plan_intent_hint"] is not None
    assert "/plan" in updates["plan_intent_hint"]


def test_observe_no_hint_for_low_keyword():
    state = {"user_input": "que horas sao", "cycle_start": "2026-09-04"}
    from agents.v2.nodes.observe import observe_node

    updates = observe_node(state)
    # Hint is None for low-intent (default stub returns level="low")
    assert updates.get("plan_intent_hint") is None


def test_observe_no_hint_when_user_input_empty():
    state = {"user_input": None, "cycle_start": "2026-09-04"}
    from agents.v2.nodes.observe import observe_node

    updates = observe_node(state)
    assert updates.get("plan_intent_hint") is None
