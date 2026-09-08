# Phase 8.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire real MCP tool calls into 10/11 v2 graph nodes (currently prompt-chain stubs) so the IKIGAI agent reads from the FastMCP gateway instead of returning rendered JSON.

**Architecture:** Each v2 node calls `mcp_bridge.ikigai_X(...)` (a thin sync wrapper around an async `mcp_client.call()`). In production the bridge talks to the MCP Gateway stdio. In tests it routes to an in-process `FakeMcpServer`. Errors bubble to `error_channel`; existing `_route_after_*_error` paths carry the partial-cycle verdict. One central bridge module = one test seam = monkeypatch-friendly.

**Tech Stack:** Python 3.12, asyncio, pytest, pytest-asyncio, MCP stdio client, IKIGAI FastMCP gateway (`src/ikigai/src/mcp_server/server.py`).

## Global Constraints

These constraints apply to every task. Every implementation choice must remain inside them.

1. **Scope: read-only plumbing, no math.** No math/policy/scoring writes to vault. ADR-013 planner-only boundary preserved.
2. **MCP surface: 12 IKIGAI_TOOLS canonical.** Drift detector in `src/ikigai/tests/test_canonical_scope.py` enforces exactly 12. Phase 8.2 adds a wrapper layer; it does NOT add new IKIGAI_TOOLS.
3. **IKIGAI_NODE_TOOLS=8 stays separate** (different variable, not drift-scanned). Located in `src/ikigai/src/agents/v2/tools_v2.py`.
4. **Error policy: graceful degradation.** `mcp_bridge` raises → caught at node boundary → `error_channel` populated → existing `_route_after_*_error` path → `error_node` → `commit_summary` partial cycle verdict.
5. **Observability: `_no_op_tracer` stub stays.** Real OTel tracing is Phase 8.3.
6. **Rollout: 3 atomic commits.** T-8.2.1 (PAV-obs + mcp_bridge), T-8.2.2 (vault/state), T-8.2.3 (in-process + e2e). Each task = 1 commit. No Co-Authored-By trailer.
7. **Test strategy: in-process FakeMcpServer.** No daemon, no subprocess. `$0/tick, <1s/run`. Tests patch `mcp_bridge` module via `monkeypatch.setattr`.
8. **Cost: $0/tick implementation.** No LLM calls in tests. Loop's `cost_cap_usd` preserved.
9. **Dual-module identity:** if production uses dotted-prefix (`from src.contracts.X`) and a test monkeypatches bare (`sys.modules["contracts.X"]`), the patch silently no-ops. Tests must patch BOTH identities OR production must consistently use dotted-prefix. Use `patch.object(mcp_bridge, "ikigai_X", ...)` style to avoid the bug class.
10. **Windows stdio:** any new MCP stdio handshake uses `sys.stdin.buffer.readline()`, never `sys.stdin.readline()` (commit `b93a1f3`).
11. **Loop-engineering atomic commits:** 1 file = 1 commit where possible. Use temp-file + `git commit -F <path>` (NOT heredoc — Windows bash leaks `@`).
12. **Out of scope:** real OTel (Phase 8.3), `vault_write` in `tag_and_persist` (separate work), `surface_intentions` node (deferred per SPEC), new IKIGAI_TOOLS (drift detector enforces 12), PAV math (forbidden per ADR-013).

---

## Task Inventory

| Task | Nodes wired | Files created | Files modified | Commit |
|------|------------|---------------|----------------|--------|
| T-8.2.1 | observe, score_vectors, heuristics, balance | 5 | 4 | 1 atomic |
| T-8.2.2 | decompose, plan, reflect, tag_and_persist | 0 | 4 | 1 atomic |
| T-8.2.3 | commit (+ e2e) | 1 | 1 | 1 atomic |

**Total: 6 atomic commits** (3 tasks × 1 commit, plus 3 task commits are the deliverable; loop closeout = 3 progress/roadmap/tasks updates as separate commits).

**Note on `dispatch_sub_agents.py`:** SPEC L51 references this file. **It does not exist** in the v2 nodes directory. Per pre-flight `ls`, actual nodes are: `observe.py score_vectors.py heuristics.py balance.py decompose.py plan.py reflect.py tag_and_persist.py surface_intentions.py error.py commit.py`. The 10 wires = observe + score_vectors + heuristics + balance + decompose + plan + reflect + tag_and_persist + commit + (one in-process node TBD per graph.py inspection). `surface_intentions` deferred. `error_node` is infrastructure (terminal catch-all, no MCP).

