# Algorithm Issues Registry — IKIGAi / PAV — Data-First Phase

> **⚠️ ADR-007 propagation note (2026-08-29):** The 31 items catalogued in this registry are **correctly deferred** (algorithm work waits), but the cited reason ("5 SONHO logs gate") was a **propagated misconception**. The actual gate is **system readiness** (backend + data + agent functional), per `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`. Re-resolution of items in this registry requires the system-readiness gate to open, NOT a SONHO counter to reach 5/5.

> **Status.** Living document. Created 2026-07-02 during the closing-2026 data-first
> documentation pass. **No code changes** — only diagnostic findings, mapped to the canonical
> TW (Trajectory/Planning) × EW (Execution/Logging) hierarchy. Each issue carries:
>
> - **Severity** — `BLOCKER` (cannot reason further) / `HIGH` (will mis-score on first real log)
>   / `MEDIUM` (off by definition) / `LOW` (cosmetic, doc drift)
> - **Scope** — `TEMPLATE` / `PERSONA` / `CODE` / `DOC` / `META`
> - **Status** — `OPEN` / `DEFERRED` / `RESOLVED-DRAFT` / `RESOLVED`
>
> **Resolution policy.** Per ADR-007 (data-first), nothing is "fixed" until 5+ SONHO logs
> confirm the inconsistency is real-world, not just a doc typo. Until then, registry entries
> accumulate. When the threshold is crossed, items graduate to ADRs.

---

## 0. Index

| Range | Category | Count |
|-------|----------|-------|
| **N01..N05** | Nomenclature / taxonomy collisions | 5 |
| **A01..A09** | Algorithm / math issues | 9 |
| **D01..D05** | Data drift (template ↔ persona ↔ code) | 5 |
| **P01..P04** | Persona (mock-dataset) internal errors | 4 |
| **X01..X04** | Cross-cutting / systemic | 4 |
| **M01..M02** | Meta / governance | 2 |
| **Total** | | **31** |

---

## Section N — Nomenclature / Taxonomy

### N01 — Vector count mismatch (5 vs 4)

| Severity | HIGH | Scope | META | Status | OPEN |
|----------|------|-------|------|--------|------|
| **Sources** | | | | |
| 1. `CLAUDE.md` §"IKIGAi meta-brain": *"5 vectors: Passion, Skill, Market, Revenue, **Course**"* |
| 2. `README.md` arch §: 5 vectors (P/S/M/R/C) |
| 3. `code-docs/ikigai/ikigai-as-dom-on-planning-engine.md` §1.1: 5 vectors, including Course |
| 4. `.omo/ikigai/mock-datasets/00-sonho_example.md` §8: **5 rows** (Passion/Skill/Market/Revenue/Course) |
| 5. `vibe-ops/planning/_templates_periodos_v2/01-sonho.md` §8: **4 rows only** |
| 6. `vibe-ops/planning/_templates_periodos_v2/03-onda.md` §1, §9: 4 vectors |
| 7. `vibe-ops/planning/_templates_periodos_v2/02-avaliacao-trimestral.md` §7: 4 vectors |
| 8. `vibe-ops/planning/_templates_periodos_v2/06-quartely-review.md` §3: 4 vectors |
| 9. PRD-07: 4 vectors (no Course column) |
| 10. `vibe-ops/src/models/ikigai_entities.py` (18 lines, hypothetical from naming pattern): 4 fields |
| 11. `vibe-ops/src/pipeline/ikigai_scorer.py` (46 lines): references 4 vector fields |

**Root cause.** Course vector added to the IKIGAi conceptual model (passion/skill/market/revenue +
course) after templates were authored. The "5th vector" never propagated into the periodic
templates or the code that should compute the score.

**Impact.** Sonnet cannot reference Course in any quarterly/onda/semanal/diario alignment
table. Persona Marina explicitly uses Course(3,0.55) — the math breaks when she copies her
sonho template into onda/revisao templates.

**Resolution gate.** User decision: is Course a separate vector or subsumed under "Skill"?
If separate, every template with §"IKIGAi Alignment" needs a 5th row; if merged, every
sonho/onda example needs reconciliation.

