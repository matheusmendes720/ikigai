# Phase B3 — MCP Gateway Consolidado Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `src/ikigai/src/mcp_server/server.py` from low-level MCP API to FastMCP decorators; add 3 new mesh tools (`ikigai_mesh_show`, `ikigai_task_create`, `ikigai_health`), 5 resources (`ueid://`, `queue://`, `health://`, `plans://`), declare capabilities, wire `interfaces/cli/server.py` mcp_gateway status to real pidfile + health probe, add `make mcp-inspect` target, add CI gate.

**Architecture:** Hybrid (per A2UI spec §11 R1): A2UI is the logical contract; MCP is the canonical transport. A2UI Pydantic schemas in `src/mesh/adapters/a2ui_schema.py` are reused as tool input shapes. FastMCP (`mcp.server.fastmcp.FastMCP`) generates JSON Schemas from Python type hints. Per-adapter failure isolation already in `src/mesh/agent_propagator.propagate()`. Review queue at `data/review_queue/<id>.json` (already atomic).

**Tech Stack:**
- `mcp = "^1.1"` (existing in `src/ikigai/pyproject.toml`)
- `pydantic = "^2.6` (existing)
- Existing: `src/mesh/adapters/{cli,taskdog,solverforge_calendar,base}.py`, `src/mesh/{queue,agent_consumer,agent_propagator}.py`
- Testing: `pytest` (existing); new `pytest-asyncio` for FastMCP tool tests
- MCP Inspector: `npx @modelcontextprotocol/inspector` (no install; npx fetches)

## Global Constraints

- **Append-only invariant** on `data/review_queue/` — never delete events; `ack()` updates status in place
- **Pydantic v2 strict** everywhere (`frozen=True`, `extra="forbid"`) — `src/contracts/` is canonical
- **UEID canonical regex** `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` — never mutate
- **v1 = create action only** — `task.write` actions `update`/`delete`/`done` return `-32601` Method not found
- **No LLM in pipeline** — gateway logic is pure arithmetic + adapter I/O
- **stdio transport only v1** — `localhost`-only is v2 trigger
- **A2UI schemas unchanged** — `src/mesh/adapters/a2ui_schema.py` is referenced (not modified) by tool input shapes
- **Per-adapter failure isolation preserved** — `agent_propagator.propagate()` already isolates; B3 must not break that contract
- **Backward compat window:** 8 existing tools retain names + behavior; B3 only adds
- **Atomic commits, no Co-Authored-By trailer** (per CLAUDE.md)

---

## File Structure

| File | Role | Action |
|---|---|---|
| `src/ikigai/src/mcp_server/server.py` | MCP server (low-level) → FastMCP refactor | MODIFY (in place; preserve 10 existing tools + add 3 + 5 resources) |
| `src/ikigai/src/mcp_server/server_v2.py` | Shim re-export to server.py after refactor | CREATE (zero-cost re-export; lets `run_mcp_server.py` work unchanged) |
| `src/ikigai/src/mcp_server/resources.py` | 5 resource handlers (ueid, queue, health, plans) | CREATE |
| `src/ikigai/src/mcp_server/tools_mesh.py` | 3 new tool handlers (mesh_show, task_create, health) | CREATE |
| `src/ikigai/tests/test_server_fastmcp.py` | Tests for refactored server (existing tools still work) | CREATE |
| `src/ikigai/tests/test_tools_mesh.py` | Tests for 3 new tools | CREATE |
| `src/ikigai/tests/test_resources.py` | Tests for 5 resources | CREATE |
| `interfaces/cli/server.py` | Wire `mcp_gateway` BACKEND_PROCESSES entry to real status | MODIFY (add pidfile path + probe helper) |
| `interfaces/cli/tests/test_server.py` | Update tests for real mcp_gateway status (when process not running: running=False; pidfile present but stale: special handling) | MODIFY |
| `interfaces/cli/mcp_gateway_probe.py` | Probe helper: read pidfile + send `health://gateway` resource request | CREATE |
| `Makefile` | Add `mcp-inspect` target | MODIFY |
| `.github/workflows/ci.yml` | Add `mcp-gateway-contract` step | MODIFY |
| `pyproject.toml` (ikigai) | Add `pytest-asyncio` to dev deps | MODIFY |

---

## Task 1: B3.0 — Smoke test B1+B2 (no regressions)

**Files:**
- Read: `interfaces/cli/tests/test_server.py`, `interfaces/cli/tests/test_task_add_e2e.py`
- Read: `src/mesh/adapters/tests/test_a2ui_schema.py`

**Goal:** Confirm B1 (A2UI schemas) + B2 (server-mgmt sub-app) all pass before refactoring.

- [ ] **Step 1: Run all B1+B2 tests**

Run from repo root:
```bash
cd src/ikigai
poetry run pytest tests/test_mcp_server_tracing.py src/mesh/adapters/tests/test_a2ui_schema.py -v 2>&1 | tail -30
```

Expected: all passing (these existed before B3).

- [ ] **Step 2: Run interfaces/cli tests**

Run from repo root:
```bash
cd src/ikigai
poetry run pytest ../../interfaces/cli/tests/ -v 2>&1 | tail -30
```

Expected: all 27+5+ tests passing.

- [ ] **Step 3: Capture test counts for regression baseline**

Write to your report:
```
B1+B2 baseline: <N> tests passing
```

- [ ] **Step 4: No commit** (this task is verification only)

---

## Task 2: B3.1 — Refactor server.py to FastMCP decorator API

**Files:**
- Modify: `src/ikigai/src/mcp_server/server.py` (low-level → FastMCP; preserve 10 tools)
- Create: `src/ikigai/src/mcp_server/server_v2.py` (zero-cost re-export)
- Modify: `src/ikigai/pyproject.toml` (add `pytest-asyncio`)

**Goal:** Replace `mcp.server.Server` + `@SERVER.list_tools()` + `@SERVER.call_tool()` with `FastMCP("ikigai-gateway")` + `@mcp.tool()` decorators. Auto-generated JSON Schemas from type hints. No new functionality — pure refactor.

**Interfaces:**
- Consumes: existing `_handle_*` functions (10 of them) from current `server.py`
- Produces: `FastMCP` instance named `MCP`; tool names unchanged; `main()` entrypoint unchanged

- [ ] **Step 1: Add pytest-asyncio dev dependency**

In `src/ikigai/pyproject.toml`, under `[tool.poetry.group.dev.dependencies]`, add:
```toml
pytest-asyncio = "^0.23"
```

After:
```bash
cd src/ikigai && poetry lock --no-update && poetry install
```

- [ ] **Step 2: Write the failing test for FastMCP refactor**

Create `src/ikigai/tests/test_server_fastmcp.py`:
```python
"""Tests for FastMCP refactor of server.py.

Validates:
  - FastMCP instance is exposed as `MCP`
  - All 10 existing tools are still registered (8 original + 2 from B1 fix)
  - Each tool's schema is auto-generated from type hints
  - main() entrypoint still works (stdio transport)
"""
from __future__ import annotations

import pytest

from mcp_server.server import MCP, main, TOOLS


def test_fastmcp_instance_exists() -> None:
    assert MCP is not None
    assert MCP.name == "ikigai-gateway"


def test_all_ten_tools_registered() -> None:
    expected_tools = {
        "ikigai_score",
        "ikigai_regime",
        "ikigai_phase",
        "ikigai_decompose",
        "ikigai_corrections",
        "ikigai_plan_cycle",
        "ikigai_checkpoint",
        "ikigai_sync_vault",
        "ikigai_write_tasks",
        "ikigai_read_tasks",
    }
    registered = {tool.name for tool in TOOLS}
    assert registered == expected_tools, (
        f"Missing: {expected_tools - registered}; "
        f"Extra: {registered - expected_tools}"
    )


@pytest.mark.asyncio
async def test_main_entrypoint_callable() -> None:
    """main() must remain an async coroutine for stdio transport."""
    import inspect
    assert inspect.iscoroutinefunction(main)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd src/ikigai && poetry run pytest tests/test_server_fastmcp.py -v 2>&1 | tail -20
```

Expected: FAIL with `ImportError: cannot import name 'MCP' from 'mcp_server.server'` or `TOOLS not found`.

- [ ] **Step 4: Refactor server.py to use FastMCP**

