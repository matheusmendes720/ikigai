# IKIGAI System Top-Down Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the top-down review across all 10 layers of the IKIGAI agentic system per `docs/superpowers/specs/2026-09-10-system-review-design.md`, producing a gap catalogue, drift net baseline, MEMORY entry, and prioritized remediation recommendations.

**Architecture:** Research/diagnostic plan with 9 sequential tasks. Each task inspects one or more layers, captures findings in a working markdown file, and commits. Drift net baseline is recorded before + after. Runtime probes through 4 entry-points produce empirical evidence of "ultima ponta" gaps. Final tasks consolidate findings into a diagnosis document and MEMORY entry.

**Tech Stack:** Python 3.11, pytest, git, gh CLI, MCP gateway stdio, ikigai.bat, CLI v2, TUI operator, bash/PowerShell.

---

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-09-10-system-review-design.md` (every task implicitly references this)
- **Companion spec:** `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md` (law of attribution)
- **Attribution is law:** Any proposed fix respects
  `[[algorithm-attribution-decisions-2026-08-29]]` + ADR-013 +
  `[[algorithm-gate-dropped-2026-09-03]]` +
  `[[archived-feature-not-vocabulary-2026-09-06]]`
- **Append-only MEMORY:** New gaps → new MEMORY entry. Never edit existing.
- **No code changes in this plan:** This plan produces a diagnosis. Code fixes
  belong in a future plan (post-diagnosis user decision).
- **Drift net commands (verbatim):**
  - `pytest src/ikigai/tests/test_canonical_scope.py -v`
  - `pytest src/ikigai/tests/test_drift_invariants.py -v`
  - `pytest src/ikigai/tests/test_drift_extended_invariants.py -v`
- **Severity tiers per spec §3 [4]:** P0 (attribution violated) → P1 (drift detection missing) → P2 (UX/inconsistency) → P3 (cosmetic). Highest applicable wins.
- **Commit message style:** `chore(review): <layer> inspection + <n> provisional gaps` (no Co-Authored-By trailer per CLAUDE.md).
- **Output directory:** `docs/superpowers/specs/` (per spec §8).

---

## File Structure

**Created by this plan:**

- `docs/superpowers/specs/2026-09-10-drift-net-baseline.md` — drift net PASS counts before/after review (Task 1 + Task 9)
- `docs/superpowers/specs/2026-09-10-system-review-working.md` — interim gap catalogue, one section per layer (Tasks 2-7)
- `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md` — final consolidated diagnosis + prioritized remediation recommendations (Task 8)
- `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/system-review-gaps-2026-09-10.md` — MEMORY entry (Task 9)

**Modified by this plan:**

- `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md` — add 1-line index pointer (Task 9)

**Read-only references (no modification):**

- `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md` — attribution law
- `docs/architecture/2026-08-29-attribution-report.md` — companion attribution report
- `strategics/*.md` (6 PT-BR files) — Layer 1
- `src/contracts/*.py` — Layer 2
- `src/mesh/*.py` — Layer 3
- `src/ikigai/src/mcp_server/*.py` — Layer 4
- `src/ikigai/src/agents/v2/*.py` + `prompts/` + `skills/` + `algorithm_constants.json` — Layer 5
- `sys_ikigai/**/*.py` — Layer 6
- `vibe-ops/**/*.py` — Layer 7
- `interfaces/cli/**/*.py` + `interfaces/tui/operator/**/*.py` — Layer 8
- `src/ikigai/tests/test_canonical_scope.py` + `test_drift_invariants.py` + `test_drift_extended_invariants.py` — Layer 9
- `langgraph.json` + `vibe-ops/src/langgraph_entry.py` — Layer 10

---

## Task 1: Setup + Drift Net Baseline

**Files:**
- Create: `docs/superpowers/specs/2026-09-10-drift-net-baseline.md`
- Modify: none
- Read: spec files for context

**Goal:** Establish pre-review drift net PASS count. This becomes the baseline against which post-review coverage is measured (Task 9).

- [ ] **Step 1: Run drift net — test_canonical_scope**

```bash
cd C:/Users/mathe/code_space/life-oss/life
python -m pytest src/ikigai/tests/test_canonical_scope.py -v 2>&1 | tail -40
```

Expected: list of PASS/FAIL with summary line like `=== N passed, M failed in Xs ===`.

- [ ] **Step 2: Run drift net — test_drift_invariants**

```bash
cd C:/Users/mathe/code_space/life-oss/life
python -m pytest src/ikigai/tests/test_drift_invariants.py -v 2>&1 | tail -40
```

Expected: PASS list. Record count.

- [ ] **Step 3: Run drift net — test_drift_extended_invariants**

```bash
cd C:/Users/mathe/code_space/life-oss/life
python -m pytest src/ikigai/tests/test_drift_extended_invariants.py -v 2>&1 | tail -40
```

Expected: PASS list. Record count.

- [ ] **Step 4: Write baseline document**

Create `docs/superpowers/specs/2026-09-10-drift-net-baseline.md` with content:

```markdown
# Drift Net Baseline — System Review 2026-09-10