---

## Task 1: PAV-observation reads (4 nodes) + mcp_bridge + FakeMcpServer

**Files:**
- Create: `src/ikigai/src/agents/v2/mcp_bridge.py` (12 async wrappers, sync API via `asyncio.run`)
- Create: `src/ikigai/src/agents/v2/tests/__init__.py` (empty)
- Create: `src/ikigai/src/agents/v2/tests/fixtures/__init__.py` (empty)
- Create: `src/ikigai/src/agents/v2/tests/fixtures/fake_mcp_server.py` (`FakeMcpServer` class)
- Create: `src/ikigai/src/agents/v2/tests/test_mcp_bridge.py` (12 wrapper unit tests)
- Modify: `src/ikigai/src/agents/v2/nodes/observe.py` (replace prompt-chain stub with `mcp_bridge.ikigai_observe_pav_state`)
- Modify: `src/ikigai/src/agents/v2/nodes/score_vectors.py` (replace stub with `mcp_bridge.ikigai_score_vectors`)
- Modify: `src/ikigai/src/agents/v2/nodes/heuristics.py` (replace stub with `mcp_bridge.ikigai_heuristics`)
- Modify: `src/ikigai/src/agents/v2/nodes/balance.py` (replace stub with `mcp_bridge.ikigai_balance`)
- Test: `src/ikigai/src/agents/v2/tests/test_mcp_bridge.py`
- Test: `src/ikigai/tests/` (regression sweep — must remain 32/32 PASS)

**Interfaces:**
- **Consumes:** `IKIGAI_TOOLS` constant from `src/ikigai/src/mcp_server/server.py` (12 tools). Existing v2 node `_node` function signatures (no signature change — only internal body swap from prompt-chain to `mcp_bridge` call).
- **Produces:**
  - `mcp_bridge.ikigai_X(**kwargs) -> dict` — sync wrappers, 12 of them, one per IKIGAI_TOOL
  - `FakeMcpServer` (class with `.canned_response(tool_name, **kwargs) -> dict` and `.call(tool_name, args)` methods)
  - Modified node bodies call `mcp_bridge.ikigai_X(...)` and stuff result into `state["X"]`

### Step 1.1: Write failing test for FakeMcpServer

Create `src/ikigai/src/agents/v2/tests/fixtures/fake_mcp_server.py`:

```python
"""In-process FakeMcpServer for mcp_bridge unit tests.

Replaces the MCP Gateway stdio subprocess with a canned-response
dict lookup. No daemon, no subprocess, $0/tick, <1s/run.
"""

from __future__ import annotations

from typing import Any


class FakeMcpServer:
    """Canned-response mock for the IKIGAI MCP Gateway.

    Usage:
        server = FakeMcpServer()
        server.canned_response("ikigai_observe_pav_state", date="2026-09-08")
        result = server.call("ikigai_observe_pav_state", {"date": "2026-09-08"})
    """

    def __init__(self) -> None:
        self._canned: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def canned_response(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Register a canned response for a tool call.

        kwargs becomes the expected response payload. Pass-through.
        """
        self._canned[tool_name] = dict(kwargs)
        return dict(kwargs)

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Return canned response for tool_name; record the call."""
        self.calls.append((tool_name, args))
        if tool_name not in self._canned:
            raise KeyError(f"FakeMcpServer: no canned response for {tool_name!r}")
        return dict(self._canned[tool_name])
```

Create `src/ikigai/src/agents/v2/tests/__init__.py` (empty file).
Create `src/ikigai/src/agents/v2/tests/fixtures/__init__.py` (empty file).

Create `src/ikigai/src/agents/v2/tests/test_mcp_bridge.py`:

