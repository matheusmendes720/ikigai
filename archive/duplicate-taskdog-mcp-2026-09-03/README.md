# Archive: Duplicate Path 3 taskdog MCP implementation (2026-09-03)

## Why archived

Two Path 3 taskdog MCP implementations existed in the working tree as of
2026-09-03. Per `docs/design-system/24-taskdog-paths-architecture.md`:

- **Path 1 (CANONICAL)** = harness `@tool` subprocess → `taskdog.exe`
- **Path 3** = standalone MCP server over stdio

The implementations:

| Location | Module path | FastMCP name | Resources | Subprocess pattern | Status |
|----------|-------------|--------------|-----------|-------------------|--------|
| `src/ikigai/src/mcp_server/taskdog_mcp/` (committed, fe61dcc) | `mcp_server.taskdog_mcp.server` | `ikigai-taskdog-gateway` | (none) | Delegates to Path 1 `agents.tools` functions | **CANONICAL** — 5/5 tests PASS |
| `src/taskdog_mcp/` at repo root (this archive) | `src.taskdog_mcp` | `taskdog-mcp-gateway` | `taskdog://health` | Standalone `_run_taskdog()` helper | DUPLICATE — tests fail at import |

## Why the duplicate is broken

`tests/test_taskdog_mcp_path3.py` (in this archive) imports via
`from src.taskdog_mcp import MCP, main`, which fails with
`ModuleNotFoundError: No module named 'src'`.

Root cause: the test expects `src/` to be importable as a top-level
package from repo root. The existing pytest infrastructure (conftest at
`src/ikigai/conftest.py`) adds `<repo>/life/src/` to `sys.path`, which
works for `from src.mesh import ...` etc. but does NOT add the repo
root itself. So `from src.taskdog_mcp import ...` from a test at
`<repo>/life/tests/` cannot resolve.

Adding `from src.X import ...` as a public API would also conflict with
the existing convention where `src/` is a directory of subpackages
(`src/mesh`, `src/contracts`, `src/ikigai`), not a package itself.

## Why the canonical version differs

The committed Path 3 (`src/ikigai/src/mcp_server/taskdog_mcp/`) takes a
different design approach:

- **Delegates to Path 1** (`agents.tools.taskdog_*` functions) — no
  subprocess duplication; uses the same canonical Path 1 logic that
  the IKIGAI agent uses.
- **No health resource** — Path 1 has no health resource either; the
  health endpoint is provided by the gateway at a higher layer
  (`/health` in `gateway.py`).
- **Lives under `mcp_server/`** — matches the existing MCP server
  convention (sibling to `tools_vault.py`, `server.py`).

The archived version (this dir) was a standalone implementation that
re-implemented the subprocess runner. While it could be made to work
(moving it to `src/ikigai/src/mcp_server/` or adding a `src/__init__.py`
+ sys.path fix), it duplicates logic that's already canonical in Path 1.

## Decision

**Canonical Path 3** = `src/ikigai/src/mcp_server/taskdog_mcp/` (fe61dcc).
**Archive** this duplicate.

## Recovering (if needed)

If a future use case requires the standalone pattern (e.g., a health
resource endpoint that exposes taskdog binary availability), this
implementation can be revived and adapted. Suggested revival path:

1. Move files from `archive/duplicate-taskdog-mcp-2026-09-03/` to
   `src/ikigai/src/mcp_server/standalone_taskdog_mcp/` (sibling to
   `taskdog_mcp/`)
2. Rename FastMCP instance name to avoid conflict with canonical
3. Add the health resource as a separate tool, not a FastMCP resource
   (resources are for static data; a health check is a tool)
4. Wire as a separate MCP server entry point, not an alternative
   Path 3
5. Add proper sys.path handling in the test conftest

## Files preserved here

- `server.py` — FastMCP server with 4 tools + 1 resource
- `__init__.py` — package init (`from src.taskdog_mcp.server import MCP, main`)
- `__main__.py` — `python -m src.taskdog_mcp` entry point
- `test_taskdog_mcp_path3.py` — 8 tests for the duplicate implementation
