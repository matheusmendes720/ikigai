# ADR-034 — Phase 8.2 MCP Wiring (v2 Graph Node → mcp_bridge.py → FastMCP Gateway)

> **Status:** ACCEPTED (initial)
> **Deciders:** matheus (project owner)
> **Date:** 2026-09-21
> **Wave:** R4 (Master-04 attribution gap closure)
> **Load-bearing:** YES (drift invariant D1-1 enforced by `test_mcp_bridge_wrapped_tool_count_matches_canonical` per ADR-032; D5/D6 enforce Phase 8.3 observability + stdio binding)
> **Supersedes:** none (new decision — formalizes 7 design decisions locked at spec level per `docs/superpowers/specs/2026-09-08-phase-8-2-wiring-design.md`)
> **Related code:**
> - `src/ikigai/src/agents/v2/mcp_bridge.py` (sync wrappers around async MCP Gateway calls; only `ikigai_decompose` survives post-M12)
> - `src/ikigai/src/mcp_server/server.py` (canonical `@MCP.tool` registry per ADR-032 R1)
> - `src/ikigai/src/agents/v2/nodes/*.py` (11 v2 graph nodes; 8 wired to mcp_bridge, 1 in-process, 2 stubs)
> - `src/ikigai/src/agents/v2/tests/fixtures/fake_mcp_server.py` (canned-response mock per Phase 8.2 SPEC §6)
> - `src/ikigai/src/observability/otel_init.py` + `mcp_server/tracing.py:traced_tool_dispatch` (Phase 8.3 observability)
> - `src/ikigai/tests/test_drift_extended_invariants.py:299-374` (`test_mcp_bridge_wrapped_tool_count_matches_canonical`, gates D1)
> - `docs/superpowers/specs/2026-09-08-phase-8-2-wiring-design.md` (Phase 8.2 spec, SOT for the 7 locked decisions)

---

## Context

The v2 IKIGAI graph (`src/ikigai/src/agents/v2/`) ships **11 nodes** that initially called `tools_v2.py` helpers — `@tool` decorated functions wrapping `prompts/*.py` JSON renderers. These render observation JSON but DO NOT execute MCP calls against the gateway. Phase 8.2 transforms these prompt-chain stubs into real executor wiring.

### Pre-Phase-8.2 state

- **8 v2 nodes** wired to **`tools_v2.py`** helpers (observe, balance, heuristics, commit, plan, reflect, score_vectors, tag_and_persist) — all returning canned JSON via prompt-chain stubs.
- **2 v2 nodes** in-process (dispatch_sub_agents, commit_summary) — already bypass MCP.
- **1 v2 node** (`surface_intentions`) — explicitly deferred per roadmap, not blocking.

The prompt-chain stubs render JSON-shaped responses from `vault/ikigai/cycle-state.md` and similar artifacts but never call the canonical MCP gateway. **Failure modes: stale data, divergence from server handler logic, silent drift from PAV-written vault artifacts.**

### Phase 8.2 goal

Wire read-only MCP calls into the 8 stubbed nodes so the v2 graph orchestrates through the canonical FastMCP gateway (`server.py @MCP.tool` registry) instead of prompt-chain stubs. **ADR-013 canonical scope is preserved: read-only plumbing only, no math/policy/scoring writes to vault.**

### Phase 8.2 spec (SOT: `docs/superpowers/specs/2026-09-08-phase-8-2-wiring-design.md`)

7 design decisions locked at spec level (2026-09-08):

| # | Decision | Spec section |
|---|----------|--------------|
| 1 | Scope: read-only plumbing, no math (ADR-013 preserved) | §1 |
| 2 | MCP surface: 12 IKIGAI_TOOLS canonical; wrapper layer does NOT add new tools | §2 |
| 3 | Error policy: graceful degradation → error_channel → error_node | §3 |
| 4 | Observability: stub for Phase 8.3; Phase 8.2 wires calls only | §4 |
| 5 | Rollout: 3 atomic commits (T-8.2.1 obs / T-8.2.2 vault+state / T-8.2.3 in-proc+e2e) | §5 |
| 6 | Test strategy: `FakeMcpServer` canned-response mock, $0/tick, <1s/run | §6 |
| 7 | Wiring layer: centralized `mcp_bridge.py` (sync API, async underneath) | §7 |

