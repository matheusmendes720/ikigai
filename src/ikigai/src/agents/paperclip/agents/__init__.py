"""Paperclip agent adapters.

Each AI coding tool Paperclip can route to lives in its own module:

* ``claude.py`` — REAL adapter (subprocess to ``claude`` CLI). MVP.
* ``pi.py``, ``mcode.py``, ``omo.py``, ``hermes.py``, ``openclaw.py`` —
  STUB adapters (raise ``NotImplementedError``); wire them in future waves.

All adapters conform to ``AgentAdapter`` (see ``base.py``). The drift
invariant ``test_paperclip_agents_have_adapters`` (test_paperclip_drift.py)
asserts all 6 files exist + parse to at least one class/function definition.
"""

from __future__ import annotations

from .base import AgentAdapter, AgentResult

__all__ = ["AgentAdapter", "AgentResult"]
