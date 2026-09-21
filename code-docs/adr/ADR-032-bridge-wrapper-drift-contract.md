# ADR-032 — Bridge-Wrapper Drift Contract (mcp_bridge.py ⊆ server.py @MCP.tool registry)

> **Status:** ACCEPTED (2026-09-21)
> **Deciders:** matheus (project owner)
> **Load-bearing:** YES — drift invariant (`test_mcp_bridge_wrapped_tool_count_matches_canonical` in `src/ikigai/tests/test_drift_extended_invariants.py`) depends on this contract
> **Supersedes:** none (new decision — locks an implicit invariant that was violated in M11)
> **Related code:**
> - `src/ikigai/src/agents/v2/mcp_bridge.py` (sync wrappers around async MCP Gateway calls)
> - `src/ikigai/src/mcp_server/server.py` (canonical `@MCP.tool` registry)
> - `src/ikigai/src/agents/tools.py` (`IKIGAI_TOOLS = [...]` list, gated at 12 entries per ADR-013)
> - `src/ikigai/tests/test_drift_extended_invariants.py:299-374` (`test_mcp_bridge_wrapped_tool_count_matches_canonical`)
> - `src/ikigai/tests/test_canonical_scope.py:493-534` (`test_ikigai_tools_count_is_12`)

---

## Context

The v2 IKIGAI graph (`src/ikigai/src/agents/v2/`) communicates with the MCP Gateway through a thin sync wrapper module (`mcp_bridge.py`) that exposes one Python function per MCP tool. Each wrapper does:

```python
def ikigai_<name>(*args, **kwargs) -> dict[str, Any]:
    return _call("ikigai_<name>", {"key": value, ...})
```

The `_call` helper dispatches via the canonical tool-name string to `_server.call(tool_name, args)` — the FastMCP gateway client in production, `FakeMcpServer` in tests. The bridge is therefore a **projection** of the server-side tool registry into the synchronous, graph-callable surface.

Two sources of truth exist for the agent-layer tool surface:

1. **Server registry** — `src/ikigai/src/mcp_server/server.py` `@MCP.tool(...)` decorators. Every tool exposed via FastMCP MUST be registered here.
2. **Bridge wrappers** — `src/ikigai/src/agents/v2/mcp_bridge.py` `def ikigai_*` functions. v2 nodes call these wrappers synchronously.

The M11 IKIGAI Agentic System Review (2026-09-12, `memory/system-review-gaps-2026-09-12.md`) found a **P0 attribution violation (L4 G-1)** that had been silent for ~5 days:

- **Pre-M12 state** (commit `b960e852`, 2026-09-07): V5-E "Opção B-A — radical-máxima" deleted 7 PAV-math tools from `server.py` (`ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_corrections`, `ikigai_plan_cycle`, `ikigai_checkpoint`, `ikigai_sync_vault`).
- **However**: `mcp_bridge.py` continued to export wrappers for those deleted tools (`ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`, `ikigai_plan`, `ikigai_reflect`, `ikigai_tag_and_persist`, `ikigai_commit_summary`).
- **Runtime behavior**: every v2 node that called a deleted wrapper silently failed via the `dict_protocol_no_op` fallback. No exception, no log, no drift detection. **9 PAV-flavored tool calls were silently no-ops for ~5 days.**
- **Plus** (G-2): the bridge-wrapper count was not drift-net enforced. Adding a 13th wrapper silently grew agent surface without any CI guard.

This is the canonical pattern for a class of failures: **wrapper/registry drift** — a derived projection layer (sync wrappers, async bindings, RPC stubs, CLI dispatch tables) silently falls out of sync with its source-of-truth registry, and no test trips the detector.

The M11 review (T-12.1) added `test_mcp_bridge_wrapped_tool_count_matches_canonical` to pin the alignment. **M12 (2026-09-13) removed 8 PAV-flavored wrappers from `mcp_bridge.py`; only `ikigai_decompose` survives.** This ADR formalizes the contract that the M11 review surfaced.

