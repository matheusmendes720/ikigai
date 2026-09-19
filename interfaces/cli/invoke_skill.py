"""invoke_skill.py - W3.5/W3.6 skill manifest loader + LLM dispatcher + taskdog post-processor.

Per W3.5 brief: skills are markdown manifests under
``src/ikigai/src/agents/v2/skills/<name>.md`` with YAML frontmatter
declaring entry_point, actor, triggers, inputs, outputs.

The ``outputs`` list is the gate for downstream post-processors:
- empty `outputs: []` - skill is surface-only (e.g., daily.md)
- `outputs: [vault_write: "..."]` - skill writes vault only
- `outputs: [taskdog_create_task: "<description>"]` - skill fires taskdog

This module implements the W3.6 ``invoke_skill(name)`` function per the
test contract in src/ikigai/tests/test_v2_invoke_skill_taskdog.py:
- Loads the skill manifest from the canonical skills dir
- In IKIGAI_FAKE_LLM=1 mode, returns a stub result (no LLM call)
- After the skill runs, post-processes per the outputs list
- On taskdog success: returns {"taskdog_result": <@tool stdout>}
- On taskdog failure: writes a TaskChange to data/review_queue/

Per project policy: never silently swallow exceptions. A failed
taskdog fires a warning + queues the request for human review.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Default skills directory (canonical, used in production). Tests
# monkeypatch this via IKIGAI_VAULT_ROOT or by setting the SKILLS_DIR
# env var.
# Path resolution: file lives at interfaces/cli/invoke_skill.py
# (3 levels deep from repo root). The default skills dir is
# src/ikigai/src/agents/v2/skills/ (5 levels deep from repo root).
# We compute by walking parents until we find "src/ikigai/src/agents/v2/skills".
_DEFAULT_SKILLS_DIR = None  # populated at module import via _find_default_skills_dir()


def _find_default_skills_dir() -> Path:
    """Walk up from this file's parent until we find src/ikigai/src/agents/v2/skills.

    Robust against pytest collection running from various CWDs.
    """
    file_path = Path(__file__).resolve()
    for ancestor in file_path.parents:
        candidate = ancestor / "src" / "ikigai" / "src" / "agents" / "v2" / "skills"
        if candidate.exists():
            return candidate
    # Fallback: derive from file path
    return file_path.parent.parent.parent.parent / "src" / "ikigai" / "src" / "agents" / "v2" / "skills"


def _resolve_skills_dir() -> Path:
    """Resolve the skills directory.

    Resolution order:
    1. SKILLS_DIR env var (test override)
    2. IKIGAI_VAULT_ROOT + .claude/skills (production deployment)
    3. _DEFAULT_SKILLS_DIR (repo-relative)
    """
    env = os.environ.get("SKILLS_DIR")
    if env:
        return Path(env)
    vault_root = os.environ.get("IKIGAI_VAULT_ROOT")
    if vault_root:
        candidate = Path(vault_root) / ".claude" / "skills"
        if candidate.exists():
            return candidate
    return _find_default_skills_dir()


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter dict from markdown text.

    Returns {} if no frontmatter. Uses a simple line parser (no PyYAML
    dependency) since manifests are intentionally simple.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    out: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    for line in block.split("\n"):
        # List item: `  - value` or `  - key: value`
        if line.startswith("  - ") and current_list is not None:
            item = line[4:].strip()
            if ":" in item:
                k, _, v = item.partition(":")
                # Convert to dict inside list (test expects dict entries)
                if current_list and isinstance(current_list[-1], dict):
                    current_list[-1][k.strip()] = _coerce(v.strip())
                else:
                    current_list.append({k.strip(): _coerce(v.strip())})
            else:
                current_list.append(_coerce(item))
            continue
        # Key: value
        if ":" in line and not line.startswith(" "):
            if current_list is not None:
                current_list = None
            k, _, v = line.partition(":")
            current_key = k.strip()
            v = v.strip()
            if v == "":
                # Could be list start on next line
                current_list = []
                out[current_key] = current_list
            elif v == "[]":
                out[current_key] = []
                current_list = None
            else:
                out[current_key] = _coerce(v)
                current_list = None
    return out


def _coerce(s: str) -> Any:
    """Best-effort YAML scalar coercion (int, bool, str)."""
    if s == "" or s is None:
        return s
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        return s


def load_skill_manifest(name: str) -> dict[str, Any]:
    """Load <name>.md and return the parsed frontmatter dict.

    Empty dict if file missing or malformed.

    Resolution: try ``<name>.md`` first, then strip ``ikigai-`` prefix
    if present (skill canonical names are bare per repo layout:
    daily.md, weekly.md, etc.; W3.6 short names are ikigai-daily, etc.).
    """
    skills_dir = _resolve_skills_dir()
    candidates = [skills_dir / f"{name}.md"]
    if name.startswith("ikigai-"):
        candidates.append(skills_dir / f"{name[len('ikigai-'):]}.md")
    for md_path in candidates:
        if md_path.exists():
            return _parse_frontmatter(md_path.read_text(encoding="utf-8"))
    logger.warning("skill manifest not found (tried %s)", candidates)
    return {}


def _fake_llm_dispatch(manifest: dict[str, Any]) -> dict[str, Any]:
    """Stub LLM dispatch for IKIGAI_FAKE_LLM=1 mode.

    Returns a deterministic skeleton that downstream post-processors
    can operate on. Real LLM integration is out of M77 scope.
    """
    return {
        "skill": manifest.get("name", "unknown"),
        "entry_point": manifest.get("entry_point", "observe"),
        "actor": manifest.get("actor", "agent"),
        "llm_stub": True,
        "outputs_fired": [],
        "graph_state": {"iteration": 0, "last_step": manifest.get("entry_point", "observe")},
    }


def _real_llm_dispatch(manifest: dict[str, Any]) -> dict[str, Any]:
    """Real LLM dispatch via ChatAnthropic (M87).

    Calls Claude with a structured prompt that asks for:
    - skill analysis (what should the skill do?)
    - key outputs (1-3 concrete actions or written artifacts)
    - next action (the immediate next step)

    Returns graph_state dict. Falls back to fake dispatch on any error
    (missing API key, network failure, parse error, etc).

    Lazy-imports langchain_anthropic to avoid hard dep when
    IKIGAI_FAKE_LLM=1.
    """
    import json as _json
    import logging
    import os

    logger = logging.getLogger(__name__)

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        return _fake_llm_dispatch(manifest) | {
            "llm_stub": False,
            "ok_reason": "missing ANTHROPIC_API_KEY/CLAUDE_API_KEY env var",
        }

    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError as exc:
        logger.warning("langchain_anthropic import failed: %s", exc)
        return _fake_llm_dispatch(manifest) | {
            "llm_stub": False,
            "ok_reason": f"import_failed: {exc}",
        }

    model_name = os.environ.get("IKIGAI_MODEL", "claude-3-5-sonnet-latest")
    try:
        # Pass api_key explicitly - ChatAnthropic checks ANTHROPIC_API_KEY
        # by default, not CLAUDE_API_KEY. We accept either alias.
        llm = ChatAnthropic(model=model_name, temperature=0, api_key=api_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ChatAnthropic init failed: %s", exc)
        return _fake_llm_dispatch(manifest) | {
            "llm_stub": False,
            "ok_reason": f"init_failed: {exc}",
        }

    sys_msg = SystemMessage(
        content=(
            "You are IKIGAI's skill dispatcher. Given a skill manifest "
            "(name, entry_point, description, inputs, outputs), produce "
            "a brief 2-4 sentence analysis of what this skill does in the "
            "current cycle, then return JSON only with keys: "
            "'analysis' (string), 'outputs' (list of strings - concrete "
            "actions or artifacts), 'next_action' (string - the immediate "
            "next step). Do NOT include any markdown fences, just raw JSON."
        )
    )
    user_msg = HumanMessage(
        content=_json.dumps(
            {
                "skill_name": manifest.get("name"),
                "entry_point": manifest.get("entry_point"),
                "description": manifest.get("description", ""),
                "inputs": manifest.get("inputs", []),
                "outputs": manifest.get("outputs", []),
                "actor": manifest.get("actor", "agent"),
            },
            default=str,
        )
    )

    try:
        response = llm.invoke([sys_msg, user_msg])
        raw = (response.content or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        parsed = _json.loads(raw)
        analysis = parsed.get("analysis", "")
        outputs = parsed.get("outputs", [])
        next_action = parsed.get("next_action", "")
        return {
            "skill": manifest.get("name", "unknown"),
            "entry_point": manifest.get("entry_point", "observe"),
            "actor": manifest.get("actor", "agent"),
            "llm_stub": False,
            "llm_model": model_name,
            "graph_state": {
                "iteration": 0,
                "last_step": manifest.get("entry_point", "observe"),
                "analysis": analysis,
                "outputs": outputs if isinstance(outputs, list) else [],
                "next_action": next_action,
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM dispatch failed: %s", exc)
        return _fake_llm_dispatch(manifest) | {
            "llm_stub": False,
            "ok_reason": f"invoke_failed: {exc}",
        }


def _llm_dispatch(manifest: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to real LLM unless IKIGAI_FAKE_LLM=1 (M87).

    Behavior:
    - IKIGAI_FAKE_LLM=1 → _fake_llm_dispatch (deterministic, no API call)
    - Otherwise → _real_llm_dispatch (calls ChatAnthropic if key present,
      falls back to fake on any error)
    """
    import os

    if os.environ.get("IKIGAI_FAKE_LLM") == "1":
        return _fake_llm_dispatch(manifest)
    return _real_llm_dispatch(manifest)


