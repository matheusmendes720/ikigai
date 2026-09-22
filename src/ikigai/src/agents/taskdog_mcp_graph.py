"""taskdog MCP graph — exposes all 26 taskdog tools via LangGraph dev.

M105: This graph lets the visual debugger (Studio UI) at port 2024
invoke any of the 26 taskdog-mcp tools. It's a ReAct agent — the LLM
decides which tool to call based on the user's request.

Per the langgraph.json contract:
    "ikigai_taskdog": "./src/ikigai/src/agents/taskdog_mcp_graph.py:make_taskdog_mcp_graph"

Usage:
    - Start `langgraph dev` → open Studio UI → pick "ikigai_taskdog"
      from the assistants dropdown
    - Send any natural-language request like "list pending tasks",
      "create a task called X with priority 5", etc.
    - The ReAct agent picks the right MCP tool and calls it.

Note: This graph requires taskdog-server running at http://127.0.0.1:8000
and taskdog-mcp installed. If either is missing, returns a placeholder
graph with a single message node that explains the setup requirement.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def make_taskdog_mcp_graph() -> Any:  # noqa: D401
    """LangGraph-API-compatible factory (async signature).

    Per M105: wraps all 26 taskdog-mcp tools in a ReAct agent so the
    visual debugger can invoke them via natural language.

    Returns:
        Compiled StateGraph with taskdog tools bound.
    """
    # Lazy import so the langgraph-api loader doesn't crash on missing deps.
    try:
        from langchain_anthropic import ChatAnthropic
        from langgraph.prebuilt import create_react_agent
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as e:
        logger.warning("taskdog_mcp_graph dependencies missing: %s", e)
        return _placeholder_graph(f"missing deps: {e}")

    # Detect API key (same chain as deepagents_harness.py M104).
    api_key = (
        os.environ.get("MINIMAX_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("CLAUDE_API_KEY")
        or ""
    )
    if not api_key:
        return _placeholder_graph("no API key set (MINIMAX_API_KEY / ANTHROPIC_API_KEY / CLAUDE_API_KEY)")

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
    if (
        not os.environ.get("MINIMAX_API_KEY")
        and not os.environ.get("ANTHROPIC_API_KEY")
        and os.environ.get("CLAUDE_API_KEY")
        and not os.environ.get("ANTHROPIC_BASE_URL")
    ):
        base_url = "http://127.0.0.1:8045/v1"
    model_name = os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7-highspeed")

    llm = ChatAnthropic(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        default_headers={"x-api-key": api_key},
    )

    # Connect to taskdog-mcp via stdio transport.
    client = MultiServerMCPClient(
        {
            "taskdog": {
                "command": "taskdog-mcp",
                "args": [],
                "transport": "stdio",
            }
        }
    )
    try:
        tools = await client.get_tools()
    except Exception as e:
        logger.warning("taskdog-mcp failed to start: %s", e)
        return _placeholder_graph(f"taskdog-mcp connection failed: {e}")

    agent = create_react_agent(
        llm,
        tools=tools,
        name="ikigai-taskdog",
        prompt=(
            "You are a task management assistant. You have access to 26 taskdog "
            "tools for creating, listing, updating, completing, and managing "
            "tasks. Use them to fulfill the user's request. When done, summarize "
            "the result clearly."
        ),
    )
    return agent


def _placeholder_graph(reason: str) -> Any:
    """Return a minimal graph that reports why the real graph couldn't load.

    Used when taskdog-mcp isn't running or API key isn't configured.
    The user sees this message in Studio UI instead of a hard crash.
    """
    from langgraph.graph import END, START, StateGraph

    def _report(state: dict) -> dict:
        return {"messages": [{"role": "assistant", "content": (
            f"⚠️ taskdog-mcp graph unavailable: {reason}\n\n"
            "Fix:\n"
            "  1. pip install taskdog-mcp (or `pipx install taskdog-mcp`)\n"
            "  2. Start taskdog-server: pipx run taskdog-server (port 8000)\n"
            "  3. Set MINIMAX_API_KEY / ANTHROPIC_API_KEY / CLAUDE_API_KEY\n"
            "  4. Restart `langgraph dev`"
        )}]}

    builder = StateGraph(dict)
    builder.add_node("report", _report)
    builder.add_edge(START, "report")
    builder.add_edge("report", END)
    return builder.compile()


# ---------------------------------------------------------------------------
# M102-compatible sync wrapper. langgraph_api expects sync factories that
# accept ServerRuntime and/or RunnableConfig. Async factories are also
# supported (we use async for MultiServerMCPClient.get_tools()), but the
# sync entry point must exist for validate.
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
    """Sync wrapper for langgraph_api compatibility.

    langgraph_api requires sync factories (or async ones with __wrapped__).
    We delegate to asyncio.run() to invoke the async version.
    """
    import asyncio

    return asyncio.run(make_taskdog_mcp_graph())
