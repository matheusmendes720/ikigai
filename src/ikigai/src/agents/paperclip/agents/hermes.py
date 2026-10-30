"""Hermes adapter — STUB.

Wave N+2: wire once Hermes's CLI/MCP is reachable from this machine.
"""

from __future__ import annotations

from pathlib import Path

from .base import AgentResult


class HermesAdapter:
    """Stub for the Hermes adapter."""

    name = "hermes"
    timeout_s = 180

    def run(
        self,
        prompt: str,
        cwd: Path,
        *,
        timeout_s: int | None = None,
    ) -> AgentResult:
        raise NotImplementedError(
            "Paperclip: hermes adapter pending (Wave N+2 — see specs/M169-paperclip/SPEC.md)"
        )
