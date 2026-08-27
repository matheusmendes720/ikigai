"""Vibe-ops agents package.

Each submodule under this package is a self-contained agent that operates
on the operational/vibe-ops data mesh. Currently houses:

  - pae_maintainer: Always-on strategic planning agent (5 nodes x 2 channels
    + balancer). Implemented per .omo/plans/agentic-markdown-system.md T9-T11.

Agents in this package follow these rules:
  - Custom Python orchestration (NOT langgraph SDK) — matches qa_swarm.yaml.
  - Pure arithmetic decision rules (no LLM, no chat, no streaming).
  - Pydantic v2 strict models for state.
  - Idempotent checkpoint persistence via SQLite.
"""
from __future__ import annotations

__all__: list[str] = []