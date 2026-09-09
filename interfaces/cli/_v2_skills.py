"""_v2_skills — skill dispatch for IKIGAI v2 graph.

Provides:
- load_skill_manifest(name): parse YAML frontmatter from skills/{name}.md
- invoke_skill(skill_name, **kwargs): dispatch make_v2_graph() with entry_point
- ensure_mcp_server_bound(): idempotent production binding
- _manifest_declares_taskdog(outputs): check if outputs list declares taskdog
- _derive_taskdog_title(skill_name, description): compose task name with date

This module is lazy-imported inside v2.py command bodies to break
the circular import (v2.py ↔ agents.v2.subgraph ↔ agents.v2.nodes.proposal_executor).
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Cost guard — per-skill token caps (PROD-3)
# ---------------------------------------------------------------------------
def _get_token_cap(skill_name: str) -> int:
    """Return the max tokens cap for the given skill (env var override).

    Defaults:
      daily    → 1 000 tokens
      weekly   → 8 000 tokens
      monthly  → 32 000 tokens
      quarterly → 96 000 tokens
    """
    defaults = {
        "daily": 1_000,
        "weekly": 8_000,
        "monthly": 32_000,
        "quarterly": 96_000,
    }
    env_keys = {
        "daily": "IKIGAI_MAX_TOKENS_DAILY",
        "weekly": "IKIGAI_MAX_TOKENS_WEEKLY",
        "monthly": "IKIGAI_MAX_TOKENS_MONTHLY",
        "quarterly": "IKIGAI_MAX_TOKENS_QUARTERLY",
    }
    key = env_keys.get(skill_name)
    if key:
        override = os.environ.get(key)
        if override is not None:
            try:
                return int(override)
            except ValueError:
                pass
    return defaults.get(skill_name, 96_000)


# ---------------------------------------------------------------------------
# Rate limiter — simple in-memory token bucket (PROD-3)
# ---------------------------------------------------------------------------
class _RateLimiter:
    """Simple token-bucket rate limiter: max N calls per hour."""

    def __init__(self, max_calls: int = 10, window_s: float = 3600.0):
        self._max_calls = max_calls
        self._window = window_s
        self._calls: list[float] = []

    def acquire(self) -> bool:
        """Return True if under limit; else False. Consumes a token on True."""
        now = time.monotonic()
        # Evict calls outside the window
        self._calls = [t for t in self._calls if now - t < self._window]
        if len(self._calls) >= self._max_calls:
            return False
        self._calls.append(now)
        return True


_rate_limiter: _RateLimiter | None = None


def _get_rate_limiter() -> _RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        max_calls = int(os.environ.get("IKIGAI_RATE_LIMIT", "10"))
        _rate_limiter = _RateLimiter(max_calls=max_calls, window_s=3600.0)
    return _rate_limiter


# ---------------------------------------------------------------------------
# Helper functions (moved from deleted _skill_outputs — PROD-2)
# ---------------------------------------------------------------------------
def _manifest_declares_taskdog(outputs: Any) -> str | None:
    """Return the taskdog description string if outputs declares it, else None.

    Per W3.6: ``outputs: [taskdog_create_task: <description>]`` gates the
    taskdog @tool call in invoke_skill post-processing.
    """
    if not outputs:
        return None
    if isinstance(outputs, list):
        for item in outputs:
            if isinstance(item, str) and item.startswith("taskdog_create_task"):
                # Bare string: "taskdog_create_task" — no description
                return ""
            if isinstance(item, dict):
                if "taskdog_create_task" in item:
                    return str(item["taskdog_create_task"])
        return None
    return None


def _derive_taskdog_title(skill_name: str, description: str) -> str:
    """Compose ``<description> <YYYY-MM-DD>`` or ``<skill_name> <YYYY-MM-DD>``."""
    today = date.today().isoformat()
    if description:
        return f"{description} {today}"
    return f"{skill_name} {today}"


def _repo_root() -> Path:
    """Compute repo root from this file's location (interfaces/cli/_v2_skills.py)."""
    return Path(__file__).resolve().parents[2]


def load_skill_manifest(name: str) -> dict[str, Any]:
    """Parse YAML frontmatter from skills/{name}.md.

    Returns the manifest dict including `entry_point` field.
    Raises FileNotFoundError if the skill file doesn't exist.
    """
    skill_path = (
        _repo_root()
        / "src"
        / "ikigai"
        / "src"
        / "agents"
        / "v2"
        / "skills"
        / f"{name}.md"
    )
    raw = skill_path.read_text(encoding="utf-8")
    # Strip Pandoc-style YAML frontmatter (--- delimiters)
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            parsed = yaml.safe_load(raw[3:end])
            if parsed:
                return dict(parsed)
    return {}


def _build_initial_state(skill_name: str, date_str: str) -> dict[str, Any]:
    """Build a minimal IKIGAiStateDict for the given skill and date."""
    today = date.fromisoformat(date_str) if date_str else date.today()
    return {
        "cycle_id": f"ikigai-{skill_name}-{date_str}",
        "cycle_start": date_str,
        "cycle_end": date_str,
        "iteration": 0,
        "vault_root": "vault",
        "regime_state": "MAINTAIN",
        "q_he_score": 0.65,
        "days_in_regime": 3,
        "is_hysteresis_active": False,
        "phase": "BUSCA",
        "phase_iteration": 0,
        "phase_converged": False,
        "phase_weights": {
            "passion": 0.5,
            "skill": 0.5,
            "market": 0.5,
            "revenue": 0.5,
            "course": 0.5,
        },
        "vector_scores": {
            "passion": 0.7,
            "skill": 0.7,
            "market": 0.6,
            "revenue": 0.6,
            "course": 0.7,
        },
        "meta_vector_score": 0.66,
        "workload_estimate": 4.0,
        "capacity_estimate": 8.0,
        "balancer_verdict": "OK",
    }


