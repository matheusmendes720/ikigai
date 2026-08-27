# Socratic Interview — Annual Closing 2026

> **Purpose.** A scaffolded set of open questions whose answers will populate the
> 6-month horizon (2026-07 → 2026-12) across the 5 IKIGAi templates. Paste free-text
> answers verbatim below each question; structured extraction happens in a follow-up step.

---

# 0. How to use this

1. Open this file and answer each question in order (Q1 → Q7).
2. Paste raw answers **directly under each prompt** — no editing, no bullet-rewriting.
   Long is fine; vague is not.
3. If a question doesn't apply, write **N/A + 1 sentence why** rather than leaving it blank.
4. After the interview, the extracted structured data feeds the manual fill-in of:
   - `_templates_periodos_v2/01-sonho.md` (horizon + IKIGAi vectors)
   - `_templates_periodos_v2/00-quartely-planning.md` (Q3/Q4 bets + KPIs)
   - `_templates_periodos_v2/03-onda.md` (3 waves per quarter)
   - `_templates_periodos_v2/04-revisao-semanal.md` (non-negotiables + signals)
   - `_templates_periodos_v2/05-relatorio-diario.md` (daily invariants)

**Style guide for answers.** Use present tense for current state, future tense for the target.
Anchor dates explicitly (e.g. "by 2026-12-31"). When quoting numbers, give units (h, %, count).

---

# Q1 — Horizon

> **Question.** Where do you want to be on 2027-12-31? Be specific about lifestyle, work,
> health, relationships. Use the 5 IKIGAi vectors: passion (P), skill (S), market (M),
> revenue (R), course (C). For each vector, give a 0.0-1.0 score (current → target).

**Why it matters.** The 12-month horizon is the only input that makes the 6-month and
quarterly bets falsifiable. Without a vector-level target, Q_HE & 5x3x3 aggregates can't
anchor; downstream templates have no north star.

**Anchor-to-template.**
- `01-sonho.md` § 8 *IKIGAi Alignment Check* (Passion / Skill / Market / Revenue rows).
- `01-sonho.md` § 1 *Definição do Sonho (Hipótese Falseável)* — hypothesis text.
- `_drafts/ikigai-as-dom-on-planning-engine.md` § 2.1 — `IKIGAiVectorEntity` storage.

**Gap-analysis columns (what the answer should reveal).**
- Current vs. target delta per vector (>0.3 delta = aggressive, <0.1 = complacent).
- Which vector anchors the **primary sonho** (exactly one, per template § 1).
- Conflicts between vectors (e.g. high-R target incompatible with P-only work).
- Course (C) vector has no template row yet — answer will feed C-extension spec.
- Explicit "by 2026-12-31" checkpoint vs. by "2027-12-31" — the interview asks 2027-12-31
  but the templates roll up only to end-of-2026; expect an interim 2026-12-31 sub-target.

**Spec-implication.**
- If `R-target > 0.7`: the RICE exporter needs a `scale` field to model revenue ramps.
- If `C-target > 0.5`: a 6th `course` vector column is needed in `01-sonho.md` § 8 row.

**[ Paste your answer below this line ]**




---

# Q2 — Verticals

> **Question.** Which 2-3 verticals will you go deep on this half (2026-07 → 2026-12)?
> Examples: work, study, health, relationships, side-project, financial. For each:
> name + intent (1 sentence) + 1 measurable outcome by 2026-12-31.

**Why it matters.** Verticals are how the horizon becomes a portfolio. One vertical = one
macro-epic per quarterly template; two-three is the sweet spot for finite capacity
(avoid spread-thin failure mode flagged in § 1.3 *Capacidade Disponível*).

**Anchor-to-template.**
- `00-quartely-planning.md` § 6 *Top 3 Épicos do Trimestre*.
- `00-quartely-planning.md` § 4 *Desdobramento em 3 Ondas* — each vertical → ≥ 1 wave.
- `01-sonho.md` § 7 *Status dos Dreams Vinculados* — vertical = sonho root.

