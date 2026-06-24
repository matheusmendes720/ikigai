# IKIGAi — Canonical Specification (v1.0)

> **AI-native spec** for the standalone IKIGAi meta-brain. A coding agent should be able to implement the entire module reading only this file + `CONVENTIONS.md`.

---

## 1. Mission

IKIGAi is the **meta-brain** (propositivo-superior) of the Algorithmic Life OS. It:

1. Holds the **5 canonical vectors** + their fractal sub-vectors
2. Owns the **22 North Star Metrics** (NSM) constants
3. Runs **6 deterministic heuristics** (no LLM, no NLP, only arithmetic)
4. Decomposes **Dreams → Goals → Objectives → Projects → Tasks → Deliverables**
5. Hosts the **canonical markdown vault** (single source of truth)
6. Propagates decisions to downstream subsystems (PROJ, STUDY, PLAN, METRICS)

---

## 2. Architectural Decisions (locked from 16-question review)

| # | Decision | Resolution |
|---|----------|------------|
| D1 | Hierarchy shape | **Strict tree + 'related' links**: `parent_ueid` + `related_ueids[]` |
| D2 | Course vector | **5th vector + external tag**: `VectorType.COURSE` with `is_external=True` |
| D3 | Fractal vectors | **Sub-vectors**: e.g., `skill.python`, `skill.sql`, `market.freelance` |
| D4 | Score range | **`ScoreValue(value, unit)`**: explicit unit per score |
| D5 | Meta-vetor formula | **Hybrid**: 60% geometric mean + 40% harmonic mean (tunable per phase) |
| D6 | Entity polymorphism | **`PlanEntity` polymorphic** with `entity_type` discriminator + `extra="allow"` |
| D7 | Forward-compat | **Placeholders**: `is_placeholder` + `placeholder_owner` |
| D8 | SoT | **Markdown vault is canonical**; SQLite is internal mirror |
| D9 | Append-only | **DB-level triggers** prevent UPDATE/DELETE on plan tables |
| D10 | UEID | **Tri-key**: `slug:uuid_short:content_hash_short` (anti-fragile) |
| D11 | Phase cycle | **Snapshot within phase + iterative convergence at boundary** (max 5 iters) |
| D12 | Override | **Manual + recommendation_score**: 0.0–1.0 with audit trail |
| D13 | Regime granularity | **Fractal**: Global → Cluster → Vector → SubVector |
| D14 | Failure policy | **Soft-warn + auto-migrate + triagem.md entry** |
| D15 | Tests | **2700+ tests** (match `life-ops/operational/`) |
| D16 | AI Harness | **Separate module** (`life-ops/harness/`) |

---

## 3. Data Model

### 3.1 Identity (UEID — tri-key, anti-fragile)

Format: `<namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>`

- `namespace`: `ikigai` | `tw` | `obsidian` | `external`
- `entity_type`: dream | goal | objective | project | task | deliverable | routine | block | ritual | habit | skill | topic | material | session | vector | profile
- `slug`: human-readable, immutable post-creation
- `uuid_short`: 8-char UUID, immutable
- `content_hash_short`: 8-char SHA-256 of canonical frontmatter

### 3.2 Core Entities

#### `PlanEntity` (polymorphic base)
```python
class PlanEntity(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        discriminator="entity_type",
        frozen=False,
    )
    ueid: UEID
    entity_type: EntityType
    slug: str
    parent_ueid: UEID | None
    related_ueids: list[UEID]
    title: str
    description: str | None
    status: StatusType
    created_at: datetime
    updated_at: datetime
    last_reviewed_at: datetime | None
    ikigai_vectors: list[VectorType]
    vector_weights_snapshot: dict[VectorType, float]
    phase_at_creation: Phase | None
    regime_at_creation: RegimeType | None
    horizon_days: int | None
    primary_score: ScoreValue | None
    is_placeholder: bool = False
    placeholder_owner: str | None
    custom: dict[str, Any]
    source_md_path: Path | None
```

#### Hierarchy (5-10y → 1-3y → 3-12mo → 1-6mo → 1-7d → concrete)

| Entity | Horizon | Inheritance |
|--------|---------|-------------|
| `DreamEntity` | 5-10y (1825-3650d) | PlanEntity + motivation |
| `GoalEntity` | 1-3y (365-1095d) | PlanEntity + success_metrics |
| `ObjectiveEntity` | 3-12mo (90-365d) | PlanEntity + key_results |
| `ProjectEntity` | 1-6mo (30-180d) | PlanEntity + tech_stack (forward-compat) |
| `TaskEntity` | 1-7d (1-7d) | PlanEntity + priority, assignee |
| `DeliverableEntity` | concrete | PlanEntity + artifact_path |

