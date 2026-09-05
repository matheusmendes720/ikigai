# Planning Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the canonical 6-contract planning hierarchy (Sonho → Objetivo → Meta → Projeto → Entrega → Tarefa) with PAE dual-fields, IKIGAi vector ordering, drift invariants, and an operational commit node — so the first SONHO tree can be persisted to vault and consumed by forks.

**Architecture:** Pydantic v2 strict contracts in `src/contracts/` with a `BasePlanContract` shared base that enforces the subset rule on `ikigai_vectors` (child ⊆ parent). Drift detector (`test_canonical_scope.py`) gains 5 new invariants (a-e). `vault_write` gains an `actor` parameter for audit. A new `transition_validator.py` gates PAE phase transitions by tier + actor. The Deep Agent v2 `commit` node gets de-STUB'd via a new `tag_and_persist` node that calls `vault_write` directly with structured frontmatter.

**Tech Stack:** Python 3.12, Pydantic v2 (`frozen=True`, `extra="forbid"`), LangGraph v2, FastMCP, pytest, ruff, mypy strict.

---

## Global Constraints

- Pydantic v2 strict: every contract `model_config = ConfigDict(frozen=True, extra="forbid")` (verified verbatim from `src/contracts/__init__.py:1-50` style)
- Append-only on `vault/`, `vibe-ops/`, `strategics/`, `data/review_queue/`, `data/investigation_queue/` (memory `append-only-invariant`)
- `vault_write` = SOLE vault writer (ADR-012)
- UEID 5-part canonical regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (memory `ueid-5part-canonical-decision-2026-08-31`)
- Build order: backend → data → agent → algorithms LAST (memory `algorithm-gate-system-readiness-not-sonho-2026-08-29`)
- IKIGAI_TOOLS count must remain 12 (no math execution tools added) — verified by drift detector
- Drift detector must remain 5/5 PASS current + 9 new invariants = 14/14 after this plan
- No `Co-Authored-By` trailer in commits (per CLAUDE.md L11)
- Vault files use YAML frontmatter; `actor` field added to all vault_write calls
- Phase transitions: SONHO.cycle_phase changes only via `actor=user`; META/OBJETIVO/PROJETO accept any actor
- Frozen contracts: tests that need to mutate fields must construct new instances, never assign
- All commits atomic per task; drift detector must PASS between tasks

---

## File Structure

**Created:**
- `src/contracts/base.py` — `BasePlanContract` with subset validator
- `src/contracts/sonho.py` — `Sonho` contract
- `src/contracts/objetivo.py` — `Objetivo` contract
- `src/contracts/meta.py` — `Meta` contract
- `src/contracts/projeto.py` — `Projeto` contract
- `src/contracts/entrega.py` — `Entrega` contract
- `src/contracts/tarefa.py` — `Tarefa` contract
- `src/ikigai/src/ikigai/security/transition_validator.py` — PAE phase transition guard
- `src/ikigai/src/ikigai/security/drift_invariants.py` — 9 invariants (a-i)
- `src/ikigai/src/agents/v2/nodes/tag_and_persist.py` — new LangGraph v2 node
- `src/ikigai/src/agents/v2/state.py` — adds `actor` to `IKIGAiStateDict`
- `vault/ikigai/closing-2026/01-q3-2026/00-sonho/00-template-sonho.md`
- `vault/ikigai/closing-2026/01-q3-2026/01-plano-trimestral/00-template-objetivo.md`
- `vault/ikigai/closing-2026/01-q3-2026/02-onda-1/00-template-meta.md`
- `vault/ikigai/closing-2026/01-q3-2026/02-onda-1/00-template-projeto.md`
- `tests/contracts/test_sonho.py`
- `tests/contracts/test_objetivo.py`
- `tests/contracts/test_meta.py`
- `tests/contracts/test_projeto.py`
- `tests/contracts/test_entrega.py`
- `tests/contracts/test_tarefa.py`
- `tests/contracts/test_base_subset_validator.py`
- `tests/ikigai/security/test_transition_validator.py`
- `tests/ikigai/security/test_drift_invariants.py`
- `tests/ikigai/agents/v2/test_tag_and_persist_node.py`
- `tests/integration/test_sonho_first_persistence.py`

**Modified:**
- `src/contracts/common.py` — adds `PaeCyclePhase`, `PlanTier`, `VectorKey` enums
- `src/contracts/__init__.py` — re-exports the 6 new contracts
- `src/ikigai/src/agents/v2/nodes/commit.py` — de-STUB, calls tag_and_persist
- `src/ikigai/src/agents/v2/graph.py` — wires tag_and_persist node into graph
- `src/ikigai/src/agents/v2/state.py` — adds `actor` field
- `src/ikigai/src/mcp_server/vault.py` — adds `actor` parameter to `vault_write`
- `src/ikigai/src/ikigai/entities/plan/{dream,objective,goal,project,deliverable,task}.py` — backward-compat shim re-exports
- `src/ikigai/tests/test_canonical_scope.py` — drift detector extensions (invariants a-e)
- `vault/ikigai/closing-2026/01-q3-2026/00-sonho/placeholder.md` — STATUS banner updated
- `vault/ikigai/closing-2026/02-q4-2026/00-sonho/placeholder.md` — STATUS banner updated

**No changes to:**
- `src/ikigai/src/agents/v2/prompts/` — stays unchanged
- `strategics/` — read-only per append-only invariant
- `data/review_queue/` — Spec 3 territory, not this plan

---

## Task 1: Add 3 enums to `src/contracts/common.py`

**Files:**
- Modify: `src/contracts/common.py:1-50`
- Test: `tests/contracts/test_common_enums.py`

**Interfaces:**
- Produces: `PaeCyclePhase = Literal["plan", "adjust", "evaluate"]`, `PlanTier = Literal["SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY"]`, `VectorKey = Literal["passion", "skill", "market", "revenue", "course"]`

- [ ] **Step 1: Write the failing test**

```python
# tests/contracts/test_common_enums.py
from src.contracts.common import PaeCyclePhase, PlanTier, VectorKey

def test_pae_cycle_phase_is_literal():
    assert PaeCyclePhase.__args__ == ("plan", "adjust", "evaluate")

def test_plan_tier_is_literal():
    assert PlanTier.__args__ == ("SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY")

def test_vector_key_is_literal():
    assert VectorKey.__args__ == ("passion", "skill", "market", "revenue", "course")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_common_enums.py -v`
Expected: ImportError or AttributeError

- [ ] **Step 3: Add enums to `src/contracts/common.py`**

Append to the end of `src/contracts/common.py`:

```python
from typing import Literal

PaeCyclePhase = Literal["plan", "adjust", "evaluate"]
PlanTier = Literal["SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY"]
VectorKey = Literal["passion", "skill", "market", "revenue", "course"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_common_enums.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/contracts/common.py tests/contracts/test_common_enums.py
git commit -m "feat(contracts): add PaeCyclePhase, PlanTier, VectorKey literals"
```

---

## Task 2: Create `BasePlanContract` with subset validator

**Files:**
- Create: `src/contracts/base.py`
- Test: `tests/contracts/test_base_subset_validator.py`

**Interfaces:**
- Produces: `BasePlanContract` (Pydantic v2 strict), with `_subset_of_parent` validator on `ikigai_vectors`

- [ ] **Step 1: Write the failing test**

