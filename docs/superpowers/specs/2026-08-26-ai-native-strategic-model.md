# AI-Native Strategic Model — Specification

> **For agentic workers:** Use `superpowers:writing-plans` to create the implementation plan after this spec is approved.
> **Status:** APPROVED — executing

**Date:** 2026-08-26
**Paradigm:** AI-native, contract-first, zero bespoke UI

---

## 1. Mission

Transform `life-ops` from a runnable productivity application (PAV TUI + CLI) into a **strategic model template** — a portable IKIGAi meta-brain that defines contracts consumed by external AI-native interfaces. No UI code lives here. The workspace is the brain; external apps are the eyes, hands, and voice.

**The inversion:**
- Before: workspace has UI + logic + data; external tools are thin clients
- After: workspace has contracts + logic + data; AI agents (Claude Code, deepagents) are the UI

---

## 2. Architectural Decisions (Locked)

| # | Decision | Resolution |
|---|----------|------------|
| AD1 | UI layer | **Delete** PAV TUI + CLI. No bespoke UI. |
| AD2 | Agent harness | **deepagents** (`langchain-ai/deepagents`) — LangGraph runtime + checkpointing + memory |
| AD3 | Interface protocol | **MCP** (stdio + HTTP+SSE dual transport) — all apps expose tools via MCP |
| AD4 | Data ownership | Markdown vault is canonical SoT. SQLite is internal mirror. External apps consume via MCP. |
| AD5 | Execution model | Human-in-the-loop via existing apps (Claude Code, Obsidian). Cron daemon optional. |
| AD6 | Strategic model | `life-ops/ikigai/` — IKIGAi 5 vectors, 6 heuristics, UEID hierarchy, regime FSM, phase FSM |
| AD7 | Planning engine | `vibe-ops/` PAE-Maintainer — dual-channel (prospective + retrospective), wrapped as deepagents |
| AD8 | Bridge to UPIs | Phase MCP (`solverforge-calendar-mcp`) — UPI CRUD as MCP tools |

---

## 3. What Gets Deleted (Full Removal)

```
life-ops/operational/apps/   ← DELETE ENTIRE DIRECTORY
```

**Everything in `apps/` is deleted** — the PAV Typer CLI and the Textual TUI are gone. Git history is preserved in git (can be recovered via `git log` + `git show`).

No archive step. No backup directory. Clean deletion.

**What gets preserved:**
```
life-ops/operational/
├── packages/core/src/operational/   ← KEEP (pure logic, zero I/O)
│   ├── entities/                     ← KEEP (Pydantic models)
│   ├── core/                        ← KEEP (habit_engine, policy_engine, etc.)
│   ├── persistence/                 ← KEEP (Repository Protocol + SQLite)
│   └── constants.py                 ← KEEP (PAV_NS 22 constants)
├── tests/                           ← KEEP
└── life-ops/ikigai/                 ← KEEP + BUILD HERE (strategic model)
```

---

## 4. What Gets Built

### 4.1 `ikigai_maintainer` — Deep Agents LangGraph

**Path:** `life-ops/ikigai/src/agents/ikigai_maintainer/`

A deepagent that runs the IKIGAi meta-brain as a LangGraph. Wraps `pae_maintainer` dual-channel + adds IKIGAi-specific nodes.

```
IKIGAi-Maintainer StateGraph (ikigai_maintainer)

OBSERVE ────────────────────────────────▶ PLAN ‖ REFLECT ──▶ BALANCE ──▶ VECTOR_SCORING ──▶ HEURISTICS ──▶ DECOMPOSE ──▶ COMMIT
              │                                                      │
              └──────────────────────────────────────────────────────┘
```

**Nodes:**

| Node | Responsibility | FSM |
|------|---------------|-----|
| `observe` | Read sensors: habits, tasks, Q_HE, UPI state | — |
| `plan` | Prospective: draft next actions for current tier | — |
| `reflect` | Retrospective: aggregate completed work | — |
| `balance` | Workload vs capacity + hysteresis enforcement | Shared |
| `score_vectors` | Compute 5 IKIGAi vectors + meta-vector | H4/H5 |
| `apply_heuristics` | Run H1-H6 deterministic algorithms | H1-H6 |
| `decompose` | Traverse UEID hierarchy (Dream→Task) | — |
| `commit` | Persist to SQLite + markdown vault (guarded by balancer) | — |

**State dict shape (`IKIGAiStateDict`):**

