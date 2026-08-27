# Agentic/Multi-Agent Swarm Infrastructure Map
**Generated:** 2026-06-30  
**Path:** `C:\Users\mathe\code_space\life-oss\life\.omo\evidence\agentic-md-swarm-map.md`

---

## 1. Existing Workflow YAMLs

### 1.1 `life-ops/operational/workflows/pav_qa_pipeline.yaml`
- **Type:** Shell-based sequential pipeline (author: hermes-orchestrator)
- **Tasks:** 6 phases — UX/IO Analyst → TDD Agent → Flow Analyzer → Reqs Validator → Style Analyzer → System Optimizer
- **Features:** Slack notifications, cron trigger, retry policy, on_success callbacks
- **Execution:** Sequential with dependencies, max_parallel configurable
- **Status:** Defined, appears executable

### 1.2 `life-ops/operational/workflows/daily_pipeline.yaml`
- **Type:** Scheduled daily pipeline (cron: `0 2 * * *`)
- **Tasks:** Health check → State → Demo → Habit/Routine metrics → Policy → Reports → Parallel benchmarks
- **Features:** Slack notifications, parallel task group for benchmarks, environment variables
- **Status:** Defined, appears executable

### 1.3 `life-ops/operational/agents/workflows/qa_swarm.yaml`
- **Type:** LangGraph-style swarm definition (400 lines)
- **Nodes (6):** ux_io_analyst, tdd_agent, flow_analyzer, reqs_validator, style_analyzer, system_optimizer
- **Edges:** Phase 1 parallel group (depends on ux_io_analyst), Phase 2 feeds reqs_validator, Phase 3 feeds optimizer
- **Author:** hermes-qa-engine
- **Tags:** qa, cli, integration, synthetic-data, hermes
- **State Schema:** Full shared state with io_patterns, flow_graph, spec_gaps, benchmarks, etc.
- **Status:** Schema defined; needs FileBasedHarness execution engine

---

## 2. Claude Skills/Agents Directories

### 2.1 Skills (30 found in `.claude/skills/`)

**Swarm-Orchestration Relevant:**
| Path | Description |
|------|-------------|
| `.claude/skills/swarm-orchestration/SKILL.md` | agentic-flow swarm init/spawn/orchestrate, mesh/hierarchical/adaptive topologies |
| `.claude/skills/swarm-advanced/SKILL.md` | 970-line comprehensive guide: Research/Dev/Testing/Analysis swarms, MCP tool integration |
| `.claude/skills/v3-swarm-coordination/SKILL.md` | 15-agent hierarchical mesh for v3, 4-phase 14-week timeline |

**Other Agent/Coordination Skills:**
| Path | Description |
|------|-------------|
| `.claude/skills/stream-chain/SKILL.md` | Stream-JSON chaining for multi-agent pipelines |
| `.claude/skills/sparc-methodology/SKILL.md` | SPARC development methodology |
| `.claude/skills/pair-programming/SKILL.md` | Pair programming with agents |
| `.claude/skills/hooks-automation/SKILL.md` | Pre/post task hooks automation |
| `.claude/skills/agentdb-advanced/SKILL.md` | AgentDB advanced features |
| `.claude/skills/agentdb-memory-patterns/SKILL.md` | Persistent memory for agents |
| `.claude/skills/agentdb-vector-search/SKILL.md` | Vector search for agents |
| `.claude/skills/agentdb-optimization/SKILL.md` | AgentDB performance optimization |
| `.claude/skills/agentdb-learning/SKILL.md` | RL algorithms for agents |

### 2.2 Agents (18 found in `.claude/agents/`)

**Swarm Coordinators (`.claude/agents/swarm/`):**
| Path | Type | Description |
|------|------|-------------|
| `swarm/mesh-coordinator.md` | Peer-to-peer | Gossip/pBFT/Raft consensus, 963 lines, GraphRoPE, Byzantine detection |
| `swarm/hierarchical-coordinator.md` | Queen-worker | Task decomposition, hyperbolic attention, 710 lines |
| `swarm/adaptive-coordinator.md` | Dynamic | Topology switching, dynamic attention selection, 1127 lines |

**Consensus Agents (`.claude/agents/consensus/`):**
| Path | Type | Description |
|------|------|-------------|
| `consensus/quorum-manager.md` | Coordinator | Dynamic quorum adjustment, weighted voting, 823 lines |
| `consensus/raft-manager.md` | Coordinator | Raft consensus implementation |
| `consensus/gossip-coordinator.md` | Coordinator | Epidemic dissemination, peer selection |
| `consensus/crdt-synchronizer.md` | Coordinator | CRDT-based conflict-free sync |
| `consensus/byzantine-coordinator.md` | Coordinator | Byzantine fault tolerance |
| `consensus/performance-benchmarker.md` | Evaluator | Performance benchmarking agent |

