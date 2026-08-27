# IKIGAi as Domain Object Model on planning-with-files Engine

> **Working draft** — architectural design proposal
> **Source request:** "use planning files engines as Domain Object Model for store our @strategics\  @life-ops/ikigai/src\  SYSTEMS DATA STRUCTURES AND THEIR MANY CONTRACTS"
> **Engine:** `strategics/planning-with-files/` (v3.1.3, 279 commits, 60+ agent adapters)

---

## 1. Why a planning-with-files DOM for IKIGAi?

The planning-with-files engine is **file-based persistent state for AI agents** with:
- 3 persistent files per task (`task_plan.md`, `findings.md`, `progress.md`)
- A **deterministic completion gate** (file-checkmark verification)
- 60+ agent adapters (Claude Code, Codex, Cursor, Kiro, OpenCode, Hermes)
- **Hash attestation** + **parallel plan isolation**
- **SKILL.md standard** for cross-tool interop

IKIGAi (the meta-brain) has 5-vector scoring, 8 state machines, markdown-vault SoT, SQLite mirror, and many contracts between subsystems. Using planning-with-files as a DOM for these would give us:
- **Crash-proof contracts**: state survives /clear, context loss
- **Version-controlled state**: every contract change is a git diff
- **Cross-agent operability**: same state consumed by Claude, Codex, etc.
- **Free completion verification**: gate replaces manual contract tests

## 2. Mapping IKIGAi → planning-with-files structure

### 2.1 Entity → Plan Tier mapping

| IKIGAi entity (in `src/ikigai/entities/`) | planning-with-files tier | Storage path | Frontmatter keys |
|----------------------------------------|--------------------------|--------------|------------------|
| `Dream` (entities/plan/dream.py) | task_plan.md (root) | `strategics/dreams/{slug}.md` | `ueid`, `entity_type=dream`, `title`, `score`, `verdict` |
| `Goal` | goal.md | `strategics/dreams/{slug}/goal-{n}.md` | `ueid`, `parent_ueid`, `score`, `verdict` |
| `Objective` | objective.md | nested | adds `meso_verdict` |
| `Project` | project.md | nested | adds `success_criteria` |
| `Task` | task.md | nested | adds `due`, `assignee` |
| `Deliverable` | deliverable.md | nested | adds `output_path` |
| `Routine` (entities/ops/routine.py) | routine.md | `strategics/routines/{slug}.md` | `ueid`, `cadence`, `type` |
| `TimeBlock` (entities/ops/time_block.py) | timeblock.md | nested | `start_at`, `end_at`, `routine_ueid` |
| `Ritual` | ritual.md | nested | `steps[]` |
| `Pomodoro` | pomodoro.md | nested | `started_at`, `focus` |
| `IKIGAiVectorEntity` (entities/vector.py) | vector.md | `strategics/vectors/{name}.md` | `passion`, `skill`, `market`, `revenue`, `course` |
| `VectorScorePoint` | score.md | nested | `vector_ueid`, `value`, `timestamp` |
| `IKIGAiProfile` (entities/profile.py) | profile.md | `strategics/profiles/{snapshot_id}.md` | `vector_ueids[]`, `captured_at` |
| `SkillNode` (entities/skill.py) | skill.md | `strategics/skills/{slug}.md` | `ueid`, `level`, `parent` |
| `OpportunitySignal` (entities/opportunity.py) | opportunity.md | `strategics/opportunities/{id}.md` | `ueid`, `vector_ueid`, `deadline` |
| `RegimeOverride` (override/) | override.md | `strategics/overrides/{id}.md` | `entity_ueid`, `from_regime`, `to_regime`, `recommendation_score` |

### 2.2 Per-tier atomic file structure

```
strategics/
├── dreams/
│   └── [slug]/
│       ├── _plan.md              # task_plan.md equivalent
│       ├── _findings.md          # findings.md equivalent
│       ├── _progress.md          # progress.md equivalent
│       ├── 01-goal.md
│       ├── 02-objective.md
│       ├── 03-project.md
│       └── tasks/
│           ├── 01-task.md
│           └── 02-task.md
├── routines/
│   └── [slug]/
│       ├── _plan.md
│       ├── _findings.md
│       ├── _progress.md
│       └── timeblocks.md
├── vectors/
│   ├── passion.md
│   ├── skill.md
│   ├── market.md
│   ├── revenue.md
│   └── course.md
├── profiles/
│   └── 2026-Q1-snapshot.md
├── overrides/
│   └── 2026-06-30-override.md
├── _cross-cutting/
│   ├── aggregates/
│   │   ├── 5x3x3.md
│   │   ├── regime.md
│   │   └── test-de-fogo.md
│   └── logs/
│       └── 2026-06-30.md
└── 00-ÍNDICE-PROGRESSIVO.md
```

## 3. Frontmatter Contract (per file)