---

### N02 — Period unit suffix (`_wd` vs `_cd`) — nomenclature collision (Fonte A vs B)

| Severity | BLOCKER | Scope | META | Status | RESOLVED-DRAFT |
|----------|---------|-------|------|--------|----------------|

**RESOLVED-DRAFT** per prior session (definitive proposal: Canonical = Fonte B with `*_wd` /
`*_cd` suffix everywhere). Awaiting 5+ SONHO empirical validation per ADR-007 before
graduating to ADR-008.

| OBJETIVO | 3 × ONDAS | 45 wd (33 cd × ρ) |
| META | 1 ONDA_WD | 15 wd |
| TAREFA | 1 SPRINT | 5 wd |

Wait — the row 1 is incorrect. Let me fix:

| OBJETIVO | 3 × ONDAS | 45 wd |
| META | 1 ONDA_WD | 15 wd |
| TAREFA | 1 SPRINT | 5 wd |

---

### N03 — Phase 5 onboarding confusion (PUSH/M/REDUCE/RECOVER vs MAINTAIN)

| Severity | LOW | Scope | DOC | Status | OPEN |
|----------|-----|-------|-----|--------|------|

`vibe-ops/src/pipeline/policy_engine.py` and `vibe-ops/base/IKIGAi.md` use both "MAINTAIN" and
"PUSH" as sibling states. The state machine in `Points_of_premisses-task-habits.md` lists them
in order PUSH→MAINTAIN→REDUCE→RECOVER (4 states), but a few internal-doc sections refer to
"PUSH/MAINTAIN/REDUCE/RECOVER" interchangeably with "OPTIMIZE/HOLD/DROP/RECOVER" wording.

**Resolution.** Pin state names to `PUSH | MAINTAIN | REDUCE | RECOVER` in `code-docs/adr/`
once 5+ state transitions are observed.

---

### N04 — Diâmetros / Tensão / Regime — overlapping vocabularies

| Severity | MEDIUM | Scope | DOC | Status | OPEN |
|----------|--------|-------|-----|--------|------|

`CONCEPTUAL_MODEL.md` introduces "Tensão→Comportamento→Solução" and 5 tensões. The
`policy_engine.py` uses "regime". `Points_of_premisses-task-habits.md` uses "regime FSM".
They are not formally bound; e.g. "Tensão 1 = Sleep" maps informally to "RECOVER regime" but
no canonical mapping table exists.

**Resolution.** Create `.omo/ikigai/meta/tensao-regime-map.md` once 5+ weekly reviews surface
the link in practice.

---

### N05 — "Onda 3 (Dias 91-135... ou D-90)" semantic ambiguity in 00 template

| Severity | HIGH | Scope | TEMPLATE | Status | OPEN |
|----------|------|-------|----------|--------|------|

`vibe-ops/planning/_templates_periodos_v2/00-quartely-planning.md` §4.3 has label:
*"Onda 3 (Dias 91-135... ou D-90)"* — this is internally contradictory (91-135 is 45 cd, but
"D-90" suggests 90 cd). It conflates `cd` (calendar days) and `wd` (work days).

**Resolution.** Edit template §4.3 to specify `Onda 3 (Dias 46-60 wd, ou D-90 cd)`. **Note:**
this violates the append-only rule for `vibe-ops/` — must follow Refactor Protocol
(STOP → propose Action Plan → wait for Approval Gate → only then mutate).

---

## Section A — Algorithm / Math Issues

### A01 — Q_HE weights Σ = 0.90 (not 1.0)

| Severity | MEDIUM | Scope | DOC | Status | OPEN |
|----------|--------|-------|-----|--------|------|

`Points_of_premisses-task-habits.md` declares weights `w_sono=0.35, w_med=0.20, w_workout=0.25,
w_lunch=0.10, η=0.15` (where η is the "overall multiplier" or "Q_HE_bias"). Σw_i = 0.90, not 1.0.

