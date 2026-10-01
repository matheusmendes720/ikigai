"""v2 — restored LangGraph scaffolding from archive/recovered-agentic-2026-09-01.

This package is a READ-ONLY parallel branch. All math calls have been replaced
with prompt-chain stubs. Phase 8.2 will wire the actual MCP tool calls.

Drift detector: this directory is scanned by test_canonical_scope.py.
Do NOT import sys_ikigai.core.scoring, ikigai.core.heuristics, or cybernetics.daily_loop.

M158g — langchain_anthropic compat shim.

ROOT CAUSE (locked in M158e investigation, 2026-09-29):
- langchain_anthropic 1.7.2 requires anthropic>=0.120.0 (per its METADATA).
- This machine has anthropic 0.76.0 because browser-use 0.13.10 pins it.
- anthropic 0.76.0 has no OverloadedError attribute.
- langchain_anthropic.chat_models:984 declares:

      class AnthropicOverloadedError(anthropic.OverloadedError, ModelAPIError):

  which crashes at IMPORT-TIME with AttributeError on this machine.
- Result: from langchain_anthropic import ChatAnthropic raises AttributeError,
  every LLM call in v2 graph silently returns "0 suggestions".

FIX: monkey-patch anthropic.OverloadedError BEFORE any langchain_anthropic
import. Done in _ensure_overloaded_error() below.

WHY WE KEEP THE SHIM (not upgrade):
- pip install "anthropic>=0.120.0" works but breaks browser-use 0.13.10
  (pinned to anthropic==0.76.0). browser-use is installed for Hermes agent
  workflows and is OUT of scope for life-oss.
- pip install "langchain-anthropic<0.3" works in theory but means giving up
  LangGraph 1.x compatibility + losing the prompt-chain observability hooks.

REMOVAL PLAN: when browser-use 0.13.10+ supports anthropic>=0.120.0, this
shim can be deleted. Until then, every v2 graph entry point must import
this module (or rely on this __init__.py to do it).
"""
from .langchain_anthropic_shim import _ensure_overloaded_error, install_response_normalizer  # noqa: F401
_ensure_overloaded_error()
install_response_normalizer()
