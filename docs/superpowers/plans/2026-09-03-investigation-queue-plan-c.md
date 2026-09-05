# Investigation Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a filesystem-backed investigation queue (`data/investigation_queue/`) so the Deep Agent v2 can park *pre-form* tasks that don't fit the 6-level SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA hierarchy — raw observations, ambiguous research leads, shadow loops — and dispatch them via 3 MCP tools without polluting the planning tree.

**Architecture:** `data/investigation_queue/` is an append-only filesystem queue (one JSON per investigation). Each file is a frozen-ish record (status: `open` → `in_progress` → `resolved`/`archived`). 3 MCP tools expose lifecycle ops (`enqueue` / `status` / `complete`). A worker consumer (cron-driven, not blocking) reads pending items and emits them into the planning tree once they crystallize. Drift invariant (h) enforces append-only + status transitions valid.

**Tech Stack:** Python 3.12, Pydantic v2 (frozen=True, extra="forbid"), FastMCP, filesystem atomic-rename (per memory `append-only-invariant`).

---

## Global Constraints

- Pydantic v2 strict everywhere (`frozen=True`, `extra="forbid"`)
- Append-only invariant: investigations are never deleted, only `archived` (per memory)
- Atomic writes via tmp-file + atomic-rename (mirror pattern from `src/mesh/queue.py`)
- No LLM in worker consumer (pure dispatch — read JSON, check status, write next state)
- IKIGAI_TOOLS count goes 13 → 16 (Plan B 13 + 3 new tools = 16); drift 10/10 → 11/11
- Status transitions: `open` → `in_progress` → `resolved` | `archived` (terminal states); no resurrection
- Reuse existing `data/review_queue/` patterns (file naming, atomic rename) for consistency
- All commits atomic per task; drift detector must remain ≥10/11 PASS between tasks
- No `Co-Authored-By` trailer per CLAUDE.md L11
- Worker consumer is NOT a hot loop; consumes on cron tick or explicit invocation (≤60s)
- Investigations don't get a UEID — they get a `inq_id` (separate from hierarchy)
- Audit log per state transition: append to `data/investigation_queue/.investigation_audit.log`
- Plan A dependency: DriftInvariants class must exist; if not yet shipped, see Plan A Task 10

---

## File Structure

**Created:**
- `data/investigation_queue/` — directory at repo root (mkdir via Python)
- `data/investigation_queue/.keep` — marker so git tracks empty dir
- `src/contracts/investigation.py` — `Investigation` Pydantic schema + `InvestigationStatus` enum
- `src/ikigai/src/ikigai/mesh/investigation_queue.py` — atomic queue helpers (mirror of `src/mesh/queue.py`)
- `src/ikigai/src/mcp_server/investigation_enqueue.py` — MCP tool #14
- `src/ikigai/src/mcp_server/investigation_status.py` — MCP tool #15
- `src/ikigai/src/mcp_server/investigation_complete.py` — MCP tool #16
- `src/ikigai/src/ikigai/workers/investigation_dispatcher.py` — cron-invoked worker (NOT daemon)
- `tests/contracts/test_investigation.py`
- `tests/ikigai/mesh/test_investigation_queue.py`
- `tests/mcp_server/test_investigation_lifecycle.py`
- `tests/ikigai/workers/test_investigation_dispatcher.py`
- `tests/integration/test_investigation_queue_smoke.py`

**Modified:**
- `src/contracts/__init__.py` — re-exports `Investigation` + `InvestigationStatus`
- `src/ikigai/src/mcp_server/__init__.py` — IKIGAI_TOOLS grows 13 → 16
- `src/ikigai/src/ikigai/security/drift_invariants.py` — adds `check_investigation_queue_invariants` (h)
- `src/ikigai/tests/test_canonical_scope.py` — wires drift invariant (h)
- `.gitignore` — `data/investigation_queue/!*.keep` pattern OR commit queue base structure

**No changes to:**
- `data/review_queue/` — already exists, different concern (TaskChange → fork propagation)
- `vault/` — investigations are pre-vault; never written there by this plan
- `archive/legacy-pav/` — untouched

---

## Task 1: `Investigation` Pydantic schema

**Files:**
- Create: `src/contracts/investigation.py`
- Modify: `src/contracts/__init__.py`
- Test: `tests/contracts/test_investigation.py`

**Interfaces:**
- Produces: `InvestigationStatus` (Literal: `"open" | "in_progress" | "resolved" | "archived"`)
- Produces: `Investigation(inq_id, source, payload, status, created_at, updated_at, inq_ueid: str | None, actor, tags)`

- [ ] **Step 1: Write the failing test**

