# Deep-Dive Diagnostic Log — IKIGAi / PAV — 2026-07-02

> **Session goal.** Per user *"proceed to every deep dive logs"* — full diagnostic pass over
> the data-first corpus (`vibe-ops/planning/_templates_periodos_v2/`,
> `.omo/ikigai/mock-datasets/`, `.omo/ikigai/meta/`, `life-ops/planner/`,
> `life-ops/operational/apps/tui/`).
>
> **Result.** 31 issues catalogued in `algorithm-issues-registry.md`. This log is the
> *narrative* layer: it walks the user through what was found, what is still coherent, and
> what blocks real Sonnet-data fills. All severity, scope, and resolution-gate reasoning
> lives in the registry; this file is the read-once synthesis.

---

## 1. The TW × EW hierarchy in 30 seconds

The user's canonical hierarchy (verbatim, with the `_wd` vs `_cd` resolution from N02):

| Layer (TW = Trajectory / EW = Execution) | Horizon (Fonte B) | Verdict vocabulary | Aggregation |
|----|----|----|----|
| SONHO (T) | 6-18 months | ACTIVE / VALIDATED / FALSIFIED / PIVOTED / ABANDONED | (single) |
| TRIMESTRE (T) | 3 × ONDAS = 45 wd | PASS / PARTIAL / FAIL | 3 SONHOs |
| ONDA (T) | 15 wd | CONTINUE_WAVE / CORRECT_TRAJECTORY / KILL_WAVE | 3 weeks |
| SEMANA (EW) | 7 d | PASS / PARTIAL / FAIL | 7 days |
| DIA (EW) | 1 d | PASS / PARTIAL / FAIL | (single) |
| ── ATIVIDADES / CÓDIGO ── | (deferred) | — | (TW) |

The TW/EW split is **what was missing from every prior diagnostic**: the SONHO/OBJETIVO/META/TAREFA
stack is *trajectory* (planning-as-falsification), while SEMANA/DIA is *execution* (logging-as-data).
The two planes share `ikigai_vector`, `parent_period`, and the verdict aggregator, but differ
in **direction of truth** (TW says *"what we will do"*; EW says *"what we did"*).

---

## 2. What is **coherent** (kept working)

Despite 31 issues, the structural skeleton holds:

1. **All 9 templates exist** (`00` through `08`) and each has frontmatter + numbered sections.
2. **The ID chain works** — `sonho_id` → `parent_period` FKs traverse the full hierarchy.
   Verified: `03-revisao-semanal_example.md` frontmatter `parent_period: onda-01-climate-tech-internal-demo`,
   `sonho_id: marina.climate-tech-lead.2027` — both consistent with the README's ID chain diagram.
3. **The 5-vector IKIGAi scoring is in the README** (PASS / SKILL / MARKET / REVENUE / COURSE)
   with consistent start/mid/target deltas. This is the **only** place Course is documented
   correctly end-to-end.
4. **The policy FSM (PUSH/MAINTAIN/REDUCE/RECOVER) is exercised in the persona** —
   `03-revisao-semanal_example.md` §4 records 4 PUSH + 1 MAINTAIN + 2 RECOVER = 7 days (matches
   the hysteresis rules in §7.1 of the quarterly template: 3-up / 2-down). The *individual*
   persona daily report is internally consistent.
5. **The completion-rate aggregation rule** (simple 7-day mean) matches the README's
   *"How Verdicts Aggregate Upward"* table.
6. **The Pomodoro log + Taskwarrior + Timewarrior sync chain** is referenced (in `03-...` §8)
   and uses the canonical sync language (`life sync vault`).

So the user's mental model of "5 levels + 5 vectors + 4 regimes" is **structurally sound**.
The bugs are in details, not in the skeleton.

---

## 3. What **is broken** — top-10 issues to fix first

Ranked by **what blocks the user's first real SONHO fill**:

### 3.1 — `vector count: 5 in README, 4 in templates/code/persona` (N01, HIGH)
The user will copy a SONHO with 5 vectors into a quarterly template that has 4 rows.
**Mechanical fix:** add Course row to every `_templates_periodos_v2/*.md` template §"IKIGAi
Alignment". **Cost:** 8 template edits (00, 02, 03, 04, 05, 06, 07, 08). **Risk:** if templates
are append-only (M01), this needs Refactor Protocol. **Alternative:** declare Course subsumed
under Skill in the spec — but then Marina's persona loses her Course dimension.