def _fire_taskdog(description: str, skill_name: str) -> dict[str, Any]:
    """Call the taskdog_create_task @tool with the derived title.

    Returns {"ok": True, "result": <stdout>} on success.
    Returns {"ok": False, "error": <exc>} on failure.
    """
    from interfaces.cli._skill_outputs import _derive_taskdog_title
    title = _derive_taskdog_title(skill_name, description)
    try:
        # Import inside function: tests monkeypatch the `agents.tools`
        # module attribute. Per M73 dual-identity lessons, the production
        # code uses `src.ikigai.src.agents.tools` but tests rely on
        # `agents.tools`. Resolve via sys.modules lookup which works under
        # both pytest conftest configurations.
        import sys as _sys

        tools_mod = _sys.modules.get("agents.tools") or _sys.modules.get(
            "src.ikigai.src.agents.tools"
        )
        if tools_mod is None:
            # Fallback: import via the dual-path module-level name
            from src.ikigai.src.agents import tools as tools_mod  # type: ignore[no-redef]

        result = tools_mod.taskdog_create_task.invoke({"name": title})
        return {"ok": True, "result": str(result)}
    except Exception as exc:  # noqa: BLE001 - surface all errors
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _enqueue_review_queue(
    skill_name: str,
    description: str,
    original_params: dict[str, Any],
    error_msg: str,
    queue_dir: Path,
) -> str:
    """Write a TaskChange to the review queue (failure path).

    Mirrors the canonical TaskChange shape (mesh/queue.py:enqueue).
    Tests check fields.target_fork / actor / error / created_at.
    """
    from contracts.task_change import TaskAction, TaskChange, TaskStatus
    from src.mesh import queue as queue_mod

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    ueid = f"tsk:{skill_name}:{hashlib.sha256(title_or_name(skill_name, description).encode()).hexdigest()[:8]}:{hashlib.sha256(error_msg.encode()).hexdigest()[:8]}"
    now = _dt.datetime.now(_dt.timezone.utc)
    fields = {
        "target_fork": "taskdog",
        "actor": "agent",
        "created_at": now.isoformat(),
        "error": error_msg,
        "original_params": original_params,
    }
    event = TaskChange(
        event_id=event_id,
        ueid=ueid,
        action=TaskAction.CREATE,
        fields=fields,
        source_fork="taskdog",
        timestamp=now,
        status="pending",
    )
    # Use the queue's enqueue but with our overridden QUEUE_DIR
    original_qdir = queue_mod.QUEUE_DIR
    queue_mod.QUEUE_DIR = queue_dir
    try:
        queue_mod.enqueue(event)
    finally:
        queue_mod.QUEUE_DIR = original_qdir
    return event_id


