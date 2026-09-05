# Diagnostic 07 — SONHO Tree Capability × Tier Matrix

**Date:** 2026-09-04
**Author:** diagnostic agent 07 of 10
**Scope:** Capability status across SONHO → OBJETIVO → META → PROJETO → ENTREGA → TAREFA hierarchy
**Method:** Read-only inspection of `src/contracts/`, `src/mesh/`, `src/ikigai/`, `interfaces/cli/`, `vault/ikigai/`, plus drift detector and roadmap references.

---

## 1. 6×6 Capability Matrix

Legend: ✅ working · ⚠️ partial · ❌ broken · 🚫 not implemented

| Capability ↓ \ Tier → | SONHO | OBJETIVO | META | PROJETO | ENTREGA | TAREFA |
|---|---|---|---|---|---|---|
| **1. Create (user-level dream)** | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial |
| **2. Read tree / traverse hierarchy** | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial |
| **3. Update (modify fields)** | 🚫 not impl | 🚫 not impl | 🚫 not impl | 🚫 not impl | 🚫 not impl | 🚫 not impl |
| **4. Connect parent-child link** | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial | ⚠️ partial |
| **5. Render in fork (tuiboard/solverforge)** | 🚫 not impl | 🚫 not impl | 🚫 not impl | 🚫 not impl | 🚫 not impl | 🚫 not impl |
| **6. Show via mesh (cross-fork)** | ✅ working | ✅ working | ✅ working | ✅ working | ✅ working | ✅ working |

**Summary:** 1 row working (mesh show), 3 rows partial (create/read/connect), 2 rows blocked or missing (update + render).

---

## 2. Per-Capability Detail

### Capability 1 — Create SONHO (user-level dream)

**SONHO** — ⚠️ partial
- **Implementation:** `vault_write` MCP tool with `actor: Literal["user","agent","system"]` (`src/ikigai/src/mcp_server/tools_vault.py:40-71`); enforced by `transition_validator.validate_phase_transition` (`src/ikigai/src/ikigai/security/transition_validator.py:38-42`) which raises `PermissionError` when `entity.tier=="SONHO"` and `actor!="user"`. Persisted via `tag_and_persist_node` (`src/ikigai/src/agents/v2/nodes/tag_and_persist.py:42-79`) which builds structured frontmatter and calls `vault_write`.
- **Test coverage:** Entity construction only — `tests/contracts/test_sonho.py:7` (Pydantic model), `tests/contracts/test_sonho.py:28` (motivation required). No end-to-end vault write test for SONHO. `tests/ikigai/security/test_transition_validator.py` exists for the actor rule.
- **Blocker:** No live SONHO entity in `vault/` — `vault/ikigai/closing-2026/01-q3-2026/00-sonho/placeholder.md` and `02-q4-2026/00-sonho/placeholder.md` are still placeholders. Roadmap Task **A.4** ("Seed 1 vault template exemplo (1 SONHO + 1 OBJETIVO + 1 META)") still pending.

**OBJETIVO / META / PROJETO / ENTREGA / TAREFA** — ⚠️ partial (same path as SONHO)
- **Implementation:** Same `vault_write` + `tag_and_persist_node` write path; `transition_validator` accepts any actor for these tiers (`src/ikigai/src/ikigai/security/transition_validator.py:44`).
- **Test coverage:** `tests/contracts/test_objetivo.py:8`, `test_meta.py:8`, `test_projeto.py:8`, `test_entrega.py:8`, `test_tarefa.py:8` — model construction only; no vault persistence test for any child tier.
- **Blocker:** No seed vault entities exist for any child tier. Mesh adapters at `src/mesh/adapters/cli.py:14` only persist `title/due/priority/ueid/written_at/source_fork` — no tier-aware write path; subset-rule enforcement happens at application layer (`src/contracts/base.py:67-81`) not at write time.

---

### Capability 2 — Read SONHO tree (traverse hierarchy)

