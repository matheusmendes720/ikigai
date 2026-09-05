# Meta-Planner Design — Intent-Aware To-Do Layer for the IKIGAI Orchestrator

**Date:** 2026-09-04
**Status:** Proposed (post 5-section grill session, awaiting user review per brainstorming skill step 8)
**Scope:** Spec 4 of the SONHO-Tree series (after Spec 1 Planning Contract / Spec 2 External Folder Access / Spec 3 Investigation Queue). Design only — code deferred to writing-plans skill.

---

## Context

The IKIGAI orchestrator currently routes every `user_request` through a single fast-path graph:

```
user_request → observe → score_vectors → heuristics → balance
              → decompose → plan → tag_and_persist → reflect → commit
```

This is correct for **incidental inputs** (status checks, quick questions) but under-serves the recurring operator pattern:

> *"I want to focus on X this week"*
> *"Help me organize the Y project"*
> *"Decompose Z into this week's tasks"*

Such requests cross **three different layers of data** that today are accessed one-at-a-time with no automatic mapping:

1. **Vault hierarchy** — the 6-level Plan A tree (SONHO → OBJETIVO → META → PROJETO → ENTREGA → TAREFA) with strict subset rules, transition validators, and `vault_write.actor` enforcement (ADR-029, Plan A 2026-09-03)
2. **Memory layer** — cross-cycle recall of prior decisions, SONHO logs, and vault trajectories (ADR-028, B-N12)
3. **External project folders** — pre-SONHO context that lives outside the vault (Plan B `external_folder_read`, `external_roots.yaml` allowlist)

Today, the operator must run `vault_read` → `memory_query` → `external_folder_read` → `vault_write` manually, in that order, with explicit schema lookups at every step. The meta-planner compresses this into a single opt-in intent (`/plan <request>`) that:

- **Classifies** whether the user request is planning-shaped (keyword detection, no LLM)
- **Fetches** the right context across memory + external folders + vault hierarchy
- **Generates** a typed `Proposal` (Pydantic v2 strict) of proposed vault writes + taskdog creates
- **Waits for human approval** before executing (PROPOSTAS only — never auto-write)
- **Executes** via reused infrastructure (ADR-029 `vault_write_wrapper` + W3.6 `taskdog_create_task` Path 1)

This is **Option 2 (feature interna — subgraph paralelo)** from the 5-option grill, approved after comparing against (a) embedding into the existing fast-path, (b) external supervisor layer, (c) LLM-driven PDDL-style planner. The trade-offs and rationale are in §Locked Decisions.

---

## Goal

Add an opt-in meta-planner that:

1. **Classifies** user intent at the entry of every request, with zero LLM cost in the default fast-path
2. **Routes** planning-shaped requests through a parallel subgraph (`meta_plan_subgraph`) that produces a typed `Proposal`
3. **Requires explicit human approval** before any write — never auto-write, never auto-approve
4. **Reuses** all shipped infrastructure: `invoke_skill()` (W3.5/W3.6), `vault_write_wrapper` (ADR-029), `taskdog_create_task` (W3.6 Path 1), `external_folder_read` (Plan B), `recall_memory` (ADR-028)
5. **Preserves** the existing fast-path for incidental inputs (zero regression to the 78/78 PASS baseline)
6. **Enforces** 3 new drift invariants (n, o, p) and integrates with `test_canonical_scope.py`

Out of scope: full autonomous task decomposition (LLM-driven planning), multi-agent collaboration, real-time vault watching, GUI/TUI approval flow.

---

## Architecture (1 paragraph)

The meta-planner is a **3-node subgraph** invoked via `invoke_skill("meta_plan", user_request)` (per ADR-025 skill-binding pattern). The `observe` node gains a 30-LOC keyword-classifier that adds a `plan_intent_hint` to state when a planning-shape is detected, suggesting (in-chat, zero writes) the `/plan` invocation. The subgraph itself is `classify_intent → fetch_context → generate_proposal`, producing a typed `Proposal` (Pydantic v2 strict, ADR-009) with `approval_state="pending"`. Approval happens via in-chat display + CLI flag (`--approve` / `--reject X.field`) and routes through a new `proposal_executor` node that reuses `vault_write_wrapper` (ADR-029) for vault writes and `taskdog_create_task` (W3.6 Path 1) for taskdog writes — zero new write code. SONHO writes (Plan A user-only) are rejected at `generate_proposal` time, never reaching executor. State lives in `MetaPlanStateDict` (subset of `IKIGAiStateDict`) with `proposal`, `proposal_pending`, `approval_state` keys. The entire flow adds 3 new drift invariants (n, o, p) to `test_canonical_scope.py`.

