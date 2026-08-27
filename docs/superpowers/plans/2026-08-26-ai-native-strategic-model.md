# AI-Native Strategic Model — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete PAV UI, build ikigai_maintainer deepagent with MCP tool contracts, establish AI-native architecture where external apps consume contracts from this workspace.

**Architecture:** Workspace becomes contract + agentic systems only. No bespoke UI. MCP tools expose IKIGAi, PAE-Maintainer, UPI, tuiboard, and taskdog interfaces to AI agents via mcp-gateway. deepagents is the LangGraph harness.

**Tech Stack:** Python (ikigai_maintainer), Rust (solverforge-calendar-mcp), TypeScript (tuiboard), deepagents (LangGraph), MCP (stdio + HTTP+SSE), SQLite + Markdown vault

## Global Constraints

- Markdown vault is canonical SoT — markdown wins on drift
- Append-only on plan_entities (SQLite trigger)
- Zero LLM in hot path — pure arithmetic only
- Pydantic v2 strict on all new schemas (`frozen=True`, `extra="forbid"`)
- UEID format: `<namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>`
- MCP dual transport: stdio (Claude Code) + HTTP+SSE (deepagents)
- IKIGAi 5 vectors: passion, skill, market, revenue, course
- IKIGAi 6 heuristics: H1 (regime FSM), H2 (phase FSM), H3 (UCB weight recalibration), H4 (opportunity fit), H5 (skill velocity), H6 (task priority)

---

## Task Decomposition

### Task 1: Delete PAV UI — `life-ops/operational/apps/`

**Files:**
- Delete: `life-ops/operational/apps/` (entire directory — cli + tui)
- Modify: `life-ops/operational/pyproject.toml` (remove `apps/` from workspace members)
- Modify: `life-ops/operational/CLAUDE.md` (remove PAV commands)
- Modify: `.github/workflows/ci.yml` (remove PAV test steps)

**Steps:**

- [ ] **Step 1: Verify `apps/` contents before deletion**

Run: `ls life-ops/operational/apps/`
Expected: `cli/` and `tui/` directories listed

- [ ] **Step 2: Delete `apps/` directory**

```bash
rm -rf life-ops/operational/apps/
```

- [ ] **Step 3: Update `pyproject.toml` workspace members**

Remove `apps/` entry from `members` or `packages` list in `life-ops/operational/pyproject.toml`

Run: `grep -n "apps" life-ops/operational/pyproject.toml`
Expected: No matches for `apps/` path

- [ ] **Step 4: Update `life-ops/operational/CLAUDE.md`**

Remove all `pav tui`, `pav home`, `pav doctor`, `pav demo seed`, and `pav --help` commands from the CLAUDE.md. Keep `packages/core/` references.

Run: `grep -n "pav" life-ops/operational/CLAUDE.md`
Expected: No matches

- [ ] **Step 5: Update CI workflow**

Remove PAV test steps from `.github/workflows/ci.yml`:
- Remove `pav tui` test steps
- Remove `pav doctor` from health checks
- Keep `ruff check`, `ruff format`, `mypy src/`, `pytest` for `packages/core/`

Run: `grep -n "pav\|tui\|operational" .github/workflows/ci.yml`
Expected: Only `packages/core/src/operational/` remains

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: delete PAV UI — workspace is now contract + agentic systems only"
```

---

### Task 2: Create `ikigai_maintainer` directory structure

**Files:**
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/__init__.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/state.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/__init__.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/observe.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/plan.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/reflect.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/balance.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/score_vectors.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/heuristics.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/decompose.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/commit.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/graph.py`
- Create: `life-ops/ikigai/pyproject.toml`

**IKIGAiStateDict (TypedDict):**