**Q_HE formula.** `Q_HE = η · (w_sono·sono_norm + w_med·med_norm + w_workout·workout_norm + w_lunch·lunch_norm)`

If η = 0.15 is intended as a "scale", then `Q_HE_max = 0.15 × 0.90 = 0.135` — the 0.65
threshold is unreachable. If η = 1.0 and the residual 0.10 is "free", it's missing a
component (e.g. `w_reading=0.10`).

**Sources for Q_HE threshold 0.65:**
- persona `04-relatorio-diario_example.md` §7: threshold ≥ 0.65
- persona `01-trimestral_example.md` §3.3: target qhe 0.65
- `meta_heuristics.md` (referenced in SCALAR_DECOMPOSITION_BACKLOG): DOWN at 0.60

**Resolution.** Specify whether η is a scale, a fifth weight (rename to `w_residual`), or an
unrelated bias term. Pick one. Until then, every Q_HE computation across the 5 levels is
inconsistent.

---

### A02 — RECOVER trigger ambiguity (3 distinct thresholds)

| Severity | HIGH | Scope | CODE+DOC | Status | **PARTIALLY RESOLVED — A02.1 pending** |
|----------|------|-------|----------|--------|

Three different RECOVER entry conditions coexist in the documentation:

1. **Persona `01-trimestral_example.md` §7.2 + quarterly §7.1:**
   `Q_HE < 0.30 OR infractions ≥ 3` — emergency floor, single-day entry.
2. **`Points_of_premisses-task-habits.md` §"PolicyEngine FSM":**
   `Q_HE < 0.60 sustained 2 days OR sleep_debt > 2h` — early warning, multi-day.
3. **`SCALAR_DECOMPOSITION_BACKLOG.md` MODEL-005:**
   `Q_HE < 0.60 OR consecutive_sleep_misses ≥ 2` — early warning variant.

**Impact.** Two different thresholds (0.30 vs 0.60) trigger the same state. Different
trigger vocabularies (`infractions` vs `sleep_debt` vs `consecutive_sleep_misses`) for the
same state machine.

**Resolution (2026-08-26 — INNER GUIDELINES):**
- INNER GUIDELINES canonical: `RECOVER < 0.60` — single threshold, no 0.30 floor.
- **A02.1 OPEN:** The persona's `Q_HE < 0.30` emergency floor is NOT in the canonical
  INNER GUIDELINES table. Decision required: keep 0.30 as EMERGENCY sub-state inside RECOVER,
  or remove it entirely. Per Proibição constitucional: "nunca confundir fase com regime" —
  EMERGENCY would be a *phase* (not a *regime*).

**A02.1 pending:** Define EMERGENCY sub-state scope — is it a *phase* or a *regime*?

---

### A03 — Verdict Score math (template §3.3) — undocumented divisor 8

| Severity | MEDIUM | Scope | TEMPLATE | Status | OPEN |
|----------|--------|-------|----------|--------|------|

`00-quartely-planning.md` §3.3: `verdict_score = (media_teste_fogo * 0.5) + (leading_cumprido * 0.3) + (histerese_sustentada * 0.2)`.

`05-relatorio-diario.md` §7: `verdict_score = 0.5 × completion_rate + 0.3 × (sono_horas/8) + 0.2 × qhe`.

The divisor `8` for `sono_horas` is undocumented — is 8 the `sleep_target` (PUSH regime),
or a universal normalization constant? Persona `04-relatorio-diario_example.md` §7
uses `7.6/8 = 0.95` despite Marina being in MAINTAIN regime where sleep_target = 8.0h.
No clamp — `sono_horas = 12` would give `1.5` (impossible).

**Resolution.** Either: (a) clamp `(sono_horas / sleep_target)` where `sleep_target = π(s_t)`
[regime-dependent], or (b) document 8 as a hard constant and add clamp `[0, 1]`.

---

### A04 — Persona Verdict Score arithmetic error (`0.62` claimed, `0.50` correct)

| Severity | HIGH | Scope | PERSONA | Status | OPEN |
|----------|------|-------|---------|--------|------|

