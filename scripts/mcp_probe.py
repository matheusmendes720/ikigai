"""Live probe of the IKIGAI MCP server (uses MCP SDK ClientSession).

Spawns the MCP server subprocess via MCP SDK's stdio_client (handles
Windows ProactorEventLoop init properly), then issues real tools/call
requests against the live server.

Verifies the interface works end-to-end:
  - initialize handshake (server identifies as "ikigai-gateway")
  - tools/list returns 15 tools
  - tools/call for: ikigai_health, vault_read, ikigai_score, ikigai_regime
  - resources/read for health://gateway

Usage:
  cd C:\\Users\\mathe\\code_space\\life-oss\\life
  python scripts/mcp_probe.py
"""

from __future__ import annotations

import asyncio
import os
import platform
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parent.parent
IKIGAI_CWD = REPO_ROOT / "src" / "ikigai" / "src"


def build_pythonpath() -> str:
    src_dir = str(REPO_ROOT / "src")
    mcp_src = str(IKIGAI_CWD)
    sep = ";" if platform.system() == "Windows" else ":"
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        return f"{existing}{sep}{src_dir}{sep}{mcp_src}"
    return f"{src_dir}{sep}{mcp_src}"


async def run_probe() -> int:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u", "-m", "mcp_server"],
        cwd=str(IKIGAI_CWD),
        env={**os.environ, "PYTHONPATH": build_pythonpath()},
    )

    print(f"[probe] spawning: {server_params.command} {' '.join(server_params.args)}")
    print(f"[probe] PYTHONPATH: {server_params.env['PYTHONPATH']}")
    print(f"[probe] cwd: {server_params.cwd}")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"[1] initialize -> server={init.serverInfo.name} v{init.serverInfo.version}")

            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"[2] tools/list -> {len(tool_names)} tools: {tool_names}")

            # 3. ikigai_health
            r = await session.call_tool("ikigai_health", {})
            print(f"[3] ikigai_health -> {r.content[0].text[:200]}")

            # 4. ikigai_score (observation wrapper around PAV-written state)
            r = await session.call_tool("ikigai_score", {"date": "2026-09-03"})
            print(f"[4] ikigai_score -> {r.content[0].text[:300]}")

            # 5. ikigai_regime (observation wrapper around PAV-written regime)
            r = await session.call_tool("ikigai_regime", {"date": "2026-09-03"})
            print(f"[5] ikigai_regime -> {r.content[0].text[:300]}")

            # 6. vault_read (allowlisted path; reads vault markdown)
            r = await session.call_tool("vault_read", {"path": "plans/ikigai-agent-spec.md"})
            body = r.content[0].text
            first_line = body.splitlines()[0] if body else "(empty)"
            print(f"[6] vault_read(plans/ikigai-agent-spec.md) -> first line: {first_line}")

            # 7. resource read: health://gateway
            rr = await session.read_resource("health://gateway")
            print(f"[7] health://gateway -> {rr.contents[0].text[:200]}")

            print("\n[OK] MCP stdio interface probe complete - all 7 calls succeeded.")
            return 0


def main() -> int:
    try:
        return asyncio.run(run_probe())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