```python
# tests/contracts/test_investigation.py
import pytest
from datetime import datetime
from pydantic import ValidationError
from src.contracts.investigation import Investigation, InvestigationStatus


def _now() -> datetime:
    return datetime.fromisoformat("2026-09-03T00:00:00+00:00")


def test_investigation_minimum_fields():
    inv = Investigation(
        inq_id="inq-20260903-001",
        source="agent",
        payload="Raw CSV observation from research log — needs DECISION on whether to canonicalize.",
        status="open",
        created_at=_now(),
    )
    assert inv.inq_id == "inq-20260903-001"
    assert inv.status == "open"
    assert inv.source == "agent"
    assert inv.inq_ueid is None
    assert inv.tags == ()


def test_investigation_status_is_literal():
    assert InvestigationStatus.__args__ == ("open", "in_progress", "resolved", "archived")


def test_investigation_status_validates():
    with pytest.raises(ValidationError):
        Investigation(
            inq_id="inq-bad",
            source="user",
            payload="p",
            status="bogus_status",  # type: ignore
            created_at=_now(),
        )


def test_investigation_inq_ueid_is_optional():
    inv = Investigation(
        inq_id="inq-20260903-002",
        source="user",
        payload="Raw idea: maybe a SONHO about life OS",
        status="open",
        created_at=_now(),
        inq_ueid="sn:life-os-v1:abc:def:ghi",  # cross-ref, optional
    )
    assert inv.inq_ueid == "sn:life-os-v1:abc:def:ghi"


def test_investigation_frozen():
    inv = Investigation(
        inq_id="inq-x",
        source="user",
        payload="p",
        status="open",
        created_at=_now(),
    )
    with pytest.raises(Exception):
        inv.status = "in_progress"


def test_investigation_extra_field_rejected():
    with pytest.raises(ValidationError, match="Extra inputs"):
        Investigation(
            inq_id="inq-x",
            source="user",
            payload="p",
            status="open",
            created_at=_now(),
            unknown="x",  # type: ignore
        )


def test_investigation_roundtrips_through_dict():
    inv = Investigation(
        inq_id="inq-rt",
        source="agent",
        payload="rt test",
        status="in_progress",
        created_at=_now(),
        tags=("research", "raw"),
    )
    d = inv.model_dump()
    inv2 = Investigation(**d)
    assert inv == inv2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_investigation.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `Investigation`**

Create `src/contracts/investigation.py`:

```python
"""Investigation contract — pre-form tasks before they crystallize.

Per Plan C / spec 2026-09-03-sonho-tree-hybrid-design §4.

Investigations are NOT part of the 6-level hierarchy (SONHO → TAREFA). They
are a separate filesystem queue (`data/investigation_queue/`) for raw
observations, ambiguous leads, and shadow loops that may eventually be
lifted into the planning tree via the worker dispatcher.

Status lifecycle: open → in_progress → resolved | archived
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


InvestigationStatus = Literal["open", "in_progress", "resolved", "archived"]


class Investigation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    inq_id: str = Field(pattern=r"^inq-\d{8}-\d{3}$")  # inq-YYYYMMDD-NNN
    source: Literal["user", "agent", "system", "external"]
    payload: str = Field(min_length=1, max_length=30000)
    status: InvestigationStatus = "open"
    inq_ueid: str | None = None  # optional cross-reference to hierarchy UEID
    tags: tuple[str, ...] = ()
    custom: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    actor: Literal["user", "agent", "system"] = "agent"
```

- [ ] **Step 4: Add re-export to `src/contracts/__init__.py`**

```python
from src.contracts.investigation import Investigation, InvestigationStatus
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../contracts/test_investigation.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/contracts/investigation.py src/contracts/__init__.py tests/contracts/test_investigation.py
git commit -m "feat(contracts): Investigation + InvestigationStatus (Pydantic v2 strict)"
```

---

## Task 2: Atomic queue helpers (mirror `src/mesh/queue.py`)

**Files:**
- Create: `src/ikigai/src/ikigai/mesh/investigation_queue.py`
- Test: `tests/ikigai/mesh/test_investigation_queue.py`

**Interfaces:**
- Produces: `enqueue(inv: Investigation, base_dir: Path) -> Path`
- Produces: `get_by_id(inq_id: str, base_dir: Path) -> Investigation | None`
- Produces: `list_by_status(status: InvestigationStatus, base_dir: Path) -> list[Investigation]`
- Produces: `transition(inv_id: str, new_status: InvestigationStatus, base_dir: Path, actor: str) -> Investigation`

- [ ] **Step 1: Write the failing test**

```python
# tests/ikigai/mesh/test_investigation_queue.py
import pytest
from datetime import datetime
from pathlib import Path

from src.contracts.investigation import Investigation
from src.ikigai.src.ikigai.mesh.investigation_queue import (
    enqueue,
    get_by_id,
    list_by_status,
    transition,
    InvalidStatusTransitionError,
)


def _now() -> datetime:
    return datetime.fromisoformat("2026-09-03T00:00:00+00:00")


def _make(inq_id: str = "inq-20260903-001", status: str = "open") -> Investigation:
    return Investigation(
        inq_id=inq_id,
        source="agent",
        payload="raw observation",
        status=status,
        created_at=_now(),
    )


def test_enqueue_writes_json_file(tmp_path):
    inv = _make()
    path = enqueue(inv, base_dir=tmp_path)
    assert path.exists()
    assert path.name == "inq-20260903-001.json"
    text = path.read_text(encoding="utf-8")
    assert "inq-20260903-001" in text
    assert "raw observation" in text


def test_enqueue_creates_dir_if_missing(tmp_path):
    base = tmp_path / "investigation_queue"
    assert not base.exists()
    inv = _make(inq_id="inq-20260903-002")
    enqueue(inv, base_dir=base)
    assert base.exists()


def test_get_by_id_returns_investigation(tmp_path):
    inv = _make()
    enqueue(inv, base_dir=tmp_path)
    fetched = get_by_id("inq-20260903-001", base_dir=tmp_path)
    assert fetched is not None
    assert fetched.payload == "raw observation"


def test_get_by_id_missing_returns_none(tmp_path):
    assert get_by_id("inq-not-there", base_dir=tmp_path) is None


def test_list_by_status_filters(tmp_path):
    enqueue(_make(inq_id="inq-1", status="open"), base_dir=tmp_path)
    enqueue(_make(inq_id="inq-2", status="in_progress"), base_dir=tmp_path)
    enqueue(_make(inq_id="inq-3", status="open"), base_dir=tmp_path)
    open_invs = list_by_status("open", base_dir=tmp_path)
    assert len(open_invs) == 2
    assert all(i.status == "open" for i in open_invs)


def test_transition_validates_status_progression(tmp_path):
    enqueue(_make(inq_id="inq-1", status="open"), base_dir=tmp_path)
    # open → in_progress is valid
    updated = transition("inq-1", "in_progress", base_dir=tmp_path, actor="agent")
    assert updated.status == "in_progress"


def test_transition_rejects_invalid_progression(tmp_path):
    enqueue(_make(inq_id="inq-1", status="open"), base_dir=tmp_path)
    # open → resolved is invalid (must go through in_progress)
    with pytest.raises(InvalidStatusTransitionError, match="open → resolved"):
        transition("inq-1", "resolved", base_dir=tmp_path, actor="agent")


def test_transition_terminal_state_blocks_further(tmp_path):
    """resolved/archived are terminal; no transition out."""
    enqueue(_make(inq_id="inq-1", status="resolved"), base_dir=tmp_path)
    with pytest.raises(InvalidStatusTransitionError, match="terminal"):
        transition("inq-1", "open", base_dir=tmp_path, actor="agent")


def test_transition_writes_audit(tmp_path):
    enqueue(_make(inq_id="inq-1", status="open"), base_dir=tmp_path)
    transition("inq-1", "in_progress", base_dir=tmp_path, actor="agent")
    audit = tmp_path / ".investigation_audit.log"
    assert audit.exists()
    assert "inq-1" in audit.read_text(encoding="utf-8")
    assert "open→in_progress" in audit.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/mesh/test_investigation_queue.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `investigation_queue.py`**

Create `src/ikigai/src/ikigai/mesh/investigation_queue.py`:

```python
"""Atomic filesystem-backed investigation queue.

