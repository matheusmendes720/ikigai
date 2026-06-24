"""Agent node registry — maps agent_type strings to executable agent classes.

Inspired by LangGraph's node registry. Each registered agent implements the
BaseAgent protocol (read state → execute → write state → emit messages).

Usage:
    registry = NodeRegistry()
    registry.register("tdd_agent", MyTDDAgent)
    agent = registry.instantiate("tdd_agent", node_config, shared_state)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel

from agents.harness.workflow_schema import AgentNode, AgentStatus


# ── Agent Protocol ────────────────────────────────────────────────────────────

class BaseAgent:
    """Abstract base class for all harness agents.

    Subclass this and implement:
        execute(self, state: dict) -> dict[str, Any]
        validate_input(self, state: dict) -> bool

    The harness handles:
        - subprocess execution (CLI calls)
        - message bus publishing
        - checkpointing state
        - error handling + retry
    """

    def __init__(self, node: AgentNode, workflow_id: str):
        self.node = node
        self.workflow_id = workflow_id
        self.status = AgentStatus.PENDING
        self.result: dict[str, Any] = {}

    def validate_input(self, state: dict) -> bool:
        """Return True if required state keys are present."""
        required = list(self.node.input_schema.get("required", []))
        return all(k in state for k in required)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the agent logic. Returns dict to merge into shared state."""
        raise NotImplementedError

    def before_execute(self, state: dict[str, Any]) -> None:
        """Hook called before execution (e.g. log start)."""

    def after_execute(self, state: dict[str, Any], result: dict[str, Any]) -> None:
        """Hook called after successful execution (e.g. publish result)."""

    def on_error(self, error: Exception) -> None:
        """Hook called when execute() raises an exception."""
        self.node.error = str(error)
        self.node.status = AgentStatus.FAILED


# ── NodeRegistry ──────────────────────────────────────────────────────────────

class NodeRegistry:
    """Maps agent_type strings → BaseAgent subclasses.

    Supports:
        - Direct class registration
        - Auto-discovery from engines/ directory
        - Dynamic import from arbitrary module paths
    """

    def __init__(self, engines_dir: str | Path | None = None):
        self._registry: dict[str, Type[BaseAgent]] = {}
        if engines_dir:
            self.discover(engines_dir)

    def register(self, agent_type: str, cls: Type[BaseAgent]) -> None:
        """Register an agent class by type string."""
        self._registry[agent_type] = cls

    def get(self, agent_type: str) -> Type[BaseAgent] | None:
        return self._registry.get(agent_type)

    def instantiate(self, agent_type: str, node: AgentNode, workflow_id: str) -> BaseAgent:
        """Create a runnable agent instance for a node."""
        cls = self._registry.get(agent_type)
        if cls is None:
            raise ValueError(
                f"Unknown agent_type '{agent_type}'. "
                f"Registered: {list(self._registry.keys())}"
            )
        return cls(node=node, workflow_id=workflow_id)

    def discover(self, engines_dir: str | Path) -> None:
        """Auto-import all BaseAgent subclasses from a directory.

        Each Python file in `engines_dir` should define ONE agent class
        named `XxxAgent` that inherits from BaseAgent. It will be
        registered under `xxx_agent` (snake_case of the class name).
        """
        engines_path = Path(engines_dir)
        if not engines_path.exists():
            return

        # Ensure parent package is importable
        parent = engines_path.parent
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))

        for fpath in engines_path.glob("*.py"):
            if fpath.name.startswith("_"):
                continue
            module_name = f"agents.harness.engines.{fpath.stem}"
            try:
                mod = importlib.import_module(module_name)
            except Exception:
                continue

            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseAgent)
                    and attr is not BaseAgent
                ):
                    # snake_case class name → agent_type
                    stem = fpath.stem  # e.g. "tdd_agent"
                    self.register(stem, attr)

    def list_registered(self) -> list[str]:
        """Return all registered agent_type strings."""
        return sorted(self._registry.keys())
