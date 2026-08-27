# IKIGAi Gap Analysis — Deep Scan Synthesis (2026-07-02)

> **Purpose:** Distill the 5-agent deep-scan of templates / drafts / evidence / docs /
> planning-with-files engine into a single map of (a) what's already present, (b) what's
> still missing for the closing-2026 dataset, (c) which decisions are still open.
>
> **Inputs:**
> - `.omo/run-continuation/wf_962fbcee-a33/journal.jsonl` (full structured inventory)
> - `.omo/drafts/ikigai-as-dom-on-planning-engine.md` (D1–D4 open decisions)
> - `.omo/ikigai/meta/architecture-overview.md` (3-subsystem topology)
> - `.omo/ikigai/mock-datasets/README.md` (Marina persona scaffold)
>
> **Constraint:** This file is read-only with respect to `vibe-ops/`, `strategics/`,
> `code-docs/`, and `life-ops/operational/` — append-only rule respected.
> All writes for closing-2026 stay inside `.omo/ikigai/closing-2026/`.

---

## 1. Executive Summary (TL;DR)

1. **Templates are internally consistent.** The 9 period templates v2 share a common
   schema (ikigai_cluster, ikigai_vector, 2-score tracking on aggregate types,
   verdict_score + verdict enum, parent_period FK chain). PASS/PARTIAL/FAIL is the
   universal verdict; CONTINUE_WAVE/CORRECT_TRAJECTORY/KILL_WAVE is the onda-specific
   variant; ACTIVE/VALIDATED/FALSIFIED/PIVOTED/ABANDONED is the sonho-specific variant.