---

## The 6 Locked Decisions

| # | Decision | Source |
|---|----------|--------|
| 1 | **Activation = hybrid**: default `/plan` opt-in + observe-node in-chat hint for planning-shaped requests | 5-option grill §Q1; user chose hybrid |
| 2 | **Position = Option 2 (feature interna)**: subgraph paralelo inside IKIGAI orchestrator, NOT external supervisor | 5-option grill §Q2; user chose feature interna after eval vs Option 3 |
| 3 | **Mode = PROPOSTAS only**: meta-planner never auto-writes; user approves before execution | 5-option grill §Q3 |
| 4 | **Approval UX = in-chat + CLI flags**: `--approve` / `--reject X.field` on `life plan` command | 5-option grill §Q4 |
| 5 | **Approach = A — Minimal vertical slice**: 3 nodes, keyword classifier, executor reuso, ~6-10h | 5-option grill §Q5 (user picked A over B full extraction, C minimal hybrid) |
| 6 | **No new IKIGAI_TOOLS**: meta_plan reuses existing 12 planning tools + ADR-029 wrapper + W3.6 taskdog | ADR-030 R2 + ADR-013 |

---

## Three-Layer Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  FAST-PATH (default — 99% of interactions)                            │
│  user_request → observe → score_vectors → heuristics → balance       │
│                 → decompose → plan → tag_and_persist → reflect →    │
│                 commit                                                 │
│                                                                       │
│  PHASE 8.2 observe gains intent detection (~30 LOC):                  │
│    if classify_intent(user_request).level in ("high", "medium"):     │
│      → state["plan_intent_hint"] = "💡 Detectei intent de planning.  │
│        Use /plan <request> para proposta estruturada."                │
│    else: zero writes, zero proposal                                    │
└─────────────────────────────────────────┬────────────────────────────┘
                                          │
                          /plan <request> (opt-in CLI/skill)
                                          │
┌─────────────────────────────────────────▼────────────────────────────┐
│  META-PLAN SUBGRAPH (new, 3 nodes)                                    │
│                                                                       │
│  1. classify_intent                                                    │
│     signals: high (≥1 high keyword) / medium (≥2 medium) / low        │
│     input:  user_request                                               │
│     output: IntentClassification(level, score)                         │
│                                                                       │
│  2. fetch_context                                                      │
│     reusa: recall_memory (ADR-028 B-N12),                             │
│            external_folder_read (Plan B),                             │
│            scan_hierarchy (vault frontmatter walk)                     │
│     input:  user_request + IntentClassification                        │
│     output: memory_refs + folder_reads + hierarchy_matches             │
│                                                                       │
│  3. generate_proposal                                                  │
│     Pydantic v2 strict Proposal (ADR-009)                              │
│     refuses SONHO writes if actor_required != user (Plan A)            │
│     output: Proposal(operations=[...], approval_state="pending")       │
└─────────────────────────────────────────┬────────────────────────────┘
                                          │
                              In-chat display + --approve/--reject
                                          │
┌─────────────────────────────────────────▼────────────────────────────┐
│  PROPOSAL EXECUTOR (new node — REUSES shipped infra)                  │
│                                                                       │
│  assert state.proposal.approval_state == "approved"  [drift (o)]      │
│  for op in proposal.operations:                                        │
│    if op.op_type == "vault_write":                                     │
│      → wrap_vault_write(actor=op.actor_required, …)  [ADR-029]        │
│    elif op.op_type == "taskdog_create":                                │
│      → taskdog_create_task(title=…, priority=…)        [W3.6 Path 1]  │
│  output: ExecutionReport(proposal_id, ops_completed, status)          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components (Pydantic v2 Strict, ADR-009)

All models are `frozen=True, extra="forbid"`. All 4-part UEIDs per ADR-014 regex.