```python
class IKIGAiStateDict(TypedDict, total=False):
    cycle_id: str
    cycle_start: str
    cycle_end: str
    iteration: int
    last_step: str

    regime_state: Literal["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]
    q_he_score: float
    days_in_regime: int
    is_hysteresis_active: bool

    phase: Literal["FUNDAÇÃO", "BUSCA", "HACKATHON", "RECUPERACAO", "OVERCLOCK"]
    phase_iteration: int
    phase_converged: bool
    phase_weights: dict[str, float]

    vector_scores: dict[str, float]
    meta_vector_score: float

    active_dream_ueid: str | None
    active_goal_ueids: list[str]
    active_objective_ueids: list[str]
    active_project_ueids: list[str]
    active_task_ueids: list[str]

    workload_estimate: float
    capacity_estimate: float
    balancer_verdict: Literal["OK", "OVERLOAD", "UNDERLOAD", "RECOVER"]

    prospective_buffer: Annotated[list[str], operator.add]
    retrospective_log: Annotated[list[str], operator.add]

    corrections: Annotated[list[dict], operator.add]
    kill_switch_triggered: bool
    terminated: bool
```

**Steps:**

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p life-ops/ikigai/src/agents/ikigai_maintainer/nodes
touch life-ops/ikigai/src/agents/ikigai_maintainer/__init__.py
touch life-ops/ikigai/src/agents/ikigai_maintainer/nodes/__init__.py
```

- [ ] **Step 2: Write `state.py`**

Create `IKIGAiStateDict`, `CorrectionSignal` Pydantic model, and `TIER_DAYS` constant.

Run: `python -c "from life_ops.ikigai.src.agents.ikigai_maintainer.state import IKIGAiStateDict; print('OK')"`
Expected: `OK` (imports cleanly)

- [ ] **Step 3: Write `nodes/observe.py`**

Reads Q_HE from `operational/core/policy_engine.py` and UPI state from `solverforge-calendar-mcp`. Returns dict with `q_he_score`, `workload_estimate`, `capacity_estimate`.

- [ ] **Step 4: Write `nodes/plan.py` and `nodes/reflect.py`**

Prospective and retrospective channels. Use `Annotated[list[str], operator.add]` for accumulation.

- [ ] **Step 5: Write `nodes/balance.py`**

Implements hysteresis-aware workload balancer. Threshold constants imported from `operational.constants`.

- [ ] **Step 6: Write `nodes/score_vectors.py`**

Implements IKIGAi 5-vector scoring (H4 + H5 from SPEC). Returns `vector_scores` dict + `meta_vector_score`.

- [ ] **Step 7: Write `nodes/heuristics.py`**

Implements H1-H6 deterministic algorithms. Returns `corrections` list + updates `regime_state`, `phase`.

- [ ] **Step 8: Write `nodes/decompose.py`**

Traverses UEID hierarchy (Dream→Goal→Objective→Project→Task). Reads from markdown vault or SQLite.

- [ ] **Step 9: Write `nodes/commit.py`**

Checkpoint to SQLite (via `SqliteSaver`). Triggers `ikigai_sync_vault` reconciliation. Guarded by `balancer_verdict`.

- [ ] **Step 10: Write `graph.py`**

Factory: `make_ikigai_graph()` — builds StateGraph with all 8 nodes, conditional edges for regime FSM routing and balancer guard.

```python
from langgraph.graph import END, START, StateGraph

def make_ikigai_graph() -> StateGraph:
    g: StateGraph[IKIGAiStateDict] = StateGraph(IKIGAiStateDict)
    g.add_node("observe", observe_node)
    g.add_node("plan", plan_node)
    g.add_node("reflect", reflect_node)
    g.add_node("balance", balance_node)
    g.add_node("score_vectors", score_vectors_node)
    g.add_node("apply_heuristics", heuristics_node)
    g.add_node("decompose", decompose_node)
    g.add_node("commit", commit_node)
    g.add_edge(START, "observe")
    g.add_edge("observe", "plan")
    g.add_edge("observe", "reflect")
    g.add_edge("plan", "balance")
    g.add_edge("reflect", "balance")
    g.add_edge("balance", "score_vectors")
    g.add_edge("score_vectors", "apply_heuristics")
    g.add_edge("apply_heuristics", "decompose")
    g.add_edge("decompose", "commit")
    g.add_edge("commit", END)
    return g