2. **The 4 missing pieces for closing-2026** (the next 5+ manual logs you'll write)
   are: **(a) Marina's 1 sonho** (top-of-pyramid, 6–12mo horizon), **(b) her
   Q3/Q4 trimestral**, **(c) her weekly reviews with policy_recommendation trail**,
   **(d) her daily reports with state-machine actions**. The infra (templates + mock
   personas) is ready; the actual data is yours.
3. **The planning-with-files engine (v3.1.3)** can host IKIGAi DOM as-is — no engine
   changes needed. D1 (location) and D3 (snapshot granularity) are still your call.
4. **The 2518 PAV tests + 9 TUI screens** are NOT a dependency for the manual sprint.
   They're operational-level scaffolding that emerges only after 5+ logs prove which
   workflow matters. (See ADR-007 for the data-first guardrails.)
5. **One architectural drift was detected:** `life-ops/operational/docs/architecture/09-INTERFACE-TUI.md`
   is empty. Not blocking, but worth flagging if you ever circle back to PAV docs.

---

## 2. Template Inventory — Consistency Matrix

All 9 templates verified by deep-scan. Cross-checks:

| # | Template | Period | Verdict enum | His­teresis | IKIGAi 4-vec | Teste de Fogo | Lines |
|---|----------|--------|--------------|-------------|--------------|---------------|-------|
| 0 | `00-quartely-planning.md` | quarterly (T1) | PASS / PARTIAL / FAIL | ✓ (full) | parcial | ✓ (5×4×4) | 229 |
| 1 | `01-sonho.md` | sonho (6–12mo) | ACTIVE / VALIDATED / FALSIFIED / PIVOTED / ABANDONED | — | ✓ full table | lite | 198 |
| 2 | `02-avaliacao-trimestral.md` | trimestral | PASS / PARTIAL / FAIL | — | ✓ full table | lite | 194 |
| 3 | `03-onda.md` | onda (15d) | CONTINUE_WAVE / CORRECT_TRAJECTORY / KILL_WAVE | — | ✓ full table | — | 171 |
| 4 | `04-revisao-semanal.md` | weekly | PASS / PARTIAL / FAIL | ✓ | ✓ per-epic | — | 183 |
| 5 | `05-relatorio-diario.md` | daily | PASS / PARTIAL / FAIL | ✓ | ✓ per-pomodoro | — | 191 |
| 6 | `06-quartely-review.md` | quarterly (T2) | PASS / PARTIAL / FAIL | ✓ (full) | ✓ full table | ✓ (5×4×3) | 180 |
| 7 | `07-sprint-kickoff.md` | onda (T3) | (no top-level) | ✓ | parcial | — | 182 |
| 8 | `08-sprint-retrospective.md` | onda (T4) | PASS / PARTIAL / FAIL | ✓ | — | — | 188 |

### Verdict formula consistency

- **PASS** = `media_agregada ≥ 0.70 AND leading_cumprido ≥ 0.80` (or per-sprint `completion ≥ 0.80 AND Q_HE ≥ 0.65`)
- **PARTIAL** = `0.50 ≤ x < 0.70` (or `0.50 ≤ completion < 0.80 OR Q_HE ≥ 0.45`)
- **FAIL** = `x < 0.50`
- **Histerese asymétrica:** `3+ dias MAINTAIN com Q_HE ≥ 0.85 → PUSH`; `2+ dias MAINTAIN com Q_HE < 0.65 → REDUCE`; `Q_HE < 0.30 OR infractions ≥ 3 → RECOVER (emergency)`

→ **Consistent across all templates that include verdict.** No drift detected.

### YAML frontmatter consistency

- All 9 share: `type`, `entity_type`, `period`, `date_start`, `date_end`, `id`,
  `template_version`, `ikigai_cluster`, `sonho_id`, `ikigai_vector`, `verdict`,
  `verdict_score`, `parent_period`, `status`, `tags`, `vault_path`, `vault_hash`.
- Diff: `00/06/07/08` carry `template_role` (the v2.0 discriminator).
- Diff: `01–08` carry `xp_gained` + `mastery_delta` (delta tracking).
- Diff: only `00` and `06` carry both `ikigai_score_inicio` + `ikigai_score_fim`
  (quarterly aggregate types).

→ **Schema is mature.** No migration needed before the first manual fill.

---

## 3. Field-Coverage Analysis — What's Needed for `closing-2026/`

The placeholder tree at `.omo/ikigai/closing-2026/` has 14 files staged but **none
filled**. The deep-scan tells us exactly which fields each needs.

### 3.1 What YOU need to write by hand (5+ log threshold)

| Period | Counts needed for closing-2026 | Sample file pattern | Status |
|--------|-------------------------------|---------------------|--------|
| **Sonho (6–12mo)** | 1 file | `01-q3-2026/00-sonho-q3.md` (or root `00-sonho-2026.md`) | ⬜ empty |
| **Trimestral (Q3, Q4)** | 2 files | `01-q3-2026/01-trimestral-q3.md`, `02-q4-2026/01-trimestral-q4.md` | ⬜ empty |
| **Onda (3 per Q × 2 Q)** | 6 files | `01-q3-2026/02-onda-q3-{1,2,3}.md` etc. | ⬜ empty |
| **Revisão Semanal (13/Q × 2)** | 26 files | `01-q3-2026/03-semanal/...md` | ⬜ empty |
| **Relatório Diário (65/Q × 2)** | 130 files | `01-q3-2026/04-diario/YYYY-MM-DD.md` | ⬜ empty |
| **Sprint Kickoff (4–6)** | 4–6 files | `01-q3-2026/05-kickoff/...md` (optional, .07 template) | ⬜ empty |
| **Sprint Retrospective (4–6)** | 4–6 files | `01-q3-2026/06-retro/...md` (optional, .08 template) | ⬜ empty |
| **Quarterly Review (Q3 + Q4)** | 2 files | `01-q3-2026/07-review-q3.md`, `02-q4-2026/07-review-q4.md` | ⬜ empty |

**Total empty target:** ~170 files for closing-2026.

**Reality check:** you won't write 170. Pick ONE of these narrowing strategies:

- **Strategy A (Recommended for week 1):** start with **1 sonho + 1 trimestral + 1 weekly + 5 daily**. = 8 files. Get the rhythm first.
- **Strategy B (Aggressive):** block-fill **1 onda (15 days)** end-to-end. = 1 onda + 3 weekly + 15 daily = 19 files. Heaviest investment, most informative.
- **Strategy C (Minimal):** **5 daily only**. = 5 files. Proves the daily rhythm is viable; nothing about the upper pyramid.

The data-first rule says: **5 daily minimum** before any code emerges from it. Strategy C is the minimum viable; A and B are richer.

### 3.2 What needs to be scaffolded (helper docs, optional)

These are NOT planning artifacts — they're templates and guides to help you fill
the above without losing context. The deep-scan found these gaps:

| Gap | What it is | Why it matters | Where it should go |
|-----|-----------|----------------|--------------------|
| **G1** Persona scaffold beyond Marina | 2–3 more mock personas (Carlos, Roberta) so you can stress-test frontmatter | Demonstrates template generality; gives you comparison points | `.omo/ikigai/mock-datasets/` (already has Marina) |
| **G2** Manual quickstart | 1-page "how to fill a daily report" — 5–8 bullet steps | First-run friction-killer | `.omo/ikigai/meta/manual-quickstart.md` |
| **G3** Field-coverage cheatsheet | 1-page table of "required vs optional" fields per template | Avoids frontmatter validation failures | `.omo/ikigai/meta/field-coverage-cheatsheet.md` |
| **G4** KPI helper spreadsheet (markdown) | Pre-computed 5×3×3 dimension table for weekly/daily | Removes arithmetic overhead during fills | `.omo/ikigai/meta/kpi-helper.md` |
| **G5** Policy decision log | Running tally of policy_recommendation shifts across weeks | Makes hysteresis visible | `.omo/ikigai/closing-2026/01-q3-2026/99-policy-trail-q3.md` |
| **G6** "Lessons from week 1" template | After 1 week of fills, capture what blocked/confused you | Iterates the templates based on real use | `.omo/ikigai/meta/retrospective-week-1.md` |

**Priority order:** G2 → G3 → G5 → G6. Skip G1 until you have 5+ real logs (otherwise
personas drift from reality). Skip G4 — compute by hand once, you'll internalize it.

### 3.3 What NOT to scaffold (over-engineering traps)

- ❌ Pydantic models for the frontmatter — `vibe-ops/specs/schema-frontmatter-contract-v2.md`
  already exists (348 lines, exhaustive). Don't re-write.
- ❌ New TUI screens — ADR-007 says no new code until 5+ logs prove the workflow.
- ❌ Sync to vibe-ops DB — not in scope per your "isolate environment" directive.
- ❌ Bidirectional vault sync — already shipped (plan `vault-bidirectional-sync` CLOSED).

---

## 4. Decisions Still Open (carried from `ikigai-as-dom-on-planning-engine.md`)

D1–D4 from the draft, **plus** new ones surfaced by the deep-scan:

| # | Decision | Options | Default if no input | Affects |
|---|----------|---------|----------------------|---------|
| **D1** | Where do `_plan.md` files live? | (a) vault (Obsidian) / (b) code (`life-ops/ikigai/data/`) | (b) — code, append-only, git-tracked | All entities |
| **D2** | Migrate existing 250+ IKIGAi tests to DOM? | (a) this PR / (b) follow-up | (b) — defer until Phase E | IKIGAi tests |
| **D3** | Daily snapshot granularity? | (a) 1 file/day / (b) 1 file/cycle | (a) — daily is what your rhythm will produce | 130 daily files |
| **D4** | Custom frontmatter (entity_type=IKIGAiDream)? | (a) extend planning-with-files / (b) repurpose existing `type` | (b) — repurpose, no engine changes needed | planning-with-files |
| **D5** *(new)* | Use Marina persona as the default exemplar? | (a) yes, default / (b) replace with real first name | (a) — Marina persona is illustrative; real name can be substituted | mock-datasets |
| **D6** *(new)* | Schema for `xp_gained` / `mastery_delta`? | (a) integer / (b) float / (c) enum (LOW/MED/HIGH/EPIC) | (a) integer, 0–100 | all delta-tracking templates |
| **D7** *(new)* | How to link `04-revisao-semanal.md` to Taskwarrior? | (a) UDA tag / (b) external `roadmap_sync` table | (a) UDA tag — already pattern from `vault-bidirectional-sync` | weekly template §8 |
| **D8** *(new)* | Strict mode for ikigai_score_inicio? | (a) `> 0` validation / (b) `0.0–1.0` validation | (b) — both inicio and fim are 0.0–1.0 floats | 00 + 06 templates |

→ **D1, D3, D6, D8** are blocking the first manual fill. They have sensible defaults
but worth a one-line confirmation. **D2, D4, D5, D7** can wait until Phase E.

---

## 5. Data-First Checklist — What Must Be True Before Code Emerges

(From ADR-007 + meta/agents.md, restated for the closing-2026 context.)

### 5.1 Before writing ANY code (PAV, sync, CLI):

- [ ] **≥ 5 daily reports** filled manually (`04-diario/YYYY-MM-DD.md`)
- [ ] **≥ 3 weekly reviews** filled manually (`03-semanal/...md`)
- [ ] **≥ 1 onda** end-to-end (1 kickoff + 3 weekly + 15 daily + 1 retro)
- [ ] **≥ 1 sonho + 1 trimestral** with 4-vector IKIGAi scoring
- [ ] All 7 above populated with **real data** (not boilerplate)
- [ ] At least **1 KAIZEN item** captured per onda retro
- [ ] At least **1 policy_recommendation shift** observed (hysteresis in action)

### 5.2 Before adding any new entity type:

- [ ] The entity appears in **5+ manual logs** as a real concept the user tracks
- [ ] The entity has **frontmatter candidates** (you can name 3+ fields you'd want)
- [ ] The entity has **at least 1 manual workflow** that uses it

### 5.3 Before adding any new CLI command:

- [ ] The workflow has been done **3+ times manually** with a recognizable pattern
- [ ] You can describe the command in **1 sentence** without rereading the code

### 5.4 Roll-back criteria (ADR-007):

- If after 6 months (i.e., 2027-01) there are **< 10 fully-filled templates** manually,
  reconsider the data-first methodology. Switch back to design-first if logs prove the
  templates are over-engineered.

---

## 6. Risk Register

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | **Daily fill fatigue** — you skip daily after 3 days, then template becomes shelf-ware | HIGH | Strategy C (5 dailies minimum) — lower the bar. KAIZEN the template after week 1 if friction appears. |
| R2 | **Frontmatter validation drift** — ad-hoc fields diverge from schema-frontmatter-contract-v2.md | MEDIUM | Run a `pre-commit` check after 5 fills: extract YAML, diff against contract schema. |
| R3 | **Scoring drift** — your ikigai_score_inicio/fim drift toward inflation | MEDIUM | Calibrate once a month: re-score week-1 and compare. If delta > 0.15, recalibrate. |
| R4 | **Template overgrowth** — you add sections to templates to fit one-off use | HIGH | Don't modify templates mid-cohort. Capture KAIZEN items in retro; apply at cohort boundary. |
| R5 | **Over-reading, under-writing** — you read all 170 docs but write 0 | HIGH | Timebox reading to 1 hour; switch to filling after that. The reading informs, doesn't replace. |
| R6 | **PAV cut temptation** — you start refactoring PAV because the dashboard feels wrong | HIGH | Per ADR-007: PAUSE. Document the pain in `.omo/ikigai/meta/retrospective-week-1.md`. PAV cut is Phase E. |
| R7 | **Draft re-reads** — `.omo/drafts/ikigai-as-dom-on-planning-engine.md` is 347 lines and calls for major refactor | MEDIUM | That's the *next* plan after closing-2026, not this one. Don't touch. |

---

## 7. Recommended Sequence — Next 5–10 Parallel Writes

If you say "ok go ahead" / "go ahead" / "mais paralelizando," dispatch 8–10
general-purpose subagents in a single message, each on a non-overlapping file.
Each agent must READ existing files first to ground output.

| # | Agent | File | Goal |
|---|-------|------|------|
| A1 | Manual quickstart | `.omo/ikigai/meta/manual-quickstart.md` | G2 — 1-page, 5–8 bullet "how to fill a daily" |
| A2 | Field-coverage cheatsheet | `.omo/ikigai/meta/field-coverage-cheatsheet.md` | G3 — required vs optional per template |
| A3 | Policy trail scaffold (Q3) | `.omo/ikigai/closing-2026/01-q3-2026/99-policy-trail-q3.md` | G5 — table to log every policy_recommendation |
| A4 | Policy trail scaffold (Q4) | `.omo/ikigai/closing-2026/02-q4-2026/99-policy-trail-q4.md` | G5 (same for Q4) |
| A5 | KPI helper | `.omo/ikigai/meta/kpi-helper.md` | G4 — 5×3×3 table for fast fill |
| A6 | Lessons-from-week-1 template | `.omo/ikigai/meta/retrospective-week-1.md` | G6 — captures friction after first 5 dailies |
| A7 | Marina sonho (mock) | `.omo/ikigai/mock-datasets/00-sonho_marina.md` | extra mock data — validates 01-sonho.md template |
| A8 | Marina Q3 trimestral (mock) | `.omo/ikigai/mock-datasets/01-trimestral_q3_marina.md` | extra mock — validates 02-avaliacao-trimestral.md |
| A9 | Marina onda (mock) | `.omo/ikigai/mock-datasets/02-onda_q3w1_marina.md` | extra mock — validates 03-onda.md |
| A10 | IKIGAi vectors primer | `.omo/ikigai/meta/ikigai-vectors-primer.md` | extract 5-vector model from `vibe-ops/vectors/*.md` + `ikigai_4_vectors.md` into 1p primer |

**All A1–A10 are non-overlapping files. Each agent gets explicit absolute Windows paths.**

---

## 8. Cross-References to All Artifacts

### 8.1 Already written (this session)

- `.omo/ikigai/meta/agents.md` (185 lines)
- `.omo/ikigai/meta/socratic-interview.md` (312 lines)
- `.omo/ikigai/meta/architecture-overview.md` (363 lines)
- `.omo/ikigai/meta/tui-screen-survey.md` (151 lines)
- `.omo/ikigai/mock-datasets/README.md` + 5 example files (912 lines total)
- `.omo/ikigai/closing-2026/01-q3-2026/` (7 placeholder files)
- `.omo/ikigai/closing-2026/02-q4-2026/` (7 placeholder files)
- `.omo/ikigai/closing-2026/99-archive/README.md`
- `code-docs/00-INDEX.md` + `code-docs/00-INDEX-specs.md` (508 lines total)
- `code-docs/adr/ADR-007-data-first-methodology.md` (86 lines)

### 8.2 Memory (cross-session)

- `~/.claude/projects/.../memory/data-first-methodology.md`
- `~/.claude/projects/.../memory/parallel-execution-trigger.md`
- `~/.claude/projects/.../memory/MEMORY.md`

### 8.3 Deep-scan sources

- `C:\Users\mathe\AppData\Local\Temp\claude\...\tasks\w3wsb1hsk.output` (114KB, full)
- `C:\Users\mathe\.claude\projects\...\subagents\workflows\wf_962fbcee-a33\journal.jsonl` (per-agent logs)

### 8.4 External references (read-only)

- `vibe-ops/planning/_templates_periodos_v2/` — 9 templates + RELEASE-NOTES
- `vibe-ops/architecture/ADR-006-period-reports-schema.md` — schema contract
- `vibe-ops/specs/schema-frontmatter-contract-v2.md` (348 lines) — YAML contract
- `vibe-ops/vectors/vector-{passion,skill,market,revenue}.md` — 4 IKIGAi vectors
- `strategics/planning-with-files/v3.1.3` — Central Engine (158 files)
- `.omo/drafts/ikigai-as-dom-on-planning-engine.md` — D1–D4 open decisions

---

## 9. Confidence Calibration

| Claim | Confidence | Flip-condition |
|-------|-----------|----------------|
| Templates are internally consistent | HIGH (95%) | New template added that breaks the verdict enum |
| Strategy C (5 dailies) is the right minimum viable | MEDIUM (70%) | User prefers Strategy A or B from §3.1 |
| G2/G3/G5/G6 are the right priority order | MEDIUM (65%) | User surfaces another friction during fills |
| D1 default = code location | HIGH (85%) | User has vault preference |
| 6-month roll-back criteria is sufficient | LOW (50%) | Methodology decays faster than expected |
| PAV cut is correctly deferred to Phase E | HIGH (90%) | User reports daily fills reveal a missing screen |

---

## 10. Closing Note

The deep-scan closed the **"find every gap"** arc. The remaining work is **writing**,
not **scanning** — and it is YOUR work, not the agent's. The agent can scaffold
helper docs (G2–G6), but the 8–170 daily/weekly/onda/trimestral files are yours
alone. That's the data-first contract.

> *"Code emerges from manual execution patterns, not vice versa."*
> — `.omo/ikigai/meta/agents.md`, rule 1.

---

*Gap analysis compiled 2026-07-02 from 5-agent deep-scan (686K tokens, 818s, 145 tool uses).*
*Next inflection-point candidates: G2–G6 helper docs (8–10 parallel writes), then the first daily.*