# Strategics ↔ Templates Mapping — IKIGAi Closing-2026

> **Author.** `data-first` meta-scan, 2026-07-02.
> **Sources analyzed.**
> - `strategics/00-ÍNDICE-PROGRESSIVO.md` (425 lines — concept map E/T/O)
> - `strategics/Planejamento (Estratégico e Tático).md` (602 lines — PAE + 5×3×3)
> - `strategics/Hierarquia de Objetivos.md` (278 lines — 4-level cascade)
> - `strategics/Modelagem Operacional.md` (snippet — PAE ↔ Estrutura Hierárquica)
> - `vibe-ops/planning/_templates_periodos_v2/*.md` (9 canonical templates)
> - `.omo/ikigai/meta/socratic-interview.md` (Q1–Q7 + D1–D4)
> - `.omo/ikigai/meta/gap-analysis-2026-07-02.md` (10-section synthesis)
>
> **Purpose.** Before the top-down kickoff `2026/12 ← 07`, this document (a) maps each
> `x(y)` template to its source concept, (b) inventories gaps between `strategics/` and
> templates v2, (c) generates socratic questions to disambiguate Q1–Q7, and (d) flags the
> **dataset standalone location** decision.

---

## 1. The mapping `x(y)` — periods × templates × sources

Notation: `x` is the period/level; `y` is the canonical template; `s` is the
`strategics/` document where the concept originates.

| Period `x`             | Horizon           | Template `y` (v2)                      | Source `s`                  | Cadence of fill        |
|------------------------|--------------------|----------------------------------------|------------------------------|------------------------|
| **Sonho**              | 6–12 months        | `01-sonho.md`                           | `Hierarquia de Objetivos` §Nível 1 | 1× per quarter kickoff |
| **Trimestre**          | 90 days (Q1–Q4)    | `00-quartely-planning.md`               | `Planejamento (E&T)` §1.2    | 1× per quarter         |
| **Avaliação Trimestral** | 90d post-mortem   | `02-avaliacao-trimestral.md`            | `Planejamento (E&T)` §3 (Teste de Fogo) | 1× per quarter end |
| **Onda**               | 15 d úteis (3 sem) | `03-onda.md`                            | `Planejamento (E&T)` §1.1 (Hierarquia: METAS) | 6× per half (≈6 waves/half) |
| **Revisão Semanal**    | 7 d                | `04-revisao-semanal.md`                 | `Planejamento (E&T)` §2.3 (Supervisão)  | 13× per quarter        |
| **Relatório Diário**   | 1 d                | `05-relatorio-diario.md`                | `Hierarquia de Objetivos` §Nível 4 | daily                 |
| **Quartely Review (T2)** | 90d OKR-grade     | `06-quartely-review.md`                 | `Planejamento (E&T)` §3.2 (OKR-style review) | 1× per quarter |
| **Sprint Kickoff (T3)** | 5 d úteis         | `07-sprint-kickoff.md`                  | (NEW — proposed) Maps to `Planejamento (E&T)` §2.2 (Blocos diários) | per wave |
| **Sprint Retro (T4)**  | 5 d úteis          | `08-sprint-retrospective.md`            | (NEW — proposed) Maps to `Planejamento (E&T)` §3.1 (Kaizen) | per wave |
| **Diário Avaliativo**  | 1 d                | (gap — see §3.A)                        | `Hierarquia de Objetivos` §3.4 | daily — UNCOVERED |

**Read this table as the wiring diagram.** Filling a `01-sonho.md` requires reading
`Hierarquia de Objetivos` §Nível 1; filling a `05-relatorio-diario.md` requires reading
`Hierarquia de Objetivos` §Nível 4 + `Planejamento (E&T)` §2.2 (blocos diários).

---

## 2. Where the standalone local dataset lives

The persistent question from the user — *"ainda não entendi onde vai ficar o nosso
dataset local de trabalho standalone"* — has four paths, with **trade-offs**:

### 2.A — `.omo/ikigai/` (current scratchpad, gitignored)

