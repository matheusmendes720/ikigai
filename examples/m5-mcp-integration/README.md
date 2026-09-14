# Example: M5 IKIGAI MCP Integration

Demonstrates how a milestone WIRES external tools to the agent layer and ADDS a drift net test to validate the integration.

## What this example covers

The IKIGAI agent layer binds 12 tools (10 external data + 2 vault reads). Per CLAUDE.md "Global Conventions":

> Drift detectors in `tests/test_canonical_scope.py` enforce this invariant.

So adding an MCP tool requires:

1. Wire `@MCP.tool` decorator in `src/ikigai/src/mcp_server/server.py`
2. Register in `IKIGAI_TOOLS` list at `src/ikigai/src/agents/tools.py:556`
3. Add a drift net invariant in `src/ikigai/tests/test_canonical_scope.py` that asserts `len(IKIGAI_TOOLS) == 12`

## TDD pattern (per M5 final review)

1. Write the failing test FIRST:

   ```python
   def test_ikigai_tools_count_is_12(self):
       assert len(IKIGAI_TOOLS) == 12
   ```

2. See it FAIL (count is currently 11 or 13)
3. Apply the change (add tool + bump count)
4. See test PASS
5. Atomic commit:

   ```
   feat(ikigai): add new MCP tool via @MCP.tool decorator

   Adds `<tool_name>` to server.py + IKIGAI_TOOLS list.
   Drift net test_ikigai_tools_count_is_12 enforces count invariant.

   drift net 35/35 PASS preserved.
   ```

## Drift net pattern

Every M-series milestone that adds an invariant must add a drift test in one of:

- `src/ikigai/tests/test_canonical_scope.py` (positive invariants)
- `src/ikigai/tests/test_drift_invariants.py` (negative constraints)
- `src/ikigai/tests/test_drift_extended_invariants.py` (cross-module alignment)

## How to run this example

```bash
cd examples/m5-mcp-integration

# See what was added in M5
cat .claude/loop/roadmap.md
cat .claude/loop/progress.md
```

## Key takeaway

The drift net is the regression guard for new features. Adding a tool WITHOUT updating the drift net invariant = future drift waiting to happen. The TDD pattern enforces discipline.