```yaml
---
# IKIGAi Entity Contract (planning-with-files extension)
type: period_report
period: [sonho|trimestral|onda|semanal|diario]
entity_type: [dream|goal|objective|project|task|deliverable|routine|timeblock|ritual|pomodoro|vector|profile|skill|opportunity|override]

# Identity
ueid: [str]
slug: [str]
title: [str]
created: YYYY-MM-DD
updated: YYYY-MM-DD
parent_ueid: [str|None]   # for nested entities
sonho_id: [str|None]      # always back-reference the root Dream

# 5-Vector contract
passion: [float 0.0-1.0]
skill: [float 0.0-1.0]
market: [float 0.0-1.0]
revenue: [float 0.0-1.0]
course: [float 0.0-1.0]
ikigai_score: [float 0.0-1.0]

# Verdict contract
verdict: [ACTIVE|VALIDATED|FALSIFIED|PIVOTED|ABANDONED|PASS|PARTIAL|FAIL|CONTINUE_WAVE|CORRECT_TRAJECTORY|KILL_WAVE]
verdict_score: [float 0.0-1.0]

# Score components
ucb_score: [float]
rice_score: [float]
qhe_score: [float]
metacritic_score: [float]
opportunity_score: [float]

# Plan contract
sonho_ueid: [str]
goal_ueid: [str|None]
objective_ueid: [str|None]
project_ueid: [str|None]
task_ueid: [str|None]

# Override / regime
from_regime: [PUSH|MAINTAIN|REDUCE|RECOVER]
to_regime: [PUSH|MAINTAIN|REDUCE|RECOVER]
recommendation_score: [float 0.0-1.0]

# Sync metadata
vault_hash: [str]  # sha256:16
last_synced_at: ISO
sync_status: [draft|active|closed]
tags: [str|list]

# Custom (per-entity)
[type_specific_data]: [varies]
---
```

## 4. The 4 Planning Files per Task (adapted for IKIGAi)

### 4.1 `_plan.md` (was task_plan.md)

Represents the planning structure for a Dream root or any planning unit:

```markdown
# Plan: {Entity Title}

## Phase: {Active Phase}
## Owner: {Entity UEID}
## Period: {start_at} → {end_at}

## Goals
- [ ] {goal_1}
- [ ] {goal_2}

## Objectives
- [ ] {objective_1} | target: {score}
- [ ] {objective_2}

## Tasks
- [ ] {task_1} | P: {priority} | T: {tier}
- [ ] {task_2}

## Regime
Current: {PUSH|MAINTAIN|REDUCE|RECOVER}
Histerese: {days_in_current_state}

## Test de Fogo (5 dimensions)
- Execution: {score}
- Analysis: {score}
- Planning: {score}
- Learning: {score}
- Wellbeing: {score}

## Acceptance Criteria
- [ ] {AC_1}
- [ ] {AC_2}
```

### 4.2 `_findings.md`

Documents discoveries, anomalies, IKIGAi scores, regime shifts:

```markdown
# Findings: {Entity Title}

## Verdict Trajectory
- {date}: PASS (score 0.78)
- {date}: PARTIAL (score 0.62)
- ...

## 5-Vector Trends
| Vector | W-1 | W-2 | W-3 | Trend |
|--------|-----|-----|-----|-------|
| Passion | 0.7 | 0.8 | 0.9 | ↑ |
| Skill | 0.5 | 0.6 | 0.7 | ↑ |
| Market | 0.3 | 0.3 | 0.4 | → |
| Revenue | 0.1 | 0.1 | 0.2 | ↑ |
| Course | 0.4 | 0.4 | 0.4 | → |

## Regime Shifts
- {date}: PUSH → MAINTAIN (his terese sustained 3 days, Q_HE 0.86)
- ...

## Anomalies
- {date}: 5x3x3 imbalance detected (Planning at 0.4, others > 0.7)

## Overrides Applied
- {date}: MAINTAIN → REDUCE override (recommendation_score 0.85)
```

### 4.3 `_progress.md`

Real-time cycle progress:

```markdown
# Progress: {Entity Title}

## Iteration: {n}
## Last Sync: {ISO}

## Plan → Act → Verify
- [x] {completed_step_1}
- [x] {completed_step_2}
- [ ] {current_step}
- [ ] {next_step}

## Daily Snapshots
- {date}: iteration {n} | {verdict} | {score} | {qhe}
```

### 4.4 `_logs/{date}.md`

Append-only audit trail (replaces raw log files):

```markdown
# Log: {date}

## IKIGAi Heartbeat
- iteration: {n}
- regime: {from} → {to}
- qhe_score: {score}
- 5x3x3: exec={s} anal={s} plan={s} learn={s} wb={s}

## Computations
- completion_rate: {ratio}
- opportunity_score: {score}
- meta_heuristic: {state}
- override_count: {n}

## Verifications
- [✓/✗] all 5 vectors present
- [✓/✗] parent_ueid set
- [✓/✗] verdict matches qhe (5x3x3 invariant)
- [✓/✗] sync_status == 'active'
```