### Why this ADR exists (Master-04 attribution gap)

Master-04 review (2026-09-21) flagged that the 7 Phase 8.2 decisions were locked at **spec level** (`docs/superpowers/specs/2026-09-08-phase-8-2-wiring-design.md`) without a corresponding **ADR**. Specs are tactical execution documents; ADRs are durable architectural contracts. The two layers serve different purposes:

- **Spec** — operational recipe (T-8.2.1/2/3 atomic commits, files to create/modify, acceptance checklist). Disposable after the milestone ships.
- **ADR** — formal decision that locks the architectural contract and references the drift detector enforcement. Survives long after the spec is deleted.

This ADR formalizes decisions D1-D7 (8 nodes wired, 8/11 partially, 1 in-process, 2 stubs preserved), locking the bridge-wrapper drift contract (ADR-032) inheritance plus the post-Phase-8.3 observability + stdio binding extensions.

### Closest existing ADRs

- **ADR-032 — Bridge-Wrapper Drift Contract** (Accepted 2026-09-21) — locks `mcp_bridge.py ⊆ server.py` with `test_mcp_bridge_wrapped_tool_count_matches_canonical`. **D1 of this ADR inherits ADR-032 R1-R3 unchanged.**
- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) — IKIGAI is planner-only; math/policy/scoring tools are forbidden in `IKIGAI_TOOLS`. **D2 of this ADR inherits ADR-013 §"OUT OF SCOPE" unchanged.**
- **ADR-012 — Fork-connection architecture** (Accepted 2026-08-30) — transport + registry layers for fork MCP servers. **D6 stdio binding is the v2-graph → FastMCP gateway analogue of ADR-012.**

ADR-032 covers the **bridge-wrapper contract**; ADR-012 covers the **fork-server transport**. **This ADR covers the v2 graph node-wiring layer** — neither predecessor addresses which v2 nodes call which bridge wrappers, or under what observability + binding contracts.

---

## Decision

**Wire the 8 stubbed v2 graph nodes to real MCP calls via `mcp_bridge.py`, preserving the read-only planner-only scope of ADR-013. Each node dispatches through a single bridge wrapper (or in-process handler) with OTel observability spans and FastMCP stdio binding. The remaining 3 nodes (in-process `dispatch_sub_agents` + `commit_summary`; deferred `surface_intentions`) stay as they are.**

The contract has **7 decisions (D1–D7)** and **3 enforcement invariants** (D1, D5, D6 — each with a dedicated drift detector or wired enforcement).

### D1 — Bridge wrappers MUST be a subset of `server.py @MCP.tool` registry (per ADR-032 R1)

Every `def ikigai_*(...)` function in `src/ikigai/src/agents/v2/mcp_bridge.py` MUST appear as a `@MCP.tool(...)` decorator on a function of the same name in `src/ikigai/src/mcp_server/server.py`. Reverse direction is permitted (server may register tools with no bridge wrapper yet — those are unreachable from v2 graph but available via JSON-RPC stdio for non-graph consumers).

**Inheritance:** This decision is identical to ADR-032 R1. Adding a Phase-8.2 wrapper without server registration is FORBIDDEN; CI fails via `test_mcp_bridge_wrapped_tool_count_matches_canonical`.

### D2 — `ikigai_decompose` is the ONLY wrapper in production as of V5-E

Post-M12 (T-12.1, 2026-09-13), the `mcp_bridge.py` module exports exactly **1 wrapper**: `ikigai_decompose(task_id: str) -> dict[str, Any]`. The 8 PAV-flavored wrappers that existed in earlier versions (`ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`, `ikigai_plan`, `ikigai_reflect`, `ikigai_tag_and_persist`, `ikigai_commit_summary`) were **REMOVED** because they referenced PAV-math tools that V5-E `b960e852` deleted from `server.py` (the M11 L4 G-1 silent-failure bug).

