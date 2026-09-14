"""Recall stage: gathers context for reasoning (decision #9)."""
from __future__ import annotations


def recall_node(state):
    state = dict(state)
    state.setdefault("context", {})
    state["context"]["recalled_at"] = "2026-09-14"
    state["context"]["strategics_loaded"] = True
    return state
