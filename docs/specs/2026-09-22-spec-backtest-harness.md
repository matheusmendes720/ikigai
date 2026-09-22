# M113 — Monthly-backtest judge-LLM harness (SPEC)

**Status:** SPEC ONLY — implementation deferred to M114
**Date:** 2026-09-22
**Owner:** Matheus
**Goal:** Backtest our deep-agent stack against a 4-week strategy generated from last-Q3 vault knowledge; Hermes acts as judge-LLM to score overall behavior across the most varied practical tasks; exhaustively exercise every taskdog tool.

---

## Why this exists

Today's daily-use 100% comes from M97b (38 tools) + M105 (3rd graph) + M112 (HTTP path). But we have **no way to measure** whether the agent actually picks the right tool, argues correctly, or fails gracefully under realistic load. Without measurement, every release ships blind.

A backtest harness turns "I think it works" into "I have last week's reliability score."

## Drill-down: role anchors (per user directive 2026-09-22)

Per `./strategics/` and `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`, the deep-agent role has explicit requirements that the harness MUST model:

### Read-side roles (from algorithm-attribution §1 + strategics/index)

1. **Constitutional SOT reader** — `./strategics/` PT-BR markdown per algorithm-attribution §1; the agent reads business rules from markdown, not from algorithm code.
2. **Dual-frame temporal tracker** — PAE (Plan-Ajustar-Executar) × Hierarchical (5-level Pyramid). One Cycle = 1.5 months (3 Waves). One Wave = 3 weeks (15 work-days). Macro-Fase = 180 days (Test de Fogo).
3. **5-level hierarchy mapper** (Modelagem Operacional): SONHOS → OBJETIVOS → METAS → TAREFAS → ATIVIDADES. The agent must answer queries about any level and the live status across levels.
4. **Tagging-system conversant** (Integracao_Tática): #supervisão (E), #revisão/#relatórios (T), #narrativa/#to-do (O). Hierarchical tag chains: Sonho #PublicarLivro → Objetivo #RascunhoCap1 → Meta #Semana1-Escrever20pg → Tarefa #Dia1-5pg.
5. **Time-horizon aware** (Análise T&O): Daily routines (Rotina Inicial + Final with checklist), Blocos de Tempo, Relatórios Diários. Surveillance cycles: Day 1, 2-5, 7 (Weekly Revisão), 15 (Quinzenal Supervisão), 45 (Wave Revisão Geral + Correção), 180 (Test de Fogo).

### Write-side roles (from algorithm-attribution §7 + chapter 5 vault_write invariant)

6. **vault_write MCP enforcer** — Per §7: all vault writes (deep agent + native CLI + forks) go through the `vault_write` MCP tool, append-only. **No other code path writes to vault/.** The harness MUST simulate that taskdog's `done` operation propagates a `vault_event.json` entry to the vault, updating linked plans automatically.
7. **taskdog → vault propagation driver** — When a user marks a task done via `life task done` (manual) OR via the agent (ReAct tool call), the system writes a `vault_event.json` line AND the vault plan file (`vault/.../projeto-SOMETHING.md`) gets the related checkbox/tally updated. This is the user-facing requirement.
8. **Plan-update-on-the-fly reflector** — User can refactor / update plans mid-stream. Harness must model: scenario that says "user updates Objetivo #RascunhoCap1 mid-cycle → agent should re-decompose TAREFAS to align". Agent must read vault current state, restructure, write back via vault_write.

### Cross-cutting role requirements

9. **Cross-routine executor** — Routine Inicial (morning: state, todos, blockers) + Routine Final (evening: done tally, tomorrow plan, learnings). Agent must execute both realistically.
10. **Diagnostic reporter** — On failure, agent must surface: which level in hierarchy is broken, what's the impact on Telemetry (commit velocity, LOC), and which Correção do Trajeto applies.
11. **Cultural voice compliance** — PT-BR responses per `00-ÍNDICE-PROGRESSIVO.md`; no English-only jargon; respects the ABT framing (Executive → Key Conclusions → Why Now / How / What / Results / Risk).