| Pro | Con |
|-----|-----|
| Already structured (meta + mock-datasets + closing-2026). | **Line 4 of `.gitignore` excludes ALL `.omo/`.** Files cannot be `git commit`-ed. |
| Coherent with `strategics/planning-with-files/v3.1.3` (the canonical engine uses `.omo/plans/`, `.omo/drafts/`, `.omo/evidence/`). | 99-archive annual closing **lost on machine failure**. |
| Easy to edit locally without polluting repo. | Hard to share; collaborators can't `git clone`. |

**Verdict.** Fits the "data-first methodology" *Phase 1* (observation, scratchpad), but
**fails** as long-term home of the 6-month dataset.

### 2.B — `life-ops/ikigai/` (alongside PAV kernel)

| Pro | Con |
|-----|-----|
| Versioned in git. | **Violates STANDALONE rule** (`life-ops/operational/` must not import from root `life/` or `vibe-ops/`, but `life-ops/ikigai/` is separate and can co-exist). |
| Coherent with `life-ops/operational/` (the active dev target). | Splits "ikigai" across two paths (`.omo/` for plans + `life-ops/` for archive). |
| Discoverable by `code-docs/00-INDEX.md`. | |

**Verdict.** Best for the 99-archive (annual closing) but creates a split-brain.

### 2.C — `vibe-ops/ikigai/` (alongside the cybernetic engine)

| Pro | Con |
|-----|-----|
| Coherent with `vibe-ops/` SyncEngine — direct read by the chokepoint. | **Append-only rule** (`vibe-ops/`, `strategics/`, cluster docs forbid deleting/pruning/rewriting) — but this is a NEW directory, so append-only is the default. |
| Versioned. | Risk of being mistaken for engine source by `vibe-ops/contributors`. |

**Verdict.** Coherent if IKIGAi will be wired into SyncEngine (ADR-006 plan). For now,
**defer**.

### 2.D — `code-docs/ikigai/` (alongside other code-docs)

| Pro | Con |
|-----|-----|
| Versioned, co-located with `code-docs/adr/ADR-007-data-first-methodology.md`. | `code-docs/` is *spec docs* (PRDs, BRDs, ADRs, SPECs) — not *operational data*. |
| Clean separation: spec lives in `code-docs/`; ops data lives in `life-ops/` or `.omo/`. | May be mistaken for "spec draft" instead of "user dataset". |

**Verdict.** Best for **spec scaffolding** (this file, future ADRs, future SPECs),
**NOT** for the Marina-persona templates or closing-2026/.

### 2.E — Recommendation

| Content | Recommended path | Rationale |
|---------|------------------|-----------|
| Specs, ADRs, methodology docs (this file) | `code-docs/ikigai/` | Specs version with the repo |
| Mock-dataset exemplar (Marina persona) | `life-ops/ikigai/mock-datasets/` | Reference shape, versioned |
| Closing-2026 working dataset (Q3 + Q4 + 99-archive) | `life-ops/ikigai/closing-2026/` | Versioned annual dataset |
| In-flight scratch (`.omo/plans/`, `.omo/drafts/`, `.omo/evidence/`) | `.omo/` (gitignored) | Stays as agent runtime |

**Action required from user.** Approve the **dual-write pattern**: scratchpad stays in
`.omo/ikigai/` (gitignored, working dir), canonical copy lives in `life-ops/ikigai/`
(versioned). Or override `.gitignore` with `!.omo/ikigai/` to keep the single-path model.

---

## 3. Gaps between `strategics/` and templates v2

### Gap A — Teste de Fogo (5 dimensions) ↔ `05-relatorio-diario.md`

`Planejamento (E&T)` §3 defines the **Teste de Fogo** with 5 dimensions:
**Resiliência · Coerência · Eficiência · Adaptabilidade + Suporte**.

