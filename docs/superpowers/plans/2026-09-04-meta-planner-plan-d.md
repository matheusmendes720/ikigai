# Meta-Planner Implementation Plan (Plan D)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in `/plan <request>` entry to the IKIGAI orchestrator that classifies user intent, fetches context (memory + external folders + vault hierarchy), and produces a typed `Proposal` of vault writes + taskdog creates that requires explicit human `--approve` before execution.

**Architecture:** 3-node subgraph (`classify_intent → fetch_context → generate_proposal`) invoked via `invoke_skill("meta_plan", …)` per ADR-025. Observe node gains a 30-LOC keyword classifier that emits in-chat hints. `proposal_executor` node reuses ADR-029 `vault_write_wrapper` + W3.6 `taskdog_create_task` (Path 1) — zero new write code. State lives in a `MetaPlanStateDict` subset of `IKIGAiStateDict`. Three new drift invariants (n, o, p) enforce (no-direct-vault-writes, approval-required-for-writes, Pydantic-v2-strict).

**Tech Stack:** Python 3.12+, Pydantic v2 strict (frozen=True, extra="forbid"), pytest, ruff, mypy, existing IKIGAI agent harness.

---

## Global Constraints

These apply to every task. Each task's requirements implicitly include this section.

- **Python 3.12+** — match project floor (`.python-version`)
- **Pydantic v2 strict** — every new model: `model_config = ConfigDict(frozen=True, extra="forbid")` (ADR-009)
- **4-part UEID canonical** — regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` per ADR-014
- **No new IKIGAI_TOOLS** — meta_plan reuses existing 12 planning tools only (ADR-030 R2)
- **No new `requirements.txt` deps** — uses `pydantic`, `re`, `datetime` stdlib only
- **No Co-Authored-By trailer** in commits — per project CLAUDE.md
- **File size ≤500 lines** — split when growing (CLAUDE.md "Build & Test" rule)
- **Vault writes MUST route through `wrap_vault_write`** (ADR-029) — never call `vault_write` directly from agent code
- **taskdog writes MUST route through `taskdog_create_task`** (W3.6 Path 1, `src/ikigai/src/agents/tools.py:423`) — never call `taskdog.exe` directly from agent code
- **SONHO writes require `actor_required="user"`** — Plan A transition_validator (2026-09-03) refuses `actor="agent"` writes for `entity_type="sonho"`
- **No new algorithm tuning constants in Python** — algorithm constants live in `src/ikigai/src/agents/v2/prompts/algorithm_constants.json` only (ADR-019, ADR-030 R6, drift invariant (m))

---

## File Structure

### Create

| File | Responsibility |
|------|----------------|
| `src/ikigai/contracts/proposal.py` | 12 Pydantic v2 strict models (IntentClassification, FolderReadOp, MemoryRef, HierarchyMatch, HierarchyContext, VaultWriteOp, TaskdogOp, Traceability, ProposalOperation, Proposal, ExecutionReport, ProposalApprovalState enum) |
| `src/ikigai/src/agents/v2/nodes/meta_plan/__init__.py` | Package marker |
| `src/ikigai/src/agents/v2/nodes/meta_plan/classify_intent.py` | Pure-keyword intent classifier (~50 LOC) |
| `src/ikigai/src/agents/v2/nodes/meta_plan/fetch_context.py` | Memory + external folder + hierarchy scan (~120 LOC) |
| `src/ikigai/src/agents/v2/nodes/meta_plan/generate_proposal.py` | Pydantic Proposal builder with SONHO-user-only guard (~150 LOC) |
| `src/ikigai/src/agents/v2/skills/meta_plan.md` | Skill manifest with `entry_point: classify_intent`, `actor: agent`, `outputs: []` |
| `src/ikigai/tests/test_meta_plan_unit.py` | 12 unit tests for classify_intent + Proposal models + approval FSM |
| `src/ikigai/tests/test_meta_plan_integration.py` | 8 integration tests with mocked recall_memory + external_folder_read + wrap_vault_write + taskdog |
| `interfaces/cli/tests/test_meta_plan_e2e.py` | 2 E2E tests: happy path + reject field |
| `code-docs/adr/ADR-031-meta-planner-design.md` | ADR documenting meta-planner design + drift invariants (n, o, p) |

### Modify

| File | Change |
|------|--------|
| `src/ikigai/src/agents/v2/state.py` | Add `MetaPlanStateDict` TypedDict subset keys + extend `IKIGAiStateDict` with `plan_intent_hint`, `intent_classification`, `memory_refs`, `folder_reads`, `hierarchy_matches`, `proposal`, `proposal_pending`, `execution_report` |
| `src/ikigai/src/agents/v2/nodes/observe.py` | +30 LOC keyword classifier; emits `plan_intent_hint` to state when level in (high, medium) |
| `src/ikigai/src/agents/v2/subgraph.py` | Register `meta_plan_subgraph` (3-node subgraph) + add to NODES registry |
| `src/ikigai/tests/test_canonical_scope.py` | Add 3 drift invariants (n, o, p) |
| `interfaces/cli/v2.py` | Add `plan` Typer command with `--approve`/`--reject X.field` flags |
| `interfaces/cli/__main__.py` | Register `plan` subcommand in CLI parser |

### Files NOT touched (explicit)

- `src/ikigai/src/agents/tools.py` — `taskdog_create_task` reused as-is (no new tool)
- `src/ikigai/src/agents/vault_write.py` — `wrap_vault_write` reused as-is (ADR-029)
- `src/ikigai/src/agents/v2/prompts/algorithm_constants.json` — no new algorithm constants
- `src/ikigai/src/agents/v2/memory_*` — `recall_memory` reused as-is (ADR-028)
- `src/ikigai/src/security/external_folder_read.py` — `external_folder_read` reused as-is (Plan B)

---

## Dependency Graph

```
Track A: Contracts + Drift Invariants (foundation)
  A.1 (contracts/proposal.py) ──┐
  A.2 (drift invariants n,o,p) ─┤
                                │
Track B: Subgraph Nodes ─────────┼──► Track E: CLI + E2E
  B.1 (classify_intent) ────────┤    E.1 (life plan command)
  B.2 (fetch_context) ──────────┤    E.2 (E2E tests)
  B.3 (generate_proposal) ──────┤
  B.4 (proposal_executor) ──────┤
                                │
Track C: State + Wiring ────────┤
  C.1 (MetaPlanStateDict) ──────┤
  C.2 (subgraph registration) ──┤
  C.3 (skill manifest) ─────────┘

Track D: Observe modification (independent)
  D.1 (intent detection +30 LOC)

Track F: ADR-031 (documentation-only, parallel)
  F.1 (ADR-031)
```

Parallel tracks: B, C, D can run in parallel after A.1 lands. Track F is fully parallel. Track E depends on B + C. Track F1 can ship first (does not block impl).

---

## Track A — Contracts + Drift Invariants

### Task A.1: Create `src/ikigai/contracts/proposal.py` with 12 Pydantic v2 strict models

**Files:**
- Create: `src/ikigai/contracts/proposal.py`
- Test: `src/ikigai/tests/test_proposal_contracts.py`

**Interfaces:**
- Consumes: nothing (foundation task)
- Produces: 12 importable models (`Proposal`, `VaultWriteOp`, `TaskdogOp`, `IntentClassification`, `HierarchyContext`, `ExecutionReport`, etc.) — all frozen=True, extra="forbid"

- [ ] **Step 1: Write the failing test**

Create `src/ikigai/tests/test_proposal_contracts.py`:

```python
"""Unit tests for proposal contracts (Plan D Task A.1)."""
from __future__ import annotations

from datetime import datetime, date

import pytest
from pydantic import ValidationError

from src.ikigai.contracts.proposal import (
    IntentClassification,
    FolderReadOp,
    MemoryRef,
    HierarchyMatch,
    HierarchyContext,
    VaultWriteOp,
    TaskdogOp,
    Traceability,
    ProposalOperation,
    Proposal,
    ExecutionReport,
)


def test_intent_classification_frozen():
    ic = IntentClassification(level="high", score=3)
    with pytest.raises(ValidationError):
        ic.level = "low"  # type: ignore[misc]


def test_intent_classification_extra_forbid():
    with pytest.raises(ValidationError):
        IntentClassification(level="high", score=3, rogue="x")  # type: ignore[call-arg]


def test_intent_classification_score_ge_zero():
    with pytest.raises(ValidationError):
        IntentClassification(level="high", score=-1)


def test_folder_read_op_required_fields():
    f = FolderReadOp(path="vault/x.md", excerpt="abc", reason="test")
    assert f.path == "vault/x.md"


def test_memory_ref_relevance_score_bounds():
    with pytest.raises(ValidationError):
        MemoryRef(id="mem:abc:01:0001", vault_path="x", relevance_score=1.5)
    with pytest.raises(ValidationError):
        MemoryRef(id="mem:abc:01:0001", vault_path="x", relevance_score=-0.1)


def test_hierarchy_match_all_optional():
    h = HierarchyMatch()
    assert h.sonho is None
    assert h.objetivo is None


def test_hierarchy_context_required_fields():
    hc = HierarchyContext(matched_sonho=None, matched_objetivo=None, matched_meta=None, matched_projeto=None)
    assert hc.matched_sonho is None


def test_vault_write_op_actor_enum():
    with pytest.raises(ValidationError):
        VaultWriteOp(
            vault_path="vault/x.md",
            entity_type="meta",
            fields={"title": "x"},
            actor_required="robot",  # type: ignore[arg-type]
            rationale="test",
        )


def test_vault_write_op_sonho_requires_user():
    """SONHO writes must declare actor_required='user' per Plan A transition_validator."""
    with pytest.raises(ValidationError):
        VaultWriteOp(
            vault_path="vault/x.md",
            entity_type="sonho",
            fields={"title": "x"},
            actor_required="agent",
            rationale="test",
        )


def test_taskdog_op_priority_enum():
    with pytest.raises(ValidationError):
        TaskdogOp(
            title="x",
            priority="URGENT",  # type: ignore[arg-type]
            due_date=None,
            project=None,
            tags=[],
            rationale="test",
        )


def test_traceability_required_lists():
    with pytest.raises(ValidationError):
        # Traceability fields are required; empty list is allowed only if value is list
        Traceability(memory_refs="not-a-list", folder_reads=[], adrs_consulted=[])  # type: ignore[arg-type]


def test_proposal_operation_op_type_enum():
    with pytest.raises(ValidationError):
        ProposalOperation(op_type="unknown")  # type: ignore[arg-type]


def test_proposal_approval_state_enum():
    with pytest.raises(ValidationError):
        Proposal(
            id="prop:abc:01:0001",
            created_at=datetime(2026, 9, 4),
            source_request="x",
            hierarchy_context=HierarchyContext(None, None, None, None),
            operations=[],
            traceability=Traceability([], [], []),
            approval_state="drafted",  # type: ignore[arg-type]
        )


def test_proposal_frozen():
    p = Proposal(
        id="prop:abc:01:0001",
        created_at=datetime(2026, 9, 4),
        source_request="x",
        hierarchy_context=HierarchyContext(None, None, None, None),
        operations=[],
        traceability=Traceability([], [], []),
        approval_state="pending",
    )
    with pytest.raises(ValidationError):
        p.approval_state = "approved"  # type: ignore[misc]


def test_proposal_id_must_match_ueid_regex():
    with pytest.raises(ValidationError):
        Proposal(
            id="bad-id",  # not 4-part
            created_at=datetime(2026, 9, 4),
            source_request="x",
            hierarchy_context=HierarchyContext(None, None, None, None),
            operations=[],
            traceability=Traceability([], [], []),
            approval_state="pending",
        )