### 3.2 — `Q_HE weights Σ = 0.90` (A01, MEDIUM)
Marina's Q_HE values in `04-relatorio-diario_example.md` (0.71) and the weekly review
(`qhe_medio: 0.71`) match — meaning the persona *applied* the same formula. But which
formula? The text in `Points_of_premisses-task-habits.md` says `Σw_i = 0.90`, leaving 0.10
unaccounted for. The user will copy this and arrive at `Q_HE_max = 0.15 × 0.90 = 0.135`,
which can never reach the 0.65 threshold. **Mechanical fix:** pick one of (a) `η = 1.0`
and rename `η` → `w_residual`, OR (b) keep `η = 0.15` and rescale `Σw_i` to 1.0 by adding a
5th weight `w_reading = 0.10`.

### 3.3 — `RECOVER trigger: 3 sources` (A02, HIGH)
The persona uses `Q_HE < 0.30 OR infractions ≥ 3` (emergency); the docs use
`Q_HE < 0.60 sustained 2d` (early warning); SCALAR uses `Q_HE < 0.60 OR
consecutive_sleep_misses ≥ 2`. **Resolution:** a single trigger rule. Persona floor
(0.30) becomes EMERGENCY sub-state; 0.60 is the RECOVER entry; `infractions` definition
needs D04 first.

### 3.4 — `SCALAR_DECOMPOSITION_BACKLOG path conflict` (D02, HIGH)
SCALAR says write `vibe-ops/src/models/habit_engine.py`. Real PAV lives at
`life-ops/operational/packages/core/src/operational/core/`. **Mechanical fix:** update
SCALAR §"Module/file map" + every `MODEL-XXX` reference. **Cost:** doc edit only,
~20 lines.

### 3.5 — `ONDA length drift` (D01, HIGH)
Three numbers in three docs:
- Template: 15 wd (canonical)
- Persona `01-trimestral_example.md` §4.3: 33 wd (Onda 3)
- README §"5-Minute Walkthrough": ~45 wd per Onda

Marina's `03-revisao-semanal_example.md` §1 says *"15 business days"* for Onda 01,
which **matches the template**. So the canonical is 15 wd. README is wrong, persona §4.3
is wrong. **Resolution:** edit README walkthrough to *"3 Ondas of 15 business days each =
45 wd total"*; edit persona `01-trimestral_example.md` §4.3 Onda 3 dates to actual 15 wd
window.

### 3.6 — `Q_HE threshold: 3 sources` (D03, HIGH)
Persona uses 0.65. `Points_of_premisses-task-habits.md` uses 0.60. SCALAR inherits 0.60.
Template §7.1: UP @ 0.85, DOWN @ 0.65 (2d). **Resolution:** tier set
`WARN ≤ 0.70 < DOWN ≤ 0.60 < EMERGENCY ≤ 0.30`. Persona 0.65 becomes the WARN → DOWN
threshold; 0.85 is the UPGRADE threshold.

### 3.7 — `Q3 calendar math: 87 cd ≠ 90 cd ≠ 64 wd` (X04, MEDIUM)
Persona `01-trimestral_example.md` `date_start: 2026-07-06, date_end: 2026-09-30` = 87 cd.
ρ = 0.7333 → 64 wd. But 3 ONDAS × 15 wd = 45 wd. **Resolution:** either pick actual
calendar (Mon-Fri count) or ρ-conversion; pin one. Document choice in
`SCALAR_DECOMPOSITION_BACKLOG.md`.

### 3.8 — `infractions metric: undefined` (D04, MEDIUM)
3 docs use it, none define it. **Resolution:** define `infractions_3d = sum(planned −
completed, 3 days)` with a 5-level enum (none/light/medium/heavy/critical). Or:
infraction = broken non-negotiable invariant. Pick the latter (simpler, matches Q4
template).

