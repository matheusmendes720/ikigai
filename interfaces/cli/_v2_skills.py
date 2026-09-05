"""v2 — Skill manifest loader + invoke_skill() + per-skill orchestrators.

Owns:
  - load_skill_manifest(skill_name) → frontmatter dict
  - invoke_skill(skill_name, entry_point_override=None) → graph result
  - _run_daily/_run_weekly/_run_monthly/_run_quarterly(date_str) → skill dict

Per ADR-025 §"Loader rule": skill frontmatter is the canonical binding
(entry_point, actor, outputs). The skill files (src/ikigai/src/agents/v2/
skills/*.md) declare `entry_point:` (which LangGraph node to start from) and
`outputs:` (which side-effect tools the post-processor should fire).

Per W3.6 / W6.X item 2: the per-skill orchestrators used to call prompt-chain
primitives directly. After W6.X they route through invoke_skill() so the
post-processor (skill_outputs) can fire declared outputs (vault_write,
taskdog_create_task) AFTER the graph returns.

Late-binding note: tests patch `interfaces.cli.v2.invoke_skill`. Both this
module and `_v2_plan._run_plan` look up invoke_skill via the v2 module at
call time so the patches take effect.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import yaml

# Ensure repo root is on sys.path so `from agents.v2.X` resolves.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

log = logging.getLogger(__name__)

_SKILLS_DIR = _REPO_ROOT / "src" / "ikigai" / "src" / "agents" / "v2" / "skills"


def load_skill_manifest(skill_name: str) -> dict:
    """Parse YAML frontmatter from <skills_dir>/<skill_name>.md.

    Per ADR-025 §"Loader rule": frontmatter is the canonical skill binding.
    skill_name is the full name (e.g. "ikigai-daily") but the file is
    named "daily.md" — this function strips the "ikigai-" prefix to find
    the actual file.
    Raises FileNotFoundError if the skill file is missing.
    """
    # Strip "ikigai-" prefix — file is named daily.md not ikigai-daily.md
    file_name = skill_name
    if skill_name.startswith("ikigai-"):
        file_name = skill_name[len("ikigai-") :]
    skill_file = _SKILLS_DIR / f"{file_name}.md"
    content = skill_file.read_text(encoding="utf-8")

    # Extract YAML block between first `---` markers
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        raise ValueError(f"Skill {skill_name!r}: no YAML frontmatter found")
    manifest = yaml.safe_load(m.group(1))
    if not isinstance(manifest, dict):
        raise ValueError(f"Skill {skill_name!r}: frontmatter is not a YAML dict")
    return manifest


def invoke_skill(
    skill_name: str,
    entry_point_override: str | None = None,
) -> dict:
    """Load skill manifest and invoke make_v2_graph(entry_point=entry_point).

    Per ADR-025 §"Loader rule": reads skill .md frontmatter for entry_point
    and actor, then calls make_v2_graph().invoke(initial_state).

    entry_point_override is used for testing/edge cases; if it differs from
    the manifest's entry_point, a warning is logged (per ADR-025 R5).

    W3.6 post-processor: AFTER the graph returns, the manifest's `outputs`
    list is consulted by ``post_process_skill_outputs`` (see
    ``_skill_outputs.py``). Skills declaring ``taskdog_create_task`` trigger
    the existing ``taskdog_create_task`` @tool (Path-1 canonical harness,
    src/ikigai/src/agents/tools.py:423). On success the graph result is
    extended with ``taskdog_result``; on failure a TaskChange is enqueued to
    ``data/review_queue/`` and ``taskdog_pending_review_queue: True`` is
    added. Per ADR-013 the graph itself stays pure — orchestration lives in
    the CLI.
    """
    manifest = load_skill_manifest(skill_name)
    entry_point = manifest.get("entry_point")
    if entry_point_override is None:
        pass  # use manifest value
    elif entry_point_override != entry_point:
        log.warning(
            f"Skill {skill_name!r} entry_point override: "
            f"manifest={entry_point!r}, caller={entry_point_override!r}"
        )
        entry_point = entry_point_override
    else:
        entry_point = entry_point_override

    # Late-bind through v2's namespace so monkeypatch.setattr(v2, ...) works
    # in tests (test_v2_cli.test_v2_daily_routes_to_suggest etc.).
    from . import v2 as _v2_mod

    from agents.v2.graph import NODES

    if entry_point not in NODES:
        raise ValueError(f"Invalid entry_point {entry_point!r}; must be in {NODES}")

    make_v2_graph = _v2_mod._load_graph_factory()
    graph = make_v2_graph(entry_point=entry_point)
    config = {"configurable": {"thread_id": f"skill-{skill_name}"}}
    initial_state = {
        "vault_root": str(_v2_mod._resolve_vault_root()),
        "last_step": "invoke_skill",
    }
    graph_result = graph.invoke(initial_state, config)

    # W3.6 — post-processor: fire taskdog_create_task if manifest declares it.
    # The manifest's `outputs` list is the single source of truth for which
    # side-effect tools a skill invokes. Surface-only skills (daily) have
    # outputs=[] and short-circuit here.
    from ._skill_outputs import post_process_skill_outputs

    return post_process_skill_outputs(skill_name, manifest, graph_result)


# ---------------------------------------------------------------------------
# Per-skill orchestrators — W2.3 / W6.X item 2
# ---------------------------------------------------------------------------
# Each per-skill command routes through invoke_skill() (NOT the legacy primitives
# _run_score/_run_regime directly). This unifies the daily/weekly/monthly/
# quarterly path with the post-processor that fires declared outputs.
#
# Strictly read-only on vault/ (per ADR-012 + skill frontmatter constraints):
#   - Writes go through `vault_write` MCP tool (which the v2 graph calls in its
#     `commit` node). The per-skill commands themselves NEVER call vault_write.
#   - These commands ORCHESTRATE — they do NOT execute math (per ADR-013).


def _run_daily(date_str: str) -> dict:
    """Run ikigai-daily skill via invoke_skill().

    Per W3.5 + ADR-025: wires `daily` command to
    make_v2_graph(entry_point="surface_intentions") via the invoke_skill()
    helper. daily.md is surface-only (no vault_write, no taskdog).

    Transforms graph result to the format expected by the Typer command:
    graph result -> {"skill": "...", "date": "...", "surface": {"suggestions": [...], ...}}
    """
    from . import v2 as _v2_mod

    graph_result = _v2_mod.invoke_skill("ikigai-daily")
    return {
        "skill": "ikigai-daily",
        "date": date_str,
        "surface": {
            "suggestions": graph_result.get("user_suggestions", []),
            "language": graph_result.get("suggestions_language", "pt-BR"),
        },
    }


def _run_weekly(date_str: str) -> dict:
    """Run ikigai-weekly skill via invoke_skill().

    Per W6.X item 2: wires `weekly` command to
    make_v2_graph(entry_point="observe") via the invoke_skill()
    helper. Weekly.md declares outputs=[vault_write, taskdog_create_task].

    Transforms graph result to the format expected by the Typer command:
    graph result -> {"skill": "...", "date": "...", "score": {...}, "regime": {...}}
    """
    from . import v2 as _v2_mod

    graph_result = _v2_mod.invoke_skill("ikigai-weekly")
    return {
        "skill": "ikigai-weekly",
        "date": date_str,
        "score": graph_result.get("score", {}),
        "regime": graph_result.get("regime", {}),
    }


def _run_monthly(date_str: str) -> dict:
    """Run ikigai-monthly skill via invoke_skill().

    Per W6.X item 2: wires `monthly` command to
    make_v2_graph(entry_point="observe") via the invoke_skill()
    helper. Monthly.md declares outputs=[vault_write].

    Transforms graph result to the format expected by the Typer command:
    graph result -> {"skill": "...", "date": "...", "cycle": {...}, "score": {...}, "regime": {...}}
    """
    from . import v2 as _v2_mod

    graph_result = _v2_mod.invoke_skill("ikigai-monthly")
    return {
        "skill": "ikigai-monthly",
        "date": date_str,
        "cycle": graph_result.get("cycle", {}),
        "score": graph_result.get("score", {}),
        "regime": graph_result.get("regime", {}),
    }


def _run_quarterly(date_str: str) -> dict:
    """Run ikigai-quarterly skill via invoke_skill().

    Per W6.X item 2: wires `quarterly` command to
    make_v2_graph(entry_point="observe") via the invoke_skill()
    helper. Quarterly.md declares outputs=[vault_write, taskdog_create_task].

    Transforms graph result to the format expected by the Typer command:
    graph result -> {"skill": "...", "date": "...", "cycle": {...}, "score": {...}, "regime": {...}}
    """
    from . import v2 as _v2_mod

    graph_result = _v2_mod.invoke_skill("ikigai-quarterly")
    return {
        "skill": "ikigai-quarterly",
        "date": date_str,
        "cycle": graph_result.get("cycle", {}),
        "score": graph_result.get("score", {}),
        "regime": graph_result.get("regime", {}),
    }