The closest existing ADR is **ADR-012** (fork-connection architecture), which establishes the pattern "fork MCP server modules wrap external tools via hand-rolled JSON-RPC over stdio." ADR-012 covers the **transport** layer (how forks connect) and the **registry** layer (forks register tools in their own server modules). It does **not** cover the **bridge-wrapper** layer (how the v2 graph calls those tools synchronously without going async). This is the architectural gap.

---

## Decision

**The set of `ikigai_*` wrappers in `src/ikigai/src/agents/v2/mcp_bridge.py` MUST be a subset of the `@MCP.tool` registry in `src/ikigai/src/mcp_server/server.py`. Adding a wrapper without registering it in `server.py` (or vice versa) is FORBIDDEN.**

The contract has **3 rules (R1-R3)** and **1 enforcement invariant**.

### R1 — Bridge ⊆ server registry

Every `def ikigai_*(...)` function in `mcp_bridge.py` MUST appear as a `@MCP.tool(...)` decorator (either bare `@MCP.tool()` or `@MCP.tool(name="...")`) on a function of the same name in `server.py`. Reverse direction is permitted: `server.py` may register tools that have no bridge wrapper yet (those tools are simply unreachable from the v2 graph; adding a wrapper to call them is opt-in).

### R2 — IKIGAI_TOOLS = 12 is the upper bound

`IKIGAI_TOOLS` in `src/ikigai/src/agents/tools.py` MUST contain exactly 12 entries (per `test_ikigai_tools_count_is_12` in `src/ikigai/tests/test_canonical_scope.py:493-534`). Adding any math/policy/scoring tool to `IKIGAI_TOOLS` violates ADR-013 §"OUT OF SCOPE"; removing a legitimate tool breaks the agent harness. Both directions require an ADR.

### R3 — Bridge wrappers must dispatch via `_call`

Every wrapper in `mcp_bridge.py` MUST dispatch through `_call(tool_name, args)` using its own name as the first argument. No direct `_server` access, no inlined dispatch logic, no per-wrapper exception swallowing. This rule makes the wrapper a pure projection — failure modes are observable via OTel spans (`ikigai.bridge.{tool_name}`) and the test detector.

### Enforcement invariant

`test_mcp_bridge_wrapped_tool_count_matches_canonical` in `src/ikigai/tests/test_drift_extended_invariants.py:299-374` MUST PASS. The test:

1. Discovers all `@MCP.tool(...)` registrations in `server.py` (both bare decorators with function-name fallback and explicit `name="..."` decorators).
2. Discovers all `def ikigai_*(...)` definitions in `mcp_bridge.py`.
3. Asserts `bridge ⊆ server` (with a single reserved exception: `ikigai_helper`, which is documented as a purely-internal helper and may be added later without server registration).
4. Asserts every wrapper calls `_call(...)` with its own name (catches typos that would route to a non-existent server tool at runtime).

If the test fails, CI fails. There is no override flag.

---

## Rationale

1. **Single source of truth for tool names.** `server.py` is the canonical tool surface (FastMCP registry, exposed via JSON-RPC stdio). The bridge is a derived projection for sync graph calls. Inverting the relationship — letting the bridge define new tool names — silently grows the agent surface (the M11 G-2 finding).

2. **Test-typed alignment beats documentation.** Documentation about "which wrappers exist" goes stale. A drift detector that walks two ASTs and asserts the subset relationship cannot go stale without CI catching it. Per ADR-013 §"Persistent enforcement": "drift detectors are load-bearing — running the test in CI is the canonical way to prevent future sessions from accidentally re-introducing deleted code."

