# M113 — Monthly-backtest judge-LLM harness (SPEC)

**Status:** SPEC ONLY — implementation deferred to M114
**Date:** 2026-09-22
**Owner:** Matheus
**Goal:** Backtest our deep-agent stack against a 4-week strategy generated from last-Q3 vault knowledge; Hermes acts as judge-LLM to score overall behavior across the most varied practical tasks; exhaustively exercise every taskdog tool.

---

## Why this exists

Today's daily-use 100% comes from M97b (38 tools) + M105 (3rd graph) + M112 (HTTP path). But we have **no way to measure** whether the agent actually picks the right tool, argues correctly, or fails gracefully under realistic load. Without measurement, every release ships blind.

A backtest harness turns "I think it works" into "I have last week's reliability score."

## Scope (in/out)

**IN:**
- 4-week strategy generated from last-Q3 vault events (Aug-Sep 2025 if available, else constructed scenarios anchored to known task patterns in this repo: BYD career track, M34 autonomous loop, M112 HTTP path tests, etc.)
- Judge-LLM scoring: pass-rate, tool-selection accuracy, argument correctness, graceful-failure rate
- Taskdog tool exhaustive coverage: all 26 MCP tools exercised at least N times
- Reliability scoring per task category
- Report output: `reports/backtest-Q{N}.md`

**OUT (this milestone):**
- Continuous CI integration (manual run only)
- Vault event auto-extraction from Q3 2025 (use a deterministic scenario-seed; manual Q3 ingestion later if/when user provides)
- Real money cost guardrails (use IKIGAI_DISABLE_OTEL=1 + small token budgets)
- Multi-LLM judge ensemble (single judge-LLM is fine for v1)

## Architecture

```
                ┌─────────────────────────────────────────┐
                │  seed_q3_scenarios() — deterministic 4-week
                │         ↓                               │
   vault/drafts/q3-scenarios.yaml  (generated, gitignored)
                │         ↓                               │
   backtest_harness.runner ── simulated task ──►  ikigai_maintainer_v2 / ikigai_taskdog_mcp
                │         ↓                               │
                │   llm-as-judge (Hermes adapter, no LLM call required for grading)
                │         ↓                               │
                │ reports/backtest-Q{N}.md                │
                └─────────────────────────────────────────┘
```

### Components

| Component | Path | Role |
|---|---|---|
| `seed_q3_scenarios.py` | `tools/backtest/seed_q3_scenarios.py` | Generates 28-day scenario corpus, anchored to real BYD career-track + M34 autonomous loop patterns discovered in this repo |
| `backtest_harness.py` | `tools/backtest/backtest_harness.py` | Runs scenario → agent → records transcript + tool calls |
| `judge_llm.py` | `tools/backtest/judge_llm.py` | Scores transcripts (rule-based v1; LLM-based deferred) |
| `taskdog_exhaustiveness.py` | `tools/backtest/taskdog_exhaustiveness.py` | Maps each of 26 MCP tools to N scenarios that exercise it; ensures coverage |
| `run_backtest.sh` | `scripts/backtest/run.sh` | Shell wrapper (PARALLEL=false first, then PARALLEL=true) |
| `reports/backtest-Q{n}.md` | Auto-generated | Score report |

### Scenarios (v1 corpus, 28 days × 1 task/day)

Each scenario is one of:
1. **Add-task** — "user has a new task idea (BYD outreach, daily review, IKIGAI skill draft) → agent should call taskdog.add with priority + tags"
2. **List-tasks** — "user wants today's tasks → agent calls taskdog.list with status filter"
3. **Update-task** — "user wants to bump priority → agent calls taskdog.update"
4. **Complete-task** — "user finished X → agent calls taskdog.complete"
5. **Decompose** — "user has a complex goal (e.g. Folha Norte projeto-META) → agent should recall vault + decompose into 3-7 tasks"
6. **Daily-plan** — "user asks for today's plan → agent calls list + reason about priorities + return plan"
7. **Weekly-review** — "user wants last week's burndown → agent calls metrics + formats report"

The 28-day cycle progresses from "fresh start" to "mid-month crunch" to "month-end close" — matching realistic BYD/IKIGAI effort intensity curves.

### Reliability scoring (judge-LLM rule-based v1)

Per transcript:
- **pass**: correct tool selected + correct args + tool succeeded + final answer addresses user
- **partial**: correct tool but wrong/missing arg, OR succeeded but off-topic answer
- **fail**: wrong tool, OR tool error, OR no response

Aggregate → pass-rate % and per-tool coverage matrix.

## Cost guardrails (production-mode)

- Use `IKIGAI_DISABLE_OTEL=1` to skip telemetry in test runs
- Run single-judge (no ensemble) to halve LLM cost
- Cap scenarios at 28 (not 28×N models)

If real LLM API fails (per user fallback chain), degrade to: try `MiniMax-M3` first, fall back to `Claude Haiku`, then to `rule-only judge`. **Never** mark a run "fail" because the LLM had a 5xx — degrade gracefully.

## Success criteria

1. `bash scripts/backtest/run.sh` completes without crash
2. `reports/backtest-Q1.md` exists with coverage matrix + pass-rate
3. Drift net still 23/23 PASS (no regression from added tool dirs)
4. CI-like stability: 2 consecutive runs produce same pass-rate ±2%

## Acceptance

This is a SPEC. The user OKs scope; M114 implements in atomic phases:
- **M114a** — `seed_q3_scenarios.py` (deterministic generator)
- **M114b** — `backtest_harness.py` (run scenarios against ReAct agent)
- **M114c** — `judge_llm.py` (rule-based scoring v1)
- **M114d** — `taskdog_exhaustiveness.py` (map 26 tools to scenarios)
- **M114e** — `run_backtest.sh` + `reports/backtest-Q1.md` generation

## Open questions for user

1. **Q3 seed corpus source**: ✅ **RESOLVED — vault is the SOT.** `seed_q3_scenarios.py` sweeps `vault/` recursively, parses frontmatter, anchors scenarios to documented events/dates/people. Implementation must handle sparse-vault gracefully (synthesize anchored scenarios from cluster docs / progress.md milestones when no Q3 vault events exist yet).
2. **Real LLM vs fake-LLM for v1**: Default `IKIGAI_FAKE_LLM=1` for first run (deterministic, no API cost), then a second run with real API (with model-downgrade chain MiniMax → Haiku → rule-only).
3. **Per-tool coverage target**: 3 invocations per tool × 26 tools = 78 task-instances spread over 28 daily scenarios.