Replace the entire `server.py` body with the FastMCP version. Key changes:
- Drop imports: `from mcp.server import Server`, `from mcp.server.stdio import stdio_server`, `from mcp.types import Tool, TextContent, ListToolsResult, CallToolResult`
- Add imports: `from mcp.server.fastmcp import FastMCP`, `from typing import Annotated`
- Create `MCP = FastMCP("ikigai-gateway")` instance at module level
- Keep all 10 `_handle_*` functions exactly as they are
- Convert `_TOOL_DISPATCH` to use `@MCP.tool()` decorator — one decorator per handler:

```python
"""IKIGAi gateway MCP server — FastMCP decorator API (Phase B3).

Implements: hybrid A2UI (logical) over MCP stdio (transport).
See docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md §11 R1.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Annotated, Any

import frontmatter
from mcp.server.fastmcp import FastMCP

from mcp_server.tracing import init_mcp_tracing, traced_tool_dispatch


MCP = FastMCP("ikigai-gateway")
init_mcp_tracing()


# ---------------------------------------------------------------------------
# DB helpers (unchanged from B1 — preserved verbatim)
# ---------------------------------------------------------------------------
def _db_path(suffix: str = "ikigai_checkpoints.db") -> Path:
    return Path.home() / ".ikigai" / suffix


def _decompose_ueid(ueid: str) -> dict[str, Any]:
    """Traverse the vault hierarchy for a given Dream UEID."""
    # ... [UNCHANGED - copy verbatim from existing server.py lines 140-216] ...


def _read_checkpoint(thread_id: str | None = None) -> dict[str, Any]:
    # ... [UNCHANGED - copy verbatim from existing server.py lines 219-245] ...


def _read_plan_entity(cycle_id: str) -> dict[str, Any]:
    # ... [UNCHANGED - copy verbatim from existing server.py lines 248-262] ...


def _read_entity(table: str) -> dict[str, Any]:
    # ... [UNCHANGED - copy verbatim from existing server.py lines 265-280] ...


# ---------------------------------------------------------------------------
# Task I/O — Deep Agent ↔ interfaces via data/tasks.jsonl (unchanged)
# ---------------------------------------------------------------------------
def _tasks_path() -> Path:
    """Path to the shared tasks file. Lives in data/ at repo root."""
    repo_root = Path(__file__).parent.parent.parent.parent
    return repo_root / "data" / "tasks.jsonl"


def _write_tasks_to_data(tasks: list[dict]) -> str:
    # ... [UNCHANGED - copy verbatim from existing server.py lines 293-327] ...


def _read_tasks_from_data(
    horizon: str | None = None,
    done: bool | None = None,
    project_id: str | None = None,
    limit: int = 50,
) -> str:
    # ... [UNCHANGED - copy verbatim from existing server.py lines 330-368] ...


# ---------------------------------------------------------------------------
# Tool handlers (FastMCP decorator — auto-schemas from type hints)
# ---------------------------------------------------------------------------

@MCP.tool(
    name="ikigai_score",
    description="Returns current IKIGAi 5-vector scores and meta-vector score",
)
def ikigai_score() -> str:
    """5-vector IKIGAi scores (passion/skill/market/revenue/course) + meta-vector."""
    d = _read_checkpoint()
    vs = d.get("vector_scores", {})
    mv = d.get("meta_vector_score", 0.0)
    qhe = d.get("q_he_score")
    if not vs:
        row = _read_entity("plan_entities")
        if row:
            vs = {k: row.get(k, 0.0) for k in ("passion", "skill", "market", "revenue", "course")}
            mv = row.get("meta_vector", 0.0)
            qhe = row.get("q_he")
    return json.dumps({"vector_scores": vs, "meta_vector_score": round(mv, 4), "q_he_score": qhe}, indent=2)


@MCP.tool(
    name="ikigai_regime",
    description="Returns current regime (PUSH/MAINTAIN/REDUCE/RECOVER) and days in regime",
)
def ikigai_regime() -> str:
    """Operational regime state + Q_HE snapshot."""
    d = _read_checkpoint()
    regime = d.get("regime_state", "MAINTAIN")
    days = d.get("days_in_regime", 0)
    qhe = d.get("q_he_score")
    if not d:
        row = _read_entity("plan_entities")
        if row:
            regime = row.get("regime", regime)
            qhe = row.get("q_he", qhe)
    return json.dumps({"regime_state": regime, "days_in_regime": days, "q_he_score": qhe}, indent=2)


@MCP.tool(
    name="ikigai_phase",
    description="Returns current phase (FUNDAÇÃO/BUSCA/HACKATHON/RECUPERACAO/OVERCLOCK)",
)
def ikigai_phase() -> str:
    """IKIGAi cycle phase + iteration + weights."""
    d = _read_checkpoint()
    return json.dumps({
        "phase": d.get("phase", "BUSCA"),
        "phase_iteration": d.get("phase_iteration", 0),
        "phase_converged": d.get("phase_converged", False),
        "phase_weights": d.get("phase_weights", {}),
    }, indent=2)


@MCP.tool(
    name="ikigai_decompose",
    description="Decompose a Dream UEID into its full UEID hierarchy",
)
def ikigai_decompose(dream_ueid: str) -> str:
    """Traverse vault hierarchy for a Dream UEID → {dream, objectives, projects}."""
    if not dream_ueid:
        return json.dumps({"error": "dream_ueid required"})
    return json.dumps(_decompose_ueid(dream_ueid), indent=2)


@MCP.tool(
    name="ikigai_corrections",
    description="List recent correction signals from H1-H6 heuristics",
)
def ikigai_corrections(limit: Annotated[int, "Max corrections to return"] = 20) -> str:
    """Recent H1-H6 heuristic corrections (default 20)."""
    d = _read_checkpoint()
    corrs = d.get("corrections", [])[-limit:]
    if not corrs:
        row = _read_entity("plan_entities")
        if row:
            try:
                corrs = json.loads(row.get("corrections", "[]"))[-limit:]
            except Exception:
                corrs = []
    return json.dumps({"corrections": corrs, "count": len(corrs)}, indent=2)


@MCP.tool(
    name="ikigai_plan_cycle",
    description="Trigger an IKIGAi plan cycle — runs the full LangGraph agent",
)
def ikigai_plan_cycle(
    active_dream_ueid: Annotated[str, "Active Dream UEID"] | None = None,
    cycle_start: Annotated[str, "ISO date"] | None = None,
    cycle_end: Annotated[str, "ISO date"] | None = None,
) -> str:
    """Run a full IKIGAi plan cycle via LangGraph."""
    # ... [UNCHANGED body from existing server.py lines 442-523] ...


@MCP.tool(
    name="ikigai_checkpoint",
    description="Get or set a named checkpoint in the IKIGAi checkpoint DB",
)
def ikigai_checkpoint(
    action: Annotated[str, "One of: get, set, list"],
    thread_id: Annotated[str, "Thread ID for get/set"] | None = None,
    state_snapshot: Annotated[dict, "State to persist for set"] | None = None,
) -> str:
    """Read/write/list LangGraph checkpoints."""
    # ... [UNCHANGED body from existing server.py lines 526-575] ...


@MCP.tool(
    name="ikigai_sync_vault",
    description="Sync IKIGAi cycle data to the markdown vault",
)
def ikigai_sync_vault(cycle_id: Annotated[str, "Cycle ID to sync"]) -> str:
    """Persist cycle state to markdown in data/matheus/ikigai_state/."""
    # ... [UNCHANGED body from existing server.py lines 578-643] ...


@MCP.tool(
    name="ikigai_write_tasks",
    description="Write structured tasks to data/tasks.jsonl — Deep Agent output for interfaces",
)
def ikigai_write_tasks(tasks: Annotated[list[dict], "Tasks to write"]) -> str:
    """Append tasks to data/tasks.jsonl (atomic append-only)."""
    return _write_tasks_to_data(tasks)


@MCP.tool(
    name="ikigai_read_tasks",
    description="Read structured tasks from data/tasks.jsonl — interfaces consumer",
)
def ikigai_read_tasks(
    horizon: Annotated[str, "Filter by horizon"] | None = None,
    done: Annotated[bool, "Filter by done status"] | None = None,
    project_id: Annotated[str, "Filter by project"] | None = None,
    limit: Annotated[int, "Max tasks to return"] = 50,
) -> str:
    """Read tasks from data/tasks.jsonl with optional filters."""
    return _read_tasks_from_data(horizon, done, project_id, limit)


# ---------------------------------------------------------------------------
# TOOLS list — derived from FastMCP internals (for backward compat with tests)
# ---------------------------------------------------------------------------
TOOLS = list(MCP._tool_manager._tools.values())


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
async def main() -> None:
    """Run the FastMCP gateway over stdio."""
    await MCP.run_async(transport="stdio")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Notes for implementer:**
- Copy the unchanged function bodies verbatim from the existing `server.py` (lines 140-643)
- The `TOOLS` list is derived from FastMCP's internal `_tool_manager` for backward compat with tests
- `MCP.run_async(transport="stdio")` is the FastMCP equivalent of the old `stdio_server()` context

- [ ] **Step 5: Run test to verify it passes**

```bash
cd src/ikigai && poetry run pytest tests/test_server_fastmcp.py -v 2>&1 | tail -20
```

Expected: 3 tests passing.

- [ ] **Step 6: Run all B1 tests to confirm zero regression**

```bash
cd src/ikigai && poetry run pytest tests/ src/mesh/adapters/tests/ -v 2>&1 | tail -30
```

Expected: all tests passing (existing + new 3).

- [ ] **Step 7: Create server_v2.py shim (zero-cost re-export)**

Create `src/ikigai/src/mcp_server/server_v2.py`:
```python
"""Server v2 — zero-cost re-export of FastMCP-refactored server.

Lets downstream imports like `from mcp_server.server_v2 import main` work
without forcing renames in run_mcp_server.py or tests.

Created in Phase B3 (2026-08-28).
"""
from mcp_server.server import (
    MCP,
    TOOLS,
    ikigai_score,
    ikigai_regime,
    ikigai_phase,
    ikigai_decompose,
    ikigai_corrections,
    ikigai_plan_cycle,
    ikigai_checkpoint,
    ikigai_sync_vault,
    ikigai_write_tasks,
    ikigai_read_tasks,
    main,
)