`.omo/ikigai/mock-datasets/00-sonho_example.md` §5:
*"verdict_score = 0.5 × 0.78 + 0.5 × (1 − 0.78) = 0.5 × 0.78 + 0.5 × 0.22"* (text truncates
here; then states *"≈ 0.62"*). The math gives `0.39 + 0.11 = 0.50`, not 0.62.

**Either** the formula is wrong (should yield 0.62 with some different inputs), **or** the
arithmetic is wrong (should claim ≈0.50).

**Resolution.** First manually fill 5 SONHO logs and see which one actually applies. Until
then, this is an exemplar of how personas will mislead any user copying from them.

---

### A05 — Persona §6 self-contradiction (PARTIAL → PASS same paragraph)

| Severity | MEDIUM | Scope | PERSONA | Status | OPEN |
|----------|--------|-------|---------|--------|------|

`00-sonho_example.md` §6: First sentence says *"Verdict: PARTIAL"*, then the next line
says *"Veredito Final: PASS"*. No transition explanation.

**Resolution.** Update mock-dataset to a single verdict per the actual algorithm. Until then,
any reader using this persona as a template will reproduce the ambiguity.

---

### A06 — Persona IKIGAi Total: simple avg vs weighted (template mismatch)

| Severity | HIGH | Scope | PERSONA+TEMPLATE | Status | OPEN |
|----------|------|-------|-----------------|--------|------|

Template `01-sonho.md` §8 specifies weighted aggregation (each vector has its own weight).
Persona `01-trimestral_example.md` §6 uses **simple average**:
*(0.83+0.74+0.71+0.58+0.69)/5 = 0.71*.

Template weights (per `00-quartely-planning.md` §3.2): `Execucao=0.50, Analise=0.20,
Plan=0.15, Aprend=0.10, Bem-estar=0.05` → Σ=1.00. With those weights, persona's 5-dim
0.83/0.74/0.71/0.58/0.69 gives:
`0.5×0.83 + 0.2×0.74 + 0.15×0.71 + 0.10×0.58 + 0.05×0.69 = 0.76`.

**Persona 0.71 vs weighted 0.76** — they differ. User copying the persona into real SONHO
fills will use simple avg; spec says weighted. Real Sonnet's total will not match the
system's.

**Resolution.** Pin persona example to template formula (weighted). Or revise template to
simple average. Decision-blocked on 5+ SONHO.

---

### A07 — Verdict Score clamp missing (son's_score unbounded)

| Severity | LOW | Scope | TEMPLATE | Status | OPEN |
|----------|-------|-------|----------|--------|------|

`05-relatorio-diario.md` §7 has no clamp on `(sono_horas / 8)`. A 12h sleep gives `1.5`
and the verdict_score exits `[0, 1]`. Persona `04-relatorio-diario_example.md` §7
explicitly writes `7.6/8 = 0.95`, which is fine — but the formula does not enforce it.

**Resolution.** Add `min(1, sono_horas / sleep_target)` to the template formula.

---

### A08 — WORK_RATIO ρ = 22/30 ≈ 0.7333 (good but under-documented)

| Severity | LOW | Scope | DOC | Status | OPEN |
|----------|-------|-------|-----|--------|------|

`ρ = 22/30 ≈ 0.7333` is the calendar-to-workdays conversion used everywhere (45 wd × ρ ≈ 33 cd,
etc.). The choice of 22 workdays/month (not 20 or 22.5) is not justified in any doc.

**Resolution.** Document the rationale (Brazilian CLT 22 dias úteis/mês) or pin a different
ratio and recompute all the constants.

---

### A09 — Hysteresis asymmetric (3d UP, 2d DOWN, immediate RECOVER)

| Severity | MEDIUM | Scope | DOC+CODE | Status | OPEN |
|----------|--------|-------|----------|--------|------|

`Points_of_premisses-task-habits.md` + `00-quartely-planning.md` §7.1 declare:
- 3-day sustained Q_HE≥0.85 → UPGRADE
- 2-day sustained Q_HE<0.65 → DOWNGRADE
- Emergency (Q_HE<0.30 OR infractions≥3) → immediate RECOVER
- 3-day sustained Q_HE≥0.65 → exit RECOVER