**Add/remove a wrapper is 3 lines / 1 line respectively.** Adding a wrapper requires:
1. `@MCP.tool(name="ikigai_<name>", description=...)` decorator in `server.py` (if not already present)
2. `def ikigai_<name>(...)` wrapper in `mcp_bridge.py`
3. Drift detector passes (both grow together)

**Inheritance:** Per ADR-013 §"OUT OF SCOPE", PAV-flavored wrappers (math/policy/scoring surface) are forbidden in `mcp_bridge.py`. Per ADR-032 R2, `IKIGAI_TOOLS` count stays at 12; adding a 13th wrapper requires amending ADR-013 (or this ADR).

### D3 — `surface_intentions` stays as prompt-chain stub

The `surface_intentions` v2 node reads `vault/ikigai/cycle-state.md` (PAV-written state) and emits in-chat surface hints. Per Phase 8.2 SPEC §"Out of Scope" item 5, it is **deferred** — there is no MCP-callable equivalent and the prompt-chain renderer matches operator expectations today.

- **No bridge wrapper for `surface_intentions`.**
- **No `error_channel` routing** — it cannot fail (no MCP call to make).
- **Drift detector does NOT scan `surface_intentions`** (it has no bridge wrapper to check).

Promoting `surface_intentions` to MCP-backed requires either:
- A new `ikigai_observe_pav_state` server tool (forbidden per ADR-013 — PAV math read), OR
- A new non-PAV observation surface (e.g., read from a non-PAV vault artifact) — this is FUTURE scope and requires amending ADR-013 + this ADR.

### D4 — `tag_and_persist` is READ-ONLY (vault_write is separate)

The `tag_and_persist` v2 node reads tags from existing vault artifacts (`ikigai_tag_and_persist` server tool, when registered). **Writes to vault** (creating new tags, persisting new tagged artifacts) are NOT wired in this node — they route through the canonical `vault_write` infrastructure per ADR-012 §"vault_write is sole vault writer" (ADR-012 R3).

- **Bridge wrapper behavior:** `tag_and_persist` reads tags ONLY. If a v2 node needs to write a tag, it MUST call `vault_write` (per ADR-012) — not `tag_and_persist`.
- **MCP server tool:** A read-only `ikigai_tag_and_persist` tag reader MUST be registered in `server.py` before the bridge wrapper is added.
- **Drift detection:** D1 invariant (`test_mcp_bridge_wrapped_tool_count_matches_canonical`) catches the wrapper/server drift. A second invariant (`test_tag_and_persist_read_only`) MAY be added in the future to assert the handler body has no write side effects — out of scope for this ADR.

### D5 — `mcp_bridge._call` uses OTel spans for observability (Phase 8.3)

Every `_call(tool_name, args)` invocation in `mcp_bridge.py` opens an OTel span named `ikigai.bridge.{tool_name}` with attributes:

- `tool.name` — the canonical server tool name
- `tool.args.hash` — SHA256 of the args dict (privacy-preserving)
- `tool.duration_ms` — wall-clock from span start to close
- `tool.error.class` / `tool.error.message` / `tool.error.traceback` — populated on failure

The bridge span prefix `ikigai.bridge.*` is deliberately distinct from the server-side span prefix `ikigai.mcp.*` (emitted by `src/ikigai/src/mcp_server/tracing.py:traced_tool_dispatch`) so the two layers do not double-count in trace exporters.

**Inheritance:** Per ADR-013 §"Persistent enforcement", observability is the canonical mechanism for invariant protection. Phase 8.3 (commit `5d92ed20`) wired the OTel spans; this ADR formalizes the contract that Phase 8.2 SPEC §4 left as "stub for Phase 8.3."

### D6 — Stdio binding via FastMcpClient (Phase 8.3)

`mcp_bridge._server` is bound at startup to a `FastMcpClient` instance that speaks JSON-RPC over stdio. The stdio transport MUST use `sys.stdin.buffer.readline()` (not `sys.stdin.readline()`) per the Windows stdio binary-mode fix (commit `b93a1f3`, 2026-08-30).