```python
# src/ikigai/contracts/proposal.py

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from datetime import datetime, date

class IntentClassification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    level: Literal["high", "medium", "low"]
    score: int = Field(ge=0)

class FolderReadOp(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str  # vault path
    excerpt: str
    reason: str

class MemoryRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str  # 4-part UEID
    vault_path: str | None
    relevance_score: float = Field(ge=0.0, le=1.0)

class HierarchyMatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    sonho: str | None = None        # 4-part UEID
    objetivo: str | None = None     # 4-part UEID
    meta: str | None = None         # 4-part UEID
    projeto: str | None = None      # 4-part UEID

class HierarchyContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    matched_sonho: str | None
    matched_objetivo: str | None
    matched_meta: str | None
    matched_projeto: str | None

class VaultWriteOp(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    vault_path: str
    entity_type: Literal["sonho", "objetivo", "meta", "projeto", "entrega", "tarefa"]
    fields: dict[str, Any]   # matches the corresponding Plan A contract
    actor_required: Literal["user", "agent"]  # user for SONHO per Plan A transition_validator
    rationale: str

class TaskdogOp(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    title: str
    priority: Literal["H", "M", "L"]
    due_date: date | None
    project: str | None
    tags: list[str]
    rationale: str

class Traceability(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    memory_refs: list[str]
    folder_reads: list[str]
    adrs_consulted: list[str]

class ProposalOperation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    op_type: Literal["vault_write", "taskdog_create", "data_tasks_append"]
    vault_write: VaultWriteOp | None = None
    taskdog_create: TaskdogOp | None = None

class Proposal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str  # 4-part UEID
    created_at: datetime
    source_request: str
    hierarchy_context: HierarchyContext
    operations: list[ProposalOperation]
    traceability: Traceability
    approval_state: Literal["pending", "approved", "rejected", "rejected_safety", "partial"]
    actor_approving: str | None = None
    approval_timestamp: datetime | None = None

class ExecutionReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    proposal_id: str
    ops_total: int
    ops_completed: int
    ops_failed: int
    status: Literal["ok", "partial", "failed"]
    errors: list[str]
```

### Node contracts

| Node | Input | Output | New code |
|------|-------|--------|----------|
| `observe` (modify) | `IKIGAiStateDict` | + `plan_intent_hint` (str \| None) | +30 LOC keyword classifier |
| `classify_intent` (new) | `user_request: str` | `IntentClassification` | ~50 LOC pure keyword |
| `fetch_context` (new) | `user_request + IntentClassification` | `memory_refs + folder_reads + hierarchy_matches` | ~120 LOC reusing `recall_memory`, `external_folder_read`, `scan_hierarchy` |
| `generate_proposal` (new) | `user_request + ctx` | `Proposal(approval_state="pending")` | ~150 LOC |
| `proposal_executor` (new) | `Proposal(approval_state="approved")` | `ExecutionReport` | ~80 LOC reusing `wrap_vault_write` + `taskdog_create_task` |

### State extension (`MetaPlanStateDict` subset of `IKIGAiStateDict`)

```python
class MetaPlanStateDict(TypedDict, total=False):
    # Reused from IKIGAiStateDict
    user_request: str
    cycle_context: dict[str, Any]
    actor: str
    # New keys
    plan_intent_hint: str | None
    intent_classification: IntentClassification | None
    memory_refs: list[MemoryRef]
    folder_reads: list[FolderReadOp]
    hierarchy_matches: HierarchyMatch | None
    proposal: Proposal | None
    proposal_pending: bool
    execution_report: ExecutionReport | None
```

---

## Data Flow + Error Handling

### Happy path (intent = high)

```
/plan "quero focar em entrega E1 essa semana"
  → classify_intent: level=high, score=3
  → fetch_context:
       memory_refs = recall_memory(...) → 3 refs
       folder_reads = external_folder_read(...) → 2 paths
       hierarchy_matches = scan_hierarchy(...) → matched_meta=M01
  → generate_proposal:
       operations = [
         ProposalOperation(vault_write={...E1 fields...}),
         ProposalOperation(taskdog_create={...T1, T2...}),
       ]
       approval_state = "pending"
  → In-chat display:
       "📋 Proposta gerada (UEID: prop:abc123:01:0001):
        • Criar Entrega [E1] em vault/ikigai/closing-2026/...
        • Criar tarefa taskdog [T1, T2]
        → Aprovar? (--approve / --reject X.field)"
  → user: --approve
  → proposal_executor:
       wrap_vault_write(...) [ADR-029 wrapper]
       taskdog_create_task(...) [W3.6 Path 1]
       → ExecutionReport(ops_total=3, ops_completed=3, status="ok")
  → state.execution_report populated
  → graph returns to fast-path commit
```

### Intent = low (default fast-path unchanged)