## Updated scope (v1)

**IN:**
- 28-day scenario cycle generated from last-Q3 vault knowledge (Aug-Sep 2025 if available, else constructed from 5-level hierarchy + cluster docs)
- **Each scenario exercises at least one role-anchor above** (1-11 from above list)
- Taskdog taskdog exhaustive coverage: all 26 MCP tools exercised at least N times
- Judge-LLM scoring: pass-rate, role-anchor satisfaction, vault_write invariance
- **Propagation verifier**: taskdog `done` → vault `vault_event.json` + linked plan checkbox toggled
- **Plan-update-on-the-fly verifier**: user mid-cycle refactor → vault_write archive + new plan file
- Reliability scoring per role requirement
- Report output: `reports/backtest-Q{N}.md` with per-role-anchor matrix + judge-LLM summary

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
                │         ↓           ↓                  │
                │   vault_write MCP  ←  simulates propagation (taskdog done → vault_event.json + plan toggle)
                │         ↓           ↓                  │
                │   llm-as-judge (Hermes adapter, no LLM call required for grading)
                │         ↓                               │
                │ reports/backtest-Q{N}.md                │
                └─────────────────────────────────────────┘
```

### Components

| Component | Path | Role |
|---|---|---|
| `seed_q3_scenarios.py` | `tools/backtest/seed_q3_scenarios.py` | Generates 28-day scenario corpus (DONE M114a) |
| `taskdog_exhaustiveness.py` | `tools/backtest/taskdog_exhaustiveness.py` | Ensures 26-tool coverage (DONE M114d) |
| `role_anchors.py` | `tools/backtest/role_anchors.py` | Maps scenarios to role-anchor requirements 1-11 |
| `backtest_harness.py` | `tools/backtest/backtest_harness.py` | Runs scenarios; checks role-anchor satisfaction; simulates vault_write propagation |
| `vault_propagation.py` | `tools/backtest/vault_propagation.py` | Simulates the taskdog done → vault_event.json + plan toggle flow |
| `judge_llm.py` | `tools/backtest/judge_llm.py` | Rule-based v1 + LLM-judge v2 (LLM optional) |
| `run_backtest.sh` | `scripts/backtest/run.sh` | Shell wrapper (PARALLEL=false first, then true) |
| `reports/backtest-Q{n}.md` | Auto-generated | Report with per-role-anchor matrix + judge-LLM summary |

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
- **M114a** — `seed_q3_scenarios.py` (deterministic generator) ✅
- **M114b** — `backtest_harness.py` (run scenarios against ReAct agent)
- **M114c** — `judge_llm.py` (rule-based scoring v1)
- **M114d** — `taskdog_exhaustiveness.py` (map 26 tools to scenarios) ✅
- **M114e** — `role_anchors.py` (map scenarios → role-anchor 1-11)
- **M114f** — `vault_propagation.py` (simulate taskdog done → vault_event.json + plan toggle)
- **M114g** — `run_backtest.sh` + `reports/backtest-Q1.md` generation
- **M114h** — End-to-end propagation test: real taskdog `done` → real vault plan update verified by file mtime + vault_event.json line count

Each phase lands its own commit; drift net stays 23/23.

## Open questions for user

1. **Q3 seed corpus source**: ✅ **RESOLVED — vault is the SOT.** `seed_q3_scenarios.py` sweeps `vault/` recursively, parses frontmatter, anchors scenarios to documented events/dates/people. Implementation must handle sparse-vault gracefully (synthesize anchored scenarios from cluster docs / progress.md milestones when no Q3 vault events exist yet).
2. **Real LLM vs fake-LLM for v1**: Default `IKIGAI_FAKE_LLM=1` for first run (deterministic, no API cost), then a second run with real API (with model-downgrade chain MiniMax → Haiku → rule-only).
3. **Per-tool coverage target**: 3 invocations per tool × 26 tools = 78 task-instances spread over 28 daily scenarios.