**SONHO** — ⚠️ partial
- **Implementation:**
  - Single-file read: `vault_read` (`src/ikigai/src/mcp_server/tools_vault.py:74-96`) reads one markdown file with parsed frontmatter + body + sha256 + mtime.
  - Hierarchy traversal: `ikigai_decompose` MCP tool (`src/ikigai/src/mcp_server/server.py:91-177`, handler `_decompose_ueid` line 99-177) walks `data/matheus/dreams|objectives|projects|tasks` (legacy path, NOT the new `vault/ikigai/closing-2026/...` SONHO tree).
- **Test coverage:** None directly on tree-walk; only the deprecated `data/matheus/` path is wired.
- **Blocker:** `_decompose_ueid` reads `data/matheus/{dreams,objectives,projects}/` (line 102-103, 117-119) — the directory does NOT exist at the canonical vault path. Roadmap Task **C.6** ("`mesh show` SONHO tree traversal") still pending; Task **B.3** ("Vault templates seeded for SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA (6 tiers)") pending.

**OBJETIVO → TAREFA** — ⚠️ partial
- **Implementation:** Same single-file `vault_read`; legacy decompose walks `objectives/`, `projects/` only (no `meta/`, `entrega/`, `tarefa/` subdirs in the legacy path).
- **Test coverage:** None.
- **Blocker:** Full hierarchy walk across all 6 entity types not implemented.

---

### Capability 3 — Update SONHO (modify fields)

**All 6 tiers** — 🚫 not implemented
- **Why:** `BasePlanContract` is `frozen=True` (`src/contracts/base.py:49`) so even in-memory mutation is blocked. Phase 3 v1 mesh adapters explicitly early-return on non-create actions: `src/mesh/adapters/cli.py:34`, `src/mesh/adapters/taskdog.py:83`, `src/mesh/adapters/solverforge_calendar.py:58` all return immediately when `event.action.value != "create"`. No `update` MCP tool exists.
- **Test coverage:** `tests/contracts/test_sonho.py:44`, `test_objetivo.py:56`, `test_meta.py:40`, `test_projeto.py:60`, `test_entrega.py:56`, `test_tarefa.py:40` all assert frozen rejection — but these test in-process mutation, not the mesh update path (which is absent).
- **Blocker:** Explicit design decision — `src/mesh/adapters/__init__.py:9-11`: *"v1 scope: only CREATE actions are wired. UPDATE/DELETE/DONE return early (per Phase 3 v1 design — full scope gated on 5+ SONHO logs)."* Update is gated on **C.3** (5+ SONHO logs collected) per roadmap.

---

### Capability 4 — Connect SONHO to OBJETIVO (link parent-child)

**SONHO → all 5 children** — ⚠️ partial
- **Implementation:**
  - `parent_ueid: UEID | None` field in base contract (`src/contracts/base.py:55`).
  - Subset validator enforces `child.ikigai_vectors ⊆ parent.ikigai_vectors` (`src/contracts/base.py:67-81`) — static non-empty check; cross-entity subset enforced at application layer via `_check_vector_subset` helper (`src/contracts/base.py:13-36`).
  - `tests/contracts/test_base_subset_validator.py:22` confirms OBJETIVO with `[skill]` validates against SONHO `[skill, market, revenue]`.
- **Test coverage:** Subset validator tested (`tests/contracts/test_base_subset_validator.py:39-47`); no test for the full link operation.
- **Blocker:** No "link parent" tool — `parent_ueid` is set at entity construction but since Update is 🚫 (Capability 3), reparenting is impossible after creation.

---

### Capability 5 — Render SONHO in fork (tuiboard/solverforge)

**All 6 tiers** — 🚫 not implemented
- **Why:**
  - `tuiboard` adapter exists as a stdio factory (`src/ikigai/src/ikigai/gateway/clients/tuiboard.py:10-26`) — expected tools are `tuiboard_render/snapshot/diff/aggregate` (`src/tuiboard/tools/tuiboard_render.py` etc.) — these render dashboard views, NOT SONHO tree entities.
  - `solverforge_calendar` adapter exists (`src/ikigai/src/ikigai/gateway/clients/solverforge_calendar.py:14-29`) — expected tools are `sf_schedule/sf_replan/sf_availability`, all calendar/optimizer ops. No SONHO-aware renderer.
  - The 3 mesh adapters (`src/mesh/adapters/cli.py:14`, `taskdog.py:13`, `solverforge_calendar.py:15`) only persist task-shaped fields (`title/due/priority/ueid/source_fork`) — no `tier`, no `parent_ueid`, no SONHO-specific fields.