Templates v2's `05-relatorio-diario.md` has a `Verdict` of `PASS|PARTIAL|FAIL` but
**does not break the verdict into 5D**. → Cannot compute media_teste_fogo at quarter
level (templates v2 §6 expects aggregated daily PASS-rates per dimension, but only
binary daily verdict is captured).

**Fix proposal.** Extend `05-relatorio-diario.md` §10 with 5 sub-scores
(`Resiliência_score`, `Coerência_score`, `Eficiência_score`, `Adaptabilidade_score`,
`Suporte_score`), each 0.0–1.0, summing to `Verdict = PASS` if avg ≥ 0.65.

### Gap B — Correção do Trajeto (3 layers) ↔ missing template

`Planejamento (E&T)` §3.2 specifies **3 correction layers**:
1. **Diagnóstico Pré** — what triggered the deviation
2. **Protocolo Durante** — what to do DURING the next 5d
3. **Garantia Pós** — what confirms the fix took hold (re-measure at +15d)

Templates v2 cover `02-avaliacao-trimestral.md` (post-mortem) and `06-quartely-review.md`
(OKR-grade) but **have no dedicated `correction-protocol.md`**. → When a `03-onda.md`
ends in `KILL_WAVE`, there is no place to record the 3-layer trajectory correction.

**Fix proposal.** Add `09-correcao-trajeto.md` to v2 — fills after `KILL_WAVE` verdict
with the 3 layers.

### Gap C — `07-sprint-kickoff.md` and `08-sprint-retrospective.md` are unmapped to `Planejamento (E&T)`

`Planejamento (E&T)` §2.2 (Blocos diários) and §3.1 (Kaizen) describe sprint-scale
execution but the **sprint template itself** is not anchored in any section of `Planejamento (E&T)`.
→ Gap because templates v2 added sprints (T3/T4) WITHOUT updating the strategics
documents.

**Fix proposal.** Either (i) append a section to `Planejamento (E&T)` describing sprints,
OR (ii) treat templates v2 as the canonical spec and deprecate `Planejamento (E&T)` §2.2/§3.1.

### Gap D — `05-relatorio-diario.md` doesn't anchor to specific `Bloco` (Manhã/Tarde/Noite)

`Hierarquia de Objetivos` §3.4 specifies *turnos*: **Manhã / Tarde / Noite**, with
specific questions per shift.

Templates v2's `05-relatorio-diario.md` has only a single §4 (Hábitos) and §10
(Plano para Amanhã). It does **not** split the day into 3 shifts. → Cannot answer
"Pior turno da semana?" (`Planejamento (E&T)` §3.3 pergunta típica).

**Fix proposal.** Add `Bloco` field to `05-relatorio-diario.md` §2 (Estado Fisiológico)
with sub-entries `Bloco_manha` / `Bloco_tarde` / `Bloco_noite`.

### Gap E — `04-revisao-semanal.md` doesn't capture `Taxa de Conclusão` (Planejamento (E&T) §2.1)

The KPI `Taxa de Conclusão = metas concluídas / metas planejadas × 100` is central in
both `Planejamento (E&T)` §2.1 and `Hierarquia de Objetivos` §3.3, but **templates v2
have no canonical field for it** in `04-revisao-semanal.md` §2.

**Fix proposal.** Add `taxa_conclusao_pct` to frontmatter.

### Gap F — `01-sonho.md` doesn't capture 5-vector IKIGAi scoring

The IKIGAi meta-brain uses 5 vectors (P, S, M, R, C) at 0.0–1.0 each. `01-sonho.md`
in templates v2 has a `Sonho Principal` text but **no 5-vector scoring block**.

**Fix proposal.** Add §8 *IKIGAi Alignment* with row per vector (current, target, delta).

---

## 4. Socratic questions (additional) to close Q1–Q7

The `socratic-interview.md` Q1–Q7 already cover Horizon / Verticals / Bets /
Non-negotiables / Success Signals / Kill Conditions / Known Unknowns. Below are 5
additional questions to close gaps surfaced by this mapping:

