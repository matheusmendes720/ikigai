"""taskdog MCP graph — exposes all 12 taskdog tools via LangGraph dev.

M150: Refactored to be **fully sync** (no asyncio.run) so it works inside
langgraph_api's event loop without RuntimeError. Uses the existing
`.claude/loop/mcp_bridge.py` directly as the tool source — no need for
the `taskdog-mcp` subprocess or HTTP daemon.

Per the langgraph.json contract:
    "ikigai_taskdog_mcp": "./src/ikigai/src/agents/taskdog_mcp_graph.py:make_taskdog_mcp_graph_sync"

Usage:
    - Start `langgraph dev` → open Studio UI → pick "ikigai_taskdog_mcp"
      from the assistants dropdown (or call /threads/{id}/runs/stream via API)
    - Send any natural-language request like "list pending tasks",
      "create a task called X with priority 5", etc.
    - The ReAct agent picks the right MCP tool and calls it.

History:
    M105 original used MultiServerMCPClient + asyncio.run — broke under
    langgraph_api (RuntimeError: asyncio.run() cannot be called from a
    running event loop). M150 switched to direct mcp_bridge import +
    LangChain StructuredTool wrapping the sync Python wrappers.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)


def _allow_blocking_active() -> bool:
    """True iff dev binding should be active.

    OPEN-1 fix (2026-10-02): prefer ``--allow-blocking`` in ``sys.argv``
    (set by ``langgraph dev --allow-blocking``) so the auto-bind happens
    whenever the langgraph dev CLI is invoked in blocking-tolerant mode,
    without requiring the operator to also set ``IKIGAI_TASKDOG_FULL_BRIDGE``.

    Falls back to the legacy env var for callers that set it explicitly
    (e.g. CI smoke tests, manual boots).
    """
    if "--allow-blocking" in sys.argv:
        return True
    return os.environ.get("IKIGAI_TASKDOG_FULL_BRIDGE", "").lower() in ("1", "true", "yes")


# M150: pre-compute the bridge path at module-import time (NOT inside the
# ASGI event loop, so blocking-safe). langgraph_api loads this module via
# `importlib.util.spec_from_file_location(..., spec.path)` where
# `spec.path` is the RELATIVE path from langgraph.json
# (e.g. `./src/ikigai/src/agents/taskdog_mcp_graph.py`). The naive
# rsplit-on-separator approach landed at `C:\Users\.claude/...` (home dir)
# because relative __file__ + the literal `/.claude/...` suffix resolve
# against cwd — which on Windows is the user's home, not the workspace.
#
# Fix: use os.path.abspath() (resolves relative paths against cwd) then
# walk 5 levels up with os.path.dirname(). cwd is read once at module
# import time (blocking-safe — this runs before the event loop starts).
import os as _os_for_path
_FILE_ABS = _os_for_path.path.abspath(__file__)  # absolute path to this .py
# Walk 4 levels up from this file: agents -> src -> ikigai -> src -> life (workspace root)
_DIR = _os_for_path.path.dirname(_FILE_ABS)
for _ in range(4):
    _DIR = _os_for_path.path.dirname(_DIR)
_BRIDGE_PATH = _os_for_path.path.join(_DIR, ".claude", "loop", "mcp_bridge.py")


def _placeholder_graph(reason: str) -> Any:
    """Return a minimal graph that reports why the real graph couldn't load.

    Used when ANTHROPIC_API_KEY isn't set or bridge is not bound.
    """
    from langgraph.graph import END, START, StateGraph

    def _report(state: dict) -> dict:
        return {"messages": [{"role": "assistant", "content": (
            f"⚠️ taskdog-mcp graph unavailable: {reason}\n\n"
            "Fix:\n"
            "  1. Set ANTHROPIC_API_KEY (or MINIMAX_API_KEY) in .env\n"
            "  2. Make sure .claude/loop/mcp_bridge.py is importable\n"
            "  3. Restart `langgraph dev`"
        )}]}

    builder = StateGraph(dict)
    builder.add_node("report", _report)
    builder.add_edge(START, "report")
    builder.add_edge("report", END)
    return builder.compile()


def _build_lc_tools() -> list[Any]:
    """Build LangChain tools from mcp_bridge.taskdog_* wrappers.

    M150: instead of using the async MultiServerMCPClient + subprocess
    `taskdog-mcp`, we directly wrap the sync Python wrappers from
    `.claude/loop/mcp_bridge.py`. This avoids the asyncio.run() call
    and works inside langgraph_api's event loop.

    2026-09-29: bind `_server` to our _DirectTaskdogServer after loading
    the bridge module so the ReAct agent's tool calls have a real backend
    (replaces M146 production binding — direct SQLite adapter, no daemon).

    Returns:
        List of LangChain StructuredTool instances, one per taskdog_*
        wrapper, or empty list if bridge can't be imported.
    """
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as e:
        logger.warning("langchain_core not available: %s", e)
        return []

    # Locate the bridge module. M147 added `_get_mcp_bridge()` for
    # cross-alias resolution but that's in mcp_runtime, not here.
    # We import the file directly via importlib since it's not a package.
    import importlib.util
    import sys as _sys

    bridge_path = _BRIDGE_PATH
    # Register under a stable name in sys.modules so any subsequent
    # importlib.util.spec_from_file_location call returns the SAME module
    # object (otherwise _DirectTaskdogServer binding would be lost).
    bridge_modname = "loop_mcp_bridge"
    spec = importlib.util.spec_from_file_location(bridge_modname, bridge_path)
    bridge = importlib.util.module_from_spec(spec)
    _sys.modules[bridge_modname] = bridge  # pin before exec_module
    spec.loader.exec_module(bridge)

    # 2026-09-29: bind _server to our direct adapter-backed implementation
    # so the ReAct agent's tool calls (taskdog_list etc.) have a real backend.
    if getattr(bridge, "_server", None) is None:
        bridge._server = _DirectTaskdogServer()

    # Enumerate taskdog_* wrappers
    tools: list[Any] = []
    for name in sorted(dir(bridge)):
        if not name.startswith("taskdog_"):
            continue
        func = getattr(bridge, name, None)
        if not callable(func):
            continue
        # Build a StructuredTool. The wrapper signature has kwargs that
        # vary per tool; StructuredTool introspects the func.
        try:
            tool = StructuredTool.from_function(
                func=func,
                name=name,
                description=(
                    f"taskdog operation `{name}` from the Life-OSS mesh. "
                    f"See mcp_bridge.py docstring for argument details."
                ),
            )
            tools.append(tool)
        except Exception as e:
            logger.warning("failed to wrap %s as LC tool: %s", name, e)

    # M50-ultracode: append ikigai_read_vault + ikigai_write_vault so the
    # ReAct agent can round-trip the vault (read context, write notes).
    # Both are already LangChain @tool-decorated StructuredTools in
    # src/ikigai/src/agents/{ikigai_read_vault,ikigai_write_vault}.py —
    # import the module objects (NOT the bare tool) so we get the
    # StructuredTool instance with the @tool-decorated signature.
    try:
        from src.ikigai.src.agents.ikigai_read_vault import (
            ikigai_read_vault as _lc_ikigai_read_vault,
        )
        from src.ikigai.src.agents.ikigai_write_vault import (
            ikigai_write_vault as _lc_ikigai_write_vault,
        )
        for _lc_tool in (_lc_ikigai_read_vault, _lc_ikigai_write_vault):
            if _lc_tool is not None:
                tools.append(_lc_tool)
    except Exception as e:
        logger.warning("failed to import ikigai_read_vault / ikigai_write_vault: %s", e)

    return tools


def _build_agent() -> Any:
    """Build the ReAct agent with taskdog tools. Returns a compiled graph.

    Returns placeholder if ANTHROPIC_API_KEY isn't set OR if
    langchain_anthropic has a broken install (M157: catches
    AttributeError too, e.g. when anthropic SDK is too new and
    no longer has OverloadedError that langchain_anthropic expects).
    """
    try:
        from langchain_anthropic import ChatAnthropic
        from langgraph.prebuilt import create_react_agent
    except (ImportError, AttributeError) as e:
        # M157: langchain_anthropic import can fail with AttributeError
        # when anthropic SDK version is incompatible.
        return _placeholder_graph(f"missing or broken deps: {e}")

    api_key = (
        os.environ.get("MINIMAX_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("CLAUDE_API_KEY")
        or ""
    )
    if not api_key:
        return _placeholder_graph("no API key set (MINIMAX_API_KEY / ANTHROPIC_API_KEY / CLAUDE_API_KEY)")

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
    model_name = os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7-highspeed")

    llm = ChatAnthropic(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        default_headers={"x-api-key": api_key},
    )

    tools = _build_lc_tools()
    if not tools:
        return _placeholder_graph("no taskdog tools loaded (bridge not importable or empty)")

    agent = create_react_agent(
        llm,
        tools=tools,
        name="ikigai-taskdog",
        prompt=(
            "You are a task management assistant. You have access to 12 taskdog "
            "tools for creating, listing, updating, completing, and managing "
            "tasks via the Life-OSS mesh. Use them to fulfill the user's "
            "request. When done, summarize the result clearly in pt-BR."
        ),
    )
    return agent


# ---------------------------------------------------------------------------
# LangGraph-API-compatible sync factory. M150: fully sync, no asyncio.run.
# ---------------------------------------------------------------------------
# DirectTaskdogServer — minimal server handle bound to .claude/loop/mcp_bridge.
#
# 2026-09-29: replaces M146 (production binding). Talks straight to our
# TaskdogAdapter (SQLite canonical store) — no daemon, no subprocess.
# Implements the .call(tool_name, args) protocol that mcp_bridge._call expects.
# Binds mcp_bridge._server at import time when env says so.
# ---------------------------------------------------------------------------
class _DirectTaskdogServer:
    """Server stub: forwards taskdog_* → tuples in session-state, real to TaskdogAdapter."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._adapter: Any = None

    def _get_adapter(self) -> Any:
        if self._adapter is None:
            # 2026-09-29: ensure src/ is on sys.path so 'contracts' package
            # resolves when langgraph spawns this module without PYTHONPATH.
            import sys as _sys
            import pathlib as _pathlib
            # file: src/ikigai/src/agents/taskdog_mcp_graph.py
            # parents[3] = .../src
            _src = str(_pathlib.Path(__file__).resolve().parents[3])
            if _src not in _sys.path:
                _sys.path.insert(0, _src)
            from src.mesh.adapters.taskdog import TaskdogAdapter  # noqa: E402
            self._adapter = TaskdogAdapter()
        return self._adapter

    def call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, args))
        try:
            if tool_name == "taskdog_list":
                rows = self._get_adapter().list_all()
                status = (args.get("status") or "").lower() or None
                limit = args.get("limit")
                if status:
                    rows = [r for r in rows if (r.get("status") or "").lower() == status]
                if isinstance(limit, int):
                    rows = rows[:limit]
                return {"ok": True, "tasks": rows, "count": len(rows)}
            if tool_name == "taskdog_read":
                from contracts.common import UEID  # noqa: E402
                ueid = UEID(args["ueid"])
                row = self._get_adapter().read(ueid)
                return {"ok": row is not None, "task": row}
            if tool_name == "taskdog_create":
                # Hand-off to mesh review queue (canonical write path per ADR-014)
                from src.mesh.queue import enqueue_change  # type: ignore  # noqa: E402
                from contracts.task_change import TaskChange, TaskAction  # type: ignore
                ch = TaskChange(
                    ueid=args["ueid"],
                    action=TaskAction.CREATE,
                    fields=args.get("fields", {}),
                )
                enqueue_change(ch)
                return {"ok": True, "queued": True, "ueid": args["ueid"]}
            if tool_name == "taskdog_supports_field":
                return {"ok": True, "supported": self._get_adapter().supports_field(args["field_name"])}
            # Everything else (vault_*, ikigai_*, investigation_*) → not implemented yet
            raise KeyError(f"_DirectTaskdogServer: tool {tool_name!r} not implemented in dev binding")
        except KeyError:
            raise
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _bind_mcp_bridge_server() -> None:
    """Bind mcp_bridge._server to _DirectTaskdogServer. Idempotent.

    OPEN-1 fix (2026-10-02): bind at module-load when ``--allow-blocking``
    is in ``sys.argv`` (the canonical flag passed by ``langgraph dev``)
    OR when ``IKIGAI_TASKDOG_FULL_BRIDGE`` is set (legacy env path).

    The loaded bridge module is pinned in ``sys.modules`` under the SAME
    name used by ``_build_lc_tools`` (``"loop_mcp_bridge"``) so a later
    ``_build_lc_tools`` call returns the SAME module object — without
    this, ``bridge._server = _DirectTaskdogServer()`` would mutate a
    throwaway module that no production caller ever sees (dual-module
    identity bug pattern, see CLAUDE.md "Import-Path Rules").
    """
    if not _allow_blocking_active():
        return
    try:
        import importlib.util as _ilu  # noqa: E402
        # Must match the name in _build_lc_tools so sys.modules de-dupes.
        bridge_modname = "loop_mcp_bridge"
        spec = _ilu.spec_from_file_location(bridge_modname, _BRIDGE_PATH)
        bridge = _ilu.module_from_spec(spec) if spec and spec.loader else None
        if not bridge:
            return
        # Register in sys.modules BEFORE exec_module so the module
        # object is the one production callers will import (avoids
        # dual-module identity split).
        sys.modules[bridge_modname] = bridge
        spec.loader.exec_module(bridge)
        # One-shot: never overwrite an already-bound server (tests
        # monkeypatch bridge._server to a MagicMock per the FakeMcpServer
        # pattern in mcp_bridge.py docstring).
        if getattr(bridge, "_server", None) is None:
            bridge._server = _DirectTaskdogServer()
    except Exception as exc:  # noqa: BLE001
        if os.environ.get("IKIGAI_DEBUG"):
            print(f"[taskdog_mcp_graph] bind failed: {exc}")