- **Test seam:** Tests monkeypatch `_server` to a `FakeMcpServer` instance with canned responses keyed by tool name (per Phase 8.2 SPEC §6 — `$0/tick, <1s/run`).
- **Production seam:** Production binds `_server` to the FastMCP client returned by `FastMcpClient.connect(...)` via the stdio JSON-RPC handshake.
- **Error path:** stdio read errors → exception → OTel span marks error → caller catches → routes to `error_channel` per D7 spec.

**Inheritance:** Stdio binding is the v2-graph → FastMCP gateway analogue of ADR-012 fork MCP transport. ADR-012 covers fork-MCP registration + stdio; this ADR covers the v2-graph side of the same stdio contract.

### D7 — Drift net enforces wrapper subset

The drift detector `test_mcp_bridge_wrapped_tool_count_matches_canonical` (M11 T-12.1, ADR-032 R1 enforcement) MUST PASS. The test:

1. Discovers all `@MCP.tool(...)` registrations in `server.py`.
2. Discovers all `def ikigai_*(...)` definitions in `mcp_bridge.py`.
3. Asserts `bridge ⊆ server` (with `ikigai_helper` reserved exception).
4. Asserts every wrapper calls `_call(...)` with its own name (catches typos that route to non-existent server tools).

**Phase 8.2 SPEC §6 test strategy** (`FakeMcpServer` canned responses, monkeypatch seam, `$0/tick`) is operational guidance; D7 codifies the **architectural contract** that the drift detector enforces.

---

## Rationale

1. **Single source of truth for tool names.** `server.py` is the canonical tool surface (per ADR-032 R1). The bridge is a derived projection for sync graph calls. Inverting the relationship would silently grow agent surface — exactly the M11 G-2 finding.

2. **Read-only plumbing preserves ADR-013.** Phase 8.2 SPEC §1 locks scope to read-only MCP calls. Writing math/policy/scoring results back to vault would violate the canonical-scope discipline (IKIGAI = planner only). D3 + D4 enforce this: `surface_intentions` stays stubbed (no PAV math surface), `tag_and_persist` is read-only (no vault_write).

3. **Asymmetric bridge ⊆ server is the right shape.** `server.py` registers 11 `@MCP.tool` decorators (8 IKIGAI + 3 Plan C investigation queue). `mcp_bridge.py` exports 1 wrapper (`ikigai_decompose`). The asymmetry is by design: server can expose tools for non-graph consumers (CLI, future A2UI) without forcing every tool to have a sync wrapper.

4. **OTel spans give failure isolation.** Each bridge wrapper dispatches via `_call` with its own name → OTel span `ikigai.bridge.{tool_name}` captures latency + errors uniformly. Per-wrapper exception handlers (the M11 silent-failure pattern) are forbidden; the single dispatch point is the only place errors surface.

5. **`FakeMcpServer` cost is zero.** Canned-response mock with monkeypatch seam = `$0/tick, <1s/run` per Phase 8.2 SPEC §6. Real OTel-on-FastMCP integration tests are deferred to Phase 8.3 (D5 + D6 are still load-bearing but enforced via binding contract, not via E2E test).

6. **Stdio binary-mode is a Windows landmine.** Per the memory entry `windows-stdio-binary-mode-fix-2026-08-30.md`, any new MCP stdio handshake MUST use `sys.stdin.buffer.readline()` not `sys.stdin.readline()` — commit `b93a1f3` documented the bug class. D6 inherits the fix.

7. **Reversibility favors additive wrappers.** Adding a wrapper is a 3-line edit; removing a wrapper is a 1-line delete. Adding a server tool is a `@MCP.tool(name=...)` decorator + handler. Removing a server tool requires removing the wrapper in the same commit (drift detector trips). Neither direction requires an ADR — only changing the contract (e.g., making bridge ⊇ server, adding a 13th `IKIGAI_TOOLS`, wiring vault_write in `tag_and_persist`) requires an ADR per D2 + D4.

---

## Implementation Rules

**R1 — New MCP tools go through `server.py` FIRST, then optional bridge wrapper.** Adding a tool requires:
1. `@MCP.tool(name="ikigai_<name>", description=...)` decorator + handler in `src/ikigai/src/mcp_server/server.py` (canonical surface)
2. **OPTIONAL:** `def ikigai_<name>(...)` wrapper in `src/ikigai/src/agents/v2/mcp_bridge.py` (only if a v2 node needs to call it synchronously)
3. Drift detector passes (both grow together, or neither — never just the wrapper)

