# IKIGAi Mock Datasets — Reference Examples

> **Purpose:** These five markdown files are fully-filled reference examples of the IKIGAi
> planning chain. They show what a real, internally-consistent planning hierarchy looks like
> when populated end-to-end with one persona (Marina Souza) across all five period levels.

> **Audience:** A human user who wants to copy, adapt, and ship their own dream planning set.
> Read each file end-to-end, then duplicate the structure with your own data.

---

## The Five Example Files (read in this order)

| # | File | Period | Horizon | Purpose |
|---|------|--------|---------|---------|
| 0 | `00-sonho_example.md` | Sonho (Dream) | 18 months | Strategic falsifiable hypothesis + IKIGAi 5-vector snapshot + Kill Switch |
| 1 | `01-trimestral_example.md` | Trimestral (Quarterly) | 90 days | Aggregates 3 months → 3 Ondas → 9 Semanais → 45 Diários |
| 2 | `02-onda_example.md` | Onda (Wave) | 15 business days | Tactical sprint; aggregates 3 weekly reviews |
| 3 | `03-revisao-semanal_example.md` | Revisão Semanal | 7 days | Sensor/adjuster of the cybernetic loop; aggregates 7 daily reports |
| 4 | `04-relatorio-diario_example.md` | Relatório Diário | 1 day | Atomic unit — pomodoros, habits, Q_HE, PolicyEngine decision |

---

## 5-Minute Walkthrough

1. **Start at the top of the pyramid** — open `00-sonho_example.md`. This is Marina's dream in
   one falsifiable sentence: *"Become a tech lead at a climate-tech startup within 3 years,
   while sustaining 8h sleep and 3x/week training for a half-marathon in 2027."* Note the
   `sonho_id: marina.climate-tech-lead.2027` — that's the foreign key every downstream
   report will reference.

2. **Drop down one level** — open `01-trimestral_example.md`. This is her **Q3-2026** plan.
   The trimestre is broken into **3 Ondas** of ~45 business days each. The bet for Q3-2026 is
   *"Build internal demo + first climate-tech interview."* Verdict mechanism (PASS/PARTIAL/FAIL)
   is shown populated with realistic numbers.

3. **Drop to the tactical layer** — open `02-onda_example.md`. This is **Onda 1** of Q3
   (`onda-01-climate-tech-internal-demo`), running 2026-07-06 → 2026-07-24. Three weekly
   reviews aggregate here. The verdict formula is computed in §4.

4. **Drop to the operational layer** — open `03-revisao-semanal_example.md`. This is
   **Week 1** of Onda 1 (`semana-01`), Mon 2026-07-06 → Sun 2026-07-12. Each daily report
   feeds this. PolicyEngine trail (PUSH/MAINTAIN/REDUCE/RECOVER) is recorded day-by-day.

5. **Hit the atomic layer** — open `04-relatorio-diario_example.md`. This is **Wednesday
   2026-07-08**, a PUSH day with 5/6 pomodoros completed, Q_HE 0.71, sleep 7.6h. Verdict:
   PASS. Recommendation: tomorrow also PUSH.

---

## Cross-Reference ID Chain (the spine)

```
Sentinel ─────────────────────────────────────────────────── Atomic

sonho:       marina.climate-tech-lead.2027          (horizon: 2026-07-06 → 2027-12-31)
   │
   ├── trimestre: quarterly-2026-Q3                 (2026-07-06 → 2026-09-30)
   │      │
   │      └── onda: onda-01-climate-tech-internal-demo
   │             (2026-07-06 → 2026-07-24, 15 business days)
   │             │
   │             ├── semana: semana-01              (2026-07-06 → 2026-07-12)
   │             │      │
   │             │      └── dia: 2026-07-08          (Wed, PUSH, 5/6 pomodoros)
   │             ├── semana: semana-02              (...)
   │             └── semana: semana-03              (...)
   │
   ├── trimestre: quarterly-2026-Q4                 (...)
   └── trimestre: quarterly-2027-Q1 ... Q3
```

**Every parent_period field in the YAML frontmatter of each file points up one level.**

Example: `02-onda_example.md` frontmatter has `parent_period: quarterly-2026-Q3`.
Example: `04-relatorio-diario_example.md` frontmatter has `parent_period: semana-01`.

---

## How the Verdicts Aggregate Upward

| Layer | Verdict | Aggregates from |
|-------|---------|-----------------|
| Diário (day) | PASS / PARTIAL / FAIL | Internal computation (completion, sono, Q_HE) |
| Semanal (week) | PASS / PARTIAL / FAIL | 7 daily verdicts + completion_rate + policy trail |
| Onda (15 days) | CONTINUE_WAVE / CORRECT_TRAJECTORY / KILL_WAVE | 3 weekly verdicts + completion_rate médio |
| Trimestral (90 days) | PASS / PARTIAL / FAIL | 3 onda verdicts + Teste de Fogo (5 dims × 4 weeks) |
| Sonho (6-18 months) | ACTIVE / VALIDATED / FALSIFIED / PIVOTED / ABANDONED | 3-Axis intersection (leading × lagging × refactor) |

---

## How IKIGAi Vectors Accumulate

Marina's vectors (current → 2027-12-31 target):

| Vetor | Current (2026-07-06) | Mid (Q3 end) | Target (2027-12-31) | Δ Total |
|-------|:---:|:---:|:---:|:---:|
| Passion | 0.60 | 0.70 | 0.80 | +0.20 |
| Skill | 0.70 | 0.78 | 0.85 | +0.15 |
| Market | 0.40 | 0.55 | 0.70 | +0.30 |
| Revenue | 0.60 | 0.70 | 0.80 | +0.20 |
| Course | 0.50 | 0.60 | 0.70 | +0.20 |

Each report shows the **current state vs the start-of-period state** so the delta is auditable.

---

## How to Use These Files

1. **Copy the folder.** Rename `.omo/ikigai/mock-datasets` → `.omo/ikigai/marina-souza`
   (or your own name).
2. **Replace the persona.** Change `Marina Souza` → your name everywhere. Change
   `marina.climate-tech-lead.2027` → a slug matching your dream.
3. **Rewrite `00-sonho_example.md` first.** Pick one falsifiable dream. Set horizons. Set
   kill switches. Don't move on until that is honest.
4. **Fill `01-trimestral_example.md`.** Pick the current quarter. Set the bet. Choose the
   regime (PUSH/MAINTAIN/REDUCE/RECOVER).
5. **Generate the Onda.** One of three inside the trimestre. Make it concrete: a single
   observable outcome.
6. **Run the week.** Aggregate the 7 days you actually lived. The verdict at the bottom
   tells you whether to PUSH or RECOVER next week.
7. **Capture the day.** Every evening, 10 minutes. The system reads what you wrote.

> **Mantra:** *"If it isn't in a report, it didn't happen. If it isn't aggregateable, it
> didn't teach you anything."*

---

## Constraints Honored in These Examples

- All dates are ISO (`YYYY-MM-DD`).
- All YAML keys match the canonical schema in `vibe-ops/planning/_templates_periodos_v2/`.
- All `parent_period` FKs point to a real upstream file.
- Verdict algorithms are **evaluated literally** (the result of the formula is shown, not
  just stated).
- Numbers roll up: weekly completion averages the daily completion rates; onda completion
  averages the three weekly completion rates; trimestral aggregates the three ondas.
- Regime transitions follow the hysteresis rule (≥3 days up, ≥2 days down).

---

*Reference set created 2026-07-02 · v1.0 · Cluster PLAN · IKIGAi Sys-01*