```

- [ ] **Step 11: Add `pyproject.toml` for `ikigai_maintainer`**

Add as a Python package under `life-ops/ikigai/`. Depends on: `pydantic`, `sqlalchemy`, `python-dateutil`, `operational` (the `packages/core/` workspace).

Run: `cd life-ops/ikigai && uv sync`
Expected: No import errors

- [ ] **Step 12: Commit**

```bash
git add life-ops/ikigai/src/agents/ikigai_maintainer/
git add life-ops/ikigai/pyproject.toml
git commit -m "feat(ikigai): ikigai_maintainer core — 8 nodes + IKIGAiStateDict"
```

---

### Task 3: Add `SqliteSaver` checkpointing to `ikigai_maintainer`

**Files:**
- Modify: `life-ops/ikigai/src/agents/ikigai_maintainer/graph.py`

**Steps:**

- [ ] **Step 1: Add checkpointing to `make_ikigai_graph`**

```python
from langgraph.checkpoint.sqlite import SqliteSaver

CHECKPOINT_DB = Path.home() / ".ikigai" / "checkpoints" / "ikigai.db"
CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)

def make_ikigai_graph() -> CompiledStateGraph:
    g = StateGraph(IKIGAiStateDict)
    # ... add nodes and edges ...
    checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{CHECKPOINT_DB}")
    return g.compile(checkpointer=checkpointer)
```

- [ ] **Step 2: Add `checkpoint()` function**

```python
def checkpoint(state: IKIGAiStateDict, thread_id: str = "default") -> None:
    """Persist current state to SQLite checkpoint."""
    app = make_ikigai_graph()
    app.update_state({"configurable": {"thread_id": thread_id}}, state)
```

- [ ] **Step 3: Test checkpoint round-trip**

```python
def test_checkpoint_roundtrip():
    from ikigai_maintainer.graph import make_ikigai_graph
    app = make_ikigai_graph()
    initial = {"cycle_id": "test", "iteration": 0, ...}
    app.update_state({"configurable": {"thread_id": "test"}}, initial)
    loaded = app.get_state({"configurable": {"thread_id": "test"}})
    assert loaded["values"]["cycle_id"] == "test"
```

Run: `cd life-ops/ikigai && uv run pytest tests/ -v -k "checkpoint"`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(ikigai): add SqliteSaver checkpointing to ikigai_maintainer"
```

---

### Task 4: Build `ikigai_maintainer-mcp` — MCP server with 8 tools

**Files:**
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer_mcp/__init__.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer_mcp/server.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer_mcp/tools.py`
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer_mcp/bin/ikigai_maintainer-mcp.py` (entry point)
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer_mcp/pyproject.toml`

**MCP Tools:**

| Tool | Input | Output |
|------|-------|--------|
| `ikigai_score` | `{}` | `{vector_scores: dict, meta_vector_score: float}` |
| `ikigai_regime` | `{}` | `{regime_state, days_in_regime, severity}` |
| `ikigai_phase` | `{}` | `{phase, phase_weights, phase_iteration}` |
| `ikigai_decompose` | `{dream_ueid: str}` | `{ueid_tree: dict}` |
| `ikigai_corrections` | `{}` | `{corrections: list[dict]}` |
| `ikigai_plan_cycle` | `{input?: dict}` | `{cycle_result: dict}` |
| `ikigai_checkpoint` | `{}` | `{success: bool}` |
| `ikigai_sync_vault` | `{}` | `{sync_result: dict}` |

**Steps:**

- [ ] **Step 1: Write `tools.py`**

Each tool is a function that calls into `ikigai_maintainer` state/graph. Use FastMCP or the Python MCP SDK.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ikigai_maintainer")

@mcp.tool()
def ikigai_score() -> dict:
    """Returns 5 IKIGAi vector scores + meta-vector."""
    from ikigai_maintainer.graph import make_ikigai_graph
    app = make_ikigai_graph()
    state = app.get_state({"configurable": {"thread_id": "default"}})
    return {
        "vector_scores": state["values"].get("vector_scores", {}),
        "meta_vector_score": state["values"].get("meta_vector_score", 0.0),
    }
```