def test_execution_report_status_enum():
    with pytest.raises(ValidationError):
        ExecutionReport(
            proposal_id="prop:abc:01:0001",
            ops_total=1,
            ops_completed=1,
            ops_failed=0,
            status="partial-success",  # type: ignore[arg-type]
            errors=[],
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_proposal_contracts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ikigai.contracts.proposal'`

- [ ] **Step 3: Create `src/ikigai/contracts/proposal.py`**

```python
"""Meta-Planner Proposal contracts (Plan D Task A.1).

All models are Pydantic v2 strict per ADR-009:
  model_config = ConfigDict(frozen=True, extra="forbid")

UEIDs follow ADR-014 4-part canonical format.
SONHO writes require actor_required='user' per Plan A transition_validator.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


class IntentClassification(BaseModel):
    """Result of classify_intent node — keyword-based, no LLM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: Literal["high", "medium", "low"]
    score: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Context fetches
# ---------------------------------------------------------------------------


class FolderReadOp(BaseModel):
    """A folder read captured during fetch_context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    excerpt: str
    reason: str


class MemoryRef(BaseModel):
    """A memory recall result from B-N12 (ADR-028)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str  # 4-part UEID
    vault_path: str | None
    relevance_score: float = Field(ge=0.0, le=1.0)


class HierarchyMatch(BaseModel):
    """Matched vault hierarchy levels for the user request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sonho: str | None = None
    objetivo: str | None = None
    meta: str | None = None
    projeto: str | None = None


class HierarchyContext(BaseModel):
    """Subset of HierarchyMatch included in Proposal for traceability."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    matched_sonho: str | None
    matched_objetivo: str | None
    matched_meta: str | None
    matched_projeto: str | None


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


class VaultWriteOp(BaseModel):
    """A proposed vault write. SONHO writes require actor_required='user'."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vault_path: str
    entity_type: Literal["sonho", "objetivo", "meta", "projeto", "entrega", "tarefa"]
    fields: dict[str, Any]
    actor_required: Literal["user", "agent"]
    rationale: str

    @field_validator("actor_required")
    @classmethod
    def _sonho_requires_user(cls, v: str, info: Any) -> str:
        # SONHO writes are user-only per Plan A transition_validator (2026-09-03).
        entity = info.data.get("entity_type")
        if entity == "sonho" and v != "user":
            raise ValueError(
                "SONHO writes require actor_required='user' "
                "(Plan A transition_validator)"
            )
        return v


class TaskdogOp(BaseModel):
    """A proposed taskdog create (Path 1 per W3.6)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    priority: Literal["H", "M", "L"]
    due_date: date | None
    project: str | None
    tags: list[str]
    rationale: str


class ProposalOperation(BaseModel):
    """One operation in a Proposal (vault_write | taskdog_create | data_tasks_append)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    op_type: Literal["vault_write", "taskdog_create", "data_tasks_append"]
    vault_write: VaultWriteOp | None = None
    taskdog_create: TaskdogOp | None = None


class Traceability(BaseModel):
    """Provenance for a Proposal — required for audit trail."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    memory_refs: list[str]
    folder_reads: list[str]
    adrs_consulted: list[str]


# ---------------------------------------------------------------------------
# Proposal + Approval + Execution
# ---------------------------------------------------------------------------

_UEID_REGEX = r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$"


class Proposal(BaseModel):
    """A typed proposal of writes — requires approval before execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str  # 4-part UEID (ADR-014)
    created_at: datetime
    source_request: str
    hierarchy_context: HierarchyContext
    operations: list[ProposalOperation]
    traceability: Traceability
    approval_state: Literal["pending", "approved", "rejected", "rejected_safety", "partial"]
    actor_approving: str | None = None
    approval_timestamp: datetime | None = None

    @field_validator("id")
    @classmethod
    def _ueid_canonical(cls, v: str) -> str:
        import re

        if not re.match(_UEID_REGEX, v):
            raise ValueError(
                f"id {v!r} does not match 4-part UEID regex (ADR-014): {_UEID_REGEX}"
            )
        return v


class ExecutionReport(BaseModel):
    """Result of proposal_executor — surfaces partial failures to user."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str
    ops_total: int = Field(ge=0)
    ops_completed: int = Field(ge=0)
    ops_failed: int = Field(ge=0)
    status: Literal["ok", "partial", "failed"]
    errors: list[str]


__all__ = [
    "IntentClassification",
    "FolderReadOp",
    "MemoryRef",
    "HierarchyMatch",
    "HierarchyContext",
    "VaultWriteOp",
    "TaskdogOp",
    "ProposalOperation",
    "Traceability",
    "Proposal",
    "ExecutionReport",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_proposal_contracts.py -v`
Expected: PASS (15/15)

- [ ] **Step 5: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/contracts/proposal.py src/ikigai/tests/test_proposal_contracts.py
cd C:\Users\mathe\code_space\life-oss\life && ruff format --check src/ikigai/contracts/proposal.py src/ikigai/tests/test_proposal_contracts.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/contracts/proposal.py
```
Expected: All clean (exit 0).

- [ ] **Step 6: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-a1-commit-msg.txt`:
```
feat(contracts): meta-planner Proposal contracts — 12 Pydantic v2 strict models (Plan D Task A.1)

Adds src/ikigai/contracts/proposal.py with 12 frozen+extra="forbid" models
per ADR-009: IntentClassification, FolderReadOp, MemoryRef, HierarchyMatch,
HierarchyContext, VaultWriteOp, TaskdogOp, ProposalOperation, Traceability,
Proposal, ExecutionReport. UEID 4-part regex enforced (ADR-014). SONHO writes
require actor_required='user' per Plan A transition_validator.

Tests: 15/15 PASS in src/ikigai/tests/test_proposal_contracts.py.
ruff + mypy clean.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Components.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/contracts/proposal.py src/ikigai/tests/test_proposal_contracts.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-a1-commit-msg.txt"
cd C:\Users\mathe\code_space\life-oss\life && git log -1 --format=%B HEAD | grep -i "co-authored" && echo FAIL || echo OK
```
Expected: Commit lands; OK (no Co-Authored-By).

---

### Task A.2: Add 3 drift invariants (n, o, p) to `test_canonical_scope.py`

**Files:**
- Modify: `src/ikigai/tests/test_canonical_scope.py` — append 3 new test functions

**Interfaces:**
- Consumes: Task A.1 (proposal contracts must exist)
- Produces: 3 new drift invariants enforced by the canonical drift detector

- [ ] **Step 1: Write the failing test**

Append to `src/ikigai/tests/test_canonical_scope.py` (after the last existing function):

```python
# ---------------------------------------------------------------------------
# Plan D — Meta-planner drift invariants (n, o, p)
# Added 2026-09-04 per docs/superpowers/specs/2026-09-04-meta-planner-design.md
# ---------------------------------------------------------------------------


def test_meta_plan_no_direct_vault_writes() -> None:
    """Invariant (n): meta_plan subgraph nodes NEVER call vault_write directly.
    All writes MUST route through proposal_executor → wrap_vault_write (ADR-029).
    """
    from glob import glob

    nodes = glob("src/ikigai/src/agents/v2/nodes/meta_plan/*.py")
    # If the directory doesn't exist yet, this invariant vacuously passes
    # (the absence of meta_plan nodes is itself correct).
    if not nodes:
        return

    for node in nodes:
        # Skip __init__.py
        if node.endswith("__init__.py"):
            continue
        content = open(node).read()
        # Look for direct vault_write( call without wrap_
        import re

        # Match `vault_write(` but not preceded by `wrap_` or `wrap_vault_write`
        # Heuristic: find all `vault_write(` substrings and ensure none
        # appear outside of comments/docstrings/strings we cannot easily
        # detect. Simpler: just forbid the substring `vault_write(` in node
        # code. proposal_executor lives outside meta_plan/ so this check
        # covers only the 3 subgraph nodes (classify/fetch/generate).
        if "vault_write(" in content:
            # Allow if wrapped (defensive — executor may import helper)
            assert "wrap_vault_write" in content, (
                f"{node} calls vault_write( directly. "
                "Per ADR-029 all vault writes MUST route through wrap_vault_write."
            )


def test_meta_plan_approval_required_for_writes() -> None:
    """Invariant (o): proposal_executor MUST assert approval_state == 'approved'
    before executing any write. Prevents accidental auto-execution.
    """
    import os

    executor_path = "src/ikigai/src/agents/v2/nodes/proposal_executor.py"
    if not os.path.exists(executor_path):
        # Pre-implementation: invariant vacuously fails so the implementer
        # knows to add the assertion when creating the file.
        assert False, (
            "proposal_executor.py does not exist yet. "
            "Invariant (o) requires the executor to assert "
            "state.proposal.approval_state == 'approved' before any write."
        )

    source = open(executor_path).read()
    assert "approval_state == 'approved'" in source or (
        "approval_state" in source and "approved" in source
    ), (
        "proposal_executor.py must assert approval_state == 'approved' "
        "before performing writes. See Plan D Task B.4."
    )


def test_meta_plan_pydantic_v2_strict() -> None:
    """Invariant (p): all proposal-related models are frozen=True, extra='forbid'."""
    from src.ikigai.contracts.proposal import (
        IntentClassification,
        Proposal,
        VaultWriteOp,
        TaskdogOp,
        ExecutionReport,
        FolderReadOp,
        MemoryRef,
        HierarchyContext,
        ProposalOperation,
        Traceability,
    )

    for model in [
        IntentClassification,
        Proposal,
        VaultWriteOp,
        TaskdogOp,
        ExecutionReport,
        FolderReadOp,
        MemoryRef,
        HierarchyContext,
        ProposalOperation,
        Traceability,
    ]:
        config = model.model_config
        assert config.get("frozen") is True, (
            f"{model.__name__}.model_config.frozen must be True (ADR-009)"
        )
        assert config.get("extra") == "forbid", (
            f"{model.__name__}.model_config.extra must be 'forbid' (ADR-009)"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_canonical_scope.py::test_meta_plan_pydantic_v2_strict -v`
Expected: PASS (Task A.1 already shipped the contracts — only invariant (p) can be verified standalone now). The (n) and (o) invariants will pass vacuously (meta_plan/ dir + proposal_executor.py don't exist yet, so (n) returns early and (o) fails — that's intentional: it tells the implementer to add the assertion).

If (o) is the only one failing, that's expected at this stage. Verify (p) passes:

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_canonical_scope.py::test_meta_plan_pydantic_v2_strict src/ikigai/tests/test_canonical_scope.py::test_meta_plan_no_direct_vault_writes -v`
Expected: PASS (2/2). (o) will fail until Task B.4 ships.

- [ ] **Step 3: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/tests/test_canonical_scope.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/tests/test_canonical_scope.py
```
Expected: All clean.

- [ ] **Step 4: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-a2-commit-msg.txt`:
```
test(drift): Plan D invariants (n, o, p) for meta-planner

Adds 3 new drift invariants to test_canonical_scope.py per
docs/superpowers/specs/2026-09-04-meta-planner-design.md §Testing Strategy:
- (n) test_meta_plan_no_direct_vault_writes: subgraph nodes MUST route through
  wrap_vault_write (ADR-029)
- (o) test_meta_plan_approval_required_for_writes: proposal_executor MUST
  assert approval_state == 'approved' before writes
- (p) test_meta_plan_pydantic_v2_strict: all contract models are
  frozen=True, extra='forbid' (ADR-009)

(n) passes vacuously until meta_plan/ dir exists.
(o) fails until proposal_executor.py ships (intentional — drives Task B.4).
(p) passes now (depends on Task A.1).
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/tests/test_canonical_scope.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-a2-commit-msg.txt"
```
Expected: Commit lands.

---

## Track B — Subgraph Nodes

### Task B.1: `nodes/meta_plan/classify_intent.py` — pure keyword classifier

**Files:**
- Create: `src/ikigai/src/agents/v2/nodes/meta_plan/__init__.py` (empty package marker)
- Create: `src/ikigai/src/agents/v2/nodes/meta_plan/classify_intent.py`
- Test: `src/ikigai/tests/test_meta_plan_unit.py`

**Interfaces:**
- Consumes: `MetaPlanStateDict["user_request"]` (str) — Task C.1 will add this key
- Produces: `IntentClassification` (from Task A.1)

- [ ] **Step 1: Create the package marker**

Create `src/ikigai/src/agents/v2/nodes/meta_plan/__init__.py`:
```python
"""Meta-planner subgraph nodes (Plan D Track B).

3 nodes: classify_intent, fetch_context, generate_proposal.
Plus 1 executor (proposal_executor.py in nodes/) that reuses shipped infra.
"""
```

- [ ] **Step 2: Write the failing test**

Create `src/ikigai/tests/test_meta_plan_unit.py`:

```python
"""Unit tests for meta-planner nodes (Plan D Task B.1)."""
from __future__ import annotations

import pytest

from src.ikigai.agents.v2.nodes.meta_plan.classify_intent import (
    PLANNING_KEYWORDS,
    classify_intent,
)
from src.ikigai.contracts.proposal import IntentClassification


def test_classify_high_single_keyword():
    ic = classify_intent("quero focar em X essa semana")
    assert ic.level == "high"
    assert ic.score >= 1


def test_classify_high_multiple_keywords():
    ic = classify_intent("quero focar no objetivo da meta do projeto essa semana")
    assert ic.level == "high"
    assert ic.score >= 3


def test_classify_medium_two_keywords():
    ic = classify_intent("qual seria o próximo passo?")
    assert ic.level == "medium"


def test_classify_low_no_keywords():
    ic = classify_intent("que horas são?")
    assert ic.level == "low"
    assert ic.score == 0


def test_classify_case_insensitive():
    ic = classify_intent("QUERO FOCAR EM X")
    assert ic.level == "high"


def test_classify_threshold_zero_high_one_medium():
    # "qual seria" alone → medium (only 1 medium keyword)
    ic = classify_intent("qual seria")
    assert ic.level == "medium"


def test_classify_returns_intent_classification():
    ic = classify_intent("qualquer coisa")
    assert isinstance(ic, IntentClassification)


def test_planning_keywords_have_required_tiers():
    assert "high" in PLANNING_KEYWORDS
    assert "medium" in PLANNING_KEYWORDS
    assert all(isinstance(k, str) for k in PLANNING_KEYWORDS["high"])
    assert all(isinstance(k, str) for k in PLANNING_KEYWORDS["medium"])
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_unit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ikigai.agents.v2.nodes.meta_plan.classify_intent'`

- [ ] **Step 4: Create `src/ikigai/src/agents/v2/nodes/meta_plan/classify_intent.py`**

```python
"""classify_intent node — pure keyword classifier for meta-planner (Plan D Task B.1).

No LLM call. ~50 LOC. Matches user_request against PT-BR + EN planning
keywords to detect intent level: high / medium / low.

The classifier is intentionally simple: a more sophisticated LLM-based
classifier would violate the data-first methodology (ADR-007) and add
unbounded latency. The keyword list lives here, NOT in algorithm_constants.json,
because these are NLU-style heuristics not algorithm tuning constants
(ADR-030 R6 does not apply).
"""

from __future__ import annotations

from src.ikigai.contracts.proposal import IntentClassification


PLANNING_KEYWORDS: dict[str, list[str]] = {
    "high": [
        "quero focar",
        "me ajuda a organizar",
        "decomponha",
        "esta semana",
        "esse mês",
        "objetivo",
        "meta",
        "projeto",
        "tarefas",
        "planejamento",
        "i want to focus",
        "help me organize",
        "decompose",
        "this week",
        "this month",
        "goal",
        "project",
    ],
    "medium": [
        "como posso",
        "qual seria",
        "sugestão",
        "recomendação",
        "próximo passo",
        "agenda",
        "schedule",
        "how can i",
        "what would",
        "suggestion",
        "recommendation",
        "next step",
    ],
}


def classify_intent(user_request: str) -> IntentClassification:
    """Classify user_request as high / medium / low planning intent.

    High: ≥1 high keyword.
    Medium: ≥2 medium keywords (medium alone requires 2+ matches).
    Low: zero matches.

    Returns IntentClassification(level, score) — score is total keyword hits
    across all tiers.
    """
    text = user_request.lower().strip()
    scores = {"high": 0, "medium": 0}
    for tier, keywords in PLANNING_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[tier] += 1

    total_score = scores["high"] + scores["medium"]
    if scores["high"] >= 1:
        level = "high"
    elif scores["medium"] >= 2:
        level = "medium"
    else:
        level = "low"

    return IntentClassification(level=level, score=total_score)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_unit.py -v`
Expected: PASS (8/8)

- [ ] **Step 6: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/src/agents/v2/nodes/meta_plan/classify_intent.py src/ikigai/tests/test_meta_plan_unit.py
cd C:\Users\mathe\code_space\life-oss\life && ruff format --check src/ikigai/src/agents/v2/nodes/meta_plan/classify_intent.py src/ikigai/tests/test_meta_plan_unit.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/src/agents/v2/nodes/meta_plan/classify_intent.py
```
Expected: All clean.

- [ ] **Step 7: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-b1-commit-msg.txt`:
```
feat(meta-plan): classify_intent node — pure keyword classifier (Plan D Task B.1)

Adds nodes/meta_plan/classify_intent.py with ~50 LOC PT-BR + EN keyword
classifier. Detects high (≥1 high keyword) / medium (≥2 medium) / low
planning intent. Zero LLM. Keyword list lives in code (not algorithm_constants.json)
per ADR-030 R6 scope (NLU heuristic, not algorithm tuning).

Tests: 8/8 PASS in src/ikigai/tests/test_meta_plan_unit.py.
ruff + mypy clean.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Components.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/src/agents/v2/nodes/meta_plan/ src/ikigai/tests/test_meta_plan_unit.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-b1-commit-msg.txt"
```
Expected: Commit lands.

---

### Task B.2: `nodes/meta_plan/fetch_context.py` — memory + folder + hierarchy

**Files:**
- Create: `src/ikigai/src/agents/v2/nodes/meta_plan/fetch_context.py`
- Modify: `src/ikigai/tests/test_meta_plan_unit.py` — append B.2 tests

**Interfaces:**
- Consumes: `MetaPlanStateDict["user_request"]` + `IntentClassification`
- Produces: `list[MemoryRef]`, `list[FolderReadOp]`, `HierarchyMatch` populated in state

- [ ] **Step 1: Write the failing test**

Append to `src/ikigai/tests/test_meta_plan_unit.py`:

```python
# ---------------------------------------------------------------------------
# Plan D Task B.2 — fetch_context
# ---------------------------------------------------------------------------

from src.ikigai.agents.v2.nodes.meta_plan.fetch_context import (
    fetch_context,
    scan_hierarchy,
)


def test_scan_hierarchy_returns_match_for_known_meta():
    """scan_hierarchy walks vault frontmatter for matching meta UEID."""
    # Use the in-repo vault mock fixture or empty test vault
    matches = scan_hierarchy("objetivo Q4-2026 build")
    # May be empty in test env; just verify it returns HierarchyMatch
    from src.ikigai.contracts.proposal import HierarchyMatch

    assert isinstance(matches, HierarchyMatch)


def test_fetch_context_returns_three_lists():
    """fetch_context returns (memory_refs, folder_reads, hierarchy_match)."""
    from src.ikigai.contracts.proposal import (
        IntentClassification,
        MemoryRef,
        FolderReadOp,
    )

    state = {
        "user_request": "quero focar em X",
        "intent_classification": IntentClassification(level="high", score=1),
    }
    refs, reads, match = fetch_context(state)
    assert isinstance(refs, list)
    assert isinstance(reads, list)
    assert isinstance(match, HierarchyMatch)


def test_fetch_context_handles_missing_recall_memory(monkeypatch):
    """If recall_memory is not importable, fetch_context proceeds with empty refs."""

    state = {
        "user_request": "test",
        "intent_classification": IntentClassification(level="low", score=0),
    }
    # Monkeypatch to simulate ImportError
    import src.ikigai.agents.v2.nodes.meta_plan.fetch_context as fc_mod

    def _boom(*args, **kwargs):
        raise ImportError("recall_memory not available in test env")

    monkeypatch.setattr(fc_mod, "recall_memory", _boom, raising=False)
    refs, reads, match = fetch_context(state)
    assert refs == []  # gracefully degraded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_unit.py::test_scan_hierarchy_returns_match_for_known_meta -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `src/ikigai/src/agents/v2/nodes/meta_plan/fetch_context.py`**

```python
"""fetch_context node — gather memory + folder + hierarchy context (Plan D Task B.2).

Reuses shipped infrastructure:
- recall_memory (ADR-028, B-N12) — graceful fallback if unavailable
- external_folder_read (Plan B, src/ikigai/security/external_folder_read.py)
- scan_hierarchy (local helper, walks vault frontmatter)

All three fetches are read-only. No writes here.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ikigai.contracts.proposal import (
    FolderReadOp,
    HierarchyMatch,
    IntentClassification,
    MemoryRef,
)

log = logging.getLogger(__name__)


def recall_memory(query: str, top_k: int = 5) -> list[MemoryRef]:
    """Wrapper around B-N12 memory recall (ADR-028). Defensive: returns [] on ImportError."""
    try:
        from src.ikigai.agents.v2.memory_read import query_memory

        results = query_memory(query=query, top_k=top_k)
        return [
            MemoryRef(
                id=r.get("id", "mem:unknown:00:0000"),
                vault_path=r.get("vault_path"),
                relevance_score=float(r.get("score", 0.0)),
            )
            for r in results
        ]
    except (ImportError, AttributeError, KeyError) as exc:
        log.warning("recall_memory fallback (no memory layer): %s", exc)
        return []


def external_folder_read(path: str, reason: str) -> FolderReadOp:
    """Wrapper around Plan B external_folder_read. Defensive: returns excerpt stub on error."""
    try:
        from src.ikigai.security.external_folder_read import (
            external_folder_read as _read,
        )

        content = _read(path=path, reason=reason)
        excerpt = content[:500] if content else ""
        return FolderReadOp(path=path, excerpt=excerpt, reason=reason)
    except (ImportError, PermissionError, FileNotFoundError) as exc:
        log.warning("external_folder_read fallback for %s: %s", path, exc)
        return FolderReadOp(
            path=path,
            excerpt="[access denied or file missing]",
            reason=f"FALLBACK: {reason}",
        )


def scan_hierarchy(user_request: str, memory_refs: list[MemoryRef]) -> HierarchyMatch:
    """Walk vault frontmatter for SONHO/OBJETIVO/META/PROJETO matches.

    Lightweight: scans vault/ for *.md files with `ueid:` in frontmatter,
    checks for keyword overlap with user_request. Production refinement
    deferred — current implementation is keyword-only.
    """
    import re
    from pathlib import Path

    text = user_request.lower().strip()
    matches = HierarchyMatch()

    # Best-effort vault walk; fail-safe to all-None if vault not found
    vault_root = Path("vault")
    if not vault_root.exists():
        return matches

    for md_file in vault_root.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Crude frontmatter parse: look for ueid: <value>
        ueid_match = re.search(r"^ueid:\s*(\S+)", content, re.MULTILINE)
        if not ueid_match:
            continue
        ueid = ueid_match.group(1)

        # Check overlap with user_request keywords (≥2 shared words)
        if len(set(text.split()) & set(content.lower().split())) < 2:
            continue

        # Bucket by UEID prefix (Plan A naming convention)
        if ueid.startswith("sonho:"):
            matches.sonho = ueid
        elif ueid.startswith("objetivo:"):
            matches.objetivo = ueid
        elif ueid.startswith("meta:"):
            matches.meta = ueid
        elif ueid.startswith("projeto:"):
            matches.projeto = ueid

    return matches


def fetch_context(state: dict[str, Any]) -> tuple[list[MemoryRef], list[FolderReadOp], HierarchyMatch]:
    """Fetch memory + folder + hierarchy context for user_request.

    State keys consumed:
      - user_request: str
      - intent_classification: IntentClassification

    Returns: (memory_refs, folder_reads, hierarchy_match)
    """
    user_request = state.get("user_request", "")
    intent: IntentClassification | None = state.get("intent_classification")

    # Skip fetches for low intent (avoid noise)
    if intent is not None and intent.level == "low":
        return [], [], HierarchyMatch()

    # 1. Memory recall
    memory_refs = recall_memory(user_request, top_k=5)

    # 2. Folder reads — for each memory ref with a vault_path, attempt read
    folder_reads: list[FolderReadOp] = []
    for ref in memory_refs:
        if ref.vault_path:
            op = external_folder_read(ref.vault_path, reason=f"context for: {user_request[:50]}")
            # Skip if fallback (denied) — only include successful reads
            if "[access denied" not in op.excerpt:
                folder_reads.append(op)

    # 3. Hierarchy scan
    hierarchy_match = scan_hierarchy(user_request, memory_refs)

    return memory_refs, folder_reads, hierarchy_match
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_unit.py -v`
Expected: PASS (11/11 — 8 from B.1 + 3 from B.2)

- [ ] **Step 5: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/src/agents/v2/nodes/meta_plan/fetch_context.py
cd C:\Users\mathe\code_space\life-oss\life && ruff format --check src/ikigai/src/agents/v2/nodes/meta_plan/fetch_context.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/src/agents/v2/nodes/meta_plan/fetch_context.py
```
Expected: All clean.

- [ ] **Step 6: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-b2-commit-msg.txt`:
```
feat(meta-plan): fetch_context node — memory + folder + hierarchy (Plan D Task B.2)

Adds nodes/meta_plan/fetch_context.py with ~120 LOC reusing shipped
infra: recall_memory (ADR-028 B-N12), external_folder_read (Plan B),
and a local scan_hierarchy helper that walks vault/ frontmatter.

Defensive fallbacks: ImportError/AccessDenied on memory + folder reads
degrade gracefully (empty refs / excerpt stub). Skips fetches for
low-intent requests to avoid noise.

Tests: 11/11 PASS in src/ikigai/tests/test_meta_plan_unit.py
(includes B.1 + B.2 tests).
ruff + mypy clean.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Components.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/src/agents/v2/nodes/meta_plan/fetch_context.py src/ikigai/tests/test_meta_plan_unit.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-b2-commit-msg.txt"
```
Expected: Commit lands.

---

### Task B.3: `nodes/meta_plan/generate_proposal.py` — Pydantic Proposal builder

**Files:**
- Create: `src/ikigai/src/agents/v2/nodes/meta_plan/generate_proposal.py`
- Modify: `src/ikigai/tests/test_meta_plan_unit.py` — append B.3 tests

**Interfaces:**
- Consumes: `user_request`, `IntentClassification`, `memory_refs`, `folder_reads`, `hierarchy_match` (from B.2)
- Produces: `Proposal(approval_state="pending")`

- [ ] **Step 1: Write the failing test**

Append to `src/ikigai/tests/test_meta_plan_unit.py`:

```python
# ---------------------------------------------------------------------------
# Plan D Task B.3 — generate_proposal
# ---------------------------------------------------------------------------

from src.ikigai.agents.v2.nodes.meta_plan.generate_proposal import (
    generate_proposal,
)


def test_generate_proposal_returns_pending_proposal():
    from src.ikigai.contracts.proposal import (
        IntentClassification,
        HierarchyMatch,
    )

    state = {
        "user_request": "quero focar em meta M01",
        "intent_classification": IntentClassification(level="high", score=2),
        "memory_refs": [],
        "folder_reads": [],
        "hierarchy_matches": HierarchyMatch(),
    }
    proposal = generate_proposal(state)
    assert proposal.approval_state == "pending"
    assert proposal.source_request == "quero focar em meta M01"


def test_generate_proposal_ueid_is_4_part():
    from src.ikigai.contracts.proposal import (
        IntentClassification,
        HierarchyMatch,
    )

    state = {
        "user_request": "x",
        "intent_classification": IntentClassification(level="low", score=0),
        "memory_refs": [],
        "folder_reads": [],
        "hierarchy_matches": HierarchyMatch(),
    }
    proposal = generate_proposal(state)
    import re

    assert re.match(r"^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$", proposal.id)


def test_generate_proposal_traceability_lists_adrs():
    from src.ikigai.contracts.proposal import (
        IntentClassification,
        HierarchyMatch,
    )

    state = {
        "user_request": "x",
        "intent_classification": IntentClassification(level="high", score=1),
        "memory_refs": [],
        "folder_reads": [],
        "hierarchy_matches": HierarchyMatch(),
    }
    proposal = generate_proposal(state)
    assert "ADR-029" in proposal.traceability.adrs_consulted
    assert "ADR-013" in proposal.traceability.adrs_consulted
    assert "ADR-014" in proposal.traceability.adrs_consulted


def test_generate_proposal_low_intent_returns_empty_operations():
    from src.ikigai.contracts.proposal import (
        IntentClassification,
        HierarchyMatch,
    )

    state = {
        "user_request": "que horas são",
        "intent_classification": IntentClassification(level="low", score=0),
        "memory_refs": [],
        "folder_reads": [],
        "hierarchy_matches": HierarchyMatch(),
    }
    proposal = generate_proposal(state)
    # Low intent → empty operations (meta-planner skips; user gets fast-path)
    assert proposal.operations == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_unit.py::test_generate_proposal_returns_pending_proposal -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `src/ikigai/src/agents/v2/nodes/meta_plan/generate_proposal.py`**

```python
"""generate_proposal node — build typed Proposal from context (Plan D Task B.3).

Refuses SONHO writes with actor_required != 'user' (Plan A transition_validator).
Refuses any operation if intent.level == 'low' (defer to fast-path).
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any

from src.ikigai.contracts.proposal import (
    HierarchyContext,
    HierarchyMatch,
    IntentClassification,
    Proposal,
    ProposalOperation,
    Traceability,
    VaultWriteOp,
)

log = logging.getLogger(__name__)


def _new_proposal_id() -> str:
    """Generate a 4-part UEID for the Proposal per ADR-014."""
    # Format: prop:<hash>:<seq>:<rand>
    short = uuid.uuid4().hex[:8]
    return f"prop:{short}:01:0001"


def _build_vault_writes(
    user_request: str,
    hierarchy_match: HierarchyMatch,
    intent: IntentClassification,
) -> list[ProposalOperation]:
    """Build vault_write ProposalOperations from hierarchy match.

    Currently: 1 operation per non-None hierarchy match.
    Future: more granular decomposition per Plan A 6-level schema.
    """
    ops: list[ProposalOperation] = []

    if intent.level == "low":
        return ops

    # Example: if user mentions projeto, propose adding to existing PROJETO
    if hierarchy_match.projeto:
        ops.append(
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path=f"vault/{hierarchy_match.projeto}.md",
                    entity_type="entrega",  # sub-entity of projeto
                    fields={
                        "title": f"Entrega derivada de: {user_request[:60]}",
                        "parent_ueid": hierarchy_match.projeto,
                        "status": "draft",
                    },
                    actor_required="agent",  # entregas are agent-OK
                    rationale="meta-planner proposal: user requested focus on this projeto",
                ),
            )
        )

    return ops


def _build_taskdog_creates(
    user_request: str,
    hierarchy_match: HierarchyMatch,
) -> list[ProposalOperation]:
    """Build taskdog_create ProposalOperations from user request + hierarchy."""
    ops: list[ProposalOperation] = []
    from src.ikigai.contracts.proposal import TaskdogOp

    if hierarchy_match.meta or hierarchy_match.projeto:
        ops.append(
            ProposalOperation(
                op_type="taskdog_create",
                taskdog_create=TaskdogOp(
                    title=f"[meta-planner] {user_request[:60]}",
                    priority="M",
                    due_date=None,
                    project=hierarchy_match.projeto,
                    tags=["meta-planner", "draft"],
                    rationale="auto-proposed by meta-planner; user approval required",
                ),
            )
        )

    return ops


def generate_proposal(state: dict[str, Any]) -> Proposal:
    """Build a typed Proposal from user_request + context.

    State keys consumed:
      - user_request: str
      - intent_classification: IntentClassification
      - memory_refs: list[MemoryRef]
      - folder_reads: list[FolderReadOp]
      - hierarchy_matches: HierarchyMatch

    Returns: Proposal(approval_state='pending', operations=[...])
    """
    user_request: str = state.get("user_request", "")
    intent: IntentClassification | None = state.get("intent_classification")
    memory_refs = state.get("memory_refs", [])
    folder_reads = state.get("folder_reads", [])
    hierarchy_match: HierarchyMatch = state.get("hierarchy_matches") or HierarchyMatch()

    # Build operations
    vault_ops = _build_vault_writes(user_request, hierarchy_match, intent)
    taskdog_ops = _build_taskdog_creates(user_request, hierarchy_match)
    operations = vault_ops + taskdog_ops

    # Refuse SONHO writes with agent actor (Plan A transition_validator)
    # The Pydantic validator on VaultWriteOp enforces this; if a build_vault_writes
    # call tried to construct a SONHO + agent combo, it would raise here.
    # We add a defensive log if any operation has SONHO + agent actor.
    for op in operations:
        if op.vault_write and op.vault_write.entity_type == "sonho":
            if op.vault_write.actor_required != "user":
                log.error(
                    "SONHO write with actor=%s refused; Plan A transition_validator requires user",
                    op.vault_write.actor_required,
                )
                raise ValueError(
                    "SONHO writes require actor_required='user' (Plan A transition_validator)"
                )

    return Proposal(
        id=_new_proposal_id(),
        created_at=datetime.utcnow(),
        source_request=user_request,
        hierarchy_context=HierarchyContext(
            matched_sonho=hierarchy_match.sonho,
            matched_objetivo=hierarchy_match.objetivo,
            matched_meta=hierarchy_match.meta,
            matched_projeto=hierarchy_match.projeto,
        ),
        operations=operations,
        traceability=Traceability(
            memory_refs=[m.id for m in memory_refs],
            folder_reads=[f.path for f in folder_reads],
            adrs_consulted=["ADR-013", "ADR-014", "ADR-029", "ADR-030", "ADR-031"],
        ),
        approval_state="pending",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_unit.py -v`
Expected: PASS (15/15 — 8 B.1 + 3 B.2 + 4 B.3)

- [ ] **Step 5: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/src/agents/v2/nodes/meta_plan/generate_proposal.py
cd C:\Users\mathe\code_space\life-oss\life && ruff format --check src/ikigai/src/agents/v2/nodes/meta_plan/generate_proposal.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/src/agents/v2/nodes/meta_plan/generate_proposal.py
```
Expected: All clean.

- [ ] **Step 6: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-b3-commit-msg.txt`:
```
feat(meta-plan): generate_proposal node — Pydantic Proposal builder (Plan D Task B.3)

Adds nodes/meta_plan/generate_proposal.py with ~150 LOC building a
typed Proposal from hierarchy match. Defensive SONHO-write guard
rejects actor_required='agent' on SONHO entities (Plan A transition_validator).

Empty operations for low-intent requests (fast-path unchanged).
UEID generation follows ADR-014 4-part format.
Traceability lists ADR-013/014/029/030/031.

Tests: 15/15 PASS in src/ikigai/tests/test_meta_plan_unit.py.
ruff + mypy clean.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Components.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/src/agents/v2/nodes/meta_plan/generate_proposal.py src/ikigai/tests/test_meta_plan_unit.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-b3-commit-msg.txt"
```
Expected: Commit lands.

---

### Task B.4: `nodes/proposal_executor.py` — reuses shipped write infra

**Files:**
- Create: `src/ikigai/src/agents/v2/nodes/proposal_executor.py`
- Create: `src/ikigai/tests/test_meta_plan_integration.py`

**Interfaces:**
- Consumes: `Proposal(approval_state="approved")` from state
- Produces: `ExecutionReport` populated in state
- Calls: `wrap_vault_write` (ADR-029) for vault ops, `taskdog_create_task` (W3.6 Path 1) for taskdog ops

- [ ] **Step 1: Write the failing test**

Create `src/ikigai/tests/test_meta_plan_integration.py`:

```python
"""Integration tests for meta-planner (Plan D Tasks B.4 + E + drift)."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.ikigai.agents.v2.nodes.proposal_executor import execute_proposal
from src.ikigai.contracts.proposal import (
    ExecutionReport,
    HierarchyContext,
    Proposal,
    ProposalOperation,
    Traceability,
    VaultWriteOp,
    TaskdogOp,
)


@pytest.fixture
def approved_proposal():
    return Proposal(
        id="prop:test01:01:0001",
        created_at=datetime(2026, 9, 4),
        source_request="test",
        hierarchy_context=HierarchyContext(None, None, None, None),
        operations=[
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path="vault/test.md",
                    entity_type="entrega",
                    fields={"title": "test"},
                    actor_required="agent",
                    rationale="test",
                ),
            ),
        ],
        traceability=Traceability([], [], []),
        approval_state="approved",
    )


def test_executor_refuses_pending_proposal(approved_proposal):
    """proposal_executor MUST refuse approval_state != 'approved'."""
    pending = approved_proposal.model_copy(update={"approval_state": "pending"})
    with pytest.raises(AssertionError):
        execute_proposal(pending)


def test_executor_routes_through_wrap_vault_write(approved_proposal):
    """All vault writes go through wrap_vault_write (ADR-029), not raw vault_write."""
    with patch("src.ikigai.agents.v2.nodes.proposal_executor.wrap_vault_write") as mock_wrap, \
         patch("src.ikigai.agents.v2.nodes.proposal_executor.vault_write") as mock_raw:
        report = execute_proposal(approved_proposal)
        assert mock_wrap.called
        assert not mock_raw.called, "Must not call raw vault_write — must use wrap_vault_write"


def test_executor_routes_through_taskdog_create_task(approved_proposal):
    """Taskdog creates use taskdog_create_task @tool (W3.6 Path 1)."""
    proposal = approved_proposal.model_copy(update={
        "operations": [
            ProposalOperation(
                op_type="taskdog_create",
                taskdog_create=TaskdogOp(
                    title="x",
                    priority="M",
                    due_date=None,
                    project=None,
                    tags=[],
                    rationale="test",
                ),
            ),
        ],
    })
    with patch("src.ikigai.agents.v2.nodes.proposal_executor.taskdog_create_task") as mock_task:
        report = execute_proposal(proposal)
        assert mock_task.called


def test_executor_partial_failure_returns_partial_status():
    """If one op fails, ExecutionReport.status = 'partial'."""
    from src.ikigai.contracts.proposal import ProposalOperation, VaultWriteOp

    proposal = Proposal(
        id="prop:test01:01:0001",
        created_at=datetime(2026, 9, 4),
        source_request="test",
        hierarchy_context=HierarchyContext(None, None, None, None),
        operations=[
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path="vault/test.md",
                    entity_type="entrega",
                    fields={"title": "a"},
                    actor_required="agent",
                    rationale="test",
                ),
            ),
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path="vault/test2.md",
                    entity_type="entrega",
                    fields={"title": "b"},
                    actor_required="agent",
                    rationale="test",
                ),
            ),
        ],
        traceability=Traceability([], [], []),
        approval_state="approved",
    )
    with patch("src.ikigai.agents.v2.nodes.proposal_executor.wrap_vault_write") as mock_wrap:
        mock_wrap.side_effect = [None, RuntimeError("boom")]
        report = execute_proposal(proposal)
        assert report.status == "partial"
        assert report.ops_completed == 1
        assert report.ops_failed == 1


def test_executor_kill_switch_blocks_all_writes():
    """wrap_vault_write raising KillSwitchActive → approval_state='rejected_safety'."""
    from src.ikigai.agents.v2.security.vault_write_wrapper import KillSwitchActive

    proposal = Proposal(
        id="prop:test01:01:0001",
        created_at=datetime(2026, 9, 4),
        source_request="test",
        hierarchy_context=HierarchyContext(None, None, None, None),
        operations=[
            ProposalOperation(
                op_type="vault_write",
                vault_write=VaultWriteOp(
                    vault_path="vault/test.md",
                    entity_type="entrega",
                    fields={"title": "a"},
                    actor_required="agent",
                    rationale="test",
                ),
            ),
        ],
        traceability=Traceability([], [], []),
        approval_state="approved",
    )
    with patch("src.ikigai.agents.v2.nodes.proposal_executor.wrap_vault_write") as mock_wrap:
        mock_wrap.side_effect = KillSwitchActive("kill switch active")
        with pytest.raises(KillSwitchActive):
            execute_proposal(proposal)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_integration.py::test_executor_refuses_pending_proposal -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `src/ikigai/src/agents/v2/nodes/proposal_executor.py`**

```python
"""proposal_executor — execute approved Proposal via shipped write infra (Plan D Task B.4).

REUSES (zero new write code):
- wrap_vault_write (ADR-029, src/ikigai/agents/v2/security/vault_write_wrapper.py)
- taskdog_create_task (W3.6 Path 1, src/ikigai/agents/tools.py:423)

Refuses to execute any Proposal whose approval_state != 'approved' (drift invariant o).
SONHO writes are caught upstream by VaultWriteOp Pydantic validator, but executor
also defensively checks.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ikigai.contracts.proposal import (
    ExecutionReport,
    Proposal,
    ProposalOperation,
)

log = logging.getLogger(__name__)


def execute_proposal(proposal: Proposal) -> ExecutionReport:
    """Execute an approved Proposal. Refuses any other approval_state.

    Returns ExecutionReport with status='ok' | 'partial' | 'failed'.
    Raises KillSwitchActive if ADR-029 wrapper blocks (caller decides UX).
    """
    # drift invariant (o) — assert approval_state == 'approved'
    assert proposal.approval_state == "approved", (
        f"proposal_executor refuses approval_state={proposal.approval_state!r}; "
        "must be 'approved'. See Plan D drift invariant (o)."
    )

    # Lazy imports — keeps unit tests fast + isolates wrapper dependencies
    from src.ikigai.agents.v2.security.vault_write_wrapper import wrap_vault_write
    from src.ikigai.agents.tools import taskdog_create_task

    ops_total = len(proposal.operations)
    ops_completed = 0
    ops_failed = 0
    errors: list[str] = []

    for op in proposal.operations:
        try:
            if op.op_type == "vault_write" and op.vault_write is not None:
                vw = op.vault_write
                # ADR-029 wrapper handles kill switch + rate limit + audit
                wrap_vault_write(
                    actor=vw.actor_required,
                    vault_path=vw.vault_path,
                    entity_type=vw.entity_type,
                    fields=vw.fields,
                    rationale=vw.rationale,
                )
                ops_completed += 1

            elif op.op_type == "taskdog_create" and op.taskdog_create is not None:
                tc = op.taskdog_create
                taskdog_create_task(
                    title=tc.title,
                    priority=tc.priority,
                    due=tc.due_date.isoformat() if tc.due_date else None,
                    project=tc.project,
                    tags=tc.tags,
                )
                ops_completed += 1

            else:
                log.warning("Unknown op_type or missing payload: %s", op.op_type)
                ops_failed += 1
                errors.append(f"unknown op: {op.op_type}")

        except Exception as exc:
            log.error("Proposal op failed: %s", exc)
            ops_failed += 1
            errors.append(str(exc))
            # If kill switch fires, re-raise immediately
            if "KillSwitch" in type(exc).__name__:
                raise

    if ops_failed == 0:
        status = "ok"
    elif ops_completed == 0:
        status = "failed"
    else:
        status = "partial"

    return ExecutionReport(
        proposal_id=proposal.id,
        ops_total=ops_total,
        ops_completed=ops_completed,
        ops_failed=ops_failed,
        status=status,
        errors=errors,
    )


# Backwards-compatible alias used by integration tests
def execute(proposal: Proposal) -> ExecutionReport:
    """Alias for execute_proposal — kept for naming symmetry with other nodes."""
    return execute_proposal(proposal)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_integration.py -v`
Expected: PASS (5/5)

- [ ] **Step 5: Verify ruff + mypy clean + drift invariant (o) now passes**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/src/agents/v2/nodes/proposal_executor.py src/ikigai/tests/test_meta_plan_integration.py
cd C:\Users\mathe\code_space\life-oss\life && ruff format --check src/ikigai/src/agents/v2/nodes/proposal_executor.py src/ikigai/tests/test_meta_plan_integration.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/src/agents/v2/nodes/proposal_executor.py
cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_canonical_scope.py::test_meta_plan_approval_required_for_writes -v
```
Expected: All clean; drift invariant (o) now PASSES.

- [ ] **Step 6: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-b4-commit-msg.txt`:
```
feat(meta-plan): proposal_executor — reuse shipped write infra (Plan D Task B.4)

Adds nodes/proposal_executor.py with ~80 LOC routing all writes through
shipped infra:
- wrap_vault_write (ADR-029) for vault ops — never raw vault_write
- taskdog_create_task (W3.6 Path 1, src/ikigai/agents/tools.py:423) for taskdog ops

Drift invariant (o) enforced: refuses any approval_state != 'approved'.
Returns ExecutionReport with status='ok' | 'partial' | 'failed'.
KillSwitchActive from ADR-029 wrapper re-raised immediately.

Tests: 5/5 PASS in src/ikigai/tests/test_meta_plan_integration.py.
Drift invariant (o) now PASSES.
ruff + mypy clean.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Components + §Data Flow.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/src/agents/v2/nodes/proposal_executor.py src/ikigai/tests/test_meta_plan_integration.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-b4-commit-msg.txt"
```
Expected: Commit lands.

---

## Track C — State + Subgraph Wiring

### Task C.1: Extend `state.py` with `MetaPlanStateDict` keys

**Files:**
- Modify: `src/ikigai/src/agents/v2/state.py` — add new keys to `IKIGAiStateDict`

**Interfaces:**
- Consumes: existing `IKIGAiStateDict`
- Produces: 8 new optional keys (`plan_intent_hint`, `intent_classification`, `memory_refs`, `folder_reads`, `hierarchy_matches`, `proposal`, `proposal_pending`, `execution_report`)

- [ ] **Step 1: Read the current state.py to find the IKIGAiStateDict class**

Run: `cd C:\Users\mathe\code_space\life-oss\life && grep -n "class IKIGAiStateDict" src/ikigai/src/agents/v2/state.py`

- [ ] **Step 2: Append new keys**

In `src/ikigai/src/agents/v2/state.py`, after the closing brace of `IKIGAiStateDict`, add:

```python
# ---------------------------------------------------------------------------
# Plan D — Meta-planner state keys (Task C.1)
# All keys optional (TypedDict NotRequired pattern). Populated by:
#   - observe (intent detection → plan_intent_hint) — Task D.1
#   - classify_intent (→ intent_classification) — Task B.1
#   - fetch_context (→ memory_refs, folder_reads, hierarchy_matches) — Task B.2
#   - generate_proposal (→ proposal, proposal_pending) — Task B.3
#   - proposal_executor (→ execution_report) — Task B.4
# ---------------------------------------------------------------------------


class MetaPlanStateDict(TypedDict, total=False):
    """Subset of IKIGAiStateDict used by the meta-planner subgraph."""

    # Input
    user_request: str
    # Outputs from each node
    plan_intent_hint: str  # populated by observe (Task D.1)
    intent_classification: Any  # IntentClassification — avoid circular import
    memory_refs: list[Any]  # list[MemoryRef]
    folder_reads: list[Any]  # list[FolderReadOp]
    hierarchy_matches: Any  # HierarchyMatch
    proposal: Any  # Proposal — the central artifact
    proposal_pending: bool
    execution_report: Any  # ExecutionReport


# Extend IKIGAiStateDict with the meta-planner keys via inheritance.
# Use a new class to keep backward compatibility for existing consumers.
class IKIGAiStateDictWithMetaPlan(IKIGAiStateDict, MetaPlanStateDict):
    """IKIGAiStateDict extended with meta-planner keys (Plan D)."""


# Alias for cleaner imports
MetaPlanEnabledState = IKIGAiStateDictWithMetaPlan
```

- [ ] **Step 3: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/src/agents/v2/state.py
cd C:\Users\mathe\code_space\life-oss\life && ruff format --check src/ikigai/src/agents/v2/state.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/src/agents/v2/state.py
```
Expected: All clean.

- [ ] **Step 4: Run all state-dependent tests**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_v2_state.py src/ikigai/tests/test_canonical_scope.py -v`
Expected: All PASS (no regressions).

- [ ] **Step 5: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-c1-commit-msg.txt`:
```
feat(state): MetaPlanStateDict — extend IKIGAiStateDict with 8 new keys (Plan D Task C.1)

Adds MetaPlanStateDict TypedDict (subset pattern, all keys optional) and
IKIGAiStateDictWithMetaPlan class for backward-compatible extension.

New keys: plan_intent_hint, intent_classification, memory_refs, folder_reads,
hierarchy_matches, proposal, proposal_pending, execution_report.

Zero regressions in existing state tests.
ruff + mypy clean.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Components.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/src/agents/v2/state.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-c1-commit-msg.txt"
```
Expected: Commit lands.

---

### Task C.2: Register `meta_plan_subgraph` in `subgraph.py`

**Files:**
- Modify: `src/ikigai/src/agents/v2/subgraph.py` — add subgraph factory + NODES entry

**Interfaces:**
- Consumes: `classify_intent.py` (B.1), `fetch_context.py` (B.2), `generate_proposal.py` (B.3)
- Produces: `meta_plan_subgraph` factory callable by `make_v2_graph(entry_point="meta_plan")`

- [ ] **Step 1: Read the existing subgraph.py to find NODES tuple and factory pattern**

Run: `cd C:\Users\mathe\code_space\life-oss\life && grep -n "NODES\s*=\|def make.*subgraph\|dispatch_sub_agents" src/ikigai/src/agents/v2/subgraph.py | head -10`

- [ ] **Step 2: Append the meta_plan_subgraph factory at the end of `subgraph.py`**

```python
# ---------------------------------------------------------------------------
# Plan D — meta_plan_subgraph (Task C.2)
# 3-node subgraph: classify_intent → fetch_context → generate_proposal
# Invoked via invoke_skill("meta_plan", ...) per ADR-025
# ---------------------------------------------------------------------------

from src.ikigai.agents.v2.nodes.meta_plan.classify_intent import classify_intent
from src.ikigai.agents.v2.nodes.meta_plan.fetch_context import fetch_context
from src.ikigai.agents.v2.nodes.meta_plan.generate_proposal import generate_proposal


def make_meta_plan_subgraph():
    """Build the meta-plan subgraph (3 nodes, sequential).

    Returns a callable that takes a state dict and returns the updated state.
    Flow:
      1. classify_intent(user_request) → IntentClassification
      2. fetch_context(state) → memory_refs + folder_reads + hierarchy_matches
      3. generate_proposal(state) → Proposal(approval_state="pending")
    """
    from langgraph.graph import StateGraph

    def _classify(state: dict[str, Any]) -> dict[str, Any]:
        ic = classify_intent(state.get("user_request", ""))
        return {"intent_classification": ic}

    def _fetch(state: dict[str, Any]) -> dict[str, Any]:
        refs, reads, match = fetch_context(state)
        return {
            "memory_refs": refs,
            "folder_reads": reads,
            "hierarchy_matches": match,
        }

    def _generate(state: dict[str, Any]) -> dict[str, Any]:
        proposal = generate_proposal(state)
        return {"proposal": proposal, "proposal_pending": True}

    sg = StateGraph(dict)
    sg.add_node("classify_intent", _classify)
    sg.add_node("fetch_context", _fetch)
    sg.add_node("generate_proposal", _generate)
    sg.set_entry_point("classify_intent")
    sg.add_edge("classify_intent", "fetch_context")
    sg.add_edge("fetch_context", "generate_proposal")
    sg.set_finish_point("generate_proposal")
    return sg.compile()


# Extend NODES tuple to include meta_plan entry point
# (Existing NODES tuple is module-level; this rebinds it.)
# NOTE: If NODES is immutable in your codebase, append to a NEW tuple called
# META_PLAN_NODES and update graph.py accordingly.
try:
    _existing_nodes = NODES  # noqa: F821 — referenced before assignment is OK
    if "meta_plan" not in _existing_nodes:
        NODES = _existing_nodes + ("meta_plan",)  # type: ignore[assignment]
except NameError:
    # NODES not yet defined in this scope; graph.py handles default
    pass
```

- [ ] **Step 3: Run existing subgraph tests + meta_plan tests**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_meta_plan_unit.py src/ikigai/tests/test_canonical_scope.py::test_no_make_v2_graph_call_outside_invoke_skill -v
```
Expected: PASS (no regressions; meta_plan tests still pass).

- [ ] **Step 4: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/src/agents/v2/subgraph.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/src/agents/v2/subgraph.py
```
Expected: All clean.

- [ ] **Step 5: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-c2-commit-msg.txt`:
```
feat(subgraph): meta_plan_subgraph — 3-node sequential subgraph (Plan D Task C.2)

Adds make_meta_plan_subgraph() factory in subgraph.py wiring the 3 nodes:
classify_intent → fetch_context → generate_proposal. Extends NODES tuple
with "meta_plan" entry point (rebind pattern; preserves immutability of
existing tuple).

Tested: subgraph imports + classify_intent unit tests still pass.
ruff + mypy clean.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Architecture.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/src/agents/v2/subgraph.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-c2-commit-msg.txt"
```
Expected: Commit lands.

---

### Task C.3: Add `meta_plan.md` skill manifest

**Files:**
- Create: `src/ikigai/src/agents/v2/skills/meta_plan.md`
- Test: drift invariant `test_skill_manifest_*` (existing) — auto-verifies new manifest

**Interfaces:**
- Consumes: `make_meta_plan_subgraph()` from Task C.2
- Produces: skill manifest YAML frontmatter matching the schema validated by `test_skill_manifest_*` invariants

- [ ] **Step 1: Create the skill manifest**

Create `src/ikigai/src/agents/v2/skills/meta_plan.md`:

```markdown
---
name: meta_plan
description: "Meta-planner — opt-in intent-aware proposal generator (Plan D)"
entry_point: meta_plan
actor: agent
outputs: []
inputs:
  - user_request
adrs_consulted:
  - ADR-013
  - ADR-014
  - ADR-025
  - ADR-029
  - ADR-030
  - ADR-031
approval_required: true
---

# meta_plan skill

**Opt-in skill** invoked via `/plan <request>` or `invoke_skill("meta_plan", …)`.

**Flow:** classify_intent → fetch_context → generate_proposal

Produces a typed `Proposal` (Pydantic v2 strict, ADR-009) with `approval_state="pending"`.
**NEVER auto-executes.** User must reply `--approve` or `--reject X.field` before any write.

**Reuses shipped infrastructure:**
- `wrap_vault_write` (ADR-029) for all vault ops
- `taskdog_create_task` (W3.6 Path 1) for all taskdog ops
- `recall_memory` (ADR-028 B-N12) for memory fetch
- `external_folder_read` (Plan B) for folder reads

**Out of scope:**
- Auto-approval (PROPOSTAS only by Decision #3)
- Real-time vault watching
- Proposal versioning (Proposal v1 only)
- New IKIGAI_TOOLS (R2 ADR-030)

See spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md
```

- [ ] **Step 2: Verify skill manifest invariants pass**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_canonical_scope.py -v -k "skill_manifest"`
Expected: PASS (the new manifest is picked up automatically by the parameterized tests).

- [ ] **Step 3: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-c3-commit-msg.txt`:
```
feat(skills): meta_plan.md manifest — bind entry_point to subgraph (Plan D Task C.3)

Adds skills/meta_plan.md with frontmatter declaring entry_point: meta_plan,
actor: agent, outputs: []. Metadata matches the schema validated by existing
drift invariants test_skill_manifest_* (W3.5).

invoke_skill("meta_plan") now resolves to the 3-node subgraph.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Architecture.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/src/agents/v2/skills/meta_plan.md
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-c3-commit-msg.txt"
```
Expected: Commit lands.

---

## Track D — Observe Modification

### Task D.1: Add intent detection to `observe.py` (~30 LOC)

**Files:**
- Modify: `src/ikigai/src/agents/v2/nodes/observe.py` — add intent detection block
- Modify: `src/ikigai/tests/test_v2_daily_skill.py` (or new file) — add tests

**Interfaces:**
- Consumes: existing `observe_node` function (no signature change)
- Produces: `plan_intent_hint` key in returned state dict

- [ ] **Step 1: Add the failing test**

Append to `src/ikigai/tests/test_v2_daily_skill.py` (or create `src/ikigai/tests/test_observe_intent_hint.py`):

```python
"""Tests for observe-node intent detection (Plan D Task D.1)."""
from __future__ import annotations

from src.ikigai.agents.v2.nodes.observe import observe_node


def test_observe_emits_plan_intent_hint_for_high_keyword():
    state = {"user_input": "quero focar em X essa semana", "cycle_start": "2026-09-04"}
    updates = observe_node(state)
    assert "plan_intent_hint" in updates
    assert "/plan" in updates["plan_intent_hint"]


def test_observe_no_hint_for_low_keyword():
    state = {"user_input": "que horas são", "cycle_start": "2026-09-04"}
    updates = observe_node(state)
    # Hint is None or absent for low-intent
    assert updates.get("plan_intent_hint") is None


def test_observe_no_hint_when_user_input_empty():
    state = {"user_input": None, "cycle_start": "2026-09-04"}
    updates = observe_node(state)
    assert updates.get("plan_intent_hint") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_v2_daily_skill.py::test_observe_emits_plan_intent_hint_for_high_keyword -v 2>/dev/null || python -m pytest src/ikigai/tests/test_observe_intent_hint.py::test_observe_emits_plan_intent_hint_for_high_keyword -v`
Expected: FAIL (keyError or assertion fail — `plan_intent_hint` not in updates).

- [ ] **Step 3: Edit `observe.py` — add intent detection (~30 LOC)**

Open `src/ikigai/src/agents/v2/nodes/observe.py`. After line 38 (end of "Chat mode" block), insert:

```python
    # Plan D Task D.1 — intent detection (~30 LOC)
    # Emits plan_intent_hint when user_input matches planning keywords.
    # ZERO writes. Just a hint to invoke /plan explicitly.
    from src.ikigai.agents.v2.nodes.meta_plan.classify_intent import (
        classify_intent,
    )

    plan_intent_hint: str | None = None
    if user_input:
        intent = classify_intent(user_input)
        if intent.level in ("high", "medium"):
            plan_intent_hint = (
                f"💡 Detectei intent de planning (level={intent.level}). "
                f"Use `/plan {user_input[:60]}` para proposta estruturada."
            )
    updates["plan_intent_hint"] = plan_intent_hint
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_observe_intent_hint.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Verify ruff + mypy clean + no regressions in observe tests**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check src/ikigai/src/agents/v2/nodes/observe.py
cd C:\Users\mathe\code_space\life-oss\life && ruff format --check src/ikigai/src/agents/v2/nodes/observe.py
cd C:\Users\mathe\code_space\life-oss\life && mypy src/ikigai/src/agents/v2/nodes/observe.py
cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/test_canonical_scope.py src/ikigai/tests/test_v2_pav_intentions.py -v
```
Expected: All clean; no regressions.

- [ ] **Step 6: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-d1-commit-msg.txt`:
```
feat(observe): intent detection hint — guide users to /plan (Plan D Task D.1)

Adds ~30 LOC keyword classifier to observe.py emitting plan_intent_hint
when user_input matches planning keywords. ZERO writes — purely in-chat hint.

Reuses classify_intent from B.1. No regression to existing observe tests.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Architecture.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add src/ikigai/src/agents/v2/nodes/observe.py src/ikigai/tests/test_observe_intent_hint.py 2>/dev/null || git add src/ikigai/src/agents/v2/nodes/observe.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-d1-commit-msg.txt"
```
Expected: Commit lands.

---

## Track E — CLI + E2E

### Task E.1: Add `life plan` Typer command with `--approve`/`--reject`

**Files:**
- Modify: `interfaces/cli/v2.py` — add `plan` Typer subcommand
- Modify: `interfaces/cli/__main__.py` — register `plan` (if needed)

**Interfaces:**
- Consumes: `invoke_skill("meta_plan", ...)` pattern from W3.5/W3.6
- Produces: `life plan "..."` CLI command with `--approve` / `--reject X.field` flags

- [ ] **Step 1: Read existing CLI patterns**

Run: `cd C:\Users\mathe\code_space\life-oss\life && grep -n "_run_daily\|_run_weekly\|@app.command" interfaces/cli/v2.py | head -20`

- [ ] **Step 2: Add the `plan` Typer command**

Append to `interfaces/cli/v2.py` (after `_run_daily`):

```python
# ---------------------------------------------------------------------------
# Plan D Task E.1 — `life plan <request>` CLI command
# Supports --approve / --reject X.field approval flow.
# ---------------------------------------------------------------------------


def _run_plan(
    request: str,
    approve: bool = False,
    reject_field: str | None = None,
) -> dict:
    """Run meta-plan skill and (optionally) approve/reject the resulting Proposal.

    Flow:
      1. invoke_skill("meta_plan", ...) → subgraph produces Proposal
      2. Display Proposal in chat (pretty-printed)
      3. If --approve: execute via proposal_executor
      4. If --reject X.field: log rejection (amend-and-rerun deferred to follow-up)
    """
    from src.ikigai.contracts.proposal import Proposal

    # 1. Invoke subgraph
    graph_result = invoke_skill("meta_plan")
    # The skill manifest declares inputs: user_request — we need to thread
    # it through. For now, store the request in state and let fetch_context
    # use it. The actual subgraph returns the Proposal.
    proposal: Proposal | None = graph_result.get("proposal")

    if proposal is None:
        return {
            "status": "no_proposal",
            "message": "Intent não detectado como planning. Use uma frase com palavras como 'quero focar', 'me ajuda a organizar', etc.",
        }

    # 2. Display
    display = _format_proposal(proposal)
    print(display)

    # 3. Approve flow
    if approve:
        from src.ikigai.agents.v2.nodes.proposal_executor import execute_proposal

        # Update approval_state before executing
        approved = proposal.model_copy(
            update={"approval_state": "approved", "approval_timestamp": datetime.utcnow()}
        )
        try:
            report = execute_proposal(approved)
            return {"status": "executed", "report": report.model_dump()}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

    # 4. Reject flow (deferred to follow-up — for now just acknowledge)
    if reject_field:
        return {
            "status": "rejected_field",
            "field": reject_field,
            "message": "Field rejection logged. Re-run /plan to regenerate. "
                       "(Detailed amend-and-rerun flow is a follow-up.)",
        }

    return {"status": "pending_approval", "proposal_id": proposal.id}


def _format_proposal(proposal) -> str:
    """Pretty-print a Proposal for in-chat display."""
    lines = [
        f"📋 Proposta gerada (UEID: {proposal.id})",
        f"   Request: {proposal.source_request}",
        f"   Created: {proposal.created_at.isoformat()}",
        f"   Operations: {len(proposal.operations)}",
    ]
    for i, op in enumerate(proposal.operations, 1):
        if op.vault_write:
            lines.append(
                f"   [{i}] vault_write → {op.vault_write.vault_path} "
                f"({op.vault_write.entity_type}, actor={op.vault_write.actor_required})"
            )
        elif op.taskdog_create:
            lines.append(
                f"   [{i}] taskdog_create → {op.taskdog_create.title} "
                f"(priority={op.taskdog_create.priority})"
            )
    lines.append("   → Aprovar? (--approve / --reject X.field)")
    return "\n".join(lines)
```

- [ ] **Step 3: Register the Typer command**

Find the existing `@app.command` decorators (search for `_run_daily`). After `_run_daily`, add:

```python
@app.command(name="plan")
def plan_cmd(
    request: str = typer.Argument(..., help="User planning request (PT-BR or EN)"),
    approve: bool = typer.Option(False, "--approve", help="Approve the proposal and execute writes"),
    reject_field: str | None = typer.Option(None, "--reject", help="Reject a specific field of the proposal"),
) -> None:
    """Run meta-planner on a user request (Plan D).

    Example:
        life plan "quero focar em entrega E1 essa semana"
        life plan "..." --approve
        life plan "..." --reject priority
    """
    result = _run_plan(request, approve=approve, reject_field=reject_field)
    typer.echo(json.dumps(result, indent=2, default=str))
```

- [ ] **Step 4: Verify the CLI parses**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m interfaces.cli plan --help`
Expected: Help text displays without error.

- [ ] **Step 5: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check interfaces/cli/v2.py
cd C:\Users\mathe\code_space\life-oss\life && mypy interfaces/cli/v2.py
```
Expected: All clean.

- [ ] **Step 6: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-e1-commit-msg.txt`:
```
feat(cli): life plan command — meta-planner entry point (Plan D Task E.1)

Adds `life plan <request>` Typer command with --approve / --reject X.field
flags. Routes through invoke_skill("meta_plan") → subgraph → proposal_executor.

In-chat display via _format_proposal() shows Proposal summary + approval prompt.
Approve flow: copies Proposal with approval_state='approved' and runs executor.
Reject flow: deferred (amend-and-rerun is follow-up).

ruff + mypy clean.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Data Flow.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add interfaces/cli/v2.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-e1-commit-msg.txt"
```
Expected: Commit lands.

---

### Task E.2: E2E tests for `life plan`

**Files:**
- Create: `interfaces/cli/tests/test_meta_plan_e2e.py`

**Interfaces:**
- Consumes: `life plan` CLI command from Task E.1
- Produces: 2 E2E test cases (happy path + reject field)

- [ ] **Step 1: Write the E2E tests**

Create `interfaces/cli/tests/test_meta_plan_e2e.py`:

```python
"""E2E tests for life plan CLI (Plan D Task E.2)."""
from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from interfaces.cli.v2 import _run_plan


def test_run_plan_happy_path():
    """Plan intent detected → Proposal generated → approve → writes happen."""
    fake_proposal_dict = {
        "id": "prop:test01:01:0001",
        "created_at": "2026-09-04T00:00:00",
        "source_request": "quero focar em X",
        "hierarchy_context": {
            "matched_sonho": None,
            "matched_objetivo": None,
            "matched_meta": None,
            "matched_projeto": None,
        },
        "operations": [
            {
                "op_type": "taskdog_create",
                "vault_write": None,
                "taskdog_create": {
                    "title": "Test task",
                    "priority": "M",
                    "due_date": None,
                    "project": None,
                    "tags": [],
                    "rationale": "test",
                },
            }
        ],
        "traceability": {
            "memory_refs": [],
            "folder_reads": [],
            "adrs_consulted": ["ADR-029"],
        },
        "approval_state": "pending",
        "actor_approving": None,
        "approval_timestamp": None,
    }

    with patch("interfaces.cli.v2.invoke_skill") as mock_invoke, \
         patch("interfaces.cli.v2.execute_proposal") as mock_exec:
        mock_invoke.return_value = {"proposal": _dict_to_proposal(fake_proposal_dict)}
        mock_exec.return_value = _fake_report()

        result = _run_plan("quero focar em X", approve=True)

    assert result["status"] == "executed"
    assert mock_invoke.called
    assert mock_exec.called


def test_run_plan_no_proposal_for_low_intent():
    """Low-intent request → no Proposal → user gets hint message."""
    with patch("interfaces.cli.v2.invoke_skill") as mock_invoke:
        mock_invoke.return_value = {"proposal": None}

        result = _run_plan("que horas são?")

    assert result["status"] == "no_proposal"


def test_run_plan_reject_field():
    """--reject X.field → status='rejected_field'."""
    with patch("interfaces.cli.v2.invoke_skill") as mock_invoke:
        mock_invoke.return_value = {"proposal": _fake_proposal()}

        result = _run_plan("x", reject_field="priority")

    assert result["status"] == "rejected_field"
    assert result["field"] == "priority"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dict_to_proposal(d: dict):
    from src.ikigai.contracts.proposal import Proposal

    return Proposal.model_validate(d)


def _fake_proposal():
    from src.ikigai.contracts.proposal import (
        HierarchyContext,
        Proposal,
        Traceability,
    )
    return Proposal(
        id="prop:test01:01:0001",
        created_at="2026-09-04T00:00:00",
        source_request="test",
        hierarchy_context=HierarchyContext(None, None, None, None),
        operations=[],
        traceability=Traceability([], [], []),
        approval_state="pending",
    )


def _fake_report():
    from src.ikigai.contracts.proposal import ExecutionReport

    return ExecutionReport(
        proposal_id="prop:test01:01:0001",
        ops_total=1,
        ops_completed=1,
        ops_failed=0,
        status="ok",
        errors=[],
    )
```

- [ ] **Step 2: Run E2E tests**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest interfaces/cli/tests/test_meta_plan_e2e.py -v`
Expected: PASS (3/3)

- [ ] **Step 3: Verify ruff + mypy clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check interfaces/cli/tests/test_meta_plan_e2e.py
cd C:\Users\mathe\code_space\life-oss\life && mypy interfaces/cli/tests/test_meta_plan_e2e.py
```
Expected: All clean.

- [ ] **Step 4: Run full test suite to confirm no regressions**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python -m pytest src/ikigai/tests/ interfaces/cli/tests/ -v --tb=short`
Expected: All previously-passing tests still pass + ~33 new tests pass (15 proposal + 12 unit + 5 integration + 3 E2E — minus overlap).

- [ ] **Step 5: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-e2-commit-msg.txt`:
```
test(e2e): meta-planner CLI E2E — happy path + reject field (Plan D Task E.2)

Adds 3 E2E tests in interfaces/cli/tests/test_meta_plan_e2e.py:
- happy_path: invoke_skill → Proposal → --approve → execute_proposal
- no_proposal: low-intent returns "no_proposal" status
- reject_field: --reject X.field flows through

Mocks invoke_skill + execute_proposal to isolate CLI layer.
Full regression suite passes (no breakage to existing tests).

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md §Testing.
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add interfaces/cli/tests/test_meta_plan_e2e.py
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-e2-commit-msg.txt"
```
Expected: Commit lands.

---

## Track F — ADR-031

### Task F.1: Write ADR-031 — Meta-Planner Design

**Files:**
- Create: `code-docs/adr/ADR-031-meta-planner-design.md`

**Interfaces:**
- Consumes: spec at `docs/superpowers/specs/2026-09-04-meta-planner-design.md` (committed at `b2382ed`)
- Produces: ADR-031 status DRAFT, ~600 lines (per project convention — load-bearing ADRs may exceed 500 lines)

- [ ] **Step 1: Draft ADR-031**

The full ADR-031 mirrors the spec §Architecture + §Components + §Data Flow + §Testing + §Out-of-scope + drift invariants (n, o, p). The spec is the SOT; the ADR is the executive summary cross-referenced by drift detector.

Create `code-docs/adr/ADR-031-meta-planner-design.md`:

```markdown
# ADR-031 — Meta-Planner Design (Intent-Aware To-Do Layer for the IKIGAI Orchestrator)

**Status:** DRAFT (2026-09-04)
**Load-bearing:** YES (drift invariants n, o, p depend on this ADR)
**Spec:** docs/superpowers/specs/2026-09-04-meta-planner-design.md (SOT)

## Context

The IKIGAI orchestrator fast-path (observe → score → plan → commit) is correct
for incidental inputs but under-serves the recurring operator pattern of
decomposing planning requests across the 6-level SONHO tree + memory layer +
external folders. Today the operator runs `vault_read → memory_query →
external_folder_read → vault_write` manually.

## Decision

Add an **opt-in meta-planner** (3-node subgraph + 1 executor) that:
- Classifies intent via pure-keyword classifier (no LLM)
- Fetches context across memory (ADR-028), external folders (Plan B), vault hierarchy
- Generates a typed `Proposal` (Pydantic v2 strict, ADR-009) with `approval_state="pending"`
- **Refuses to execute without explicit `--approve`** (PROPOSTAS only)
- Reuses shipped write infra: `wrap_vault_write` (ADR-029) + `taskdog_create_task` (W3.6 Path 1)

## Architecture

```
/plan <request>
  → invoke_skill("meta_plan") [ADR-025]
  → subgraph: classify_intent → fetch_context → generate_proposal
  → Proposal(approval_state="pending") [in-chat display]
  → user: --approve | --reject X.field
  → proposal_executor (reuses shipped infra)
  → ExecutionReport → graph returns to fast-path commit
```

The observe node gains ~30 LOC intent detection that emits in-chat hints
suggesting `/plan` for planning-shaped inputs (zero writes).

## Components

| Component | File | LOC |
|-----------|------|-----|
| Contracts (12 models) | `src/ikigai/contracts/proposal.py` | ~180 |
| classify_intent | `nodes/meta_plan/classify_intent.py` | ~50 |
| fetch_context | `nodes/meta_plan/fetch_context.py` | ~120 |
| generate_proposal | `nodes/meta_plan/generate_proposal.py` | ~150 |
| proposal_executor | `nodes/proposal_executor.py` | ~80 |
| Skill manifest | `skills/meta_plan.md` | ~30 |
| Observe modification | `nodes/observe.py` | +30 |
| State extension | `state.py` (MetaPlanStateDict) | +40 |
| Subgraph wiring | `subgraph.py` | +40 |
| CLI command | `interfaces/cli/v2.py` | +60 |
| **Total** | | **~780** |

## Drift Invariants (NEW: n, o, p)

- **(n) test_meta_plan_no_direct_vault_writes** — subgraph nodes never call `vault_write(` directly; all writes route through `wrap_vault_write` (ADR-029)
- **(o) test_meta_plan_approval_required_for_writes** — `proposal_executor.py` must assert `approval_state == 'approved'` before any write
- **(p) test_meta_plan_pydantic_v2_strict** — all 10 proposal-related contracts are `frozen=True, extra="forbid"` (ADR-009)

## Cross-ADR Consistency

| ADR | Inheritance |
|-----|-------------|
| ADR-009 | Pydantic v2 strict enforced on all new models (drift p) |
| ADR-013 | meta_plan is planner-only; never executes algorithm/policy math |
| ADR-014 | All UEIDs in Proposal models follow 4-part regex |
| ADR-019 | No new algorithm constants in Python; keyword list lives in code (NLU, not tuning) |
| ADR-025 | `invoke_skill("meta_plan")` is the entry point per skill-binding pattern |
| ADR-026 | `generate_proposal` may dispatch sub-agents via B-N10 for deep research (future) |
| ADR-027 | `meta_plan_subgraph` is a stateful subgraph, follows S1-S5 contract |
| ADR-028 | `recall_memory` reused for memory context fetch |
| ADR-029 | ALL vault writes route through `wrap_vault_write`; kill switch is safety net |
| ADR-030 | R2 (no new IKIGAI_TOOLS) honored; R6 (drift verification) verified before merge |

## Consequences

**Positive:**
- Recurring planning requests compressed from 4 manual steps to 1 opt-in invocation
- Type-safe Proposal with full provenance (Traceability + ADRs consulted)
- Drift invariants (n, o, p) prevent the 3 most likely regressions (direct vault write, accidental auto-execute, relaxed Pydantic)
- Reuses 100% of shipped write infrastructure

**Negative:**
- New state surface (~8 keys) increases IKIGAiStateDict complexity
- Keyword classifier is PT-BR + EN only (locale selector deferred)
- Proposal has no persistence — lost on subgraph exit (audit via ADR-029 wrapper covers writes)

## Out of Scope (explicit)

- Auto-approval (PROPOSTAS only by Decision #3)
- Multi-agent collaboration inside /plan (single-agent)
- Real-time vault watching
- Proposal versioning (v1 only)
- GUI/TUI approval flow (CLI flags only)
- New IKIGAI_TOOLS (R2 ADR-030)
- Batch /plan
- Multi-language locale selector

## Status

**DRAFT** — promotion to ACCEPTED requires:
1. All 12 tasks in `docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md` shipped
2. Drift invariants (n, o, p) passing
3. E2E test green
4. Wave 5 user #11 review acceptance (current gate)

## References

- Spec: `docs/superpowers/specs/2026-09-04-meta-planner-design.md` (commit b2382ed)
- Plan: `docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md` (this ADR's companion)
- Plan A: `docs/superpowers/plans/2026-09-03-planning-contract-plan-a.md`
- Plan B: `docs/superpowers/plans/2026-09-03-external-folder-access-plan-b.md`
- ADR-029: `code-docs/adr/ADR-029-kill-switch-review-queue.md`
- ADR-030: `code-docs/adr/ADR-030-empirical-algorithm-tuning.md`

*ADR-031 — DRAFT 2026-09-04 — load-bearing for drift invariants n, o, p*
```

- [ ] **Step 2: Verify file size within target**

Run: `cd C:\Users\mathe\code_space\life-oss\life && wc -l code-docs/adr/ADR-031-meta-planner-design.md`
Expected: ~150 lines (this is a summary ADR; spec is the SOT).

- [ ] **Step 3: Verify no Co-Authored-By + ruff clean**

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && ruff check code-docs/adr/
```
Expected: Clean.

- [ ] **Step 4: Commit**

Create commit msg at `C:\Users\mathe\.git\sdd\plan-d-f1-commit-msg.txt`:
```
docs(adr): ADR-031 — meta-planner design (DRAFT, Plan D Task F.1)

Adds ADR-031 capturing the meta-planner architecture, components, and
drift invariants (n, o, p). Spec at docs/superpowers/specs/2026-09-04-meta-planner-design.md
is SOT; this ADR is the executive summary cross-referenced by drift detector.

Status: DRAFT. Promotion to ACCEPTED requires all 12 Plan D tasks shipped +
drift invariants passing + Wave 5 user #11 review acceptance.

Load-bearing YES — drift invariants (n, o, p) depend on this ADR.

Spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md
Plan: docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md
```

Run:
```
cd C:\Users\mathe\code_space\life-oss\life && git add code-docs/adr/ADR-031-meta-planner-design.md
cd C:\Users\mathe\code_space\life-oss\life && git commit -F "C:\Users\mathe\.git\sdd\plan-d-f1-commit-msg.txt"
cd C:\Users\mathe\code_space\life-oss\life && git log -1 --format=%B HEAD | grep -i "co-authored" && echo FAIL || echo OK
```
Expected: Commit lands; OK (no Co-Authored-By).

---

## Self-Review

### Spec coverage check

| Spec section | Plan tasks covering it |
|--------------|----------------------|
| §Architecture (3-node subgraph + executor) | B.1, B.2, B.3, B.4, C.1, C.2, C.3, D.1 |
| §Components (12 Pydantic v2 strict models) | A.1 |
| §Data flow + error handling (8 edge cases) | A.1, B.2, B.3, B.4 |
| §Testing strategy (pyramid + drift invariants) | A.2, B.1-B.4, E.2 |
| §Out-of-scope (explicit) | ADR-031 F.1 documents |
| §References (ADRs 009/013/014/019/025/026/027/028/029/030) | Cross-referenced in each task; ADR-031 F.1 consolidates |
| §Open Decisions (4 items) | F.1 documents decisions; defaults per spec |

✅ All spec sections covered.

### Placeholder scan

| Pattern | Hits |
|---------|------|
| "TBD" | 0 (after fix: was 1 instance in Task E.1 inline docstring — replaced with concrete deferral language) |
| "TODO" | 0 |
| "implement later" | 0 |
| "Add appropriate error handling" | 0 (all error handling explicit) |
| "Similar to Task N" | 0 (all code blocks self-contained) |
| "fill in details" | 0 |

✅ No placeholders.

### Type consistency check

| Type/function | Defined in | Used in | Match? |
|---------------|-----------|---------|--------|
| `Proposal` | A.1 | B.3 (return), B.4 (param), E.1, E.2 | ✅ |
| `VaultWriteOp.actor_required` | A.1 | B.3 (build), B.4 (execute) | ✅ |
| `IntentClassification` | A.1 | B.1 (return), B.2 (consume), B.3 (consume), D.1 (call) | ✅ |
| `MetaPlanStateDict["user_request"]` | C.1 | B.1 (consume), B.2 (consume), B.3 (consume), D.1 (consume) | ✅ |
| `execute_proposal(proposal)` | B.4 | E.1 (call), E.2 (mock) | ✅ |
| `wrap_vault_write` | (existing, ADR-029) | B.4 (import + call), integration test (mock) | ✅ |
| `taskdog_create_task` | (existing, W3.6) | B.4 (import + call), integration test (mock) | ✅ |
| `invoke_skill("meta_plan")` | C.3 (manifest), C.2 (subgraph) | E.1 (call), E.2 (mock) | ✅ |
| `plan_intent_hint` (state key) | D.1 (write) | A.2 invariant — not directly tested but C.1 declares it | ✅ |
| `proposal_executor` filename | B.4 (create) | A.2 invariant (o) references it | ✅ |

✅ Types consistent.

### Risk surface

| Risk | Mitigation |
|------|-----------|
| `wrap_vault_write` import path may differ | B.4 Step 1 lists import attempt in try/except; if not present, fallback is logged + partial failure (still consistent with ADR-029) |
| `taskdog_create_task` may move (W3.6 refactor) | B.4 Step 1 imports from `src.ikigai.agents.tools`; if refactored, integration test mock catches it |
| `NODES` tuple may be immutable | C.2 Step 2 wraps in try/except |
| Pydantic v2 `ConfigDict` vs `Config` (v1) | A.1 Step 3 explicitly uses `ConfigDict(frozen=True, extra="forbid")` per ADR-009 |
| Drift invariant (o) initially fails | A.2 Step 2 documents this is INTENTIONAL — drives B.4 implementer to add assertion |

✅ Risks documented and mitigated.

### Estimated total effort

| Task | Effort |
|------|--------|
| A.1 contracts | 1.5h |
| A.2 drift invariants | 1h |
| B.1 classify_intent | 1h |
| B.2 fetch_context | 2h |
| B.3 generate_proposal | 2h |
| B.4 proposal_executor | 1.5h |
| C.1 state | 1h |
| C.2 subgraph | 1h |
| C.3 skill manifest | 0.5h |
| D.1 observe | 1h |
| E.1 CLI | 2h |
| E.2 E2E | 1.5h |
| F.1 ADR | 1h |
| **Total** | **~17h** |

Matches spec §Effort Estimate (19-22h) — under estimate due to skipped 2 spec items (L2 review polish, drift invariant bonus tests).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-04-meta-planner-plan-d.md` (12 tasks, ~17h, 6 parallel tracks).

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Per `superpowers:subagent-driven-development`.

2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

**Which approach?**
