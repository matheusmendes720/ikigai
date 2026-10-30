"""Paperclip — AgentAdapter Protocol + AgentResult model.

The Protocol mirrors ``ForkAdapter`` (``src/mesh/adapters/base.py``) so the
two abstractions feel like siblings: each declares ``name`` + a single
``run(...)`` method that returns a frozen result. ``AgentResult`` is a
Pydantic v2 model (frozen, extra=forbid) per the project-wide invariant in
``CLAUDE.md``: Pydantic v2 strict on all schemas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class AgentResult(BaseModel):
    """Frozen result of an AgentAdapter invocation.

    Mirrors the contract of ``vault_write`` (in sys_ikigai/vault/) — strict
    Pydantic v2 with ``frozen=True`` and ``extra="forbid"`` so downstream
    nodes can rely on field presence and immutability.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    output: str
    duration_s: float
    error: str | None = None


@runtime_checkable
class AgentAdapter(Protocol):
    """Protocol for a Paperclip-routable AI coding session.

    Implementations live under ``paperclip/agents/<name>.py`` (claude, pi,
    mcode, omo, hermes, openclaw). MVP only ships ``claude.py`` as a real
    subprocess wrapper; the others are stubs that raise
    ``NotImplementedError("Paperclip: <name> adapter pending")``.

    Attributes:
        name: short identifier (``"claude"``, ``"pi"`` etc.) — used in
            Paperclip logs and routing decisions.
        timeout_s: default wall-clock cap for one ``run()`` call.
    """

    name: str
    timeout_s: int

    def run(
        self,
        prompt: str,
        cwd: Path,
        *,
        timeout_s: int | None = None,
    ) -> AgentResult:
        """Invoke the AI session on the given prompt inside the worktree.

        Args:
            prompt: the spec / task to give the agent. Usually the resolved
                spec (post-HIL-merge) plus an implementation hint.
            cwd: working directory — the worktree path the agent should
                operate in. Implementations must NOT escape this path.
            timeout_s: optional per-call override of ``self.timeout_s``.

        Returns:
            Frozen ``AgentResult`` — never raises on agent failure; populates
            ``success=False`` + ``error=`` instead.
        """
        ...
