"""PAE-Maintainer Agent — always-on strategic planning operating system.

Source: .omo/plans/agentic-markdown-system.md T9
Linked: ADR-006 (period schema), operational constants (Q_HE + 5x3x3)

Architecture: 5 nodes x 2 channels (PROSPECTIVE + RETROSPECTIVE) + balancer.
Uses custom Python orchestration (NOT langgraph SDK) — matches qa_swarm.yaml pattern.
"""
from __future__ import annotations

from .channels import ProspectiveChannel, RetrospectiveChannel
from .nodes import (
    balance_node,
    commit_node,
    observe_node,
    plan_node,
    reflect_node,
)
from .state import (
    BalancerState,
    BalancerVerdict,
    PAEState,
    PlanNode,
    PlanTier,
    PlanVerdict,
    ProspectiveNode,
    RetrospectiveNode,
)

__all__ = [
    "PAEState",
    "ProspectiveNode",
    "RetrospectiveNode",
    "BalancerState",
    "BalancerVerdict",
    "PlanTier",
    "PlanVerdict",
    "PlanNode",
    "observe_node",
    "plan_node",
    "reflect_node",
    "balance_node",
    "commit_node",
    "ProspectiveChannel",
    "RetrospectiveChannel",
]