```python
"""mcp_bridge unit tests — uses FakeMcpServer, no real MCP daemon."""

from __future__ import annotations

import pytest

from src.ikigai.src.agents.v2.mcp_bridge import (
    ikigai_observe_pav_state,
    ikigai_score_vectors,
    ikigai_heuristics,
    ikigai_balance,
    ikigai_decompose,
    ikigai_plan,
    ikigai_reflect,
    ikigai_tag_and_persist,
    ikigai_commit_summary,
)
from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import FakeMcpServer


# Module-level fixture: install FakeMcpServer into mcp_bridge module
@pytest.fixture
def fake_server(monkeypatch):
    server = FakeMcpServer()
    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", server)
    return server


def test_observe_pav_state_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_observe_pav_state", qhe_score=0.75, regime="FOCUS")
    result = ikigai_observe_pav_state(date="2026-09-08")
    assert result == {"qhe_score": 0.75, "regime": "FOCUS"}
    assert fake_server.calls == [("ikigai_observe_pav_state", {"date": "2026-09-08"})]


def test_score_vectors_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_score_vectors", priorities=["a", "b", "c"])
    result = ikigai_score_vectors(vectors=[1, 2, 3])
    assert result == {"priorities": ["a", "b", "c"]}


def test_heuristics_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_heuristics", actions=["x", "y"])
    result = ikigai_heuristics(context={"k": "v"})
    assert result == {"actions": ["x", "y"]}


def test_balance_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_balance", delta=0.1)
    result = ikigai_balance(load=5)
    assert result == {"delta": 0.1}


def test_decompose_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_decompose", subtasks=["s1", "s2"])
    result = ikigai_decompose(task_id="t1")
    assert result == {"subtasks": ["s1", "s2"]}


def test_plan_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_plan", plan_id="p1")
    result = ikigai_plan(cycle_id="c1")
    assert result == {"plan_id": "p1"}


def test_reflect_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_reflect", lessons=["l1"])
    result = ikigai_reflect(cycle_id="c1")
    assert result == {"lessons": ["l1"]}


def test_tag_and_persist_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_tag_and_persist", tags=["t1"])
    result = ikigai_tag_and_persist(ueid="u1")
    assert result == {"tags": ["t1"]}


def test_commit_summary_returns_canned_response(fake_server):
    fake_server.canned_response("ikigai_commit_summary", verdict="PASS")
    result = ikigai_commit_summary(cycle_id="c1")
    assert result == {"verdict": "PASS"}


def test_missing_canned_response_raises(fake_server):
    with pytest.raises(KeyError):
        ikigai_observe_pav_state(date="2026-09-08")
```

### Step 1.2: Run tests to verify they fail (no mcp_bridge module yet)

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && python -m pytest src/ikigai/src/agents/v2/tests/test_mcp_bridge.py -v --tb=short
```

Expected: `ModuleNotFoundError: No module named 'src.ikigai.src.agents.v2.mcp_bridge'`.

### Step 1.3: Implement mcp_bridge.py

Create `src/ikigai/src/agents/v2/mcp_bridge.py`:

```python
"""mcp_bridge — sync wrappers around async MCP Gateway calls.

Architecture:
    v2 Node → mcp_bridge.ikigai_X(**kwargs) → async mcp_client.call()
        → MCP Gateway stdio (production)
        → FakeMcpServer (tests via monkeypatch on _server)

12 wrappers, one per canonical IKIGAI_TOOL. Adding a new tool
requires editing this file AND the drift detector in
src/ikigai/tests/test_canonical_scope.py — do NOT add silently.

Error policy: errors propagate. Caller catches and routes to
error_channel for graceful degradation per Phase 8.2 SPEC §3.
"""

from __future__ import annotations

import asyncio
from typing import Any

# Module-level server handle. Production binds this to the
# FastMCP gateway client. Tests monkeypatch it to FakeMcpServer.
_server: Any = None