_bind_mcp_bridge_server()


# ---------------------------------------------------------------------------
try:
    from langgraph_sdk.runtime import ServerRuntime as _ServerRuntime  # noqa: E402
    from langgraph_sdk.schema import Config as _RunnableConfig  # noqa: E402
except ImportError:
    _ServerRuntime = None  # type: ignore[assignment]
    _RunnableConfig = None  # type: ignore[assignment]


def make_taskdog_mcp_graph_sync(  # type: ignore[no-redef]
    runtime: "_ServerRuntime | None" = None,
    config: "_RunnableConfig | None" = None,
) -> Any:
    """Sync factory for langgraph_api. No asyncio.run() — works inside event loop.

    Per M150: previously this called asyncio.run() to wrap the async
    make_taskdog_mcp_graph(), which broke under langgraph_api because
    the event loop is already running. The sync factory builds the agent
    directly. The bridge import (which involves Path operations + reads)
    is also blocking under the ASGI loop, so we use the
    placeholder graph by default; for full bridge tools, pass the
    `__experimental_allow_blocking=True` config flag and run with
    `langgraph dev --allow-blocking`.
    """
    # Default to placeholder graph to avoid BlockingError under the
    # ASGI event loop. Users who need the full taskdog toolset should
    # run with --allow-blocking (dev-only).
    return _build_agent() if _ALLOW_BLOCKING else _placeholder_graph(
        "ikigai-taskdog graph requires --allow-blocking on `langgraph dev`. "
        "Restart with: langgraph dev --allow-blocking --port 2027"
    )


# Module-level toggle: set to True by user via env var to enable the
# full bridge-backed agent. Default False to avoid BlockingError.
#
# 2026-09-29: langgraph dev does NOT auto-load .env in local mode (only
# for docker-compose). The chat appeared "disabled" because MINIMAX_API_KEY
# + IKIGAI_TASKDOG_FULL_BRIDGE were never reaching os.environ when the
# process was spawned by the bg-watcher. Auto-load .env from CWD on import
# so any caller (watcher, manual, future boots) gets the keys.
import os as _os

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()  # idempotent: leaves process.env intact if already set
except ImportError:
    pass  # python-dotenv not installed — fall back to process.env only

_ALLOW_BLOCKING = _allow_blocking_active()