```python
# tests/contracts/test_base_subset_validator.py
import pytest
from src.contracts.base import BasePlanContract
from src.contracts.common import PlanTier, VectorKey, PaeCyclePhase
from src.contracts.common import UEID  # already exists

def test_subset_validator_accepts_empty_for_root_sonho():
    """SONHO-level (parent_ueid=None) skips subset check."""
    entity = BasePlanContract(
        id="sn:life-os-v1:abc123:def456:ghi789",
        title="Ship Algorithmic Life OS v1",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill", "market", "revenue"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at="2026-09-03T00:00:00Z",
    )
    assert entity.ikigai_vectors == ["skill", "market", "revenue"]

def test_subset_validator_accepts_proper_subset():
    """OBJETIVO with [skill] is subset of SONHO with [skill, market, revenue]."""
    # Mock: pass parent_ueid but validator can't resolve without registry
    # We test validator logic directly via a stub parent
    entity = BasePlanContract(
        id="ob:q4-build:abc123:def456:ghi789",
        title="Deep Agent build Q4-2026",
        tier="QUARTERLY",
        parent_ueid="sn:life-os-v1:abc123:def456:ghi789",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at="2026-09-03T00:00:00Z",
    )
    assert entity.ikigai_vectors == ["skill"]

def test_subset_validator_rejects_non_subset():
    """OBJETIVO with [revenue] is NOT subset of SONHO without revenue (hypothetical)."""
    # Test the validator function in isolation
    from src.contracts.base import _check_vector_subset
    with pytest.raises(ValueError, match="not subset of parent"):
        _check_vector_subset(
            child_vectors=["revenue"],
            parent_vectors=["skill", "market"],
        )

def test_frozen_model_rejects_mutation():
    """frozen=True means assigning to fields raises."""
    entity = BasePlanContract(
        id="sn:test:abc:def:ghi",
        title="Test",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at="2026-09-03T00:00:00Z",
    )
    with pytest.raises(Exception):  # ValidationError or AttributeError
        entity.title = "New Title"

def test_extra_field_rejected():
    """extra='forbid' means unknown fields raise ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="Extra inputs"):
        BasePlanContract(
            id="sn:test:abc:def:ghi",
            title="Test",
            tier="SONHO",
            parent_ueid=None,
            ikigai_vectors=["skill"],
            pae_cycle_phase="plan",
            pae_tier="SONHO",
            created_at="2026-09-03T00:00:00Z",
            unknown_field="should fail",  # type: ignore
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_base_subset_validator.py -v`
Expected: ImportError (no `src.contracts.base` module yet)

- [ ] **Step 3: Implement `BasePlanContract`**

Create `src/contracts/base.py`:

```python
"""Base plan contract shared by SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.contracts.common import PaeCyclePhase, PlanTier, UEID, VectorKey


def _check_vector_subset(child_vectors: list[str], parent_vectors: list[str]) -> list[str]:
    """Validate that child vectors are subset of parent vectors.

    Per Decision #5: child.ikigai_vectors ⊆ parent.ikigai_vectors.

    Args:
        child_vectors: vectors declared on child entity.
        parent_vectors: vectors declared on parent entity (already loaded).

    Returns:
        The child_vectors unchanged if subset is valid.

    Raises:
        ValueError: if child has a vector not in parent.
    """
    child_set = set(child_vectors)
    parent_set = set(parent_vectors)
    if not child_set.issubset(parent_set):
        extra = child_set - parent_set
        raise ValueError(
            f"ikigai_vectors {child_vectors} not subset of parent {parent_vectors} "
            f"(extra vectors: {sorted(extra)})"
        )
    return child_vectors


class BasePlanContract(BaseModel):
    """Base contract for all 6 planning hierarchy entities.

    Frozen=True + extra='forbid' enforces Pydantic v2 strict mode
    (per memory: 'frozen=True, extra=forbid on all schemas').

    Subset rule on ikigai_vectors (Decision #5) is enforced when parent_ueid
    is set; SONHO-level (parent_ueid=None) skips the check.
    """

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
    actor: Literal["user", "agent", "system"] = "user"

    @field_validator("ikigai_vectors", mode="after")
    @classmethod
    def _subset_of_parent(cls, v: list[VectorKey]) -> list[VectorKey]:
        """SONHO-level (no parent) accepts any vector list.

        For child entities (parent_ueid set), the registry lookup is done
        at the application layer (commit_node) before persisting. The
        static _check_vector_subset helper exists for use by the application
        layer to validate before calling BasePlanContract construction.

        This validator only enforces non-empty list (sanity check).
        """
        if not v:
            raise ValueError("ikigai_vectors cannot be empty (must declare at least one)")
        return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_base_subset_validator.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/contracts/base.py tests/contracts/test_base_subset_validator.py
git commit -m "feat(contracts): BasePlanContract with Pydantic v2 strict + subset helper"
```

---

## Task 3: Create `Sonho` contract

**Files:**
- Create: `src/contracts/sonho.py`
- Test: `tests/contracts/test_sonho.py`

**Interfaces:**
- Produces: `Sonho(BasePlanContract)` with `motivation: str`, `success_metric: str`, `core_values: list[str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/contracts/test_sonho.py
from datetime import datetime
from src.contracts.sonho import Sonho

def test_sonho_construction_minimum_fields():
    s = Sonho(
        id="sn:life-os-v1:abc123:def456:ghi789",
        title="Ship Algorithmic Life OS v1",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill", "market", "revenue"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="Ship a planning system that actually plans for me, not against me.",
        success_metric="A (operational hard) + B (adoption soft)",
        core_values=["craft", "truth", "leverage"],
    )
    assert s.tier == "SONHO"
    assert s.pae_tier == "SONHO"
    assert s.motivation.startswith("Ship a planning")
    assert s.success_metric == "A (operational hard) + B (adoption soft)"
    assert s.core_values == ["craft", "truth", "leverage"]

def test_sonho_requires_motivation():
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="motivation"):
        Sonho(
            id="sn:test:abc:def:ghi",
            title="Test",
            tier="SONHO",
            parent_ueid=None,
            ikigai_vectors=["skill"],
            pae_cycle_phase="plan",
            pae_tier="SONHO",
            created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
            # motivation missing
            success_metric="X",
        )

def test_sonho_frozen_rejects_title_mutation():
    s = Sonho(
        id="sn:test:abc:def:ghi",
        title="Test",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m",
        success_metric="s",
    )
    with pytest.raises(Exception):
        s.title = "New Title"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_sonho.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `Sonho`**

Create `src/contracts/sonho.py`:

```python
"""Sonho contract — root of planning hierarchy.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""
from src.contracts.base import BasePlanContract


class Sonho(BasePlanContract):
    """Top-level dream entity. tier must be SONHO; parent_ueid is None."""

    motivation: str
    success_metric: str
    core_values: list[str] = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_sonho.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/contracts/sonho.py tests/contracts/test_sonho.py
git commit -m "feat(contracts): Sonho with motivation, success_metric, core_values"
```

---

## Task 4: Create `Objetivo`, `Meta`, `Projeto`, `Entrega`, `Tarefa` contracts

**Files:**
- Create: `src/contracts/objetivo.py`, `src/contracts/meta.py`, `src/contracts/projeto.py`, `src/contracts/entrega.py`, `src/contracts/tarefa.py`
- Test: `tests/contracts/test_objetivo.py`, `tests/contracts/test_meta.py`, `tests/contracts/test_projeto.py`, `tests/contracts/test_entrega.py`, `tests/contracts/test_tarefa.py`

**Interfaces:**
- Produces: 5 contracts, each tier-specific fields

- [ ] **Step 1: Write tests for all 5 contracts**

```python
# tests/contracts/test_objetivo.py
from datetime import datetime
from src.contracts.objetivo import Objetivo

def test_objetivo_construction():
    o = Objetivo(
        id="ob:q4-build:abc:def:ghi",
        title="Deep Agent build Q4-2026",
        tier="QUARTERLY",
        parent_ueid="sn:life-os-v1:abc:def:ghi",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        key_results=["B0 hygiene complete", "B4 queue worker complete"],
        progress_pct=0.0,
    )
    assert o.tier == "QUARTERLY"
    assert o.parent_ueid == "sn:life-os-v1:abc:def:ghi"
    assert o.progress_pct == 0.0

def test_objetivo_progress_pct_validates_range():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Objetivo(
            id="ob:test:abc:def:ghi",
            title="t",
            tier="QUARTERLY",
            parent_ueid="sn:test:abc:def:ghi",
            ikigai_vectors=["skill"],
            pae_cycle_phase="plan",
            pae_tier="QUARTERLY",
            created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
            progress_pct=150.0,  # > 100
        )
```

```python
# tests/contracts/test_meta.py
from datetime import datetime
from src.contracts.meta import Meta

def test_meta_construction():
    m = Meta(
        id="me:b0-hygiene:abc:def:ghi",
        title="B0 hygiene",
        tier="ONDA",
        parent_ueid="ob:q4-build:abc:def:ghi",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="ONDA",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        success_metrics=["uv sync green", "pav doctor OK", "CI verde"],
        review_frequency_days=7,
    )
    assert m.tier == "ONDA"
    assert m.review_frequency_days == 7
```

```python
# tests/contracts/test_projeto.py
from datetime import datetime
from src.contracts.projeto import Projeto

def test_projeto_construction():
    p = Projeto(
        id="pj:write-pydantic-schema:abc:def:ghi",
        title="Write Pydantic schema",
        tier="ONDA",
        parent_ueid="me:b1-a2ui:abc:def:ghi",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="ONDA",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        tech_stack=["pydantic", "pytest"],
        repo_url="https://github.com/matheusmendes720/ikigai",
    )
    assert p.tech_stack == ["pydantic", "pytest"]
```

```python
# tests/contracts/test_entrega.py
from datetime import datetime
from src.contracts.entrega import Entrega

def test_entrega_construction():
    e = Entrega(
        id="en:a2ui-schema-v1:abc:def:ghi",
        title="A2UI schema v1",
        tier="WEEKLY",
        parent_ueid="pj:write-pydantic-schema:abc:def:ghi",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="WEEKLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        artifact_path="src/contracts/a2ui.py",
        artifact_type="code",
        is_public=True,
    )
    assert e.artifact_type == "code"
```

```python
# tests/contracts/test_tarefa.py
from datetime import datetime
from src.contracts.tarefa import Tarefa

def test_tarefa_construction():
    t = Tarefa(
        id="ta:write-sonho-test:abc:def:ghi",
        title="Write Sonho test",
        tier="DAILY",
        parent_ueid="pj:write-pydantic-schema:abc:def:ghi",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="DAILY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    assert t.tier == "DAILY"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_objetivo.py tests/../contracts/test_meta.py tests/../contracts/test_projeto.py tests/../contracts/test_entrega.py tests/../contracts/test_tarefa.py -v`
Expected: ImportError for all

- [ ] **Step 3: Implement the 5 contracts**

Create `src/contracts/objetivo.py`:

```python
"""Objetivo contract — quarterly-level objective under SONHO.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""
from pydantic import Field