- [ ] **Step 2: Write `server.py`**

Bootstraps the FastMCP server, registers all 8 tools, sets up dual transport.

- [ ] **Step 3: Write entry point `bin/ikigai_maintainer-mcp.py`**

```python
#!/usr/bin/env python
"""ikigai_maintainer MCP server entry point."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ikigai_maintainer_mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

- [ ] **Step 4: Add to `gateways.yaml`**

Add `ikigai_` prefix to mcp-gateway routing:

```yaml
  - name: ikigai_maintainer
    command: ["python", "-m", "ikigai_maintainer_mcp.bin.ikigai_maintainer-mcp"]
    cwd: "C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai"
    tool_prefixes:
      - "ikigai_"
```

- [ ] **Step 5: Verify server starts without crash**

```bash
cd life-ops/ikigai && echo '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | timeout 5 python -m ikigai_maintainer_mcp.bin.ikigai_maintainer-mcp
```

Expected: JSON-RPC response with `protocolVersion`

- [ ] **Step 6: Commit**

```bash
git add life-ops/ikigai/src/agents/ikigai_maintainer_mcp/
git commit -m "feat(ikigai): ikigai_maintainer MCP server — 8 tools exposed"
```

---

### Task 5: Deep Agents Harness — integrate with `deepagents`

**Files:**
- Create: `life-ops/ikigai/src/agents/ikigai_maintainer/deepagents_harness.py`
- Modify: `life-ops/ikigai/pyproject.toml` (add `deepagents` dependency)

**Steps:**

- [ ] **Step 1: Add `deepagents` dependency**

```bash
cd life-ops/ikigai && uv add deepagents langgraph
```

- [ ] **Step 2: Write `deepagents_harness.py`**

```python
"""Deep agents harness for IKIGAi-Maintainer.

Wraps ikigai_maintainer StateGraph as a deepagent using deepagents.create_deep_agent.
"""
from pathlib import Path
from deepagents import create_deep_agent
from ikigai_maintainer.graph import make_ikigai_graph
from ikigai_maintainer_mcp.tools import (
    ikigai_score, ikigai_regime, ikigai_phase,
    ikigai_decompose, ikigai_corrections,
    ikigai_plan_cycle, ikigai_checkpoint, ikigai_sync_vault,
)

CHECKPOINT_DIR = Path.home() / ".ikigai" / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

IKIGAI_SYSTEM_PROMPT = """You are the IKIGAi meta-brain.

You operate the IKIGAi-Maintainer dual-channel planning system:
- 5 vectors: passion, skill, market, revenue, course
- 6 deterministic heuristics: H1 (regime FSM), H2 (phase FSM), H3 (UCB weights),
  H4 (opportunity fit), H5 (skill velocity), H6 (task priority)
- 4-state regime FSM: PUSH / MAINTAIN / REDUCE / RECOVER
- 5-phase FSM: FUNDAÇÃO / BUSCA / HACKATHON / RECUPERACAO / OVERCLOCK

Use the ikigai_* tools to inspect state and trigger cycles.
Always checkpoint after mutations.
Markdown vault is the source of truth — never mutate it directly.
"""

def build_ikigai_deep_agent():
    return create_deep_agent(
        model="anthropic:claude-sonnet-4",
        tools=[
            ikigai_score,
            ikigai_regime,
            ikigai_phase,
            ikigai_decompose,
            ikigai_corrections,
            ikigai_plan_cycle,
            ikigai_checkpoint,
            ikigai_sync_vault,
        ],
        system_prompt=IKIGAI_SYSTEM_PROMPT,
        checkpoint_dir=str(CHECKPOINT_DIR),
        memory_backend="sqlite",
    )
