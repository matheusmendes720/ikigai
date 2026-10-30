"""MCode / mmx-cli adapter — STUB.

Wave N+1: wire to ``mmx-cli`` (the loaded skill ``minimax-skills:mmx-cli``).
Until then this is a stub — same pattern as ``pi.py``.
"""

from __future__ import annotations

from pathlib import Path

from .base import AgentResult


class MCodeAdapter:
    """Stub for the MCode (mmx-cli) adapter."""

    name = "mcode"
    timeout_s = 180

    def run(
        self,
        prompt: str,
        cwd: Path,
        *,
        timeout_s: int | None = None,
    ) -> AgentResult:
        raise NotImplementedError(
            "Paperclip: mcode/mmx-cli adapter pending (Wave N+1 — see specs/M169-paperclip/SPEC.md)"
        )
