"""Workflow schema — Pydantic models for file-based agent graph definitions.

Matches LangGraph's file-based state machine concept:
    - Workflow: directed graph of AgentNodes + TaskEdges
    - State: shared JSON dict that persists between nodes
    - Each node is an agent that reads State, does work, writes back

Inspired by LangGraph's checkpointer + state graph pattern.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class AgentStatus(str, Enum):
    """Lifecycle states for an agent node."""

    PENDING = "pending"       # Not yet started
    READY = "ready"           # Waiting for input
    RUNNING = "running"       # Actively executing
    WAITING = "waiting"       # Blocked on dependency
    COMPLETE = "complete"     # Finished successfully
    FAILED = "failed"         # Finished with error
    SKIPPED = "skipped"       # Not run (condition not met)


class TriggerType(str, Enum):
    """What causes a node to fire."""

    MANUAL = "manual"          # Explicit trigger
    ON_COMPLETE = "on_complete"      # When predecessor finishes
    ON_FAIL = "on_fail"              # When predecessor fails
    ON_STATE_CHANGE = "on_state_change"  # State key changed
    SCHEDULED = "scheduled"          # Time-based


# ── Core Schema ──────────────────────────────────────────────────────────────

class ToolCall(BaseModel):
    """A single CLI command executed by an agent."""

    command: str = Field(description="CLI command string (e.g. 'pav habit list --json')")
    cwd: str | None = Field(default=None, description="Working directory override")
    env_vars: dict[str, str] = Field(default_factory=dict, description="Env overrides")
    timeout_s: int = Field(default=60, description="Timeout in seconds")
    expected_exit: int = Field(default=0, description="Expected process exit code")
    retry_on_fail: bool = Field(default=False, description="Re-run if non-zero exit")


class AgentCapability(BaseModel):
    """A named capability that an agent declares it can perform."""

    name: str = Field(description="Capability name (e.g. 'rich_table_parse')")
    description: str = Field(default="", description="Human-readable description")


class AgentNode(BaseModel):
    """A single agent (node) in the workflow graph.

    Each node:
    - Reads shared State (JSON dict)
    - Optionally executes CLI commands via Tools
    - Writes results back to State
    - Emits messages to other nodes via SharedMessageBus
    """

    id: str = Field(description="Unique node ID (e.g. 'ux_io_analyst')")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="", description="What this agent does")

    # Agent identity
    agent_type: str = Field(
        default="generic",
        description="Agent class type (used to load from engines/)",
    )
    capabilities: list[AgentCapability] = Field(default_factory=list)

    # Execution
    tools: list[ToolCall] = Field(default_factory=list, description="CLI commands to run")
    script_path: str | None = Field(
        default=None,
        description="Path to Python agent script (alternative to tools)",
    )
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for this node's expected input state keys",
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for this node's output state keys",
    )

    # Routing
    triggers: list[TriggerType] = Field(
        default_factory=lambda: [TriggerType.ON_COMPLETE],
        description="What activates this node",
    )
    condition: str | None = Field(
        default=None,
        description="JS expression evaluated against state — must be truthy to run",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Node IDs that must complete before this node fires",
    )
    parallel_group: str | None = Field(
        default=None,
        description="Nodes in same parallel_group run concurrently",
    )

    # Persistence
    state_key: str | None = Field(
        default=None,
        description="Key in shared State dict where this node writes its result",
    )
    checkpoint_after: bool = Field(
        default=True,
        description="Persist checkpoint after this node completes",
    )

    # Status (runtime — not serialized to YAML)
    status: AgentStatus = Field(default=AgentStatus.PENDING, exclude=True)
    error: str | None = Field(default=None, exclude=True)
    started_at: datetime | None = Field(default=None, exclude=True)
    finished_at: datetime | None = Field(default=None, exclude=True)
    result: dict[str, Any] = Field(default_factory=dict, exclude=True)

    class Config:
        use_enum_values = True


class TaskEdge(BaseModel):
    """A directed edge in the workflow graph (node A → node B)."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    trigger: TriggerType = Field(default=TriggerType.ON_COMPLETE)
    condition: str | None = Field(default=None, description="JS expr — if false, edge blocked")
    label: str | None = Field(default=None, description="Human-readable label")

    class Config:
        use_enum_values = True


class WorkflowMetadata(BaseModel):
    """Metadata for the workflow definition."""

    name: str = Field(description="Workflow name")
    version: str = Field(default="1.0.0")
    description: str = Field(default="")
    author: str | None = Field(default=None)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = Field(default_factory=list)
    parallelism: int = Field(default=4, description="Max concurrent nodes")
    retry_policy: dict[str, Any] = Field(
        default_factory=lambda: {"max_retries": 2, "backoff_s": 5},
    )


class WorkflowSchema(BaseModel):
    """Complete workflow definition — matches LangGraph's file-based state graph."""

    metadata: WorkflowMetadata
    state_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for the shared workflow state",
    )
    nodes: list[AgentNode] = Field(default_factory=list)
    edges: list[TaskEdge] = Field(default_factory=list)

    # ── I/O ────────────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, path: str | Path) -> WorkflowSchema:
        """Load workflow from a YAML file."""
        text = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return cls.model_validate(data)

    def to_yaml(self, path: str | Path) -> None:
        """Serialize workflow to a YAML file."""
        text = yaml.safe_load(self.model_dump(exclude_none=True, mode="json"))
        Path(path).write_text(yaml.dump(text), encoding="utf-8")

    # ── Graph helpers ───────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> AgentNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_outgoing_edges(self, node_id: str) -> list[TaskEdge]:
        return [e for e in self.edges if e.source == node_id]

    def get_incoming_edges(self, node_id: str) -> list[TaskEdge]:
        return [e for e in self.edges if e.target == node_id]

    def topological_sort(self) -> list[str]:
        """Return node IDs in execution order (Kahn's algorithm)."""
        in_degree: dict[str, int] = {n.id: 0 for n in self.nodes}
        adjacency: dict[str, list[str]] = {n.id: [] for n in self.nodes}
        for edge in self.edges:
            adjacency[edge.source].append(edge.target)
            in_degree[edge.target] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_ids: list[str] = []
        while queue:
            node_id = queue.pop(0)
            sorted_ids.append(node_id)
            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return sorted_ids

    # ── Runtime state ───────────────────────────────────────────────────────

    def get_ready_nodes(self, completed: set[str], failed: set[str]) -> list[str]:
        """Return node IDs that are now ready to execute."""
        ready: list[str] = []
        for node in self.nodes:
            if node.status not in (AgentStatus.PENDING,):
                continue
            # All dependencies satisfied?
            deps_ok = all(d in completed for d in node.depends_on)
            if not deps_ok:
                continue
            ready.append(node.id)
        return ready