The asymmetry (3-up vs 2-down) is intentional ("harder to advance than to retreat") but no
underlying theory is cited. Persona practice shows 2-day drops but 3-day recoveries.

**Resolution.** Document the theoretical basis (asymmetric loss function? anti-fragility
principle?) or pin as empirical heuristic. Either way, make it grep-able in one place.

---

## Section D — Data Drift (Template ↔ Persona ↔ Code)

### D01 — WAVE drift: 15 wd (canonical) vs 33 wd (Marina Onda 01 actual)

| Severity | HIGH | Scope | PERSONA | Status | OPEN |
|----------|------|-------|---------|--------|------|

`02-onda_example.md` frontmatter: `xp_gained: 312, mastery_delta: 0.08` (15 wd period).

But `01-trimestral_example.md` §4.2 declares *"Onda 1: 11 wd (2026-07-06 → 2026-07-24)"* (date
range 2026-07-06 → 2026-07-24 = 19 cd = 13 wd ≈ 11 wd minus weekends — this is plausible).
**However**, §4.3 says *"Onda 3 spans 33 wd (2026-08-17 → 2026-09-30)"* — 33 wd is **2.2× the
canonical ONDA size of 15 wd**.

**Impact.** If 3 ONDAS span 33 + 11 + 11 = 55 wd, but CYCLE (OBJETIVO) is 45 wd, the algebra
collapses. Probably Marina's `04-revisao-semanal_example.md` (not yet read) will clarify.

**Resolution.** Read 03-revisao-semanal_example.md; reconcile persona's 11-wd Onda with
spec's 15-wd Onda. Likely: Marina used a non-standard "study sprint" definition, not the
spec's "Onda". Renaming in the persona.

---

### D02 — SCALAR_DECOMPOSITION_BACKLOG module path conflict

| Severity | HIGH | Scope | DOC | Status | OPEN |
|----------|------|-------|-----|--------|------|

`SCALAR_DECOMPOSITION_BACKLOG.md` references module paths:
- `models/habit_engine.py` — MODEL-001..004, 006, 017, 018, 021, 022, 023, 024
- `models/policy_engine.py` — MODEL-005, 007, 008
- `models/temporal.py` — MODEL-025, 026, 027

But the actual code location (per `CLAUDE.md` §"PAV kernel") is
`life-ops/operational/packages/core/src/operational/core/` — NOT `vibe-ops/src/models/`.

**Impact.** When 5+ logs are collected and the user starts coding, the SCALAR plan will
direct them to write `vibe-ops/src/models/habit_engine.py` — which contradicts the
"Standalone" invariant (`life-ops/operational/` must not import from `vibe-ops/`).

**Resolution.** Update SCALAR_DECOMPOSITION_BACKLOG to use the canonical PAV path:
`life-ops/operational/packages/core/src/operational/core/`.

---

### D03 — 3 Q_HE thresholds (0.65 / 0.65 / 0.60)

| Severity | HIGH | Scope | PERSONA+DOC | Status | **RESOLVED by INNER GUIDELINES** |
|----------|------|-------|-------------|--------|

`Points_of_premisses-task-habits.md`: DOWN @ 0.60 (2d).
`meta_heuristics.md` (per SCALAR): DOWN @ 0.60.
Persona examples: 0.65.
`00-quartely-planning.md` §7.1: UP @ 0.85, DOWN @ 0.65 (2d).

**Three thresholds (0.60, 0.65, 0.85)** for one operator. The `meta_heuristics.md` 0.60
might be the "early warning" threshold (separate from "DOWNGRADE" 0.65); needs explicit
distinction.