#### IKIGAi Core

| Entity | Purpose |
|--------|---------|
| `IKIGAiVectorEntity` | One of 5 vectors (passion/skill/market/revenue/course) + sub-vectors |
| `IKIGAiProfile` | Snapshot of all 5 vectors + zones + alignment |
| `SkillNode` | Specific skill within skill vector |
| `OpportunitySignal` | Market opportunity |

#### Operational (forward-compat)

| Entity | Forward-Compat Target |
|--------|----------------------|
| `RoutineEntity` | CLUSTER_PLAN |
| `TimeBlockEntity` | life_tatics |
| `RitualEntity` | CLUSTER_PLAN |
| `HabitEntity` | CLUSTER_PLAN (habit tracker) |

---

## 4. Vector Scoring

### 4.1 The 5 Vectors

| Vector | Formula (0-100) | Substrate |
|--------|------------------|-----------|
| **Passion** | $1 - e^{-\lambda \cdot streak}$, $\lambda = 0.093 D^{-1}$ | habits, sleep, workout, meditation |
| **Skill** | $\sum skill.level\_score \cdot market\_demand\_weight \cdot 0.5 + learning\_momentum \cdot 0.3 + project\_completion \cdot 0.2$ | study sessions, projects |
| **Market** | $fit\_avg \cdot 0.4 + skills\_demand\_avg \cdot 0.4 + opportunities\_pipeline \cdot 0.2$ | opportunities, fit_score |
| **Revenue** | $\frac{revenue\_actual}{\max(revenue\_target, 1)} \cdot 70 + pipeline\_health \cdot 30$ | actual revenue, pipeline |
| **Course** | $attendance\_rate \cdot 0.5 + assignments\_on\_time \cdot 0.3 + exam\_avg \cdot 0.2$ | SENAI attendance, exams |

### 4.2 Meta-Vetor (Hybrid)

```python
def meta_vector(scores: dict[VectorType, ScoreValue], weights: dict[VectorType, float]) -> ScoreValue:
    """
    Hybrid: 60% geometric mean (balance) + 40% harmonic mean (low-vec floor).
    """
    active = {k: v.value for k, v in scores.items() if v.value > 0}
    if not active:
        return ScoreValue(value=0.0, unit="percent")
    
    w_norm = {k: weights.get(k, 0.0) / sum(weights.values()) for k in active}
    log_sum = sum(w_norm[k] * math.log(max(v, 0.01)) for k, v in active.items())
    geo = math.exp(log_sum)
    harm = 1.0 / sum(w_norm[k] / max(v, 0.01) for k, v in active.items())
    
    w_geo = PAV_NS.META_VETOR_W_GEO  # 0.6
    w_harm = PAV_NS.META_VETOR_W_HARM  # 0.4
    final = w_geo * geo + w_harm * harm
    
    return ScoreValue(value=final, unit="percent")
```

### 4.3 Alignment Labels

| Score | Label |
|-------|-------|
| `>= 75` | `ALIGNED` |
| `[50, 75)` | `CONVERGING` |
| `[25, 50)` | `MISALIGNED` |
| `< 25` | `CRITICAL` |

---

## 5. Heuristics (6 deterministic algorithms)

### H1. `compute_regime(qhe_7d, c_comp_24h, infractions_24h, sleep_debt_h) -> RegimeType`

4-state FSM: `PUSH ↔ MAINTAIN ↔ REDUCE ↔ RECOVER`

Hysteresis:
- Upgrade: 3 days
- Downgrade: 2 days
- RECOVER entry: immediate (1 day)
- RECOVER exit: 3 days

Setpoints per regime:

| Regime | hardwork_budget_h | pause_min | sleep_target_h | Q_HE_target |
|--------|-------------------|-----------|----------------|-------------|
| PUSH | 4.0 | 10 | 7.5 | 0.85 |
| MAINTAIN | 2.5 | 15 | 8.0 | 0.65 |
| REDUCE | 1.5 | 20 | 8.5 | 0.45 |
| RECOVER | 0.5 | 30 | 9.0 | 0.25 |

### H2. `compute_phase(ikigai_score, revenue_pct, opportunities, cognitive_debt) -> Phase`

5-phase FSM: `FUNDAÇÃO → BUSCA → HACKATHON → RECUPERACAO → OVERCLOCKING`

