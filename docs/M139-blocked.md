# M139 — Real-LLM Smoke Test (BLOCKED)

**Status (2026-09-22):** Documented-blocked.

## Why this milestone exists

The backtest pipeline uses an LLM-as-judge step (`tools/backtest/llm_judge.py`)
to score scenarios on 4 qualitative dimensions:
- `argument_quality` — was the task description well-formed?
- `sequence_coherence` — was the tool order sensible?
- `cultural_fit` — does it respect PT-BR + ABT framing?
- `tool_selection` — was the right tool chosen?

Without a real LLM, the pipeline falls back to a deterministic stub that
returns 0.5 across all dimensions. M139's goal was to **prove** the
real-LLM path works end-to-end with a known-good API key.

## Why it's blocked

The environment has:
- `CLAUDE_API_KEY=sk-cp-i-***` — hermes-agent proxy key
- No `ANTHROPIC_API_KEY`
- No running hermes-agent proxy on `http://127.0.0.1:8045/v1`

Direct `ChatAnthropic(model='claude-3-5-sonnet', api_key=CLAUDE_API_KEY)`
returns `401 authentication_error` because the proxy key is not a direct
Anthropic key. Without the local hermes-agent proxy running on 8045, the
fallback `base_url` in `deepagents_harness.py` is unreachable.

## What works today

- `judge_scenario_llm(..., use_llm=True)` with **no key** → returns stub.
- `judge_scenario_llm(..., use_llm=True)` with **`CLAUDE_API_KEY` set**
  → tries the real LLM, gets 401, **catches the exception**, returns
  stub with `mode="stub_fallback"`.
- `tests/test_m139_real_llm_blocked.py` — 7/7 PASS in stub mode, with
  the 2 real-LLM tests gracefully skipped when the response is stub.

## How to unblock

Pick one:

### Option A — Direct Anthropic key
```bash
export ANTHROPIC_API_KEY="sk-ant-...your-key..."
PYTHONPATH=. pytest tests/test_m139_real_llm_blocked.py -v
```

### Option B — Hermes-agent proxy
```bash
# Start hermes-agent proxy on default port 8045
hermes serve --port 8045 &  # or equivalent command
export CLAUDE_API_KEY="sk-cp-...existing-key..."
PYTHONPATH=. pytest tests/test_m139_real_llm_blocked.py -v
```

If the proxy is reachable, the real-LLM tests will hit Anthropic via
the proxy, return real scores, and pass without skipping.

## What "passing" looks like

```
tests/test_m139_real_llm_blocked.py::test_real_llm_smoke_end_to_end PASSED
tests/test_m139_real_llm_blocked.py::test_real_llm_handles_partial_outcome PASSED
```

Currently both are SKIPPED with reason "fell back to stub (mode='stub_fallback')".

## Timeline

This milestone is parked. If unblocked, expect:
- Real LLM judge scores replace the stub's 0.5/0.5/0.5/0.5 baseline
- Backtest report's "qualitative rollup" becomes informative
- CI's `backtest-pipeline` job can add a `--use-llm` flag (currently
  only runs stub mode for speed)

## Files added in M139

- `tests/test_m139_real_llm_blocked.py` — 7 tests (5 always-pass + 2
  conditionally-passing real-LLM smoke tests)
- `tools/backtest/llm_judge.py` — `_is_real_llm_available()` gate
  function added (was inline `os.environ.get(...)` checks)