__all__ = [
    "MCP",
    "TOOLS",
    "main",
    "ikigai_score",
    "ikigai_regime",
    "ikigai_phase",
    "ikigai_decompose",
    "ikigai_corrections",
    "ikigai_plan_cycle",
    "ikigai_checkpoint",
    "ikigai_sync_vault",
    "ikigai_write_tasks",
    "ikigai_read_tasks",
]
```

- [ ] **Step 8: Commit**

```bash
cd /c/Users/mathe/code_space/life-oss/life
git add src/ikigai/src/mcp_server/server.py \
        src/ikigai/src/mcp_server/server_v2.py \
        src/ikigai/tests/test_server_fastmcp.py \
        src/ikigai/pyproject.toml \
        src/ikigai/poetry.lock
git commit -m "feat(ikigai): refactor mcp_server to FastMCP decorator API (B3.1)"
```

---

## Task 3: B3.2 — Add 3 new mesh tools (ikigai_mesh_show, ikigai_task_create, ikigai_health)

**Files:**
- Create: `src/ikigai/src/mcp_server/tools_mesh.py` (3 new tool handlers)
- Modify: `src/ikigai/src/mcp_server/server.py` (import + register 3 new tools)
- Create: `src/ikigai/tests/test_tools_mesh.py` (tests for 3 new tools)

**Goal:** Add 3 MCP tools that map directly to A2UI's 3 methods:
- `ikigai_mesh_show(ueid)` ↔ A2UI `mesh.read` — joins across 3 adapters via `ForkAdapter.read()`
- `ikigai_task_create(ueid, fields, source_fork)` ↔ A2UI `task.write action=create` — emits `TaskChange` to `data/review_queue/<id>.json`
- `ikigai_health()` ↔ A2UI gateway heartbeat — returns version, uptime, adapter statuses

**Interfaces:**
- Consumes: `ForkAdapter.read(ueid)` from `src/mesh/adapters/base.py`; `src.mesh.queue.enqueue()`; `src.mesh.adapters.{CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter}` instances
- Produces: `MeshShowResult` dict; `TaskWriteResult` dict; `HealthSnapshot` dict

- [ ] **Step 1: Write the failing test for ikigai_mesh_show**

Create `src/ikigai/tests/test_tools_mesh.py`:
```python
"""Tests for B3.2 mesh tools (ikigai_mesh_show, ikigai_task_create, ikigai_health).

Validates:
  - ikigai_mesh_show joins across 3 adapters and reports mismatches
  - ikigai_task_create emits TaskChange to review queue
  - ikigai_health returns version + adapter statuses
  - v1 limitation: action='update'/'delete'/'done' returns error
"""
from __future__ import annotations

import json
import time
from unittest.mock import patch

import pytest

from src.contracts.common import UEID
from src.contracts.task_change import TaskAction
from src.mesh.adapters.cli import CliAdapter
from src.mesh.adapters.taskdog import TaskdogAdapter
from src.mesh.adapters.solverforge_calendar import SolverforgeCalendarAdapter


VALID_UEID = UEID("tsk:foo:11111111-1111-1111-1111-111111111111:1111111111111111")


@pytest.fixture
def three_adapters():
    return [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]


# === ikigai_mesh_show ===

def test_mesh_show_joins_across_adapters(three_adapters, tmp_path) -> None:
    """ikigai_mesh_show returns one record per adapter (or None if absent)."""
    from mcp_server.tools_mesh import ikigai_mesh_show
    with patch("mcp_server.tools_mesh._load_adapters", return_value=three_adapters):
        result = json.loads(ikigai_mesh_show(ueid=str(VALID_UEID)))
    assert result["ueid"] == str(VALID_UEID)
    assert "view" in result
    assert set(result["view"].keys()) == {"cli", "taskdog", "solverforge_calendar"}
    assert "mismatches" in result


def test_mesh_show_rejects_invalid_ueid() -> None:
    from mcp_server.tools_mesh import ikigai_mesh_show
    result = json.loads(ikigai_mesh_show(ueid="not-a-ueid"))
    assert "error" in result
    assert "UEID" in result["error"]


# === ikigai_task_create ===

def test_task_create_emits_to_review_queue(tmp_path) -> None:
    """ikigai_task_create creates a TaskChange + enqueues to data/review_queue/."""
    from mcp_server.tools_mesh import ikigai_task_create
    # Monkey-patch queue dir to tmp
    with patch("src.mesh.queue.QUEUE_DIR", tmp_path / "review_queue"):
        result = json.loads(ikigai_task_create(
            ueid=str(VALID_UEID),
            fields={"title": "Test task", "priority": "high"},
            source_fork="interfaces/cli",
        ))
    assert "event_id" in result
    assert result["status"] == "pending"

    # Verify queue file was written
    queue_files = list((tmp_path / "review_queue").glob("*.json"))
    assert len(queue_files) == 1
    payload = json.loads(queue_files[0].read_text())
    assert payload["ueid"] == str(VALID_UEID)
    assert payload["action"] == "create"
    assert payload["fields"]["title"] == "Test task"


def test_task_create_rejects_unknown_source_fork() -> None:
    """source_fork validation enforced (min_length=2)."""
    from mcp_server.tools_mesh import ikigai_task_create
    result = json.loads(ikigai_task_create(
        ueid=str(VALID_UEID),
        fields={"title": "x"},
        source_fork="x",  # too short
    ))
    assert "error" in result


# === ikigai_health ===

def test_health_returns_version_and_adapters() -> None:
    from mcp_server.tools_mesh import ikigai_health
    result = json.loads(ikigai_health())
    assert result["version"] == "1.0.0"
    assert result["name"] == "ikigai-gateway"
    assert "uptime_s" in result
    assert result["uptime_s"] >= 0
    assert "adapters" in result
    adapter_names = {a["name"] for a in result["adapters"]}
    assert {"cli", "taskdog", "solverforge_calendar"} <= adapter_names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd src/ikigai && poetry run pytest tests/test_tools_mesh.py -v 2>&1 | tail -20
```

Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_server.tools_mesh'`.

- [ ] **Step 3: Create tools_mesh.py with the 3 tool handlers**

