"""dcode — IKIGAi Deep Agent CLI (canonical entry point).

Project-internal shorthand for "deep code" / "deep agent code".
Per Phase 8.x scope (ADR-013): the IKIGAi agent is a PLANNING ASSISTANT ONLY.
It binds 8 IKIGAi tools via deepagents' create_deep_agent + LangGraph
checkpointing. Math/policy/scoring tools live behind the MCP interface
(src/mcp_server/server.py) — they are NOT in scope here.

Usage:
    dcode                              # one-shot help
    dcode --chat                       # interactive REPL (default thread)
    dcode --chat --thread my-session   # interactive REPL with custom thread
    dcode --chat --human-in-the-loop   # pause before each tool write

The `dcode` CLI is the canonical PowerShell/global-PATH entry point.
Aliases: `ikigai-deep-agent` (registered too — same underlying main()).
"""

from __future__ import annotations

# Re-export the harness main() so the dcode entry point and the
# ikigai-deep-agent entry point share one implementation. This keeps
# behavior identical and avoids drift between aliases.
from agents.deepagents_harness import main


if __name__ == "__main__":
    main()
