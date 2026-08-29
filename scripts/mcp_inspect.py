#!/usr/bin/env python3
"""MCP gateway contract test — spawns the gateway via stdio and asserts tool/resource counts.

Used by `make mcp-inspect` (Makefile) and `scripts/mcp-inspect.bat` (Windows).
Also runnable directly: `python scripts/mcp_inspect.py`.

Cross-platform (no Node.js, no jq, no poetry). Uses the MCP Python SDK's
stdio_client + ClientSession to do the same handshake the inspector does.

Asserts:
  - initialize handshake completes (no McpError)
  - tools/list returns >= 13 tools
  - resources/list returns >= 6 resources
  - Exits 0 on pass, 1 on fail

Usage:
  python scripts/mcp_inspect.py [--tool-count N] [--resource-count N] [--help]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import platform
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# === Defaults (B3.5 spec) ===
DEFAULT_TOOL_COUNT = 13        # 10 original + 3 mesh (B3.1 + B3.2)
# Per A2UI spec §11 R4: 6 total resources = 3 concrete + 3 templates
DEFAULT_RESOURCE_COUNT = 6     # queue://pending, health://gateway, plans://cycles (concrete)
                             # + ueid://{ueid}, queue://events/{event_id}, plans://cycles/{cycle_id} (templates)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp_inspect",
        description="MCP gateway contract test — asserts tool + resource counts via stdio handshake.",
    )
    parser.add_argument(
        "--tool-count",
        type=int,
        default=DEFAULT_TOOL_COUNT,
        help=f"Minimum expected tool count (default {DEFAULT_TOOL_COUNT})",
    )
    parser.add_argument(
        "--resource-count",
        type=int,
        default=DEFAULT_RESOURCE_COUNT,
        help=f"Minimum expected resource count (default {DEFAULT_RESOURCE_COUNT})",
    )
    return parser.parse_args(argv)


def build_pythonpath(repo_root: Path) -> str:
    """Build PYTHONPATH string for gateway subprocess.

    Gateway requires two paths:
      - repo root (for `from src.contracts.common import UEID`)
      - src/ikigai/src (for `from mcp_server.server import main`)

    Cross-platform separator:
      - POSIX (Linux, macOS, Git Bash): ':'
      - Native Windows: ';'
    """
    repo_root_str = str(repo_root)
    mcp_src = str(repo_root / "src" / "ikigai" / "src")
    sep = ";" if platform.system() == "Windows" else ":"
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        return f"{existing}{sep}{repo_root_str}{sep}{mcp_src}"
    return f"{repo_root_str}{sep}{mcp_src}"


async def run_inspect(min_tools: int, min_resources: int) -> int:
    """Spawn gateway via stdio, assert tool/resource counts. Returns 0 on pass, 1 on fail."""
    repo_root = Path(__file__).resolve().parent.parent  # scripts/ is sibling of repo_root

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u", "-m", "mcp_server"],
        cwd=str(repo_root / "src" / "ikigai" / "src"),
        env={**os.environ, "PYTHONPATH": build_pythonpath(repo_root)},
    )

    print(f"[mcp-inspect] spawning: {server_params.command} {' '.join(server_params.args)}")
    print(f"[mcp-inspect] PYTHONPATH: {server_params.env['PYTHONPATH']}")
    print(f"[mcp-inspect] cwd: {server_params.cwd}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                init_result = await session.initialize()
                print(f"[mcp-inspect] initialized: server={init_result.serverInfo.name}")

                tools_result = await session.list_tools()
                tools_count = len(tools_result.tools)
                tool_names = [t.name for t in tools_result.tools]
                print(f"[mcp-inspect] tools: {tools_count} -> {tool_names}")

                resources_result = await session.list_resources()
                resources_count = len(resources_result.resources)
                resource_uris = [str(r.uri) for r in resources_result.resources]
                print(f"[mcp-inspect] resources: {resources_count} -> {resource_uris}")

                # Per A2UI spec §11 R4: 6 total resources = 3 concrete + 3 templates
                # MCP SDK Pydantic models use camelCase attributes (serverInfo, resourceTemplates)
                templates_result = await session.list_resource_templates()
                templates_count = len(templates_result.resourceTemplates)
                template_uris = [str(t.uriTemplate) for t in templates_result.resourceTemplates]
                print(f"[mcp-inspect] resource_templates: {templates_count} -> {template_uris}")

                total_resources = resources_count + templates_count
                errors: list[str] = []
                if tools_count < min_tools:
                    errors.append(f"tools: got {tools_count}, expected >= {min_tools}")
                if total_resources < min_resources:
                    errors.append(
                        f"resources: got {total_resources} "
                        f"(concrete={resources_count} + templates={templates_count}), "
                        f"expected >= {min_resources}"
                    )

                if errors:
                    print("[mcp-inspect] FAIL:")
                    for e in errors:
                        print(f"  - {e}")
                    return 1

                print(
                    f"[mcp-inspect] PASS ({tools_count} tools, {total_resources} resources "
                    f"= {resources_count} concrete + {templates_count} templates)"
                )
                return 0
    except Exception as e:
        print(f"[mcp-inspect] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return asyncio.run(run_inspect(args.tool_count, args.resource_count))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