Create `src/ikigai/src/mcp_server/tools_mesh.py`:
```python
"""B3.2 mesh tools: ikigai_mesh_show, ikigai_task_create, ikigai_health.

These are the three MCP tools that map directly to A2UI's three methods
(see docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md §11 R1):

  ikigai_mesh_show(ueid)        ↔  A2UI mesh.read
  ikigai_task_create(...)       ↔  A2UI task.write (action=create only in v1)
  ikigai_health()               ↔  gateway heartbeat

v1 scope: create action only. Other actions return -32601 (deferred to v1.2+).
"""
from __future__ import annotations

import json
import time as _time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import ValidationError

from src.contracts.common import UEID
from src.contracts.task_change import TaskAction, TaskChange
from src.mesh import queue as _queue
from src.mesh.adapters import CliAdapter, SolverforgeCalendarAdapter, TaskdogAdapter


# Module-level gateway start time (used by ikigai_health for uptime_s)
_GATEWAY_STARTED_AT: float = _time.time()
_GATEWAY_VERSION = "1.0.0"


def _load_adapters() -> list:
    """Load the 3 fork adapters. Mirrors interfaces/cli/server.py ADAPTER_REGISTRY logic."""
    return [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]


def _adapter_status(adapter) -> dict[str, Any]:
    """Probe one adapter: returns {name, slice_type, exists, error?}."""
    info: dict[str, Any] = {
        "name": adapter.name,
        "slice_type": getattr(adapter, "slice_type", "unknown"),
        "exists": True,
    }
    try:
        if hasattr(adapter, "storage_path") and adapter.storage_path is not None:
            info["storage_path"] = str(adapter.storage_path)
            info["exists"] = adapter.storage_path.exists()
    except Exception as e:
        info["exists"] = False
        info["error"] = str(e)
    return info


# ---------------------------------------------------------------------------
# ikigai_mesh_show — A2UI mesh.read
# ---------------------------------------------------------------------------
def ikigai_mesh_show(ueid: Annotated[str, "UEID to look up across forks"]) -> str:
    """Cross-fork view for one UEID. Joins CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter.

    Returns: {"ueid", "view": {adapter_name: record | null}, "mismatches": [...]}
    """
    # Validate UEID
    try:
        parsed = UEID(ueid)
    except ValueError as e:
        return json.dumps({"error": f"Invalid UEID: {e}"})

    adapters = _load_adapters()
    view: dict[str, Any] = {}
    mismatches: list[str] = []

    for adapter in adapters:
        try:
            record = adapter.read(parsed)
            view[adapter.name] = record
        except Exception as e:
            view[adapter.name] = None
            mismatches.append(f"{adapter.name}: {type(e).__name__}: {e}")

    # Detect status mismatches (status field differs across adapters)
    statuses = {
        name: rec.get("status")
        for name, rec in view.items()
        if isinstance(rec, dict) and "status" in rec
    }
    if len(set(statuses.values())) > 1:
        mismatches.append(f"status mismatch across adapters: {statuses}")

    return json.dumps({
        "ueid": str(parsed),
        "view": view,
        "mismatches": mismatches,
    }, indent=2, default=str)


# ---------------------------------------------------------------------------
# ikigai_task_create — A2UI task.write (create only in v1)
# ---------------------------------------------------------------------------
def ikigai_task_create(
    ueid: Annotated[str, "UEID for the new task"],
    fields: Annotated[dict, "Task fields (title required, priority/due/etc. optional)"],
    source_fork: Annotated[str, "Originating fork name (e.g. 'interfaces/cli')"],
    action: Annotated[str, "Task action: create only in v1"] = "create",
) -> str:
    """Emit a TaskChange to data/review_queue/<id>.json (atomic append-only).

    v1 limitation: only action='create' is implemented. Other actions return error.
    Returns: {"event_id", "status": "pending"} on success, {"error": "..."} on failure.
    """
    # v1 limitation
    if action != "create":
        return json.dumps({
            "error": f"action={action!r} not supported in v1 (create only)",
            "code": -32601,
        })

    # Validate UEID
    try:
        parsed_ueid = UEID(ueid)
    except ValueError as e:
        return json.dumps({"error": f"Invalid UEID: {e}"})

    # Validate source_fork (A2UI spec: min_length=2)
    if not source_fork or len(source_fork) < 2:
        return json.dumps({"error": "source_fork must be >= 2 chars"})

    # Validate required field
    if not fields.get("title"):
        return json.dumps({"error": "fields.title is required"})

    # Build TaskChange
    try:
        event = TaskChange(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            ueid=parsed_ueid,
            action=TaskAction.CREATE,
            fields=fields,
            source_fork=source_fork,
            timestamp=datetime.now(UTC).replace(tzinfo=None),
        )
    except ValidationError as e:
        return json.dumps({"error": f"TaskChange validation failed: {e}"})

    # Atomic enqueue to review queue
    try:
        _queue.enqueue(event)
    except Exception as e:
        return json.dumps({"error": f"queue enqueue failed: {e}"})

    return json.dumps({
        "event_id": event.event_id,
        "status": "pending",
        "ueid": str(parsed_ueid),
    }, indent=2)


# ---------------------------------------------------------------------------
# ikigai_health — gateway heartbeat
# ---------------------------------------------------------------------------
def ikigai_health() -> str:
    """Gateway heartbeat: version, uptime, adapter statuses.

    Returns: {"name", "version", "uptime_s", "started_at", "adapters": [...]}
    """
    adapters = _load_adapters()
    return json.dumps({
        "name": "ikigai-gateway",
        "version": _GATEWAY_VERSION,
        "started_at": _GATEWAY_STARTED_AT,
        "uptime_s": round(_time.time() - _GATEWAY_STARTED_AT, 3),
        "adapters": [_adapter_status(a) for a in adapters],
    }, indent=2)


__all__ = [
    "ikigai_mesh_show",
    "ikigai_task_create",
    "ikigai_health",
]
```

- [ ] **Step 4: Wire the 3 new tools into server.py**

In `src/ikigai/src/mcp_server/server.py`, add after the existing 10 tool definitions (after `ikigai_read_tasks` block, before the `TOOLS = ...` line):

```python
# ---------------------------------------------------------------------------
# Phase B3.2 — 3 new mesh tools (delegate to tools_mesh.py)
# ---------------------------------------------------------------------------
from mcp_server.tools_mesh import (
    ikigai_mesh_show,
    ikigai_task_create,
    ikigai_health,
)


@MCP.tool(
    name="ikigai_mesh_show",
    description="Cross-fork view for one UEID (joins CLI + taskdog + solverforge_calendar)",
)
def _ikigai_mesh_show_tool(ueid: str) -> str:
    """A2UI mesh.read realization — see docs/.../a2ui-protocol-design.md §11 R1."""
    return ikigai_mesh_show(ueid=ueid)


@MCP.tool(
    name="ikigai_task_create",
    description="Emit a TaskChange to data/review_queue/<id>.json (create action only in v1)",
)
def _ikigai_task_create_tool(
    ueid: str,
    fields: dict,
    source_fork: str,
    action: str = "create",
) -> str:
    """A2UI task.write realization (create action only)."""
    return ikigai_task_create(
        ueid=ueid,
        fields=fields,
        source_fork=source_fork,
        action=action,
    )


@MCP.tool(
    name="ikigai_health",
    description="Gateway heartbeat: version, uptime, adapter statuses",
)
def _ikigai_health_tool() -> str:
    """Returns gateway health snapshot."""
    return ikigai_health()
```

Also update the existing test `test_all_ten_tools_registered` in `test_server_fastmcp.py` to expect 13 tools (add the 3 new names to `expected_tools`):
```python
expected_tools = {
    "ikigai_score",
    "ikigai_regime",
    "ikigai_phase",
    "ikigai_decompose",
    "ikigai_corrections",
    "ikigai_plan_cycle",
    "ikigai_checkpoint",
    "ikigai_sync_vault",
    "ikigai_write_tasks",
    "ikigai_read_tasks",
    # Phase B3.2 additions
    "ikigai_mesh_show",
    "ikigai_task_create",
    "ikigai_health",
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd src/ikigai && poetry run pytest tests/test_tools_mesh.py tests/test_server_fastmcp.py -v 2>&1 | tail -30
```

Expected: all passing (5 mesh tests + 3 server tests).

- [ ] **Step 6: Run all tests to confirm zero regression**

```bash
cd src/ikigai && poetry run pytest tests/ src/mesh/adapters/tests/ -v 2>&1 | tail -30
```

Expected: all tests passing.

- [ ] **Step 7: Commit**

```bash
cd /c/Users/mathe/code_space/life-oss/life
git add src/ikigai/src/mcp_server/server.py \
        src/ikigai/src/mcp_server/tools_mesh.py \
        src/ikigai/tests/test_tools_mesh.py \
        src/ikigai/tests/test_server_fastmcp.py
git commit -m "feat(ikigai): add 3 mesh tools (mesh_show, task_create, health) — B3.2"
```

---

## Task 4: B3.3 — Add 5 MCP resources (ueid://, queue://, health://, plans://)