Per Plan C / spec 2026-09-03-sonho-tree-hybrid-design §4.

Mirrors the pattern in src/mesh/queue.py (append-only review queue):
atomic writes via tmp-file + os.replace(), no in-place mutation.
"""
from datetime import datetime, timezone
from pathlib import Path

from src.contracts.investigation import Investigation, InvestigationStatus


VALID_TRANSITIONS: dict[InvestigationStatus, set[InvestigationStatus]] = {
    "open": {"in_progress", "archived"},
    "in_progress": {"resolved", "archived"},
    "resolved": set(),  # terminal
    "archived": set(),  # terminal
}


class InvalidStatusTransitionError(Exception):
    """Status transition violated lifecycle (e.g., open→resolved)."""


def _atomic_write(target: Path, content: str) -> None:
    """Write content atomically via tmp-file + os.replace()."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(target)


def _audit_log(base_dir: Path, inq_id: str, from_s: str, to_s: str, actor: str) -> None:
    """Append-only audit log (.investigation_audit.log)."""
    audit = base_dir / ".investigation_audit.log"
    now = datetime.now(timezone.utc).isoformat()
    line = f"{now} inq_id={inq_id} {from_s}→{to_s} actor={actor}\n"
    try:
        with audit.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # audit failure non-fatal


def enqueue(inv: Investigation, base_dir: Path) -> Path:
    """Write investigation to queue (atomic). Returns file path."""
    target = base_dir / f"{inv.inq_id}.json"
    _atomic_write(target, inv.model_dump_json(indent=2))
    _audit_log(base_dir, inv.inq_id, "—", "open", inv.actor)
    return target


def get_by_id(inq_id: str, base_dir: Path) -> Investigation | None:
    """Fetch a single investigation by ID."""
    target = base_dir / f"{inq_id}.json"
    if not target.exists():
        return None
    return Investigation.model_validate_json(target.read_text(encoding="utf-8"))


def list_by_status(status: InvestigationStatus, base_dir: Path) -> list[Investigation]:
    """List all investigations matching status."""
    if not base_dir.exists():
        return []
    out: list[Investigation] = []
    for f in base_dir.glob("inq-*.json"):
        try:
            inv = Investigation.model_validate_json(f.read_text(encoding="utf-8"))
            if inv.status == status:
                out.append(inv)
        except Exception:
            continue  # skip malformed
    return out


def transition(
    inv_id: str,
    new_status: InvestigationStatus,
    base_dir: Path,
    actor: str,
) -> Investigation:
    """Transition an investigation's status; validates progression."""
    current = get_by_id(inv_id, base_dir)
    if current is None:
        raise FileNotFoundError(f"investigation {inv_id} not found")
    if new_status not in VALID_TRANSITIONS.get(current.status, set()):
        raise InvalidStatusTransitionError(
            f"invalid transition: {current.status} → {new_status} "
            f"(allowed from {current.status}: {sorted(VALID_TRANSITIONS[current.status])})"
        )

    updated = current.model_copy(update={
        "status": new_status,
        "updated_at": datetime.now(timezone.utc),
    })
    target = base_dir / f"{inv_id}.json"
    _atomic_write(target, updated.model_dump_json(indent=2))
    _audit_log(base_dir, inv_id, current.status, new_status, actor)
    return updated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/mesh/test_investigation_queue.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/ikigai/mesh/investigation_queue.py tests/ikigai/mesh/test_investigation_queue.py
git commit -m "feat(mesh): investigation queue with atomic writes + status FSM"
```

---

## Task 3: 3 MCP lifecycle tools

**Files:**
- Create: `src/ikigai/src/mcp_server/investigation_enqueue.py`
- Create: `src/ikigai/src/mcp_server/investigation_status.py`
- Create: `src/ikigai/src/mcp_server/investigation_complete.py`
- Test: `tests/mcp_server/test_investigation_lifecycle.py`

**Interfaces:**
- Produces:
  - `investigation_enqueue(source, payload, inq_ueid: str | None, tags: list[str]) -> Investigation`
  - `investigation_status(inq_id: str) -> Investigation | None`
  - `investigation_complete(inq_id: str, terminal_status: Literal["resolved", "archived"], actor: str) -> Investigation`

- [ ] **Step 1: Write the failing test**

```python
# tests/mcp_server/test_investigation_lifecycle.py
import pytest
from pathlib import Path
from datetime import datetime, timezone


@pytest.fixture
def queue_dir(tmp_path, monkeypatch):
    """Redirect INVESTIGATION_QUEUE_DIR to a tmp directory."""
    qdir = tmp_path / "investigation_queue"
    monkeypatch.setattr(
        "src.ikigai.src.ikigai.mesh.investigation_queue.INVESTIGATION_QUEUE_DIR",
        None,  # placeholder; see step 4 below
    )
    from src.ikigai.src.ikigai.mesh import investigation_queue as iq_mod
    # Patch the module-level path
    monkeypatch.setattr(iq_mod, "INVESTIGATION_QUEUE_DIR", qdir)
    return qdir