If both files grow in the same commit, `test_mcp_bridge_wrapped_tool_count_matches_canonical` passes. If only one grows, the drift detector fails.

**R2 — Drift tests grow when tools grow.** Adding a new tool MUST be accompanied by:
- `@MCP.tool` registration in `server.py`
- (Optional) `def ikigai_*` wrapper in `mcp_bridge.py`
- Drift test PASS (no test edits required for simple additions)
- If tool count changes (e.g., adding a 3rd Plan C tool makes server_tools > 11), `test_ikigai_tools_count_is_12` MAY need re-evaluation — `IKIGAI_TOOLS` (12) and `server_tools` (11+3=14) are different variables and have separate drift detectors

**R3 — PAV-flavored wrappers are FORBIDDEN.** Per ADR-013 §"OUT OF SCOPE":
- Math/policy/scoring tools (`ikigai_score`, `ikigai_regime`, `ikigai_phase`, `ikigai_corrections`, `ikigai_plan_cycle`, `ikigai_checkpoint`, `ikigai_sync_vault` etc.) MUST NOT appear in `mcp_bridge.py`.
- Adding a PAV-flavored wrapper = violating ADR-013 = violating this ADR.
- The M11 L4 G-1 silent failure (V5-E `b960e852` deleted PAV-math tools from `server.py` but `mcp_bridge.py` kept wrappers) MUST NOT recur.

**R4 — `surface_intentions` stays as prompt-chain stub.** No bridge wrapper for `surface_intentions` until either ADR-013 is amended to permit PAV math reads OR a non-PAV observation surface is added.

**R5 — `tag_and_persist` is READ-ONLY.** Writes to vault (creating tagged artifacts, persisting new tags) route through `vault_write` per ADR-012 R3 / ADR-032 §"neutral". `tag_and_persist` bridge wrapper reads tags only; if a v2 node requires writing, it MUST call `vault_write` directly — not `tag_and_persist`.

**R6 — OTel span prefix is `ikigai.bridge.{tool_name}`.** Every `_call(tool_name, args)` opens a span with that name. Server-side spans from `mcp_server/tracing.py` use `ikigai.mcp.{tool_name}`. The two prefixes MUST NOT collide (mappers and trace exporters rely on the distinction).

**R7 — Windows stdio binary-mode is mandatory.** Any stdio handshake uses `sys.stdin.buffer.readline()` not `sys.stdin.readline()`. Per commit `b93a1f3` and the memory entry `windows-stdio-binary-mode-fix-2026-08-30.md`.

**R8 — Drift detector load-bearing.** `test_mcp_bridge_wrapped_tool_count_matches_canonical` is the canonical enforcement for D1 + D7. Bypassing it (commenting out, narrowing regex, adding names to the exclusion list without an ADR) is FORBIDDEN per ADR-032 R5.

---

## Consequences

### Positive

- **8/11 v2 graph nodes wired to canonical MCP gateway.** Real executor calls replace prompt-chain stubs. No silent drift between v2 nodes and server-side handler logic.
- **Single canonical tool surface.** `server.py` is the only source of truth for tool names; `mcp_bridge.py` is a derived projection; `IKIGAI_TOOLS` is the planner-exposed subset (gated at 12 per ADR-013).
- **Prevents M11 silent-failure re-occurrence.** Per ADR-032 R1: any wrapper referencing a non-existent server tool trips the drift detector immediately. The 9 PAV-flavored wrappers that were silently no-ops for ~5 days (`b960e852` → `9980f22` → `80bedf9` → `ed2803b` window) cannot recur.
- **OTel observability intact.** R6 keeps `_call` as the single dispatch point; OTel spans `ikigai.bridge.{tool_name}` capture latency and errors uniformly.
- **Test seam at zero cost.** `FakeMcpServer` canned-response mock with monkeypatch seam = `$0/tick, <1s/run` per Phase 8.2 SPEC §6. Drift tests live in `src/ikigai/tests/test_drift_extended_invariants.py` and run on every CI cycle.
- **Reversible without ADR.** Adding/removing wrappers (not server tools) is a 1-3 line edit; no ADR required. The drift detector validates the change.

