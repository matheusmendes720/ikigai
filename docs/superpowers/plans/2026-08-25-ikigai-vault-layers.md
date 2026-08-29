> **[SUPERSEDED 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> This Phase 0 migration plan was authored 2026-08-25, before the AI-native
> pivot (2026-08-26). It assumes PAV is the canonical kernel and vault
> migration is pre-work for the IKIGAI meta-brain to plug into PAV's persistence.
> Post-pivot, PAV is desativado; canonical is deep-agent over forks-prontas widgets.
> The 5+ SONHO log gate (ADR-007 data-first methodology) still applies — defer
> any frontmatter-strict-migration until evidence accumulates.

> **⚠️ ADR-007 propagation note (2026-08-29):** The "5+ SONHO log gate" reference above reflects a **propagated misconception**. ADR-007's "5+ manual logs per workflow" rule is **observation depth**, NOT a release gate. The actual gate for algorithm/IKIGAI work is **system readiness** (backend + data + agent functional). Canonical clarification: `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`.

# IKIGAi Vault — Phase 0 Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate all 12 existing vault files to strict frontmatter schema — uppercase status enums, real UEID hashes, required fields, JSON profile converted to MD+YAML.

**Architecture:** Single-file in-place edits; batch-of-2 commits per spec Section 5.1. No new entities. No file creation beyond the JSON→MD conversion. Each file is migrated independently then committed in pairs.

**Tech Stack:** Plaintext editing only — SHA-256 (Python `hashlib`), UUID v4 generation, YAML rewrite. No Pydantic validation tests until 5+ SONHO logs (data-first, ADR-007).

## Global Constraints

- Data-first: no code in `src/ikigai/` until 5+ SONHO logs (currently 1/5)
- Append-only: never delete narrative prose; structural fields migrate only
- No `Co-Authored-By` trailer in commits
- Branch: `gitbutler/workspace` — no push until explicit user approval
- Pre-commit hook skips Phase 0 batch (has `00000000:00000000`)
- Batch-of-2 cadence: never commit more than 2 entities per commit
- UEID hash format: `sha256(canonical_frontmatter_without_ueid)[:8]` updated per commit

---

## Phase 0 Inventory (12 files)

| # | File | Entity | Changes |
|---|------|--------|---------|
| 1 | `dreams/vaga-remota-2026.md` | SONHO | `seed` → `ACTIVE`; add `last_reviewed_at`, `related_ueids: []`, `source_md_path: null`, `is_placeholder: false`, `placeholder_owner: null`, `custom: {}` |
| 2 | `objectives/q3-2026-primeira-vaga.md` | TRIMESTRE | `planned` → `ACTIVE`; add `last_reviewed_at`, `related_ueids: []`, `source_md_path: null`, `is_placeholder: false`, `placeholder_owner: null`, `custom: {}` |
| 3 | `projects/onda-q3-1-pipeline-bi-cold-outreach.md` | ONDA | `draft` → `DRAFT` (already uppercase); add `last_reviewed_at`, `related_ueids: []`, `source_md_path: null`, `is_placeholder: false`, `placeholder_owner: null`, `custom: {}` |
| 4 | `projects/onda-2026-07-byd-deep-dive.md` | ONDA | `draft` → `DRAFT`; same adds |
| 5 | `projects/onda-2026-07-salvador-data-pipeline.md` | ONDA | `draft` → `DRAFT`; same adds |
| 6 | `deliverables/byd-market-research.md` | DELIVERABLE | `draft` → `DRAFT`; add `last_reviewed_at`, `related_ueids: []`, `source_md_path: null`, `is_placeholder: false`, `placeholder_owner: null`, `custom: {}` |
| 7 | `deliverables/byd-econometric-vulnerability-analysis.md` | DELIVERABLE | `draft` → `DRAFT`; same adds |
| 8 | `deliverables/byd-cold-outreach-assets.md` | DELIVERABLE | `draft` → `DRAFT`; same adds |
| 9 | `deliverables/byd-process-tracker.md` | DELIVERABLE | `draft` → `DRAFT`; same adds |
| 10 | `ikigai_state/profile-2026-07-03.json` | PROFILE | Full format conversion to MD+YAML (see Task 5) |
| 11 | `README.md` | — | Minor path updates if needed (do not migrate — skip) |
| 12 | `ikigai_state/` dir | — | Already correct structure |

---

## UEID Migration Protocol (all files)

For each file, compute new UEID:

```python
import uuid, hashlib

def compute_ueid(entity_type: str, slug: str) -> str:
    uuid_short = uuid.uuid4().hex[:8]
    # Placeholder — real hash computed from canonical frontmatter at commit time
    content_hash = "COMPUTE_AT_COMMIT"
    return f"ikigai:{entity_type}:{slug}:{uuid_short}:{content_hash}"
```

**At commit time** for each batch, recompute `content_hash_short` from the actual canonical frontmatter (with UEID placeholder stripped before hashing).

For Phase 0, the implementer generates `uuid_short` per file and uses `00000000` as placeholder for `content_hash_short` in the file. The real `content_hash_short` is computed and updated just before `git add` using:

```python
import hashlib

def content_hash(frontmatter_text: str) -> str:
    # Strip the ueid line, normalize blank lines, hash
    lines = [l for l in frontmatter_text.splitlines() if not l.startswith('ueid:')]
    canonical = '\n'.join(sorted(lines)).encode()
    return hashlib.sha256(canonical).hexdigest()[:8]
```

---

## Required Frontmatter Per Entity Type

### DreamEntity (SONHO)

```yaml
---
ueid: ikigai:dream:<slug>:<uuid_short>:<content_hash_short>
entity_type: dream
slug: <slug>
parent_ueid: null
related_ueids: []
title: "<string>"
description: null
status: DRAFT | ACTIVE | PAUSED | ACHIEVED | ABANDONED | ARCHIVED
created_at: <ISO-8601>
updated_at: <ISO-8601>
last_reviewed_at: <ISO-8601 | null>
ikigai_vectors: [passion, skill, market, revenue, course]
vector_weights_snapshot: {passion: 0.20, skill: 0.20, market: 0.20, revenue: 0.20, course: 0.20}
phase_at_creation: fundacao | consolidacao | expansao | maturidade | null
regime_at_creation: push | maintain | reduce | recover | null
horizon_days: <int>  # 1825–3650 for Dream
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [<string>, ...]
---
```

### ObjectiveEntity (TRIMESTRE)

```yaml
---
ueid: ikigai:objective:<slug>:<uuid_short>:<content_hash_short>
entity_type: objective
slug: <slug>
parent_ueid: <parent_dream_ueid>
related_ueids: []
title: "<string>"
description: null
status: DRAFT | ACTIVE | PAUSED | ACHIEVED | ABANDONED | ARCHIVED
created_at: <ISO-8601>
updated_at: <ISO-8601>
last_reviewed_at: <ISO-8601 | null>
ikigai_vectors: [passion, skill, market, revenue, course]
vector_weights_snapshot: {passion: 0.10, skill: 0.40, market: 0.30, revenue: 0.15, course: 0.05}  # already set
phase_at_creation: fundacao | consolidacao | expansao | maturidade | null
regime_at_creation: push | maintain | reduce | recover | null
horizon_days: <int>  # 90–365 for Objective
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [<string>, ...]
# type-specific fields below base (via extra="allow"):
key_results:
  - <string>
progress_pct: 0.0
---
```

### ProjectEntity (ONDA)

```yaml
---
ueid: ikigai:project:<slug>:<uuid_short>:<content_hash_short>
entity_type: project
slug: <slug>
parent_ueid: <parent_objective_ueid>
related_ueids: []
title: "<string>"
description: null
status: DRAFT | ACTIVE | PAUSED | ACHIEVED | ABANDONED | ARCHIVED
created_at: <ISO-8601>
updated_at: <ISO-8601>
last_reviewed_at: <ISO-8601 | null>
ikigai_vectors: [market, skill]  # varies
vector_weights_snapshot: {...}  # already set
phase_at_creation: fundacao | consolidacao | expansao | maturidade | null
regime_at_creation: push | maintain | reduce | recover | null
horizon_days: <int>  # 30–180 for Project
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [<string>, ...]
# type-specific:
tech_stack: [python, polars, ...]
---
```

### DeliverableEntity

```yaml
---
ueid: ikigai:deliverable:<slug>:<uuid_short>:<content_hash_short>
entity_type: deliverable
slug: <slug>
parent_ueid: <parent_project_ueid>
related_ueids: []
title: "<string>"
description: null
status: DRAFT | ACTIVE | PAUSED | ACHIEVED | ABANDONED | ARCHIVED
created_at: <ISO-8601>
updated_at: <ISO-8601>
last_reviewed_at: <ISO-8601 | null>
ikigai_vectors: [market]  # varies
vector_weights_snapshot: {...}  # already set
phase_at_creation: fundacao | consolidacao | expansao | maturidade | null
regime_at_creation: push | maintain | reduce | recover | null
horizon_days: <int>  # 1–7 for Deliverable (or n/a as concrete)
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [<string>, ...]
# type-specific:
artifact_path: null
artifact_type: document | code | data
is_public: false
---
```

### ProfileEntity (JSON → MD+YAML)

```yaml
---
ueid: ikigai:profile:matheus-2026-07-03:<uuid_short>:<content_hash_short>
entity_type: profile
slug: matheus-2026-07-03
parent_ueid: null
related_ueids: []
title: "Matheus IKIGAi profile snapshot — 2026-07-03 (SONHO creation)"
description: null
status: ACTIVE  # was "active" → uppercase
created_at: 2026-07-03T00:00:00Z
updated_at: <ISO-8601>  # bump to migration time
last_reviewed_at: <ISO-8601>
ikigai_vectors: [passion, skill, market, revenue, course]
vector_weights_snapshot: {passion: 0.20, skill: 0.20, market: 0.20, revenue: 0.20, course: 0.20}
phase_at_creation: fundacao
regime_at_creation: maintain
horizon_days: 547
primary_score: null
is_placeholder: false
placeholder_owner: null
custom:
  _intent_vector: revenue
  _horizon_rationale: "Snapshot captured at SONHO creation; horizon matches SONHO (547d)."
  note: "Vector scores illustrative; real values populate after 5+ SONHO logs (ADR-007). Currently at 1/5 SONHOs."
  next_review_date: 2026-08-01
  linked_dream_ueid: ikigai:dream:vaga-remota-2026:<uuid_short>:<hash>
  linked_objective_ueid: ikigai:objective:q3-2026-primeira-vaga:<uuid_short>:<hash>
  linked_project_ueid: ikigai:project:onda-q3-1-pipeline-bi-cold-outreach:<uuid_short>:<hash>
source_md_path: null
tags: [persona/matheus, snapshot/initial]
# type-specific:
snapshot_date: 2026-07-03
vector_scores_snapshot:
  passion: 0.50
  skill: 0.55
  market: 0.30
  revenue: 0.00
  course: 0.40
---
```

---

## Task 1: Migrate SONHO + TRIMESTRE (Batch 1)

**Files:**
- Modify: `life-ops/ikigai/data/matheus/dreams/vaga-remota-2026.md`
- Modify: `life-ops/ikigai/data/matheus/objectives/q3-2026-primeira-vaga.md`

**Interfaces:**
- Produces: Two migrated frontmatter files, committed together

- [ ] **Step 1: Generate UUIDs**

```python
# SONHO
import uuid
print(f"SONHO uuid_short: {uuid.uuid4().hex[:8]}")
# TRIMESTRE
print(f"TRIMESTRE uuid_short: {uuid.uuid4().hex[:8]}")
```

Run: `python -c "import uuid; print(uuid.uuid4().hex[:8], uuid.uuid4().hex[:8])"`

Expected: Two 8-hex strings, e.g. `a3f1c2d4` and `b7e8f901`

- [ ] **Step 2: Edit SONHO frontmatter (vaga-remota-2026.md)**

Replace the `---` frontmatter block with the strict schema:

```yaml
---
ueid: ikigai:dream:vaga-remota-2026:<uuid_from_step1>:00000000
entity_type: dream
slug: vaga-remota-2026
parent_ueid: null
related_ueids: []
title: "Primeira vaga remota em Data/AI até 2026-12-31"
description: null
status: ACTIVE
ikigai_vectors: [passion, skill, market, revenue, course]
vector_weights_snapshot: {passion: 0.20, skill: 0.20, market: 0.20, revenue: 0.20, course: 0.20}
phase_at_creation: fundacao
regime_at_creation: maintain
horizon_days: 547
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/18m, vertical/generalist, target/remote]
last_reviewed_at: 2026-07-03T00:00:00Z
---
```

Preserve all body prose below `---` exactly as-is.

- [ ] **Step 3: Edit TRIMESTRE frontmatter (q3-2026-primeira-vaga.md)**

Replace the `---` frontmatter block:

```yaml
---
ueid: ikigai:objective:q3-2026-primeira-vaga:<uuid_from_step1>:00000000
entity_type: objective
parent_ueid: ikigai:dream:vaga-remota-2026:<uuid_SONHO>:00000000
related_ueids: []
title: "Q3-2026 — primeira vaga remota: pipeline + portfolio + 1 processo"
description: null
status: ACTIVE
ikigai_vectors: [skill, market, revenue]
vector_weights_snapshot: {passion: 0.10, skill: 0.40, market: 0.30, revenue: 0.15, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 90
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/3m, quarter/q3-2026]
last_reviewed_at: 2026-07-03T00:00:00Z
key_results:
  - "Pipeline BI (W1): 30 empresas-alvo mapeadas, 20 mensagens enviadas, 5 respostas"
  - "Portfolio (W2): 1 demo interna de 12min gravada até 2026-09-15 + 1 projeto público no GitHub"
  - "1 processo seletivo técnico completo em empresa remote-first (phone screen + take-home + onsite)"
  - "Q_HE ≥ 0.65 sustentado (sem burnout)"
progress_pct: 0.0
---
```

Preserve body prose exactly as-is. The TRIMESTRE `status: planned` → `status: ACTIVE` is the key migration change.

- [ ] **Step 4: Compute content hashes and update UEID final segments**

```python
import hashlib, re

def canonical_frontmatter_without_ueid(filepath):
    with open(filepath) as f:
        content = f.read()
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    lines = fm_match.group(1).splitlines()
    lines = [l for l in lines if not l.startswith('ueid:')]
    return '\n'.join(sorted(lines)).encode()

def content_hash_short(filepath):
    return hashlib.sha256(canonical_frontmatter_without_ueid(filepath)).hexdigest()[:8]

# Run for both files
```

Run: `python -c "..."` with the above functions on both files. Update the last `:00000000` segment of each UEID to the computed hash.

- [ ] **Step 5: Verify and commit**

Run: `git diff --stat` on the two files.
Expected: Only frontmatter lines changed; body prose untouched.

```bash
git add life-ops/ikigai/data/matheus/dreams/vaga-remota-2026.md life-ops/ikigai/data/matheus/objectives/q3-2026-primeira-vaga.md
git commit -m "chore(ikigai-vault): migrate SONHO + TRIMESTRE to strict frontmatter schema

Migrate status: seed→ACTIVE (SONHO), planned→ACTIVE (TRIMESTRE).
Add required fields: last_reviewed_at, related_ueids, source_md_path, is_placeholder, placeholder_owner, custom, primary_score.
Preserve all body prose. Phase 0 batch 1/6."
```

---

## Task 2: Migrate ONDA Q3-1 + ONDA BYD Deep-Dive (Batch 2)

**Files:**
- Modify: `life-ops/ikigai/data/matheus/projects/onda-q3-1-pipeline-bi-cold-outreach.md`
- Modify: `life-ops/ikigai/data/matheus/projects/onda-2026-07-byd-deep-dive.md`

**Interfaces:**
- Consumes: TRIMESTRE UEID from Task 1 (`ikigai:objective:q3-2026-primeira-vaga:<uuid>:<hash>`)
- Produces: Two migrated ONDA frontmatter files, committed together

- [ ] **Step 1: Generate UUIDs for both ONDAs**

Run: `python -c "import uuid; print(uuid.uuid4().hex[:8], uuid.uuid4().hex[:8])"`

- [ ] **Step 2: Edit ONDA Q3-1 frontmatter**

Replace `status: draft` → `status: DRAFT` (already uppercase, but verify). Add all missing required fields.

```yaml
---
ueid: ikigai:project:onda-q3-1-pipeline-bi-cold-outreach:<uuid>:00000000
entity_type: project
slug: onda-q3-1-pipeline-bi-cold-outreach
parent_ueid: ikigai:objective:q3-2026-primeira-vaga:<TRIMESTRE_uuid>:<TRIMESTRE_hash>
related_ueids: []
title: "Onda Q3-1 — Pipeline BI + cold outreach (15 wd, 2026-07-06 → 2026-07-24)"
description: null
status: DRAFT
ikigai_vectors: [market, skill]
vector_weights_snapshot: {passion: 0.05, skill: 0.35, market: 0.45, revenue: 0.10, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 30
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/15wd, onda/q3-1, workstream/w1]
last_reviewed_at: 2026-07-03T00:00:00Z
tech_stack: [python, polars, sqlite, obsidian, taskwarrior]
---
```

**Preserve ALL body prose** — especially the UNDs table and the `status: draft (R3: bootstrap, não "active")` comment in the body (append-only applies to prose).

- [ ] **Step 3: Edit ONDA BYD Deep-Dive frontmatter**

Replace `status: draft` → `status: DRAFT`. Add all missing required fields. `parent_ueid` same TRIMESTRE UEID.

```yaml
---
ueid: ikigai:project:onda-2026-07-byd-deep-dive:<uuid>:00000000
entity_type: project
slug: onda-2026-07-byd-deep-dive
parent_ueid: ikigai:objective:q3-2026-primeira-vaga:<TRIMESTRE_uuid>:<TRIMESTRE_hash>
related_ueids: []
title: "Onda Jul-2026 — BYD deep-dive (1 empresa, full cycle, 2026-07-09 → 2026-08-08)"
description: null
status: DRAFT
ikigai_vectors: [market, skill, course]
vector_weights_snapshot: {passion: 0.15, skill: 0.30, market: 0.35, revenue: 0.05, course: 0.15}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 30
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/30d, onda/2026-07, vertical/quant-finance, workstream/w1-w4, empresa/byd, mode/deep-dive-single]
last_reviewed_at: 2026-07-09T00:00:00Z
tech_stack: [python, polars, statsmodels, scikit-learn, vectorbt, plotly, jupyter, obsidian, taskwarrior]
---
```

- [ ] **Step 4: Compute and update content hashes**

Run hash computation for both files and replace `:00000000` with computed hash in each UEID.

- [ ] **Step 5: Verify and commit**

```bash
git add life-ops/ikigai/data/matheus/projects/onda-q3-1-pipeline-bi-cold-outreach.md life-ops/ikigai/data/matheus/projects/onda-2026-07-byd-deep-dive.md
git commit -m "chore(ikigai-vault): migrate ONDA Q3-1 + BYD deep-dive to strict frontmatter schema

Add required fields: last_reviewed_at, related_ueids, source_md_path, is_placeholder, placeholder_owner, custom, primary_score.
Update parent_ueid to point to migrated TRIMESTRE UEID.
Preserve all body prose. Phase 0 batch 2/6."
```

---

## Task 3: Migrate ONDA Salvador + Deliverable D1 (Batch 3)

**Files:**
- Modify: `life-ops/ikigai/data/matheus/projects/onda-2026-07-salvador-data-pipeline.md`
- Modify: `life-ops/ikigai/data/matheus/deliverables/byd-market-research.md`

**Interfaces:**
- Consumes: TRIMESTRE UEID from Task 1; ONDA BYD UEID from Task 2
- Produces: Two migrated files

- [ ] **Step 1: Generate UUIDs**

Run: `python -c "import uuid; print(uuid.uuid4().hex[:8], uuid.uuid4().hex[:8])"`

- [ ] **Step 2: Edit ONDA Salvador frontmatter**

```yaml
---
ueid: ikigai:project:onda-2026-07-salvador-data-pipeline:<uuid>:00000000
entity_type: project
slug: onda-2026-07-salvador-data-pipeline
parent_ueid: ikigai:objective:q3-2026-primeira-vaga:<TRIMESTRE_uuid>:<TRIMESTRE_hash>
related_ueids: []
title: "Onda 2026-07 Salvador-Data Pipeline — Tier 1 FALLBACK (parallel to BYD ONDA)"
description: null
status: DRAFT
ikigai_vectors: [market, skill]
vector_weights_snapshot: {passion: 0.05, skill: 0.30, market: 0.50, revenue: 0.10, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 30
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/30d, onda/q3-2, workstream/w1, fallback/salvador, mode/data-pipeline]
last_reviewed_at: 2026-07-09T00:00:00Z
tech_stack: [python, polars, duckdb, plotly, sqlite, obsidian, taskwarrior]
---
```

- [ ] **Step 3: Edit Deliverable D1 frontmatter**

```yaml
---
ueid: ikigai:deliverable:byd-market-research:<uuid>:00000000
entity_type: deliverable
slug: byd-market-research
parent_ueid: ikigai:project:onda-2026-07-byd-deep-dive:<ONDA_uuid>:<ONDA_hash>
related_ueids: []
title: "D1 — BYD market intelligence + greenfield detection"
description: null
status: DRAFT
ikigai_vectors: [market]
vector_weights_snapshot: {passion: 0.10, skill: 0.20, market: 0.60, revenue: 0.05, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 3
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/3d, deliverable/d1, workstream/w1, empresa/byd]
last_reviewed_at: 2026-07-09T00:00:00Z
artifact_path: null
artifact_type: document
is_public: false
---
```

- [ ] **Step 4: Compute and update content hashes**

- [ ] **Step 5: Verify and commit**

```bash
git add life-ops/ikigai/data/matheus/projects/onda-2026-07-salvador-data-pipeline.md life-ops/ikigai/data/matheus/deliverables/byd-market-research.md
git commit -m "chore(ikigai-vault): migrate ONDA Salvador + Deliverable D1 to strict frontmatter schema

Add required fields to ONDA Salvador: last_reviewed_at, related_ueids, source_md_path, is_placeholder, placeholder_owner, custom, primary_score.
Migrate D1: status draft→DRAFT, add artifact_path/artifact_type/is_public as type-specific fields.
Update parent_ueid on D1 to point to migrated ONDA BYD UEID.
Preserve all body prose. Phase 0 batch 3/6."
```

---

## Task 4: Migrate Deliverables D2 + D3 (Batch 4)

**Files:**
- Modify: `life-ops/ikigai/data/matheus/deliverables/byd-econometric-vulnerability-analysis.md`
- Modify: `life-ops/ikigai/data/matheus/deliverables/byd-cold-outreach-assets.md`

**Interfaces:**
- Consumes: ONDA BYD UEID from Task 2
- Produces: Two migrated deliverable files

- [ ] **Step 1: Generate UUIDs**

Run: `python -c "import uuid; print(uuid.uuid4().hex[:8], uuid.uuid4().hex[:8])"`

- [ ] **Step 2: Edit Deliverable D2 frontmatter**

```yaml
---
ueid: ikigai:deliverable:byd-econometric-vulnerability-analysis:<uuid>:00000000
entity_type: deliverable
slug: byd-econometric-vulnerability-analysis
parent_ueid: ikigai:project:onda-2026-07-byd-deep-dive:<ONDA_uuid>:<ONDA_hash>
related_ueids: []
title: "D2 — Econometric vulnerability analysis (BYD macro + portfolio piece)"
description: null
status: DRAFT
ikigai_vectors: [skill, market, course]
vector_weights_snapshot: {passion: 0.10, skill: 0.50, market: 0.25, revenue: 0.05, course: 0.10}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 5
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/5d, deliverable/d2, workstream/w2, empresa/byd, skill/quant]
last_reviewed_at: 2026-07-09T00:00:00Z
artifact_path: null
artifact_type: code
is_public: false
---
```

- [ ] **Step 3: Edit Deliverable D3 frontmatter**

```yaml
---
ueid: ikigai:deliverable:byd-cold-outreach-assets:<uuid>:00000000
entity_type: deliverable
slug: byd-cold-outreach-assets
parent_ueid: ikigai:project:onda-2026-07-byd-deep-dive:<ONDA_uuid>:<ONDA_hash>
related_ueids: []
title: "D3 — Cold outreach assets (LinkedIn + email PT-BR)"
description: null
status: DRAFT
ikigai_vectors: [market, course]
vector_weights_snapshot: {passion: 0.10, skill: 0.15, market: 0.55, revenue: 0.10, course: 0.10}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 2
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/2d, deliverable/d3, workstream/w3, empresa/byd, mode/cold-outreach, lang/pt-br]
last_reviewed_at: 2026-07-09T00:00:00Z
artifact_path: null
artifact_type: document
is_public: false
---
```

- [ ] **Step 4: Compute and update content hashes**

- [ ] **Step 5: Verify and commit**

```bash
git add life-ops/ikigai/data/matheus/deliverables/byd-econometric-vulnerability-analysis.md life-ops/ikigai/data/matheus/deliverables/byd-cold-outreach-assets.md
git commit -m "chore(ikigai-vault): migrate Deliverables D2 + D3 to strict frontmatter schema

Migrate D2: add artifact_path/artifact_type (code)/is_public type-specific fields.
Migrate D3: add artifact_path/artifact_type (document)/is_public type-specific fields.
Update parent_ueid on both to point to migrated ONDA BYD UEID.
Preserve all body prose (templates, A/B test plan). Phase 0 batch 4/6."
```

---

## Task 5: Migrate Deliverable D4 + PROFILE JSON→MD (Batch 5)

**Files:**
- Modify: `life-ops/ikigai/data/matheus/deliverables/byd-process-tracker.md`
- Create: `life-ops/ikigai/data/matheus/ikigai_state/profile-2026-07-03.md`
- Delete: `life-ops/ikigai/data/matheus/ikigai_state/profile-2026-07-03.json` (after verification)

**Interfaces:**
- Consumes: ONDA BYD UEID from Task 2
- Produces: Migrated D4 + new PROFILE MD file

- [ ] **Step 1: Generate UUIDs**

Run: `python -c "import uuid; print(uuid.uuid4().hex[:8], uuid.uuid4().hex[:8])"`

- [ ] **Step 2: Edit Deliverable D4 frontmatter**

```yaml
---
ueid: ikigai:deliverable:byd-process-tracker:<uuid>:00000000
entity_type: deliverable
slug: byd-process-tracker
parent_ueid: ikigai:project:onda-2026-07-byd-deep-dive:<ONDA_uuid>:<ONDA_hash>
related_ueids: []
title: "D4 — Process tracker (outreach → response → processo)"
description: null
status: DRAFT
ikigai_vectors: [market, revenue]
vector_weights_snapshot: {passion: 0.10, skill: 0.10, market: 0.50, revenue: 0.25, course: 0.05}
phase_at_creation: fundacao
regime_at_creation: push
horizon_days: 7
primary_score: null
is_placeholder: false
placeholder_owner: null
custom: {}
source_md_path: null
tags: [persona/matheus, horizon/7d, deliverable/d4, workstream/w4, empresa/byd, mode/process-tracking]
last_reviewed_at: 2026-07-09T00:00:00Z
artifact_path: null
artifact_type: data
is_public: false
---
```

- [ ] **Step 3: Create PROFILE MD+YAML from JSON**

Read `profile-2026-07-03.json`. Flatten nested `ikigai_vectors` to `vector_scores_snapshot` at top level. Convert to MD+YAML:

```yaml
---
ueid: ikigai:profile:matheus-2026-07-03:<PROFILE_uuid>:00000000
entity_type: profile
slug: matheus-2026-07-03
parent_ueid: null
related_ueids: []
title: "Matheus IKIGAi profile snapshot — 2026-07-03 (SONHO creation)"
description: null
status: ACTIVE
created_at: 2026-07-03T00:00:00Z
updated_at: <migration_timestamp>
last_reviewed_at: <migration_timestamp>
ikigai_vectors: [passion, skill, market, revenue, course]
vector_weights_snapshot: {passion: 0.20, skill: 0.20, market: 0.20, revenue: 0.20, course: 0.20}
phase_at_creation: fundacao
regime_at_creation: maintain
horizon_days: 547
primary_score: null
is_placeholder: false
placeholder_owner: null
source_md_path: null
tags: [persona/matheus, snapshot/initial]
snapshot_date: 2026-07-03
vector_scores_snapshot:
  passion: 0.50
  skill: 0.55
  market: 0.30
  revenue: 0.00
  course: 0.40
custom:
  _intent_vector: revenue
  _horizon_rationale: "Snapshot captured at SONHO creation; horizon matches SONHO (547d)."
  note: "Vector scores illustrative; real values populate after 5+ SONHO logs (ADR-007). Currently at 1/5 SONHOs."
  next_review_date: 2026-08-01
  linked_dream_ueid: ikigai:dream:vaga-remota-2026:<SONHO_uuid>:<SONHO_hash>
  linked_objective_ueid: ikigai:objective:q3-2026-primeira-vaga:<TRIMESTRE_uuid>:<TRIMESTRE_hash>
  linked_project_ueid: ikigai:project:onda-q3-1-pipeline-bi-cold-outreach:<ONDA_Q31_uuid>:<ONDA_Q31_hash>
---
```

After creating the MD file, compute content hash and update `:00000000` to real hash.

- [ ] **Step 4: Verify JSON→MD fidelity**

Check that every top-level key from the JSON appears either as a top-level frontmatter field or inside `custom:` in the MD file. Specifically verify:
- `linked_dream_ueid` → `custom.linked_dream_ueid` ✓
- `linked_objective_ueid` → `custom.linked_objective_ueid` ✓
- `linked_project_ueid` → `custom.linked_project_ueid` ✓
- `ikigai_vectors.*.value` → `vector_scores_snapshot.*` ✓
- `ikigai_vectors.*.evidence` → dropped (data-first defers vector evidence to later phase)
- `next_review_date` → preserved in `custom.next_review_date` ✓

- [ ] **Step 5: Commit D4 + PROFILE**

```bash
git add life-ops/ikigai/data/matheus/deliverables/byd-process-tracker.md life-ops/ikigai/data/matheus/ikigai_state/profile-2026-07-03.md
git commit -m "chore(ikigai-vault): migrate Deliverable D4 + PROFILE JSON→MD to strict frontmatter schema

D4: add artifact_path/artifact_type (data)/is_public type-specific fields.
PROFILE: convert from JSON to MD+YAML. Flatten nested ikigai_vectors to vector_scores_snapshot.
Move linked_*_ueid to custom. Update all timestamps.
Delete old JSON after verification.
Preserve all JSON fields (no data loss). Phase 0 batch 5/6."
```

- [ ] **Step 6: Delete the old JSON file in a separate commit**

```bash
rm life-ops/ikigai/data/matheus/ikigai_state/profile-2026-07-03.json
git add life-ops/ikigai/data/matheus/ikigai_state/profile-2026-07-03.json
git commit -m "chore(ikigai-vault): delete legacy JSON PROFILE after MD+YAML migration

profile-2026-07-03.json replaced by profile-2026-07-03.md (strict frontmatter schema).
All fields preserved — no data loss. Phase 0 batch 5/6 (final)."
```

Note: The JSON deletion is a separate commit because git treats file deletions as a distinct change from content modifications.

---

## Task 6: Verification and Edge Cases

**Files:**
- Review: all 9 migrated `.md` files
- Review: `life-ops/ikigai/data/matheus/ikigai_state/profile-2026-07-03.md`

**Interfaces:**
- Consumes: All UEIDs computed in Tasks 1–5
- Produces: Final verification commit or patch commits

- [ ] **Step 1: Verify all UEIDs have real uuid_short segments**

```bash
grep -r "ueid: ikigai:" life-ops/ikigai/data/matheus/ --include="*.md" | grep "00000000:00000000"
```

Expected: no matches (all `00000000:00000000` replaced). If any remain, fix and amend.

- [ ] **Step 2: Verify all status values are uppercase**

```bash
grep -r "^status: " life-ops/ikigai/data/matheus/ --include="*.md" | grep -v "ACTIVE\|DRAFT\|PAUSED\|ACHIEVED\|ABANDONED\|ARCHIVED"
```

Expected: no matches (no lowercase status tokens). If `seed` or `planned` remain, fix.

- [ ] **Step 3: Verify all required base fields present in each file**

Check each migrated file has: `ueid`, `entity_type`, `slug`, `parent_ueid`, `related_ueids`, `title`, `description`, `status`, `created_at`, `updated_at`, `last_reviewed_at`, `ikigai_vectors`, `vector_weights_snapshot`, `phase_at_creation`, `regime_at_creation`, `horizon_days`, `primary_score`, `is_placeholder`, `placeholder_owner`, `custom`, `source_md_path`, `tags`.

```bash
# Per file: check all 23 required base fields are present
```

- [ ] **Step 4: Verify cross-references are consistent**

- SONHO has `parent_ueid: null` ✓
- TRIMESTRE has `parent_ueid` pointing to SONHO ✓
- All 3 ONDAs have `parent_ueid` pointing to TRIMESTRE ✓
- All 4 Deliverables have `parent_ueid` pointing to ONDA BYD ✓
- PROFILE `custom.linked_*_ueid` fields point to migrated UEIDs ✓

- [ ] **Step 5: Check for any remaining legacy placeholders**

```bash
grep -r "source: user" life-ops/ikigai/data/matheus/ --include="*.md"
```

`source` field is not in the base schema (not a required field per spec). If present, it may stay in `custom:` or be dropped — decision: drop it (not in schema, extra field not declared in type-specific). Remove or move to `custom: {legacy_source: user}`.

- [ ] **Step 6: Final commit for any edge case fixes**

If any issues found in Steps 1–5, fix in-place and commit as:

```bash
git commit -m "chore(ikigai-vault): fix Phase 0 edge cases and verify all migrations

Fix remaining: [list fixes].
Verify cross-refs consistent: SONHO→TRIMESTRE→3 ONDAs→4 Deliverables.
Phase 0 complete — all 12 files migrated to strict frontmatter schema."
```

---

## Self-Review Checklist

**1. Spec coverage:**
- [ ] Phase 0 (Section 4 of spec): 12 files in 6 batches of 2 — covered by Tasks 1–6
- [ ] Status enum migration (amendment #6): seed→ACTIVE, planned→ACTIVE, draft→DRAFT — covered in all tasks
- [ ] UEID hash placeholder replacement (Section 3.3): `00000000:00000000` → real uuid_short — covered in all tasks
- [ ] Required base fields (23 per entity): added in every task
- [ ] Type-specific fields per entity: `key_results`, `progress_pct` (Objective); `tech_stack` (Project); `artifact_path`, `artifact_type`, `is_public` (Deliverable) — all covered
- [ ] PROFILE JSON→MD conversion (Section 2.3): Task 5 with full field mapping

**2. Placeholder scan:**
- [ ] No `TBD`, `TODO`, or "implement later" anywhere in plan steps
- [ ] All field values are exact (e.g., `status: ACTIVE`, not `status: <UPPERCASE>`)
- [ ] All UUIDs use generated values, not `<uuid>`
- [ ] No "Similar to Task N" — each task is self-contained with full frontmatter

**3. Type consistency:**
- [ ] `ueid` field name lowercase (matches Pydantic `ueid`, amendment #2)
- [ ] `horizon_days: 547` for SONHO (within 1825–3650 bound ✓)
- [ ] `horizon_days: 90` for TRIMESTRE (within 90–365 bound ✓)
- [ ] `horizon_days: 30` for all ONDAs (within 30–180 bound ✓)
- [ ] `horizon_days: 3/5/2/7` for Deliverables (within 1–7 bound ✓ for D1/D2/D3, D4=7 within bound)
- [ ] `parent_ueid` on Deliverables points to ONDA BYD (correct parent: ONDA BYD is the project parent of all 4 D deliverables per spec Section 7.1)
- [ ] `entity_type` values match discriminator list: `dream`, `objective`, `project`, `deliverable`, `profile`

**4. Commit format check:**
- [ ] All commit messages use `chore(ikigai-vault):` prefix ✓
- [ ] All commit messages use spec format: `add <entity_type>/<slug>` ✓
- [ ] No `Co-Authored-By` trailers ✓
- [ ] No `--no-verify` flags ✓