3. **Wrapper ≤ 12 is mechanically consistent with ADR-013.** ADR-013 §"OUT OF SCOPE" forbids adding algorithm/policy/scoring tools to `IKIGAI_TOOLS`. The bridge wrappers in `mcp_bridge.py` are a subset of those 12 tools (the planner-exposed subset). If `IKIGAI_TOOLS` grows beyond 12, ADR-013 must be amended first; if a new bridge wrapper appears, it must reference a tool that exists in the canonical 12 (or be a new one added via an ADR).

4. **Asymmetric subset is the right direction.** Bridge ⊆ server (not bridge == server) because:
   - `server.py` may register infra tools (investigation queue, vault reads, task I/O) that the v2 graph doesn't need synchronously.
   - `mcp_bridge.py` may add or remove wrappers per v2-node demand without re-touching the canonical server registry.
   - Today only `ikigai_decompose` is wired through the bridge (post-M12 cleanup); the other 11 server tools are exposed via JSON-RPC stdio for non-graph consumers.

5. **Failure isolation via OTel spans.** R3 (every wrapper must call `_call` with its own name) keeps the wrapper a pure projection. Failures surface as OTel spans `ikigai.bridge.{tool_name}` with `tool.error.class` / `tool.error.message` / `tool.error.traceback` attributes. Without this rule, per-wrapper exception handlers would silently swallow dispatch failures — exactly the M11 silent-failure pattern.

6. **Reversibility.** Adding a wrapper is a 3-line edit (def + return + import); removing a wrapper is a 1-line delete. Adding a tool to the server is a `@MCP.tool(name=...)` decorator + handler. Removing a tool from the server requires either keeping the wrapper removed (per R1, drift test trips) or removing both. Neither direction requires an ADR — only changing the contract (e.g., making bridge ⊇ server, or adding a 13th `IKIGAI_TOOLS`) requires an ADR per R2.

---

## Implementation Rules

**R1 — Bridge ⊆ server.** New wrappers MUST be added to `mcp_bridge.py` ONLY if the corresponding `@MCP.tool` already exists in `server.py` (or is added in the same commit). The drift detector pins this; CI enforces.

**R2 — IKIGAI_TOOLS count stays at 12.** Adding/removing entries from `IKIGAI_TOOLS` in `src/ikigai/src/agents/tools.py` requires an ADR amendment to ADR-013 (or this ADR). The drift detector `test_ikigai_tools_count_is_12` enforces.

**R3 — Wrappers dispatch via `_call`.** Every wrapper MUST follow the pattern:

```python
def ikigai_<name>(*, kwarg1: type1, kwarg2: type2) -> dict[str, Any]:
    """<one-line docstring>."""
    return _call("ikigai_<name>", {"kwarg1": kwarg1, "kwarg2": kwarg2})
```

No direct `_server` access. No per-wrapper try/except (let the `traced_tool_dispatch` in `_call` surface errors).

**R4 — Add a new wrapper in 1 commit, 2 files.** Adding a wrapper requires:
1. `@MCP.tool(name="ikigai_<name>", description=...)` decorator in `server.py` (if not already present)
2. `def ikigai_<name>(...)` wrapper in `mcp_bridge.py`
3. Drift test must pass

If both files are touched in the same commit, the drift test passes (both `server_tools` and `bridge_tools` grow together).

**R5 — Drift detector is the canonical enforcement.** `test_mcp_bridge_wrapped_tool_count_matches_canonical` is the load-bearing enforcement. Bypassing it (commenting out the assertion, narrowing the regex, adding `ikigai_helper` to the exclusion list without an ADR) is FORBIDDEN.

---

## Consequences

### Positive