```

- [ ] **Step 3: Write entry point**

```python
# life-ops/ikigai/src/agents/ikigai_maintainer/__main__.py
from ikigai_maintainer.deepagents_harness import build_ikigai_deep_agent

if __name__ == "__main__":
    agent = build_ikigai_deep_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": "Run an IKIGAi cycle"}]})
    print(result)
```

- [ ] **Step 4: Test harness loads**

```bash
cd life-ops/ikigai && python -c "from ikigai_maintainer.deepagents_harness import build_ikigai_deep_agent; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(ikigai): deepagents harness for ikigai_maintainer"
```

---

### Task 6: Update `langgraph_entry.py` for IKIGAi

**Files:**
- Modify: `life-ops/ikigai/src/langgraph_entry.py` (or create if not existing)
- Create: `life-ops/ikigai/langgraph.json`

**Steps:**

- [ ] **Step 1: Update `langgraph_entry.py`**

Add `make_ikigai_graph()` factory (imported from `ikigai_maintainer.graph`).

```python
def make_ikigai_graph(config: RunnableConfig | None = None) -> StateGraph:
    from ikigai_maintainer.graph import _make_ikigai_graph_inner
    return _make_ikigai_graph_inner(config)
```

- [ ] **Step 2: Create `langgraph.json`**

```json
{
  "graphs": {
    "ikigai": "./src/langgraph_entry.py:make_ikigai_graph",
    "pae_maintainer": "./vibe-ops/src/langgraph_entry.py:make_pae_graph"
  },
  "default_graph": "ikigai"
}
```

- [ ] **Step 3: Verify `langgraph dev` picks up ikigai graph**

Run: `cd life-ops/ikigai && langgraph dev --graph ikigai --port 2024`
Expected: Server starts on port 2024

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(ikigai): langgraph entry point for ikigai_maintainer"
```

---

### Task 7: Remove PAV references from `life-ops/operational/CLAUDE.md` and CI

**Files:**
- Modify: `life-ops/operational/CLAUDE.md`
- Modify: `.github/workflows/ci.yml`

**Steps:**

- [ ] **Step 1: Remove PAV commands from CLAUDE.md**

Remove all `pav home`, `pav tui`, `pav doctor`, `pav demo seed` references. Keep `operational` core references only.

- [ ] **Step 2: Update CI to remove PAV steps**

Remove PAV health checks from CI. Keep only:
```yaml
- uv run ruff check src/
- uv run ruff format --check src/
- uv run mypy src/
- uv run pytest -m "not e2e"
```

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove PAV references from operational CLAUDE.md and CI"
```

---

## Verification Commands

```bash
# Phase 0: PAV deleted
ls life-ops/operational/apps/  # → No such file or directory

# Phase 1: Core loads
cd life-ops/ikigai && uv run python -c "from ikigai_maintainer.state import IKIGAiStateDict; print('OK')"

# Phase 2: MCP server starts
echo '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | timeout 5 python -m ikigai_maintainer_mcp.bin.ikigai_maintainer-mcp

# Phase 3: LangGraph entry
cd life-ops/ikigai && langgraph dev --graph ikigai --port 2024

# Phase 4: All tests pass
cd life-ops/ikigai && uv run pytest tests/ -v

# Phase 5: CI green
gitHub Actions CI passes
```

---

## Commit Summary

| Task | Commit |
|------|--------|
| 1 | `chore: delete PAV UI — workspace is now contract + agentic systems only` |
| 2 | `feat(ikigai): ikigai_maintainer core — 8 nodes + IKIGAiStateDict` |
| 3 | `feat(ikigai): add SqliteSaver checkpointing to ikigai_maintainer` |
| 4 | `feat(ikigai): ikigai_maintainer MCP server — 8 tools exposed` |
| 5 | `feat(ikigai): deepagents harness for ikigai_maintainer` |
| 6 | `feat(ikigai): langgraph entry point for ikigai_maintainer` |
| 7 | `chore: remove PAV references from operational CLAUDE.md and CI` |