**Gap-analysis columns.**
- Measurable outcome must use a unit (count, %, currency, hours) — not adjectives.
- Outcomes must be independent (no two verticals sharing the same KPI).
- 2026-12-31 deadline aligns with kill-switch date in `01-sonho.md` § 2.
- "Intent" should fit in one sentence — long intents signal unclear scope.
- Vertical count: ≤ 3 (capacity) ≥ 2 (portfolio diversification).

**Spec-implication.**
- If a vertical is *financial* with $ outcome: needs new currency-typed KPI column in
  `_drafts/ikigai-as-dom-on-planning-engine.md` § 3 *Frontmatter Contract*.
- If a vertical is *relationships*: no current template carries relational KPIs → open
  D5 candidate (extends D1-D4 from the DOM draft).

**[ Paste your answer below this line ]**




---

# Q3 — Quarterly bets

> **Two sub-questions.**
> - **Q3a:** Q3-2026 (Jul → Sep): what is the ONE bet?
> - **Q3b:** Q4-2026 (Oct → Dec): what is the ONE bet?
>
> Each bet must be a **falsifiable hypothesis** (Axis 1 in
> `00-quartely-planning.md` § 2.1): a single statement ending in a measurable outcome,
> a measurement window, and a kill date.

**Why it matters.** One bet per quarter is what makes iteration cheap. Multiple parallel
bets fragment attention and prevent the 5x3x3 distribution from hitting 0.50 on execution.
The falsifiability clause is the contract that lets the system kill without guilt.

**Anchor-to-template.**
- `00-quartely-planning.md` § 2.1 *Hipótese Falsificável (Axis 1 — Kill Switch)*.
- `00-quartely-planning.md` § 8 *Critérios de Saída*.
- `00-quartely-planning.md` § 2.2 *Leading vs Lagging Indicators (Axis 2)* — each bet
  needs ≥ 1 leading and 1 lagging indicator attached.

**Gap-analysis columns.**
- Each bet has **exactly one** outcome metric (no bundled KPIs).
- Kill date ≤ `2026-09-30` for Q3, ≤ `2026-12-31` for Q4.
- Measurement window ≥ 30 days (Axis 1 best-practice note in template).
- Bet should NOT duplicate any Q2 vertical (different axis = orthogonal bet).
- One IKIGAi vector attribution per bet (per `01-sonho.md` § 1 *IKIGAi Vetor Principal*).

**Spec-implication.**
- If either bet lacks a lagging indicator: 5x3x3 weighting shifts — rebalancing Algorithm
  in `00-quartely-planning.md` § 3.3 needs a "leading-only bet" exception case.
- If Q3 bet and Q4 bet collide: triggers a `00-quartely-planning.md` § 10 *Rota de
  Correção* in mid-Q4 (manual pre-emption).

**[ Paste your answer below this line ]**




---

# Q4 — Non-negotiables

> **Question.** What are the 3-5 daily/weekly invariants that CANNOT break for the next
> 6 months? Examples: 7h sleep, daily journal, weekly review, X pomodoros/day.

**Why it matters.** Invariants are the floor below which Q_HE collapses and the system
shifts into RECOVER (per `00-quartely-planning.md` § 7.1 *Histerese Asymmetric*). They are
also the cheapest verification targets — daily reports and weekly reviews consume them.

**Anchor-to-template.**
- `05-relatorio-diario.md` § 2 *Estado Fisiológico* + § 4 *Hábitos (Status do Dia)*.
- `04-revisao-semanal.md` § 2 *KPIs da Semana* (8 indicators).
- `05-relatorio-diario.md` § 10 *Plano para Amanhã (Forward-Looking)* — anchors daily
  check on at-least-one invariant.

**Gap-analysis columns.**
- 3 ≤ count ≤ 5 (more = false rigor; fewer = single-point-of-failure).
- At least one **physiological** invariant (sleep, training, hydration).
- At least one **review/reflection** invariant (journal, weekly review, shutdown ritual).
- Frequency explicit (daily vs. weekly) per item.
- Each invariant has a measurable threshold ("≥ 7h sleep", not "good sleep").

**Spec-implication.**
- If the user picks > 5 invariants: the `04-revisao-semanal.md` § 2 KPI table needs to
  widen (currently 8 indicators; +1 per extra invariant) — frontmatter schema change.
