# Phase B7 — Agent Layer Activation: vault ↔ agent ↔ forks round-trip

**Status:** DRAFT 2026-08-30 (audit + spec)
**Author:** main session (autonomous, post-compact)
**Scope:** Phase B7 in the rev.3 backend sequence
**Predecessor:** Phase B6 vault sync (✅ SHIPPED `phase-b6-vault-sync-shipped-2026-08-29`) + Combo A bidirectional (✅ SHIPPED `phase-b6-combo-a-bidirectional-vault-sync-shipped-2026-08-29`)
**Successor:** B8 (algorithm work, **only if B7's system-readiness ADR opens the gate**)

---

## 1. Context

Per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] (CANONICAL), the build order is strictly:

```
backend → data → agent → algorithms (LAST)
```

The backend layer is closed (B0–B5.B + B2 start/stop `0e82e4e`). The data layer closed with Phase B6 vault sync + Combo A bidirectional. The **agent layer is the next gate**.

### 1.1 What the agent layer needs to do (canonical flow)

Per [[master-branch-carro-chefe-2026-08-28]]:

> **master = deep-agent (AI-native) bidirectionally syncing forks-prontas ↔ vault local `.db.markdown`**

The agent loop, end-to-end:

```
vault/*.md (canonical NL planning)
   │  vault_read + strategics loader
   ▼
Deep Agent (applies PAE, derives tasks)
   │  enqueue(TaskChange)
   ▼
data/review_queue/<id>.json
   │  agent_propagator
   ▼
forks (cli / taskdog / solverforge-calendar)
   │  reverse_sync (fork → vault via vault_write)
   ▼
vault/*.md (cycle log + TaskChange resolution)
```

### 1.2 What's actually shipped vs. what's missing (audit)

| Component | Status | Source |
|---|---|---|
| `vault_write` MCP tool | ✅ SHIPPED (B6.7) | `src/ikigai/src/mcp_server/server.py:776` |
| `vault_read` MCP tool | ❌ MISSING | n/a — no tool, no resource |
| Strategics loader (PT-BR → agent context) | ❌ MISSING | `./strategics/*.md` exists, no reader |
| `ikigai_maintainer` graph (8-node) | ✅ REAL | B5.0 + B5.1 |
| `agent_consumer.py` (queue → adapters) | ⚠️ MVP 75 LOC | B5.2 (F6 closed) |
| `agent_propagator.py` (TaskChange → adapters) | ⚠️ MVP 103 LOC | B5.B |
| `reverse_sync` (taskdog → vault via TaskChange) | ✅ SHIPPED | B6.6 |
| `IKIGAiAgenticWriter` (`agentic_writer.py`) | ⚠️ ORPHANED | pre-attribution, still in tree |
| End-to-end round-trip test | ❌ MISSING | no integration test |
| F8 multi-tool MCP chain test | ❌ OPEN | B5.0 audit |
| F11 `run_chat()` 270-line REPL refactor | ❌ OPEN | B5.0 audit |
| Algorithm gate evaluation ADR | ❌ MISSING | per [[algorithm-gate-system-readiness-not-…]] |

**Critical gap:** the agent harness in `src/ikigai/src/agents/tools.py` has 17 deepagent tools, but **NONE reads vault markdown**. All read paths are:
- `_read_checkpoint_data()` → SQLite msgpack
- `_decompose_ueid()` → in-memory helper
- Subprocess wrappers → external CLIs

The attribution report ([[algorithm-attribution-decisions-2026-08-29]]) says `./strategics/ PT-BR is SOT for instructions`, but no agent loader actually reads it. The current agent loop is **self-referential** (cycle → checkpoint → cycle), not **vault-grounded**.

### 1.3 Attribution §7 violation still open

