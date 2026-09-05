# SONHO Tree Hybrid Design — IKIGAI Hierarchy + Investigation Layer + External Access

**Date:** 2026-09-03
**Status:** Proposed (post 11-round grill session, awaiting user review per brainstorming skill step 8)
**Scope:** Spec 1 (Planning Contract) + Spec 2 (MCP + Fork Protocol) + Spec 3 (Investigation Queue) — design only, code deferred to writing-plans skill

---

## Context

The user asked: *"finally close the gap log sonho manual?? expandido e fully featured.. based on my last requirements pending to fit on our overall infrastructure of agentic workflows?"*

After 11 grill rounds, the gap is reframed: the SONHO log is not a manual artifact to be authored in isolation — it is a **typed entity in a 6-level planning hierarchy**, persisted via `vault_write`, validated by drift detector, consumed by forks, and informed by an investigation layer that lets the Deep Agent do pre-SONHO research without polluting the planning tree.

The canonical active plan (`vault/ikigai/closing-2026/02-q4-2026/01-plano-trimestral/deep-agent-build-q4-2026.md`, 155 lines) self-declares as **infra enabling future work**, not as a lifestyle outcome. This design promotes it to OBJETIVO under a parent SONHO at the correct tier, with deferred siblings for the work that the active plan §8 marks out-of-scope.

---

## Goal

Codify a SONHO tree that:
1. Matches the 6-level canonical hierarchy (SONHO → OBJETIVO → META → PROJETO → ENTREGA → TAREFA) with the 5-tier PlanTier (SONHO/QUARTERLY/ONDA/WEEKLY/DAILY)
2. Carries IKIGAi vectors as ordered lists with a strict subset rule from parent → child
3. Tracks PAE phase per entity with hybrid manual/agent-managed transitions
4. Lives alongside a separate investigation layer (`data/investigation_queue/`) for pre-form research
5. Reads external project paths through an allowlisted MCP tool
6. Enforces 9 drift invariants via the canonical drift detector (`test_canonical_scope.py`)

---

## Architecture (1 paragraph)

The SONHO tree is rooted at **`Ship Algorithmic Life OS v1 by 2027-Q3`** (tier=SONHO, horizon=12 months, ikigai_vectors=[skill, market, revenue]). It contains 3 OBJETIVOs: one active (`Deep Agent build Q4-2026`, tier=QUARTERLY, ikigai=[skill]) and two deferred (`IKIGAI v2 wiring`, `vault-sync combo A`, both 2027-Q1). The active OBJETIVO has 5 METAs (B0-B4) inheriting from the existing Q4 plan §2, and ~17 PROJETOs as the granularity forks consume. PAE phase is dual (`pae_cycle_phase` + `pae_tier`); SONHO transitions are user-only, META transitions are agent-OK, gated by a new `actor` parameter on `vault_write`. Investigation tasks live in `data/investigation_queue/` (filesystem queue pattern reused from `data/review_queue/`), exposed via 3 MCP tools. External project paths are read through `external_folder_read` (Spec 2 step 4) gated by `src/ikigai/src/ikigai/security/external_roots.yaml`. Nine drift invariants enforce completeness, hierarchy, phase transitions, append-only, audit, and allowlist invariants.

---

## The 12 Locked Decisions