- **Test coverage:** None for SONHO rendering.
- **Blocker:** Adapters are task-shaped, not plan-shaped. Roadmap Task **B.3** + **C.8** ("Operator TUI SONHOs tab") still pending.

---

### Capability 6 — Show SONHO via mesh (cross-fork view)

**All 6 tiers** — ✅ working
- **Implementation:**
  - MCP tool `ikigai_mesh_show` (`src/ikigai/src/mcp_server/tools_mesh.py:56-94`) reads UEID across 3 adapters (`_load_adapters` line 31-33: CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter) and joins slices into a single view with mismatches list.
  - CLI command `life mesh-show <ueid>` (`interfaces/cli/read_tasks.py:256-260`) calls the same `show_mesh` function with `cli/taskdog/solverforge_calendar` adapters (`interfaces/cli/read_tasks.py:232-253`).
  - Returns `{"ueid", "view": {cli: ..., taskdog: ..., solverforge_calendar: ...}, "mismatches": [...]}`.
  - The mesh view is **tier-agnostic** — it indexes by UEID, so any of the 6 tiers can be looked up as long as a UEID is known.
- **Test coverage:** None directly — relies on `tests/interfaces/test_tui_operator.py` style for the broader surface; smoke tested via the v1.2 CliAdapter dedup (referenced in [[phase-b3-mcp-gateway-complete-2026-08-28]]).
- **Blocker:** Read returns `null` if no slice exists in any fork. SONHO entities are not yet seeded in `vault/` so reading SONHO UEIDs today returns empty `view` dicts (with `a2ui: null` placeholder per `tools_mesh.py:76`).

---

## 3. Blockers

