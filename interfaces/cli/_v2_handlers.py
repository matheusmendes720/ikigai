"""v2 — Handler + factory + vault-root loaders.

Owns lazy imports for:
  - _load_handlers     5-tuple (score_handler, regime_handler,
                       render_score_passion_observation, render_heuristics_
                       regime_observation, render_surface_pav_intentions)
  - _load_graph_factory  make_v2_graph
  - _resolve_vault_root  IKIGAI_VAULT_ROOT env var → Path

The lazy-import pattern is required because the imports under the hood
transitively touch ikigai's v2 namespace package; loading them at v2.py
import-time would re-introduce the legacy `src.ikigai.src.*` import-path
conflict that ADR-013 / Phase 8 work has spent effort avoiding.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `from src.ikigai.src...` resolves.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_handlers():
    """Lazily import handler functions + graph factory + prompt renderers.

    Doing this at module level would cause ImportError if the repo root is not
    yet on sys.path (the CLI runner sets PYTHONPATH but conftest does it too).
    Splitting into a helper lets tests patch sys.path before first call.

    Returns 5-tuple (per v2 architecture per ADR-013):
        (score_handler, regime_handler,
         render_score_passion, render_heuristics_regime, render_surface_pav)

    The graph factory is loaded lazily per-command via `_load_graph_factory()`
    because it transitively imports v2 nodes that use a legacy import path
    (`src.ikigai.src.agents.v2.state`) which conflicts with the v2 namespace
    package layout used by the prompt renderers.

    - score_handler / regime_handler: MCP observation wrappers (legacy fallback,
      may be None if the legacy import path is unavailable in the active venv).
    - render_*: prompt-chain renderers (v2 architecture per Plan §11.4;
      canonical path per ADR-013 planner-only — agent layer must not execute
      math/observation tools directly).
    """
    # v2 prompt-chain renderers (preferred path per ADR-013 planner-only).
    # Imported first because they are the canonical v2 surface.
    from agents.v2.prompts.score_passion_observation import (
        render_score_passion_observation,
    )
    from agents.v2.prompts.heuristics_regime_observation import (
        render_heuristics_regime_observation,
    )
    from agents.v2.prompts.surface_pav_intentions import (
        render_surface_pav_intentions,
    )

    # Legacy MCP observation handlers — imported lazily + tolerantly. These use
    # the `src.ikigai.src.mcp_server.server` import path which conflicts with
    # the v2 namespace package layout (`src.ikigai.src` is a namespace package
    # and `agents.v2.X` requires `src/ikigai/src/` on sys.path). When both
    # cannot coexist, the legacy handlers are simply unavailable and the v2
    # prompt chain stands alone. Per ADR-013 this is the desired state.
    score_handler = None
    regime_handler = None
    try:
        from src.ikigai.src.mcp_server.server import (
            _handle_ikigai_score as _score_handler,
            _handle_ikigai_regime as _regime_handler,
        )

        score_handler = _score_handler
        regime_handler = _regime_handler
    except ImportError:
        # Legacy path not available in this environment — v2 prompt chain is
        # the sole observation surface. This is the expected state post
        # ADR-013 (planner-only).
        pass

    return (
        score_handler,
        regime_handler,
        render_score_passion_observation,
        render_heuristics_regime_observation,
        render_surface_pav_intentions,
    )


def _load_graph_factory():
    """Lazy import of make_v2_graph — separate from _load_handlers.

    The graph factory transitively imports v2 nodes (commit.py, etc.) that
    use the legacy `src.ikigai.src.agents.v2.state` import style which
    conflicts with the v2 namespace package layout. Loading it lazily means
    that commands which don't need the graph (suggest/score/regime) do not
    pay the import cost or trigger the conflict.
    """
    from agents.v2.graph import make_v2_graph

    return make_v2_graph


def _resolve_vault_root() -> Path:
    """Return IKIGAI_VAULT_ROOT env var (if set), else relative `vault/`."""
    env_root = os.environ.get("IKIGAI_VAULT_ROOT")
    if env_root:
        return Path(env_root)
    return Path("vault")