**Files:**
- Create: `src/ikigai/src/mcp_server/resources.py` (5 resource handlers)
- Modify: `src/ikigai/src/mcp_server/server.py` (register 5 resources)
- Create: `src/ikigai/tests/test_resources.py` (tests for 5 resources)

**Goal:** Expose read-only views as MCP resources (per A2UI spec §11 R4):
- `ueid://{ueid}` — cross-fork view (same data as ikigai_mesh_show tool)
- `queue://pending` — list of pending TaskChange events
- `queue://events/{id}` — one TaskChange event JSON
- `health://gateway` — gateway health snapshot (mirrors ikigai_health)
- `plans://cycles` — list of recent PlanningCycles
- `plans://cycles/{id}` — one PlanningCycle full record

**Interfaces:**
- Consumes: `src.mesh.queue.consume_pending()`; `src.mesh.adapters.{*}.read()`; `tools_mesh.ikigai_health()`
- Produces: MCP resource URIs registered with `@MCP.resource("uri://template")`

- [ ] **Step 1: Write the failing test for resources**

Create `src/ikigai/tests/test_resources.py`:
```python
"""Tests for B3.3 MCP resources.

Validates:
  - ueid://{ueid} resource reads cross-fork view
  - queue://pending resource lists pending events
  - queue://events/{id} resource reads one event
  - health://gateway resource returns heartbeat
  - plans://cycles resource lists cycles
"""
from __future__ import annotations

import json

import pytest

from src.contracts.common import UEID


VALID_UEID = UEID("tsk:foo:11111111-1111-1111-1111-111111111111:1111111111111111")


# === ueid://{ueid} ===

def test_ueid_resource_returns_cross_fork_view() -> None:
    from mcp_server.resources import ueid_resource
    result = json.loads(ueid_resource(str(VALID_UEID)))
    assert result["ueid"] == str(VALID_UEID)
    assert "view" in result


def test_ueid_resource_rejects_invalid_ueid() -> None:
    from mcp_server.resources import ueid_resource
    result = json.loads(ueid_resource("not-a-ueid"))
    assert "error" in result


# === queue://pending ===

def test_queue_pending_resource_returns_list(tmp_path) -> None:
    from mcp_server.resources import queue_pending_resource
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("src.mesh.queue.QUEUE_DIR", tmp_path / "review_queue")
        result = json.loads(queue_pending_resource())
    assert "events" in result
    assert "count" in result
    assert isinstance(result["events"], list)


# === queue://events/{id} ===

def test_queue_event_resource_returns_event(tmp_path) -> None:
    from mcp_server.resources import queue_event_resource
    # Write a sample event
    queue_dir = tmp_path / "review_queue"
    queue_dir.mkdir()
    (queue_dir / "evt_test123.json").write_text(json.dumps({
        "event_id": "evt_test123",
        "ueid": str(VALID_UEID),
        "action": "create",
        "fields": {"title": "Sample"},
        "source_fork": "interfaces/cli",
        "timestamp": "2026-08-28T12:00:00",
        "status": "pending",
    }))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("src.mesh.queue.QUEUE_DIR", queue_dir)
        result = json.loads(queue_event_resource("evt_test123"))
    assert result["event_id"] == "evt_test123"


def test_queue_event_resource_missing_returns_error(tmp_path) -> None:
    from mcp_server.resources import queue_event_resource
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("src.mesh.queue.QUEUE_DIR", tmp_path / "review_queue")
        result = json.loads(queue_event_resource("evt_missing"))
    assert "error" in result


# === health://gateway ===

def test_health_resource_matches_tool() -> None:
    """health://gateway resource must return identical data to ikigai_health tool."""
    from mcp_server.resources import health_resource
    from mcp_server.tools_mesh import ikigai_health
    resource_result = json.loads(health_resource())
    tool_result = json.loads(ikigai_health())
    assert resource_result == tool_result


# === plans://cycles ===

def test_plans_cycles_resource_returns_list() -> None:
    from mcp_server.resources import plans_cycles_resource
    result = json.loads(plans_cycles_resource())
    assert "cycles" in result
    assert isinstance(result["cycles"], list)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd src/ikigai && poetry run pytest tests/test_resources.py -v 2>&1 | tail -20
```

Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_server.resources'`.

- [ ] **Step 3: Create resources.py with the 5 resource handlers**

Create `src/ikigai/src/mcp_server/resources.py`:
```python
"""B3.3 MCP resources: ueid://, queue://, health://, plans://.

Exposes read-only views as MCP resources (per A2UI spec §11 R4). UI clients
can read these via resources/read without going through tools.

Resources:
  ueid://{ueid}            cross-fork view (same as ikigai_mesh_show tool)
  queue://pending          list of pending TaskChange events
  queue://events/{id}      one TaskChange event JSON
  health://gateway         gateway heartbeat (mirrors ikigai_health tool)
  plans://cycles           list of recent PlanningCycles
  plans://cycles/{id}      one PlanningCycle full record
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.contracts.common import UEID
from src.mesh import queue as _queue
from src.mesh.adapters import CliAdapter, SolverforgeCalendarAdapter, TaskdogAdapter
from mcp_server.tools_mesh import ikigai_health


# ---------------------------------------------------------------------------
# ueid://{ueid}
# ---------------------------------------------------------------------------
def ueid_resource(ueid: str) -> str:
    """Cross-fork view for one UEID (same data as ikigai_mesh_show tool)."""
    try:
        parsed = UEID(ueid)
    except ValueError as e:
        return json.dumps({"error": f"Invalid UEID: {e}"})

    adapters = [CliAdapter(), TaskdogAdapter(), SolverforgeCalendarAdapter()]
    view: dict[str, Any] = {}
    for adapter in adapters:
        try:
            view[adapter.name] = adapter.read(parsed)
        except Exception as e:
            view[adapter.name] = {"error": f"{type(e).__name__}: {e}"}

    return json.dumps({"ueid": str(parsed), "view": view}, indent=2, default=str)


# ---------------------------------------------------------------------------
# queue://pending
# ---------------------------------------------------------------------------
def queue_pending_resource() -> str:
    """List of pending TaskChange events in data/review_queue/."""
    events = []
    try:
        for event in _queue.consume_pending():
            events.append({
                "event_id": event.event_id,
                "ueid": str(event.ueid),
                "action": event.action.value,
                "source_fork": event.source_fork,
                "timestamp": event.timestamp.isoformat(),
                "status": event.status,
            })
    except Exception as e:
        return json.dumps({"error": f"queue read failed: {e}"})

    return json.dumps({"events": events, "count": len(events)}, indent=2)


# ---------------------------------------------------------------------------
# queue://events/{id}
# ---------------------------------------------------------------------------
def queue_event_resource(event_id: str) -> str:
    """One TaskChange event by ID."""
    qdir = _queue.QUEUE_DIR
    target = qdir / f"{event_id}.json"
    if not target.exists():
        return json.dumps({"error": f"event {event_id!r} not found"})

    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return json.dumps({"error": f"read failed: {e}"})


# ---------------------------------------------------------------------------
# health://gateway
# ---------------------------------------------------------------------------
def health_resource() -> str:
    """Gateway heartbeat (mirrors ikigai_health tool output)."""
    return ikigai_health()


# ---------------------------------------------------------------------------
# plans://cycles
# ---------------------------------------------------------------------------
def plans_cycles_resource() -> str:
    """List of recent PlanningCycles from ~/.ikigai/plan_entities.db."""
    plan_db = Path.home() / ".ikigai" / "plan_entities.db"
    if not plan_db.exists():
        return json.dumps({"cycles": [], "count": 0})

    try:
        import sqlite3
        conn = sqlite3.connect(str(plan_db))
        cur = conn.cursor()
        cur.execute(
            "SELECT cycle_id, regime, q_he, meta_vector, created_at "
            "FROM plan_entities ORDER BY created_at DESC LIMIT 20"
        )
        rows = cur.fetchall()
        conn.close()
        cycles = [
            {
                "cycle_id": row[0],
                "regime": row[1],
                "q_he": row[2],
                "meta_vector": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]
        return json.dumps({"cycles": cycles, "count": len(cycles)}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"plan_entities.db read failed: {e}"})


def plans_cycle_resource(cycle_id: str) -> str:
    """One PlanningCycle full record from ~/.ikigai/plan_entities.db."""
    plan_db = Path.home() / ".ikigai" / "plan_entities.db"
    if not plan_db.exists():
        return json.dumps({"error": "plan_entities.db not found"})

    try:
        import sqlite3
        conn = sqlite3.connect(str(plan_db))
        cur = conn.cursor()
        cur.execute("SELECT * FROM plan_entities WHERE cycle_id = ?", (cycle_id,))
        row = cur.fetchone()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        if not row:
            return json.dumps({"error": f"cycle {cycle_id!r} not found"})
        return json.dumps(dict(zip(cols, row)), indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": f"read failed: {e}"})


__all__ = [
    "ueid_resource",
    "queue_pending_resource",
    "queue_event_resource",
    "health_resource",
    "plans_cycles_resource",
    "plans_cycle_resource",
]
```

