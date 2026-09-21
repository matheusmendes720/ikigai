"""M100: `taskdog` CLI sub-app — direct MCP-backed taskdog commands.

Exposes all 26 taskdog-mcp tools as direct Typer subcommands. No LLM
roundtrip — each command invokes the corresponding MCP tool via
``tool.ainvoke()`` and prints the JSON result.

Usage:
    life taskdog list-tasks --status PENDING --limit 10
    life taskdog create-task --name "review PR" --priority 8 --tag urgent
    life taskdog cancel-task --task-id 162
    life taskdog decompose-task --task-id 150 --num-subtasks 5
    life taskdog optimize-schedule

Implementation notes:
- 26 commands are registered dynamically via _register_all_tools()
- Each command is async — we use asyncio.run() at the Typer boundary
- Output is MCP-formatted list of {type, text} blocks; we flatten
  the first text block to JSON or text for terminal readability
- IKIGAI_DISABLE_MCP_TASKDOG=1 escape hatch returns an error
- taskdog-mcp binary required on PATH (verified by _check_mcp())
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from typing import Any

import typer

from .mcp_runtime import (
    _ensure_ikigai_src_on_path,
    get_mcp_tools_async,
)

# Force IKIGAI src onto sys.path (needed because taskdog_tools.py in
# ikigai.src.mcp_server transitively imports strategics.*).
_ensure_ikigai_src_on_path()

app = typer.Typer(
    name="taskdog",
    help="M100: Direct taskdog-mcp commands (26 tools, no LLM). "
    "Bypasses the deep-agent for power users.",
    no_args_is_help=True,
)


def _check_mcp_available() -> tuple[bool, str]:
    """Return (ok, error_msg). MCP requires taskdog-mcp on PATH."""
    if os.environ.get("IKIGAI_DISABLE_MCP_TASKDOG") == "1":
        return False, "IKIGAI_DISABLE_MCP_TASKDOG=1 — taskdog MCP disabled."
    if shutil.which("taskdog-mcp") is None:
        return False, "taskdog-mcp binary not on PATH. Install via `pipx install taskdog-mcp`."
    return True, ""


def _format_result(result: Any) -> str:
    """Flatten MCP result list[{type,text}] → JSON for terminal output."""
    if isinstance(result, list):
        if len(result) == 1 and isinstance(result[0], dict) and result[0].get("type") == "text":
            text = result[0].get("text", "")
            try:
                return json.dumps(json.loads(text), indent=2, default=str)
            except Exception:
                return text
        # Multiple blocks or non-text → JSON dump
        try:
            return json.dumps(result, indent=2, default=str)
        except Exception:
            return repr(result)
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, indent=2, default=str)
        except Exception:
            pass
    return str(result)


# Map MCP tool name → kebab-case CLI command name
def _to_cli_name(tool_name: str) -> str:
    """list_tasks → list-tasks, add_dependency → add-dependency, etc."""
    return tool_name.replace("_", "-")


async def _invoke_tool(tool_name: str, **kwargs: Any) -> Any:
    """Async invoke a specific MCP tool by name. Raises on unknown."""
    tools = await get_mcp_tools_async()
    tool = next((t for t in tools if t.name == tool_name), None)
    if tool is None:
        raise KeyError(f"Unknown MCP tool: {tool_name}")
    return await tool.ainvoke(kwargs)


def _make_command(tool_name: str, args_schema: dict[str, Any] | None) -> Any:
    """Build a Typer command function for one MCP tool.

    The schema's `properties` define per-tool arguments; we map them
    1:1 to Typer options. Required fields (no default in schema)
    become required arguments.
    """
    properties = (args_schema or {}).get("properties", {})
    required = set((args_schema or {}).get("required", []))

    # Build a wrapper function with explicit Typer annotations
    import inspect

    params = []
    for pname, pdef in properties.items():
        default = typer.Option(
            ... if pname in required else None,
            "--" + pname.replace("_", "-"),
            help=str(pdef.get("description") or ""),
        )
        params.append(
            inspect.Parameter(
                name=pname,
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=_python_type_for_schema(pdef),
            )
        )

    def cmd_with_annotations(**kwargs: Any) -> None:
        """Dynamic Typer command body (M100)."""
        # Drop None values (Typer sets unset optional args to None)
        call_args = {k: v for k, v in kwargs.items() if v is not None}
        # If schema expects an array, split the comma-separated string back.
        if properties:
            for pname, pdef in properties.items():
                if pname in call_args and isinstance(call_args[pname], str):
                    expected_type = _schema_inner_type(pdef)
                    if expected_type == "array":
                        call_args[pname] = [
                            s.strip() for s in call_args[pname].split(",") if s.strip()
                        ]
                    elif expected_type == "object":
                        try:
                            call_args[pname] = json.loads(call_args[pname])
                        except Exception:
                            pass  # leave as string; MCP server will error if needed
        try:
            result = asyncio.run(_invoke_tool(tool_name, **call_args))
            typer.echo(_format_result(result))
        except Exception as exc:  # noqa: BLE001
            typer.echo(
                json.dumps(
                    {"ok": False, "error": str(exc), "tool": tool_name, "args": call_args},
                    indent=2,
                )
            )
            raise typer.Exit(code=1)

    cmd_with_annotations.__name__ = tool_name
    cmd_with_annotations.__doc__ = f"Invoke MCP tool `{tool_name}` (M100)."
    cmd_with_annotations.__signature__ = inspect.Signature(parameters=params)  # type: ignore[attr-defined]
    return cmd_with_annotations


def _python_type_for_schema(prop: dict[str, Any]) -> Any:
    """Map JSON-schema type to Python type for Typer annotation.

    Typer only supports a limited type set (str, int, float, bool).
    For arrays of strings we use str with comma-separated values, and
    the command body splits them back. JSON-schema objects are mapped
    to str (JSON-encoded) since Typer doesn't support dict either.
    """
    return str | None


def _schema_inner_type(prop: dict[str, Any]) -> str | None:
    """Resolve the inner JSON-schema type for a property.

    Handles both:
    - Direct: {"type": "array"} or {"type": "string"}
    - anyOf:  {"anyOf": [{"type": "array"}, {"type": "null"}]}

    Returns the non-null inner type, or None if not resolvable.
    """
    if "type" in prop:
        return prop["type"]
    if "anyOf" in prop:
        for variant in prop["anyOf"]:
            t = variant.get("type")
            if t and t != "null":
                return t
    return None


def register_taskdog_app(app_instance: typer.Typer) -> None:
    """Discover all 26 MCP tools and register one Typer command per tool.

    Lazy: only invoked when the user runs `life taskdog --help`.
    """
    ok, err = _check_mcp_available()
    if not ok:

        @app_instance.command(name="__unavailable", deprecated=False)
        def _unavailable() -> None:
            """Placeholder when MCP is unavailable."""
            typer.echo(
                json.dumps(
                    {"ok": False, "error": err, "fix": "pipx install taskdog-mcp"},
                    indent=2,
                )
            )
            raise typer.Exit(code=1)

        return

    # Async discovery → sync wrapper
    try:
        tools = asyncio.run(get_mcp_tools_async())
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error": f"failed to discover MCP tools: {exc}",
                    "fix": "Check `taskdog-mcp` is installed and taskdog-server is running on :8000",
                },
                indent=2,
            )
        )
        raise typer.Exit(code=1)

    # Register each tool as a Typer command
    for tool in tools:
        cli_name = _to_cli_name(tool.name)
        # Each tool has its own args_schema; we generate the command
        # dynamically using Typer's callback function with annotations.
        cmd = _make_command(tool.name, tool.args_schema)
        app_instance.command(name=cli_name)(cmd)


__all__ = ["app", "register_taskdog_app"]