### 3.9 — `Verdict Score divisor 8` (A03, MEDIUM)
Template `05-relatorio-diario.md` §7: `(sono_horas/8)`. **Resolution:** use
`(sono_horas / sleep_target)` where `sleep_target = π(s_t)` (regime-dependent). Add
clamp `[0, 1]`.

### 3.10 — `persona propagation risk` (M02, HIGH)
The persona is treated as "reference example", but per ADR-007 data-first, the user will
*copy* Marina's structure into their real SONHO. So:
- A04 (Verdict math error 0.62 vs 0.50) — will propagate verbatim.
- A05 (PARTIAL → PASS self-contradiction) — will reproduce the ambiguity.
- D05 (Chinese `呼吸` encoding artifact) — will appear in real data.

**Resolution:** treat persona files as "test fixtures"; require validation checklist
(`mock-dataset-validation.md`) before any persona is published.

---

## 4. What is **implicit** (not yet in any doc)

These are patterns the docs gesture at but never state:

### 4.1 — The `ikigai_vector` field on a weekly review is a **single value**
`03-revisao-semanal_example.md` frontmatter: `ikigai_vector: skill`. This implies the
weekly review picks **one dominant vector** for the week (the "lead bet"). Templates
`04-revisao-semanal.md` and `02-onda.md` use `ikigai_vector: [P | S | M | R]` (single
choice). The SONHO has 5, the TRIMESTRE has 1, the ONDA has 1, the SEMANA has 1, the
DIA has 1. **The 5 vectors are an aggregation property of SONHO only.**

### 4.2 — The `verdict_score` is **shared across all 5 levels**
Daily `0.5×completion + 0.3×(sono/sleep_target) + 0.2×qhe`. Weekly same formula. Trimestral
different formula (`0.5×media_teste_fogo + 0.3×leading_cumprido + 0.2×histerese_sustentada`).
Onda different (`completion_medio ≥ 0.75`).
**There is no single "verdict_score" formula.** Each level has its own. The naming
collision implies a homogeneity that isn't there. **Resolution:** rename per-level
(formula_v1, formula_v2, etc.) or document the divergence.

### 4.3 — The `_wd` suffix is **only used in v2 templates and SCALAR**
`Hierarquia de Objetivos.md` (PT-BR strategics) uses no suffix. `Planejamento (E&T).md`
also no suffix. The `_wd`/`_cd` resolution (N02) is **only half-applied** — it lives in
this session's synthesis but not in the canonical docs. **Resolution:** when N02
graduates to ADR-008, edit both PT-BR strategics files to use `_wd`/`_cd`.

---

## 5. What's **missing entirely** (gaps)

1. **No "correction protocol" template (gap B)** — when an ONDA verdict is
   CORRECT_TRAJECTORY or KILL_WAVE, what is the actual workflow? Templates reference §10
   *"Rota de Correção"* but no template exists to fill it. **Defer until 5+ SONHO.**
2. **5-D Teste de Fogo not in daily template (gap A)** — only the quarterly template has
   the 5-dim × 4-week test. The daily template should propagate leading/lagging indicators
   up; today it doesn't. **Defer until templates actually filled.**
3. **No `09-sprint-correction.md` template** — same reason.
4. **No `tensao-regime-map.md`** (per N04) — Tensão→Regime mapping not formalized.
5. **No `mock-dataset-validation.md`** (per M02) — persona QA process absent.
6. **No `entity_count_decision.md`** (per X02) — 14 `_PersistentRepo` instances vs ~4
   active. Which 10 to defer? Decision deferred to 5+ SONHO.

---

## 6. The user's actual workflow (reconstructed)

From the persona + templates + memories:

```
Sonnet (Q3-Q4 2026) — write dreams, decide which verticals, define bets.
  ↓ (Q3 starts 2026-07-06)
Trimestre Q3-2026 — pick 1 bet, decompose to 3 ONDAS, decide regime.
  ↓
Onda 01 (15 wd, e.g. 2026-07-06 → 2026-07-24) — break into 3 SPRINTS,
each SPRINT = 1 SEMANA = 5 wd. Pick 1 IKIGAi vector for the onda.
  ↓
Semana W1 (Mon-Sun, 5 wd) — list Top-3 must-haves. Run daily reports.
Policy trail: 7 days × {PUSH|MAINTAIN|REDUCE|RECOVER}.
  ↓
Dia D (1 day) — pomodoros, sleep, Q_HE. Verdict: PASS/PARTIAL/FAIL.
  ↓
Activity / Code (the TW×EW cut-off: "daqui pra baixo nao vamos mexer em nada")
```