**Resolution (2026-08-26 — INNER GUIDELINES canonical):**
```
PUSH     ≥ 0.85
MAINTAIN 0.70 – 0.85   ← previously 0.65 in some docs (D03 gap now closed)
REDUCE   0.60 – 0.70   ← previously 0.60 in some docs
RECOVER  < 0.60         ← single threshold; no separate 0.30 emergency floor
```
**Hysteresis:** UP requires 3 consecutive days; DOWN requires 2 consecutive days.
The INNER GUIDELINES from `strategics/` layer (constitutional) now provides the
single canonical threshold table. A02 (RECOVER emergency floor 0.30) is addressed
separately (see A02 status update below).

---

### D04 — 3 sources for `infractions` metric — none define it

| Severity | MEDIUM | Scope | PERSONA+DOC | Status | OPEN |
|----------|--------|-------|-------------|--------|------|

`Points_of_premisses-task-habits.md`, persona quarterly §7.2, and SCALAR_DECOMPOSITION all
reference `infractions` as a metric — but no document defines what an infraction is. Is it:
- A missed pomodoro? A skipped daily report? A broken non-negotiable invariant?

**Resolution.** Define `infraction = (planned_task − completed_task)` per day, aggregated
to 3-day/7-day window. Or invent a 5-level enum (no-infraction, light, medium, heavy,
critical) tied to specific non-negotiables.

---

### D05 — Encoding artifact: Chinese characters in PT-BR doc

| Severity | LOW | Scope | PERSONA | Status | OPEN |
|----------|-------|-------|---------|--------|------|

`.omo/ikigai/mock-datasets/04-relatorio-diario_example.md` line ~50: *"10min呼吸 meditation"* — the
character `呼吸` is Chinese for "breath". This is a copy-paste artifact from a meditation
app, not intentional content.

**Resolution.** Replace with PT-BR: *"10min meditação respiratória"*.

---

## Section P — Persona Internal Errors

### P01 — Persona Onda §8 totals 17, not 15

| Severity | MEDIUM | Scope | PERSONA | Status | OPEN |
|----------|--------|-------|---------|--------|------|

`.omo/ikigai/mock-datasets/02-onda_example.md` §8 *"Policy Trail: Dias em PUSH: 15, MAINTAIN: 2,
REDUCE: 0, RECOVER: 0"* — total = 17 wd, but an Onda is 15 wd.

**Resolution.** Either recount or note that 2 days straddled the Onda boundary. Document in
persona metadata.

---

### P02 — Persona §7.2 occupation 171% (over-budget default)

| Severity | HIGH | Scope | PERSONA+TEMPLATE | Status | OPEN |
|----------|------|-------|-----------------|--------|------|

Persona `01-trimestral_example.md` §7.2: *"Taxa ocupação = 171%"* — Marina notes this is
*"impossível"* and recalibrates `48 → 30 pomodoros/week`.

This shows the **template defaults are over-budget by design**, requiring manual
recalibration. No template warning flags this. Likely root: `pomodoros_meta` default
exceeds regime capacity (PUSH regime allows ~4h/day × 22 wd ≈ 88 pomodoros/month ≈ 22/week).

**Resolution.** Add a `pomodoros_warning_threshold = regime_capacity × 1.0` to the template
header. Cross-check 5+ SONHO.

---

### P03 — Filename bug: 04-relatorio-diario_example.md is daily, not weekly

| Severity | LOW | Scope | PERSONA | Status | OPEN |
|----------|-------|-------|---------|--------|------|

`.omo/ikigai/mock-datasets/04-relatorio-diario_example.md` filename suggests Revisão
Semanal (weekly review), but content is a daily report (2026-07-08, Wed W1).

**Resolution.** Rename to `00-relatorio-diario_example.md` (and shift other examples) or
split the file into the correct period.

---

### P04 — Persona IKIGAi Total denominator / 20 vs / 5

| Severity | MEDIUM | Scope | PERSONA | Status | OPEN |
|----------|--------|-------|---------|--------|------|

`00-sonho_example.md` §8: *"IKIGAi Total atual: (3.40+3.70+1.92+1.80+1.65) / 20 = 0.624"*.

Sum / 20.0 = 12.47 / 20 = 0.624 ✓ (arithmetic OK). But why divide by 20?

