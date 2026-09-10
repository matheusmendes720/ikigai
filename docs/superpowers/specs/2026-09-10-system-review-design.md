# IKIGAI Agentic System — Top-Down Review Design

**Date:** 2026-09-10
**Status:** Awaiting user approval
**Author:** brainstorm session (2026-09-10)
**Companion spec:** `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`
**Companion report:** `docs/architecture/2026-08-29-attribution-report.md`

---

## §0 — Why this exists

The user observed concrete inconsistencies in `ikigai-chat` (REPL) output
versus Claude Code output for the same canonical question ("o que é o PAE
e as estruturas hierárquicas do planejamento"). Comparison revealed ≥10
divergences, e.g.:

- `ikigai-chat`: "PAE = IKIGAI" · Claude Code: "PAE = Plano Anual Estratégico
  (PT-BR em `strategics/`)"
- `ikigai-chat`: listou PAV/QHE/regime FSM como vivos · Claude Code:
  lembrou `archive/legacy-pav/src-operational/` desde 2026-08-31
- `ikigai-chat`: UEID 5-part · Claude Code: UEID 4-part per ADR-014
- `ikigai-chat`: 8 nós no ciclo · `graph.py`: 11 nós
- `ikigai-chat`: hierarquia 4 níveis SONHO→OBJ→PRJ→DEL ·
  `strategics/`: 5 níveis SONHOS→OBJETIVOS→METAS→TAREFAS→ATIVIDADES
- `ikigai-chat`: sem citações · Claude Code: cita docs + MEMORY + ADRs

These are symptoms of a single root-cause hypothesis: **vocabulary leak
from archived PAV through prompts/MCP-tool names/v2 graph node names →
LLM context → user-facing output**. The review's job is to confirm this
hypothesis, surface every other gap in the agentic system, and produce a
prioritized remediation plan.

---

## §1 — Architecture (the review method)

Top-down diagnostic across **10 layers**, each inspected with an explicit
protocol + expected contract. Gaps accumulate per layer; drift net is
ground truth; final output is a spec + plan.

```
Layer 1:  strategics/                   (PT-BR constitutional SOT)
Layer 2:  src/contracts/                (Pydantic v2 strict)
Layer 3:  src/mesh/                     (3 fork adapters + queue + agent_consumer + propagator)
Layer 4:  src/ikigai/ MCP gateway       (12 IKIGAI_TOOLS + 7 fork tools + 6 resources)
Layer 5:  src/ikigai/src/agents/v2/     (graph + 11 nodes + 15 prompts + 5 skills)
Layer 6:  sys_ikigai/                   (entities/gateway/state_machines/vault/security/adapters)
Layer 7:  vibe-ops/                     (cybernetic engine)
Layer 8:  interfaces/cli/ + tui/        (consumers)
Layer 9:  drift net                     (3 test files)
Layer 10: LangGraph graphs              (5 in langgraph.json)
                                        ↓
                         ponta: ikigai-chat + TUI + CLI + MCP responses
```

**Principles:**

1. **Append-only mentalidade.** New gaps become new MEMORY entries;
   existing entries never edited.
2. **Attribution is law.** Any proposed fix respects
   `[[algorithm-attribution-decisions-2026-08-29]]` + ADR-013 +
   `[[algorithm-gate-dropped-2026-09-03]]` +
   `[[archived-feature-not-vocabulary-2026-09-06]]`.
3. **Drift net is ground truth.** Existing tests are objective evidence;
   gaps without test coverage become new invariant tests in §5.
4. **Spec → plan → implementation.** Spec delivers diagnosis; plan
   delivers prioritized remediation (via `writing-plans` skill, post-approval).

---

## §2 — Components (per-layer inspection protocol)

| Layer | Inspection Protocol | Expected Contract | Gap Type |
|---|---|---|---|
| **1. strategics/** | Read all 6 PT-BR files + índice. Map canonical claims. | SOT immutable; PT-BR; never edited; 5-level hierarchy; dual-frame PAE × Hierarchical; 5×3×3 framework; Ciclo Macro 180 d.u. | `constitution_drift` |
| **2. src/contracts/** | Grep UEID format, read Pydantic strict invariants | UEID 4-part (ADR-014); `frozen=True, extra="forbid"`; no DEFAULT_* algorithm constants in agents layer | `schema_drift` |
| **3. src/mesh/** | Read 3 adapters (Cli/Taskdog/SolverforgeCalendar) + agent_consumer + propagator | Phase 3 v1 create-only; PAE: APPROVE/REJECT/CLARIFY; UEID cross-fork consistent | `mesh_drift` |
| **4. src/ikigai/ MCP** | Enumerate 12 IKIGAI_TOOLS + 7 fork + 6 resources; verify naming vs attribution design | Tool names must not suggest PAV math (no `*_qhe_score`, no `*_regime`, no `*_pav_state` for production paths) | `attribution_leak` ← **known** |
| **5. v2 agent** | graph.py (11 nodes) + 15 prompts + 5 skills + `algorithm_constants.json` | Node names neutral; prompts cite `strategics/` and not PAV; constants JSON contains only subagent/checkpoint/memory values, not QHE | `prompt_leak` ← **known** |
| **6. sys_ikigai/** | entities, gateway, state_machines, vault, security, adapters | FSMs without PAV math; `vault_write` sole writer (ADR-012); kill_switch functional | `core_drift` |
| **7. vibe-ops/** | cybernetics + sync_engine | Target→Sensor→Adjuster→Persist→Sync→Index; `NotImplementedError` on composition paths per attribution §3 | `engine_drift` |
| **8. interfaces/** | CLI v2 modules + TUI operator 4 tabs | Read vault; write to `data/feedback`; kill_switch tab functional; chat tab routes through v2 graph (Caminho B) | `interface_drift` |
| **9. drift net** | Run 3 test files; map covered vs uncovered invariants | Coverage: canonical_scope, drift_invariants (a–h+), UEID 4-part, append-only, dual-tree identity | `invariant_gap` |
| **10. LangGraph graphs** | langgraph.json + 5 entry factories | Graphs registered match attribution §6 (pae_maintainer, quarterly_replan, correction_protocol, dream_falsification, test_de_fogo_rollup) | `graph_drift` |

**Output per layer:** `gaps_found[]` table with
`{layer, severity (P0–P3), summary, evidence (file:line), root_cause_layer, fix_category}`.

---

## §3 — Data Flow (review execution)

```
START: docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md
       MEMORY.md (CLAUDE.md durable constraints)
            ↓
[1] STATIC READ — Layer 1 → 10 (cascata)
       Per layer:
         a) Read code/docs
         b) Diff against Expected Contract (§2)
         c) If diverges → emit provisional gap
            ↓
[2] RUNTIME PROBE — sampling nas pontas
       Canonical questions:
         - "o que é o PAE?"
         - "como funciona a hierarquia de planejamento?"
         - "o que é regime FSM?"
         - "como sincroniza vault com forks?"
         - "qual é o formato UEID?"
       Run against: ikigai-chat, TUI Chat tab, CLI v2 daily, MCP gateway responses
       Capture outputs → diff vs attribution design + strategics/
       Divergences → emit gap (severity escalates by +1 tier per additional
       ponta where the gap appears, capped at P0). Probe set is fixed
       (5 questions) so coverage is reproducible.
            ↓
[3] DRIFT NET CROSS-REFERENCE
       Run pytest on 3 test files
       Each failure → link to provisional gap
       Each provisional gap without corresponding test → emit `invariant_gap`
            ↓
[4] GAP TRIAGE
       For each gap, assign exactly one severity per the criteria below
       (the highest applicable wins):
         - **P0 — Attribution violated, output breaks:** gap causes
           ikigai-chat/TUI/CLI/MCP to produce content that contradicts
           the attribution design, ADR-013, or `strategics/`. Visible
           to user as wrong/confusing answer.
         - **P1 — Drift detection missing:** no automated test would
           catch this regression. Add a new invariant test (§5).
         - **P2 — UX/inconsistency:** visible drift between docs and
           code, but no attribution violation. (e.g. node count
           mismatch, naming inconsistency.)
         - **P3 — Cosmetic:** naming, formatting, comment drift. No
           functional impact.
       For each gap also tag:
         - **fixable?** Yes → plan entry with concrete steps. No (e.g.
           PAV revival) → ADR proposal only, no code change in this wave.
         - **root_cause_layer:** where the fix lives (typically Layer 4–5
           for prompt/attribution leaks).
            ↓
[5] PLAN OUTPUT
       docs/superpowers/plans/2026-09-10-system-review-remediation.md
       (post spec approval, via writing-plans skill)
```

**Artifacts produced:**

1. `docs/superpowers/specs/2026-09-10-system-review-design.md` (this file)
2. `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md` (gap catalogue, written during execution)
3. `docs/superpowers/specs/2026-09-10-drift-net-baseline.md` (drift net PASS count, before/after diff)
4. `~/.claude/projects/.../memory/system-review-gaps-2026-09-10.md` (MEMORY entry, append-only) + index line in `MEMORY.md`
5. `docs/superpowers/plans/2026-09-10-system-review-remediation.md` (plan, via writing-plans)

---

## §4 — Error Handling (hard constraints)

When the review finds a gap that **cannot** be fixed directly:

| Constraint | Behavior |
|---|---|
| **PAV revival** — gap asks to run QHE/regime math | **REJECT** with ADR proposal + reference to `[[algorithm-gate-dropped-2026-09-03]]` |
| **Algorithm tuning** — gap asks to change weights | **DEFER** with note: "gated em 5+ SONHO logs empíricos per `[[algorithm-scope-reframed-2026-08-30]]`" |
| **PAV vocab revival** — gap asks to reintroduce QHE/regime as feature | **REJECT** with reference to `[[archived-feature-not-vocabulary-2026-09-06]]` |
| **Vault write bypass** — gap suggests interface writing direct to vault/ | **REJECT** with ADR-012 (sole writer invariant) |
| **Pydantic non-strict** — gap suggests relaxing `frozen=True` | **REJECT** (architectural drift) |
| **PAV CLI/TUI restoration** — gap reintroduces archived PAV interfaces | **REJECT** per `[[legacy-pav-ui-era-2026-08-28]]` |
| **Master branch reintroduction of PAV** | **REJECT** per `[[master-branch-carro-chefe-2026-08-28]]` |

**Decision rule:** If the proposed fix violates any memory entry tagged
`feedback` or `architecture`, the gap becomes an **ADR Proposal** in
the plan, not a direct fix.

---

## §5 — Testing (validation)

**Before review:** drift net baseline = record PASS count of
`pytest src/ikigai/tests/test_canonical_scope.py test_drift_invariants.py test_drift_extended_invariants.py`,
written to `docs/superpowers/specs/2026-09-10-drift-net-baseline.md`
alongside the gap catalogue (so before/after can be diffed).

**During review:** Each gap becomes at least one of:

- **Regression test** if fix is mechanical (e.g. rename `ikigai_observe_pav_state` → `ikigai_observe_state` in `test_canonical_scope.py`).
- **New drift invariant** if fix is about new invariant (e.g. "no prompt mentions QHE outside archived context").
- **Manual probe** if fix is too semantic for automated tests (e.g. "ikigai-chat never claims PAE=IKIGAI").

**After remediation:** drift net must pass with **+N new invariants**
covered. Baseline + new = expanded coverage.

**Success criteria:**

1. ✅ All 10 layers inspected with explicit protocol
2. ✅ ≥1 gap cataloged per layer that has gaps (no fabricated gaps)
3. ✅ Drift net baseline recorded + post-remediation coverage expanded
4. ✅ Each gap: layer origin + root_cause_layer + severity + fix_category
5. ✅ Gaps violating constraints → ADR proposals, not direct fixes
6. ✅ Spec finalized at `docs/superpowers/specs/2026-09-10-system-review-design.md`
7. ✅ MEMORY entry appended (not edited)
8. ✅ Prioritized remediation plan delivered (via writing-plans)
9. ✅ User approves spec before any execution

---

## §6 — Scope

**In scope:**

- All 10 layers of the IKIGAI agentic system
- All entry-points (ikigai-chat, TUI 4 tabs, CLI v2, MCP gateway responses)
- Drift net audit
- Gap catalog with severity + root cause + fix category
- Prioritized remediation plan
- New drift invariants to cover the discovered gaps

**Out of scope:**

- ❌ PAV revival (per attribution design + ADR-013 + algorithm-gate-dropped)
- ❌ Algorithm weight tuning (DEC pending + algorithm-scope-reframed)
- ❌ Vault write invariant relaxation (ADR-012)
- ❌ Pydantic v2 strict relaxation
- ❌ Native PAV CLI/TUI restoration
- ❌ New fork adapters beyond the 4 documented
- ❌ Multi-agent swarm coordination (gated on IKIGAI backbone solid)
- ❌ Real-time conversation agents beyond ikigai-chat (mid-design)

---

## §7 — Known starting point (preliminary diagnosis)

The `ikigai-chat` response gap already identified (from §0) gives the
review a starting anchor. Hypothesis: **vocabulary leak from archived
PAV through prompts/MCP-tool names/v2 graph node names → LLM context
→ user-facing output**.

This hypothesis will be confirmed or refuted during Layer 4 + Layer 5
inspection. If confirmed, the fix is concentrated in Layer 4–5 (rename
tools, sanitize prompts, drain `algorithm_constants.json`); if refuted,
the gap has a different root cause and the review expands to find it.

---

## §8 — Deliverables

| Artifact | Path | Status |
|---|---|---|
| This spec | `docs/superpowers/specs/2026-09-10-system-review-design.md` | Awaiting user approval |
| Gap catalogue | `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md` | Written during execution |
| MEMORY entry | `~/.claude/projects/.../memory/system-review-gaps-2026-09-10.md` + index in MEMORY.md | Append-only |
| Remediation plan | `docs/superpowers/plans/2026-09-10-system-review-remediation.md` | Post-approval, via writing-plans |

---

## §9 — Related memory

- `[[algorithm-attribution-decisions-2026-08-29]]` — attribution is law
- `[[algorithm-gate-dropped-2026-09-03]]` — no algorithm work without explicit demand
- `[[archived-feature-not-vocabulary-2026-09-06]]` — never relist PAV/QHE/regime as pending/roadmap
- `[[algorithm-scope-reframed-2026-08-30]]` — IKIGAI = planner with stochastic feedback
- `[[master-branch-carro-chefe-2026-08-28]]` — master = deep-agent bidirectionally syncing
- `[[legacy-pav-ui-era-2026-08-28]]` — PAV CLI/TUI abandoned 2026-08-26
- `[[dual-module-identity-bug-pattern]]` — patch BOTH `src.X` and `X` identities in tests
- `[[drift-cross-pollution-2026-09-06]]` — intermittent test failures from pollution

---

*System Review Design — IKIGAI agentic system — 2026-09-10 — awaiting user approval*