```
/plan "que horas são?"
  → classify_intent: level=low, score=0
  → 3 nodes skipped, no Proposal generated
  → in-chat hint: "💡 /plan é para intents de planning estruturado"
  → ZERO writes, ZERO proposals
```

### Error matrix

| Case | Detection | Response |
|------|-----------|----------|
| `--approve` before Proposal exists | `state.proposal is None` | Error: "❌ Nenhuma proposta pendente. Use `/plan <request>` primeiro." |
| Multiple `--approve` (state not pending) | `state.proposal.approval_state != "pending"` | Error: "⚠️ Proposta já {approved/rejected}. Use `/plan <new>` para nova." |
| Memory recall timeout (>5s) | `recall_memory` raises `TimeoutError` | Fallback: skip `memory_refs`, log warning, proceed with `folder_reads` only |
| Folder read denied (Plan B) | `external_folder_read` raises `AccessDenied` | Operation removed from Proposal with note: "❌ Acesso negado: {path}. Proposta ajustada." |
| Vault write killed (ADR-029) | `wrap_vault_write` raises `KillSwitchActive` | Proposal auto-rejected: `approval_state="rejected_safety"`; audit log entry |
| Taskdog subprocess fails (Path 1) | `taskdog_create_task` raises | Operation marked `partial_failure`; `ExecutionReport.status="partial"`; user sees "⚠️ 2/3 ops succeeded" |
| Hierarchy match ambiguous | `scan_hierarchy` returns >1 SONHO/OBJETIVO match | Proposal `ambiguity_warning=True`; user must `--select-sonho <ueid>` before approve |
| SONHO write requested (Plan A user-only) | `op.vault_write.entity_type == "sonho"` + `actor_required == "agent"` | Proposal rejected at `generate_proposal`: "❌ SONHO writes requerem actor=user (Plan A transition_validator)" |

### Approval state machine

```
              pending
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
   approved  rejected  rejected_safety
   (--approve) (--reject)  (ADR-029 kill switch)
       │        │
       ▼        ▼
   executed  proposal_void
```

`rejected_safety` is terminal — user sees the kill switch explanation and must open a new Proposal.

### Timeout budget

| Operation | Timeout | Fallback |
|-----------|---------|----------|
| `classify_intent` | <1ms (pure keyword) | n/a |
| `fetch_context.memory` | 5s | skip memory, proceed |
| `fetch_context.folder` | 10s/path | skip that path |
| `generate_proposal` | 30s | error "LLM timeout — reformule request" |
| `proposal_executor.vault_write` | 15s/op | ADR-029 wrapper rate limit |
| `proposal_executor.taskdog` | 30s/op | mark partial_failure |

Total budget `/plan <request>` → approval: ~60s p99.

---

## Testing Strategy

### Pyramid

```
E2E (2 tests)         ~1h     CLI /plan end-to-end + approval flow
Integration (8-12)    ~3h     subgraph + executor + drift + memory fallback
Unit (20-30)          ~2h     classifier, schemas, approval FSM
Total: ~6h parallel to impl.
```

### Unit tests (`src/ikigai/tests/test_meta_plan_unit.py`)

| Test | Asserts |
|------|---------|
| `test_classify_intent_high_keywords` | "quero focar em X essa semana" → level="high" |
| `test_classify_intent_medium_keywords` | "qual seria o próximo passo" → level="medium" |
| `test_classify_intent_low_default` | "que horas são" → level="low" |
| `test_classify_intent_case_insensitive` | "QUERO FOCAR" matches high |
| `test_classify_intent_score_threshold` | 1 high + 0 medium → high; 0 high + 2 medium → medium |
| `test_proposal_frozen` | mutating `Proposal.id` raises `ValidationError` (ADR-009) |
| `test_proposal_extra_forbid` | extra field raises `ValidationError` |
| `test_proposal_vault_write_requires_actor` | `actor_required` must be `user`/`agent` enum |
| `test_proposal_sonho_user_only` | `entity_type=sonho + actor_required=agent` → rejected at generate |
| `test_proposal_traceability_required` | empty `traceability` lists → validation error |
| `test_approval_state_transitions` | pending → approved/rejected allowed; approved → pending rejected |
| `test_rejected_safety_is_terminal` | cannot transition from `rejected_safety` |

Target: 100% branch coverage on `classify_intent` + `Proposal` + approval FSM.

### Integration tests (`src/ikigai/tests/test_meta_plan_integration.py`)

