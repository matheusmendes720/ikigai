"""v2 — restored LangGraph scaffolding from archive/recovered-agentic-2026-09-01.

This package is a READ-ONLY parallel branch. All math calls have been replaced
with prompt-chain stubs. Phase 8.2 will wire the actual MCP tool calls.

Drift detector: this directory is scanned by test_canonical_scope.py.
Do NOT import sys_ikigai.core.scoring, ikigai.core.heuristics, or cybernetics.daily_loop.

M158e: import langchain_anthropic_shim first to monkey-patch
anthropic.OverloadedError before any submodule imports langchain_anthropic.
"""
from .langchain_anthropic_shim import _ensure_overloaded_error, install_response_normalizer  # noqa: F401
_ensure_overloaded_error()
install_response_normalizer()