| # | Decision | Source |
|---|---|---|
| 1 | SONHO tree shape = **Cenário B**: SONHO = "Ship Life OS v1" (12m); Q4 build = OBJETIVO | tier integrity + active plan §1 |
| 2 | Active OBJETIVO = "Deep Agent build Q4-2026" with 5 METAs (B0-B4) | active plan §2 |
| 3 | SONHO ikigai_vectors = `[skill, market, revenue]` | build-first SONHO |
| 4 | OBJETIVO/META ikigai_vectors = `[skill]` only | honest signal — Q4 is pure infra |
| 5 | Subset rule: `child.ikigai_vectors ⊆ parent.ikigai_vectors` | validator enforced |
| 6 | Done criteria = **A hard + B soft**: A = operational (B0-B6 + tests + 1 fork consuming); B = 30d daily use | measurable + utility signal |
| 7 | Investigation tasks = filesystem queue, NOT in 6-level hierarchy | pre-form data; pattern reuse |
| 8 | PAE phase mgmt = hybrid (SONHO=user-only, META=agent-OK) + `vault_write.actor` | lifecycle vs operational |
| 9 | Hierarchy depth = extend to PROJETO (~17 nodes), stop before ENTREGA/TAREFA | unit of sprint work |
| 10 | Lifestyle SONHOs deferred (Spec 2 `plan_create` enables them) | scope discipline |
| 11 | External folder access = `external_folder_read` (Spec 2 step 4) + `investigation_queue` (Spec 3) | 2 distinct use cases |
| 12 | Drift invariants = 9 (a-i Full) | maximal enforcement |

---

## The SONHO Tree (concrete structure)

```
SONHO  Ship Algorithmic Life OS v1 by 2027-Q3
       tier=SONHO · ikigai_vectors=[skill, market, revenue]
       pae_cycle_phase=plan · pae_tier=SONHO
       success_metric=A hard + B soft
       parent_ueid=null
  │
  ├─ OBJETIVO  Deep Agent build Q4-2026 [ACTIVE]
  │            tier=QUARTERLY · ikigai_vectors=[skill]   (subset ✓)
  │            pae_cycle_phase=plan · pae_tier=QUARTERLY
  │            parent_ueid=SONHO.ueid
  │            horizon_days=66
  │    ├─ META  B0 hygiene (1 sem, tier=ONDA, ikigai=[skill], pae=plan)
  │    │       └─ (no PROJETOs — B0 is single-shot setup; drift exception §invariant-d)
  │    ├─ META  B1 A2UI schema (2 sem, tier=ONDA, ikigai=[skill])
  │    │       ├─ PROJETO spike-A2UI-spec
  │    │       ├─ PROJETO write-pydantic-schema
  │    │       ├─ PROJETO write-unit-tests
  │    │       └─ PROJETO write-end-to-end-demo
  │    ├─ META  B2 server-mgmt CLI (2 sem, tier=ONDA, ikigai=[skill])
  │    │       ├─ PROJETO write-typer-cli-skeleton
  │    │       ├─ PROJETO implement-5-subcommands
  │    │       └─ PROJETO write-cli-tests
  │    ├─ META  B3 MCP gateway (2 sem, tier=ONDA, ikigai=[skill])
  │    │       ├─ PROJETO setup-mcp-server
  │    │       ├─ PROJETO wire-3-tools
  │    │       └─ PROJETO integration-test
  │    └─ META  B4 queue worker (2 sem, tier=ONDA, ikigai=[skill])
  │            ├─ PROJETO producer-write-to-queue
  │            ├─ PROJETO consumer-read-from-queue
  │            └─ PROJETO idempotency-on-ueid
  │
  ├─ OBJETIVO  IKIGAI v2 wiring [DEFERRED per Q4 §8 → 2027-Q1]
  │            tier=QUARTERLY · ikigai_vectors=[skill]   (subset ✓)
  │            pae_cycle_phase=plan · pae_tier=QUARTERLY
  │            parent_ueid=SONHO.ueid
  │
  └─ OBJETIVO  vault-sync combo A [DEFERRED per Q4 §8 → 2027-Q1]
               tier=QUARTERLY · ikigai_vectors=[skill, market]   (subset ✓)
               pae_cycle_phase=plan · pae_tier=QUARTERLY
               parent_ueid=SONHO.ueid
```

Total: 1 SONHO + 3 OBJETIVOs + 5 METAs + 13 PROJETOs = 22 nodes (B0 has 0 PROJETOs as setup-META exception; B1=4, B2=3, B3=3, B4=3).

---

## Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  PLAN LAYER (vault/ikigai/closing-2026/...)                    │
│  - SONHO→OBJETIVO→META→PROJETO→ENTREGA→TAREFA                   │
│  - Append-only via vault_write (ADR-012)                        │
│  - ikigai_vectors + pae_cycle_phase + pae_tier + parent_ueid    │
│  - Drift detector validates 9 invariants                        │
│  - vault_write.actor parameter tracks transition principal      │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ promotion: investigation finding → SONHO candidate
                              │ (manual via vault_write)
                              │
┌─────────────────────────────────────────────────────────────────┐
│  INVESTIGATION LAYER (data/investigation_queue/)               │
│  - Append-only JSON files (atomic write via tmp + rename)      │
│  - 3 MCP tools: investigation_enqueue / status / complete      │
│  - Pattern reuse from data/review_queue/ (Phase 3 v1)          │
│  - Pre-form data: NOT yet SONHO, NOT yet PROJETO               │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ observe: external_folder_read surfaces signals
                              │
┌─────────────────────────────────────────────────────────────────┐
│  OBSERVATION LAYER (Deep Agent v2 observe node)                │
│  - external_folder_read MCP tool (Spec 2 step 4)               │
│  - Reads .md, .py, .json, .csv from allowlisted roots          │
│  - external_roots.yaml gates access                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Schema Additions (locked)

### Spec 1 — `src/contracts/`

```python
# src/contracts/common.py
PaeCyclePhase = Literal["plan", "adjust", "evaluate"]
PlanTier = Literal["SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY"]
VectorKey = Literal["passion", "skill", "market", "revenue", "course"]

# src/contracts/base.py (new)
class BasePlanContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: UEID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=3000)
    tier: PlanTier
    parent_ueid: UEID | None = None
    related_ueids: list[UEID] = []
    horizon_days: int | None = Field(default=None, ge=1, le=7300)
    ikigai_vectors: list[VectorKey] = []
    pae_cycle_phase: PaeCyclePhase = "plan"
    pae_tier: PlanTier
    tags: list[str] = []
    custom: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    actor: Literal["user", "agent", "system"] = "user"  # NEW

    @field_validator("ikigai_vectors", mode="after")
    @classmethod
    def _subset_of_parent(cls, v, info):
        parent_ueid = info.data.get("parent_ueid")
        if parent_ueid is None:
            return v  # SONHO-level, no parent check
        parent = load_by_ueid(parent_ueid)  # registry lookup
        if not set(v).issubset(set(parent.ikigai_vectors)):
            raise ValueError(
                f"ikigai_vectors {v} not subset of parent {parent.ikigai_vectors}"
            )
        return v

# src/contracts/sonho.py
class Sonho(BasePlanContract):
    motivation: str
    success_metric: str
    core_values: list[str] = []

# src/contracts/objetivo.py
class Objetivo(BasePlanContract):
    key_results: list[str] = []
    progress_pct: float = Field(ge=0.0, le=100.0, default=0.0)

# src/contracts/meta.py
class Meta(BasePlanContract):
    success_metrics: list[str] = []
    review_frequency_days: int = 7

# src/contracts/projeto.py
class Projeto(BasePlanContract):
    tech_stack: list[str] = []
    repo_url: str | None = None
    target_revenue_brl: float = 0.0
    actual_revenue_brl: float = 0.0

# src/contracts/entrega.py
class Entrega(BasePlanContract):
    artifact_path: str | None = None
    artifact_type: str = "document"
    is_public: bool = False

# src/contracts/tarefa.py
class Tarefa(BasePlanContract):
    pass  # uses src/contracts/task.py for RICE fields
```

### Spec 1 — `vault_write` actor parameter

```python
# src/ikigai/src/mcp_server/vault.py
def vault_write(
    vault_path: str,
    frontmatter: dict,
    body: str,
    actor: Literal["user", "agent", "system"] = "user",  # NEW
) -> WriteResult:
    ...
```