Iterative convergence (max 5 iters, threshold 0.01).

Phase weights $w_1..w_5$ (snapshot at phase entry):

| Phase | $w_1$ Passion | $w_2$ Skill | $w_3$ Market | $w_4$ Revenue | $w_5$ Course |
|-------|---------------|-------------|--------------|---------------|--------------|
| FUNDAÇÃO | 0.15 | 0.40 | 0.15 | 0.10 | 0.20 |
| BUSCA | 0.10 | 0.15 | 0.45 | 0.20 | 0.10 |
| HACKATHON | 0.10 | 0.20 | 0.20 | 0.40 | 0.10 |
| RECUPERACAO | 0.50 | 0.10 | 0.05 | 0.05 | 0.30 |
| OVERCLOCK | 0.15 | 0.15 | 0.15 | 0.50 | 0.05 |

### H3. `recalibrate_weight_ucb(...)` — Upper Confidence Bound

Quarterly weight recalibration. UCB bonus for under-explored vectors.

### H4. `compute_opportunity_fit(...)` — Market fit score

`fit_score ∈ [0, 1]` based on skills_match, deadline_feasibility, R$/hour, IKIGAi alignment.

### H5. `should_promote_skill(...)` — Skill velocity

Promote skill if `hours_pct >= 0.80 AND days_in_phase >= 45 AND retention >= 0.75`.

### H6. `compute_task_priority(reach, impact, confidence, effort, w_ikigai, w_deadline)`

`PriorityScore = (R × I × C / E) × w_ikigai × w_deadline`

---

## 6. State Machines (8 explicit)

| Entity | States | Transitions |
|--------|--------|-------------|
| Dream | `seed → active → fulfilled / abandoned / archived` | with REVIEW checkpoints |
| Goal | `draft → active → achieved / abandoned / paused` | with quarterly review |
| Objective | `planned → active → done / blocked / cancelled` | key-result completion |
| Project | `backlog → active → paused → completed / cancelled` | sprint velocity |
| Task | `todo → in_progress → blocked → done / cancelled` | RICE priority |
| Routine | `draft → active → paused → archived` | daily review |
| Habit | `active → paused → archived / mastered` | streak tracking |
| Regime | `recover → reduce → maintain → push` | hysteresis-driven |

Each transition has: trigger, pre-condition, post-condition, audit log.

---

## 7. Persistence

### 7.1 Markdown Vault (Canonical SoT)

Layout:
```
~/ikigai-vault/
├── dreams/
├── goals/
├── objectives/
├── projects/
├── tasks/
├── deliverables/
├── journal/
├── weekly/
├── ikigai_state/
└── meta/
```

Each entity = 1 .md file with YAML frontmatter + markdown body.

### 7.2 SQLite (Internal Mirror, Append-Only)

Schema (key tables):
- `plan_entities` — all PlanEntity instances (append-only)
- `ikigai_vectors` — vector scores history
- `ikigai_profiles` — profile snapshots
- `phase_snapshots` — frozen phase weights
- `regime_decisions` — regime history
- `audit_log` — all state transitions

DB-level triggers:
```sql
CREATE TRIGGER plan_entities_no_update
BEFORE UPDATE ON plan_entities
BEGIN
    SELECT RAISE(ABORT, 'plan_entities is append-only; use _history table for changes');
END;
```

### 7.3 ChromaDB (Optional, Semantic Search)

Indexed lazily; fallback to grep if unavailable.

---

## 8. Propagation

### 8.1 IKIGAi → Plan Entities

Vector weights cascade: dream-level IKIGAi weights → goal → objective → project → task.

Each level can override weights (`vector_weights_snapshot`), but defaults inherit from parent.

### 8.2 Drift Detection

`triagem.md` auto-generated when:
- Markdown mtime ≠ SQLite mtime (drift > 5min)
- Both modified independently (3-way merge needed)
- Vector scores computed don't match stored

Resolution: markdown wins (per Q6/Q11). SQLite is regenerated on `ikigai sync`.

### 8.3 Histerese Scope (Fractal)

- Global regime: 3d upgrade / 2d downgrade
- Cluster regime: 3d / 2d
- Vector regime: 2d / 1d
- Sub-vector regime: 1d / 0d (immediate)

---

## 9. CLI (Typer, --json everywhere)