```python
class IKIGAiStateDict(TypedDict, total=False):
    # Identity
    cycle_id: str
    cycle_start: str
    cycle_end: str
    iteration: int
    last_step: str

    # Regime FSM (H1)
    regime_state: Literal["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]
    q_he_score: float
    days_in_regime: int
    is_hysteresis_active: bool

    # Phase FSM (H2)
    phase: Literal["FUNDAÇÃO", "BUSCA", "HACKATHON", "RECUPERACAO", "OVERCLOCK"]
    phase_iteration: int
    phase_converged: bool
    phase_weights: dict[str, float]

    # IKIGAi 5-vector scores
    vector_scores: dict[Literal["passion", "skill", "market", "revenue", "course"], float]
    meta_vector_score: float

    # UEID hierarchy
    active_dream_ueid: str | None
    active_goal_ueids: list[str]
    active_objective_ueids: list[str]
    active_project_ueids: list[str]
    active_task_ueids: list[str]

    # Balancer (shared PAE + IKIGAi)
    workload_estimate: float
    capacity_estimate: float
    balancer_verdict: Literal["OK", "OVERLOAD", "UNDERLOAD", "RECOVER"]

    # Channels
    prospective_buffer: Annotated[list[str], operator.add]
    retrospective_log: Annotated[list[str], operator.add]

    # Corrections from H1-H6
    corrections: Annotated[list[CorrectionSignal], operator.add]
    kill_switch_triggered: bool
    terminated: bool
```

### 4.2 `ikigai_maintainer-mcp` — MCP Server

**Path:** `life-ops/ikigai/src/agents/ikigai_maintainer_mcp/`

MCP server exposing IKIGAi tool contracts. Dual transport: stdio (Claude Code subprocess) + HTTP+SSE (deepagents).

**Tools exposed:**

| Tool | Signature | Description |
|------|-----------|-------------|
| `ikigai_score` | `() → vector_scores + meta_vector` | Returns 5 vector scores |
| `ikigai_regime` | `() → regime_state + days + severity` | Current regime FSM state |
| `ikigai_phase` | `() → phase + weights + iteration` | Current phase FSM state |
| `ikigai_decompose` | `(dream_ueid: str) → UEID tree` | Decompose dream to tasks |
| `ikigai_corrections` | `() → list[CorrectionSignal]` | H1-H6 corrective signals |
| `ikigai_plan_cycle` | `(input?: CycleInput) → CycleResult` | Run one observe→commit |
| `ikigai_checkpoint` | `() → bool` | Force checkpoint to SQLite |
| `ikigai_sync_vault` | `() → SyncResult` | Reconcile markdown ↔ SQLite |

### 4.3 Deep Agents Harness Integration

**File:** `life-ops/ikigai/src/agents/ikigai_maintainer/deepagents_harness.py`

```python
from deepagents import create_deep_agent

ikigai_agent = create_deep_agent(
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
    system_prompt="You are the IKIGAi meta-brain. ...",
    checkpoint_dir="~/.ikigai/checkpoints",
    memory_backend="sqlite",
)
```

### 4.4 LangGraph Entry Point

**File:** `life-ops/ikigai/src/langgraph_entry.py`

Wraps `ikigai_maintainer` as LangGraph StateGraph factories for `langgraph dev`.

```python
def make_ikigai_graph(config: RunnableConfig | None = None) -> StateGraph:
    ...

def make_replan_graph(...): ...
def make_rollup_graph(...): ...
def make_correction_graph(...): ...
```

---

## 5. MCP Contract Map

```
ikigai_maintainer-mcp (ikigai_maintainer-mcp.rs or Python)
├── tools: ikigai_score, ikigai_regime, ikigai_phase,
│          ikigai_decompose, ikigai_corrections, ikigai_plan_cycle,
│          ikigai_checkpoint, ikigai_sync_vault
├── transport: stdio + HTTP+SSE
└── auth: none (local only)

tuiboard-mcp (tuiboard, TypeScript/Bun)
├── tools: boards_list, board_get, card_create, card_update, card_delete
├── transport: stdio + HTTP+SSE
└── source: ~/.tuiboard/

taskdog-mcp (taskdog, Python/FastMCP)
├── tools: td_projects, td_tasks, td_add, td_done, td_context
├── transport: stdio + HTTP+SSE
└── source: taskwarrior

solverforge-calendar-mcp (solverforge-calendar, Rust/rmcp)
├── tools: upi_sync, upi_list, upi_get, upi_update, upi_search,
│          calendars_list, events_list, google_sync, projects_*
├── transport: stdio + HTTP+SSE
└── source: SOLVERFORGE_DATA_DIR
```

**mcp-gateway** routes by tool prefix:

```yaml
gateways:
  - name: ikigai_maintainer
    command: ["ikigai_maintainer-mcp"]
    tool_prefixes: ["ikigai_"]
  - name: tuiboard
    command: ["tuiboard"]
    tool_prefixes: ["boards_", "card_"]
  - name: taskdog
    command: ["taskdog-mcp"]
    tool_prefixes: ["td_"]
  - name: solverforge-calendar
    command: ["solverforge-calendar-mcp"]
    tool_prefixes: ["calendars_", "events_", "projects_", "dependencies_", "google_", "upi_"]
```

---

## 6. Data Flow