### Spec 1 — phase transition validator

```python
# src/ikigai/src/ikigai/security/transition_validator.py
def validate_phase_transition(
    entity: BasePlanContract,
    old_cycle_phase: PaeCyclePhase | None,
    new_cycle_phase: PaeCyclePhase,
    actor: Literal["user", "agent", "system"],
) -> None:
    if old_cycle_phase is None:
        return  # creation, no transition
    if entity.tier == "SONHO" and actor != "user":
        raise PermissionError(
            f"SONHO phase transitions require actor=user (got {actor})"
        )
    # META, OBJETIVO, PROJETO, ENTREGA, TAREFA accept any actor
```

### Spec 2 — `external_folder_read` MCP tool

```python
# src/ikigai/src/mcp_server/external_folder_tools.py
@mcp.tool()
def external_folder_read(root_prefix: str, pattern: str) -> list[str]:
    """Read files matching pattern from allowlisted root. Returns list of file contents."""
    allowlist = load_external_roots_allowlist()
    if root_prefix not in allowlist.allowed_roots:
        raise PermissionError(f"Root not in allowlist: {root_prefix}")
    # path-traversal guard (mirror vault_write.py:70-71)
    ...
```

```yaml
# src/ikigai/src/ikigai/security/external_roots.yaml
allowed_roots:
  - "C:\\Users\\mathe\\code_space\\orchestration\\value-factory\\case-studies\\byd-camacari-2025-2027"
  - "C:\\Users\\mathe\\code_space\\HSK"
  - "G:\\Other computers\\My Laptop\\notas_estudo\\2_projeto\\immigration-research\\china-research"
  - "C:\\Users\\mathe\\code_space\\job_hunter"
```

### Spec 3 — Investigation Queue

```python
# src/ikigai/src/mcp_server/investigation_tools.py
@mcp.tool()
def investigation_enqueue(
    task: str,
    context: str,
    paths_to_scan: list[str] = [],
    priority: Literal["low", "normal", "high"] = "normal",
) -> str:  # returns task_id
    """Enqueue investigation task. Append-only atomic JSON write to data/investigation_queue/."""
    ...

@mcp.tool()
def investigation_status(task_id: str) -> dict: ...

@mcp.tool()
def investigation_complete(
    task_id: str,
    finding: str,
    promote_to_sonho_candidate: bool = False,
) -> dict: ...
```

---

## Drift Invariants (9, executable form)

```python
# src/ikigai/src/ikigai/security/drift_invariants.py
class DriftInvariants:
    @staticmethod
    def check_schema_completeness(entity: BasePlanContract) -> None:
        """Invariant (a): every Sonho/Objetivo/Meta/Projeto/Entrega/Tarefa has all required fields."""
        required = {"ikigai_vectors", "pae_cycle_phase", "pae_tier", "parent_ueid", "tier"}
        for field in required:
            assert getattr(entity, field, None) is not None, f"Missing {field} on {entity.id}"

    @staticmethod
    def check_vector_subset(child: BasePlanContract, parent: BasePlanContract) -> None:
        """Invariant (b): child.ikigai_vectors ⊆ parent.ikigai_vectors."""
        assert set(child.ikigai_vectors).issubset(set(parent.ikigai_vectors)), \
            f"{child.id} vectors {child.ikigai_vectors} not subset of {parent.id} {parent.ikigai_vectors}"

    @staticmethod
    def check_phase_transition(
        entity: BasePlanContract,
        old_phase: PaeCyclePhase | None,
        new_phase: PaeCyclePhase,
        actor: str,
    ) -> None:
        """Invariant (c): SONHO.cycle_phase changes only via actor=user."""
        if old_phase is None or old_phase == new_phase:
            return
        if entity.tier == "SONHO" and actor != "user":
            raise PermissionError(f"SONHO phase transition requires actor=user (got {actor})")

    @staticmethod
    def check_meta_has_projeto(meta: Meta, exception_titles: set[str] = {"B0 hygiene"}) -> None:
        """Invariant (d): every META has ≥1 PROJETO (with B0-style setup exception)."""
        if meta.title in exception_titles:
            return
        projet = load_children_of(meta, tier="PROJETO")
        assert len(projet) >= 1, f"META {meta.id} has no PROJETO children"

    @staticmethod
    def check_pae_dual_fields(entity: BasePlanContract) -> None:
        """Invariant (e): every entity has BOTH pae_cycle_phase AND pae_tier."""
        assert entity.pae_cycle_phase in {"plan", "adjust", "evaluate"}
        assert entity.pae_tier in {"SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY"}

    @staticmethod
    def check_vault_append_only(path: str) -> None:
        """Invariant (f): vault files are append-only (frontmatter patches logged, body replaces logged)."""
        # check audit log shows append-only operations
        ...

    @staticmethod
    def check_vault_write_audit(path: str, actor: str, timestamp: datetime) -> None:
        """Invariant (g): every vault_write audit log includes actor + timestamp + path."""
        ...

    @staticmethod
    def check_investigation_queue_append_only(task_id: str) -> None:
        """Invariant (h): investigation_queue files are append-only, never deleted."""
        ...

    @staticmethod
    def check_external_allowlist(root_prefix: str) -> None:
        """Invariant (i): only paths in external_roots.yaml can be read via external_folder_read."""
        ...
```