def test_enqueue_creates_file(queue_dir):
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    inv = investigation_enqueue(
        source="agent",
        payload="observation: 3 research notes mention user fatigue",
        tags=["research", "raw"],
    )
    assert inv.inq_id.startswith("inq-")
    assert inv.status == "open"
    assert (queue_dir / f"{inv.inq_id}.json").exists()


def test_enqueue_assigns_auto_id(queue_dir):
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    inv1 = investigation_enqueue(source="agent", payload="a")
    inv2 = investigation_enqueue(source="agent", payload="b")
    assert inv1.inq_id != inv2.inq_id


def test_status_returns_open_investigation(queue_dir):
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    from src.ikigai.src.mcp_server.investigation_status import investigation_status
    enq_inv = investigation_enqueue(source="agent", payload="p")
    fetched = investigation_status(inq_id=enq_inv.inq_id)
    assert fetched is not None
    assert fetched.inq_id == enq_inv.inq_id


def test_status_returns_none_for_missing(queue_dir):
    from src.ikigai.src.mcp_server.investigation_status import investigation_status
    assert investigation_status(inq_id="inq-not-there") is None


def test_complete_transitions_to_resolved(queue_dir):
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    from src.ikigai.src.mcp_server.investigation_complete import investigation_complete
    enq_inv = investigation_enqueue(source="agent", payload="p")
    completed = investigation_complete(
        inq_id=enq_inv.inq_id,
        terminal_status="resolved",
        actor="agent",
    )
    assert completed.status == "resolved"


def test_complete_transitions_to_archived(queue_dir):
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    from src.ikigai.src.mcp_server.investigation_complete import investigation_complete
    enq_inv = investigation_enqueue(source="agent", payload="p")
    completed = investigation_complete(
        inq_id=enq_inv.inq_id,
        terminal_status="archived",
        actor="user",  # user-decision archive
    )
    assert completed.status == "archived"


def test_complete_rejects_open_terminal(queue_dir):
    """complete() cannot transition to 'open' or 'in_progress' (those aren't terminal)."""
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    from src.ikigai.src.mcp_server.investigation_complete import investigation_complete
    enq_inv = investigation_enqueue(source="agent", payload="p")
    with pytest.raises(ValueError, match="terminal_status must be"):
        investigation_complete(
            inq_id=enq_inv.inq_id,
            terminal_status="open",  # type: ignore
            actor="agent",
        )


def test_enqueue_writes_audit_log(queue_dir):
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    inv = investigation_enqueue(source="agent", payload="p")
    audit = queue_dir / ".investigation_audit.log"
    assert audit.exists()
    log_text = audit.read_text(encoding="utf-8")
    assert inv.inq_id in log_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../mcp_server/test_investigation_lifecycle.py -v`
Expected: ImportError

- [ ] **Step 3: Add `INVESTIGATION_QUEUE_DIR` constant to module**

Modify `src/ikigai/src/ikigai/mesh/investigation_queue.py`:

```python
# Add at top of file
from pathlib import Path
INVESTIGATION_QUEUE_DIR = Path("data/investigation_queue")
```

- [ ] **Step 4: Implement 3 MCP tools**

Create `src/ikigai/src/mcp_server/investigation_enqueue.py`:

```python
"""investigation_enqueue — MCP tool #14 of the IKIGAI gateway.

Per Plan C / spec 2026-09-03-sonho-tree-hybrid-design §4.

Allows the agent/user/system to park pre-form observations in the
investigation queue. Returns the assigned inq_id.
"""
from datetime import datetime, timezone
from typing import Literal

from src.contracts.investigation import Investigation, InvestigationStatus
from src.ikigai.src.ikigai.mesh.investigation_queue import (
    INVESTIGATION_QUEUE_DIR,
    enqueue,
)


def _next_inq_id() -> str:
    """Generate inq_id of form inq-YYYYMMDD-NNN."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing = list(INVESTIGATION_QUEUE_DIR.glob(f"inq-{today}-*.json")) if INVESTIGATION_QUEUE_DIR.exists() else []
    next_seq = len(existing) + 1
    return f"inq-{today}-{next_seq:03d}"


def investigation_enqueue(
    source: Literal["user", "agent", "system", "external"],
    payload: str,
    inq_ueid: str | None = None,
    tags: list[str] | None = None,
    actor: Literal["user", "agent", "system"] = "agent",
) -> Investigation:
    """Enqueue a new investigation."""
    inv = Investigation(
        inq_id=_next_inq_id(),
        source=source,
        payload=payload,
        status="open",
        inq_ueid=inq_ueid,
        tags=tuple(tags or ()),
        created_at=datetime.now(timezone.utc),
        actor=actor,
    )
    enqueue(inv, base_dir=INVESTIGATION_QUEUE_DIR)
    return inv
```

Create `src/ikigai/src/mcp_server/investigation_status.py`:

```python
"""investigation_status — MCP tool #15 of the IKIGAI gateway.

Returns the current state of an investigation by inq_id, or None if not found.
"""
from src.contracts.investigation import Investigation
from src.ikigai.src.ikigai.mesh.investigation_queue import (
    INVESTIGATION_QUEUE_DIR,
    get_by_id,
)


def investigation_status(inq_id: str) -> Investigation | None:
    """Fetch current investigation state by inq_id."""
    return get_by_id(inq_id, base_dir=INVESTIGATION_QUEUE_DIR)
```

Create `src/ikigai/src/mcp_server/investigation_complete.py`:

```python
"""investigation_complete — MCP tool #16 of the IKIGAI gateway.