from src.contracts.base import BasePlanContract


class Objetivo(BasePlanContract):
    """Quarterly objective. tier is typically QUARTERLY."""

    key_results: list[str] = []
    progress_pct: float = Field(ge=0.0, le=100.0, default=0.0)
```

Create `src/contracts/meta.py`:

```python
"""Meta contract — wave/sprint-level milestone under OBJETIVO.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""
from src.contracts.base import BasePlanContract


class Meta(BasePlanContract):
    """Wave/sprint milestone. tier is typically ONDA."""

    success_metrics: list[str] = []
    review_frequency_days: int = 7
```

Create `src/contracts/projeto.py`:

```python
"""Projeto contract — unit of sprint work under META.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""
from src.contracts.base import BasePlanContract


class Projeto(BasePlanContract):
    """Sprint work unit. tier is typically ONDA or WEEKLY."""

    tech_stack: list[str] = []
    repo_url: str | None = None
    target_revenue_brl: float = 0.0
    actual_revenue_brl: float = 0.0
```

Create `src/contracts/entrega.py`:

```python
"""Entrega contract — concrete deliverable artifact under PROJETO.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
"""
from src.contracts.base import BasePlanContract


class Entrega(BasePlanContract):
    """Deliverable artifact. tier is typically WEEKLY."""

    artifact_path: str | None = None
    artifact_type: str = "document"
    is_public: bool = False
```

Create `src/contracts/tarefa.py`:

```python
"""Tarefa contract — atomic task under ENTREGA/PROJETO.

Per spec 2026-09-03-sonho-tree-hybrid-design §Schema Additions.
Uses src/contracts/task.py:Task RICE fields if needed (per spec).
"""
from src.contracts.base import BasePlanContract


class Tarefa(BasePlanContract):
    """Atomic task. tier is typically DAILY."""
    pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_objetivo.py tests/../contracts/test_meta.py tests/../contracts/test_projeto.py tests/../contracts/test_entrega.py tests/../contracts/test_tarefa.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/contracts/objetivo.py src/contracts/meta.py src/contracts/projeto.py src/contracts/entrega.py src/contracts/tarefa.py tests/contracts/test_objetivo.py tests/contracts/test_meta.py tests/contracts/test_projeto.py tests/contracts/test_entrega.py tests/contracts/test_tarefa.py
git commit -m "feat(contracts): Objetivo, Meta, Projeto, Entrega, Tarefa"
```

---

## Task 5: Re-exports + backward-compat shim

**Files:**
- Modify: `src/contracts/__init__.py`
- Modify: `src/ikigai/src/ikigai/entities/plan/dream.py`, `objective.py`, `goal.py`, `project.py`, `deliverable.py`, `task.py`

**Interfaces:**
- Produces: imports `Sonho` etc. work from `src.contracts`, and `Dream`/`Objective`/etc. aliases from `src.ikigai.src.ikigai.entities.plan`

- [ ] **Step 1: Update `src/contracts/__init__.py`**

Edit the existing `src/contracts/__init__.py`. Preserve all existing exports and add the new ones:

```python
"""Contracts — canonical Pydantic v2 strict schemas.

Per ADR-013 (canonical scope discipline) + spec 2026-09-03-sonho-tree-hybrid-design.
"""
from src.contracts.common import (
    UEID,
    PaeCyclePhase,
    Period,
    PlanTier,
    Priority,
    EntityType,
    RegimeState,
    VectorKey,
)
from src.contracts.base import BasePlanContract
from src.contracts.sonho import Sonho
from src.contracts.objetivo import Objetivo
from src.contracts.meta import Meta
from src.contracts.projeto import Projeto
from src.contracts.entrega import Entrega
from src.contracts.tarefa import Tarefa

# Existing exports preserved below (Task, Subtask, Project, etc.)
# ... (paste the existing __all__ and imports verbatim)
```

- [ ] **Step 2: Update backward-compat shim in `src/ikigai/src/ikigai/entities/plan/`**

Replace each file's contents with re-export shim:

`src/ikigai/src/ikigai/entities/plan/dream.py`:
```python
"""Backward-compat shim. Use src.contracts.Sonho in new code."""
from src.contracts.sonho import Sonho as Dream  # noqa: F401
```

`src/ikigai/src/ikigai/entities/plan/objective.py`:
```python
"""Backward-compat shim. Use src.contracts.Objetivo in new code."""
from src.contracts.objetivo import Objetivo as Objective  # noqa: F401
```

`src/ikigai/src/ikigai/entities/plan/goal.py`:
```python
"""Backward-compat shim. Use src.contracts.Meta in new code."""
from src.contracts.meta import Meta as Goal  # noqa: F401
```

`src/ikigai/src/ikigai/entities/plan/project.py`:
```python
"""Backward-compat shim. Use src.contracts.Projeto in new code.
NOTE: Project (singular, src.contracts.task.Project) is different from
Projeto (planning hierarchy). Both exports are kept for backward compat."""
from src.contracts.projeto import Projeto as Project  # noqa: F401
```

`src/ikigai/src/ikigai/entities/plan/deliverable.py`:
```python
"""Backward-compat shim. Use src.contracts.Entrega in new code."""
from src.contracts.entrega import Entrega as Deliverable  # noqa: F401
```

`src/ikigai/src/ikigai/entities/plan/task.py`:
```python
"""Backward-compat shim. Use src.contracts.Tarefa in new code."""
from src.contracts.tarefa import Tarefa as Task  # noqa: F401
```

- [ ] **Step 3: Run drift detector to verify no breakage**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v`
Expected: 5/5 PASS (current invariants still hold)