### Negative

- **1 drift detector to maintain.** `test_mcp_bridge_wrapped_tool_count_matches_canonical` is load-bearing per ADR-032 R5; if it breaks (false positive) every CI run fails. Per Phase 8.2 SPEC §3 — "drift tests grow with the system; weakening them is forbidden."
- **Cross-platform regex brittleness.** The detector uses regex to discover tools. Edge cases (multi-line decorators with comments, decorators spanning many lines, nested scopes) need careful maintenance. Per ADR-032 §"Negative — cross-platform regex brittleness."
- **`surface_intentions` is permanently stubbed.** Until either ADR-013 is amended or a non-PAV observation surface is added, `surface_intentions` reads PAV-written state via prompt-chain renderer — no MCP call, no OTel span, no drift enforcement. This is by design (D3) but documented as deferred scope.
- **No coverage of handler bodies.** D1 + D7 pin the **registration** surface, not the handler behavior. A wrapper registered correctly in `server.py` may still route to a handler that reads PAV-written vault artifacts (e.g., `ikigai_observe_state` reads `vault/ikigai/cycle-state.md`). Handler-body attribution is enforced by ADR-013 + separate drift tests, not by this contract.
- **3 nodes do not benefit from Phase 8.2.** `dispatch_sub_agents` + `commit_summary` are in-process; `surface_intentions` is deferred. Operators using these 3 nodes get no fast-path-to-server improvement.
- **`FastMcpClient` stdio binding is a Phase 8.3 dependency.** Per Phase 8.2 SPEC §"Out of Scope" — Phase 8.2 only wires MCP calls; the actual production stdio binding ships in Phase 8.3 (D6). Until Phase 8.3 ships, the bridge is exercised via `FakeMcpServer` only.

### Neutral

- **`ikigai_helper` is the only reserved exclusion.** Per ADR-032 §"neutral", `ikigai_helper` may be added later without server registration. This is documented as a purely-internal helper; adding other names to the exclusion list requires an ADR.
- **`IKIGAI_TOOLS = 12` is the planner surface, not the server or bridge surface.** Per ADR-032 §"neutral": "Bridge wrappers reference **server-registered** tools, not `IKIGAI_TOOLS` entries." The 12 count is a separate drift detector (`test_ikigai_tools_count_is_12`); this ADR does not amend it.
- **`tag_and_persist` write path is unchanged.** Writes to vault continue to route through `vault_write` (per ADR-012) — this ADR does NOT add a write path for `tag_and_persist`; it only formalizes the read-only bridge wrapper.

---

## Alternatives Considered

### Alt A — Single mega-ADR covering all MCP decisions

Merge ADR-032 (bridge-wrapper drift contract), ADR-034 (Phase 8.2 wiring), and a future ADR for Phase 8.3 (observability + binding) into a single document.

- **Rejected**: scope too broad. Each ADR addresses a distinct architectural layer (registry contract vs node-wiring contract vs observability contract). Per the ADR-031 §"Architecture" pattern: each layer is its own ADR so drift detectors can target specific invariants.

### Alt B — Skip the ADR, rely on the Phase 8.2 spec

The 7 decisions are already locked at spec level (`docs/superpowers/specs/2026-09-08-phase-8-2-wiring-design.md:14-65`). Specs are operational recipes; ADRs are durable contracts. Master-04 attribution gap is "decisions locked at spec level without ADR."

- **Rejected**: insufficient documentation. Specs are tactical and disposable; ADRs are durable. The drift detector changes that would invalidate the spec would NOT necessarily update the spec but MUST update the ADR. Per the Master-04 attribution gap closure: "even though the spec covers the decisions, the ADR is needed as the durable contract."

### Alt C — Make all 11 v2 nodes backed by MCP

`surface_intentions`, `dispatch_sub_agents`, `commit_summary` — wire all of them.