**Pre-review baseline** (Task 1 of `2026-09-10-system-review-remediation.md`)

| Test file | PASS | FAIL | Errors | Total |
|-----------|------|------|--------|-------|
| test_canonical_scope.py | N1 | F1 | E1 | T1 |
| test_drift_invariants.py | N2 | F2 | E2 | T2 |
| test_drift_extended_invariants.py | N3 | F3 | E3 | T3 |
| **TOTAL** | **N** | **F** | **E** | **T** |

**Drift net version:** `<git rev-parse HEAD>` captured at baseline time.

**Known pre-existing failures** (if any): list them here with file:line references.

**Post-review check** (Task 9) MUST record deltas here.
```

Fill in N1/F1/E1/T1 etc. with the actual numbers from Steps 1-3. Use 0 where applicable.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-drift-net-baseline.md
git commit -m "chore(review): drift net baseline — N1/N2/N3 PASS recorded"
```

(No Co-Authored-By trailer.)

---

## Task 2: Static Read — Layer 1 (strategics/)

**Files:**
- Create: `docs/superpowers/specs/2026-09-10-system-review-working.md` (initialize with Layer 1 section)
- Read: `strategics/00-ÍNDICE-PROGRESSIVO.md`, `Planejamento (Estratégico e Tático).md`, `Hierarquia de Objetivos.md`, `Modelagem Operacional.md`, `Desempenho Subjacente.md`, `Integracao_Tatica.md`, `Análise (Tático e Operacional).md`

**Goal:** Verify strategics/ is the immutable PT-BR SOT with 5-level hierarchy, dual-frame, 5×3×3 framework. Emit 0-N gaps.

- [ ] **Step 1: Initialize working file with header**

Create `docs/superpowers/specs/2026-09-10-system-review-working.md`:

```markdown
# System Review Working File — 2026-09-10

> Interim gap catalogue. Consolidated into `2026-09-10-system-review-diagnosis.md`
> in Task 8.

---

## Layer 1 — strategics/ (PT-BR constitutional SOT)

**Files inspected:**
- [list]

**Expected contract (per spec §2):** SOT immutable; PT-BR; never edited;
5-level hierarchy (SONHOS→OBJETIVOS→METAS→TAREFAS→ATIVIDADES); dual-frame
PAE × Hierarchical; 5×3×3 framework; Ciclo Macro 180 d.u.

**Findings:**
[fill in below]

**Provisional gaps:** [list or "none"]
```

- [ ] **Step 2: Read `00-ÍNDICE-PROGRESSIVO.md` (425 lines)**

```bash
cd C:/Users/mathe/code_space/life-oss/life
wc -l strategics/00-ÍNDICE-PROGRESSIVO.md
head -100 strategics/00-ÍNDICE-PROGRESSIVO.md
```

Verify: lists all 6 docs, references dual-frame + 5×3×3 + pirâmide estratégico/tático/operacional.

- [ ] **Step 3: Read `Planejamento (Estratégico e Tático).md` §1.1.1 + §1.2.1**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -n "§1.1.1\|§1.2.1\|PAE\|SONHOS\|OBJETIVOS\|METAS\|TAREFAS\|ATIVIDADES\|5×3×3\|Hysteresis" strategics/"Planejamento (Estratégico e Tático).md" | head -30
```

Verify: PAE defined as "Plano Anual Estratégico" (NOT agent), 5-level hierarchy present, 5×3×3 framework present.

- [ ] **Step 4: Read `Hierarquia de Objetivos.md`**

```bash
cd C:/Users/mathe/code_space/life-oss/life
head -60 strategics/Hierarquia\ de\ Objetivos.md
grep -n "5 níveis\|SONHOS\|OBJETIVOS\|METAS\|TAREFAS\|ATIVIDADES\|3 meses\|15 dias" strategics/Hierarquia\ de\ Objetivos.md | head -20
```

Verify: 5-level hierarchy explicit.

- [ ] **Step 5: Read `Modelagem Operacional.md` §Ciclo Macro**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -n "Ciclo Macro\|180\|45 dias\|Onda\|3 semanas\|Teste de Fogo" strategics/Modelagem\ Operacional.md | head -20
```

Verify: Ciclo Macro 180 d.u., Teste de Fogo present.

- [ ] **Step 6: Cross-check the 6 docs for internal consistency**

For each claim that appears in multiple docs:
- 5-level hierarchy appears identically in ≥3 docs?
- 5×3×3 framework referenced consistently?
- Dual-frame PAE × Hierarchical referenced consistently?
- No doc contradicts another on a load-bearing claim?

Record any contradictions as provisional gaps in the working file.

- [ ] **Step 7: Update working file with findings**

Append to `## Layer 1 — strategics/` section:

