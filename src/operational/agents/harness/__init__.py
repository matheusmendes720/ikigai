"""PAV Agent Harness — File-based multi-agent orchestration (langgraph-style).

Architecture:
    workflow_yaml → WorkflowSchema → FileBasedHarness → subprocess pav CLI → JSON state files
                              ↓
                    ┌─────────┴──────────┐
                    │   SharedMessageBus  │  ← JSON files as pub/sub
                    │   TaskQueue         │  ← file-backed work queue
                    │   NodeRegistry       │  ← agent node registry
                    └─────────────────────┘

Each agent is a state machine:
    READY → RUNNING → WAITING → COMPLETE/FAILED

Workflows defined in YAML → loaded as WorkflowSchema → executed by harness.
"""

from agents.harness.workflow_schema import WorkflowSchema, AgentNode, TaskEdge
from agents.harness.file_harness import FileBasedHarness
from agents.harness.message_bus import SharedMessageBus
from agents.harness.task_queue import TaskQueue
from agents.harness.node_registry import NodeRegistry

__all__ = [
    "WorkflowSchema",
    "AgentNode",
    "TaskEdge",
    "FileBasedHarness",
    "SharedMessageBus",
    "TaskQueue",
    "NodeRegistry",
]
