"""v2 — Deep Agent / IKIGAI v2 Typer sub-app (W6.X item 2b — slimmed root).

Nine commands per plan §11.4 + Wave 2 W2.3 + Plan D:
  life v2 cycle       — invoke ikigai_maintainer_v2 LangGraph
  life v2 score       — call render_score_passion_observation prompt chain
  life v2 regime      — call render_heuristics_regime_observation prompt chain
  life v2 suggest     — call render_surface_pav_intentions prompt chain (W2.1)
  life v2 daily       — ikigai-daily skill orchestrator (W2.3 / W3.5)
  life v2 weekly      — ikigai-weekly skill orchestrator (W2.3 / W6.X item 2)
  life v2 monthly     — ikigai-monthly skill orchestrator (W2.3 / W6.X item 2)
  life v2 quarterly   — ikigai-quarterly skill orchestrator (W2.3 / W6.X item 2)
  life v2 plan        — meta-planner (Plan D E.1)

Module layout (W6.X item 2b — CLAUDE.md 500-line guideline compliance):
  v2.py              — typer app + re-exports + register_*() calls  (this file)
  _v2_handlers.py    — _load_handlers / _load_graph_factory / _resolve_vault_root
  _v2_primitives.py  — _run_cycle/_run_score/_run_regime/_run_suggest
                       + register_observation(app) → cycle/score/regime/suggest
  _v2_skills.py      — load_skill_manifest / invoke_skill / per-skill orchestrators
  _v2_skill_cmds.py  — register_skill(app) → daily/weekly/monthly/quarterly
  _v2_plan.py        — _run_plan / _format_proposal / register_plan(app)

Re-exports below preserve test import paths (test_v2_cli.py + test_meta_plan_e2e.py
monkeypatch symbols in this module's namespace — `from ._v2_skills import invoke_skill`
etc. must remain at module-level so `monkeypatch.setattr(v2, ..., ...)` works).

Provenance: src/ikigai/src/agents/v2/graph.py  +  mcp_server/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

# Ensure repo root is on sys.path so `from src.ikigai.src...` resolves.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

app = typer.Typer(
    help="IKIGAI v2 commands — cycle, score, regime, suggest, daily, weekly, monthly, quarterly, plan"
)
console = Console()

# ---------------------------------------------------------------------------
# Re-exports — keep test import paths stable (W6.X item 2b)
# ---------------------------------------------------------------------------
# Tests patch these symbols in this module's namespace via
# `monkeypatch.setattr(v2, "_load_handlers", ...)` etc. They MUST live on
# this module. The sub-modules look these names up late-bound through v2's
# namespace at call time so the patches take effect.

from ._v2_handlers import (  # noqa: E402, F401  # re-export — test monkeypatch target
    _load_graph_factory,
    _load_handlers,
    _resolve_vault_root,
)
from ._v2_plan import _run_plan, register_plan  # noqa: E402, F401  # re-export — test import target
from ._v2_primitives import (  # noqa: E402, F401
    _run_cycle,
    _run_regime,
    _run_score,
    _run_suggest,
    register_observation,
)
from ._v2_skill_cmds import register_skill  # noqa: E402, F401
from ._v2_skills import (  # noqa: E402, F401  # re-exports — test monkeypatch targets
    _run_daily,
    _run_monthly,
    _run_quarterly,
    _run_weekly,
    invoke_skill,
    load_skill_manifest,
)

# ---------------------------------------------------------------------------
# Bind 9 typer commands to app (cycle/score/regime/suggest + plan +
# daily/weekly/monthly/quarterly). Kept out of v2.py to honour the
# 500-line guideline; each `register_*` decorator-binds commands onto `app`
# so v2.app retains full sub-app surface.
# ---------------------------------------------------------------------------

register_observation(app, console)
register_skill(app, console)
register_plan(app)


# Public alias so `from interfaces.cli.v2 import v2_app` matches __init__.py usage.
v2_app = app

if __name__ == "__main__":
    app()