```markdown
**Findings:**
- PAE definition: `<verbatim quote from spec>`
- Hierarchy: `<5-level / 4-level / other>`
- Dual-frame: `<present / partial / absent>`
- 5×3×3 framework: `<present / absent>`
- Ciclo Macro: `<180 d.u. / other>`

**Provisional gaps:** [list each as
`{severity_guess, summary, evidence: file:line, root_cause_layer: N/A (constitution)}`]

OR:

**Provisional gaps:** none
```

- [ ] **Step 8: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): Layer 1 strategics/ inspection + N gaps"
```

(Replace `N` with actual count, 0 if none.)

---

## Task 3: Static Read — Layer 2 (src/contracts/)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-10-system-review-working.md` (append Layer 2 section)
- Read: `src/contracts/*.py`

**Goal:** Verify UEID 4-part canonical format (ADR-014), Pydantic v2 strict invariants (`frozen=True`, `extra="forbid"`), no DEFAULT_* algorithm constants.

- [ ] **Step 1: List all contracts files**

```bash
cd C:/Users/mathe/code_space/life-oss/life
ls src/contracts/
wc -l src/contracts/*.py
```

Expected: common.py, task.py, task_change.py, planning.py, metrics.py (per CLAUDE.md "Canonical Contracts").

- [ ] **Step 2: Grep UEID format definitions**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -rn "^[a-z]\{2,5\}:\|regex.*UEID\|UEID.*regex\|field_regex" src/contracts/ | head -20
```

Verify: UEID regex is `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (4-part per ADR-014).

- [ ] **Step 3: Grep Pydantic strict invariants**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -rn "frozen=True\|extra=\"forbid\"\|ConfigDict" src/contracts/ | head -20
```

Verify: every BaseModel uses `model_config = ConfigDict(frozen=True, extra="forbid")`.

- [ ] **Step 4: Check for DEFAULT_* algorithm constants**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -rn "DEFAULT_QHE\|DEFAULT_REGIME\|DEFAULT_VECTOR\|DEFAULT_HEURISTIC" src/contracts/
```

Expected: no matches (algorithm constants live in `src/ikigai/src/agents/v2/prompts/algorithm_constants.json` per ADR-019).

- [ ] **Step 5: Update working file with findings**

Append to `## Layer 2 — src/contracts/` section per same format as Task 2 Step 7.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): Layer 2 src/contracts/ inspection + N gaps"
```

---

## Task 4: Static Read — Layer 3 (src/mesh/)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-10-system-review-working.md`
- Read: `src/mesh/queue.py`, `agent_consumer.py`, `agent_propagator.py`, `adapters/base.py`, `adapters/cli.py`, `adapters/taskdog.py`, `adapters/solverforge_calendar.py`

**Goal:** Verify Phase 3 v1 create-only scope, PAE rules (APPROVE/REJECT/CLARIFY), UEID cross-fork consistent.

- [ ] **Step 1: List mesh files + line counts**

```bash
cd C:/Users/mathe/code_space/life-oss/life
find src/mesh -name "*.py" | xargs wc -l
```