`src/ikigai/src/ikigai/vault/agentic_writer.py` (57 lines) is a parallel writer to `vault_write.py` (121 lines, canonical). The attribution report §7 says vault_write is the **ONLY** vault writer. `agentic_writer.py` should be either:
1. Routed through `vault_write()` (canonical path), OR
2. Removed if unused

This is a hygiene item, not a runtime defect (it uses VaultLock + frontmatter, so it works), but the dual-writer pattern is exactly what §7 forbids.

---

## 2. Goal

**Activate the agent layer so vault ↔ agent ↔ forks round-trip is functional and demonstrable end-to-end.** Then evaluate whether the algorithm gate can open per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]].

This is the gate condition for **any** algorithm work (M01/N01/A02/A06, IKIGAI weights, scoring math). Until the round-trip is verified, no algorithm code ships.

---

## 3. Non-goals (out of scope)

- **No algorithm work.** Vector scoring, Q_HE, regime FSM, kill conditions, persona arithmetic — all DEFERRED.
- **No fork connections** beyond what's already wired (taskdog). solverforge-calendar + tuiboard stay DEFERRED per [[fork-connection-defer-2026-08-30]].
- **No A2UI** — spec-only per [[ai-native-strategic-model-migration-2026-08-26]].
- **No PAV activation** — backend control plane only per [[interfaces-architecture-2026-08-27]].
- **No src/operational/ test rot** — separately maintained workspace.
- **No net-new MCP gateway tools** beyond `vault_read` (B7.1).

---

## 4. Architecture (target)