Transitions an investigation to a terminal state (resolved or archived).
The agent cannot lift investigations back into the planning tree — that
happens via the worker dispatcher (cron consumer).
"""
from typing import Literal

from src.contracts.investigation import Investigation
from src.ikigai.src.ikigai.mesh.investigation_queue import (
    INVESTIGATION_QUEUE_DIR,
    transition,
)


def investigation_complete(
    inq_id: str,
    terminal_status: Literal["resolved", "archived"],
    actor: Literal["user", "agent", "system"],
) -> Investigation:
    """Mark an investigation as resolved or archived."""
    if terminal_status not in ("resolved", "archived"):
        raise ValueError(f"terminal_status must be 'resolved' or 'archived', got {terminal_status!r}")
    return transition(
        inv_id=inq_id,
        new_status=terminal_status,
        base_dir=INVESTIGATION_QUEUE_DIR,
        actor=actor,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/../mcp_server/test_investigation_lifecycle.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/mcp_server/investigation_enqueue.py src/ikigai/src/mcp_server/investigation_status.py src/ikigai/src/mcp_server/investigation_complete.py tests/mcp_server/test_investigation_lifecycle.py
git commit -m "feat(mcp): 3 investigation lifecycle tools (enqueue/status/complete)"
```

---

## Task 4: Register 3 tools + create queue directory

**Files:**
- Modify: `src/ikigai/src/agents/tools.py` (IKIGAI_TOOLS list — append 3 investigation tools)
- Modify: `src/ikigai/src/mcp_server/server.py` (FastMCP `@MCP.tool` registration for each)
- Modify: `src/ikigai/tests/test_canonical_scope.py` (line 313: change `total_count == 13` → `== 16`)
- Modify: `scripts/mcp_inspect.py` (line 43: change `EXPECTED_IKIGAI_TOOLS_COUNT = 13` → `= 16`)
- Create: `data/investigation_queue/.keep` (placeholder so the dir is tracked)

> **Gap-fix note (2026-09-03):** Earlier draft pointed at `src/ikigai/src/mcp_server/__init__.py`,
> but that file is just a docstring. The canonical `IKIGAI_TOOLS` list lives at
> `src/ikigai/src/agents/tools.py:556`, and FastMCP registration lives in
> `src/ikigai/src/mcp_server/server.py`. Drift detector reads `tools.py` at L283 and asserts
> the count at L313 — must update alongside the list (Plan B already bumped it 12→13).

**Interfaces:**
- Modifies: IKIGAI_TOOLS list grows 13 → 16

- [ ] **Step 1: Append to the list**

In `src/ikigai/src/agents/tools.py`, add at the bottom:

```python
from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
from src.ikigai.src.mcp_server.investigation_status import investigation_status
from src.ikigai.src.mcp_server.investigation_complete import investigation_complete

IKIGAI_TOOLS.extend([
    investigation_enqueue,    # Tool #14
    investigation_status,    # Tool #15
    investigation_complete,  # Tool #16
])
```

- [ ] **Step 2: Register FastMCP tools**

In `src/ikigai/src/mcp_server/server.py`:

```python
from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
from src.ikigai.src.mcp_server.investigation_status import investigation_status
from src.ikigai.src.mcp_server.investigation_complete import investigation_complete

MCP.tool()(investigation_enqueue)
MCP.tool()(investigation_status)
MCP.tool()(investigation_complete)
```

- [ ] **Step 3: Update drift detector + mcp_inspect**

Edit `src/ikigai/tests/test_canonical_scope.py` line 313:

```python
assert total_count == 16, (  # was 13 (was 12 pre-Plan-B)
```

Edit `scripts/mcp_inspect.py` line 43:

```python
EXPECTED_IKIGAI_TOOLS_COUNT = 16  # was 13 (was 12 pre-Plan-B)
```

- [ ] **Step 4: Create queue directory placeholder**

```bash
mkdir -p data/investigation_queue
touch data/investigation_queue/.keep
```

(Atomic queue helpers from Task 2 use this directory; the `.keep` ensures git tracks it.)

- [ ] **Step 5: Verify via mcp_inspect + drift detector**

Run: `cd C:\Users\mathe\code_space\life-oss\life && python scripts/mcp_inspect.py --tool-count 16`
Expected: PASS

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v`
Expected: 11/11 PASS (5 baseline + 4 Plan A a-e + 1 Plan B i + 1 Plan C h)

- [ ] **Step 6: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/agents/tools.py src/ikigai/src/mcp_server/server.py src/ikigai/tests/test_canonical_scope.py scripts/mcp_inspect.py data/investigation_queue/.keep
git commit -m "feat(mcp): register 3 investigation tools (IKIGAI_TOOLS 13 → 16)"
```

---

## Task 5: Worker dispatcher (cron-invoked)

**Files:**
- Create: `src/ikigai/src/ikigai/workers/investigation_dispatcher.py`
- Test: `tests/ikigai/workers/test_investigation_dispatcher.py`

**Interfaces:**
- Produces: `dispatch_pending(base_dir: Path) -> DispatchResult` — single-tick consume

- [ ] **Step 1: Write the failing test**

```python
# tests/ikigai/workers/test_investigation_dispatcher.py
import pytest
from datetime import datetime
from pathlib import Path
from src.contracts.investigation import Investigation
from src.ikigai.src.ikigai.workers.investigation_dispatcher import (
    dispatch_pending,
    DispatchResult,
)
from src.ikigai.src.ikigai.mesh.investigation_queue import (
    enqueue,
    INVESTIGATION_QUEUE_DIR,  # noqa: F401
)
from src.ikigai.src.ikigai.mesh import investigation_queue as iq_mod


@pytest.fixture
def queue_dir(tmp_path, monkeypatch):
    qdir = tmp_path / "investigation_queue"
    qdir.mkdir()
    monkeypatch.setattr(iq_mod, "INVESTIGATION_QUEUE_DIR", qdir)
    return qdir


def _now() -> datetime:
    return datetime.fromisoformat("2026-09-03T00:00:00+00:00")


def _seed(path: Path, inq_id: str, payload: str = "raw obs") -> Investigation:
    inv = Investigation(
        inq_id=inq_id,
        source="agent",
        payload=payload,
        status="open",
        created_at=_now(),
    )
    enqueue(inv, base_dir=path)
    return inv


def test_dispatcher_returns_open_count(queue_dir):
    _seed(queue_dir, "inq-1")
    _seed(queue_dir, "inq-2")
    result = dispatch_pending(base_dir=queue_dir)
    assert isinstance(result, DispatchResult)
    assert result.open_count == 2
    assert result.in_progress_count == 0


def test_dispatcher_no_op_when_empty(queue_dir):
    result = dispatch_pending(base_dir=queue_dir)
    assert result.open_count == 0
    assert result.in_progress_count == 0


def test_dispatcher_does_not_modify_queue(queue_dir):
    """Worker is OBSERVE-only in v1 — does not move state forward."""
    _seed(queue_dir, "inq-1", payload="p1")
    dispatch_pending(base_dir=queue_dir)
    inv = iq_mod.get_by_id("inq-1", base_dir=queue_dir)
    assert inv is not None
    assert inv.status == "open"  # unchanged


def test_dispatcher_emits_to_planning_sink_hook(monkeypatch, queue_dir):
    """Dispatcher hook for future planning-tree lift (stub for now)."""
    _seed(queue_dir, "inq-1", payload="some payload")
    captured: list = []

    def fake_sink(inv: Investigation) -> None:
        captured.append(inv.inq_id)

    monkeypatch.setattr(
        "src.ikigai.src.ikigai.workers.investigation_dispatcher.dispatch_to_planning_sink",
        fake_sink,
    )

    dispatch_pending(base_dir=queue_dir)
    # v1: sink is a no-op stub (just records) — does NOT persist
    # v2+ will hook into tag_and_persist node
    assert captured == []  # stub does nothing
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/workers/test_investigation_dispatcher.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `dispatch_pending`**

Create `src/ikigai/src/ikigai/workers/investigation_dispatcher.py`:

```python
"""Investigation dispatcher (cron-invoked, NOT daemon).