- [ ] **Step 2: Verify create-only in adapters**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -n "NotImplementedError\|create_only\|action.*create" src/mesh/adapters/*.py
```

Verify: each adapter raises `NotImplementedError` or early-returns for non-create actions (per CLAUDE.md "v1 mesh scope = create only").

- [ ] **Step 3: Verify PAE rules in agent_consumer**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -n "APPROVE\|REJECT\|CLARIFY\|PAE" src/mesh/agent_consumer.py
```

Expected: 3 PAE decision rules present.

- [ ] **Step 4: Verify append-only queue**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -n "append_only\|atomic\|os.O_APPEND" src/mesh/queue.py
```

- [ ] **Step 5: Update working file + commit**

Append findings; commit as:

```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): Layer 3 src/mesh/ inspection + N gaps"
```

---

## Task 5: Static Read — Layer 4 (MCP Gateway)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-10-system-review-working.md`
- Read: `src/ikigai/src/mcp_server/*.py` + `src/ikigai/src/agents/v2/mcp_bridge.py`

**Goal:** Verify 12 IKIGAI_TOOLS + 7 fork tools + 6 resources; flag tools whose names suggest PAV math execution (per attribution design — known gap).

- [ ] **Step 1: Enumerate all MCP tools**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -rn "@MCP.tool\|@mcp.tool" src/ikigai/src/mcp_server/ | head -30
```

Count distinct tool names. Expect 12 IKIGAI + 7 fork = 19 (per CLAUDE.md "22 total MCP tools" — 12 IKIGAI FastMCP + 7 fork HTTP+SSE + 3 ??? check).

- [ ] **Step 2: Enumerate all MCP resources**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -rn "@MCP.resource\|@mcp.resource" src/ikigai/src/mcp_server/ | head -20
```

Expected: 6 resources per CLAUDE.md.

- [ ] **Step 3: Flag PAV-flavored tool names (the known gap)**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -rn "pav\|qhe\|regime\|vector.*score\|heuristics" src/ikigai/src/agents/v2/mcp_bridge.py
```

Each match is a candidate `attribution_leak` gap. Examples seen:
- `ikigai_observe_pav_state`
- `ikigai_score_vectors`
- `ikigai_heuristics`

- [ ] **Step 4: Check the test_canonical_scope.py drift detector for these names**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -n "ikigai_observe_pav_state\|ikigai_score_vectors\|ikigai_heuristics" src/ikigai/tests/test_canonical_scope.py
```

Note whether the drift detector pins these names or not.

- [ ] **Step 5: Update working file + commit**

Document gaps with severity P0 (attribution violated — exposed tool names imply PAV math execution contrary to ADR-013 planner-only).

Commit:
```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): Layer 4 MCP gateway inspection + N gaps (incl. attribution_leak)"
```

---

## Task 6: Static Read — Layer 5 (v2 Agent)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-10-system-review-working.md`
- Read: `src/ikigai/src/agents/v2/graph.py`, `nodes/*.py`, `prompts/*.py`, `prompts/*.md`, `prompts/algorithm_constants.json`, `skills/*.md`

**Goal:** Identify `prompt_leak` gaps — prompts that reference PAV/QHE/regime math despite attribution design saying PAV is archived.

- [ ] **Step 1: List all v2 agent files**

```bash
cd C:/Users/mathe/code_space/life-oss/life
find src/ikigai/src/agents/v2 -name "*.py" -o -name "*.md" -o -name "*.json" | xargs wc -l
```

- [ ] **Step 2: List all 11 node names**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -n "^NODES = \|\"observe\"\|\"score_vectors\"\|\"heuristics\"\|\"balance\"\|\"decompose\"\|\"plan\"\|\"tag_and_persist\"\|\"reflect\"\|\"commit\"\|\"dispatch_sub_agents\"\|\"surface_intentions\"" src/ikigai/src/agents/v2/graph.py | head -15
```

- [ ] **Step 3: Flag PAV-flavored prompts**

```bash
cd C:/Users/mathe/code_space/life-oss/life
grep -rln "Q_HE\|qhe_score\|regime\|PUSH\|MAINTAIN\|RECOVER\|REDUCE\|hysteresis\|vector.*score\|heuristics" src/ikigai/src/agents/v2/prompts/
```

Each match is a candidate `prompt_leak` gap.

- [ ] **Step 4: Inspect `algorithm_constants.json` for algorithm-tunable values**

```bash
cd C:/Users/mathe/code_space/life-oss/life
cat src/ikigai/src/agents/v2/prompts/algorithm_constants.json
```

Identify which keys are PAV/QHE related vs which are infrastructure (subagent/checkpoint/memory/kill_switch).

Expected: only infra keys should remain per ADR-013 + ADR-019; QHE_PUSH_THRESHOLD, REGIME_TARGETS, HEURISTICS_* should NOT be there if PAV is truly archived.

- [ ] **Step 5: Inspect `observe.md` for QHE/regime FSM descriptions**

```bash
cd C:/Users/mathe/code_space/life-oss/life
head -80 src/ikigai/src/agents/v2/prompts/observe.md
```

Verify: does the prompt actually instruct the LLM to compute QHE/regime? Or is it a stale doc?

- [ ] **Step 6: Inspect `skills/*.md` (5 skills: daily/weekly/monthly/quarterly/meta_plan)**

```bash
cd C:/Users/mathe/code_space/life-oss/life
for f in src/ikigai/src/agents/v2/skills/*.md; do echo "=== $f ==="; head -30 "$f"; done
```

Look for: do skills reference `strategics/` PT-BR or PAV/QHE/regime?

- [ ] **Step 7: Update working file + commit**

Document gaps with severity P0 for prompt_leak, severity P2 for node-name inconsistency (11 vs 8 reported by ikigai-chat).

Commit:
```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): Layer 5 v2 agent inspection + N gaps (incl. prompt_leak)"
```

---

## Task 7: Static Read — Layers 6-10 (Foundation + Tools)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-10-system-review-working.md`
- Read: `sys_ikigai/**/*.py`, `vibe-ops/src/**/*.py`, `interfaces/cli/**/*.py`, `interfaces/tui/operator/**/*.py`, `src/ikigai/tests/test_*.py`, `langgraph.json`, `vibe-ops/src/langgraph_entry.py`

**Goal:** Cover Layers 6-10 with same per-layer protocol. Faster pass than Layers 1-5 (smaller surface each).

- [ ] **Step 1: Layer 6 — sys_ikigai/**

```bash
cd C:/Users/mathe/code_space/life-oss/life
find sys_ikigai -name "*.py" | xargs wc -l
grep -rn "QHE\|qhe_score\|regime\|pav_state\|PAV" sys_ikigai/ 2>&1 | head -10
grep -n "vault_write\|sole.writer" sys_ikigai/vault/*.py | head -10
```

Check: any PAV math leaked into core? vault_write sole writer preserved (ADR-012)?

Append Layer 6 section to working file.

- [ ] **Step 2: Layer 7 — vibe-ops/**

```bash
cd C:/Users/mathe/code_space/life-oss/life
find vibe-ops/src -name "*.py" | xargs wc -l
grep -rn "NotImplementedError\|composition.*path" vibe-ops/src/cybernetics/ 2>&1 | head -10
```

Check: composition paths raise NotImplementedError per attribution §3?

Append Layer 7 section.

- [ ] **Step 3: Layer 8 — interfaces/cli/ + interfaces/tui/**

```bash
cd C:/Users/mathe/code_space/life-oss/life
find interfaces/cli interfaces/tui -name "*.py" | xargs wc -l
grep -rn "vault_write\|write.*vault/" interfaces/cli/ interfaces/tui/ 2>&1 | head -10
grep -rn "kill_switch\|kill_switch_tab" interfaces/tui/ 2>&1 | head -10
```

Check: interfaces read vault only, never write? kill_switch tab present in TUI (W5.3)?

Append Layer 8 section.

- [ ] **Step 4: Layer 9 — drift net (re-inspect, do NOT re-run pytest yet)**

```bash
cd C:/Users/mathe/code_space/life-oss/life
wc -l src/ikigai/tests/test_canonical_scope.py src/ikigai/tests/test_drift_invariants.py src/ikigai/tests/test_drift_extended_invariants.py
grep -c "^def test_" src/ikigai/tests/test_canonical_scope.py src/ikigai/tests/test_drift_invariants.py src/ikigai/tests/test_drift_extended_invariants.py
```

Record: how many invariants per file? What's covered (canonical_scope, drift_invariants a-h+, UEID 4-part, append-only, dual-tree identity)? What's NOT covered (e.g., "no prompt mentions QHE", "no MCP tool named *_pav_*")?

Append Layer 9 section.

- [ ] **Step 5: Layer 10 — LangGraph graphs**

```bash
cd C:/Users/mathe/code_space/life-oss/life
cat langgraph.json
grep -n "make_pae_graph\|make_replan_graph\|make_correction_graph\|make_falsification_graph\|make_rollup_graph" vibe-ops/src/langgraph_entry.py 2>&1 | head -10
```

Verify: 5 graphs registered match attribution §6 list (pae_maintainer, quarterly_replan, correction_protocol, dream_falsification, test_de_fogo_rollup).

Append Layer 10 section.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): Layers 6-10 inspection + N gaps"
```

---

## Task 8: Runtime Probes (4 Pontas)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-10-system-review-working.md` (append Runtime Probes section)
- Read: spec for canonical question set

**Goal:** Capture empirical evidence of "ultima ponta" gaps by running the same 5 canonical questions through ikigai-chat, TUI Chat tab, CLI v2 daily, and MCP gateway responses. Diff against attribution design + strategics/.

**NOTE:** These probes are manual/interactive — the engineer executes them in sequence, captures output, documents in working file.

- [ ] **Step 1: Probe set definition**

5 canonical questions (per spec §3 step [2]):

1. "o que é o PAE?"
2. "como funciona a hierarquia de planejamento?"
3. "o que é regime FSM?"
4. "como sincroniza vault com forks?"
5. "qual é o formato UEID?"

Expected answer for each (per attribution design + strategics/):
- Q1: "PAE = Plano Anual Estratégico (PT-BR framework em `strategics/`); IKIGAI é o deep agent separado"
- Q2: "5 níveis: SONHOS → OBJETIVOS → METAS → TAREFAS → ATIVIDADES; dual-frame PAE × Hierarchical"
- Q3: "PAV/QHE/regime FSM está arquivado em `archive/legacy-pav/src-operational/` desde 2026-08-31 (commit `cc51acc`); IKIGAI é planner-only per ADR-013"
- Q4: "vault é SOT append-only; sync via `vault_write` MCP tool único writer (ADR-012); forks (tuiboard/taskdog/solverforge-calendar) emitem/recebem via data mesh"
- Q5: "UEID 4-part: `<CLUSTER>:<ENTITY>:<HASH>:<SEQ>` per ADR-014"

- [ ] **Step 2: Probe ikigai-chat**

```bash
cd C:/Users/mathe/code_space/life-oss/life
ikigai.bat chat test-thread
```

Inside the REPL, run each of the 5 questions. Capture outputs verbatim.

- [ ] **Step 3: Probe TUI Chat tab**

```bash
cd C:/Users/mathe/code_space/life-oss/life
life tui
```

Navigate to Chat tab. Run each of the 5 questions. Capture outputs verbatim (or describe if TUI doesn't log).

- [ ] **Step 4: Probe CLI v2 daily**

```bash
cd C:/Users/mathe/code_space/life-oss/life
python -m interfaces.cli.main v2 daily --date 2026-09-10
```

Capture stdout/stderr. (Note: v2 daily may not be conversational; instead try `v2 weekly` or any CLI invocation that calls the v2 graph.)

- [ ] **Step 5: Probe MCP gateway responses (if accessible)**

```bash
cd C:/Users/mathe/code_space/life-oss/life
make mcp-inspect
```

Capture tool list + sample tool responses. (Note: MCP gateway is stdio; may require FastMcpClient setup per Phase 8.5.)

- [ ] **Step 6: Diff probe outputs vs expected answers**

For each of the 5 questions × 4 entry-points (20 comparisons), flag:
- Match: ✅ no gap
- Mismatch: ❌ gap with `{ponta, question, actual_output_summary, expected_output_summary, severity_guess}`
- Severity escalation: per spec §3 [2], "severity escalates by +1 tier per additional ponta where the gap appears, capped at P0"

- [ ] **Step 7: Update working file + commit**

Append to working file:

```markdown
## Runtime Probes (4 Pontas × 5 Questions = 20 comparisons)

**Ponta 1: ikigai-chat** — captures from Step 2
**Ponta 2: TUI Chat tab** — captures from Step 3
**Ponta 3: CLI v2** — captures from Step 4
**Ponta 4: MCP gateway** — captures from Step 5

**Mismatches:** [list each]
```

Commit:
```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): runtime probes — N mismatches across 4 pontas"
```

---

## Task 9: Drift Net Cross-Reference + Gap Triage

**Files:**
- Modify: `docs/superpowers/specs/2026-09-10-system-review-working.md` (consolidate all gaps with severity)

**Goal:** Run drift net again, link failures to provisional gaps, identify new `invariant_gap`s. Apply severity tiers per spec §3 [4]. Tag fixable vs ADR proposal. Tag root_cause_layer.

- [ ] **Step 1: Run drift net — all 3 test files**

```bash
cd C:/Users/mathe/code_space/life-oss/life
python -m pytest src/ikigai/tests/test_canonical_scope.py src/ikigai/tests/test_drift_invariants.py src/ikigai/tests/test_drift_extended_invariants.py -v 2>&1 | tail -60
```

If PASS counts match Task 1 baseline, no regression. If different, investigate.

- [ ] **Step 2: Identify drift net failures that map to provisional gaps**

For each failure, find the matching provisional gap in working file by keyword (file path, function name, etc.).

- [ ] **Step 3: Identify provisional gaps that have NO test coverage**

These become `invariant_gap` (severity P1) — gaps without drift detection.

For each such gap, draft a test stub (not committed in this plan):
- New test function name
- New test location (`src/ikigai/tests/test_canonical_scope.py` likely)
- Assert statement that would catch the gap

- [ ] **Step 4: Apply severity tiers (per spec §3 [4])**

For each gap in working file, assign P0/P1/P2/P3 with explicit justification:

```markdown
- **GAP-001** [P0 attribution_leak] `ikigai_observe_pav_state` tool name implies
  PAV execution contrary to ADR-013 planner-only.
  Evidence: src/ikigai/src/agents/v2/mcp_bridge.py:74
  Root cause: Layer 4 (MCP gateway) — naming convention
  Fixable: yes (rename tool)

- **GAP-002** [P1 invariant_gap] No drift detector ensures prompts don't
  reference QHE/regime outside archived context.
  Evidence: src/ikigai/tests/test_canonical_scope.py (no such test)
  Root cause: Layer 9 (drift net) — missing invariant
  Fixable: yes (add new drift test)

- **GAP-003** [P2 ux_inconsistency] ikigai-chat reports 8 nodes; graph.py
  has 11 nodes.
  Evidence: ikigai-chat output vs graph.py:50-65
  Root cause: Layer 5 (prompts) — stale docstring in agent persona
  Fixable: yes (update persona)
```

- [ ] **Step 5: Tag root_cause_layer for every gap**

Most gaps have root cause in Layer 4-5 (MCP gateway + v2 agent). Some in Layer 9 (drift net missing invariants).

- [ ] **Step 6: Commit consolidated working file**

```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): gap triage — N P0, M P1, K P2, J P3 gaps tagged"
```

---

## Task 10: Write Diagnosis Document

**Files:**
- Create: `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md`
- Read: `docs/superpowers/specs/2026-09-10-system-review-working.md` (source of truth)

**Goal:** Consolidate working file into a formal diagnosis with: per-layer gap table, drift net violations, attribution violations, prioritized remediation recommendations. This is the deliverable that user reviews before any code-fixing plan.

- [ ] **Step 1: Write diagnosis header**

Create `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md`:

```markdown
# IKIGAI System Top-Down Review — Diagnosis

**Date:** 2026-09-10
**Companion spec:** `docs/superpowers/specs/2026-09-10-system-review-design.md`
**Companion plan:** `docs/superpowers/plans/2026-09-10-system-review-remediation.md`
**Companion baseline:** `docs/superpowers/specs/2026-09-10-drift-net-baseline.md`

---

## Summary

[Total gaps by severity: P0/N0, P1/N1, P2/N2, P3/N3]

[1-paragraph synthesis: which layers had the most gaps, which root_cause_layers dominate, what the prioritized remediation looks like]

---

## Per-Layer Findings

### Layer 1 — strategics/
[copy from working file]

### Layer 2 — src/contracts/
[copy]

### ...

### Layer 10 — LangGraph graphs
[copy]

---

## Drift Net Violations

[Test failures cross-referenced with gaps]

---

## Attribution Violations

[PAV revival attempts, scope violations, etc.]

---

## Runtime Probe Mismatches

[5 questions × 4 pontas = 20 comparisons; only mismatches listed]

---

## Prioritized Remediation Recommendations

Ordered by severity (P0 first), then by root_cause_layer proximity to user-facing ponta.

| Rank | Gap ID | Severity | Root cause | Title | Recommended fix type |
|------|--------|----------|-----------|-------|----------------------|
| 1 | GAP-001 | P0 | Layer 4 | MCP tool name `ikigai_observe_pav_state` | Rename + drift test |
| 2 | ... | ... | ... | ... | ... |

**Fix types:**
- **Rename:** mechanical, low risk, fast
- **Drift test add:** add new invariant to test_canonical_scope.py
- **Prompt edit:** sanitize prompt templates to not reference archived PAV
- **ADR proposal:** violation of attribution; document in `docs/decisions/pending/` for user adjudication, NO code change

---

## Out-of-Scope (deferred to future plan)

[List any gap that needs code changes; this diagnosis RECOMMENDS but does not EXECUTE]
```

- [ ] **Step 2: Fill in all sections from working file**

For each "Layer N — ..." section, copy findings from `2026-09-10-system-review-working.md`.

For Prioritized Remediation table, order by:
1. Severity (P0 first)
2. root_cause_layer (Layer 4-5 first, then Layer 9, then Layer 8)
3. Estimated fix effort (rename = fast, drift test add = medium, prompt edit = medium, ADR proposal = slow)

- [ ] **Step 3: Commit diagnosis**

```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-system-review-diagnosis.md
git commit -m "docs(review): diagnosis — N gaps catalogued, prioritized remediation drafted"
```

- [ ] **Step 4: Mark working file as superseded (optional)**

If diagnosis is finalized and working file is no longer needed:

```bash
cd C:/Users/mathe/code_space/life-oss/life
git rm docs/superpowers/specs/2026-09-10-system-review-working.md
git commit -m "chore(review): remove superseded working file (consolidated into diagnosis)"
```

If unsure, leave it. Future audit may want the raw layer-by-layer trail.

---

## Task 11: MEMORY Entry + Drift Net Post-Check

**Files:**
- Create: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/system-review-gaps-2026-09-10.md`
- Modify: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md`
- Modify: `docs/superpowers/specs/2026-09-10-drift-net-baseline.md` (append post-check)

**Goal:** Persist findings to MEMORY (append-only, never edit existing entries). Add 1-line index in MEMORY.md. Re-run drift net, record post-check in baseline doc.

- [ ] **Step 1: Write MEMORY entry**

Create `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/system-review-gaps-2026-09-10.md`:

```markdown
---
name: ikigai-system-review-gaps-2026-09-10
description: Top-down review of IKIGAI agentic system — N gaps catalogued across 10 layers; attribution_leak + prompt_leak dominate
metadata:
  type: project
---

# IKIGAI System Review — Gap Catalogue (2026-09-10)

**Origin:** User compared ikigai-chat vs Claude Code output for "what is PAE"
question; 10+ divergences surfaced. Triggered top-down review per spec
`docs/superpowers/specs/2026-09-10-system-review-design.md`.

**Diagnosis doc:** `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md`

**Total gaps:** [N0 P0, N1 P1, N2 P2, N3 P3]

**Top gaps (P0):**

- **GAP-001 attribution_leak:** MCP tool `ikigai_observe_pav_state` (and 2
  siblings) name implies PAV math execution contrary to ADR-013 planner-only
  + attribution design.
  Evidence: `src/ikigai/src/agents/v2/mcp_bridge.py:74`
  Recommended fix: rename tool → `ikigai_observe_state` + add drift test
  in `test_canonical_scope.py`.

- **GAP-002 prompt_leak:** Multiple v2 prompts reference QHE/regime FSM
  (e.g. `observe.md`, `heuristics_regime_observation.py`,
  `algorithm_constants.json` defines QHE_PUSH_THRESHOLD etc).
  Evidence: `src/ikigai/src/agents/v2/prompts/` (15 files)
  Recommended fix: drain algorithm_constants.json to infra-only, rewrite
  prompts to cite `strategics/` and not PAV.

- **GAP-003 ux_inconsistency:** ikigai-chat reports 8 nodes; v2 graph
  has 11. Hierarchy reported as 4-level; strategics/ has 5-level.
  Evidence: spec §0
  Recommended fix: update persona / prompts.

**Why:** System was supposed to be planner-only per ADR-013 + attribution
design (2026-08-29), but PAV vocabulary leaked through prompts/MCP-tool
names/v2 node names into LLM context, producing user-visible drift.

**How to apply:** When touching IKIGAI v2 agent, MCP gateway, or drift net,
reference this diagnosis for the open gaps. Do NOT silently revive PAV
vocabulary; the gaps here are about REMOVING it, not tuning it.

**Related:** [[algorithm-attribution-decisions-2026-08-29]],
[[archived-feature-not-vocabulary-2026-09-06]],
[[algorithm-gate-dropped-2026-09-03]]
```

- [ ] **Step 2: Add MEMORY.md index line**

Read `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md`, then append a new line in the appropriate section (likely "User / decisions (active)" or "Architecture / scope (CANONICAL)" — engineer chooses):

```markdown
- [IKIGAI system review gaps 2026-09-10](ikigai-system-review-gaps-2026-09-10.md) — N gaps across 10 layers; attribution_leak + prompt_leak dominate
```

- [ ] **Step 3: Re-run drift net for post-check**

```bash
cd C:/Users/mathe/code_space/life-oss/life
python -m pytest src/ikigai/tests/test_canonical_scope.py -v 2>&1 | tail -10
python -m pytest src/ikigai/tests/test_drift_invariants.py -v 2>&1 | tail -10
python -m pytest src/ikigai/tests/test_drift_extended_invariants.py -v 2>&1 | tail -10
```

Record PASS counts.

- [ ] **Step 4: Append post-check to baseline doc**

Edit `docs/superpowers/specs/2026-09-10-drift-net-baseline.md`, append:

```markdown
---

## Post-Review Check (Task 11 of `2026-09-10-system-review-remediation.md`)

| Test file | PASS (baseline) | PASS (post) | Δ |
|-----------|-----------------|-------------|---|
| test_canonical_scope.py | N1 | N1' | 0 |
| test_drift_invariants.py | N2 | N2' | 0 |
| test_drift_extended_invariants.py | N3 | N3' | 0 |
| **TOTAL** | **N** | **N'** | **0** |

**Note:** Drift net count unchanged because this plan produces
diagnosis only; no code/test changes. Future plan implementing
remediation will modify drift net counts (expected: +M new invariants).

**Drift net version (post):** `<git rev-parse HEAD>`
```

- [ ] **Step 5: Commit**

```bash
cd C:/Users/mathe/code_space/life-oss/life
git add docs/superpowers/specs/2026-09-10-drift-net-baseline.md
git commit -m "chore(review): drift net post-check — unchanged (diagnosis only)"
```

The MEMORY entry + MEMORY.md index line are in `~/.claude/`, which is outside the git repo. They're persisted as files on disk.

- [ ] **Step 6: Verify final state**

```bash
ls -la ~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/system-review-gaps-2026-09-10.md
grep "ikigai-system-review-gaps-2026-09-10" ~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md
cd C:/Users/mathe/code_space/life-oss/life && git log --oneline -n 7
```

Expected:
- MEMORY file exists
- MEMORY.md has the index line
- Git log shows the 6 commits from this plan's tasks

---

## Self-Review (post-plan-write)

**1. Spec coverage:**
- §1 Architecture → covered by Tasks 2-7 (per-layer protocol)
- §2 Components → covered by Tasks 2-7 (per-layer protocol)
- §3 Data flow → covered by Tasks 2-11 sequence (read → probe → cross-ref → triage → diagnosis → memory)
- §4 Error handling → covered by §4 of spec; not a task per se but enforced in Task 9 step 4 (severity tier)
- §5 Testing → covered by Task 1 (baseline) + Task 11 (post-check) + drift net in Task 9
- §6 Scope → covered (no code changes in this plan; remediation deferred to future plan)
- §7 Known starting point → confirmed/refuted during Task 5-6
- §8 Deliverables → covered (Task 1 + Task 10 + Task 11 produce all 5 artifacts)
- §9 Related memory → covered (cited in MEMORY entry step 1)

**2. Placeholder scan:**
- No "TBD", "TODO", "implement later" in task bodies ✓
- Code blocks contain real commands ✓
- Step outputs explicit ("Expected: PASS" / "Expected: FAIL") ✓
- File paths exact ✓

**3. Type consistency:**
- Severity tiers (P0-P3) consistent across spec §3, Task 9, diagnosis table ✓
- Drift net commands identical in Tasks 1, 9, 11 ✓
- Working file path `2026-09-10-system-review-working.md` consistent across Tasks 2-9 ✓
- Diagnosis file path `2026-09-10-system-review-diagnosis.md` consistent in Task 10 + Task 11 ✓
- MEMORY entry path consistent in Task 11 ✓
- MEMORY index line format matches other entries in MEMORY.md ✓

---

## Plan Metadata

**Total tasks:** 11
**Estimated time:** 2-3 hours (mostly reading + manual probes)
**Risk:** Low (no code changes; append-only docs)
**Next plan (post-user-decision):** Remediation plan for prioritized fixes. Will be a new plan after user reviews diagnosis.