- If an invariant is purely qualitative (e.g. "be present"): not enforceable → must
  be re-phrased with proxy metric.

**[ Paste your answer below this line ]**




---

# Q5 — Success signals

> **Question.** What specific numeric or behavioral signal tells you Q3 succeeded? Q4?
> Be concrete (not "be healthier" but "sleep ≥ 7h on 80% of nights").

**Why it matters.** Success signals are the inverse of kill conditions. They are what
fills the verification rows of `00-quartely-planning.md` § 5 *Teste de Fogo (5 Dimensões
x 4 Semanas)* — without them, the PASS/PARTIAL/FAIL algorithm has no inputs.

**Anchor-to-template.**
- `00-quartely-planning.md` § 5 (W1-W4 targets per dimension).
- `00-quartely-planning.md` § 9 *Verdict Computado (Algoritmo)* — media_teste_fogo input.
- `04-revisao-semanal.md` § 5 *Verdict Computado (Algoritmo da Revisão Semanal)* — same
  algorithm at weekly granularity.
- `01-sonho.md` § 1 *KPIs de Saída (definição de "done")* — the dream-level "done" markers.

**Gap-analysis columns.**
- Each quarter has ≥ 3 signals (covers Execution / Analysis / Well-being minimum).
- Signals cover different time windows (daily-counted, weekly-aggregated, quarterly-sum).
- Numeric signals ≥ 50% of the list (behavioral proxies harder to verify).
- Each signal traces to at least one template row (no orphan metrics).
- At least one signal is *lagging* (outcome-side, not just leading behavior).

**Spec-implication.**
- If a signal needs sub-weekly resolution: `04-revisao-semanal.md` template cannot carry
  it → extends `05-relatorio-diario.md` aggregation table instead.
- If the user names a goal-zero signal (e.g. "0 infrações"): the verdict algorithm in
  `00-quartely-planning.md` § 9 needs a `zero_tolerance_threshold` short-circuit.

**[ Paste your answer below this line ]**




---

# Q6 — Kill conditions

> **Question.** When do you abort a wave / dream / project? Give 3-5 conditions.

**Why it matters.** Kill conditions are the explicit output of Axis 3 *Gatilhos de
Refatoração*. They are the only signal that turns Q3/Q4 PARTIAL into a hard cut rather
than a slow bleed. Without them, *sunk-cost override* biases every subsequent quarter.

**Anchor-to-template.**
- `01-sonho.md` § 2 *Critério de Falsificação (Kill Switch — Axis 1)*.
- `01-sonho.md` § 4 *Gatilhos de Refatoração (Axis 3)* — 5 default triggers + 1 custom.
- `00-quartely-planning.md` § 8 *Critérios de Saída (End-of-Quarter)* + § 10 *Rota de
  Correção* (the correction path, not the kill path).
- `03-onda.md` § 4 *Verdict Computado (Algoritmo da Onda)* — `KILL_WAVE` branch.

**Gap-analysis columns.**
- 3 ≤ count ≤ 5 (more = no commitment; fewer = single failure kills everything).
- Each condition has a **threshold** (number or event), not just a category.
- Conditions span all three scopes: wave-level (15d), quarter-level (90d), sonho-level.
- At least one condition is internal (Q_HE / habit failure), not just external (market).
- Condition references at least one specific template section, not abstract terms.

**Spec-implication.**
- If an internal-conditions includes "I don't feel motivated": needs proxy
  (Q_HE < 0.45 sustained > 30d, per `01-sonho.md` § 4 default trigger) — subjective
  triggers are unenforceable.
- If the user picks a unique-gate condition (any one of N → kill): the verdict algorithm
  becomes a *min()* over conditions, not a weighted sum — needs new branch in
  `00-quartely-planning.md` § 9.

**[ Paste your answer below this line ]**




---

# Q7 — Known unknowns

> **Question.** What are you SURE you don't know yet but must learn by 2026-12-31?
> (At least 3 items.)

**Why it matters.** Known unknowns drive the *falsifiable hypothesis* field and the
*leading indicator* choices. Naming them converts "I should look into it" into a
testable learning target with an owner (self) and a deadline.