**Other Agents:**
| Path | Type | Description |
|------|------|-------------|
| `consensus/security-manager.md` | Security | Security auditing agent |
| `swarm/hierarchical-coordinator.md` | Coordinator | Already listed above |
| `testing/tdd-london-swarm.md` | Tester | London School TDD in swarms |
| `testing/production-validator.md` | Validator | Production validation |
| `core/planner.md` | Planner | Core planning agent |
| `sparc/specification.md` | SPARC | Specification phase |
| `sparc/pseudocode.md` | SPARC | Pseudocode phase |
| `sparc/architecture.md` | SPARC | Architecture phase |
| `sparc/refinement.md` | SPARC | Refinement phase |
| `browser/browser-agent.yaml` | Browser | Browser automation agent |

---

## 3. LangGraph Code References

### 3.1 `life-ops/operational/agents/harness/` — Python-Native LangGraph-Style Engine

**File:** `agents/harness/__init__.py` (line 1-32)
- Mentions "langgraph-style" in docstring
- Architecture: workflow_yaml → WorkflowSchema → FileBasedHarness → subprocess pav CLI → JSON state files

**Core Components:**

| File | Lines | Purpose |
|------|-------|---------|
| `harness/workflow_schema.py` | ~200 | WorkflowSchema, AgentNode, TaskEdge Pydantic models |
| `harness/file_harness.py` | ~300 | FileBasedHarness execution engine |
| `harness/message_bus.py` | 181 | JSONL pub/sub — SharedMessageBus (matches LangGraph shared state) |
| `harness/task_queue.py` | 219 | File-backed FIFO+priority queue (matches LangGraph work queue concept) |
| `harness/node_registry.py` | 138 | BaseAgent protocol + NodeRegistry (maps agent_type → class) |
| `harness/engines/tdd_agent.py` | 195 | Example agent: generates pytest + BDD from CSV |

### 3.2 `life-ops/operational/agents/orchestrator/` — Workflow Orchestrator

| File | Lines | Purpose |
|------|-------|---------|
| `orchestrator/__init__.py` | 24 | Exports WorkflowOrchestrator, WorkflowSchema, etc. |
| `orchestrator/engine.py` | 315 | **WorkflowOrchestrator** — dependency graph execution, retry, callbacks |
| `orchestrator/schema.py` | 287 | Full WorkflowSchema with TaskType (shell/python/http/docker/conditional/parallel/loop/data_processor/notify) |
| `orchestrator/state.py` | ~150 | ExecutionState, ExecutionStore, ExecutionStatus, TaskExecution |
| `orchestrator/scheduler.py` | 220 | Cron-based scheduling with cron_next_fire parser |
| `orchestrator/monitor.py` | ~100 | WorkflowMonitor |
| `orchestrator/cli.py` | ~100 | CLI app |

---

## 4. Hermes/Mesh/Orchestrator Terms Found

### 4.1 Hermes References
| File | Line | Term |
|------|------|------|
| `workflows/qa_swarm.yaml` | 30 | `author: hermes-qa-engine` |
| `workflows/pav_qa_pipeline.yaml` | 10 | `author: hermes-orchestrator` |
| `workflows/daily_pipeline.yaml` | 10 | `author: hermes-orchestrator` |

### 4.2 Orchestrator References (Python files)
| File | Line | Term |
|------|------|------|
| `vibe-ops/src/pipeline/sync_orchestrator.py` | — | SyncOrchestrator |
| `vibe-ops/src/pipeline/mvl_orchestrator.py` | — | MVLOrchestrator |
| `vibe-ops/src/pipeline/sync_orchestrator.py` | — | Sync orchestrator for Obsidian↔SQLite↔Taskwarrior |
| `life-ops/operational/agents/orchestrator/` | — | Full workflow orchestrator package |

### 4.3 Harness Architecture (Python)
| File | Line | Term |
|------|------|------|
| `agents/harness/__init__.py` | 1 | "File-based multi-agent orchestration (langgraph-style)" |
| `agents/harness/message_bus.py` | 3 | "Matches LangGraphs shared state concept" |
| `agents/harness/task_queue.py` | 3 | "Matches LangGraphs concept of a shared work queue" |
| `agents/harness/node_registry.py` | 3 | "Inspired by LangGraphs node registry" |

---

## 5. Integration Points for New System

