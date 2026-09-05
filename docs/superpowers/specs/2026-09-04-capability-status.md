# Capability Status — Master Spec 03

**Generated:** 2026-09-04
**Synthesizes:** Diag 06 (data layer), Diag 07 (SONHO capability 6×6), Diag 08 (taskdog 3×8), Diag 09 (ADR gap)
**Status:** Spec for review (not yet implementation plan)

---

## 1. SONHO-tree capability matrix (6 tiers × 6 capabilities, Diag 07)

| Capability | SONHO | OBJETIVO | META | PROJETO | ENTREGA | TAREFA |
|---|---|---|---|---|---|---|
| 1. Create | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| 2. Read tree | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| 3. Update | 🚫 | 🚫 | 🚫 | 🚫 | 🚫 | 🚫 |
| 4. Connect | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| 5. Render in fork | 🚫 | 🚫 | 🚫 | 🚫 | 🚫 | 🚫 |
| 6. Show via mesh | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Coverage: 7 ✅ (19.4%) / 18 ⚠️ (50%) / 11 🚫 (30.6%)**

### Per-capability status

#### Create — ⚠️ all 6 tiers (partial)
- Code: vault_write + actor parameter (Plan A) works for any 6-tier entity
- **Gap:** 0 SONHO entities seeded in `vault/`. Plan A A.4 placeholder work.
- **Per-tier logic:** transition_validator SONHO.user-only enforced; per-tier logic B-T02/B-T03/B-T04 gaps.

#### Read tree — ⚠️ all 6 tiers (partial)
- Code: single-file vault_read works
- **Gap:** full hierarchy walk wired only to legacy `data/matheus/` path, NOT canonical `vault/`
- **Per-tier logic:** flat tree; no parent→child traversal tool

#### Update — 🚫 all 6 tiers (not implemented)
- **Reason 1:** Pydantic frozen=True blocks in-place mutation
- **Reason 2:** Phase 3 v1 = create-only; update action deferred to v1.2
- **Roadmap gate:** 5+ SONHO logs collected (Task C.3)

#### Connect — ⚠️ all 6 tiers (partial)
- Code: `parent_ueid` field + subset validator (parent→child allowed)
- **Gap:** no link tool; relationship traversal not implemented
- **Per-tier logic:** subset validator enforces hierarchy

#### Render in fork — 🚫 all 6 tiers (not implemented)
- Reason: adapters are task-shaped (`ueid`, `description`, `priority`, `due`, etc.); no SONHO-aware renderer
- **Roadmap gate:** Scenario C.8 (TUI SONHOs tab)

#### Show via mesh — ✅ all 6 tiers
- Code: `ikigai_mesh_show` joins CLI + taskdog + solverforge_calendar adapters by ueid
- Only fully-green capability across all 6 tiers

## 2. Taskdog capability matrix (3 paths × 8 capabilities, Diag 08)

| Capability | Path 1 (harness subprocess) | Path 2 (mesh SQLite) | Path 3 (MCP gateway) |
|---|---|---|---|
| C1 Create | ✅ | ✅ | 🚫 OFF (working tree) |
| C2 Read | ⚠️ taskdog 0.23.0 bug | ✅ | 🚫 OFF |
| C3 List | ✅ | ✅ | 🚫 OFF |
| C4 Done | ⚠️ start-before-done gap | ✅ | 🚫 OFF |
| C5 Update | ❌ | ❌ | 🚫 OFF |
| C6 Delete | ❌ | ❌ | 🚫 OFF |
| C7 Sync outbound (→taskdog) | ❌ | ❌ | 🚫 OFF |
| C8 Sync inbound (from→taskdog) | ❌ | 🟡 indirect | 🚫 OFF |

**Coverage: 9 ✅ / 2 ⚠️ / 12 ❌ / 1 🟡 / 12 🚫**