5 vectors, each scored `0..4` (1-5 scale), so max = 20. Marina sum = 12.47 → 0.624 of max.

Template `01-sonho.md` §8 (per memory of the read) uses weighted aggregation. Persona uses
`/ 20` normalization.

**Resolution.** Pick one: weighted aggregation (template) OR sum/max (persona). Persona
can document the math but should match the spec.

---

## Section X — Cross-cutting / Systemic

### X01 — H/E/Q_HE unit drift across 5 levels

| Severity | MEDIUM | Scope | DOC+CODE | Status | OPEN |
|----------|--------|-------|----------|--------|------|

`H(t) = 1 − e^(−λ·streak)` — dimensionless `streak` (count, days).
`E = R·(1 − H(t))` — `R` is in hours, but `H` is dimensionless. Units mismatch.
`Q_HE` — dimensionless, in `[0, 1]`.

The unit error is hidden because `H` is bounded `[0, 1)` and `R` is an "energy required"
constant — but no document defines what `R` represents (kWh? kcal? subjective units?).

**Resolution.** Add an `Units` appendix to `Points_of_premisses-task-habits.md` with
explicit unit declarations.

---

### X02 — Repository count: 14 `_PersistentRepo` instances vs ~4 active

| Severity | MEDIUM | Scope | CODE | Status | OPEN |
|----------|--------|-------|-----|--------|------|

Per `.omo/ikigai/meta/tui-screen-survey.md` introduction: *"14 `_PersistentRepo` instances
but ~4 active in practice"*. This is a code-smell, but more importantly a **data-shape
question** — is the 14-entity model over-fitted for 4-entity usage?

**Resolution.** After 5+ SONHO logs, decide which 10 entities to defer vs which 4 to keep.

---

### X03 — SCALAR_DECOMPOSITION_BACKLOG `import` graph assumes paths that don't exist

| Severity | HIGH | Scope | DOC+CODE | Status | OPEN |
|----------|------|-------|----------|--------|------|

Beyond the path conflict (D02), the SCALAR backlog references `MODEL-022`, `MODEL-023` —
models that may not have Python signatures yet defined. Module dependencies (e.g. `temporal`
imports `policy_engine`) presume forward-compatible stubs.

**Resolution.** Sweep the SCALAR backlog and mark each MODEL as `{PLANNED, STUB, PARTIAL,
COMPLETE}`. Until then, the backlog is aspirational, not actionable.

---

### X04 — Q3 calendar vs workdays: 87 cd ≠ 90 cd ≠ 64 wd

| Severity | MEDIUM | Scope | PERSONA | Status | OPEN |
|----------|--------|-------|---------|--------|------|

