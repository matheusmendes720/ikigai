# IKIGAi Persona Vault — Hierarchical Layer Expansion

**Status:** DRAFT — pending user review (Task #6 of brainstorming checklist)
**Date:** 2026-08-25
**Owner:** Matheus Mendes
**Scope:** `life-ops/ikigai/data/matheus/` — add GOAL, HABIT, W3/W4 PROJECT, SEMANA, DIA, TASK, VECTOR, CONSTRAINT layers under the existing DREAM/OBJECTIVE/PROJECT/DELIVERABLE/PROFILE shapes.

---

## Source-of-Truth Precedence (load-bearing)

When sources disagree, the authoritative order is:

1. **Pydantic** (`packages/core/src/ikigai/entities/plan/*.py`) — what the code actually enforces
2. **SPEC.md** (`life-ops/ikigai/SPEC.md`) — design intent, may lag the code
3. **Existing drafts** (`data/matheus/**/*.md|.json`) — what humans wrote, lowest authority

Section 1 amendments that resolved conflicts (verification workflow `wf_a5a6ae8c-559` → task `wcx7y8d26`):

| # | Amendment | Resolution |
|---|-----------|------------|
| 1 | Heading rename (was ambiguous) | Section 1 title: "Frontmatter Schema" |
| 2 | `ueid` key lowercase | Matches Pydantic field name |
| 3 | `parent_ueid` optional | `null` for SONHO/PROFILE roots |
| 4 | Drop 120-char title hint | Pydantic `str` unbounded |
| 5 | Drop empty-string defaults | Use `null` where Pydantic type allows |
| 6 | Status tokens uppercase | Matches `StatusType` enum: `DRAFT`, `ACTIVE`, `PAUSED`, `ACHIEVED`, `ABANDONED`, `ARCHIVED` |
| 7 | Comment `vector_weights_snapshot` rationale | Equal 0.20 for SONHO; cascade per SPEC §8 for child entities |
| 8 | Annotate `horizon_days` allowed values | DREAM 1825-3650d, GOAL 365-1095d, OBJECTIVE 90-365d, PROJECT 30-180d, TASK 1-7d |
| 9 | Scope `success_metrics` semantics | GOAL-only (per `goal.py`); OBJECTIVE uses `key_results` |
| 10 | Document `review_frequency_days` SPEC gap | Field exists in `goal.py` but NOT in SPEC §3.2; treat as Pydantic-authoritative |
| 11 | `source_md_path` nullable | `Path \| None`; empty string invalid → use `null` |
| 12 | Document `tags` SPEC gap | Field exists on PlanEntity but not declared in SPEC §3.2; treat as Pydantic-authoritative |
| 13 | Precedence note (this section) | Pydantic > SPEC > drafts |
| 14 | Polymorphism deferral (now resolved) | `PlanEntity` IS polymorphic per Pydantic (`discriminator="entity_type"`); single-shape spec covers all 5 hierarchy levels |
| 15 | Fix `frozen` misnomer | `PlanEntity.model_config.frozen = False` per SPEC §3.2 D6 + Pydantic; CLAUDE.md "Pydantic strict" rule applies to **other** schemas in this repo (PAV, vibe-ops), NOT IKIGAi PlanEntity |

---

## Polymorphism confirmation (resolves amendment #14)

SPEC.md §3.2 D6 declares:

```python
class PlanEntity(BaseModel):
    model_config = ConfigDict(
        extra="allow",          # type-specific extras pass through
        discriminator="entity_type",  # polymorphic dispatch
        frozen=False,           # mutable; updates rewrite frontmatter
    )
```

Therefore:

- The YAML frontmatter shape is **identical** for DREAM, GOAL, OBJECTIVE, PROJECT, TASK, DELIVERABLE — all 20 PlanEntity base fields appear at top level in every file
- The discriminator is the `entity_type` field value (e.g. `entity_type: goal`)
- Type-specific fields (e.g. GoalEntity.success_metrics) appear as additional YAML keys BELOW the base block — Pydantic accepts them via `extra="allow"`, then type-checks them on the typed subclass
- No conditional schema per entity type. Single YAML template. (See Section 1.)

---

## Section 1: Frontmatter Schema

### Base fields (all 20 PlanEntity fields, all entity types)

```yaml
---
ueid: ikigai:<entity_type>:<slug>:<uuid_short_8hex>:<content_hash_short_8hex>
entity_type: dream | goal | objective | project | task | deliverable | habit | vector | profile
slug: <kebab-case-immutable>
parent_ueid: <ueid | null>           # null for SONHO/PROFILE roots
related_ueids: [<ueid>, ...]          # empty list if none
title: <string>                       # unbounded; no 120-char hint
description: <string | null>
status: DRAFT | ACTIVE | PAUSED | ACHIEVED | ABANDONED | ARCHIVED
created_at: <ISO-8601 datetime>
updated_at: <ISO-8601 datetime>
last_reviewed_at: <ISO-8601 datetime | null>
ikigai_vectors: [passion, skill, market, revenue, course]
vector_weights_snapshot: {passion: 0.20, skill: 0.20, market: 0.20, revenue: 0.20, course: 0.20}
phase_at_creation: fundacao | consolidacao | expansao | maturidade | null
regime_at_creation: push | maintain | reduce | recover | null
horizon_days: <int>                  # bounded per entity type — see §1.2
primary_score: <ScoreValue | null>
is_placeholder: false
placeholder_owner: <string | null>
custom: {}                           # escape hatch (see §1.3)
source_md_path: <Path | null>        # nullable; empty string invalid
tags: [<string>, ...]                # SPEC gap — Pydantic-authoritative
---
```

### 1.1 Entity-type discriminator

| Entity | `entity_type` value | `horizon_days` bound |
|--------|---------------------|----------------------|
| SONHO (5-10y) | `dream` | 1825-3650 |
| GOAL (1-3y) | `goal` | 365-1095 (Literal[365, 547, 730, 913, 1095] per `goal.py`) |
| TRIMESTRE (3-12mo) | `objective` | 90-365 |
| ONDA (1-6mo) | `project` | 30-180 |
| TASK (1-7d) | `task` | 1-7 |
| DELIVERABLE | `deliverable` | n/a (concrete) |
| HABIT (system) | `habit` | unbounded (sustained) |
| VECTOR | `vector` | n/a |
| PROFILE | `profile` | snapshot, single point |

### 1.2 Type-specific fields (below base, accepted via `extra="allow"`)

| Entity | Type-specific YAML keys |
|--------|--------------------------|
| GOAL | `success_metrics: list[str]`, `review_frequency_days: int = 90` |
| TRIMESTRE | `key_results: list[str]`, `progress_pct: float = 0.0` |
| ONDA | `tech_stack: list[str]` (forward-compat) |
| TASK | `priority: str`, `assignee: str \| null` |
| DELIVERABLE | `artifact_path: Path` |
| HABIT | `frequency: str`, `streak_days: int = 0` |
| VECTOR | `formula: str`, `substrate: list[str]` |
| PROFILE | `snapshot_date: date`, `linked_*_ueid` in `custom:` |

### 1.3 `custom:` block — escape hatch

Reserved for fields NOT in Pydantic base AND not yet promoted to type-specific. Used for:

- `_intent_vector: revenue` (PROFILE only — internal annotation)
- `_horizon_rationale: <text>` (per-entity rationale)
- `non_negotiables: list[str]` (per-entity constraints)
- `verticals: list[str]` (per-entity vertical categorization)
- `target_roles: list[str]`
- `pricing_lever: str`

Migration rule: if a `custom:` field appears in 3+ entities, promote to a type-specific field in Pydantic.

---

## Section 2: File Layout

### 2.1 Directory tree

```
data/matheus/
├── ikigai_state/
│   └── profile-{date}.md              # PROFILE — JSON converted to MD+YAML (flatten nested objects)
├── dreams/{slug}.md                    # SONHO
├── goals/{slug}.md                     # GOAL
├── objectives/{slug}.md                # TRIMESTRE
├── projects/{slug}.md                  # ONDA
├── deliverables/{slug}.md              # DELIVERABLE
├── tasks/{slug}.md                     # TASK
├── habits/{slug}.md                    # HABIT
├── weeks/{iso-week}.md                 # SEMANA (e.g. weeks/2026-W27.md)
├── days/{iso-date}.md                  # DIA (e.g. days/2026-07-06.md)
├── vectors/{vector-name}.md            # VECTOR (5 files: passion, skill, market, revenue, course)
└── constraints/{slug}.md               # CONSTRAINT/VALUE
```

Naming rule: `<slug>.md`, kebab-case, immutable post-creation. Hierarchy prefix (e.g. `q3-2026-`) is allowed but optional.

### 2.2 Trade-offs (resolved)

| Option | Outcome | Rationale |
|--------|---------|-----------|
| **A: Per-type dirs** (selected) | Each entity type has its own dir | Matches existing `dreams/`, `objectives/`, `projects/`, `deliverables/` structure; trivial `find` by type |
| B: Flat with type prefixes | `dreams__vaga-remota-2026.md` | One dir, but breaks `find dreams/` grep |
| C: Hybrid | Unclear split | Rejected |
| D: UEID-keyed paths | `ikigai/dream/vaga-remota-2026/` | Adds depth; redundant with filename |

### 2.3 PROFILE migration (JSON → MD+YAML)

`ikigai_state/profile-2026-07-03.json` (current, 36 lines) → `ikigai_state/profile-2026-07-03.md`. Flatten:

```yaml
# OLD (JSON nested):
"ikigai_vectors": {
  "passion": {"value": 0.50, "unit": "ratio", "evidence": "..."}
}

# NEW (MD+YAML flat scalar):
ikigai_vectors: [passion, skill, market, revenue, course]   # from base
vector_scores_snapshot:                                     # NEW key, type-specific
  passion: 0.50
  skill: 0.55
  market: 0.30
  revenue: 0.00
  course: 0.40
```

Drop nested `{value, unit, evidence}` — `evidence` migrates to `custom:_vector_evidence: {passion: "...", ...}` (deferred per data-first).

---

## Section 3: UEID Generation

### 3.1 Format

```
ikigai:<entity_type>:<slug>:<uuid_short>:<content_hash_short>
```

- `namespace`: always `ikigai` for this vault
- `entity_type`: 1-2 from the discriminator list
- `slug`: kebab-case, immutable
- `uuid_short`: 8 hex chars from `uuid.uuid4().hex[:8]`, set at file creation, immutable
- `content_hash_short`: 8 hex chars from SHA-256 of canonical frontmatter (with UEID placeholder stripped), updated on every commit

### 3.2 Generation protocol

At file creation:

1. Compute `uuid_short = uuid.uuid4().hex[:8]`
2. Compute initial `content_hash_short = sha256(canonical_frontmatter_without_ueid)[:8]`
3. Combine: `ueid = f"ikigai:{entity_type}:{slug}:{uuid_short}:{content_hash_short}"`

At every subsequent commit:

1. Recompute `content_hash_short` from updated frontmatter
2. If new hash differs from UEID's hash segment → reject the commit (UEID drift)
3. To intentionally update content, regenerate UEID (new uuid_short) and bump `updated_at`

### 3.3 Legacy phase (`00000000:00000000` placeholders)

Existing 12 files use `00000000:00000000` as hash placeholders. Phase 0 (Section 4) migrates these to real UUIDs. After Phase 0 lands, all new files MUST have real hashes; pre-commit hook or writer discipline enforces this.

---

## Section 4: Phasing / Sequencing

### Phase 0: Migrate existing 12 files (no new entities)

In-place edits to all 12 existing files. Same content, strict shape. Detailed in Section 7.

### Phase 1: Add 2 GOAL entities (first batch-of-2)

Draft 2 GOALs for `vaga-remota-2026` SONHO:

- `goals/land-first-role-12m.md` (horizon 365d, success metrics: contract signed, remote-first)
- `goals/senior-remote-consulting-3y.md` (horizon 1095d, success metrics: 3 retainer clients OR FTE at senior level)

Workflow per Section 5: inline draft → redline → commit.

### Phase 2: Add 5 HABIT entities (S1-S5 from SONHO narrative)

- `habits/s1-sleep-7h5.md`
- `habits/s2-workout-3x.md`
- `habits/s3-daily-journal.md`
- `habits/s4-taskwarrior-gtd.md`
- `habits/s5-weekly-review.md`

### Phase 3: Add 2nd DREAM (B-side)

`dreams/camila-stable-remote-work.md` — second SONHO once Phase 1 lands.

### Phase 4: Add W3/W4 PROJECTs

- `projects/w3-linkedin-twitter-social-engineering.md`
- `projects/w4-longform-video-content.md`

### Phase 5: SEMANA entities (deferred until first real week logged)

`weeks/2026-W{nn}.md` per ISO week. Trigger: first W27 entry written manually.

### Phase 6: DIA entities (deferred)

`days/2026-{MM}-{DD}.md` per day. Trigger: first daily journal entry written.

### Phase 7: TASK entities (deferred)

Decompose ONDAs into 1-7d tasks. Trigger: first W3 ONDA breaks down into work items.

### Phase 8: VECTOR templates (5 files)

`vectors/{passion,skill,market,revenue,course}.md` — canonical formula + substrate docs.

### Phase 9: CONSTRAINT/VALUE entities

`constraints/{non-negotiable-slug}.md` — extracted from SONHO custom block.

### Phase gating

- Phase 0: required before any other phase
- Phase 1: required before Phase 3, 4
- Phase 2: required before Phase 5 (habits feed weekly review)
- Phase 5: required before Phase 6 (SEMANA entries reference daily logs)
- Phase 6: required before Phase 7 (TASKs emerge from daily plan)

---

## Section 5: Review / Commit Workflow

### 5.1 Per-entity protocol

For every new or migrated entity:

1. **Inline draft** in chat — writer pastes full frontmatter + body in code fence. NO file write yet.
2. **User redline** — user marks fixes inline, may use AskUserQuestion for batch triage.
3. **Approved → write file** — writer writes to disk only after explicit user "go".
4. **Commit** — single commit per batch-of-2, no `--no-verify` after Phase 0 (pre-commit hook enforces real UEID).

### 5.2 Batch-of-2 cadence

- Never write more than 2 entities per commit.
- If 3rd entity is needed, defer to next batch.
- Rationale: keeps review surface ≤ 2 redlines per round; preserves auditability.

### 5.3 Commit message format

```
chore(ikigai-vault): add <entity_type>/<slug>

Body explains: parent UEID, horizon rationale, weight cascade, any migration notes.
```

No `Co-Authored-By` trailer (per global CLAUDE.md).

### 5.4 Pre-commit enforcement (Phase 0+)

Hook blocks commits where any `.md` file under `data/matheus/` has `00000000:00000000` in UEID. Skipped for first migration commit (Phase 0 batch).

### 5.5 Tests

- **No Pydantic validation tests** until 5+ SONHO logs (data-first methodology, ADR-007).
- Until then: visual inspection of frontmatter + manual UEID round-trip check via `python -c "from ikigai.entities.plan.goal import GoalEntity; ..."` ad-hoc.

---

## Section 6: Cross-References & Traversal

### 6.1 Parent chains

```
SONHO → GOAL → OBJECTIVE → PROJECT → TASK → DELIVERABLE
                     ↓
                  HABIT (sibling, parent_ueid = SONHO or OBJECTIVE)
```

`parent_ueid` points to immediate parent (single level). Full chain reconstructed by walking parent_ueid recursively.

### 6.2 Lateral references (`related_ueids`)

Sibling entities that share a thematic link but no parent-child relationship. Example:

- `related_ueids: [<goal-A-ueid>, <goal-B-ueid>]` on a SONHO pointing to both top-level goals.
- Used for cross-cutting concerns (e.g. BYD case analysis project + Salvador data pipeline project share SONHO 2).

### 6.3 PROFILE cross-refs

PROFILE custom block holds `linked_dream_ueid`, `linked_objective_ueid`, `linked_project_ueid` — pointing to the canonical triplet at snapshot time. Update on every SONHO creation or major regime shift.

### 6.4 Traversal tooling (deferred)

No traversal CLI until Phase 5+ (SEMANA entries). When built, command is:

```
ikigai-vault walk <ueid>              # parent chain + children
ikigai-vault related <ueid>           # lateral graph
ikigai-vault orphans                  # entities with broken parent_ueid
```

---

## Section 7: Migration of Existing 12 Files

### 7.1 Inventory

| # | File | Entity | Status today | Migration target |
|---|------|--------|--------------|------------------|
| 1 | `dreams/vaga-remota-2026.md` | SONHO | `status: seed` | `status: ACTIVE` (or `DRAFT` if user prefers) |
| 2 | `objectives/q3-2026-primeira-vaga.md` | TRIMESTRE | `status: planned` | `status: ACTIVE` |
| 3 | `projects/onda-q3-1-pipeline-bi-cold-outreach.md` | ONDA | (read pending) | strict shape |
| 4 | `projects/onda-2026-07-byd-deep-dive.md` | ONDA | (read pending) | strict shape |
| 5 | `projects/onda-2026-07-salvador-data-pipeline.md` | ONDA | (read pending) | strict shape |
| 6 | `deliverables/byd-market-research.md` | DELIVERABLE | (read pending) | strict shape |
| 7 | `deliverables/byd-econometric-vulnerability-analysis.md` | DELIVERABLE | (read pending) | strict shape |
| 8 | `deliverables/byd-cold-outreach-assets.md` | DELIVERABLE | (read pending) | strict shape |
| 9 | `deliverables/byd-process-tracker.md` | DELIVERABLE | (read pending) | strict shape |
| 10 | `deliverables/byd-d1-outputs/` | (DIR) | subdir of artifacts | n/a (kept as-is, referenced via DELIVERABLE.artifact_path) |
| 11 | `deliverables/byd-d2-outputs/` | (DIR) | subdir of artifacts | n/a (kept as-is) |
| 12 | `deliverables/byd-d3-outputs/` | (DIR) | subdir of artifacts | n/a (kept as-is) |
| 13 | `deliverables/byd-d4-outputs/` | (DIR) | subdir of artifacts | n/a (kept as-is) |
| 14 | `ikigai_state/profile-2026-07-03.json` | PROFILE | JSON shape | MD+YAML (Section 2.3) |

12 .md/.json files migrate; 4 output dirs stay as-is (referenced by artifact_path).

### 7.2 Per-file changes (uniform)

For each of the 12 files:

1. **UEID hash placeholder** `00000000:00000000` → real `uuid_short:content_hash_short` (compute per Section 3.2)
2. **Status enum** lowercase → uppercase (Section 1, amendment #6)
3. **Type-specific fields** moved out of `custom:` (where applicable — e.g. OBJECTIVE's `key_results` already at top level in q3-2026; verify each)
4. **`source_md_path`** if empty → `null`
5. **`tags`** field added if missing (Pydantic-authoritative, amendment #12)
6. **`vector_weights_snapshot`** comment added per amendment #7
7. **Narrative prose** preserved byte-for-byte (append-only rule applies to spec-only content; structural fields migrate)
8. **`updated_at`** bumped to migration timestamp
9. **`last_reviewed_at`** set to `updated_at` for migrated files

### 7.3 PROFILE migration details

`profile-2026-07-03.json` (JSON) → `ikigai_state/profile-2026-07-03.md` (MD+YAML):

- Flatten nested `ikigai_vectors` object → top-level `vector_scores_snapshot: {passion: 0.50, ...}` scalar
- Move `_intent_vector`, `_horizon_rationale`, `note` from `custom:` → either top-level or remain in `custom:` (decision: keep in `custom:` for PROFILE-specific annotations)
- Preserve `linked_dream_ueid`, `linked_objective_ueid`, `linked_project_ueid` in `custom:`
- Old `.json` file is **deleted** after migration verified (data-first methodology allows structural migration; old format is no longer canonical)

### 7.4 Migration ordering

Single batch-of-2 commits cannot accommodate 12 files. Use 6 batch-of-2 commits:

- Batch 1: SONHO + TRIMESTRE (highest priority — anchor the hierarchy)
- Batch 2: 2 ONDAs (pick the 2 most-linked ones)
- Batch 3: 1 ONDA + 1 DELIVERABLE
- Batch 4: 3 DELIVERABLES
- Batch 5: PROFILE (the format-conversion outlier)
- Batch 6: edge-case fixes if any

Each batch: inline diff preview → redline → commit.

### 7.5 Risk: PROFILE is the only JSON

The 5 other vault dirs are MD+YAML. PROFILE is JSON. Two questions:

1. Does any code READ the JSON? → check before deleting (Section 7.3)
2. Should future PROFILEs be JSON or MD+YAML? → MD+YAML (consistency)

---

## Open questions (deferred to writing-plans phase)

1. **Habit scoring integration**: HABIT entities need `streak_days` field — does Pydantic have a HabitEntity yet? (read `entities/plan/habit.py` in writing-plans)
2. **SEMANA / DIA scoping**: when do these become required vs deferred indefinitely?
3. **VECTOR template format**: 5 separate `.md` files or one `vectors/_index.md` with 5 sections?
4. **CONSTRAINT vs VALUE taxonomy**: separate entity types or unified?
5. **Migration audit log**: should `migrated_from_ueid` be added to track pre-migration state?

---

## Self-review checklist (post-write)

- [x] Placeholder scan: no TBD/TODO in body
- [x] Internal consistency: Section 1 fields match Section 2 layout; Section 7 migration matches Section 1 status enum
- [x] Scope check: single implementation plan scope (12-file migration + ~20 new entity writes, no cross-system changes)
- [x] Ambiguity check: status enum explicit; UEID format unambiguous; polymorphic dispatch documented
- [x] Precedence note front-and-center (Pydantic > SPEC > drafts)

---

*Written as Task #5 of brainstorming checklist. Awaiting Task #6 user review.*