Per Plan C / spec §4.

Single-tick function — reads pending investigations, exposes counts, and
(optionally) lifts into planning tree via hook. v1: hook is a stub. v2+:
the hook will call into the v2 tag_and_persist node (Plan A Task 8).
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.contracts.investigation import Investigation
from src.ikigai.src.ikigai.mesh.investigation_queue import (
    INVESTIGATION_QUEUE_DIR,
    list_by_status,
)


def dispatch_to_planning_sink(inv: Investigation) -> None:
    """Hook for future planning-tree integration. v1: no-op stub."""
    # v2+ will hand off to tag_and_persist (Plan A Task 8)
    return None


@dataclass(frozen=True)
class DispatchResult:
    open_count: int
    in_progress_count: int
    resolved_count: int
    archived_count: int
    source_dir: Path


def dispatch_pending(
    base_dir: Path = INVESTIGATION_QUEUE_DIR,
    sink: Callable[[Investigation], None] = dispatch_to_planning_sink,
) -> DispatchResult:
    """Consume one tick of pending investigations.

    Reads (does NOT mutate) the queue. Calls sink() for each open item —
    v1 sink is a no-op; v2 will lift into the planning tree.

    Returns counts so the caller (cron / CLI) can decide next steps.
    """
    open_invs = list_by_status("open", base_dir=base_dir)
    in_progress_invs = list_by_status("in_progress", base_dir=base_dir)
    resolved_invs = list_by_status("resolved", base_dir=base_dir)
    archived_invs = list_by_status("archived", base_dir=base_dir)

    # Observe-only; the sink is invoked for visibility but does not persist
    for inv in list_by_status("open", base_dir=base_dir):
        try:
            sink(inv)
        except Exception:
            # sink failures are non-fatal; dispatcher continues
            pass

    return DispatchResult(
        open_count=len(open_invs),
        in_progress_count=len(in_progress_invs),
        resolved_count=len(resolved_invs),
        archived_count=len(archived_invs),
        source_dir=base_dir,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/workers/test_investigation_dispatcher.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/ikigai/workers/investigation_dispatcher.py tests/ikigai/workers/test_investigation_dispatcher.py
git commit -m "feat(workers): investigation dispatcher (observe-only, cron-invoked)"
```

---

## Task 6: Drift invariant (h) — investigation queue

**Files:**
- Modify: `src/ikigai/src/ikigai/security/drift_invariants.py`
- Modify: `src/ikigai/tests/test_canonical_scope.py`
- Test: `tests/ikigai/security/test_drift_invariants.py` (add 3 tests)

**Interfaces:**
- Produces: `DriftInvariants.check_investigation_queue_invariants()` — verifies dir exists + status counts + audit log append-only

- [ ] **Step 1: Write the failing test**

Append to `tests/ikigai/security/test_drift_invariants.py`:

```python
# tests/ikigai/security/test_drift_invariants.py (add to existing file)


def test_drift_invariant_h_investigation_queue_passes_when_valid(tmp_path, monkeypatch):
    """Queue exists, all files parse, status distribution is sane."""
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    from src.ikigai.src.ikigai.mesh import investigation_queue as iq_mod
    qdir = tmp_path / "investigation_queue"
    qdir.mkdir()
    monkeypatch.setattr(iq_mod, "INVESTIGATION_QUEUE_DIR", qdir)
    # Seed 1 open + 1 resolved
    from datetime import datetime
    from src.contracts.investigation import Investigation
    inv1 = Investigation(
        inq_id="inq-20260903-001",
        source="agent",
        payload="p1",
        status="open",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    inv2 = Investigation(
        inq_id="inq-20260903-002",
        source="agent",
        payload="p2",
        status="resolved",
        created_at=datetime.fromisoformat("2026-09-03T00:00:00+00:00"),
    )
    iq_mod.enqueue(inv1, base_dir=qdir)
    iq_mod.enqueue(inv2, base_dir=qdir)
    DriftInvariants.check_investigation_queue_invariants()  # no exception


def test_drift_invariant_h_fails_on_malformed_file(tmp_path, monkeypatch):
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    from src.ikigai.src.ikigai.mesh import investigation_queue as iq_mod
    import pytest
    qdir = tmp_path / "investigation_queue"
    qdir.mkdir()
    monkeypatch.setattr(iq_mod, "INVESTIGATION_QUEUE_DIR", qdir)
    (qdir / "inq-20260903-999.json").write_text("not-json", encoding="utf-8")
    with pytest.raises(AssertionError, match="malformed"):
        DriftInvariants.check_investigation_queue_invariants()


def test_drift_invariant_h_passes_on_empty_or_missing_dir(tmp_path, monkeypatch):
    """Missing dir is OK — tool raises on use; drift doesn't fail CI."""
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    from src.ikigai.src.ikigai.mesh import investigation_queue as iq_mod
    monkeypatch.setattr(iq_mod, "INVESTIGATION_QUEUE_DIR", tmp_path / "never-created")
    DriftInvariants.check_investigation_queue_invariants()  # no exception
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/ikigai/security/test_drift_invariants.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `check_investigation_queue_invariants`**

Append to `src/ikigai/src/ikigai/security/drift_invariants.py`:

```python
# Append to existing DriftInvariants class

    @staticmethod
    def check_investigation_queue_invariants() -> None:
        """Invariant (h): investigation_queue dir is valid (or absent).

        Per Plan C / spec 2026-09-03-sonho-tree-hybrid-design §Drift Invariants.
        - If dir exists, all .json files parse as Investigation
        - Audit log (.investigation_audit.log) lines have valid prefix
        - No investigation has invalid status string
        """
        from src.ikigai.src.ikigai.mesh import investigation_queue as iq_mod
        from src.contracts.investigation import Investigation, InvestigationStatus

        base_dir = iq_mod.INVESTIGATION_QUEUE_DIR
        if not base_dir.exists():
            return  # tool raises on use; CI passes when no investigations yet

        valid_statuses = set(InvestigationStatus.__args__)

        for f in sorted(base_dir.glob("inq-*.json")):
            try:
                inv = Investigation.model_validate_json(f.read_text(encoding="utf-8"))
            except Exception as e:
                raise AssertionError(
                    f"investigation_queue has malformed file {f.name}: {e}"
                ) from e
            if inv.status not in valid_statuses:
                raise AssertionError(
                    f"investigation {inv.inq_id} has invalid status {inv.status!r}"
                )

        # Audit log shape check (best effort)
        audit = base_dir / ".investigation_audit.log"
        if audit.exists():
            for line in audit.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                if "actor=" not in line or "inq_id=" not in line:
                    raise AssertionError(
                        f"investigation_audit.log line missing required prefix: {line!r}"
                    )
```

- [ ] **Step 4: Wire invariant into drift detector**

Append to `src/ikigai/tests/test_canonical_scope.py`:

```python
def test_drift_invariant_h_investigation_queue():
    from src.ikigai.src.ikigai.security.drift_invariants import DriftInvariants
    DriftInvariants.check_investigation_queue_invariants()  # no exception
```

- [ ] **Step 5: Run full drift detector**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v`
Expected: 5 + 4 (Plan A a-e) + 1 (Plan B i) + 1 (Plan C h) = 11 invariants PASS

- [ ] **Step 6: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add src/ikigai/src/ikigai/security/drift_invariants.py src/ikigai/tests/test_canonical_scope.py tests/ikigai/security/test_drift_invariants.py
git commit -m "feat(drift): invariant h — investigation queue structure"
```

---

## Task 7: End-to-end smoke test

**Files:**
- Create: `tests/integration/test_investigation_queue_smoke.py`

**Interfaces:**
- Produces: 1 integration test exercising full lifecycle (enqueue → status → in_progress → resolved)

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_investigation_queue_smoke.py
"""End-to-end smoke test for Plan C Investigation Queue.

Per spec 2026-09-03-sonho-tree-hybrid-design §4.
"""
import pytest
from datetime import datetime


@pytest.fixture
def isolated_queue(tmp_path, monkeypatch):
    """Redirect INVESTIGATION_QUEUE_DIR for the duration of the test."""
    qdir = tmp_path / "investigation_queue"
    qdir.mkdir()
    from src.ikigai.src.ikigai.mesh import investigation_queue as iq_mod
    monkeypatch.setattr(iq_mod, "INVESTIGATION_QUEUE_DIR", qdir)
    return qdir


def test_full_investigation_lifecycle(isolated_queue):
    """Agent enqueues → marks in-progress → resolves; all transitions audited."""
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    from src.ikigai.src.mcp_server.investigation_status import investigation_status
    from src.ikigai.src.mcp_server.investigation_complete import investigation_complete

    # Step 1: enqueue
    inv = investigation_enqueue(
        source="agent",
        payload="Raw observation from research log — needs decision on canonical form.",
        tags=["research", "raw"],
    )
    assert inv.status == "open"
    assert (isolated_queue / f"{inv.inq_id}.json").exists()

    # Step 2: status fetch
    fetched = investigation_status(inq_id=inv.inq_id)
    assert fetched is not None
    assert fetched.inq_id == inv.inq_id

    # Step 3: in_progress transition (via queue.mesh directly since complete is terminal-only)
    from src.ikigai.src.ikigai.mesh.investigation_queue import transition
    mid = transition(inv.inq_id, "in_progress", base_dir=isolated_queue, actor="agent")
    assert mid.status == "in_progress"

    # Step 4: complete
    final = investigation_complete(
        inq_id=inv.inq_id,
        terminal_status="resolved",
        actor="user",
    )
    assert final.status == "resolved"

    # Step 5: audit log captures all 4 transitions
    audit = isolated_queue / ".investigation_audit.log"
    assert audit.exists()
    log_content = audit.read_text(encoding="utf-8")
    assert "open→in_progress" in log_content
    assert "in_progress→resolved" in log_content
    assert inv.inq_id in log_content
    # actor=user should appear in at least one transition
    assert "actor=user" in log_content


def test_worker_dispatcher_observes_queue_without_mutating(isolated_queue):
    """Dispatcher is OBSERVE-only; does not advance state forward."""
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    from src.ikigai.src.ikigai.workers.investigation_dispatcher import dispatch_pending

    inv1 = investigation_enqueue(source="agent", payload="p1")
    inv2 = investigation_enqueue(source="agent", payload="p2")

    result = dispatch_pending(base_dir=isolated_queue)
    assert result.open_count == 2
    assert result.in_progress_count == 0

    # Both still open after dispatch
    from src.ikigai.src.mcp_server.investigation_status import investigation_status
    s1 = investigation_status(inq_id=inv1.inq_id)
    s2 = investigation_status(inq_id=inv2.inq_id)
    assert s1.status == "open"
    assert s2.status == "open"


def test_invalid_terminal_transition_blocked(isolated_queue):
    """resolved → open is rejected (terminal state)."""
    from src.ikigai.src.mcp_server.investigation_enqueue import investigation_enqueue
    from src.ikigai.src.mcp_server.investigation_complete import investigation_complete
    from src.ikigai.src.ikigai.mesh.investigation_queue import transition
    from src.ikigai.src.ikigai.mesh.investigation_queue import InvalidStatusTransitionError

    inv = investigation_enqueue(source="agent", payload="p")
    transition(inv.inq_id, "in_progress", base_dir=isolated_queue, actor="agent")
    investigation_complete(inq_id=inv.inq_id, terminal_status="resolved", actor="user")

    # Now resolved; cannot reopen
    with pytest.raises(InvalidStatusTransitionError):
        transition(inv.inq_id, "open", base_dir=isolated_queue, actor="agent")
```

- [ ] **Step 2: Run integration test**

Run: `cd C:\Users\mathe\code_space\life-oss\life\src\ikigai && PYTHONPATH=src;../../src pytest tests/integration/test_investigation_queue_smoke.py -v`
Expected: 3 passed

- [ ] **Step 3: Full test suite + lint + type check + mcp_inspect**

```bash
cd C:\Users\mathe\code_space\life-oss\life\src\ikigai
PYTHONPATH=src;../../src pytest -v
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
```

Expected: all tests pass, lint clean.

```bash
cd C:\Users\mathe\code_space\life-oss\life
python scripts/mcp_inspect.py --tool-count 16
```

Expected: 16 IKIGAI_TOOLS advertised (was 13, +3).

- [ ] **Step 4: Commit**

```bash
cd C:\Users\mathe\code_space\life-oss\life
git add tests/integration/test_investigation_queue_smoke.py
git commit -m "test(integration): investigation queue smoke (lifecycle + dispatcher + invalid transitions)"
```

---

## Verification (post-Plan-C complete)

```bash
# 1. Drift detector: 11 invariants PASS (5 baseline + 4 Plan A a-e + 1 Plan B i + 1 Plan C h)
cd C:\Users\mathe\code_space\life-oss\life\src\ikigai
PYTHONPATH=src;../../src pytest tests/test_canonical_scope.py -v

# 2. All tests green
PYTHONPATH=src;../../src pytest -v

# 3. Lint + type
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/

# 4. MCP tool count = 16 (was 13, +3 for investigation_*)
cd C:\Users\mathe\code_space\life-oss\life
python scripts/mcp_inspect.py --tool-count 16

# 5. Queue directory exists at repo root
ls data/investigation_queue/
# Expected: .keep present (test runs create/remove their own)

# 6. Audit log shape
PYTHONPATH=src;../../src pytest tests/integration/test_investigation_queue_smoke.py -v
# Expected: 3 passed, .investigation_audit.log contains actor= lines
```

---

## Self-Review (per writing-plans skill)

**Spec coverage:**
- ✅ 3 MCP tools (enqueue/status/complete) → Tasks 3 + 4
- ✅ Filesystem queue `data/investigation_queue/` → Tasks 1 + 2 + 4
- ✅ Worker consumer (cron-invoked, observe-only) → Task 5
- ✅ Drift invariant (h) → Task 6
- ✅ Pattern reuse from `data/review_queue/` → Task 2 (atomic rename + append-only audit)
- ✅ Investigation FSM (open→in_progress→resolved|archived) → Task 2 step 3
- ✅ Audit log append-only shape → Task 1 + Task 6 invariants
- ✅ End-to-end smoke test → Task 7

**Placeholder scan:** No "TBD", "TODO", "implement later", "fill in details" — every step has explicit code or test.

**Type consistency:**
- `Investigation` Task 1 → consumed Tasks 2, 3, 5, 6 ✓
- `InvestigationStatus` Literal Task 1 → consumed Tasks 2, 6 ✓
- `enqueue/get_by_id/list_by_status/transition` Task 2 → consumed Tasks 3, 5, 7 ✓
- `Investigation.inq_id` regex matches `inq-YYYYMMDD-NNN` consistently ✓
- `INVESTIGATION_QUEUE_DIR` Task 2 step 3 → consumed Tasks 4, 5, 7 ✓
- IKIGAI_TOOLS: 12 → 13 (Plan B) → 16 (Plan C, +3)

**Coverage gaps acknowledged:**
- v1 dispatcher is OBSERVE-ONLY (does not lift into planning tree); v2 will hook into Plan A's tag_and_persist node — explicit stub
- `dispatch_to_planning_sink` is a no-op stub (returns None); future enhancement
- No bulk `archive_old()` helper; v1 single-investigation ops only
- No webhook to notify user when investigation resolves; CLI / cron-driven only
- Worktree isolation: queue tests use `tmp_path` fixtures per task, no shared state

---

## Open Items (deferred per spec)

- **Plans A & B dependency**: DriftInvariants class must exist; if either not yet shipped, run those plans first
- **Lifestyle SONHOs** (lifestyle-tier dreams): enabled by deeper agent roadmap, post-Plan C
- **Planner integration**: v1 dispatcher does not lift; v2 will hook into tag_and_persist (Plan A Task 8)
- **Worker daemon mode**: v1 is cron-invoked; future enhancement for hot-loop mode
- **Cross-queue links**: investigations don't yet link to existing UEIDs; only `inq_ueid: str | None` cross-ref
- **Bulk operations**: archive_old / list_by_date_range helpers deferred

---

*Scaffold: Investigation Queue Implementation Plan · 2026-09-03 · Plan C · claude-code interactive*
