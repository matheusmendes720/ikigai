"""Path 3 — taskdog MCP gateway server.

Re-exports the 4 Path 1 taskdog @tool functions (taskdog_list_tasks,
taskdog_create_task, taskdog_complete_task, taskdog_get_task) as an
independent MCP server. This is Path 3 in the 3-paths taskdog
architecture (canonical = Path 1, mesh alternative = Path 2, MCP gateway
= Path 3).

Per Phase A fork-connection SHIPPED 2026-08-30 (memory
[[phase-a-fork-connection-complete-2026-08-30]]) and ADR design
(`docs/design-system/24-taskdog-paths-architecture.md`).

Why this exists:
- Prevents subagent fabrication: agents that need taskdog access must
  explicitly use this MCP server, not invent "taskdog_*" tools.
- Independent stdio server: can run standalone or as a child of the
  UnifiedMCPGateway.
- Reuses Path 1 logic verbatim — no business logic duplication.

Run with::

    python -m mcp_server.taskdog_mcp.server
"""