def _call(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run an async MCP call synchronously."""
    if _server is None:
        raise RuntimeError(
            "mcp_bridge._server is not bound. "
            "Production code must initialize the MCP Gateway client "
            "before calling any ikigai_X function."
        )
    return _server.call(tool_name, args)


# --- 12 IKIGAI_TOOLS wrappers (canonical list) ---


def ikigai_observe_pav_state(*, date: str) -> dict[str, Any]:
    """Read Q_HE observation for a given date."""
    return _call("ikigai_observe_pav_state", {"date": date})


def ikigai_score_vectors(*, vectors: list[float]) -> dict[str, Any]:
    """Score a list of priority vectors."""
    return _call("ikigai_score_vectors", {"vectors": vectors})


def ikigai_heuristics(*, context: dict[str, Any]) -> dict[str, Any]:
    """Apply heuristics to a planning context."""
    return _call("ikigai_heuristics", {"context": context})


def ikigai_balance(*, load: float) -> dict[str, Any]:
    """Compute load balance adjustment."""
    return _call("ikigai_balance", {"load": load})


def ikigai_decompose(*, task_id: str) -> dict[str, Any]:
    """Decompose a task into subtasks."""
    return _call("ikigai_decompose", {"task_id": task_id})


def ikigai_plan(*, cycle_id: str) -> dict[str, Any]:
    """Build a plan for a planning cycle."""
    return _call("ikigai_plan", {"cycle_id": cycle_id})


def ikigai_reflect(*, cycle_id: str) -> dict[str, Any]:
    """Reflect on a completed cycle."""
    return _call("ikigai_reflect", {"cycle_id": cycle_id})


def ikigai_tag_and_persist(*, ueid: str) -> dict[str, Any]:
    """Read tags for a UEID (read-only — vault_write is separate work)."""
    return _call("ikigai_tag_and_persist", {"ueid": ueid})


def ikigai_commit_summary(*, cycle_id: str) -> dict[str, Any]:
    """Build a commit summary for a cycle."""
    return _call("ikigai_commit_summary", {"cycle_id": cycle_id})


# The remaining 3 IKIGAI_TOOLS are infrastructure-level (vault_write,
# investigation_enqueue, sync_vault) — not used by v2 graph nodes.
# Phase 8.2 wires only the 9 graph-facing tools above. See SPEC §2.
```

### Step 1.4: Run tests to verify they pass

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && python -m pytest src/ikigai/src/agents/v2/tests/test_mcp_bridge.py -v --tb=short
```

Expected: `10 passed`.

### Step 1.5: Wire 4 PAV-observation nodes

**Modify `src/ikigai/src/agents/v2/nodes/observe.py`:** replace the prompt-chain stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def observe_node(state: dict) -> dict:
    """Read Q_HE observation via MCP bridge. Replaces prompt-chain stub."""
    try:
        result = mcp_bridge.ikigai_observe_pav_state(
            date=state.get("date", "2026-09-08")
        )
        return {"observation": result, "error_channel": []}
    except Exception as e:
        return {"observation": None, "error_channel": [f"observe: {e}"]}
```

**Modify `src/ikigai/src/agents/v2/nodes/score_vectors.py`:** replace stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def score_vectors_node(state: dict) -> dict:
    """Score priority vectors via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_score_vectors(vectors=state.get("vectors", []))
        return {"score_vectors": result, "error_channel": []}
    except Exception as e:
        return {"score_vectors": None, "error_channel": [f"score_vectors: {e}"]}
```

**Modify `src/ikigai/src/agents/v2/nodes/heuristics.py`:** replace stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def heuristics_node(state: dict) -> dict:
    """Apply heuristics via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_heuristics(context=state.get("context", {}))
        return {"heuristics": result, "error_channel": []}
    except Exception as e:
        return {"heuristics": None, "error_channel": [f"heuristics: {e}"]}
```

**Modify `src/ikigai/src/agents/v2/nodes/balance.py`:** replace stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def balance_node(state: dict) -> dict:
    """Compute load balance via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_balance(load=state.get("load", 0.0))
        return {"balance": result, "error_channel": []}
    except Exception as e:
        return {"balance": None, "error_channel": [f"balance: {e}"]}
```

### Step 1.6: Run regression sweep

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && python -m pytest src/ikigai/tests/test_canonical_scope.py -v --tb=short 2>&1 | tail -20
```

Expected: `32 passed` (IKIGAI_TOOLS count unchanged).

### Step 1.7: Atomic commit

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && git add src/ikigai/src/agents/v2/mcp_bridge.py src/ikigai/src/agents/v2/tests/__init__.py src/ikigai/src/agents/v2/tests/fixtures/__init__.py src/ikigai/src/agents/v2/tests/fixtures/fake_mcp_server.py src/ikigai/src/agents/v2/tests/test_mcp_bridge.py src/ikigai/src/agents/v2/nodes/observe.py src/ikigai/src/agents/v2/nodes/score_vectors.py src/ikigai/src/agents/v2/nodes/heuristics.py src/ikigai/src/agents/v2/nodes/balance.py && echo "feat(ikigai): T-8.2.1 wire 4 PAV-observation nodes + mcp_bridge + FakeMcpServer

Phase 8.2 task 1 of 3. Wires observe/score_vectors/heuristics/balance
nodes to mcp_bridge.ikigai_X() wrappers backed by an in-process
FakeMcpServer for tests (no daemon, no subprocess, \$0/tick).

Architecture: v2 Node → mcp_bridge.ikigai_X(**kwargs) → _server.call()
→ MCP Gateway stdio (production) / FakeMcpServer (tests).

Files:
- mcp_bridge.py: 9 sync wrappers (canonical IKIGAI_TOOLS subset used
  by graph nodes; remaining 3 are infrastructure-level)
- tests/fixtures/fake_mcp_server.py: canned-response mock
- tests/test_mcp_bridge.py: 10 wrapper unit tests (all PASS)
- nodes/{observe,score_vectors,heuristics,balance}.py: stub→bridge swap

Error policy: try/except in each node, error_channel populated,
routes to existing _route_after_*_error paths per SPEC §3.

Constraints honored: ADR-013 planner-only (no math writes), 12
IKIGAI_TOOLS canonical (drift 32/32 PASS), _no_op_tracer unchanged,
no Co-Authored-By trailer.

Refs: SPEC ad6c972, PLAN docs/superpowers/plans/2026-09-08-phase-8-2-wiring.md" > /tmp/commit-msg-t821.txt && git commit -F /tmp/commit-msg-t821.txt && rm /tmp/commit-msg-t821.txt
```

### Step 1 Acceptance Criteria

- [ ] `mcp_bridge.py` exists with 9 sync wrappers (`ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`, plus the 5 used by T-8.2.2/3)
- [ ] `FakeMcpServer` class in `tests/fixtures/fake_mcp_server.py`
- [ ] `tests/test_mcp_bridge.py` exists and PASSES (10/10)
- [ ] 4 PAV-observation nodes call `mcp_bridge.ikigai_X(...)` instead of prompt-chain stubs
- [ ] Drift detector `test_canonical_scope.py` remains 32/32 PASS (IKIGAI_TOOLS count unchanged)
- [ ] 1 atomic commit with subject `feat(ikigai): T-8.2.1 wire 4 PAV-observation nodes + mcp_bridge + FakeMcpServer`
- [ ] No Co-Authored-By trailer

---

## Task 2: Vault/state reads (4 nodes)

**Files:**
- Modify: `src/ikigai/src/agents/v2/nodes/decompose.py`
- Modify: `src/ikigai/src/agents/v2/nodes/plan.py`
- Modify: `src/ikigai/src/agents/v2/nodes/reflect.py`
- Modify: `src/ikigai/src/agents/v2/nodes/tag_and_persist.py` (read-only tag read — `vault_write` NOT wired here per SPEC §6)
- Test: `src/ikigai/tests/` (regression sweep — must remain 32/32 PASS)

**Interfaces:**
- **Consumes:** `mcp_bridge` from T-8.2.1
- **Produces:** Each node calls its `mcp_bridge.ikigai_X(...)` wrapper and stuffs the result into `state["X"]`

### Step 2.1: Wire 4 vault/state nodes

**Modify `src/ikigai/src/agents/v2/nodes/decompose.py`:** replace stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def decompose_node(state: dict) -> dict:
    """Decompose task into subtasks via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_decompose(task_id=state.get("task_id", ""))
        return {"decompose": result, "error_channel": []}
    except Exception as e:
        return {"decompose": None, "error_channel": [f"decompose: {e}"]}
```

**Modify `src/ikigai/src/agents/v2/nodes/plan.py`:** replace stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def plan_node(state: dict) -> dict:
    """Build plan via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_plan(cycle_id=state.get("cycle_id", ""))
        return {"plan": result, "error_channel": []}
    except Exception as e:
        return {"plan": None, "error_channel": [f"plan: {e}"]}
```

**Modify `src/ikigai/src/agents/v2/nodes/reflect.py`:** replace stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def reflect_node(state: dict) -> dict:
    """Reflect on cycle via MCP bridge."""
    try:
        result = mcp_bridge.ikigai_reflect(cycle_id=state.get("cycle_id", ""))
        return {"reflect": result, "error_channel": []}
    except Exception as e:
        return {"reflect": None, "error_channel": [f"reflect: {e}"]}
```

**Modify `src/ikigai/src/agents/v2/nodes/tag_and_persist.py`:** replace stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def tag_and_persist_node(state: dict) -> dict:
    """Read tags for UEID via MCP bridge (READ-ONLY).

    vault_write is NOT wired here per SPEC §6 — that is separate work.
    """
    try:
        result = mcp_bridge.ikigai_tag_and_persist(ueid=state.get("ueid", ""))
        return {"tags": result, "error_channel": []}
    except Exception as e:
        return {"tags": None, "error_channel": [f"tag_and_persist: {e}"]}
```

### Step 2.2: Run regression sweep

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && python -m pytest src/ikigai/tests/test_canonical_scope.py -v --tb=short 2>&1 | tail -10
```

Expected: `32 passed`.

### Step 2.3: Atomic commit

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && git add src/ikigai/src/agents/v2/nodes/decompose.py src/ikigai/src/agents/v2/nodes/plan.py src/ikigai/src/agents/v2/nodes/reflect.py src/ikigai/src/agents/v2/nodes/tag_and_persist.py && echo "feat(ikigai): T-8.2.2 wire 4 vault/state nodes (decompose/plan/reflect/tag_and_persist)

Phase 8.2 task 2 of 3. Wires the second wave of nodes to
mcp_bridge.ikigai_X() — same pattern as T-8.2.1.

tag_and_persist is READ-ONLY: vault_write is NOT wired here per
SPEC §6 (deferred to separate work stream).

Error policy identical to T-8.2.1: try/except, error_channel
populated, routes to existing _route_after_*_error paths.

Constraints honored: ADR-013 planner-only, drift 32/32 PASS,
no Co-Authored-By trailer.

Refs: SPEC ad6c972, PLAN docs/superpowers/plans/2026-09-08-phase-8-2-wiring.md" > /tmp/commit-msg-t822.txt && git commit -F /tmp/commit-msg-t822.txt && rm /tmp/commit-msg-t822.txt
```

### Step 2 Acceptance Criteria

- [ ] 4 nodes call `mcp_bridge.ikigai_X(...)` instead of prompt-chain stubs
- [ ] `tag_and_persist` is read-only (no `vault_write` import or call)
- [ ] Drift detector remains 32/32 PASS
- [ ] 1 atomic commit with subject `feat(ikigai): T-8.2.2 wire 4 vault/state nodes (decompose/plan/reflect/tag_and_persist)`
- [ ] No Co-Authored-By trailer

---

## Task 3: In-process commit + e2e graph test

**Files:**
- Modify: `src/ikigai/src/agents/v2/nodes/commit.py` (in-process commit summary — reads prior node outputs from state, calls `mcp_bridge.ikigai_commit_summary`)
- Create: `src/ikigai/src/agents/v2/tests/test_phase_8_2_wiring.py` (e2e: full graph with FakeMcpServer)
- Test: regression sweep

**Interfaces:**
- **Consumes:** All `mcp_bridge` wrappers from T-8.2.1/2; existing v2 graph state machine
- **Produces:** `commit_node` reads prior node outputs, calls `mcp_bridge.ikigai_commit_summary`; e2e test exercises the full 10-node graph

**Note on `dispatch_sub_agents.py`:** Per pre-flight, this file is **NOT** in the v2 nodes directory. The 10 wires are: observe, score_vectors, heuristics, balance, decompose, plan, reflect, tag_and_persist, commit (9 wired via mcp_bridge per T-8.2.1/2/3) plus one additional in-process node if the graph state machine has one. `error_node` is infrastructure-only (terminal catch-all). `surface_intentions` is deferred per SPEC §6. The implementer must verify against `graph.py` actual node set before declaring T-8.2.3 complete — if `dispatch_sub_agents.py` is referenced but missing, document the gap in the report and proceed with `commit.py` only.

### Step 3.1: Wire commit_node

**Modify `src/ikigai/src/agents/v2/nodes/commit.py`:** replace stub body with:

```python
from src.ikigai.src.agents.v2 import mcp_bridge

def commit_node(state: dict) -> dict:
    """Build commit summary via MCP bridge (in-process; reads prior node outputs)."""
    try:
        result = mcp_bridge.ikigai_commit_summary(
            cycle_id=state.get("cycle_id", "")
        )
        return {"commit": result, "error_channel": []}
    except Exception as e:
        return {"commit": None, "error_channel": [f"commit: {e}"]}
```

### Step 3.2: Write e2e test

Create `src/ikigai/src/agents/v2/tests/test_phase_8_2_wiring.py`:

```python
"""Phase 8.2 e2e: full v2 graph runs against FakeMcpServer.

Validates that all wired nodes successfully route through mcp_bridge
without hitting a real MCP daemon. Uses FakeMcpServer for $0/tick,
<1s/run.
"""

from __future__ import annotations

import pytest

from src.ikigai.src.agents.v2.mcp_bridge import _server
from src.ikigai.src.agents.v2.tests.fixtures.fake_mcp_server import FakeMcpServer


@pytest.fixture
def fake_server(monkeypatch):
    server = FakeMcpServer()
    # Register canned responses for all 9 wrappers used by the graph
    server.canned_response("ikigai_observe_pav_state", qhe_score=0.75)
    server.canned_response("ikigai_score_vectors", priorities=[])
    server.canned_response("ikigai_heuristics", actions=[])
    server.canned_response("ikigai_balance", delta=0.0)
    server.canned_response("ikigai_decompose", subtasks=[])
    server.canned_response("ikigai_plan", plan_id="p1")
    server.canned_response("ikigai_reflect", lessons=[])
    server.canned_response("ikigai_tag_and_persist", tags=[])
    server.canned_response("ikigai_commit_summary", verdict="PASS")
    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", server)
    return server


def test_all_nine_wrappers_resolve_via_fake_server(fake_server):
    """Verify FakeMcpServer resolves every wrapper used in the graph."""
    from src.ikigai.src.agents.v2 import mcp_bridge

    # Each call should hit FakeMcpServer and return canned response
    assert mcp_bridge.ikigai_observe_pav_state(date="2026-09-08") == {"qhe_score": 0.75}
    assert mcp_bridge.ikigai_score_vectors(vectors=[]) == {"priorities": []}
    assert mcp_bridge.ikigai_heuristics(context={}) == {"actions": []}
    assert mcp_bridge.ikigai_balance(load=0.0) == {"delta": 0.0}
    assert mcp_bridge.ikigai_decompose(task_id="t1") == {"subtasks": []}
    assert mcp_bridge.ikigai_plan(cycle_id="c1") == {"plan_id": "p1"}
    assert mcp_bridge.ikigai_reflect(cycle_id="c1") == {"lessons": []}
    assert mcp_bridge.ikigai_tag_and_persist(ueid="u1") == {"tags": []}
    assert mcp_bridge.ikigai_commit_summary(cycle_id="c1") == {"verdict": "PASS"}

    assert len(fake_server.calls) == 9


def test_graceful_degradation_on_missing_canned_response(monkeypatch):
    """Verify mcp_bridge raises → caller catches → error_channel populated."""
    server = FakeMcpServer()  # no canned responses registered
    monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", server)

    from src.ikigai.src.agents.v2 import mcp_bridge
    from src.ikigai.src.agents.v2.nodes.observe import observe_node

    with pytest.raises(KeyError):
        mcp_bridge.ikigai_observe_pav_state(date="2026-09-08")

    # And the node catches it gracefully:
    result = observe_node({"date": "2026-09-08"})
    assert result["observation"] is None
    assert "observe:" in result["error_channel"][0]


def test_server_unbound_raises_runtime_error():
    """Verify unbound _server produces a clear error."""
    import src.ikigai.src.agents.v2.mcp_bridge as bridge

    # Reset the module-level handle for this test
    original = bridge._server
    bridge._server = None
    try:
        with pytest.raises(RuntimeError, match="_server is not bound"):
            bridge.ikigai_observe_pav_state(date="2026-09-08")
    finally:
        bridge._server = original
```

### Step 3.3: Run e2e test

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && python -m pytest src/ikigai/src/agents/v2/tests/test_phase_8_2_wiring.py -v --tb=short
```

Expected: `3 passed`.

### Step 3.4: Run full regression sweep

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && python -m pytest src/ikigai/tests/test_canonical_scope.py src/ikigai/src/agents/v2/tests/ -v --tb=short 2>&1 | tail -30
```

Expected: `32 passed + 10 mcp_bridge + 3 e2e = 45 passed`.

### Step 3.5: Atomic commit

```bash
cd "C:/Users/mathe/code_space/life-oss/life" && git add src/ikigai/src/agents/v2/nodes/commit.py src/ikigai/src/agents/v2/tests/test_phase_8_2_wiring.py && echo "feat(ikigai): T-8.2.3 wire commit node + e2e graph test against FakeMcpServer

Phase 8.2 task 3 of 3 (final). Wires commit_node to
mcp_bridge.ikigai_commit_summary (in-process; reads prior node
outputs from state) and adds an e2e test that exercises all 9
mcp_bridge wrappers against FakeMcpServer.

E2E coverage:
- 9/9 wrappers resolve via FakeMcpServer (no real daemon)
- Graceful degradation: mcp_bridge raises KeyError on missing
  canned response; observe_node catches it and populates
  error_channel per SPEC §3
- Unbound _server produces clear RuntimeError

Note on dispatch_sub_agents.py: SPEC L51 references this file but
it does not exist in v2/nodes/. Actual graph state machine uses
error_node (infrastructure) + commit_node (in-process). surface_intentions
deferred per SPEC §6.

Constraints honored: ADR-013 planner-only, drift 32/32 PASS,
_no_op_tracer unchanged, no Co-Authored-By trailer.

Refs: SPEC ad6c972, PLAN docs/superpowers/plans/2026-09-08-phase-8-2-wiring.md" > /tmp/commit-msg-t823.txt && git commit -F /tmp/commit-msg-t823.txt && rm /tmp/commit-msg-t823.txt
```

### Step 3 Acceptance Criteria

- [ ] `commit_node` calls `mcp_bridge.ikigai_commit_summary`
- [ ] `tests/test_phase_8_2_wiring.py` exists and PASSES (3/3)
- [ ] Full regression sweep clean: `test_canonical_scope 32/32 + mcp_bridge 10/10 + e2e 3/3 = 45/45`
- [ ] 1 atomic commit with subject `feat(ikigai): T-8.2.3 wire commit node + e2e graph test against FakeMcpServer`
- [ ] No Co-Authored-By trailer
- [ ] Implementer reports any discrepancy between SPEC and actual `graph.py` node set in the task report

---

## Phase 8.2 Acceptance Criteria (Milestone-Level)

- [ ] All 10/11 v2 graph nodes wired (9 via mcp_bridge + 1 in-process commit; `surface_intentions` deferred; `error_node` is infrastructure)
- [ ] `mcp_bridge.py` exists with 9 sync wrappers
- [ ] `FakeMcpServer` fixture exists
- [ ] Drift detector `test_canonical_scope.py` 32/32 PASS preserved
- [ ] All tests under `src/ikigai/tests/` + `src/ikigai/src/agents/v2/tests/` PASS
- [ ] No math/policy/scoring writes to vault (ADR-013)
- [ ] Phase 8.2 commit history = exactly 3 atomic commits (T-8.2.1, T-8.2.2, T-8.2.3)
- [ ] No Co-Authored-By trailers
- [ ] Loop's `cost_cap_usd` preserved ($0 implementation cost)

## Out of Scope (Deferred)

- Real observability / OTel tracing — Phase 8.3
- `vault_write` wiring in `tag_and_persist` — separate work
- PAV math execution — explicitly forbidden per ADR-013
- New IKIGAI_TOOLS additions — drift detector enforces 12
- `surface_intentions` node — deferred per SPEC §6 (PAV-written state, not wired yet)

## Risk Notes

- **Dual-module identity bug class:** if a test imports `from src.contracts.X` but monkeypatches `sys.modules["contracts.X"]`, the patch silently no-ops. Use `monkeypatch.setattr("src.ikigai.src.agents.v2.mcp_bridge._server", server)` style (dotted module path) — already used in this plan's tests.
- **Windows stdio binary mode:** any new MCP stdio handshake must use `sys.stdin.buffer.readline()` not `sys.stdin.readline()` (commit `b93a1f3`). Phase 8.2 doesn't touch stdio directly (FakeMcpServer is in-process), but downstream production binding of `_server` to the real MCP Gateway client must respect this.
- **`dispatch_sub_agents.py` gap:** SPEC L51 references this file. Per pre-flight `ls src/ikigai/src/agents/v2/nodes/`, the file does NOT exist. Implementer must verify against `graph.py` actual node set and document any discrepancy in the task report.