The **fractal**: SONHO has 5 vectors; TRIMESTRE has 1 bet; ONDA has 1 vector; SEMANA has
1 vector; DIA has 1 vector. The "5 → 1 → 1 → 1 → 1" propagation is implicit in the
frontmatter but never documented.

---

## 7. Path to "first real SONHO fill"

The user must, in order:

1. **Decide Course vector** (N01) — keep it 5th or fold into Skill?
2. **Decide append-only status of `_templates_periodos_v2/`** (M01) — Refactor Protocol
   if "edit allowed".
3. **Apply mechanical fixes** (D02, A07, A09, A03) — pure documentation cleanup, ~50
   lines total.
4. **Define `infractions`** (D04) — requires 5+ weekly reviews or a heuristic decision.
5. **Pin Q_HE threshold tier set** (D03, A01) — `WARN/DOWN/EMERGENCY` triplet.
6. **Pin RECOVER trigger** (A02) — single rule, ~3 lines.
7. **Decide ρ-conversion method** (X04, D01) — calendar count vs ρ vs manual.
8. **Re-run the persona files** with the corrected math (closes A04, A05, A06, P01..P04).
9. **Write `.omo/ikigai/mock-datasets/validation.md`** checklist.
10. **Open the Socratic Interview Q1-Q7** (`.omo/ikigai/meta/socratic-interview.md`) —
    answer each, then auto-populate the templates.

**ETA to first real Sonnet fill:** ~3-5 hours of focused work, mostly decisions not typing.

---

## 8. What this session did NOT touch

- **CÓDIGO / ATIVIDADES layer** — explicitly deferred per user *"daqui pra baixo nao vamos
  mexer em nada por enquanto"*.
- **PRD-07, BRD, ARD** — not in the read scope; out of data-first phase.
- **`code-docs/` full sweep** — only `ikigai-as-dom-on-planning-engine.md` was sampled.
- **TUI screens (other than survey)** — `tui-screen-survey.md` covers the 9-screen audit.
- **vibe-ops/src/ source code** — only file-naming patterns inferred; not read line-by-line.
- **`life-ops/life_tatics/`, `taskwarrior/`, `life-ops/planner/ikigai_planning/`** — out of
  scope; the user is focused on the IKIGAi/PAV chain.
- **Phase 5 onboarding (N03)** — secondary.
- **Encoding of `ikigai_vector` across the 5 levels** (4.1 above) — implicit pattern,
  not formalized.

---

## 9. Files created/modified this session

| Path | Action |
|------|--------|
| `.omo/ikigai/meta/algorithm-issues-registry.md` | CREATED — 31 issues, severity, scope, status, resolution queue |
| `.omo/ikigai/meta/deep-dive-log-2026-07-02.md` | CREATED — this file |
| `MEMORY.md` | TO UPDATE — add `algorithm-issues-registry` pointer |

No other files touched. No commits made (per user instruction *"continue, no commit until told"*).

---

## 10. Next session entry-point

If the user resumes with *"continue"*, the natural next step is:

1. **Pick a vector-count decision (N01)** — open the discussion on Course.
2. **Apply the mechanical doc fixes** (D02, A07, A09, A03) — list of edits queued.
3. **Open Q1 of the Socratic Interview** — start collecting the user's actual answer
   (their own SONHO, not Marina's).
4. **Or** — apply the Refactor Protocol for `_templates_periodos_v2/` (per M01) — propose
   Action Plan, await approval.

The user holds the steering wheel; the data-first methodology and the 5-log threshold are
the guardrails.

---

*Deep-dive log v1 · 2026-07-02 · IKIGAi Sys-01 · Cluster PLAN · 31 issues catalogued, 0
code changed, ~280 lines of registry + ~270 lines of synthesis.*