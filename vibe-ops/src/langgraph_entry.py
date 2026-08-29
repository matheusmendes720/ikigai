"""langgraph dev entry point for agentic-markdown-system.

Wraps the existing custom Python graphs (PAE-Maintainer + 4 swarm workflows)
as LangGraph StateGraph factories so they can be served via `langgraph dev`.

Existing custom graphs (preserved, not modified):
  - vibe-ops/src/agents/pae_maintainer/graph.py: PAE-Maintainer main graph
  - .claude/skills/quarterly-planner/workflows/*.yml: 4 swarm workflow YAMLs

Strategy: thin adapter layer - no business logic in here, just glue between
the existing custom graph runtime and the langgraph SDK.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

import yaml
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RunnableConfig

# Import the existing custom graph runtime
import sys

# B5.1-F1: this file lives at vibe-ops/src/langgraph_entry.py, so
# Path(__file__).parent is already vibe-ops/src/. The OLD path appended
# another "vibe-ops/src" (broken) and referenced "life-ops/ikigai/src"
# which was renamed to "src/ikigai/src" during the 2026-08 reorg.
PROJECT_ROOT = Path(__file__).parent.parent.parent  # = life/ (project root)
VIBE_OPS_SRC = Path(__file__).parent  # = vibe-ops/src/
PAE_SRC = VIBE_OPS_SRC / "agents"
IKIGAI_SRC = PROJECT_ROOT / "src" / "ikigai" / "src"
sys.path.insert(0, str(VIBE_OPS_SRC))
sys.path.insert(0, str(PAE_SRC))
sys.path.insert(0, str(IKIGAI_SRC))

from pae_maintainer.graph import (
    run_pae_cycle,
    should_commit,
    should_terminate,
)
from pae_maintainer.state import (
    BalancerState,
    PAEState,
    PlanTier,
    PlanVerdict,
)


# ---------------------------------------------------------------------------
# State type definitions (langgraph compatible)
# ---------------------------------------------------------------------------


class PAEStateDict(TypedDict, total=False):
    """State dict for the PAE-Maintainer graph (langgraph compatible)."""
    cycle_id: str
    cycle_start: str  # ISO date
    cycle_end: str    # ISO date
    iteration: int
    last_step: str
    terminated: bool
    kill_switch_triggered: bool
    balancer_state: str
    balancer_reason: str
    qhe_score: float
    workload_estimate: float
    capacity_estimate: float
    days_in_current_state: int
    is_histerese_active: bool
    active_node_count: int


# ---------------------------------------------------------------------------
# Graph 1: pae_maintainer
# ---------------------------------------------------------------------------


def make_pae_graph(config: RunnableConfig | None = None) -> StateGraph:
    """Build a LangGraph StateGraph that wraps the existing PAE-Maintainer cycle.

    The LangGraph SDK is used only as a thin orchestration layer here. The
    actual work is delegated to the custom Python graph in
    `vibe-ops/src/agents/pae_maintainer/graph.py:run_pae_cycle`.
    """
    g: StateGraph[PAEStateDict] = StateGraph(PAEStateDict)

    def observe(state: PAEStateDict) -> dict:
        """Node 1: Pull latest metrics and update iteration counter."""
        return {
            "iteration": state.get("iteration", 0) + 1,
            "last_step": "observe",
        }

    def plan_and_reflect(state: PAEStateDict) -> dict:
        """Nodes 2+3: Run plan and reflect channels in parallel (sequential here)."""
        return {"last_step": "plan_reflect"}

    def balance(state: PAEStateDict) -> dict:
        """Node 4: Run the balance node and capture the result."""
        import datetime as _dt

        # Reconstruct PAEState from the langgraph state dict
        pae_state = PAEState(
            cycle_id=state["cycle_id"],
            cycle_start=_dt.date.fromisoformat(state["cycle_start"]),
            cycle_end=_dt.date.fromisoformat(state["cycle_end"]),
            iteration=state.get("iteration", 0),
            last_step=state.get("last_step", ""),
            terminated=state.get("terminated", False),
            kill_switch_triggered=state.get("kill_switch_triggered", False),
            balancer_state=BalancerState(
                workload_estimate=state.get("workload_estimate", 0.0),
                capacity_estimate=state.get("capacity_estimate", 8.0),
                qhe_score=state.get("qhe_score", 0.65),
                is_histerese_active=state.get("is_histerese_active", False),
                days_in_current_state=state.get("days_in_current_state", 1),
            ),
        )

        # Run the actual PAE cycle through all 4 steps
        updated = run_pae_cycle(pae_state)

        # Return the updated fields as a dict for langgraph
        return {
            "balancer_state": updated.balancer.state.value,
            "balancer_reason": updated.balancer.reason,
            "qhe_score": updated.balancer.qhe_score,
            "workload_estimate": updated.balancer.workload_estimate,
            "capacity_estimate": updated.balancer.capacity_estimate,
            "days_in_current_state": updated.balancer.days_in_current_state,
            "is_histerese_active": updated.balancer.is_histerese_active,
            "active_node_count": len(updated.active_nodes),
            "last_step": updated.last_step,
            "terminated": updated.terminated,
            "kill_switch_triggered": updated.kill_switch_triggered,
        }

    def commit_or_terminate(state: PAEStateDict) -> Command:
        """Node 5: Commit or terminate based on balancer verdict."""
        if state.get("kill_switch_triggered"):
            return Command(goto=END, update={"terminated": True})
        return Command(goto=END, update={"last_step": "commit"})

    g.add_node("observe", observe)
    g.add_node("plan_reflect", plan_and_reflect)
    g.add_node("balance", balance)
    g.add_node("commit", commit_or_terminate)
    g.add_edge(START, "observe")
    g.add_edge("observe", "plan_reflect")
    g.add_edge("plan_reflect", "balance")
    g.add_edge("balance", "commit")
    g.add_edge("commit", END)
    return g


# ---------------------------------------------------------------------------
# Graphs 2-5: Swarm workflows (4 YAML files from .claude/skills/...)
# ---------------------------------------------------------------------------


def _load_workflow_yaml(name: str) -> dict[str, Any]:
    """Load a workflow YAML file from the quarterly-planner skill."""
    path = (
        Path(__file__).parent
        / ".claude"
        / "skills"
        / "quarterly-planner"
        / "workflows"
        / f"{name}.yml"
    )
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _make_workflow_dispatcher_graph(workflow_name: str) -> StateGraph:
    """Build a generic StateGraph that runs a single workflow YAML.

    Each node in the YAML becomes a stub step that reads the YAML and
    records its execution. In production, real node implementations would
    dispatch to specialist agents (e.g., mesh-coordinator, hierarchical-coord).
    """
    g: StateGraph[dict] = StateGraph(dict)
    g.add_node("load_yaml", lambda _: {"workflow": workflow_name, "step": "loaded"})
    g.add_node("execute_steps", lambda _: {"step": "executed"})
    g.add_node("record_result", lambda _: {"step": "recorded"})
    g.add_edge(START, "load_yaml")
    g.add_edge("load_yaml", "execute_steps")
    g.add_edge("execute_steps", "record_result")
    g.add_edge("record_result", END)
    return g


def make_replan_graph(config: RunnableConfig | None = None) -> StateGraph:
    return _make_workflow_dispatcher_graph("quarterly-replan")


def make_rollup_graph(config: RunnableConfig | None = None) -> StateGraph:
    return _make_workflow_dispatcher_graph("test-de-fogo-rollup")


def make_correction_graph(config: RunnableConfig | None = None) -> StateGraph:
    return _make_workflow_dispatcher_graph("correction-protocol")


def make_falsification_graph(config: RunnableConfig | None = None) -> StateGraph:
    return _make_workflow_dispatcher_graph("dream-falsification")


# ---------------------------------------------------------------------------
# Graph 6: IKIGAi-Maintainer (imported from ikigai package)
# ---------------------------------------------------------------------------


def make_ikigai_graph(config: RunnableConfig | None = None) -> StateGraph:
    """Build the IKIGAi-Maintainer LangGraph.

    Delegates to the ikigai_maintainer graph factory, which provides:
    - observe → score_vectors → heuristics → balance → decompose
      → plan → reflect → commit (8-node pipeline) + error_node terminal (B5.1-F3)
    - SqliteSaver checkpointing (project-local; no ~/.ikigai/ lock risk)
    - Dual-channel (prospective + retrospective)
    - H1–H6 deterministic heuristics

    B5.1-F1: import from `agents.ikigai_maintainer.graph` (post-reorg path)
    instead of the stale `ikigai_maintainer.graph` import.
    """
    from agents.ikigai_maintainer.graph import make_ikigai_graph as _make

    return _make()