```
┌────────────────────────────────────────────────────────────────────┐
│  Layer 3 (upgraded) — AGENT LAYER (vault-grounded)                  │
│                                                                     │
│  src/ikigai/src/agents/tools.py  (deepagent LangChain @tool surface)│
│   ├─ ikigai_read_strategics()  ← NEW B7.2: loads ./strategics/*.md │
│   ├─ ikigai_read_vault(path)   ← NEW B7.1: vault_read MCP bridge  │
│   ├─ ikigai_plan_cycle()        (existing — passes vault context)  │
│   ├─ ikigai_sync_vault()        (existing — writes via vault_write)│
│   └─ ... + 13 existing tools unchanged                              │
│                                                                     │
│  src/ikigai/src/mcp_server/server.py  (MCP gateway)                │
│   └─ vault_read()  ← NEW B7.1: 14th tool, mirrors vault_write      │
│                                                                     │
│  src/ikigai/src/ikigai/vault/                                       │
│   ├─ vault_read.py   ← NEW B7.1: read-side mirror of vault_write   │
│   └─ agentic_writer.py ← DELETE B7.5 (orphaned, §7 violation)      │
│                                                                     │
│  src/ikigai/src/strategics/loader.py  ← NEW B7.2: PT-BR loader     │
│                                                                     │
│  tests/e2e/test_vault_agent_round_trip.py  ← NEW B7.4: full loop   │
│  tests/ikigai/test_vault_read.py           ← NEW B7.1: unit        │
│  tests/ikigai/test_strategics_loader.py    ← NEW B7.2: unit        │
│  tests/mcp/test_multi_tool_chain.py        ← NEW B7.6 (F8)         │
│                                                                     │
│  docs/architecture/2026-08-30-system-readiness-adr.md  ← NEW B7.7  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 5. Tasks (decomposition)

### Task B7.1 — `vault_read` MCP tool + `vault_read.py` (read-side mirror of `vault_write`)

**Files:**
- Create: `src/ikigai/src/ikigai/vault/vault_read.py` (~80 LOC)
- Modify: `src/ikigai/src/mcp_server/server.py` (~+30 LOC for `vault_read` MCP tool)
- Create: `src/ikigai/tests/test_vault_read.py` (~10 tests)
- Create: `tests/mesh/test_vault_read_path_traversal.py` (~3 tests, security)

**Spec:**
- `vault_read(vault_path: str) -> dict[frontmatter, body, sha256, mtime]`
- Mirror vault_write security model:
  - Reject absolute paths
  - Reject paths resolving outside vault_root
  - VaultLock (shared reader lock, not exclusive writer lock)
- Use `frontmatter.loads()` (read-side, no atomic write)
- Return `{frontmatter: dict, body: str, sha256: str, mtime: float}`

**Acceptance:**
- 10+ unit tests (frontmatter parsing, path traversal, missing file)
- 3+ security tests (absolute path, .., symlink escape)
- Smoke: `vault_read("ikigai/meta/index.md")` returns parsed dict + body

**Mirror vault_write patterns:**
- Same vault_root anchor + resolve + relative_to guard
- Same VaultLock (read can share lock since reads don't conflict)
- Same frontmatter library (loads vs dumps)

### Task B7.2 — Strategics loader (PT-BR → agent context)

**Files:**
- Create: `src/ikigai/src/strategics/__init__.py`
- Create: `src/ikigai/src/strategics/loader.py` (~120 LOC)
- Create: `src/ikigai/tests/test_strategics_loader.py` (~8 tests)

**Spec:**
- `load_strategics(vault_root: Path) -> StrategicsContext`
- Reads `./strategics/*.md` (PT-BR), parses frontmatter, returns:
  - `documents: list[StrategicDoc]` (title, tags, body, sha256)
  - `by_tag: dict[tag, list[StrategicDoc]]`
  - `index: str` (concatenated body for prompt injection)
- Filter: only files with `tags: [strategic]` or frontmatter present
- Append-only invariant: loader does NOT write

**Why:**
- [[algorithm-attribution-decisions-2026-08-29]] §1: `./strategics/` is SOT for instructions
- Current agent has no loader — `strategics/*.md` exists but is dead text
- B7.3 uses this loader to ground `ikigai_plan_cycle` in real instructions

**Acceptance:**
- 8+ unit tests (load, filter by tag, empty dir, parse errors)
- Smoke: prints 3 doc titles from `./strategics/`

### Task B7.3 — Wire agent to vault_read + strategics in `ikigai_plan_cycle`

**Files:**
- Modify: `src/ikigai/src/agents/tools.py` (`ikigai_plan_cycle` ~+20 LOC)
- Create: `src/ikigai/src/agents/ikigai_read_strategics.py` (~30 LOC, LangChain @tool)
- Create: `src/ikigai/src/agents/ikigai_read_vault.py` (~30 LOC, LangChain @tool)
- Modify: `IKIGAI_TOOLS` list (`tools.py:965`) — register 2 new tools

**Spec:**
- Add `ikigai_read_strategics()` → returns summarized strategics as text
- Add `ikigai_read_vault(vault_path: str)` → calls vault_read MCP tool
- `ikigai_plan_cycle()` now passes strategics + vault context into graph state
- Graph `observe` node reads vault before scoring (currently reads only checkpoint)

**Acceptance:**
- New tools exposed in deepagent tool list
- `ikigai_plan_cycle` does not regress on existing 10/10 plan_cycle tests
- F11 partial: extracted vault-loading logic into standalone functions

### Task B7.4 — End-to-end round-trip test (vault → agent → forks → vault)

**Files:**
- Create: `src/ikigai/tests/e2e/test_vault_agent_round_trip.py` (~5 tests, 1 happy-path + 4 edge cases)
- Create: `docs/superpowers/specs/2026-08-30-vault-agent-e2e-trace.md` (the test trace as artifact)

**Spec:**
- **Happy path:** create `vault/plans/q3/test-task.md` → invoke agent via MCP `ikigai_plan_cycle` → assert TaskChange enqueued in `data/review_queue/` → run propagator → assert taskdog has the task → invoke `ikigai_sync_vault` → assert vault file updated
- **Reverse path:** mark task done in taskdog → invoke `reverse_sync` → assert new TaskChange in queue → invoke `vault_write` → assert vault file reflects `status: done`
- **Edge cases:** vault file deleted mid-loop, queue consumer crash mid-batch, MCP server absent (must degrade gracefully per B5.0 F13)

**Acceptance:**
- 1 happy-path E2E passes in CI
- 4 edge cases pass (or documented graceful failure)
- Trace artifact saved as `.md` (reference doc, not test output)

### Task B7.5 — Deprecate `agentic_writer.py` (attribution §7)

**Files:**
- Modify: `src/ikigai/src/ikigai/vault/agentic_writer.py` (route through vault_write, OR)
- Delete: `src/ikigai/src/ikigai/vault/agentic_writer.py` (if unused)

**Investigation first:** grep for `IKIGAiAgenticWriter` usage. If zero callers → delete. If callers exist → refactor to call `vault_write()` internally.

**Acceptance:**
- Zero references to `IKIGAiAgenticWriter` outside the module
- Or: `agentic_writer.py` rewritten as thin wrapper over `vault_write`
- ruff + mypy clean

### Task B7.6 — Multi-tool MCP chain test (F8 from B5.0 audit)

**Files:**
- Create: `src/ikigai/tests/mcp/test_multi_tool_chain.py` (~6 tests)

**Spec:**
- Spawn FastMCP server in subprocess
- Drive a chain via stdio: `vault_read` → `ikigai_plan_cycle` → `vault_write` (with content derived from step 1)
- Verify each tool call returns expected JSON
- Verify chain completes in <5s for empty vault

**Acceptance:**
- 6+ tests pass
- Closes B5.0 audit finding F8
- New test uses same `python scripts/mcp_inspect.py` pattern from B3

### Task B7.7 — System readiness ADR (algorithm gate evaluation)

**Files:**
- Create: `docs/architecture/2026-08-30-system-readiness-adr.md` (~150 LOC)

**Spec:**
- Apply the [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] checklist:
  1. Backend layer functional? (mesh, queue, MCP gateway, CLI, server mgmt) — ✅ YES, all shipped
  2. Data layer functional? (vault/data/ runtime, sync contracts, persistence verified) — ✅ YES after B6/Combo A
  3. Agent layer functional? (Deep Agent harness reads/writes contracts + data) — ✅ YES after B7.1–B7.4
- Decision matrix for each algorithm component:
  - M01 (vector scoring) — DEFER or SHIP? depends on strategist validation
  - N01 (regime thresholds) — DEFER (math auditing still WIP per memory)
  - A02 (Q_HE formula) — DEFER (3 divergent formulas; user must decide)
  - A06 (kill conditions) — DEFER (depends on M01+N01+A02)
  - IKIGAI weights — DEFER until user explicit override per [[user-revenue-weight-preference]]
- Final verdict: gate is **OPEN for [X], CLOSED for [Y]**
- Reference: [[algorithm-issues-registry-2026-07-02]] 31 issues still pending user decision

**Acceptance:**
- ADR committed
- Each algorithm component has explicit DEFER / SHIP / PARTIAL verdict
- Cross-references all relevant memories

---

## 6. Acceptance criteria (whole B7)

1. ✅ All 7 tasks shipped with tests passing
2. ✅ `vault_read` MCP tool registered + tested
3. ✅ Strategics loader serves `./strategics/*.md` to agent
4. ✅ End-to-end vault ↔ agent ↔ taskdog ↔ vault round-trip demonstrable
5. ✅ B5.0 audit F8 closed (multi-tool MCP chain test)
6. ✅ F11 partial progress (vault loading extracted; run_chat refactor deferred to B7.x or B8)
7. ✅ Attribution §7 violation resolved (agentic_writer.py removed or refactored)
8. ✅ System readiness ADR committed with explicit per-component verdicts
9. ✅ No algorithm code added (gate still closed until ADR says otherwise)

---

## 7. Dependencies

**Hard prerequisites (all SHIPPED):**
- B0-B6 backend + data layers (✅)
- `vault_write` MCP tool (✅ B6.7)
- Combo A bidirectional sync (✅ B6.6)
- ikigai_maintainer graph (✅ B5.0)
- agent_consumer / agent_propagator MVP (✅ B5.B)

**Soft prerequisites (deferrable):**
- F11 run_chat refactor — partial in B7.3, full refactor can be B7.x or B8
- src/operational/ test rot — out of scope (separately maintained)

---

## 8. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `vault_read` path traversal | HIGH | Mirror vault_write's `relative_to` guard + 3 security tests |
| Strategics loader adds latency to plan_cycle | MEDIUM | Cache loader output (mtime-keyed); reload only on file change |
| E2E test flakiness from subprocess MCP | MEDIUM | Use the same `mcp_inspect.py` polling pattern as B3 + adapter SSE wiring |
| B7.7 ADR forces premature algorithm decisions | LOW | ADR is documentation-only; defers until user explicitly unblocks per memory |
| F11 partial work blocks B7.4 | LOW | Defer full run_chat refactor to B7.x; B7.3 only extracts vault-loading helpers |
| agentic_writer.py has hidden callers | MEDIUM | B7.5 grep + investigation BEFORE deleting |

---

## 9. Estimated effort

| Task | Effort | Severity | Critical path? |
|---|---|---|---|
| B7.1 vault_read | 2-3h | HIGH (security) | ✅ YES |
| B7.2 strategics loader | 2-3h | MEDIUM | ✅ YES |
| B7.3 wire agent | 2-3h | MEDIUM | ✅ YES |
| B7.4 E2E round-trip | 3-4h | HIGH (validation) | ✅ YES |
| B7.5 deprecate agentic_writer | 1h | LOW (hygiene) | ❌ parallel |
| B7.6 multi-tool chain (F8) | 2h | MEDIUM | ❌ parallel |
| B7.7 ADR | 1-2h | LOW (docs) | ❌ parallel |
| **Total** | **13-18h** | | |

**Critical path:** B7.1 → B7.2 → B7.3 → B7.4 → B7.7 (sequential)
**Parallel:** B7.5 + B7.6 can run in parallel with critical path

---

## 10. Open questions for user (deferred to plan phase)

1. **B7.4 E2E trace artifact** — save as `.md` under `docs/superpowers/specs/` (test documentation)? Or skip and let pytest output be the trace?
2. **B7.7 ADR verdict threshold** — what counts as "system readiness" for each algorithm component? User's call.
3. **B7.5 deletion vs refactor** — preference? Both satisfy attribution §7.
4. **F11 full refactor timing** — within B7.3, or as separate B7.x?

---

## 11. Related memories

- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — gate criterion B7.7 applies
- [[master-branch-carro-chefe-2026-08-28]] — agent canonical flow B7 implements
- [[algorithm-attribution-decisions-2026-08-29]] — strategics/ SOT, vault_write ONLY writer
- [[backend-topology-diagnosis-2026-08-30]] — current state pre-B7
- [[fork-connection-defer-2026-08-30]] — fork scope (taskdog only, others deferred)
- [[b5-0-audit-findings-2026-08-29]] — F8 + F11 closed partially by B7
- [[phase-b6-vault-sync-shipped-2026-08-29]] — B6 predecessor
- [[phase-b6-combo-a-bidirectional-vault-sync-shipped-2026-08-29]] — Combo A predecessor
- [[combo-a-whole-branch-review-backlog-2026-08-29]] — Combo A review context

---

## 12. Status

DRAFT — needs user review for:
- Task decomposition granularity (7 tasks vs. consolidated into 4)
- ADR threshold for B7.7
- Effort estimates (5-week sprint vs. compressed)

Next step: convert to implementation plan via `superpowers:writing-plans` skill, then execute task-by-task via `superpowers:subagent-driven-development`.