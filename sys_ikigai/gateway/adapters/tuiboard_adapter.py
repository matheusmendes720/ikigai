"""tuiboard adapter (stub)."""
from __future__ import annotations
from typing import Any


<<<<<<< HEAD
class TuiboardAdapter:
    """Stub TuiboardAdapter — replace with real implementation per mesh spec."""
=======
class Adapter:
    """Stub adapter — replace with real implementation per mesh spec."""
>>>>>>> 97200497 (fix(serve): add {name}_adapter.py modules matching gateway import convention)

    name = "tuiboard"

    def call_tool(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"result": "stub", "adapter": self.name, "tool": tool, "args": args}
