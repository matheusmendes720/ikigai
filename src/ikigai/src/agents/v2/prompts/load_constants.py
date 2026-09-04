"""load_constants — read algorithm tuning values from prompt-template config.

Per ADR-019 (forthcoming, see dcode-harness-TASKS.md W5.2): algorithm
tuning happens ONLY by editing prompts/algorithm_constants.json. This
loader is the single entry point for v2 nodes (observe / balance /
heuristics) to consume those values — there is no other supported path.

Historical context
------------------
Pre-W3.2 (2026-09-03 and earlier), these constants lived in
``src/ikigai/src/agents/v2/state.py`` as module-level Python variables
(``DEFAULT_QHE_PUSH = 0.85``, etc.). They were imported by node modules
and compared inline. Per ADR-013 (canonical-scope-discipline) and the
prompt-chain architecture shipped in Phase 8.2, **no Python DEFAULT_*
constants for algorithm tuning are permitted in the agent layer**. Drift
detector in ``src/ikigai/tests/test_canonical_scope.py`` enforces this.

Why JSON, not YAML / TOML / .py
-------------------------------
JSON is the smallest cross-language format that (a) round-trips cleanly,
(b) is diff-friendly in PRs, and (c) requires zero third-party deps. The
companion human-readable explainer lives at ``prompts/observe.md`` (the
canonical prompt-template document) and references the same values.

API
---
- ``load_algorithm_constants()`` returns the full dict (cached).
- ``get(key)`` returns one constant.
- ``reset_cache()`` clears the LRU cache — only needed in tests that
  mutate the JSON file at runtime.

Example
-------
>>> from agents.v2.prompts.load_constants import get
>>> if q_he >= get("QHE_PUSH_THRESHOLD"):
...     regime = "PUSH"
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CONSTANTS_PATH = Path(__file__).parent / "algorithm_constants.json"


@lru_cache(maxsize=1)
def load_algorithm_constants() -> dict[str, Any]:
    """Load algorithm constants from JSON config (LRU-cached).

    Returns the full dict of tuning values. If the JSON file is missing,
    returns a defensive in-memory default that matches the pre-W3.2 values
    — so tests that mock the file path don't crash, and so a freshly-
    cloned repo without the JSON file still produces deterministic behavior.
    """
    if _CONSTANTS_PATH.exists():
        data = json.loads(_CONSTANTS_PATH.read_text(encoding="utf-8"))
        # Strip the leading "_comment" key (and any future metadata keys
        # starting with "_") before returning so callers only see real
        # constants.
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return _defensive_default()


def get(key: str) -> Any:
    """Convenience accessor for one constant.

    Raises KeyError if the key is missing — fail loud rather than silent.
    """
    return load_algorithm_constants()[key]


def reset_cache() -> None:
    """Clear the LRU cache. Used by tests that mutate algorithm_constants.json
    at runtime and need a clean reload on next access."""
    load_algorithm_constants.cache_clear()


def _defensive_default() -> dict[str, Any]:
    """Pre-W3.2 values, used only when the JSON file is absent."""
    return {
        "QHE_PUSH_THRESHOLD": 0.85,
        "QHE_RECOVER_THRESHOLD": 0.60,
        "WORKLOAD_OVERLOAD_FACTOR": 1.20,
        "WORKLOAD_UNDERLOAD_FACTOR": 0.50,
        "CAPACITY_HOURS_PER_DAY": 8.0,
        "HYSTERESIS_UPGRADE_DAYS": 3,
        "HYSTERESIS_DOWNGRADE_DAYS": 2,
        "REGIME_TARGETS": {
            "PUSH": 0.85,
            "MAINTAIN": 0.65,
            "REDUCE": 0.45,
            "RECOVER": 0.25,
        },
        "HEURISTICS_H2_DEVIATION_WARN": 0.15,
        "HEURISTICS_H2_DEVIATION_CRITICAL": 0.30,
        "HEURISTICS_H3_MAINTAIN_UPGRADE_DAYS": 14,
        "HEURISTICS_H3_PUSH_QHE_THRESHOLD": 0.80,
        "HEURISTICS_H3_PUSH_DOWNGRADE_DAYS": 10,
        "HEURISTICS_H6_SEVERITY_WARN": 0.5,
        "HEURISTICS_H6_SEVERITY_CRITICAL": 1.0,
        # W4.4 — Sub-agent dispatch tuning (ADR-026 S4 + ADR-027 R10).
        # Mirror values from prompts/algorithm_constants.json exactly.
        "SUBAGENT_PARENT_TIMEOUT_S": 60.0,
        "SUBAGENT_MAX_FAN_OUT": 5,
        "SUBAGENT_MAX_DISPATCH_DEPTH": 2,
        "SUBAGENT_CHECKPOINT_KEEP_AFTER_REPLAY": True,
        # W4.5 — Checkpoint retention tuning (ADR-027 R10).
        # Mirror values from prompts/algorithm_constants.json exactly.
        "CHECKPOINT_RETENTION_COUNT": 1000,
        "MAX_CHECKPOINT_AGE_DAYS": 90,
    }
