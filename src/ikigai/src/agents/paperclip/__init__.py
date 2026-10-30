"""Paperclip — meta-orchestrator LangGraph graph for life-oss/life.

The fourth LangGraph graph registered in ``langgraph.json`` (alongside
``ikigai_maintainer_v2``, ``ikigai_fork_smoke``, ``ikigai_taskdog_mcp``).

Purpose: turn a software-company abstraction into an executable graph —
read a spec, pause for human clarification when ambiguous, create an
isolated git worktree, invoke an AI coding agent (Claude Code MVP; Pi /
MCode / omo / hermes / openclaw later via AgentAdapter Protocol), run
tests, commit, merge back.

Wave 0 (MVP, M169-paperclip):
    * One graph: ``ikigai_paperclip`` (``paperclip_ssd_v1`` alias).
    * HIL via ``langgraph_sdk.interrupt.interrupt`` — introduces the
      first true user-input pause in the repo (kill_switch is binary
      abort, not user-input).
    * Subprocess agent invocation (Path 1 style, mirrors ``run_taskdog``
      in ``src/ikigai/tools/vault_taskdog_sync.py:61-75``).
    * 6 agent adapters declared (1 real, 5 stubs); drift 68 → 70.
"""

from __future__ import annotations

__version__ = "0.1.0-mvp"
