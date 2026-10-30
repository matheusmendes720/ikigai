# src/agents/ — Planner Agent Layer

**Score:** 8 (7 files, 100% code, 42 symbols, 23 exports, 10 import sites)
**Role:** planner-only agent layer — cross-session memory + self-review.

## OVERVIEW

Two subpackages, both **observational**: they record and replay what the agent
did so a human can adjudicate it. Per ADR-013 the agent layer never executes
policy — it proposes.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Cross-session summaries | `memory/cross_session.py` | writes `vault/ikigai/runtime/sessions/<id>.md`; `SessionSummarizer`, `summarize_and_store` |
| Decision log | `reflection/recursive.py` | appends to `vault/ikigai/decisions/<date>.jsonl`; `DecisionStore` |
| Pattern detection | `reflection/patterns.py` | `Finding` — turns the decision log into proposed adjustments |
| Reflection rendering | `reflection/writer.py` | markdown to `vault/ikigai/reflections/<date>.md` |
| CLI | `python -m src.agents.reflection.recursive` | `--lookback-days`, `--today`, `--out`, `--json` |
| Env knobs | `REFLECT_LOOKBACK_DAYS`, `REFLECT_TODAY` | read by the reflection CLI |

## CONVENTIONS

- **The two `agents` directories are one package.** `src/agents/` (planner) and
  `src/ikigai/src/agents/` (IKIGAI) are merged by extending `__path__` in both
  `__init__.py` files, so `agents.memory.*` and `agents.v2.*` both resolve
  regardless of which wins the `sys.path` race. Keep the two extensions
  symmetric — a one-sided change hides the other half.
- `cross_session.py` and `recursive.py` are split from their siblings to stay
  under the project's 500-line cap (`patterns.py`, `writer.py`).
- Internal results are frozen dataclasses (`SessionSummary`, `Finding`,
  `Decision`); only wire types are Pydantic.
- `reflection` writes into `vault/` but never deletes from it.

## ANTI-PATTERNS

- Never apply a finding automatically. Findings become **Proposals** for the
  human to adjudicate — never auto-applied.
- Never use this layer to execute policy or scoring math (ADR-013, planner-only).
  The `IKIGAI_TOOLS` count is guarded by the drift net.
- Do not make a decision-log write block the mutation that triggered it. The
  mesh CLI's `_record_decision` swallows its own exceptions; keep that property.
- Do not put a storage adapter or persistence layer here — this package records
  observations, it does not own fork state.
- `reflection/__init__.py` omits `from __future__ import annotations`; the
  repo convention is to include it in every module.
