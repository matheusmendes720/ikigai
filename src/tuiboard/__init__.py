"""tuiboard fork — TUI dashboard renderer MCP server.

In-repo per spec Q1=β. Stdlib-only JSON-RPC 2.0 transport per Q2=i.

NOTE: tuiboard is a RENDERING fork — it reads from the cross-fork storage
adapters (CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter) but does
NOT have its own storage adapter (per spec: not a data fork).
"""
__version__ = "0.1.0"