| Test | Mock | Asserts |
|------|------|---------|
| `test_fetch_context_memory_timeout_fallback` | `recall_memory` raises `TimeoutError` | `folder_reads` proceed; warning logged |
| `test_fetch_context_folder_access_denied` | `external_folder_read` raises `AccessDenied` | op removed; warning in Proposal |
| `test_proposal_executor_uses_vault_wrapper` | spy `wrap_vault_write` | wrapper called, not raw `vault_write` |
| `test_proposal_executor_uses_taskdog_path1` | spy `taskdog_create_task` | Path 1 invoked |
| `test_proposal_executor_partial_failure` | `taskdog` raises | `ExecutionReport.status="partial"` |
| `test_proposal_executor_kill_switch_blocks` | `wrap_vault_write` raises `KillSwitchActive` | `state.proposal.approval_state="rejected_safety"` |
| `test_hierarchy_match_ambiguous_warning` | `scan_hierarchy` returns 2+ matches | `ambiguity_warning=True` |
| `test_invoke_skill_meta_plan_wires_subgraph` | `invoke_skill("meta_plan")` | subgraph entered; `state.proposal` populated |

### E2E (`interfaces/cli/tests/test_meta_plan_e2e.py`)

| Test | Scenario |
|------|----------|
| `test_cli_plan_happy_path` | `life plan "quero focar em X"` → Proposal displayed → `--approve` → vault + taskdog writes happen → audit log entry |
| `test_cli_plan_reject_field` | `life plan ...` → `--reject field=priority` → Proposal amended → re-displayed |

### Drift invariants (additions to `test_canonical_scope.py`)

```python
def test_meta_plan_no_direct_vault_writes():  # invariant (n)
    """No node in meta_plan_subgraph calls vault_write directly.
    All writes route through proposal_executor → wrap_vault_write (ADR-029)."""
    nodes = glob("src/ikigai/src/agents/v2/nodes/meta_plan/*.py")
    for node in nodes:
        content = open(node).read()
        assert "vault_write(" not in content or "wrap_vault_write" in content

def test_meta_plan_approval_required_for_writes():  # invariant (o)
    """proposal_executor rejects state.proposal.approval_state != 'approved'."""
    source = open("src/ikigai/src/agents/v2/nodes/proposal_executor.py").read()
    assert "assert state.proposal.approval_state == 'approved'" in source

def test_meta_plan_pydantic_v2_strict():  # invariant (p)
    """All proposal-related models are frozen=True, extra='forbid'."""
    from ikigai.contracts.proposal import Proposal, VaultWriteOp, TaskdogOp
    for model in [Proposal, VaultWriteOp, TaskdogOp]:
        config = model.model_config
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
```

Drift detector grows from current baseline (29 functions in `test_canonical_scope.py`, letter-labeled a-m across Waves 3/4/5.1/5.2) to **+3 invariants** (n, o, p) for meta-planner safety.

### Coverage + CI gates