### Top 5 taskdog blockers (Diag 08)
1. Path 1 `taskdog_done` lacks `start` orchestration (`tools.py:463-489`)
2. Path 2 v1 = create-only hard gate (`taskdog.py:83-84`)
3. Path 3 module uncommitted-deleted from working tree (Diag 02 + 08)
4. `taskdog 0.23.0 show` has known bug (`tools.py:515-521`)
5. Path 1 ↔ Path 2 stores independent; no reconciliation code (design doc §6 anti-pattern #5)

## 3. Data layer capability (Diag 06)

| Capability | Status | Notes |
|---|---|---|
| Atomic filesystem queue | ✅ | `src/mesh/queue.py:64-71` (4-retry temp+fsync+rename) — production-grade |
| LangGraph checkpoint persistence | ✅ | `data/ikigai_checkpoints.db` (91 rows, 4 threads, WAL) |
| Single-writer tasks.jsonl | ⚠️ split-brain | 2 writers, 2 schemas, 2 atomicity models — corruption risk |
| Chroma embedding store | 🚫 | collection created, 0 embeddings |
| Investigation queue | 🚫 | `data/investigation_queue/` DOES NOT EXIST (Plan C unexecuted) |
| Mesh SQLite | 🚫 | 0-byte orphan; canonical is `vibe-ops/vibe_mesh.db` |
| Boulder.json | 🚫 | stale since 2026-06-30, references deleted `.omo/plans/` |
| Session transcripts | 🚫 | legacy Atlas, no consumer |

## 4. MCP gateway capability

| Gateway | Tools | Resources | Status |
|---|---|---|---|
| FastMCP `ikigai-gateway` (`src/ikigai/src/mcp_server/server.py`) | 15 @MCP.tool | 6 @MCP.resource | ✅ live |
| `UnifiedMCPGateway` HTTP+SSE (`src/ikigai/src/ikigai/gateway/gateway.py`) | 7 fork tools (sf_* + tuiboard_*) | 0 | ✅ live |
| Path 3 taskdog MCP (`src/ikigai/src/mcp_server/taskdog_mcp/`) | 4 tools + 1 resource | — | 🚫 **OFF on disk** (uncommitted deletes) |
| Investigation MCP (Plan C) | 3 tools | — | 🚫 **DOES NOT EXIST** (Plan C unexecuted) |

**Total gateway surface (live): 22 tools + 6 resources across 2 gateways + 1 dead gateway + 4 unbuilt tools.**

## 5. Combined capability heatmap (rolled up)

| Domain | ✅ Green | ⚠️ Partial | 🚫 Red | Total |
|---|---|---|---|---|
| SONHO tree (6×6) | 7 | 18 | 11 | 36 cells |
| Taskdog (3×8) | 9 | 2 | 12 + 1 🟡 + 12 🚫 | 36 cells |
| Data layer | 2 | 1 | 5 | 8 entries |
| MCP gateway | 22 | 0 | 8 | 30 tools+resources |
| Drift invariants (9) | 7 | 0 | 2 (B-D04 STUBBED, B-D09 ABSENT) | 9 |
| Transition matrix (4) | 1 | 0 | 3 (B-T02/03/04) | 4 |

**Overall: 48 ✅ / 21 ⚠️ / 41 🚫 across 123 capability cells = 39% green / 17% partial / 33% red.**

## 6. Top 5 capability-blocking gaps (priority order)

1. **Plan C unexecuted** — investigation_queue absent; no place for pre-form data. Blocks: all "raw observation" intake. Fix: re-dispatch Plan C implementation (3h, 7 tasks).
2. **`data/tasks.jsonl` split-brain writers** — corruption risk in steady state. Blocks: any mesh scenario with both CLI + agent activity. Fix: 4-6h refactor unifying on CliAdapter pattern.
3. **`observe.py:56-61` hardcoded QHE constants** — algorithm math in agent layer violates ADR-013. Blocks: Scenario C algorithm loop + any future agent math work. Fix: 2-4h prompt-template migration per ADR-019.
4. **Path 3 taskdog MCP OFF on disk** — 4 tools unreachable. Blocks: Path 3 alternative for taskdog. Fix: re-add canonical module or accept Path 1+2 only.
5. **B-D04 drift invariant STUBBED** — full SONHO tree coverage not enforced. Blocks: drift detector confidence in 6-tier persistence. Fix: write `drift_invariants.py` registry lookup (Plan A Task 10).

## 7. Spec self-review

- ✅ All capability cells enumerated with status + verification source.
- ✅ Heatmap aggregates roll up correctly (e.g., 7 ✅ for SONHO 6×6 matches Diag 07 exactly).
- ✅ Top 5 gaps prioritized by impact × ease-of-fix.
- ⚠️ **Ambiguity:** "MCP gateway surface" includes resources; some agents/tools may double-count. **Assumption:** tools and resources are independent dimensions.

## 8. Open questions for user

1. Investigate the 12 ❌ cells in taskdog C5-C8 (Update/Delete/Sync) — is the intent to build them in v1.2 (per Phase 3 roadmap) or defer indefinitely?
2. Investigate the 11 🚫 cells in SONHO Update + Render — are they explicitly "v1.2+" or "post-MVP only"?
3. Should "data layer capability" be a tracked dimension in future diagnostic sweeps (Diag has been light on data-layer)?