- **Rejected**: violates ADR-013. `surface_intentions` reads PAV-written state; creating an MCP-callable PAV observation surface would be PAV math in the agent layer (forbidden). `dispatch_sub_agents` and `commit_summary` are explicitly in-process per Phase 8.2 SPEC §5 T-8.2.3 — adding MCP wrappers would force them into the async-or-die pattern (per ADR-032 Alt E rejection rationale).

### Alt D — Use HTTP+SSE transport instead of stdio for v2 graph → FastMCP

ADR-011 (HTTP+SSE transport for IKIGAI MCP) is on the Proposta deck. Standardizing on HTTP+SSE would unify with the fork-MCP transport layer.

- **Rejected**: stdio is the canonical Phase 8.3 binding per the architecture (and per Windows quirks — fork MCP was stdio-first per the `windows-stdio-binary-mode-fix` memory entry). HTTP+SSE is a future ADR per ADR-011 §"Recommended for acceptance". The architectural decision to use stdio is intentional, not deferred.

### Alt E — Drop `mcp_bridge.py`; v2 nodes call MCP async directly

Make every v2 node `async def`, drop `mcp_bridge.py`, await `_server.call(...)` directly.

- **Rejected**: per ADR-032 Alt E rejection — breaks the sync invocation surface (`v2.py:241 compiled.invoke({})`). Bridge is the right boundary for sync-or-async compatibility. Same pattern as ADR-026 dispatcher wrapping both sync and async sub-agents.

### Alt F — Per-wrapper OTel span naming convention instead of D5 contract

Document the span naming as convention, not enforcement. Skip the R6 implementation rule.

- **Rejected**: this is the pre-M11 state. Conventions go stale; tests + contracts don't. The M11 review explicitly identified the lack of drift enforcement as a contributing factor to the silent failure. D5 + R6 enforce via code, not documentation.

---

## Cross-references

### Load-bearing prior ADRs

- **ADR-032 — Bridge-Wrapper Drift Contract** (Accepted 2026-09-21) — locks `mcp_bridge.py ⊆ server.py`. **D1 of this ADR inherits ADR-032 R1-R3 unchanged**; D7 enforcement invariant (`test_mcp_bridge_wrapped_tool_count_matches_canonical`) is ADR-032 R5.
- **ADR-013 — Canonical scope discipline** (Accepted 2026-08-31) — IKIGAI = planner only; math/policy/scoring tools forbidden in `IKIGAI_TOOLS`. **D2 of this ADR inherits ADR-013 §"OUT OF SCOPE" unchanged**; R3 (PAV-flavored wrappers forbidden) codifies it.
- **ADR-012 — Fork-connection architecture** (Accepted 2026-08-30) — fork-MCP transport + registry layers. **D6 stdio binding is the v2-graph analogue** of ADR-012's stdio transport contract.

### Related decisions

- **ADR-009 — Pydantic v2 strict** (Accepted 2026-08-31) — bridge wrappers return `dict[str, Any]`; Pydantic models are constructed at the call-site, not in the wrapper. Same pattern as ADR-032.
- **ADR-019 — QHE → prompt-template constants** (Proposed 2026-09-04) — bridge wrappers don't carry tuning constants; no extension to ADR-019.
- **ADR-025 — Skill binding mechanism** (Accepted 2026-09-04) — bridge wrappers are called by v2 nodes, which are bound via ADR-025's YAML manifest; the bridge is one layer below the manifest binding.
- **ADR-026 — Sub-Agent Dispatch Protocol** (Accepted 2026-09-05) — `dispatch_sub_agents` v2 node is in-process; ADR-026 covers sub-agent dispatching; D6 stdio binding is the FastMCP analogue for v2 graph → gateway.
- **ADR-031 — Meta-Planner Design** (Accepted 2026-09-05) — `invoke_skill("meta_plan")` entry point; meta-planner wires through `wrap_vault_write` (ADR-029) + `taskdog_create_task` (W3.6 Path 1). This ADR does not amend ADR-031.

### Code references