---

## Implementation Roadmap

### Spec 1 (Planning Contract) — ~5h
- Step 1: 6 contracts + 3 enums + subset validator + drift detector extension (~1.5h)
- Step 2: de-STUB commit_node + tag_and_persist + actor parameter + transition_validator (~2.5h)
- Step 3: vault templates (sonho/objetivo/meta/projeto) replacing existing placeholders (~1h)

### Spec 2 (MCP + Fork Protocol) — ~4.5h (after Spec 1)
- Step 4: external_folder_read MCP tool + external_roots.yaml (~3h)
- Step 5: plan_create / plan_query / plan_update MCP tools + TaskChange extension (~1.5h)

### Spec 3 (Investigation Queue) — ~3h (parallel with Spec 2 step 4)
- Step 1: data/investigation_queue/ filesystem queue + 3 MCP tools (~1.5h)
- Step 2: drift invariants h+i (~30min)
- Step 3: e2e demo (enqueue → worker consumes → complete) + tests (~1h)

Total: ~12.5h across 3 specs, shippable in ~3 working days.

---

## Verification Plan

```bash
# After Spec 1 ships:
cd C:\Users\mathe\code_space\life-oss\life
uv sync
python -m pytest src/ikigai/tests/test_canonical_scope.py -v
# Expected: 9 invariants PASS (current 5 + 4 new)

python scripts/mcp_inspect.py
# Expected: 12 IKIGAI_TOOLS + 7 fork tools + 3 investigation tools = 22 tools

# Smoke test: write SONHO + OBJETIVO + 5 METAs + 17 PROJETOs as first persisted planning record
python -c "
from src.contracts.sonho import Sonho
from src.ikigai.src.mcp_server.vault import vault_write
sonho = Sonho(title='Ship Algorithmic Life OS v1', ...)
vault_write('vault/ikigai/closing-2026/01-q3-2026/00-sonho/sonho-life-os-v1.md', ..., actor='user')
"
```

```bash
# After Spec 3 ships:
# Investigation flow smoke test:
# 1. Enqueue: investigation_enqueue(task='CSC scholarship 2027 viability', paths_to_scan=[...])
# 2. Worker consumes, calls external_folder_read
# 3. Synthesize finding
# 4. investigation_complete(task_id, finding, promote_to_sonho_candidate=False)
# 5. Verify audit log shows append-only chain
```

---

## Open Items (deferred per design)