### 5.1 Entry Points
1. **Workflow YAMLs** → `agents/workflows/qa_swarm.yaml` (LangGraph-style nodes/edges)
2. **FileBasedHarness** → `agents/harness/file_harness.py` — executes workflow YAMLs
3. **WorkflowOrchestrator** → `agents/orchestrator/engine.py` — dependency graph execution
4. **SharedMessageBus** → `agents/harness/message_bus.py` — JSONL pub/sub inter-agent comms
5. **TaskQueue** → `agents/harness/task_queue.py` — file-backed durable queue

### 5.2 NodeRegistry + Agent Discovery
- `agents/harness/node_registry.py` auto-discovers agents from `engines/` directory
- BaseAgent protocol: `execute(state) → dict`, `validate_input(state) → bool`
- Pattern: snake_case filename → agent_type (e.g., `tdd_agent.py` → `tdd_agent`)

### 5.3 State Passing
- Shared state via JSON files (`~/.time-tasker/agent_harness/`)
- Message bus via JSONL (`{workflow_id}_bus.jsonl`)
- Workflow state schema in YAML with explicit `state_schema` block

### 5.4 Task Types Supported
`shell`, `python`, `http`, `docker`, `conditional`, `parallel`, `loop`, `data_processor`, `notify`

### 5.5 Trigger/Schedule System
- `WorkflowScheduler` with cron parsing
- Trigger types: manual, schedule, webhook, file_change

---

## 6. Gaps Where New Infrastructure Is Needed

### 6.1 Agent Spawning / Dynamic Agent Creation
- **Gap:** No actual agent spawning infrastructure. YAML defines nodes, but no runtime agent instantiation from the `.claude/agents/` definitions.
- **Need:** Bridge between `.claude/agents/*.md` agent specs and `NodeRegistry` auto-discovery.

### 6.2 MCP Tool Integration Layer
- **Gap:** The swarm skills reference `mcp__claude-flow__*` tools extensively, but no actual MCP server/client is wired into the Python harness.
- **Need:** MCP bridge for `swarm_init`, `agent_spawn`, `task_orchestrate`, `memory_usage`, `neural_patterns`, etc.

### 6.3 Dynamic Topology Switching
- **Gap:** `adaptive-coordinator.md` describes topology switching, but no runtime implementation exists in the harness.
- **Need:** Runtime topology adaptation in `FileBasedHarness`.

### 6.4 Consensus Protocol Implementations
- **Gap:** `.claude/agents/consensus/` has 6 coordinator agent specs (quorum, raft, gossip, crdt, byzantine, benchmarker) — all are **specs only**, no Python implementation.
- **Need:** Actual consensus protocol implementations if true distributed agents are needed.

### 6.5 LangGraph Python SDK Usage
- **Gap:** The harness is described as "langgraph-style" but uses custom Python code. No actual `langgraph` or `langchain` Python package imports found.
- **Found:** 1 match for "langgraph/langchain" — in `agents/harness/__init__.py` docstring only.
- **Need:** Either embrace actual LangGraph SDK or clarify "langgraph-style" is purely conceptual.

### 6.6 Neural/Attention Mechanisms
- **Gap:** `mesh-coordinator.md` and `adaptive-coordinator.md` reference AgentDB attention services (`FlashAttention`, `HyperbolicAttention`, `MultiHeadAttention`, `GraphRoPE`) — not implemented anywhere in the codebase.
- **Need:** Either implement or mock these for actual agent coordination.

### 6.7 Persistent Agent State Across Runs
- **Gap:** TaskQueue and MessageBus are file-backed but per-workflow-id. No cross-workflow persistent agent memory.
- **Need:** Shared memory store for multi-workflow agent coordination.

### 6.8 GitHub Issue / Task Synchronization
- **Gap:** `v3-swarm-coordination` skill references GitHub issue creation/tracking, but no integration in the Python infrastructure.
- **Need:** GitHub API integration for issue → agent task mapping.

---

## Summary

The codebase has a **well-structured Python-native multi-agent harness** (`agents/harness/`) that is conceptually modeled on LangGraph but uses custom file-based state/message passing. The `agents/orchestrator/` provides a full workflow execution engine with cron scheduling. YAML workflow definitions (`workflows/*.yaml`) define executable pipelines.

The **swarm/agent specs in `.claude/agents/`** (mesh coordinator, hierarchical coordinator, adaptive coordinator, quorum manager, etc.) are **detailed specification documents** with extensive code samples — but they exist as design documentation, not as wired Python implementations.

**Key finding:** The Python infrastructure exists to build swarm orchestration on (TaskQueue, MessageBus, NodeRegistry, WorkflowOrchestrator), but the actual agent types (tdd_agent, ux_io_agent, etc.) are minimal stubs. The rich agent specs in `.claude/agents/` need a bridge to be executable.