Persona `01-trimestral_example.md`: `date_start: 2026-07-06, date_end: 2026-09-30`. Span =
87 cd (not 90 — Q3 calendar would be 92 cd; user's manual selection skipped 5 days).

If 87 cd, and ρ = 22/30 ≈ 0.7333, then expected wd = 87 × 0.7333 ≈ 64 wd. But Marina
3-onda sum: 11 + 11 + 33 = 55 wd (per D01). Or 11 + 11 + 11 = 33 wd (canonical 3 × 15-wd ONDAS
ignoring D01 drift). Neither matches 64 wd.

**Resolution.** Pick a canonical WD calculation method: (a) actual calendar with weekday
count, (b) ρ-conversion, (c) manual annotation. Pin one.

---

## Section M — Meta / Governance

### M01 — Append-only vs Edit: which docs are append-only?

| Severity | MEDIUM | Scope | META | Status | OPEN |
|----------|--------|-------|------|--------|------|

`CLAUDE.md` §"Global Conventions" lists `vibe-ops/`, `strategics/`, all cluster docs as
append-only. `_templates_periodos_v2/` lives inside `vibe-ops/planning/` — are the templates
themselves append-only? Or can they be edited (which would silently fix N05, A03, A07)?

**Resolution.** Refactor Protocol invoked on `_templates_periodos_v2/`. Action Plan:
1. List every edit candidate (N05, A03, A07, plus A04 reference in persona).
2. Identify any user-context strings that must survive byte-for-byte.
3. Wait for Approval Gate.
4. Then edit.

---

### M02 — Persona is meant to be reused; bugs in persona are bugs in user's future data

| Severity | HIGH | Scope | META | Status | OPEN |
|----------|------|-------|------|--------|------|

Per ADR-007 data-first, the user will *manually copy* the persona (Marina) into their own
real SONHO fills. Every math error, encoding artifact, or self-contradiction in the persona
**propagates to the user's data**. Hence `A04`, `A06`, `P01`, `P02` are all `HIGH` severity,
not `LOW` — they directly poison the future corpus.

**Resolution.** Persona files (under `.omo/ikigai/mock-datasets/`) must be elevated to
"high-rigor" status — treated like test fixtures, not draft examples. Add a
`mock-dataset-validation.md` checklist.

---

## Appendix A — Source coverage matrix

| Source | Templates | Persona | Code | SCALAR | Notes |
|--------|-----------|---------|------|--------|-------|
| `CLAUDE.md` | — | — | refs | refs | Source of canonical invariants |
| `_templates_periodos_v2/*.md` | 9 docs | — | — | — | Append-only (?) per M01 |
| `.omo/ikigai/mock-datasets/*.md` | refs | 5 docs | — | — | Marina persona |
| `.omo/ikigai/meta/*.md` | — | — | — | — | Socratic + survey + this registry |
| `code-docs/ikigai/*.md` | refs | — | refs | refs | DOM-on-planning-engine |
| `vibe-ops/src/{models,pipeline}/*.py` | refs | — | 2 files | refs | ikigai_scorer + ikigai_entities |
| `life-ops/planner/{SCALAR,Points}.md` | refs | — | refs | self | Math anchors |
| `life-ops/operational/apps/tui/...` | — | — | 14 repos | — | PAV kernel |

---

## Appendix B — Severity hot-list (HIGH+)

**BLOCKER (1)**
- N02 — Period unit suffix (resolved-draft, awaiting ADR-008)

**HIGH (10)**
- N01 — 5 vs 4 vector count
- N05 — Onda 3 days ambiguity (91-135 vs D-90)
- A02 — RECOVER trigger ambiguity
- A04 — Persona Verdict math error
- A06 — Persona simple avg vs weighted
- D01 — WAVE drift 33 wd vs 15 wd
- D02 — SCALAR module path conflict
- D03 — 3 Q_HE thresholds
- P02 — Persona occupation 171% over-budget
- M02 — Persona bugs propagate to user data

**Total items:** 31
**Resolved:** 0
**Resolved-draft:** 1 (N02)
**Deferred to ADR gate:** 1 (N02→ADR-008)
**Pure documentation drift (low risk):** 19

---

## Appendix C — Resolution priority queue (suggested order)

1. **D02 (HIGH)** — SCALAR module path. Cheap, mechanical fix. Update doc to point to
   `life-ops/operational/packages/core/src/operational/core/`. Removes a future code-step
   roadblock.
2. **M01 (MEDIUM)** — Resolve append-only ambiguity for `_templates_periodos_v2/`. Required
   before any of N05/A03/A07 can be addressed.
3. **N01 (HIGH)** — Vector count decision (4 vs 5). Should be resolved before any persona
   data fill, since it determines the alignment table format.
4. **A02 (HIGH)** — RECOVER trigger pin. Defines the alert pipeline.
5. **D03 (HIGH)** — Q_HE threshold tier set. Foundation for persona math.
6. **D04 (MEDIUM)** — Define `infractions`. Required for A02.
7. **A01 (MEDIUM)** — Q_HE weight clarification. Removes ambiguity in the math.
8. **A03, A04, A06, A07, P01..P04** — Persona + template alignment.
9. **D01, D05, X01..X04** — Cross-cutting. Resolve after the above.

---

*Registry scaffold: Algorithm Issues Registry v1 · IKIGAi Sys-01 · 2026-07-02 · Cluster PLAN.
Maintained by PAE-Maintainer agent (proposed) + manual review during data-first phase.*