- **Prevents re-occurrence of M11 silent failure.** The 9 PAV-flavored wrappers that were silently no-ops for ~5 days (commit `b960e852` → `9980f22` → `80bedf9` → `ed2803b` window) cannot recur: if any wrapper references a non-existent server tool, CI fails immediately.
- **Single canonical tool surface.** `server.py` is the only source of truth for tool names; `mcp_bridge.py` is a derived projection; `IKIGAI_TOOLS` is the planner-exposed subset (gated at 12 per ADR-013).
- **Adding a 13th wrapper is mechanically impossible.** Either the wrapper references a server-registered tool (drift test passes) or it doesn't (drift test fails). No silent surface growth.
- **OTel observability intact.** R3 keeps `_call` as the single dispatch point; OTel spans `ikigai.bridge.{tool_name}` continue to capture latency and errors uniformly.
- **Reversible without ADR.** Adding/removing wrappers (not tools) is a 1-3 line edit; no ADR required. The drift detector validates the change.

### Negative

- **1 drift test to maintain.** `test_mcp_bridge_wrapped_tool_count_matches_canonical` is load-bearing; if it breaks (false positive) every CI run fails. Per Phase 8.2 SPEC §3 — "drift tests grow with the system; weakening them is forbidden."
- **Cross-platform regex brittleness.** The detector uses regex (`@MCP\.tool\([^@]*?name="..."`) to discover tools. Edge cases (multi-line decorators with comments between args, decorators spanning many lines, decorators in nested scopes) need careful maintenance. M11 (T-12.1) added multi-line tolerance; future decorator forms may need detector amendments.
- **No coverage of handler bodies.** This contract pins the **registration** surface, not the handler behavior. A wrapper registered correctly in `server.py` may still route to a handler that reads PAV-written vault artifacts (e.g., `ikigai_observe_state` reads from `vault/ikigai/cycle-state.md`). Handler-body attribution is enforced by ADR-013 + separate drift tests, not by this contract.
- **Bridge ⊆ server is not symmetric.** The reverse direction (server ⊇ bridge) is permitted but not enforced. New server tools with no bridge wrapper are unreachable from the v2 graph; this is by design (opt-in projection) but may confuse implementers who expect "all server tools reachable from the graph."

### Neutral

- **`ikigai_helper` is the only reserved exclusion.** The detector excludes `ikigai_helper` from the subset check. This is documented as a purely-internal helper that may be added later without server registration. Adding other names to the exclusion list requires an ADR.
- **`IKIGAI_TOOLS = 12` is the planner surface, not the server surface.** The server has 11 `@MCP.tool` decorators (8 IKIGAI + 3 Plan C investigation queue) per `src/ikigai/src/mcp_server/server.py:49`. `IKIGAI_TOOLS` in `tools.py` is the LangChain `@tool`-wrapped subset for `create_deep_agent`. The 12 count refers to `IKIGAI_TOOLS`, not the server registry. Bridge wrappers reference **server-registered** tools, not `IKIGAI_TOOLS` entries.

---

## Alternatives Considered

### Alt A — Bridge == server (symmetric equality)

Make every server tool have a wrapper, and every wrapper have a server registration. Symmetric.

- **Rejected**: server registers infra tools the v2 graph doesn't need (investigation queue, vault_read for non-graph consumers). Symmetry would add ~10 dead wrappers. Asymmetric subset is the right shape.

### Alt B — Bridge is the source of truth (server derives from bridge)

Generate `server.py` `@MCP.tool` registrations from `mcp_bridge.py` wrapper definitions (build-time codegen).

- **Rejected**: codegen is overkill for 12 tools. The drift detector already pins the subset relationship; codegen would add a build step for no functional benefit. YAGNI per ADR-012 §"Tool versioning: YAGNI."

### Alt C — Reverse subset (server ⊆ bridge, opt-in wrappers)

Every server tool must be exposed via a bridge wrapper. Bridge is the policy, server is the registry.

- **Rejected**: this is the inverse of R1 and would force every server tool to have a graph-callable surface. Some server tools (investigation queue MCP, vault reads for ad-hoc CLI consumers) legitimately don't need sync wrappers. The opt-in subset is asymmetric by design.

### Alt D — Runtime assertion instead of CI drift test

Add a runtime assertion in `_call` that checks `bridge_tools ⊆ server_tools` at startup; raise if drift detected.