- `src/ikigai/src/agents/v2/mcp_bridge.py:1-37` — module docstring documenting the bridge architecture, post-M12 wrapper state, and OTel span contract
- `src/ikigai/src/agents/v2/mcp_bridge.py:60-110` — `_call` helper with OTel span `ikigai.bridge.{tool_name}` (R6 enforcement)
- `src/ikigai/src/agents/v2/mcp_bridge.py:109-112` — `ikigai_decompose` wrapper (only surviving bridge wrapper post-M12)
- `src/ikigai/src/mcp_server/server.py:39-40` — `MCP = FastMCP("ikigai-gateway")` registry init
- `src/ikigai/src/mcp_server/server.py:49` — section header "11 total (8 IKIGAI + 3 Plan C investigation)"
- `src/ikigai/src/mcp_server/tracing.py:traced_tool_dispatch` — server-side OTel span emitter `ikigai.mcp.{tool_name}` (distinct from bridge prefix per R6)
- `src/ikigai/src/agents/v2/nodes/*.py` — 11 v2 nodes; 8 wired to mcp_bridge, 1 in-process (`dispatch_sub_agents`), 2 stubs (`commit` in-process summary, `surface_intentions` PAV-renderer)
- `src/ikigai/src/agents/v2/tests/fixtures/fake_mcp_server.py` — `FakeMcpServer` canned-response mock (Phase 8.2 SPEC §6)
- `src/ikigai/tests/test_drift_extended_invariants.py:299-374` — D1 + D7 enforcement (`test_mcp_bridge_wrapped_tool_count_matches_canonical`)
- `src/ikigai/tests/test_canonical_scope.py:493-534` — `test_ikigai_tools_count_is_12` (gates R3 PAV-flavored wrappers forbidden)

### Memory / review references

- `memory/system-review-gaps-2026-09-12.md` — M11 IKIGAI Agentic System Review, 41 gaps; L4 G-1 is the bridge-wrapper silent failure that D1 + D7 prevent
- `memory/m12-bottom-up-infra-shipped-2026-09-14.md` — M12 P0 attribution fixes; T-12.1 added the drift test + removed 8 PAV-flavored wrappers
- `memory/phase-8-2-wiring-shipped-2026-09-08.md` — Phase 8.2 SHIPPED (45/45 PASS, $0, `invsd0f22`)
- `memory/phase-8-3-shipped-2026-09-08.md` — Phase 8.3 SHIPPED (65/65 PASS, $0, OTel bridge spans + FastMcpClient stdio binding + tech debt cleanup)
- `memory/windows-stdio-binary-mode-fix-2026-08-30.md` — Windows stdio binary-mode fix; R7 inherits the fix
- `docs/superpowers/specs/2026-09-10-system-review-diagnosis.md` — M11 diagnosis doc (288 lines, 5 cross-cutting themes)
- `docs/superpowers/specs/2026-09-08-phase-8-2-wiring-design.md` — Phase 8.2 spec (SOT for D1-D7, SOT-loaded into this ADR)

### Spec status (where the tactical execution lives)

Phase 8.2 spec status (as of 2026-09-21):
- T-8.2.1 PAV-observation reads (4 nodes: observe, score_vectors, heuristics, balance) — all 4 mcp_bridge wrappers REMOVED in M12 (PAV-flavored violation)
- T-8.2.2 Vault/state reads (4 nodes: decompose, plan, reflect, tag_and_persist) — 1 surviving wrapper (`ikigai_decompose`); `tag_and_persist` read-only branch wired under D4
- T-8.2.3 In-process nodes + e2e (2 nodes: dispatch_sub_agents, commit) — both in-process, no MCP wrappers
- `surface_intentions` — deferred per D3 (no MCP surface)

Phase 8.3 spec status:
- OTel bridge spans + FastMcpClient stdio binding — D5 + D6 ship here
- Tech debt cleanup (65/65 PASS)

This ADR formalizes the architectural contract that the 2-phase spec execution (8.2 + 8.3) delivered. The spec is retained as a historical tactical execution document; the ADR is the durable contract.

---

*ADR-034 — accepted 2026-09-21 — locks the 7 Phase 8.2 design decisions as a durable architectural contract; drift detector load-bearing via `test_mcp_bridge_wrapped_tool_count_matches_canonical` (ADR-032 inheritance); Phase 8.3 observability + stdio binding formalized as D5 + D6*
