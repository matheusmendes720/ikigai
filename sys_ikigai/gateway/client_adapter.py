"""MCPClientAdapter — downstream server protocol (Task 14 partner).

The gateway speaks to downstream MCP servers via this protocol. Each adapter
wraps an stdio-or-HTTP subprocess; the gateway itself only depends on the
`call_tool(name, arguments)` interface.

Serverless scope (ADR-037, 2026-11-01): the PC-only stdio forks were retired,
so the adapters published here are the data-mesh ones (CLI fork and taskdog
SQLite fork) — see `sys_ikigai.gateway.downstream`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MCPClientAdapter(ABC):
    """Protocol every downstream adapter implements.

    Implementations are responsible for their own lifecycle: subprocess
    spawn, JSON-RPC framing, reconnection. The gateway never sees a
    socket — it just calls `call_tool`.
    """

    def __init__(self, *, name: str, command: list[str]) -> None:
        self.name = name
        self.command = command

    @abstractmethod
    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke `name` with `arguments`; return JSON-serialisable result."""
        raise NotImplementedError

    def health(self) -> bool:
        """Default: assume healthy unless subclass overrides."""
        return True

    def close(self) -> None:
        """Default: no resources to release."""
        return None


__all__ = ["MCPClientAdapter"]