## 5. Cross-references and Routes

| IKIGAi component (in `life-ops/ikigai/src/`) | DOM file | Notes |
|--------------------------------------------|----------|-------|
| `entities/base.py::PlanEntity` | `_plan.md` frontmatter | Polymorphic — every IKIGAi entity extends it |
| `entities/plan/dream.py` | `strategics/dreams/{slug}/_plan.md` | Root entity |
| `entities/vector.py::IKIGAiVectorEntity` | `strategics/vectors/{name}.md` | Single value per (entity, vector) |
| `entities/profile.py::IKIGAiProfile` | `strategics/profiles/{snapshot_id}.md` | 5-vector snapshot |
| `core/scoring/*` (5 algorithms) | `_findings.md` 5x3x3 section | Computed from frontmatter values |
| `core/heuristics/*` | `_logs/{date}.md` | Decision audit trail |
| `override/` | `strategics/overrides/{id}.md` | Per-override file |
| `state_machines/` | `_findings.md` regime shifts | 8 FSMs transition history |
| `propagation/markdown_db` | All `strategics/**/*.md` | Reads files via the same pattern |
| `persistence/sqlite_repo` | `_progress.md` summary | DB mirror of file state |
| `cli/` | `python -m ikigai` | Replaces need for runtime DB; just reads files |

## 6. Migration Strategy

### 6.1 Phase 1: Read-only DOM (week 1)
- Copy planning-with-files to `strategics/planning-with-files/` (DONE)
- Update `00-ÍNDICE-PROGRESSIVO.md` (DONE)
- Update all 8 strategics docs (DONE)
- Commit + session log (DONE)

### 6.2 Phase 2: Sample IKIGAi→DOM write (week 2)
- Pick one IKIGAi Dream (e.g., "Land AI role in Q3 2026")
- Write `_plan.md` matching the frontmatter contract above
- Write `_findings.md` with current 5-vector scores
- Write `_progress.md` with iteration history
- Commit to `strategics/dreams/{slug}/`

### 6.3 Phase 3: Routes from `life-ops/ikigai/src/` to DOM (week 3-4)
- Modify `propagation/markdown_db.py` to read DOM files first, then fall back to legacy paths
- New CLI: `ikigai export --to-dom` (dumps all entities to DOM format)
- New CLI: `ikigai import --from-dom <file>` (creates entities from DOM)
- New: `ikigai status` shows 5x3x3 from DOM frontmatters

### 6.4 Phase 4: Completion Gate as test runner (week 5)
- Replace manual contract tests with planning-with-files gate
- Each test plan in `tests/` becomes a `_plan.md` with checkbox verification
- gate: `bash tests/run-completion-gate.sh` reads each `_plan.md` in `tests/`, verifies all checkboxes

### 6.5 Phase 5: Bidirectional sync (week 6-8)
- `ikigai sync` reads DOM, updates `core/scoring/*`, writes back to DOM
- Auto-trigger on every 5x3x3 change
- Histerese detection drives override files

## 7. Update policy

Per the central engine policy (see `strategics/00-ÍNDICE-PROGRESSIVO.md` § 🔌 Central Engine):

```bash
cd strategics/planning-with-files
git pull   # monthly for new versions
```

After pull:
- Re-check if IKIGAi entity mapping in § 2.1 needs updates
- Run tests on new sample files
- Re-verify routes in `00-ÍNDICE-PROGRESSIVO.md`

## 8. Open decisions (awaiting user input)

- **D1**: Should `_plan.md` live in vault (Obsidian) or in code (`life-ops/ikigai/data/`)? 
- **D2**: Are existing IKIGAi tests (250+) converted to `_plan.md` format in this PR, or follow-up?
- **D3**: How are daily snapshots aggregated — one file per day, or one file per cycle?
- **D4**: Does planning-with-files need to learn IKIGAi custom frontmatter (entity_type=IKIGAiDream, etc.) or do we re-purpose existing type values?

## 9. Acceptance criteria (for v1)

- [ ] At least 3 IKIGAi sample entities (Dream, Goal, Routine) migrated to DOM format
- [ ] `_findings.md` populated with 5x3x3 + regime shift data
- [ ] `_progress.md` updates on each `ikigai run` cycle
- [ ] `_logs/{date}.md` heartbeat in append-only mode
- [ ] `python -m ikigai` can read from DOM files
- [ ] tests run via completion gate pass
- [ ] No regression in existing 250+ IKIGAi tests

---

*Draft captured 2026-06-30 — central engine integrated, DOM design proposed, awaiting user decisions on D1-D4.*