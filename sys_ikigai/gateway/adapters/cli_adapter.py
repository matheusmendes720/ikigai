"""cli adapter (stub)."""
from __future__ import annotations
from typing import Any


class CliAdapter:
    """Stub CLI adapter — replace with real implementation per mesh spec."""

    name = "cli"

    def call_tool(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"result": "stub", "adapter": self.name, "tool": tool, "args": args}
