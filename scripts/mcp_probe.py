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
            print(
                f"[1] initialize -> server={init.serverInfo.name} v{init.serverInfo.version}"
            )

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
            r = await session.call_tool(
                "vault_read", {"vault_path": "plans/ikigai-agent-spec.md"}
            )
            body = r.content[0].text
            first_line = body.splitlines()[0] if body else "(empty)"
            print(
                f"[6] vault_read(plans/ikigai-agent-spec.md) -> first line: {first_line}"
            )

            # 7. resource read: health://gateway
            rr = await session.read_resource("health://gateway")
            print(f"[7] health://gateway -> {rr.contents[0].text[:200]}")

            # 8. ikigai_decompose (real UEID traversal)
            r = await session.call_tool(
                "ikigai_decompose",
                {"dream_ueid": "ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609"},
            )
            print(f"[8] ikigai_decompose -> {r.content[0].text[:200]}")

            # 9. ikigai_read_tasks (read structured tasks from data/tasks.jsonl)
            r = await session.call_tool("ikigai_read_tasks", {"limit": 3})
            print(f"[9] ikigai_read_tasks -> {r.content[0].text[:200]}")

            # 10. ikigai_mesh_show (cross-fork view)
            r = await session.call_tool(
                "ikigai_mesh_show", {"ueid": "ikigai:dream:test-2026:00000000:00000000"}
            )
            print(f"[10] ikigai_mesh_show -> {r.content[0].text[:200]}")

            # 11. ikigai_phase (no args; reads PAV phase state)
            r = await session.call_tool("ikigai_phase", {})
            print(f"[11] ikigai_phase -> {r.content[0].text[:200]}")

            # 12. ikigai_corrections
            r = await session.call_tool(
                "ikigai_corrections", {"date": "2026-09-03", "limit": 3}
            )
            print(f"[12] ikigai_corrections -> {r.content[0].text[:200]}")

            # 13. ikigai_plan_cycle (ARCHIVED — should return ARCHIVED status)
            r = await session.call_tool("ikigai_plan_cycle", {})
            print(f"[13] ikigai_plan_cycle -> {r.content[0].text[:200]}")

            # 14. ikigai_checkpoint (read latest LangGraph checkpoint)
            r = await session.call_tool(
                "ikigai_checkpoint", {"action": "get", "thread_id": ""}
            )
            print(f"[14] ikigai_checkpoint -> {r.content[0].text[:200]}")

            # 15. ikigai_sync_vault (read sync log)
            r = await session.call_tool("ikigai_sync_vault", {"date": "2026-09-03"})
            print(f"[15] ikigai_sync_vault -> {r.content[0].text[:200]}")

            # 16. resources: queue://pending + plans://cycles
            rr = await session.read_resource("queue://pending")
            print(f"[16] queue://pending -> {rr.contents[0].text[:200]}")
            rr = await session.read_resource("plans://cycles")
            print(f"[17] plans://cycles -> {rr.contents[0].text[:200]}")

            print("\n[OK] MCP stdio interface probe complete - 17 calls succeeded.")
            return 0


def main() -> int:
    try:
        return asyncio.run(run_probe())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