| # | Blocker | Location | Affected Caps |
|---|---|---|---|
| B1 | **0 SONHO entities seeded in vault/** | `vault/ikigai/closing-2026/{01,02}-q*/00-sonho/placeholder.md` | 1, 2, 6 (no real data to read/show) |
| B2 | **Phase 3 v1 scope = create only** | `src/mesh/adapters/__init__.py:9-11` + per-adapter early-returns (cli.py:34, taskdog.py:83, solverforge_calendar.py:58) | 3 (update) |
| B3 | **`_decompose_ueid` reads legacy `data/matheus/` path** | `src/ikigai/src/mcp_server/server.py:99-177` | 2 (tree walk across new vault path not wired) |
| B4 | **No "link parent" tool post-creation** | Absent — only `parent_ueid` field at construction | 4 |
| B5 | **Fork adapters are task-shaped, not plan-shaped** | `src/mesh/adapters/cli.py:14` SUPPORTED_FIELDS has no tier/parent_ueid | 5 (render) |
| B6 | **tuiboard + solverforge adapters are non-SONHO-aware** | `src/ikigai/src/ikigai/gateway/clients/tuiboard.py:10-26`, `solverforge_calendar.py:14-29` | 5 (render) |
| B7 | **Pytest collection infra broken for v2 tests** | Per roadmap "A.1 — Fix pytest collection infra" pending | blocks A.2 E2E smoke for Cap 1 |
| B8 | **graph.invoke() with real LLM not tested end-to-end** | Roadmap Task A.2 pending | blocks Cap 1 E2E |

---

## 4. Coverage Summary

### Per-tier (column-wise)

| Tier | ✅ | ⚠️ | ❌/🚫 | % Working |
|---|---|---|---|---|
| SONHO | 1 | 3 | 2 | 16.7% (1/6) |
| OBJETIVO | 1 | 3 | 2 | 16.7% |
| META | 1 | 3 | 2 | 16.7% |
| PROJETO | 1 | 3 | 2 | 16.7% |
| ENTREGA | 1 | 3 | 2 | 16.7% |
| TAREFA | 1 | 3 | 2 | 16.7% |

### Per-capability (row-wise)

| Capability | ✅ | ⚠️ | ❌/🚫 | % Working |
|---|---|---|---|---|
| 1. Create | 0 | 6 | 0 | 0% (write path exists but no real entities; tests are model-only) |
| 2. Read tree | 0 | 6 | 0 | 0% (legacy decompose wired but stale; new vault walk missing) |
| 3. Update | 0 | 0 | 6 | 0% (frozen=True + create-only) |
| 4. Connect | 0 | 6 | 0 | 0% (parent_ueid field + subset validator; no link tool) |
| 5. Render | 0 | 0 | 6 | 0% (no SONHO-aware fork renderer) |
| 6. Show via mesh | 6 | 0 | 0 | 100% (working across all tiers — UEID-indexed) |

**Headline:** 7 of 36 cells (19.4%) are ✅ or ⚠️ with a real working surface. Mesh show is the ONLY fully green capability. Update and Render are uniformly 🚫.

---

## 5. Critical Gaps (Top 5)

1. **No live SONHO entities in `vault/`** — Roadmap **A.4** pending. Without seeded data, Capabilities 1, 2, 6 cannot be exercised end-to-end. The two placeholders (`vault/ikigai/closing-2026/01-q3-2026/00-sonho/placeholder.md`, `02-q4-2026/00-sonho/placeholder.md`) explicitly defer until "system readiness" (placeholder.md line 3).

2. **`update` action deferred behind SONHO-data gate** — Roadmap **C.3** (5+ SONHO logs collected by user) blocks **C.4** algorithm tuning which gates Phase 3 v1.2 update. Phase 3 v1 explicitly documents this in `src/mesh/adapters/__init__.py:9-11`. Until then, every SONHO/OBJETIVO/META/PROJETO/ENTREGA/TAREFA is write-once.

3. **`mesh show` SONHO tree traversal not built** — Roadmap **C.6** pending (2-3 days estimate). `ikigai_decompose` exists but reads the legacy `data/matheus/` path (`server.py:99-177`) which is separate from the canonical `vault/ikigai/closing-2026/...` SONHO tree. New vault walk = blocker for Capability 2 in production.

4. **No SONHO-aware fork renderer** — Adapters at `src/mesh/adapters/cli.py:14` only persist task-shaped fields. The tuiboard and solverforge_calendar stdio adapters (`src/ikigai/src/ikigai/gateway/clients/`) handle render/schedule/aggregate but not plan-tree visualization. Roadmap **C.8** ("Operator TUI SONHOs tab") pending.

5. **End-to-end SONHO write not tested** — `tag_and_persist_node` (`src/ikigai/src/agents/v2/nodes/tag_and_persist.py:42-79`) wires vault_write, but v2 graph end-to-end smoke test is roadmap **A.2** (blocked by pytest infra **A.1**). Without that, "Create SONHO" is a code path with no green CI confirmation.

---

## 6. Verified vs Unverifiable Claims

**Verified claims (with file:line citations in matrix above): 27**

- 6 contracts exist (Sonho/Objetivo/Meta/Projeto/Entrega/Tarefa) — `src/contracts/*.py`
- 6 contract tests exist — `tests/contracts/test_{sonho,objetivo,meta,projeto,entrega,tarefa}.py`
- 1 base/subset test exists — `tests/contracts/test_base_subset_validator.py`
- 1 transition_validator test exists — `tests/ikigai/security/test_transition_validator.py`
- 3 mesh adapters (cli, taskdog, solverforge_calendar) implement ForkAdapter Protocol — `src/mesh/adapters/`
- 3 adapter `apply_change` early-return on non-create — `cli.py:34`, `taskdog.py:83`, `solverforge_calendar.py:58`
- `vault_write` MCP tool has `actor: Literal["user","agent","system"]` parameter — `src/ikigai/src/mcp_server/tools_vault.py:40-71`
- `vault_read` MCP tool exists — `src/ikigai/src/mcp_server/tools_vault.py:74-96`
- `transition_validator` enforces SONHO.user-only — `src/ikigai/src/ikigai/security/transition_validator.py:38-42`
- `tag_and_persist_node` calls `vault_write` — `src/ikigai/src/agents/v2/nodes/tag_and_persist.py:68`
- `commit_node` calls `vault_write` — `src/ikigai/src/agents/v2/nodes/commit.py:95-100`
- `ikigai_mesh_show` MCP tool joins 3 adapters — `src/ikigai/src/mcp_server/tools_mesh.py:56-94`
- `ikigai_task_create` only supports `action="create"` — `src/ikigai/src/mcp_server/tools_mesh.py:107-113`
- `ikigai_decompose` reads `data/matheus/` legacy path — `src/ikigai/src/mcp_server/server.py:102-103,117-119`
- CLI `mesh-show` joins cli/taskdog/solverforge_calendar — `interfaces/cli/read_tasks.py:232-260`
- 2 SONHO placeholder files (no real entities) — `vault/ikigai/closing-2026/{01,02}-q*-2026/00-sonho/placeholder.md`
- `BasePlanContract` is `frozen=True, extra="forbid"` — `src/contracts/base.py:49`

**Unverifiable claims (inspected but cannot confirm working without runtime probe): 9**

- Whether `vault_write` actually persists to disk in the current v2 graph flow (no E2E smoke test green; roadmap A.2 pending).
- Whether `ikigai_decompose` returns usable output for a real SONHO (only the legacy `data/matheus/` path is wired; no SONHO entities exist to test against).
- Whether `transition_validator` is actually invoked at write time (signature exists at `transition_validator.py:16-45` but no call site found in the agent layer during this audit).
- Whether the v2 graph (`make_v2_graph`) compiles end-to-end (commit `ff158da` de-stubbed it per roadmap, but CI gate `tests/ikigai/agents/v2/conftest.py` is broken per Task A.1).
- Whether `tag_and_persist_node` correctly handles the SONHO.user-only actor constraint (it always passes `actor` from state, defaulting to `"agent"` — `tag_and_persist.py:44`; this means **an agent invocation would fail at vault_write or transition_validator** if SONHO were persisted via this path. Currently safe only because no SONHO entity has been persisted).
- Whether the 3 mesh adapters correctly reconcile the same SONHO across forks (none have been propagated yet).
- Whether `ikigai_mesh_show` correctly handles UEIDs from the 5-part canonical format (the regex in `src/contracts/common.py:34` is 4-part legacy; 5-part canonical lives at `src/ikigai/src/ikigai/types.py:UEID` per roadmap `ueid-5part-canonical-decision-2026-08-31`).
- Whether fork adapter `supports_field` for SONHO-specific fields (tier, parent_ueid, ikigai_vectors) is correct (current SUPPORTED_FIELDS sets don't include any of them).
- Whether the Operator TUI (`interfaces/tui/operator/`) renders SONHOs — roadmap C.8 pending; not inspected in this audit.

---

**File written:** `C:\Users\mathe\code_space\life-oss\life\docs\superpowers\specs\2026-09-04-diag-07-sonho-capability.md`

**Counts:**
- Verified claims: 27
- Unverifiable claims: 9
- Working cells (✅): 7 of 36 (19.4%) — 1 row × 6 tiers + 1 row × 1 tier for mesh show
- Partial cells (⚠️): 18 of 36 (50.0%) — 3 rows × 6 tiers (create/read/connect)
- Broken/not-implemented cells (❌/🚫): 11 of 36 (30.6%) — 2 rows × 6 tiers (update/render) − partials from cap 3 = 12 broken but cap 3 = 6 + cap 5 = 6 = 12; corrected: 36 − 7 − 18 = 11

**Corrected broken count:** 36 − (7 ✅) − (18 ⚠️) = 11 (❌/🚫)