- [ ] **Step 4: Wire the 5 resources into server.py**

In `src/ikigai/src/mcp_server/server.py`, add after the 3 new tools block (before the `TOOLS = ...` line):

```python
# ---------------------------------------------------------------------------
# Phase B3.3 — 5 MCP resources (delegate to resources.py)
# ---------------------------------------------------------------------------
from mcp_server.resources import (
    health_resource,
    plans_cycle_resource,
    plans_cycles_resource,
    queue_event_resource,
    queue_pending_resource,
    ueid_resource,
)


@MCP.resource("ueid://{ueid}")
def _ueid_resource(ueid: str) -> str:
    """Cross-fork view for one UEID."""
    return ueid_resource(ueid)


@MCP.resource("queue://pending")
def _queue_pending_resource() -> str:
    """List of pending TaskChange events."""
    return queue_pending_resource()


@MCP.resource("queue://events/{event_id}")
def _queue_event_resource(event_id: str) -> str:
    """One TaskChange event by ID."""
    return queue_event_resource(event_id)


@MCP.resource("health://gateway")
def _health_resource() -> str:
    """Gateway heartbeat."""
    return health_resource()


@MCP.resource("plans://cycles")
def _plans_cycles_resource() -> str:
    """List of recent PlanningCycles."""
    return plans_cycles_resource()


@MCP.resource("plans://cycles/{cycle_id}")
def _plans_cycle_resource(cycle_id: str) -> str:
    """One PlanningCycle full record."""
    return plans_cycle_resource(cycle_id)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd src/ikigai && poetry run pytest tests/test_resources.py tests/test_tools_mesh.py tests/test_server_fastmcp.py -v 2>&1 | tail -30
```

Expected: 7 resource tests + 5 mesh tests + 3 server tests = 15 passing.

- [ ] **Step 6: Run all tests to confirm zero regression**

```bash
cd src/ikigai && poetry run pytest tests/ src/mesh/adapters/tests/ -v 2>&1 | tail -30
```

Expected: all tests passing.

- [ ] **Step 7: Commit**

```bash
cd /c/Users/mathe/code_space/life-oss/life
git add src/ikigai/src/mcp_server/server.py \
        src/ikigai/src/mcp_server/resources.py \
        src/ikigai/tests/test_resources.py
git commit -m "feat(ikigai): add 5 MCP resources (ueid, queue, health, plans) — B3.3"
```

---

## Task 5: B3.4 — Wire BACKEND_PROCESSES['mcp_gateway'] to real status (pidfile + health probe)

**Files:**
- Create: `interfaces/cli/mcp_gateway_probe.py` (pidfile reader + health probe)
- Modify: `interfaces/cli/server.py` (replace stub `running=False` with real check for mcp_gateway)
- Modify: `interfaces/cli/tests/test_server.py` (update tests for new mcp_gateway status logic)

**Goal:** B2 shipped with all 4 backend processes reporting `running=False`. B3.4 wires `mcp_gateway` to a real check: pidfile exists + process alive + health://gateway reachable.

**Interfaces:**
- Consumes: `BACKEND_PROCESSES["mcp_gateway"]` dict from `interfaces/cli/server.py`
- Produces: `mcp_gateway_status()` returning `{name, phase, description, running, pid, started_at, health_ok, version?}`

- [ ] **Step 1: Write the failing test for mcp_gateway_probe**

Create `interfaces/cli/tests/test_mcp_gateway_probe.py`:
```python
"""Tests for mcp_gateway_probe — real status check via pidfile + health probe."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def test_pidfile_alive_returns_running(tmp_path: Path) -> None:
    """When pidfile points to a live process (current PID), running=True."""
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway

    pidfile = tmp_path / "mcp_gateway.pid"
    pidfile.write_text(str(__import__("os").getpid()))  # current process is alive

    result = probe_mcp_gateway(pidfile_path=pidfile, probe_health=False)
    assert result["running"] is True
    assert result["pid"] == __import__("os").getpid()


def test_pidfile_stale_returns_not_running(tmp_path: Path) -> None:
    """When pidfile points to a dead PID (e.g. 99999), running=False."""
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway

    pidfile = tmp_path / "mcp_gateway.pid"
    pidfile.write_text("99999")  # unlikely to be alive

    result = probe_mcp_gateway(pidfile_path=pidfile, probe_health=False)
    assert result["running"] is False


def test_pidfile_missing_returns_not_running(tmp_path: Path) -> None:
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway
    result = probe_mcp_gateway(pidfile_path=tmp_path / "missing.pid", probe_health=False)
    assert result["running"] is False
    assert result["pid"] is None


def test_health_probe_success(tmp_path: Path, monkeypatch) -> None:
    """When health probe returns valid JSON with name=ikigai-gateway, health_ok=True."""
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway

    pidfile = tmp_path / "mcp_gateway.pid"
    pidfile.write_text(str(__import__("os").getpid()))

    def fake_health(uri: str, timeout_s: float = 1.0) -> dict:
        return {"name": "ikigai-gateway", "version": "1.0.0", "uptime_s": 5.0}

    monkeypatch.setattr(
        "interfaces.cli.mcp_gateway_probe.probe_health_resource",
        fake_health,
    )

    result = probe_mcp_gateway(pidfile_path=pidfile, probe_health=True)
    assert result["running"] is True
    assert result["health_ok"] is True
    assert result["version"] == "1.0.0"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd src/ikigai && poetry run pytest ../../interfaces/cli/tests/test_mcp_gateway_probe.py -v 2>&1 | tail -20
```

Expected: FAIL with `ModuleNotFoundError: No module named 'interfaces.cli.mcp_gateway_probe'`.

- [ ] **Step 3: Create mcp_gateway_probe.py**

Create `interfaces/cli/mcp_gateway_probe.py`:
```python
"""Probe MCP gateway status via pidfile + health://gateway resource.

Used by `life server status` to report real running state for the
`mcp_gateway` backend process (B3.4).

Logic:
  - If pidfile exists and PID is alive → process running
  - If pidfile exists but PID is dead → stale (running=False, error logged)
  - If pidfile missing → not started (running=False)

Optional health probe (probe_health=True) additionally queries health://gateway
resource via stdio subprocess call. Skipped if process not running.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _is_pid_alive(pid: int) -> bool:
    """Cross-platform check whether pid is a running process."""
    if pid <= 0:
        return False
    try:
        if os.name == "nt":  # Windows
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle == 0:
                return False
            try:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                return exit_code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        else:  # POSIX
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def probe_health_resource(timeout_s: float = 1.0) -> dict[str, Any]:
    """Probe health://gateway resource via stdio subprocess (best-effort).

    Spawns `python -m mcp_server` briefly, sends resources/read for
    health://gateway, captures first JSON response.

    Returns: parsed JSON dict, or {"error": "..."} on failure.
    """
    try:
        proc = subprocess.run(
            ["poetry", "run", "python", "-m", "mcp_server"],
            cwd=str(Path(__file__).parent.parent.parent / "src" / "ikigai"),
            input=json.dumps({
                "jsonrpc": "2.0",
                "id": "probe-001",
                "method": "resources/read",
                "params": {"uri": "health://gateway"},
            }) + "\n",
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return {"error": "no valid JSON response"}
    except subprocess.TimeoutExpired:
        return {"error": "probe timeout"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def probe_mcp_gateway(
    pidfile_path: Path,
    probe_health: bool = False,
) -> dict[str, Any]:
    """Probe mcp_gateway status.

    Args:
      pidfile_path: path to pidfile (e.g. data/run/mcp_gateway.pid)
      probe_health: whether to additionally probe health://gateway resource

    Returns:
      {running: bool, pid: int | None, started_at: str | None,
       health_ok: bool | None, version: str | None, error: str | None}
    """
    result: dict[str, Any] = {
        "running": False,
        "pid": None,
        "started_at": None,
        "health_ok": None,
        "version": None,
        "error": None,
    }

    if not pidfile_path.exists():
        result["error"] = "pidfile not found (gateway not started)"
        return result

    try:
        pid = int(pidfile_path.read_text().strip())
    except (ValueError, OSError) as e:
        result["error"] = f"pidfile unreadable: {e}"
        return result

    started_at = pidfile_path.stat().st_mtime
    result["started_at"] = str(started_at)

    if _is_pid_alive(pid):
        result["running"] = True
        result["pid"] = pid
    else:
        result["error"] = f"pid {pid} not alive (stale pidfile)"
        return result

    # Process alive — optionally probe health
    if probe_health:
        health = probe_health_resource()
        if "error" in health:
            result["health_ok"] = False
            result["error"] = health["error"]
        else:
            result["health_ok"] = health.get("name") == "ikigai-gateway"
            result["version"] = health.get("version")

    return result


__all__ = [
    "_is_pid_alive",
    "probe_health_resource",
    "probe_mcp_gateway",
]
```