### SQ-1 — *Frequência mínima de leitura do Teste de Fogo*
> Para validar uma sonho de 6–12 meses, qual é a frequência mínima aceitável de
> `05-relatorio-diario.md` com 5D Teste de Fogo? (i.e., se eu preencher 60% dos dias,
> ainda é defensável dizer que validei a sonho?)

**Why it matters.** Sets the threshold for "data sufficiency" — needed for the
**Verdict Computado** algorithm in `00-quartely-planning.md` §9.

### SQ-2 — *Bloco-noturno: obrigatório ou opcional?*
> O bloco noturno (`Hierarquia de Objetivos` §3.4) deve ser preenchido **toda noite**
> ou apenas em dias úteis? Se for diário, o threshold de "dias faltantes" muda.

**Why it matters.** Affects 5×3×3 dimension counting (5 d × 3 sem × 3 mo = 45 uteis).

### SQ-3 — *Sprint duration: 5d úteis ou 5 dias corridos?*
> O sprint (T3/T4) é de **5 dias úteis** (= 7 corridos) ou **5 dias corridos**
> (= ~3.5 úteis)? Os templates v2 chamam de "Sprint Kickoff" sem definir a unidade.

**Why it matters.** Affects how many sprints fit in one onda (15d úteis ≈ 3 sprints).

### SQ-4 — *Como o regime (PUSH/MAINTAIN/REDUCE/RECOVER) interage com o Teste de Fogo?*
> O regime state é **input** ou **output** do Teste de Fogo? Hoje parece que ambos
> coexistem (PAV operational state + IKIGAi planning state) sem ponte explícita.

**Why it matters.** Dual sources of truth → contradiction risk. Decide if
`policy_engine.next_state` reads from `media_teste_fogo` or stays independent.

### SQ-5 — *Quem é o dono do "Verdict Computado"?*
> O `Verdict Computado` em `04-revisao-semanal.md` §5 e `00-quartely-planning.md` §9
> — é gerado pelo humano (manual) ou computado automaticamente pelo `pav report`
> command? Se ambos, qual é a fonte de verdade quando discordam?

**Why it matters.** Affects whether templates v2 §9 stays as a *human* aggregation
protocol or becomes a *machine-aggregated* report (sync_engine contract).

---

## 5. Diagnostic summary (dataset × templates × planning × review)

### 5.1 — Assets

| Asset                              | Status        | Versioned? | Notes |
|------------------------------------|---------------|------------|-------|
| 9 templates v2                     | ✅ Ready       | Yes (`vibe-ops/planning/_templates_periodos_v2/`) | Append-only |
| 3 spec docs (index + inventory + ADR) | ✅ Committed | Yes (`code-docs/`) | Just committed |
| 5 meta-docs IKIGAi                 | ✅ Authored    | **No (.omo/ gitignored)** | Move pending |
| 6 mock-dataset files (Marina)      | ✅ Authored    | **No (.omo/ gitignored)** | Move pending |
| 14 closing-2026 placeholder files  | ✅ Authored    | **No (.omo/ gitignored)** | Move pending |
| `strategics-mapping.md`            | ✅ This file   | Yes (`code-docs/ikigai/`) | |

### 5.2 — Templates coverage (per `strategics/`)

- ✅ Sonho, Trimestre, Avaliação Trimestral, Onda, Revisão Semanal, Relatório Diário
- ✅ Quartely Review (T2)
- ✅ Sprint Kickoff (T3), Sprint Retro (T4) — but **unmapped** to strategics (Gap C)
- ❌ Correction protocol (3 layers — `Planejamento (E&T)` §3.2) — **MISSING** (Gap B)
- ❌ Daily Verdict (5D Teste de Fogo) — **MISSING** (Gap A)

### 5.3 — Planning ↔ Review symmetry

The 5×3×3 dimensions imply:

- 5 dias úteis × 3 semanas × 3 meses = **45 evaluation units per quarter**
- Expected fill rate: 45 daily reports × 4 quarters = **180 reports/year**

Templates cover all 180, **but** daily granularity doesn't break into 5D (Gap A).