- **pytest** must pass: existing 78/78 + new ~30 tests = ~108/108
- **mypy src/** must remain clean (Pydantic v2 strict = 0 type errors)
- **ruff check** + **ruff format --check** clean
- **Drift invariants** all PASS (current baseline + new n, o, p)
- **No new IKIGAI_TOOLS** (ADR-030 R2) — meta_plan uses existing tools only
- **No new `requirements.txt` deps** — uses `pydantic`, `re` stdlib only

---

## Effort Estimate

| Component | Effort |
|-----------|--------|
| ADR-031 (this design promoted to ADR) | 2-3h |
| `src/ikigai/contracts/proposal.py` (12 models) | 1-2h |
| `nodes/observe.py` intent detection (+30 LOC) | 1h |
| `nodes/meta_plan/classify_intent.py` | 1h |
| `nodes/meta_plan/fetch_context.py` | 2h |
| `nodes/meta_plan/generate_proposal.py` | 2h |
| `nodes/proposal_executor.py` | 1-2h |
| Tests (unit + integration + E2E + drift) | 6h |
| Wire `invoke_skill("meta_plan", ...)` in `subgraph.py` | 1h |
| CLI `life plan` command (Typer, with --approve/--reject) | 2h |
| **Total** | **~19-22h** |

Ship as Wave 5.X (between W5.2 done and W5.3 next), parallel to W3 hygiene wave. Gated on user #11 4-master review acceptance (Wave 4 ship gate, currently in flight per `wave-4-ship-complete-2026-09-04`).

---

## Out-of-scope (explicit)

- **Auto-approval** of proposals — PROPOSTAS only by Decision #3
- **Multi-agent collaboration** inside `/plan` — meta_plan is single-agent
- **Real-time vault watch** during `generate_proposal` — read-once only
- **Proposal versioning** — Proposal v1 only, no `parent_proposal_id`
- **GUI/TUI approval flow** — in-chat + CLI `--approve`/`--reject` only
- **New IKIGAI_TOOLS** — forbidden by ADR-030 R2
- **Storage of rejected proposals** — Proposal lives only in subgraph state; audit via ADR-029 wrapper already covers writes
- **Multi-language keyword classifier** — PT-BR + EN only (vault is bilíngue, estrategics are PT-BR); locale selector = YAGNI
- **Batch `/plan <req1> <req2> ...`** — one request per call (clarity for approval UX)

---

## References

### ADRs

- **ADR-009** — Pydantic v2 strict (`frozen=True, extra="forbid"`) → used for all Proposal models
- **ADR-013** — Canonical scope discipline (planner-only) → meta_plan = planner, never executes math/policy
- **ADR-014** — UEID 4-part canonical format → all UEIDs in Proposal contracts
- **ADR-019** — QHE constants → prompt-template pattern → meta_plan reads algorithm_constants.json only
- **ADR-025** — Skill binding mechanism → `invoke_skill("meta_plan", ...)` is the entry point
- **ADR-026** — Sub-agent dispatch protocol → meta_plan may dispatch sub-agents for proposal generation (B-N10 node reuse)
- **ADR-027** — Stateful subgraph strategy → `meta_plan_subgraph` follows the same pattern
- **ADR-028** — Memory layer across cycles → `recall_memory` for context fetch
- **ADR-029** — Kill switch + review queue + `vault_write_wrapper` → ALL vault writes route through wrapper
- **ADR-030** — Empirical algorithm tuning → R2 forbids new IKIGAI_TOOLS, R6 drift verification

### Plans

- **Plan A — SONHO Tree Planning Contract** (2026-09-03) → 6-level hierarchy, `vault_write.actor`, transition_validator SONHO.user-only
- **Plan B — External Folder Access** (2026-09-03) → `external_folder_read`, `external_roots.yaml`, drift invariant (i)
- **Plan C — Investigation Queue** (documentation-only 2026-09-03) → NOT used here; `data/investigation_queue/` not implemented; defer to follow-up

### Wave 3 / Wave 5 artifacts

- W3.5 invoke_skill daily wiring → `invoke_skill` mechanism
- W3.6 CLI wrapper → taskdog Path 1 (canonical), CLI dispatch pattern
- W3.7 stale NODES assertion drift fix → drift invariant hygiene
- W3.8 E2E smoke → CLI integration test pattern
- W5.1 ADR-029 kill switch → wrapper gate
- W5.2 ADR-030 algorithm tuning → R2/R6 enforcement

### Specs (companion)

- `docs/superpowers/specs/2026-09-03-sonho-tree-hybrid-design.md` — Plan A spec (6-level hierarchy, 12 locked decisions)
- `docs/superpowers/specs/2026-09-04-task-breakdown.md` — 47 backend tasks + 25 frontend tasks
- `docs/superpowers/specs/2026-09-04-dcode-harness-PLAN.md` — dcode-harness roadmap

### Memory (cross-references)

- `wave-4-ship-complete-2026-09-04` — Wave 4 SHIP-COMPLETE gates Wave 5
- `wave-5-ship-complete-2026-09-04` — Wave 5 partial 3/15 as of 2026-09-04
- `roadmap-2026-09-04-harness-mvp` — dcode-harness MVP roadmap
- `w3-followups-hygiene-wave-timing` — W6.X hygiene wave sequencing

---

## Open Decisions (your call before plan)

1. **Persistência do Proposal?** Default = in-memory only (audit via ADR-029 wrapper). If you want rejected-proposal history, that's a follow-up spec.
2. **Multi-language keywords?** Default = PT-BR + EN. Locale selector = YAGNI for now.
3. **`/plan` em batch?** Default = 1 request per call (clarity for approval UX).
4. **Should this ship as ADR-031** alongside implementation, or wait for impl-ship feedback to write ADR-031? Default: write ADR-031a (design + intent) before code, promote to ADR-031 after impl-reviewer APPROVED (W5.1 precedent at `59dd445`).

---

*Meta-Planner Design Spec — Proposed 2026-09-04 — awaiting user review*