- [ ] **Step 4: Wire probe into server.py**

In `interfaces/cli/server.py`:
1. Update `BACKEND_PROCESSES["mcp_gateway"]` to include `pidfile_path`:
```python
from pathlib import Path
MCP_GATEWAY_PIDFILE = Path(__file__).parent.parent.parent / "data" / "run" / "mcp_gateway.pid"

BACKEND_PROCESSES: dict[str, dict[str, Any]] = {
    # ... existing 3 ...
    "mcp_gateway": {
        "phase": "B3",
        "description": "13 tools + 5 resources MCP gateway (B3.1-B3.3)",
        "pidfile_path": MCP_GATEWAY_PIDFILE,
    },
}
```

2. Update `backend_status()` to use real probe for mcp_gateway:
```python
def backend_status() -> list[dict[str, Any]]:
    """Return status snapshot for all backend processes."""
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway

    rows = []
    for name, meta in BACKEND_PROCESSES.items():
        if name == "mcp_gateway":
            pidfile = meta.get("pidfile_path")
            if pidfile is None:
                running = False
                pid = None
                started_at = None
                error = "no pidfile configured"
            else:
                probe = probe_mcp_gateway(pidfile_path=pidfile, probe_health=False)
                running = probe["running"]
                pid = probe["pid"]
                started_at = probe["started_at"]
                error = probe["error"]
            rows.append({
                "name": name,
                "phase": meta["phase"],
                "description": meta["description"],
                "running": running,
                "pid": pid,
                "started_at": started_at,
                "error": error,
            })
        else:
            rows.append({
                "name": name,
                "phase": meta["phase"],
                "description": meta["description"],
                "running": False,
                "pid": None,
                "started_at": None,
            })
    return rows
```

- [ ] **Step 5: Update test_server.py for new mcp_gateway status logic**

In `interfaces/cli/tests/test_server.py`:

1. Update `test_backend_status_v1_all_report_not_running` to reflect new behavior:
```python
def test_backend_status_v1_review_queue_worker_not_running() -> None:
    """B2 stub: review_queue_worker reports running=false (real wiring in B4)."""
    snapshot = backend_status()
    row = next(r for r in snapshot if r["name"] == "review_queue_worker")
    assert row["running"] is False


def test_backend_status_mcp_gateway_uses_pidfile(tmp_path, monkeypatch) -> None:
    """mcp_gateway row reads real pidfile + reports running=True when PID alive."""
    from interfaces.cli import server as srv
    from interfaces.cli.mcp_gateway_probe import probe_mcp_gateway

    # Create a fake pidfile pointing to current process
    pidfile = tmp_path / "mcp_gateway.pid"
    pidfile.write_text(str(__import__("os").getpid()))

    # Monkey-patch MCP_GATEWAY_PIDFILE
    monkeypatch.setattr(srv, "MCP_GATEWAY_PIDFILE", pidfile)

    snapshot = backend_status()
    row = next(r for r in snapshot if r["name"] == "mcp_gateway")
    assert row["running"] is True
    assert row["pid"] == __import__("os").getpid()


def test_backend_status_mcp_gateway_no_pidfile() -> None:
    """mcp_gateway row reports running=False when pidfile missing."""
    snapshot = backend_status()
    row = next(r for r in snapshot if r["name"] == "mcp_gateway")
    assert row["running"] is False
    assert row["pid"] is None
    assert "pidfile" in (row.get("error") or "").lower() or row.get("error") is None
```

2. Update `test_backend_status_shape_is_stable`:
```python
def test_backend_status_shape_is_stable() -> None:
    """Each row has stable fields (added 'error' field for mcp_gateway detail)."""
    snapshot = backend_status()
    for row in snapshot:
        assert set(row.keys()) >= {"name", "phase", "description", "running", "pid", "started_at"}
        assert row["pid"] is None or isinstance(row["pid"], int)
        assert row["started_at"] is None or isinstance(row["started_at"], str)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd src/ikigai && poetry run pytest ../../interfaces/cli/tests/test_server.py ../../interfaces/cli/tests/test_mcp_gateway_probe.py -v 2>&1 | tail -40
```

Expected: all server tests (27 + 3 new) + all probe tests (4) passing.

- [ ] **Step 7: Run all interfaces/cli tests to confirm zero regression**

```bash
cd src/ikigai && poetry run pytest ../../interfaces/cli/tests/ -v 2>&1 | tail -30
```

Expected: all passing.

- [ ] **Step 8: Commit**

```bash
cd /c/Users/mathe/code_space/life-oss/life
git add interfaces/cli/mcp_gateway_probe.py \
        interfaces/cli/server.py \
        interfaces/cli/tests/test_mcp_gateway_probe.py \
        interfaces/cli/tests/test_server.py
git commit -m "feat(interfaces): wire mcp_gateway status to pidfile probe (B3.4)"
```

---

## Task 6: B3.5 — Add `make mcp-inspect` target

**Files:**
- Modify: `Makefile` (add `mcp-inspect` target)
- Create: `Makefile` (or modify existing) target that runs MCP Inspector

**Goal:** Provide a one-command contract test: `make mcp-inspect` spawns the gateway via stdio, lists tools + resources, exits 0.

**Interfaces:**
- Consumes: `npx @modelcontextprotocol/inspector` (auto-fetched)
- Produces: shell exit code (0 = pass, non-zero = fail)

- [ ] **Step 1: Add mcp-inspect target to Makefile**

In root `Makefile` (or create if missing), add:
```make
.PHONY: mcp-inspect
mcp-inspect: ## MCP Inspector contract test — enumerates tools + resources
	cd src/ikigai && poetry run python -m mcp_server &
	GATEWAY_PID=$$!
	sleep 2
	cd src/ikigai && npx --yes @modelcontextprotocol/inspector \
		--transport stdio \
		--command "poetry run python -m mcp_server" \
		--method tools/list \
		--method resources/list \
		--output json | jq -e '.tools | length >= 13 and .resources | length >= 5'
	kill $$GATEWAY_PID 2>/dev/null || true
	@echo "mcp-inspect: PASS"
```

**Notes for implementer:**
- The Makefile target is a starting point; the actual MCP Inspector CLI flags vary by version
- For Windows compatibility, the Bash command may need adjustment (`sleep`, `kill` syntax)
- Alternative: shell script `scripts/mcp-inspect.sh` if Makefile is hard to maintain cross-platform

- [ ] **Step 2: Document the target in CLAUDE.md**

Add to `CLAUDE.md` (project root), under "Build / Run / Test" section, after the IKIGAi block:
```markdown
### Phase B3 — MCP Gateway

```bash
make mcp-inspect              # MCP Inspector contract test (enumerates tools + resources)
```

- [ ] **Step 3: Smoke-test the target**

Run from repo root:
```bash
cd /c/Users/mathe/code_space/life-oss/life && make mcp-inspect 2>&1 | tail -30
```

Expected: `mcp-inspect: PASS` (or output showing ≥13 tools, ≥5 resources enumerated).

If MCP Inspector CLI flags don't match your npx version, document the discrepancy in your report and adjust the Makefile.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/mathe/code_space/life-oss/life
git add Makefile CLAUDE.md
git commit -m "build: add make mcp-inspect target for MCP Inspector contract test (B3.5)"
```

---

## Task 7: B3.6 — Add CI gate for MCP gateway contract test

**Files:**
- Modify: `.github/workflows/ci.yml` (add `mcp-gateway-contract` step)

**Goal:** CI runs `make mcp-inspect` on every PR; fails if gateway tools/resources are missing.