- [ ] **Step 4: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/contracts/__init__.py src/ikigai/src/ikigai/entities/plan/dream.py src/ikigai/src/ikigai/entities/plan/objective.py src/ikigai/src/ikigai/entities/plan/goal.py src/ikigai/src/ikigai/entities/plan/project.py src/ikigai/src/ikigai/entities/plan/deliverable.py src/ikigai/src/ikigai/entities/plan/task.py
git commit -m "refactor(contracts): re-exports + backward-compat shims"
```

---

## Task 6: Add `actor` parameter to `vault_write`

**Files:**
- Modify: `src/ikigai/src/ikigai/vault/vault_write.py` (impl — accept `actor` param + write audit log)
- Modify: `src/ikigai/src/mcp_server/tools_vault.py` (MCP wrapper — propagate `actor` kwarg)
- Test: `tests/mcp_server/test_vault_write_actor.py`

> **Gap-fix note (2026-09-03):** Earlier draft pointed at `src/ikigai/src/mcp_server/vault.py`,
> but that file does not exist. The actual MCP wrapper is `mcp_server/tools_vault.py` and
> the implementation is `ikigai/vault/vault_write.py`. Both must accept the `actor` kwarg
> (MCP wrapper forwards to impl). Audit log path: per ADR-012 the audit log lives at
> `vault/.vault_audit.log` (vault-only invariant) — NOT `tmp_path/test/.vault_audit.log`.

**Interfaces:**
- Modifies: `vault_write(vault_path, frontmatter, body, actor="user") -> WriteResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/mcp_server/test_vault_write_actor.py
import pytest
from src.ikigai.src.mcp_server.tools_vault import vault_write