### 5.4 — Socratic interview readiness (Q1–Q7)

| Q  | Domain              | Ready? | Blockers |
|----|---------------------|--------|----------|
| Q1 | Horizon             | ⚠️ Partial | Course (C) vector has no template row yet |
| Q2 | Verticals           | ⚠️ Partial | If a vertical is *financial*, currency-typed KPI column missing |
| Q3 | Quarterly bets      | ✅ Ready | — |
| Q4 | Non-negotiables     | ⚠️ Partial | `04-revisao-semanal.md` §2 KPI table may need +N rows if >5 invariants |
| Q5 | Success signals     | ⚠️ Partial | Sub-weekly signals can't fit `04-revisao-semanal.md`; must extend `05-relatorio-diario.md` |
| Q6 | Kill conditions     | ⚠️ Partial | If user picks "any-of-N → kill" gate, verdict algorithm needs new branch |
| Q7 | Known unknowns      | ⚠️ Partial | If unknown is *AI framework specialization*, ties to Course (C) vector extension |

**Overall readiness for kickoff `2026/12 ← 07`:** ⚠️ **Conditional on user decision**
about dataset path (§2.E) and Q1 (C-vector extension).

---

## 6. Next-step decision tree

```
START → kickoff user top-down 2026/12 ← 07
   │
   ├──► Decision A: dataset path
   │     ├── A.1 — Keep `.omo/ikigai/` + override .gitignore
   │     ├── A.2 — Dual-write (.omo/ scratchpad + life-ops/ikigai/ canonical)
   │     └── A.3 — Single canonical in life-ops/ikigai/, no .omo/ mirror
   │
   ├──► Decision B: gaps priority (which to fix first)
   │     ├── B.1 — Gap A (5D Teste de Fogo in diário) — HIGHEST (blocks Q5)
   │     ├── B.2 — Gap B (correction-protocol template) — HIGH (blocks Q6)
   │     ├── B.3 — Gap C (sprint mapping) — MEDIUM
   │     ├── B.4 — Gap D (Bloco split) — MEDIUM
   │     ├── B.5 — Gap E (taxa_conclusao_pct) — LOW
   │     └── B.6 — Gap F (5-vector IKIGAi) — HIGH (blocks Q1 if Course > 0.5)
   │
   └──► Decision C: socratic question priority
         ├── SQ-1 (frequência mínima Teste de Fogo) — must answer first
         ├── SQ-2 (Bloco-noturno) — fast (yes/no)
         ├── SQ-3 (sprint duration) — fast
         ├── SQ-4 (regime ↔ Teste de Fogo) — MEDIUM (architectural)
         └── SQ-5 (Verdict owner) — MEDIUM (architectural)
```

---

## 7. Closing note for the user

A leitura tripla de hoje confirmou três coisas:

1. **`Planejamento (E&T)` é o documento conceitualmente mais denso** (602 linhas, 5×3×3
   dimensions, Teste de Fogo 5D, Correção 3 layers). É a **fonte primária** para os
   templates v2 e para o socratic interview.

2. **`Hierarquia de Objetivos` está em colisão com `Planejamento (E&T)` na nomenclatura.**
   O primeiro usa *OBJETIVOS = 15d*, o segundo usa *OBJETIVOS = 3 meses + METAS = 15d*.
   Templates v2 seguem a segunda convenção. Recomendo oficializar a convenção do
   `Planejamento (E&T)` (mais granular) e arquivar `Hierarquia de Objetivos` como histórico.

3. **O `.gitignore` em `.omo/` é o bloqueio #1 do versionamento do dataset.** Sem decisão
   aqui, todos os artefatos `.omo/ikigai/` são *apenas locais*. Recomendo fortemente a
   Decisão A.2 (dual-write) ou A.3 (single canonical).

Aguardando teu sinal para começar o kickoff top-down `2026/12 ← 07`.

---

*Authored: 2026-07-02 · Cluster PLAN · Companion to ADR-007 + socratic-interview.md*