**Interfaces:**
- Consumes: existing CI workflow (after `pytest` step)
- Produces: green/red status on `mcp-gateway-contract` step

- [ ] **Step 1: Add CI step**

In `.github/workflows/ci.yml`, find the `test` job's `steps:` list. Add after the `pytest` step:
```yaml
      - name: MCP gateway contract test
        run: |
          cd src/ikigai
          poetry install --no-interaction
          poetry run pytest tests/ src/mesh/adapters/tests/ -v
      - name: MCP Inspector contract test
        run: |
          cd src/ikigai
          timeout 60 npx --yes @modelcontextprotocol/inspector \
            --transport stdio \
            --command "poetry run python -m mcp_server" \
            --method tools/list \
            --output json
```

(Adjust flags based on what worked in Task 6 smoke test.)

- [ ] **Step 2: Validate YAML syntax**

```bash
cd /c/Users/mathe/code_space/life-oss/life && python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
```

Expected: `YAML OK`.

- [ ] **Step 3: Commit**

```bash
cd /c/Users/mathe/code_space/life-oss/life
git add .github/workflows/ci.yml
git commit -m "ci: add MCP gateway contract test step (B3.6)"
```

---

## Task 8: B3.7 — Final verification + spec self-review

**Files:**
- Read: `docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md` (already amended in §11 R1-R4)
- Read: `docs/superpowers/plans/2026-08-28-phase-b3-mcp-gateway.md` (this plan)

**Goal:** Run final regression sweep, confirm all B3 acceptance criteria from research §9 are met.

- [ ] **Step 1: Run all tests**

From repo root:
```bash
cd src/ikigai && poetry run pytest tests/ src/mesh/adapters/tests/ ../../interfaces/cli/tests/ -v 2>&1 | tail -30
```

Expected: all passing. Record total count in your report.

- [ ] **Step 2: Run ruff + mypy**

```bash
cd src/ikigai && poetry run ruff check src/ tests/ 2>&1 | tail -20
cd src/ikigai && poetry run mypy src/ 2>&1 | tail -20
```

Expected: 0 errors (or only pre-existing ones).

- [ ] **Step 3: Spec coverage check**

Confirm each A2UI spec requirement maps to a task:
- §3.1-3.4 envelopes → unchanged in B3 (still JSON-RPC 2.0; spec §6.1 amended)
- §4.1 `mesh.read` → Task 3 (ikigai_mesh_show tool) + Task 4 (ueid:// resource)
- §4.2 `task.write` → Task 3 (ikigai_task_create tool)
- §4.3 `mesh.subscribe` → deferred to v1.1 (not blocking B3)
- §6.1 stdio transport → Task 2 (FastMCP run_async transport="stdio")
- §7 versioning → Ikigai-Version header in FastMCP init
- §8 security → stdio = process boundary trust (no HTTP yet)
- §11 R1-R4 → all documented in amended spec

- [ ] **Step 4: Acceptance criteria check (research §9)**

Confirm each criterion from research §9 is met:
- [ ] `server.py` refactored to FastMCP, gates B1-B2 e2e tests (Task 2)
- [ ] `make mcp-inspect` exits 0 (Task 6)
- [ ] `life server status --json` reports `mcp_gateway.running=true` when process alive (Task 5)
- [ ] MCP Inspector handshake shows capabilities (Task 2 — FastMCP auto-declares)
- [ ] CI step `mcp-gateway-contract` green (Task 7)
- [ ] Spec doc amended (already done in B3.0 — §11 R1-R4)
- [ ] Backwards-compat: 8 existing tools unchanged (Task 2 confirmed)

- [ ] **Step 5: No commit** (verification task)

---

## Task 9: B3.8 — Document phase completion + memory update

**Files:**
- Create: `memory/phase-b3-complete-2026-08-28.md`

**Goal:** Persist what was built, decisions made, and lessons learned to project memory.

- [ ] **Step 1: Write the phase memory**

Create `memory/phase-b3-complete-2026-08-28.md`:
```markdown
---
name: phase-b3-complete-2026-08-28
description: Phase B3 (MCP gateway consolidado) shipped — FastMCP refactor + 3 mesh tools + 5 resources + pidfile probe + CI gate
metadata:
  type: project
---

# Phase B3 — MCP Gateway Consolidado — Shipped 2026-08-28

## What shipped

- `src/ikigai/src/mcp_server/server.py` refactored from low-level `mcp.server.Server` to FastMCP decorator API
- `src/ikigai/src/mcp_server/tools_mesh.py` — 3 new tools (ikigai_mesh_show, ikigai_task_create, ikigai_health)
- `src/ikigai/src/mcp_server/resources.py` — 5 resources (ueid://, queue://pending, queue://events/{id}, health://gateway, plans://cycles[/{id}])
- `src/ikigai/src/mcp_server/server_v2.py` — zero-cost re-export shim
- `interfaces/cli/mcp_gateway_probe.py` — pidfile + health probe for `life server status`
- `interfaces/cli/server.py` — mcp_gateway row now reads real pidfile (was stub running=False)
- `Makefile` — `mcp-inspect` target for MCP Inspector contract test
- `.github/workflows/ci.yml` — CI gate for MCP gateway contract test
- `docs/superpowers/specs/2026-08-28-a2ui-protocol-design.md` §11 — Resolved Decisions R1-R4 (transport realization)
- `docs/superpowers/plans/2026-08-28-phase-b3-mcp-gateway.md` — implementation plan

## Decisions

- **Hybrid transport:** A2UI is logical spec; MCP stdio is canonical transport. UI authors read A2UI; wire is MCP.
- **FastMCP over low-level MCP:** auto-schemas from type hints; less boilerplate
- **stdio only v1:** no Streamable HTTP until v2 trigger (multi-process supervisor)
- **Prompts deferred to v1.1:** not on critical path; v1 ships tools + resources only

## Tests added

- `src/ikigai/tests/test_server_fastmcp.py` — 3 tests (FastMCP instance + 13 tools + main entrypoint)
- `src/ikigai/tests/test_tools_mesh.py` — 5 tests (mesh_show joins, task_create enqueues, health snapshot)
- `src/ikigai/tests/test_resources.py` — 7 tests (ueid, queue pending/event, health, plans)
- `interfaces/cli/tests/test_mcp_gateway_probe.py` — 4 tests (pidfile alive/stale/missing + health probe)

Total: 19 new tests; 0 regressions in B1+B2

## What's next (Phase B4)

- Review queue worker (`data/review_queue/` → agent consumer)
- Agent consumer (PAE: APPROVE/REJECT/CLARIFY) — already in `src/mesh/agent_consumer.py`
- Agent propagator (per-adapter failure isolation) — already in `src/mesh/agent_propagator.py`
- Wire all 3 into real supervisors (B4.1-B5.x)

## Related

- [[master-branch-carro-chefe-2026-08-28]] — IKIGAI as carro-chefe; B3 establishes the gateway it consumes
- [[doc-migration-2026-08-28]] — A2UI spec amended as part of registry tier-1 quick wins
- [[algorithm-decisions-defer-2026-08-28]] — algorithm polish deferred until empirical SONHO data
```

- [ ] **Step 2: Add pointer to MEMORY.md**

Append to `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/MEMORY.md`:
```markdown
- [Phase B3 MCP gateway complete](phase-b3-complete-2026-08-28.md) — FastMCP refactor + 3 mesh tools + 5 resources + pidfile probe + CI gate (2026-08-28)
```

- [ ] **Step 3: Commit**

```bash
cd /c/Users/mathe/code_space/life-oss/life
git add memory/phase-b3-complete-2026-08-28.md
git commit -m "docs(memory): persist Phase B3 completion"
```

---

## Acceptance Criteria (mapped from research §9)

| Criterion | Task |
|---|---|
| `server.py` refactored to FastMCP, gates B1-B2 e2e tests | Task 2 |
| 3 new mesh tools + 5 resources added | Tasks 3 + 4 |
| `make mcp-inspect` exits 0 | Task 6 |
| `life server status --json` reports `mcp_gateway.running=true` when process alive | Task 5 |
| MCP Inspector handshake shows capabilities | Task 2 (FastMCP auto-declares) |
| CI step `mcp-gateway-contract` green | Task 7 |
| Spec doc amended (§11 R1-R4) | done pre-B3 (amendment step) |
| Backwards-compat: 8 existing tools unchanged | Task 2 |

---

*Phase B3 plan complete. 9 tasks. ~3-4 hours of work via subagent-driven-development.*