1. **Lifestyle SONHOs** (tech remote job, China immigration) — enabled post-Spec 2 via `plan_create` MCP tool when user is ready
2. **ENTREGA/TAREFA depth** — currently empty; agent layer may populate in v2 via `decompose` step
3. **Socratic Q1-Q7 answers** — separate user task; can be ingested via `vault_write` to populate SONHO motivation/success_metric
4. **Algorithm gate per `algorithm-gate-system-readiness-not-sonho-2026-08-29`** — respected; no algorithm code added in this design
5. **Vault_placeholders** (`00-sonho/placeholder.md` × Q3+Q4) — replaced by Spec 1 vault templates; STATUS="deferred" banner removed once contract lands

---

## Cross-references

### Memory
- [[master-branch-carro-chefe-2026-08-28]] — carro-chefe canonical (this SONHO is its infra enablement)
- [[backend-phase-reordering-2026-08-28]] — B0-B6 canonical order (this SONHO covers B0-B6)
- [[interfaces-architecture-2026-08-27]] — dual-layer architecture (forks consume, CLI/TUI control)
- [[vault-planning-false-gap-2026-08-28]] — algorithm-defer scope rule respected
- [[pav-as-ikigai-subsystem-2026-08-28]] — PAV as subsystem-extension; build order backend→data→agent→algorithms LAST
- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — gate = system readiness, NOT log counter
- [[algorithm-scope-reframed-2026-08-30]] — IKIGAI = planner, not scoring engine
- [[phase-8-agentic-systems-refactor-complete-2026-09-03]] — Phase 8 SHIPPED, drift detector 5/5 PASS

### Vault files
- `vault/ikigai/closing-2026/02-q4-2026/01-plano-trimestral/deep-agent-build-q4-2026.md` — active plan, becomes OBJETIVO Q4 build
- `vault/ikigai/closing-2026/{01-q3,02-q4}-2026/00-sonho/placeholder.md` — replaced by Spec 1 vault templates
- `vault/ikigai/meta/socratic-interview.md` — Q1-Q7 source for SONHO motivation/success_metric population

### Code paths
- `src/contracts/` — new contracts land here (Spec 1 step 1)
- `src/contracts/common.py` — new enums (Spec 1 step 1)
- `src/contracts/base.py` — new BasePlanContract (Spec 1 step 1)
- `src/ikigai/src/agents/v2/nodes/commit.py` — de-STUB (Spec 1 step 2)
- `src/ikigai/src/agents/v2/nodes/tag_and_persist.py` — new node (Spec 1 step 2)
- `src/ikigai/src/mcp_server/vault.py` — actor parameter (Spec 1 step 2)
- `src/ikigai/src/mcp_server/external_folder_tools.py` — new tool (Spec 2 step 4)
- `src/ikigai/src/mcp_server/investigation_tools.py` — new tools (Spec 3)
- `src/ikigai/src/ikigai/security/external_roots.yaml` — allowlist (Spec 2 step 4)
- `src/ikigai/src/ikigai/security/transition_validator.py` — new file (Spec 1 step 2)
- `src/ikigai/src/ikigai/security/drift_invariants.py` — new file (Spec 1 step 1 + 3)
- `src/ikigai/tests/test_canonical_scope.py` — drift detector extension (all specs)
- `data/investigation_queue/` — new directory (Spec 3)

### Active plan §8 OUT OF SCOPE (preserved)
- 5 IKIGAi vector scoring (P/S/M/R/C) with current → target — DEFERRED (only listed, not weighted)
- Regime thresholds + hysteresis values — DEFERRED
- Q_HE math, 5x3x3 aggregates, weighted scoring — DEFERRED
- Kill conditions with numeric thresholds tied to Q_HE / regime — DEFERRED
- Quarterly bets with IKIGAi-vector-falsification criteria — DEFERRED
- Socratic interview Q1-Q7 vector-anchored horizon answers — DEFERRED (manual task, not algorithm)

---

*Scaffold: SONHO Tree Hybrid Design v1 · 2026-09-03 · 11-round grill session · claude-code interactive*