```bash
ikigai vector list [--json]
ikigai vector set passion 78 --evidence "5d streak"
ikigai profile snapshot [--json]
ikigai plan dream list [--json]
ikigai plan dream create --slug "senior-engineer" --horizon 3650
ikigai plan goal list --parent <dream_ueid> [--json]
ikigai regime status [--json]
ikigai regime override --to PUSH --reason "deadline" --ack-risks
ikigai phase status [--json]
ikigai sync [--prefer markdown|sqlite]
ikigai query --ikigai-vector skill [--json]
ikigai index [--backend vector]
ikigai drift [--resolve]
```

---

## 10. Invariants

| # | Invariant | Enforcement |
|---|-----------|-------------|
| I1 | Append-only on plan_entities | DB trigger |
| I2 | UEID uniqueness | DB unique constraint |
| I3 | Vector scores ∈ [0, 100] | Pydantic Field |
| I4 | Q_HE ∈ [0, 1] | Pydantic Field |
| I5 | Status transitions valid | StateMachine |
| I6 | Slug immutable post-creation | DB trigger + Pydantic frozen |
| I7 | Phase weights snapshot | separate table |
| I8 | Score unit consistency | ScoreValue validator |
| I9 | Markdown = canonical | sync orchestrator priority |
| I10 | Hysteresis respected | StateMachine.hysteresis_days |

---

## 11. North Star Metrics (22 constants)

Frozen in `CONSTANTS.py`:

```python
class PAV_NS:
    # Janelas temporais
    HORARIO_ACORDAR_MIN = 3
    HORARIO_ACORDAR_MAX = 5
    HORARIO_DORMIR_MIN = 18
    HORARIO_DORMIR_MAX = 21
    
    # Pomodoro
    POMODORO_WORK_MIN = 50
    POMODORO_BREAK_MIN = 10
    
    # Mathematical
    LAMBDA = 0.093  # habit learning rate
    RHO = 0.7333    # calendar conversion
    WORK_RATIO = 0.7333
    
    # Fractal temporal
    WAVE = 15
    CYCLE = 45
    PHASE = 180
    
    # Q_HE thresholds
    Q_HE_PUSH = 0.85
    Q_HE_REDUCE = 0.65
    Q_HE_RECOVER = 0.60
    
    # Meta-vetor hybrid weights
    META_VETOR_W_GEO = 0.6
    META_VETOR_W_HARM = 0.4
    
    # Hysteresis windows
    HYSTERESIS_UPGRADE_DAYS = 3
    HYSTERESIS_DOWNGRADE_DAYS = 2
```

---

## 12. Testing Strategy

Target: **2700+ tests** matching `life-ops/operational/`.

Distribution:
- `test_entities.py` (300): all Pydantic models
- `test_scoring.py` (250): 5 vectors + meta-vetor + hybrid
- `test_heuristics.py` (400): 6 heuristics × ~67 cases
- `test_state_machines.py` (350): 8 machines × ~44 transitions
- `test_propagation.py` (300): markdown↔SQLite, drift, sync
- `test_decomposition.py` (200): Dream→Task tree operations
- `test_overrides.py` (150): RegimeOverride + recommendation
- `test_drift_detection.py` (150): drift detector + triagem.md
- `property/test_*.py` (300): hypothesis-based
- `integration/test_cli.py` (200): end-to-end CLI

Total: **2400-2700 tests** for MVP+.

---

## 13. Roadmap

| Sprint | Scope |
|--------|-------|
| **MVP (current)** | Entities + scoring + 2 heuristics + markdown + SQLite + CLI + 250 tests |
| Sprint 2 | Remaining 4 heuristics (UCB, fit, velocity, priority) |
| Sprint 3 | ChromaDB indexing + semantic search |
| Sprint 4 | TW UDA bridge + bidirectional sync |
| Sprint 5 | TUI (Textual) for state visualization |
| Sprint 6 | Integration with root `life` CLI |
| Sprint 7 | `life-ops/harness/` (LLM-suggestion, separate) |

---

## 14. References

- `life-ops/planner/ikigai_planning/ikigai_4_vectors.md` — vector specs
- `life-ops/planner/ikigai_planning/ikigai_north_star_metrics.md` — 22 constants
- `life-ops/planner/ikigai_planning/ikigai_propagation.md` — data flow
- `life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md` — algorithms
- `vibe-ops/architecture/ADR-003-ikigai-as-meta-brain.md` — meta-brain decision
- `vibe-ops/architecture/ADR-005-data-mesh-topology.md` — 6 cross-domain contracts
- `life-ops/operational/` — quality benchmark (2717 tests, mypy --strict)

---

*SPEC.md — v1.0 — 2026-06-22 — IKIGAi Meta-Brain Canonical Spec*