- **Rejected**: startup assertions fail late (after server boots, possibly in production) rather than at CI time. Drift tests are cheaper and fail earlier (in CI, before any code reaches runtime). Per ADR-013 §"Persistent enforcement": drift tests are the canonical mechanism.

### Alt E — Drop the bridge entirely; v2 nodes call MCP async directly

Make every v2 node `async def`, drop `mcp_bridge.py`, await `_server.call(...)` directly.

- **Rejected**: breaks the sync invocation surface (`v2.py:241 compiled.invoke({})`). LangGraph supports both sync and async; inlining async at every node would force async-or-die on the entire graph. Bridge is the right boundary for sync-or-async compatibility (same pattern as ADR-026 dispatcher wrapping both).

### Alt F — Per-wrapper OTel span naming convention instead of contract

Document the span naming as convention, not enforcement. Skip the drift test.

- **Rejected**: this is the pre-M11 state. Conventions go stale; tests don't. The M11 review explicitly identified the lack of drift enforcement as a contributing factor to the silent failure.

---

## Cross-references

### Load-bearing prior ADRs

- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) — `IKIGAI_TOOLS` count of 12 is enforced by `test_ikigai_tools_count_is_12` (ADR-013 §"Drift Detector"). R2 of this ADR inherits that constraint.
- **ADR-012 — Fork-connection architecture** (Accepted 2026-08-30) — establishes the pattern "fork MCP server modules register tools in their own server modules via hand-rolled JSON-RPC over stdio." ADR-032 covers the **bridge-wrapper** layer (v2 graph sync wrappers) which ADR-012 does not address.

### Related decisions

- **ADR-009 — Pydantic v2 strict** (Accepted 2026-08-31) — bridge wrappers return `dict[str, Any]`; Pydantic models are constructed at the call-site, not in the wrapper.
- **ADR-019 — QHE → prompt-template constants** (Proposed 2026-09-04) — bridge wrappers don't carry tuning constants; no extension to ADR-019.
- **ADR-025 — Skill binding mechanism** (Accepted 2026-09-04) — bridge wrappers are called by v2 nodes, which are bound via ADR-025's YAML manifest; the bridge is one layer below the manifest binding.

### Code references

- `src/ikigai/src/agents/v2/mcp_bridge.py:103-106` — bridge-wrapper section header comment stating the subset invariant
- `src/ikigai/src/agents/v2/mcp_bridge.py:109-112` — `ikigai_decompose` wrapper (the only surviving bridge wrapper post-M12)
- `src/ikigai/src/mcp_server/server.py:39-40` — `MCP = FastMCP("ikigai-gateway")` registry init
- `src/ikigai/src/mcp_server/server.py:49` — section header "11 total (8 IKIGAI + 3 Plan C investigation)"
- `src/ikigai/src/agents/tools.py:418-446` — `IKIGAI_TOOLS = [...]` initial assignment + `.extend(...)` for vault reads
- `src/ikigai/tests/test_canonical_scope.py:493-534` — `test_ikigai_tools_count_is_12` (gates R2)
- `src/ikigai/tests/test_drift_extended_invariants.py:299-374` — `test_mcp_bridge_wrapped_tool_count_matches_canonical` (gates R1, R3)

### Memory / review references

- `memory/system-review-gaps-2026-09-12.md` — M11 IKIGAI Agentic System Review, 41 gaps; L4 G-1 is the bridge-wrapper silent failure
- `memory/m12-bottom-up-infra-shipped-2026-09-14.md` — M12 P0 attribution fixes; T-12.1 added the drift test + removed 8 PAV-flavored wrappers
- `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md` — M11 diagnosis doc (288 lines, 5 cross-cutting themes)

---

*ADR-032 — accepted 2026-09-21 — locks the bridge ⊆ server contract surfaced by M11 G-1; drift detector load-bearing via `test_mcp_bridge_wrapped_tool_count_matches_canonical`*