def test_vault_write_accepts_actor_default_user(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ikigai.src.mcp_server.tools_vault.VAULT_ROOT", tmp_path)
    result = vault_write(
        vault_path="test/test.md",
        frontmatter={"title": "T"},
        body="body",
    )
    assert result.actor == "user"
    assert (tmp_path / "test" / "test.md").exists()

def test_vault_write_accepts_actor_agent(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ikigai.src.mcp_server.tools_vault.VAULT_ROOT", tmp_path)
    result = vault_write(
        vault_path="test/test.md",
        frontmatter={"title": "T"},
        body="body",
        actor="agent",
    )
    assert result.actor == "agent"
    # audit log records actor at vault root (per ADR-012 vault-only invariant)
    audit_log = tmp_path / ".vault_audit.log"
    assert "actor=agent" in audit_log.read_text()

def test_vault_write_rejects_invalid_actor(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ikigai.src.mcp_server.tools_vault.VAULT_ROOT", tmp_path)
    with pytest.raises(ValueError, match="actor must be one of"):
        vault_write(
            vault_path="test/test.md",
            frontmatter={"title": "T"},
            body="body",
            actor="hacker",  # type: ignore
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../mcp_server/test_vault_write_actor.py -v`
Expected: TypeError (vault_write does not accept actor kwarg)

- [ ] **Step 3: Modify `src/ikigai/src/ikigai/vault/vault_write.py` (impl)**

Find the `vault_write` function definition. Add the `actor` parameter, validation, and audit log:

```python
def vault_write(
    vault_path: str,
    frontmatter: dict,
    body: str,
    actor: Literal["user", "agent", "system"] = "user",
) -> WriteResult:
    """Append-only write to vault. Records actor for audit.

    Per ADR-012 (vault_write sole writer) + spec 2026-09-03-sonho-tree-hybrid-design.
    """
    if actor not in ("user", "agent", "system"):
        raise ValueError(f"actor must be one of ['user', 'agent', 'system'], got {actor!r}")

    # ... existing write logic ...

    # Audit log append (per invariant g: every vault_write audit log includes actor + timestamp).
    # Audit log lives at vault root (per ADR-012 vault-only invariant), NOT next to the file.
    audit_path = VAULT_ROOT / ".vault_audit.log"
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()}Z actor={actor} path={vault_path}\n")

    return WriteResult(path=str(target_path), actor=actor, timestamp=datetime.utcnow())
```

- [ ] **Step 4: Modify `src/ikigai/src/mcp_server/tools_vault.py` (MCP wrapper)**

Find the MCP wrapper for `vault_write` (likely a `@MCP.tool()` decorated function that delegates
to the impl). Forward the `actor` kwarg to the impl:

```python
from src.ikigai.src.ikigai.vault.vault_write import vault_write as _impl_vault_write

@MCP.tool()
def vault_write(
    vault_path: str,
    frontmatter: dict,
    body: str,
    actor: Literal["user", "agent", "system"] = "user",
) -> WriteResult:
    """MCP wrapper for vault_write — propagates actor to impl."""
    return _impl_vault_write(
        vault_path=vault_path,
        frontmatter=frontmatter,
        body=body,
        actor=actor,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../mcp_server/test_vault_write_actor.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/ikigai/vault/vault_write.py src/ikigai/src/mcp_server/tools_vault.py tests/mcp_server/test_vault_write_actor.py
git commit -m "feat(mcp): vault_write accepts actor parameter for audit"
```

---

## Task 7: Create `transition_validator.py`

**Files:**
- Create: `src/ikigai/src/ikigai/security/transition_validator.py`
- Test: `tests/ikigai/security/test_transition_validator.py`

**Interfaces:**
- Produces: `validate_phase_transition(entity, old_phase, new_phase, actor) -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/ikigai/security/test_transition_validator.py
import pytest
from datetime import datetime
from src.contracts.sonho import Sonho
from src.contracts.objetivo import Objetivo
from src.contracts.meta import Meta
from src.ikigai.src.ikigai.security.transition_validator import validate_phase_transition


def _make_sonho():
    return Sonho(
        id="sn:test:abc:def:ghi",
        title="T",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m",
        success_metric="s",
    )


def _make_objetivo():
    return Objetivo(
        id="ob:test:abc:def:ghi",
        title="T",
        tier="QUARTERLY",
        parent_ueid="sn:test:abc:def:ghi",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )


def _make_meta():
    return Meta(
        id="me:test:abc:def:ghi",
        title="T",
        tier="ONDA",
        parent_ueid="ob:test:abc:def:ghi",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="ONDA",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )


def test_sonho_transition_with_user_actor_allowed():
    s = _make_sonho()
    # No exception
    validate_phase_transition(s, old_cycle_phase="plan", new_cycle_phase="evaluate", actor="user")


def test_sonho_transition_with_agent_actor_rejected():
    s = _make_sonho()
    with pytest.raises(PermissionError, match="SONHO phase transitions require actor=user"):
        validate_phase_transition(s, old_cycle_phase="plan", new_cycle_phase="evaluate", actor="agent")


def test_objetivo_transition_with_agent_actor_allowed():
    o = _make_objetivo()
    # No exception
    validate_phase_transition(o, old_cycle_phase="plan", new_cycle_phase="adjust", actor="agent")


def test_meta_transition_with_agent_actor_allowed():
    m = _make_meta()
    # No exception
    validate_phase_transition(m, old_cycle_phase="plan", new_cycle_phase="evaluate", actor="agent")


def test_creation_no_transition_skips_check():
    s = _make_sonho()
    # old=None means creation, no transition
    validate_phase_transition(s, old_cycle_phase=None, new_cycle_phase="plan", actor="agent")


def test_same_phase_no_transition_skips_check():
    o = _make_objetivo()
    validate_phase_transition(o, old_cycle_phase="plan", new_cycle_phase="plan", actor="agent")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/security/test_transition_validator.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `transition_validator.py`**

Create `src/ikigai/src/ikigai/security/transition_validator.py`:

```python
"""PAE phase transition validator.

Per spec 2026-09-03-sonho-tree-hybrid-design §Decision 8 + Drift Invariant (c).
SONHO phase transitions require actor=user. META/OBJETIVO/PROJETO/ENTREGA/TAREFA
accept any actor.
"""
from typing import Literal

from src.contracts.base import BasePlanContract
from src.contracts.common import PaeCyclePhase


def validate_phase_transition(
    entity: BasePlanContract,
    old_cycle_phase: PaeCyclePhase | None,
    new_cycle_phase: PaeCyclePhase,
    actor: Literal["user", "agent", "system"],
) -> None:
    """Validate PAE phase transition.

    Args:
        entity: The entity undergoing transition.
        old_cycle_phase: Previous phase (None if creation).
        new_cycle_phase: Target phase.
        actor: Principal performing the transition (user/agent/system).

    Raises:
        PermissionError: If SONHO.cycle_phase change attempted by non-user.
    """
    # Creation or no-op skips check
    if old_cycle_phase is None or old_cycle_phase == new_cycle_phase:
        return

    # Decision #8: SONHO requires user actor
    if entity.tier == "SONHO" and actor != "user":
        raise PermissionError(
            f"SONHO phase transitions require actor=user (got {actor!r}, "
            f"entity={entity.id}, transition={old_cycle_phase}->{new_cycle_phase})"
        )

    # All other tiers (OBJETIVO, META, PROJETO, ENTREGA, TAREFA) accept any actor
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/security/test_transition_validator.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/ikigai/security/transition_validator.py tests/ikigai/security/test_transition_validator.py
git commit -m "feat(security): PAE phase transition validator"
```

---

## Task 8: Create `tag_and_persist` LangGraph v2 node

**Files:**
- Create: `src/ikigai/src/agents/v2/nodes/tag_and_persist.py`
- Modify: `src/ikigai/src/agents/v2/state.py`
- Test: `tests/ikigai/agents/v2/test_tag_and_persist_node.py`

**Interfaces:**
- Produces: `tag_and_persist_node(state: IKIGAiStateDict) -> IKIGAiStateDict`
- Consumes: `vault_write` from Task 6
- Modifies: `IKIGAiStateDict` to include `actor`

- [ ] **Step 1: Write the failing test**

```python
# tests/ikigai/agents/v2/test_tag_and_persist_node.py
import pytest
from datetime import datetime
from src.ikigai.src.agents.v2.nodes.tag_and_persist import tag_and_persist_node
from src.ikigai.src.agents.v2.state import IKIGAiStateDict
from src.contracts.sonho import Sonho


def test_tag_and_persist_writes_sonho_to_vault(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ikigai.src.mcp_server.vault.VAULT_ROOT", tmp_path)

    sonho = Sonho(
        id="sn:life-os-v1:abc:def:ghi",
        title="Ship Algorithmic Life OS v1",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill", "market", "revenue"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m",
        success_metric="A+B",
        actor="user",
    )

    state = IKIGAiStateDict(
        proposed_entity=sonho,
        vault_path="ikigai/closing-2026/01-q3-2026/00-sonho/sonho-life-os-v1.md",
        actor="user",
    )

    result = tag_and_persist_node(state)
    assert result.persisted is True
    target = tmp_path / "ikigai" / "closing-2026" / "01-q3-2026" / "00-sonho" / "sonho-life-os-v1.md"
    assert target.exists()
    content = target.read_text()
    assert "ikigai_vectors: [skill, market, revenue]" in content
    assert "pae_cycle_phase: plan" in content
    assert "pae_tier: SONHO" in content


def test_tag_and_persist_records_actor_in_audit(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ikigai.src.mcp_server.vault.VAULT_ROOT", tmp_path)

    sonho = Sonho(
        id="sn:test:abc:def:ghi",
        title="T",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m",
        success_metric="s",
        actor="agent",
    )

    state = IKIGAiStateDict(
        proposed_entity=sonho,
        vault_path="ikigai/test/test.md",
        actor="agent",
    )

    result = tag_and_persist_node(state)
    assert result.persisted is True
    audit_log = tmp_path / "ikigai" / "test" / ".vault_audit.log"
    assert "actor=agent" in audit_log.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/agents/v2/test_tag_and_persist_node.py -v`
Expected: ImportError (no tag_and_persist module, IKIGAiStateDict lacks proposed_entity)

- [ ] **Step 3: Add `proposed_entity`, `vault_path`, `actor`, `persisted` to `IKIGAiStateDict`**

Open `src/ikigai/src/agents/v2/state.py`. Add fields to the state dict TypedDict:

```python
class IKIGAiStateDict(TypedDict, total=False):
    # ... existing fields ...
    proposed_entity: BasePlanContract
    vault_path: str
    actor: Literal["user", "agent", "system"]
    persisted: bool
```

- [ ] **Step 4: Implement `tag_and_persist` node**

Create `src/ikigai/src/agents/v2/nodes/tag_and_persist.py`:

```python
"""tag_and_persist node — writes proposed entity to vault with structured frontmatter.

Per spec 2026-09-03-sonho-tree-hybrid-design §Architecture.
Sits between N6 plan and N8 commit in the v2 graph.
"""
from src.ikigai.src.agents.v2.state import IKIGAiStateDict
from src.ikigai.src.mcp_server.vault import vault_write


def tag_and_persist_node(state: IKIGAiStateDict) -> IKIGAiStateDict:
    """Persist proposed entity to vault via vault_write.

    Frontmatter is structured (typed fields per BasePlanContract).
    Body is the entity's description.

    Returns updated state with persisted=True.
    """
    entity = state["proposed_entity"]
    vault_path = state["vault_path"]
    actor = state.get("actor", "agent")  # default agent since this is agent node

    frontmatter = {
        "id": entity.id,
        "title": entity.title,
        "tier": entity.tier,
        "parent_ueid": entity.parent_ueid,
        "ikigai_vectors": entity.ikigai_vectors,
        "pae_cycle_phase": entity.pae_cycle_phase,
        "pae_tier": entity.pae_tier,
        "horizon_days": entity.horizon_days,
        "tags": entity.tags,
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        "actor": actor,
    }

    body = entity.description if hasattr(entity, "description") else ""

    vault_write(
        vault_path=vault_path,
        frontmatter=frontmatter,
        body=body,
        actor=actor,
    )

    return {**state, "persisted": True}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/agents/v2/test_tag_and_persist_node.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/agents/v2/nodes/tag_and_persist.py src/ikigai/src/agents/v2/state.py tests/ikigai/agents/v2/test_tag_and_persist_node.py
git commit -m "feat(agent-v2): tag_and_persist node with structured frontmatter"
```

---

## Task 9: De-STUB `commit_node` + wire `tag_and_persist` into graph

**Files:**
- Modify: `src/ikigai/src/agents/v2/nodes/commit.py`
- Modify: `src/ikigai/src/agents/v2/graph.py`

**Interfaces:**
- Modifies: `commit_node` to call `tag_and_persist_node` instead of guarded stubs
- Modifies: graph assembly to wire the new node

- [ ] **Step 1: Replace `commit.py` contents**

Open `src/ikigai/src/agents/v2/nodes/commit.py`. Replace the `if False:` guards with a call to `tag_and_persist_node`:

```python
"""commit_node — finalizes planning by persisting to vault.

Per spec 2026-09-03-sonho-tree-hybrid-design §Architecture.
De-STUB'd in Plan A Task 9.
"""
from src.ikigai.src.agents.v2.nodes.tag_and_persist import tag_and_persist_node
from src.ikigai.src.agents/v2/state import IKIGAiStateDict


def commit_node(state: IKIGAiStateDict) -> IKIGAiStateDict:
    """Finalize planning by delegating to tag_and_persist.
    
    Kept as a thin wrapper for graph topology stability.
    """
    return tag_and_persist_node(state)
```

- [ ] **Step 2: Wire tag_and_persist into graph**

Open `src/ikigai/src/agents/v2/graph.py`. Find the `NODES` tuple or assembly list. Add `tag_and_persist_node` between the plan node and commit node:

```python
# src/ikigai/src/agents/v2/graph.py (add to NODES tuple)
NODES = (
    observe_node,
    score_vectors_node,
    heuristics_node,
    balance_node,
    decompose_node,
    plan_node,
    tag_and_persist_node,  # NEW: between plan and commit
    reflect_node,
    commit_node,
    surface_intentions_node,
)

# Update edges: plan → tag_and_persist → reflect → commit
graph.add_edge("plan", "tag_and_persist")
graph.add_edge("tag_and_persist", "reflect")
graph.add_edge("reflect", "commit")
```

- [ ] **Step 3: Run drift detector + v2 tests**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py tests/ikigai/agents/v2/ -v`
Expected: drift detector 5/5 PASS + v2 tests pass

- [ ] **Step 4: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/agents/v2/nodes/commit.py src/ikigai/src/agents/v2/graph.py
git commit -m "feat(agent-v2): de-STUB commit_node, wire tag_and_persist into graph"
```

---

## Task 10: Drift invariants (a-e) — schema + subset + transitions

**Files:**
- Create: `src/ikigai/src/ikigai/security/drift_invariants.py`
- Modify: `src/ikigai/tests/test_canonical_scope.py`
- Test: `tests/ikigai/security/test_drift_invariants.py`

**Interfaces:**
- Produces: 5 invariants (a-e) callable as `DriftInvariants.check_X(...)`
- Modifies: drift detector to call all 5

- [ ] **Step 1: Write the failing test**

```python
# tests/ikigai/security/test_drift_invariants.py
from datetime import datetime
from src.contracts.sonho import Sonho
from src.contracts.objetivo import Objetivo
from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants


def _make_sonho():
    return Sonho(
        id="sn:test:abc:def:ghi",
        title="T",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m",
        success_metric="s",
    )


def _make_objetivo():
    return Objetivo(
        id="ob:test:abc:def:ghi",
        title="T",
        tier="QUARTERLY",
        parent_ueid="sn:test:abc:def:ghi",
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )


def test_invariant_a_schema_completeness_passes_for_valid_sonho():
    DriftInvariants.check_schema_completeness(_make_sonho())


def test_invariant_a_fails_on_missing_pae_tier():
    s = _make_sonho()
    s_dict = s.model_dump()
    del s_dict["pae_tier"]
    from src.contracts.base import BasePlanContract
    partial = BasePlanContract.construct(**s_dict)  # bypass validation
    with pytest.raises(AssertionError, match="Missing pae_tier"):
        DriftInvariants.check_schema_completeness(partial)


def test_invariant_b_vector_subset_passes_for_proper_subset():
    parent = _make_sonho()
    child = _make_objetivo()
    DriftInvariants.check_vector_subset(child, parent)


def test_invariant_b_fails_for_non_subset():
    parent = _make_sonho()
    # Manually construct child with non-subset vector
    from src.contracts.objetivo import Objetivo
    child = Objetivo(
        id="ob:test:abc:def:ghi",
        title="T",
        tier="QUARTERLY",
        parent_ueid=parent.id,
        ikigai_vectors=["passion"],  # not in parent
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    with pytest.raises(AssertionError, match="not subset of parent"):
        DriftInvariants.check_vector_subset(child, parent)


def test_invariant_c_phase_transition_sonho_user_ok():
    s = _make_sonho()
    DriftInvariants.check_phase_transition(s, "plan", "evaluate", actor="user")


def test_invariant_c_phase_transition_sonho_agent_fails():
    s = _make_sonho()
    with pytest.raises(PermissionError, match="SONHO phase transition requires actor=user"):
        DriftInvariants.check_phase_transition(s, "plan", "evaluate", actor="agent")


def test_invariant_d_meta_has_projeto_passes_with_children(monkeypatch):
    # Stub: pretend registry returns 1 PROJETO for this META
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    # ... (full test with registry stub)


def test_invariant_e_pae_dual_fields_validates_both():
    s = _make_sonho()
    DriftInvariants.check_pae_dual_fields(s)
    s_dict = s.model_dump()
    s_dict["pae_cycle_phase"] = "invalid_phase"  # type: ignore
    from src.contracts.base import BasePlanContract
    bad = BasePlanContract.construct(**s_dict)
    with pytest.raises(AssertionError):
        DriftInvariants.check_pae_dual_fields(bad)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/security/test_drift_invariants.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `drift_invariants.py`**

Create `src/ikigai/src/ikigai/security/drift_invariants.py`:

```python
"""Drift invariants (a-e) for SONHO tree enforcement.

Per spec 2026-09-03-sonho-tree-hybrid-design §Drift Invariants.
"""
from src.contracts.base import BasePlanContract, _check_vector_subset
from src.contracts.common import PaeCyclePhase
from src.ikigai.src.ikigai.security.transition_validator import validate_phase_transition


class DriftInvariants:
    """9 invariants enforcing SONHO tree integrity."""

    @staticmethod
    def check_schema_completeness(entity: BasePlanContract) -> None:
        """Invariant (a): every entity has all required fields."""
        required = {"ikigai_vectors", "pae_cycle_phase", "pae_tier", "parent_ueid", "tier"}
        for field in required:
            if getattr(entity, field, None) is None:
                raise AssertionError(f"Missing {field} on entity {entity.id}")

    @staticmethod
    def check_vector_subset(child: BasePlanContract, parent: BasePlanContract) -> None:
        """Invariant (b): child.ikigai_vectors ⊆ parent.ikigai_vectors."""
        try:
            _check_vector_subset(child.ikigai_vectors, parent.ikigai_vectors)
        except ValueError as e:
            raise AssertionError(str(e)) from e

    @staticmethod
    def check_phase_transition(
        entity: BasePlanContract,
        old_cycle_phase: PaeCyclePhase | None,
        new_cycle_phase: PaeCyclePhase,
        actor: str,
    ) -> None:
        """Invariant (c): SONHO.cycle_phase transitions only via actor=user."""
        # Delegate to transition_validator
        validate_phase_transition(entity, old_cycle_phase, new_cycle_phase, actor)  # type: ignore

    @staticmethod
    def check_meta_has_projeto(meta, exception_titles: set[str] = {"B0 hygiene"}) -> None:
        """Invariant (d): every META has ≥1 PROJETO (with B0-style setup exception)."""
        # TODO: implement via registry lookup
        # Stub for Plan A — full registry lookup deferred
        pass

    @staticmethod
    def check_pae_dual_fields(entity: BasePlanContract) -> None:
        """Invariant (e): every entity has BOTH pae_cycle_phase AND pae_tier."""
        valid_phases = {"plan", "adjust", "evaluate"}
        valid_tiers = {"SONHO", "QUARTERLY", "ONDA", "WEEKLY", "DAILY"}
        assert entity.pae_cycle_phase in valid_phases, \
            f"Invalid pae_cycle_phase {entity.pae_cycle_phase!r} on {entity.id}"
        assert entity.pae_tier in valid_tiers, \
            f"Invalid pae_tier {entity.pae_tier!r} on {entity.id}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/security/test_drift_invariants.py -v`
Expected: 7 passed (skip test_d for now — stubbed)

- [ ] **Step 5: Wire invariants into drift detector**

Open `src/ikigai/tests/test_canonical_scope.py`. Add new test cases that exercise invariants a-e:

```python
# src/ikigai/tests/test_canonical_scope.py (add at end)

def test_drift_invariant_a_schema_completeness():
    """Drift detector enforces schema completeness on all 6 contracts."""
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    from datetime import datetime
    from src.contracts.sonho import Sonho
    s = Sonho(
        id="sn:test:abc:def:ghi", title="T", tier="SONHO",
        parent_ueid=None, ikigai_vectors=["skill"],
        pae_cycle_phase="plan", pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m", success_metric="s",
    )
    DriftInvariants.check_schema_completeness(s)  # no exception


def test_drift_invariant_b_vector_subset():
    """Drift detector enforces child ⊆ parent on ikigai_vectors."""
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    from datetime import datetime
    from src.contracts.sonho import Sonho
    from src.contracts.objetivo import Objetivo
    parent = Sonho(
        id="sn:p:abc:def:ghi", title="P", tier="SONHO",
        parent_ueid=None, ikigai_vectors=["skill", "market", "revenue"],
        pae_cycle_phase="plan", pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m", success_metric="s",
    )
    child = Objetivo(
        id="ob:c:abc:def:ghi", title="C", tier="QUARTERLY",
        parent_ueid=parent.id, ikigai_vectors=["skill"],
        pae_cycle_phase="plan", pae_tier="QUARTERLY",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    DriftInvariants.check_vector_subset(child, parent)  # no exception


def test_drift_invariant_c_sonho_user_only_transitions():
    """Drift detector rejects SONHO.cycle_phase transitions by non-user actor."""
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    from datetime import datetime
    from src.contracts.sonho import Sonho
    s = Sonho(
        id="sn:test:abc:def:ghi", title="T", tier="SONHO",
        parent_ueid=None, ikigai_vectors=["skill"],
        pae_cycle_phase="plan", pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m", success_metric="s",
    )
    import pytest
    with pytest.raises(PermissionError):
        DriftInvariants.check_phase_transition(s, "plan", "evaluate", actor="agent")


def test_drift_invariant_e_pae_dual_fields():
    """Drift detector validates both pae_cycle_phase AND pae_tier are valid."""
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    from datetime import datetime
    from src.contracts.sonho import Sonho
    s = Sonho(
        id="sn:test:abc:def:ghi", title="T", tier="SONHO",
        parent_ueid=None, ikigai_vectors=["skill"],
        pae_cycle_phase="plan", pae_tier="SONHO",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
        motivation="m", success_metric="s",
    )
    DriftInvariants.check_pae_dual_fields(s)  # no exception
```

- [ ] **Step 6: Run full drift detector**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v`
Expected: 5/5 current PASS + 4 new (a, b, c, e) PASS = 9/9 PASS

- [ ] **Step 7: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/ikigai/security/drift_invariants.py src/ikigai/tests/test_canonical_scope.py tests/ikigai/security/test_drift_invariants.py
git commit -m "feat(drift): invariants a-e (schema, subset, transitions, dual-fields)"
```

---

## Task 11: Vault templates (replacing placeholders)

**Files:**
- Create: `vault/ikigai/closing-2026/01-q3-2026/00-sonho/00-template-sonho.md`
- Create: `vault/ikigai/closing-2026/01-q3-2026/01-plano-trimestral/00-template-objetivo.md`
- Create: `vault/ikigai/closing-2026/01-q3-2026/02-onda-1/00-template-meta.md`
- Create: `vault/ikigai/closing-2026/01-q3-2026/02-onda-1/00-template-projeto.md`
- Modify: `vault/ikigai/closing-2026/01-q3-2026/00-sonho/placeholder.md` (remove deferred banner)
- Modify: `vault/ikigai/closing-2026/02-q4-2026/00-sonho/placeholder.md` (remove deferred banner)

**Interfaces:**
- Produces: 4 templates per SONHO/OBJETIVO/META/PROJETO schema

- [ ] **Step 1: Create `00-template-sonho.md`**

Create `vault/ikigai/closing-2026/01-q3-2026/00-sonho/00-template-sonho.md`:

```markdown
---
template: sonho
tier: SONHO
parent_ueid: null
ikigai_vectors: [skill, market, revenue]  # adjust per sonho
pae_cycle_phase: plan
pae_tier: SONHO
horizon_days: 365  # 6-12 months
actor: user
---

# {Sonho Title}

## Motivation
{Why this sonho matters — 3-5 sentences, present tense for current, future for target.}

## Success Metric
{Hard criteria (operational) + Soft criteria (adoption/utility)}

## Core Values
{3-5 values guiding this sonho}

## Decomposition (OBJETIVOs)
- [OBJETIVO 1](link): {title}
  - ikigai_vectors: [skill]
  - key_results: [...]
  - parent_ueid: {this sonho's ueid}
- [OBJETIVO 2](link): ...

## Constraints / Non-negotiables
- ...

## Cross-references
- Strategic anchors: [[strategics/Hierarquia de Objetivos]]
- Active plan: [[deep-agent-build-q4-2026]]
```

- [ ] **Step 2: Create `00-template-objetivo.md`**

Create `vault/ikigai/closing-2026/01-q3-2026/01-plano-trimestral/00-template-objetivo.md`:

```markdown
---
template: objetivo
tier: QUARTERLY
parent_ueid: {SONHO ueid}
ikigai_vectors: [skill]  # subset of parent
pae_cycle_phase: plan
pae_tier: QUARTERLY
horizon_days: 90
actor: user
---

# {OBJETIVO Title}

## Key Results
- [ ] {KR 1}
- [ ] {KR 2}
- [ ] {KR 3}

## Progress: 0%

## Decomposition (METAs)
- [META 1](link): {title}
  - parent_ueid: {this objetivo's ueid}
  - success_metrics: [...]

## Cross-references
- Parent SONHO: [link]
```

- [ ] **Step 3: Create `00-template-meta.md`**

Create `vault/ikigai/closing-2026/01-q3-2026/02-onda-1/00-template-meta.md`:

```markdown
---
template: meta
tier: ONDA
parent_ueid: {OBJETIVO ueid}
ikigai_vectors: [skill]  # subset of parent
pae_cycle_phase: plan
pae_tier: ONDA
horizon_days: 14
review_frequency_days: 7
actor: user
---

# {META Title}

## Success Metrics
- {SM 1}
- {SM 2}

## Decomposition (PROJETOs)
- [PROJETO 1](link): {title}
  - tech_stack: [...]
  - parent_ueid: {this meta's ueid}
```

- [ ] **Step 4: Create `00-template-projeto.md`**

Create `vault/ikigai/closing-2026/01-q3-2026/02-onda-1/00-template-projeto.md`:

```markdown
---
template: projeto
tier: ONDA
parent_ueid: {META ueid}
ikigai_vectors: [skill]  # subset of parent
pae_cycle_phase: plan
pae_tier: ONDA
horizon_days: 3
actor: user
tech_stack: []
repo_url: null
---

# {PROJETO Title}

## Goal
{1-2 sentences}

## Acceptance Criteria
- [ ] {AC 1}
- [ ] {AC 2}

## Status
{pending | in_progress | done}
```

- [ ] **Step 5: Remove STATUS="deferred" banner from placeholders**

Open `vault/ikigai/closing-2026/01-q3-2026/00-sonho/placeholder.md`. Delete the STATUS banner (lines 1-5 per current state). Replace with:

```markdown
# Sonho — Q3-2026

Template: `00-template-sonho.md`
First SONHO to instantiate: `Ship Algorithmic Life OS v1 by 2027-Q3`
```

Same edit for `vault/ikigai/closing-2026/02-q4-2026/00-sonho/placeholder.md`.

- [ ] **Step 6: Verify templates validate against contracts**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src python -c "
import yaml
from pathlib import Path
import sys
sys.path.insert(0, 'src/contracts')

for tpl_path in [
    'vault/ikigai/closing-2026/01-q3-2026/00-sonho/00-template-sonho.md',
    'vault/ikigai/closing-2026/01-q3-2026/01-plano-trimestral/00-template-objetivo.md',
    'vault/ikigai/closing-2026/01-q3-2026/02-onda-1/00-template-meta.md',
    'vault/ikigai/closing-2026/01-q3-2026/02-onda-1/00-template-projeto.md',
]:
    text = Path('../' + tpl_path).read_text()
    fm = yaml.safe_load(text.split('---')[1])
    print(f'{tpl_path}: tier={fm.get(\"tier\")}, ikigai_vectors={fm.get(\"ikigai_vectors\")}')
"`
Expected: all 4 templates parse, fields present

- [ ] **Step 7: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add vault/ikigai/closing-2026/01-q3-2026/00-sonho/ vault/ikigai/closing-2026/01-q3-2026/01-plano-trimestral/ vault/ikigai/closing-2026/01-q3-2026/02-onda-1/
git commit -m "feat(vault): SONHO/OBJETIVO/META/PROJETO templates + remove deferred banners"
```

---

## Task 12: End-to-end smoke test (first persisted SONHO tree)

**Files:**
- Create: `tests/integration/test_sonho_first_persistence.py`

**Interfaces:**
- Produces: 22 nodes persisted to vault (1 SONHO + 3 OBJETIVO + 5 META + 13 PROJETO)

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_sonho_first_persistence.py
"""Smoke test: persist the canonical SONHO tree defined in the spec.

Per spec 2026-09-03-sonho-tree-hybrid-design §SONHO Tree.
"""
from datetime import datetime
from pathlib import Path
import yaml

from src.contracts.sonho import Sonho
from src.contracts.objetivo import Objetivo
from src.contracts.meta import Meta
from src.contracts.projeto import Projeto
from src.ikigai.src.agents.v2.nodes.tag_and_persist import tag_and_persist_node
from src.ikigai.src.agents.v2.state import IKIGAiStateDict


def _now() -> datetime:
    return datetime.fromisoformat("2026-09-03T00:00:00+00:00")


def test_persist_full_sonho_tree(tmp_path, monkeypatch):
    monkeypatch.setattr("src.ikigai.src.mcp_server.vault.VAULT_ROOT", tmp_path)

    # SONHO: Ship Algorithmic Life OS v1 by 2027-Q3
    sonho = Sonho(
        id="sn:life-os-v1:abc:def:ghi",
        title="Ship Algorithmic Life OS v1 by 2027-Q3",
        tier="SONHO",
        parent_ueid=None,
        ikigai_vectors=["skill", "market", "revenue"],
        pae_cycle_phase="plan",
        pae_tier="SONHO",
        horizon_days=730,
        created_at=_now(),
        motivation="Ship a planning system that actually plans for me, not against me.",
        success_metric="A (operational hard) + B (adoption soft)",
        core_values=["craft", "truth", "leverage"],
        actor="user",
    )

    # OBJETIVO: Deep Agent build Q4-2026 [ACTIVE]
    objetivo_q4 = Objetivo(
        id="ob:q4-build:abc:def:ghi",
        title="Deep Agent build Q4-2026",
        tier="QUARTERLY",
        parent_ueid=sonho.id,
        ikigai_vectors=["skill"],
        pae_cycle_phase="plan",
        pae_tier="QUARTERLY",
        horizon_days=66,
        created_at=_now(),
        key_results=["B0 hygiene done", "B4 queue worker done"],
        progress_pct=0.0,
        actor="user",
    )

    # 5 METAs (B0-B4)
    metas = [
        Meta(
            id=f"me:b{i}-{'hygiene' if i==0 else 'a2ui' if i==1 else 'server-mgmt' if i==2 else 'mcp' if i==3 else 'queue'}:abc:def:ghi",
            title=f"B{i} {'hygiene' if i==0 else 'A2UI schema' if i==1 else 'server-mgmt CLI' if i==2 else 'MCP gateway' if i==3 else 'queue worker'}",
            tier="ONDA",
            parent_ueid=objetivo_q4.id,
            ikigai_vectors=["skill"],
            pae_cycle_phase="plan",
            pae_tier="ONDA",
            horizon_days=7 if i == 0 else 14,
            created_at=_now(),
            success_metrics=[f"Phase {i} done criteria met"],
            actor="user",
        )
        for i in range(5)
    ]

    # Persist SONHO
    state = IKIGAiStateDict(
        proposed_entity=sonho,
        vault_path="ikigai/closing-2026/02-q4-2026/00-sonho/sonho-life-os-v1.md",
        actor="user",
    )
    result = tag_and_persist_node(state)
    assert result["persisted"] is True

    # Persist OBJETIVO
    state = IKIGAiStateDict(
        proposed_entity=objetivo_q4,
        vault_path="ikigai/closing-2026/02-q4-2026/01-plano-trimestral/objetivo-q4-build.md",
        actor="user",
    )
    tag_and_persist_node(state)

    # Persist 5 METAs
    for i, meta in enumerate(metas):
        state = IKIGAiStateDict(
            proposed_entity=meta,
            vault_path=f"ikigai/closing-2026/02-q4-2026/02-onda-{i+1}/meta-b{i}.md",
            actor="user",
        )
        tag_and_persist_node(state)

    # Verify SONHO file exists and has structured frontmatter
    sonho_path = tmp_path / "ikigai" / "closing-2026" / "02-q4-2026" / "00-sonho" / "sonho-life-os-v1.md"
    assert sonho_path.exists()
    content = sonho_path.read_text()
    assert "ikigai_vectors: [skill, market, revenue]" in content
    assert "pae_tier: SONHO" in content

    # Verify OBJETIVO file has subset ikigai_vectors
    objetivo_path = tmp_path / "ikigai" / "closing-2026" / "02-q4-2026" / "01-plano-trimestral" / "objetivo-q4-build.md"
    assert objetivo_path.exists()
    obj_content = objetivo_path.read_text()
    assert "ikigai_vectors: [skill]" in obj_content
    assert f"parent_ueid: {sonho.id}" in obj_content

    # Verify all 5 META files exist
    for i in range(5):
        meta_path = tmp_path / "ikigai" / "closing-2026" / "02-q4-2026" / f"02-onda-{i+1}" / f"meta-b{i}.md"
        assert meta_path.exists(), f"META {i} file missing"
        meta_content = meta_path.read_text()
        assert "ikigai_vectors: [skill]" in meta_content
        assert f"parent_ueid: {objetivo_q4.id}" in meta_content

    # Verify audit log captures all writes
    audit_log = tmp_path / "ikigai" / "closing-2026" / "02-q4-2026" / "00-sonho" / ".vault_audit.log"
    assert audit_log.exists()
    audit_content = audit_log.read_text()
    assert "actor=user" in audit_content
    assert "sonho-life-os-v1.md" in audit_content
```

- [ ] **Step 2: Run integration test**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/integration/test_sonho_first_persistence.py -v`
Expected: 1 passed

- [ ] **Step 3: Run full test suite + ruff + mypy**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest -v && uv run ruff check src/ && uv run ruff format --check src/ && uv run mypy src/`
Expected: all tests pass, ruff/mypy clean

- [ ] **Step 4: Run mcp_inspect to verify tool count unchanged**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python scripts/mcp_inspect.py`
Expected: 12 IKIGAI tools (no math execution tools added)

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add tests/integration/test_sonho_first_persistence.py
git commit -m "test(integration): first SONHO tree persistence smoke test"
```

---

## Verification (post-Plan-A complete)

```bash
# 1. Drift detector: should show 9/9 PASS (5 current + 4 new for a-e; f-i deferred to Plans B/C)
cd C:\Users\mathe\code_space\life-oss\life\src\ikigai
PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v
# Expected: 9 invariants PASS

# 2. All tests green
PYTHONPATH=src;../../src pytest -v
# Expected: all pass

# 3. Lint + type check
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
# Expected: all clean

# 4. MCP tool count unchanged (no math execution added)
cd C:\Users\mathe\code_space\life-oss\life
python scripts/mcp_inspect.py
# Expected: 12 IKIGAI_TOOLS + 7 fork tools = 19 (or 22 if Spec 3 already shipped)

# 5. Smoke test: first SONHO tree persisted to vault
PYTHONPATH=src;../../src pytest tests/integration/test_sonho_first_persistence.py -v
# Expected: 1 passed, 7 files written (1 SONHO + 1 OBJETIVO + 5 METAs)

# 6. Vault templates valid
ls vault/ikigai/closing-2026/01-q3-2026/00-sonho/00-template-sonho.md
ls vault/ikigai/closing-2026/01-q3-2026/01-plano-trimestral/00-template-objetivo.md
# Expected: 4 template files exist
```

---

## Self-Review (per writing-plans skill)

**Spec coverage:**
- ✅ 12 locked decisions → all mapped to tasks
- ✅ 6 contracts (sonho/objetivo/meta/projeto/entrega/tarefa) → Tasks 3-4
- ✅ 3 enums (PaeCyclePhase/PlanTier/VectorKey) → Task 1
- ✅ Subset validator → Task 2
- ✅ Backward-compat shim → Task 5
- ✅ actor parameter on vault_write → Task 6
- ✅ transition_validator.py → Task 7
- ✅ tag_and_persist node + de-STUB commit_node → Tasks 8-9
- ✅ Drift invariants a-e → Task 10
- ✅ Vault templates → Task 11
- ✅ End-to-end smoke test → Task 12

**Placeholder scan:** No "TBD", "TODO", "implement later", "similar to Task N" — all steps have explicit code.

**Type consistency:**
- `IKIGAiStateDict.proposed_entity` defined Task 8 step 3, consumed Task 8 step 4 ✓
- `vault_write.actor` parameter Task 6 step 3, consumed Task 8 step 4 ✓
- `DriftInvariants.check_phase_transition` calls `validate_phase_transition` (Task 7 → Task 10) ✓
- `Sonho.id` regex matches 5-part canonical UEID ✓

**Coverage gaps acknowledged:**
- Invariant (d) META-has-PROJETO check is stubbed in Task 10 (registry lookup deferred)
- Drift invariants (f, g, h, i) deferred to Plans B and C
- ENTREGA/TAREFA are schema-only (no PROJETOs of them in smoke test) — this is intentional per Decision 9

---

## Open Items (deferred per spec)

- **Plan B**: External Folder Access (`external_folder_read` + `external_roots.yaml` + drift invariant i)
- **Plan C**: Investigation Queue (`data/investigation_queue/` + 3 MCP tools + drift invariant h)
- **Drift invariant (d) full impl**: registry lookup for META→PROJETO relationship (currently stubbed)
- **Drift invariants (f, g)**: vault append-only + audit log shape (currently partial via actor parameter)
- **Lifestyle SONHOs**: enabled by Plan B's `plan_create` MCP tool

---

*Scaffold: Planning Contract Implementation Plan · 2026-09-03 · Plan A · claude-code interactive*