```
External AI Interface (Claude Code, deepagents)
        │
        │  HTTP+SSE or stdio
        ▼
┌─────────────────────────────────────────┐
│         mcp-gateway (:3737)              │
│                                          │
│  routes by tool prefix → MCP server     │
└─────────────────────────────────────────┘
        │
        ├────────────────────┬──────────────────────┐
        ▼                    ▼                      ▼
┌───────────────┐  ┌────────────────┐  ┌────────────────────────┐
│ikigai_maintain│  │  tuiboard-mcp │  │solverforge-calendar-mcp│
│er-mcp         │  │                │  │                        │
│(Python or Rust)│  │(TypeScript)   │  │(Rust)                  │
└───────┬───────┘  └───────┬────────┘  └──────────┬───────────┘
        │                  │                      │
        │ reads            │ reads                │ reads/writes
        ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────┐
│              Markdown Vault (IKIGAi SoT)             │
│  ~/ikigai-vault/                                    │
│  dreams/, goals/, objectives/, projects/, tasks/      │
└─────────────────────────────────────────────────────┘
        │
        │ sync
        ▼
┌─────────────────┐
│     SQLite       │
│ (internal mirror) │
└─────────────────┘
```

---

## 7. Migration Plan

### Phase 0: Delete PAV UI

- [ ] Delete `life-ops/operational/apps/` directory entirely
- [ ] Update `pyproject.toml` workspace members — remove `apps/` references
- [ ] Update `life-ops/operational/CLAUDE.md` — remove PAV commands
- [ ] Remove PAV from CI workflows (`.github/workflows/ci.yml`)
- [ ] Commit: `chore: delete PAV UI — workspace is now contract + agentic systems only`

### Phase 1: Build `ikigai_maintainer` Core (MVP)

- [ ] Create `life-ops/ikigai/src/agents/ikigai_maintainer/state.py`
- [ ] Implement 8 nodes (observe, plan, reflect, balance, score_vectors, apply_heuristics, decompose, commit)
- [ ] Create `make_ikigai_graph()` factory
- [ ] Integrate with existing `pae_maintainer` where possible
- [ ] Add `SqliteSaver` checkpointing
- [ ] Commit: `feat(ikigai): ikigai_maintainer core — 8 nodes + checkpointing`

### Phase 2: Build `ikigai_maintainer-mcp`

- [ ] Create MCP server exposing 8 IKIGAi tools
- [ ] Dual transport: stdio + HTTP+SSE
- [ ] Wire into `mcp-gateway` with `ikigai_` prefix
- [ ] Commit: `feat(ikigai): ikigai_maintainer MCP server — 8 tools`

### Phase 3: Deep Agents Harness

- [ ] Create `deepagents_harness.py` using `deepagents.create_deep_agent`
- [ ] Configure `SqliteSaver` + `InMemoryStore` for memory
- [ ] LangSmith integration for tracing
- [ ] Commit: `feat(ikigai): deepagents harness integration`

### Phase 4: LangGraph Entry Point

- [ ] Update `life-ops/ikigai/src/langgraph_entry.py`
- [ ] Expose `make_ikigai_graph()`, `make_replan_graph()`, etc.
- [ ] `langgraph.json` update for `ikigai` graph
- [ ] Commit: `feat(ikigai): langgraph entry point for ikigai_maintainer`

### Phase 5: Decommission PAV references

- [ ] Remove PAV mentions from `CLAUDE.md`, `AGENTS.md`
- [ ] Remove PAV from CI workflows
- [ ] Update docs to reflect new architecture
- [ ] Commit: `chore: remove PAV UI references`

---

## 8. Invariants (Preserved from IKIGAi SPEC)

| Invariant | Enforcement |
|-----------|-------------|
| Markdown vault = canonical SoT | Sync protocol: markdown wins on drift |
| Append-only on plan_entities | SQLite DB trigger |
| UEID uniqueness | DB unique constraint |
| Vector scores ∈ [0, 100] | Pydantic Field validator |
| Q_HE ∈ [0, 1] | Pydantic Field validator |
| Hysteresis respected | `days_in_regime` counter in state |
| Zero LLM in hot path | Only `ikigai_score` explanation uses LLM (optional) |

---

## 9. What's NOT Being Built

- No new TUI or CLI (PAV deleted)
- No LangChain hub or agent marketplace integration
- No cloud APIs or OAuth
- No real-time daemon (cron-based optional trigger is fine for v1)

---

## 10. References

- IKIGAi SPEC: `life-ops/ikigai/SPEC.md`
- PAE-Maintainer: `vibe-ops/src/agents/pae_maintainer/`
- Phase MCP: `docs/superpowers/plans/2026-08-26-phase-mcp-unified-planning.md`
- deepagents: `langchain-ai/deepagents`
- MCP gateway: `apps/mcp-gateway/config/gateways.yaml`
- langgraph_entry.py: `vibe-ops/src/langgraph_entry.py`

---

*Spec status: DRAFT — awaiting user approval*