def invoke_skill(skill_name: str, date_str: str | None = None) -> dict[str, Any]:
    """Dispatch the v2 graph for the named skill.

    Args:
        skill_name: one of "daily", "weekly", "monthly", "quarterly"
        date_str: YYYY-MM-DD string; defaults to today

    Returns:
        dict with skill name, date, and graph output dict

    Raises:
        RuntimeError: if rate limit (10 calls/hour) is exceeded.
    """
    # PROD-3 rate limit check
    limiter = _get_rate_limiter()
    if not limiter.acquire():
        raise RuntimeError(
            f"Rate limit exceeded for invoke_skill ({limiter._max_calls}/hour). "
            "Set IKIGAI_RATE_LIMIT env var to adjust."
        )

    from src.ikigai.src.agents.v2.graph import make_v2_graph

    manifest = load_skill_manifest(skill_name)
    entry_point: str = manifest.get("entry_point", "observe")
    date_str = date_str or str(date.today())

    # Token cap check (PROD-3): record intent; actual enforcement happens in graph
    token_cap = _get_token_cap(skill_name)

    compiled = make_v2_graph(entry_point=entry_point, max_tokens=token_cap)
    initial_state = _build_initial_state(skill_name, date_str)

    result = compiled.invoke(
        initial_state,
        config={"configurable": {"thread_id": f"{skill_name}-{date_str}"}},
    )

    return_dict: dict[str, Any] = {
        "skill": manifest.get("name", f"ikigai-{skill_name}"),
        "date": date_str,
        entry_point: result,
    }

    # W3.6 post-processing: check manifest outputs for taskdog_create_task gate
    outputs: list[Any] = manifest.get("outputs", []) or []
    taskdog_desc = _manifest_declares_taskdog(outputs)
    if taskdog_desc is not None:
        title = _derive_taskdog_title(skill_name, taskdog_desc)
        try:
            # Import the @tool function (mirrors tools.py canonical path)
            from src.ikigai.src.agents.tools import taskdog_create_task as _td_tool

            result_str = _td_tool.invoke({"name": title})
            return_dict["taskdog_result"] = result_str
        except Exception as exc:  # noqa: BLE001
            # W3.6 partial-success invariant: taskdog failure → review_queue entry
            return_dict["taskdog_pending_review_queue"] = True
            return_dict["taskdog_error"] = str(exc)
            # Enqueue to mesh queue for agent retry
            try:
                from src.mesh.queue import enqueue
                from src.contracts.task_change import TaskChange

                tc = TaskChange(
                    event_id=f"err-{skill_name}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    ueid="tsk:taskdog-review:00000000-0000-0000-0000-000000000000:0000000000000000",
                    action="create",
                    source_fork="taskdog",
                    fields={
                        "target_fork": "taskdog",
                        "error": str(exc),
                        "original_params": {"name": title},
                        "created_at": str(date.today()),
                        "actor": "agent",
                    },
                    timestamp=datetime.now(),
                )
                enqueue(tc)
            except Exception:
                # Queue write failure is non-fatal; flag is already set
                pass

    return return_dict


def ensure_mcp_server_bound() -> None:
    """Idempotently bind the production MCP server to mcp_bridge._server.

    Uses dotted-prefix setter per dual-module-identity bug class.
    Does nothing if _server is already bound.
    """
    # Import inside to avoid activating the subprocess until needed.
    # Note: mcp_client.py exports bind_server_to_gateway (NOT bind_prod_server).
    # mcp_bridge.py re-exports it as bind_prod_server, so we import from
    # mcp_bridge to get the canonical name.
    from src.ikigai.src.agents.v2 import mcp_bridge as _bridge_mod
    from src.ikigai.src.agents.v2 import mcp_client as _mcp_client_mod

    if _bridge_mod._server is not None:
        return  # already bound — idempotent

    # Compute paths for the MCP server subprocess.
    # The module lives at src/ikigai/src/mcp_server/ and uses
    # "from mcp_server.server import main" (relative import in __main__.py).
    # cwd MUST be src/ikigai/src (the INNER src), NOT src/ikigai -- when
    # cwd=src/ikigai, Python prepends '' to sys.path and resolves
    # `import contracts.X` to <repo>/src/ikigai/contracts/ (a stale
    # editable-install shadow) instead of <repo>/src/contracts/.
    # The inner-src layout sidesteps the shadow. Same pattern as
    # scripts/mcp_inspect.py and tests/test_m5_ikigai_mcp_integration.py.
    # PYTHONPATH needs THREE entries (REPO_ROOT + LIFE_SRC + IKIGAI_SRC) to
    # satisfy every import style: dotted-prefix `src.contracts.X`, bare-namespace
    # `contracts.X`, and `python -m mcp_server`.
    worktree_root = str(_repo_root())
    mcp_cwd = str(Path(worktree_root) / "src" / "ikigai" / "src")
    life_src = str(Path(worktree_root) / "src")
    env = dict(os.environ)
    env["PYTHONPATH"] = worktree_root + ";" + life_src + ";" + mcp_cwd

    # bind_server_to_gateway is the factory in mcp_client.py.
    # server_script is the short module name `mcp_server` (relies on cwd=mcp_cwd).
    server = _mcp_client_mod.bind_server_to_gateway(
        "mcp_server", env=env, cwd=mcp_cwd
    )
    # Dotted-prefix setter: assign to the actual module, not a local var
    _bridge_mod._server = server