**Anchor-to-template.**
- `01-sonho.md` § 1 *Hipótese* — hypothesis text frames the unknown.
- `01-sonho.md` § 3 *Indicadores Leading vs Lagging (Axis 2)* — each unknown should
  yield at least 1 leading indicator (otherwise it's just curiosity, not a bet).
- `00-quartely-planning.md` § 2.1 *Criterio de falsificacao* — the unknown becomes the
  falsification criterion once resolved.

**Gap-analysis columns.**
- ≥ 3 items (minimum viable rigor per template § 1 *Hipótese* guideline).
- Each item is a **specific fact/skill**, not "be better at X" — must be answerable
  yes/no after 6 months.
- Each item has a concrete signal of resolution (e.g. "can write a 50-line X without
  looking at docs"), not just "understand Y".
- Domains span at least 2 IKIGAi vectors (otherwise the half-year is mono-vector).
- At least 1 unknown crosses a vertical (Q2) — unknown stays anchored to action.

**Spec-implication.**
- If the unknown is "which AI framework to specialize in": ties to the *course* vector,
  triggers the C-vector extension called out in Q1 spec-implication.
- If unknowns duplicate Q2 verticals: collapse them — Q7 should add depth to verticals,
  not parallel-track.

**[ Paste your answer below this line ]**




---

# Appendix A — Question-to-template matrix

| Question | Primary template | Sections fed | Also touches |
|----------|------------------|--------------|--------------|
| **Q1** Horizon | `01-sonho.md` | § 1 *Hipótese*, § 8 *IKIGAi Alignment* | `_drafts/ikigai-as-dom-on-planning-engine.md` § 2.1, § 3 |
| **Q2** Verticals | `00-quartely-planning.md` | § 4 *Desdobramento em 3 Ondas*, § 6 *Top 3 Épicos* | `01-sonho.md` § 7 *Sub-sonhos*, `03-onda.md` § 1 *Tema* |
| **Q3** Quarterly bets | `00-quartely-planning.md` | § 2.1 *Hipótese Falsificável*, § 2.2 *Leading vs Lagging* | `01-sonho.md` § 2 *Kill Switch*, § 5 *Verdict Computado* |
| **Q4** Non-negotiables | `05-relatorio-diario.md` + `04-revisao-semanal.md` | Daily § 2/§ 4, Weekly § 2 *KPIs* | `00-quartely-planning.md` § 7.1 *Histerese Asymmetric* |
| **Q5** Success signals | `00-quartely-planning.md` | § 5 *Teste de Fogo*, § 9 *Verdict Computado* | `04-revisao-semanal.md` § 5, `01-sonho.md` § 1 *KPIs de Saída* |
| **Q6** Kill conditions | `01-sonho.md` | § 2 *Kill Switch*, § 4 *Gatilhos de Refatoração* | `00-quartely-planning.md` § 10 *Rota de Correção*, `03-onda.md` § 4 *KILL_WAVE* |
| **Q7** Known unknowns | `01-sonho.md` | § 1 *Hipótese*, § 3 *Leading vs Lagging* | `00-quartely-planning.md` § 2.1 *Criterio de falsificacao* |

---

# Appendix B — Open architectural decisions inherited from drafts

From `.omo/drafts/ikigai-as-dom-on-planning-engine.md` § 8 *Open decisions*:

- **D1.** Should `_plan.md` live in vault (Obsidian) or in code (`life-ops/ikigai/data/`)?
- **D2.** Are existing IKIGAi tests (250+) converted to `_plan.md` format in this PR,
  or follow-up?
- **D3.** How are daily snapshots aggregated — one file per day, or one file per cycle?
- **D4.** Does planning-with-files need to learn IKIGAi custom frontmatter
  (`entity_type=IKIGAiDream`, etc.) or do we re-purpose existing `type` values?

**Interview impact.** Answers to Q1-Q7 may surface new decisions (D5+) — track them in
the same `§ 8` location of the draft during extraction.

---

*Scaffold: Socratic Interview v1 · IKIGAi Sys-01 · 2026-07-02 · Cluster PLAN (Estratégico).*