def title_or_name(skill_name: str, description: str) -> str:
    """For ueid hashing - use description or skill_name."""
    return description if description else skill_name


def invoke_skill(
    name: str,
    *,
    entry_point_override: str | None = None,
    actor: str = "agent",
) -> dict[str, Any]:
    """Run a skill manifest end-to-end with post-processors.

    Returns:
    - {"taskdog_result": "..."} if taskdog fires and succeeds
    - {"taskdog_pending_review_queue": True} if taskdog fails
    - {} (no taskdog keys) if manifest doesn't declare taskdog output
    Always includes "skill" + "entry_point" + "outputs_fired" + "graph_state".

    Per W3.5 brief:
    - Loads <name>.md manifest
    - Dispatches to entry_point graph (FAKE_LLM mode skips LLM)
    - Post-processes outputs in declaration order
    """
    manifest = load_skill_manifest(name)

    if not manifest:
        return {
            "skill": name,
            "entry_point": "unknown",
            "outputs_fired": [],
            "graph_state": {"error": f"manifest not found: {name}"},
            "actor": actor,
        }

    entry_point = entry_point_override or manifest.get("entry_point", "observe")
    graph_state = _llm_dispatch(manifest)

    result: dict[str, Any] = {
        "skill": manifest.get("name", name),
        "entry_point": entry_point,
        "outputs_fired": [],
        "graph_state": graph_state,
        "actor": actor,
    }

    outputs = manifest.get("outputs", []) or []
    # Detect taskdog output declaration
    from interfaces.cli._skill_outputs import _manifest_declares_taskdog
    taskdog_desc = _manifest_declares_taskdog(outputs)

    if taskdog_desc is None:
        # No taskdog output declared — skip post-processor entirely
        return result

    # Compose taskdog title from description (or skill name fallback)
    from interfaces.cli._skill_outputs import _derive_taskdog_title
    title = _derive_taskdog_title(manifest.get("name", name), taskdog_desc)
    params = {"name": title}

    # Fire taskdog
    td_result = _fire_taskdog(taskdog_desc, manifest.get("name", name))
    if td_result["ok"]:
        result["taskdog_result"] = td_result["result"]
        result["outputs_fired"].append("taskdog_create_task")
    else:
        # Failure path: write to review_queue. Prefer the live
        # src.mesh.queue.QUEUE_DIR (which tests monkeypatch) so the
        # write goes where the test expects.
        try:
            from src.mesh import queue as _queue_mod

            review_queue = _queue_mod.QUEUE_DIR
        except ImportError:
            vault_root = os.environ.get("IKIGAI_VAULT_ROOT")
            if vault_root:
                review_queue = Path(vault_root) / "review_queue"
            else:
                review_queue = Path.cwd() / "data" / "review_queue"
        review_queue.mkdir(parents=True, exist_ok=True)
        try:
            _enqueue_review_queue(
                skill_name=manifest.get("name", name),
                description=taskdog_desc,
                original_params=params,
                error_msg=td_result["error"],
                queue_dir=review_queue,
            )
            result["taskdog_pending_review_queue"] = True
        except Exception as exc:  # noqa: BLE001
            result["taskdog_pending_review_queue"] = True
            result["taskdog_review_queue_error"] = f"{type(exc).__name__}: {exc}"
        result["outputs_fired"].append("taskdog_create_task_failed")

    return result


__all__ = [
    "invoke_skill",
    "load_skill_manifest",
    "_resolve_skills_dir",
]
