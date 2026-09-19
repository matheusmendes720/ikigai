---
name: M87-real-llm-integration
description: Real LLM dispatch via ChatAnthropic - replaces IKIGAI_FAKE_LLM stub with actual API call (graceful fallback)
owner: matheus-mendes
status: DONE
milestone: M87
estimated_cost_usd: 0.20
constitution_refs:
  - reversibility_over_cleverness
  - spec_driven_not_vibe_driven
  - tests_are_the_contract
---

# M87 - Real LLM integration (ChatAnthropic with graceful fallback)

## Context

`invoke_skill()` previously called `_fake_llm_dispatch()` unconditionally,
returning a deterministic skeleton regardless of manifest content. Real
LLM integration was scoped out of M77 (per its docstring). This meant:

- No actual analysis of skill manifests
- No LLM-driven insights into graph_state
- No conditional outputs based on manifest content

M87 adds `_real_llm_dispatch()` using `langchain_anthropic.ChatAnthropic`
with **graceful fallback**: any error (missing key, import failure,
API auth, network) returns the fake dispatch skeleton with `ok_reason`
captured for diagnostics.

## What changed

### interfaces/cli/invoke_skill.py

- Added `_real_llm_dispatch(manifest)`: reads `ANTHROPIC_API_KEY` or
  `CLAUDE_API_KEY` (hermes-agent proxy alias), constructs
  `ChatAnthropic(model=model_name, api_key=api_key)`, sends a structured
  prompt asking for `analysis`/`outputs`/`next_action` JSON.
- Added `_llm_dispatch(manifest)`: umbrella selector — routes to fake
  when `IKIGAI_FAKE_LLM=1`, otherwise real (with fallback).
- Replaced `invoke_skill` line `graph_state = _fake_llm_dispatch(manifest)`
  with `graph_state = _llm_dispatch(manifest)`.

### tests/test_llm_dispatch.py (NEW)

12 tests:
- `_fake_llm_dispatch` deterministic behavior + missing-field defaults
- `_real_llm_dispatch` missing API key → fallback path
- `_real_llm_dispatch` CLAUDE_API_KEY env var aliasing
- `_real_llm_dispatch` langchain import failure → fallback
- `_real_llm_dispatch` JSON parsing + markdown fence stripping
- `_real_llm_dispatch` invoke failure → fallback with reason
- `_llm_dispatch` IKIGAI_FAKE_LLM=1 routes to fake
- `_llm_dispatch` IKIGAI_FAKE_LLM=0/unset routes to real

## Acceptance

- [x] `_real_llm_dispatch` calls ChatAnthropic when key present
- [x] `_real_llm_dispatch` falls back to fake on any error
- [x] `_llm_dispatch` respects IKIGAI_FAKE_LLM=1 env var
- [x] 12/12 unit tests PASS
- [x] Drift 18/18 PASS
- [x] Root 346 PASS + 27 SKIP (was 334, +12 new tests)
- [x] E2E: invoke_skill with no key → ok_reason=missing, no crash
- [x] E2E: invoke_skill with valid key (CLAUDE_API_KEY) → reaches
  Anthropic API, gets 401 (key is local proxy not real Anthropic),
  falls back gracefully with invoke_failed reason

## Lessons

- **`ChatAnthropic` reads `ANTHROPIC_API_KEY` only** — not
  `CLAUDE_API_KEY`. We accept both env vars as aliases but pass
  `api_key=` explicitly to `ChatAnthropic.__init__`.
- **Graceful fallback is essential**: any LLM API hiccup (timeout,
  401, 429, network) should not break the user's invoke_skill flow.
  Return the deterministic fake + ok_reason for diagnostics.
- **Markdown fence stripping** is needed: Claude sometimes wraps JSON
  in ```json``` fences. Strip them before parsing.
- **Lazy imports** prevent hard dep on langchain_anthropic for users
  who only run in IKIGAI_FAKE_LLM=1 mode.
- **Test mocking via sys.modules**: setting `"langchain_anthropic": None`
  simulates ImportError. Setting it to a MagicMock with ChatAnthropic
  attr lets us verify the constructor args without network calls.

## Out of scope

- LangSmith tracing (different dep, separate work)
- OpenAI fallback (only Anthropic for now; can add later)
- Per-skill prompt customization (single generic system prompt)
- Cost tracking / token counting (could add via callbacks)

## E2E Verified

```bash
PYTHONPATH=src IKIGAI_FAKE_LLM=1 python -m life.cli.cli v2 invoke-skill ikigai-quarterly
# -> llm_stub: true (fake path)

PYTHONPATH=src python -m life.cli.cli v2 invoke-skill ikigai-quarterly
# -> llm_stub: false, ok_reason: import_failed (no langchain_anthropic)

PYTHONPATH=src:src/ikigai/src src/ikigai/.venv/Scripts/python.exe \
  -c "from interfaces.cli.invoke_skill import _llm_dispatch, load_skill_manifest;
      print(_llm_dispatch(load_skill_manifest('ikigai-quarterly')).get('ok_reason'))"
# -> invoke_failed: Anthropic authentication failed (key is local proxy)
```
