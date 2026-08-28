# 05 — Open Questions (10 Items for Phase 3 Brainstorm)

**Source:** `docs/diagnostics/2026-08-28-ultracode-verified.md` §6
**Status:** All UNRESOLVED. Carry forward to Phase 3 brainstorm.

---

## OQ-1 — Storage topology (blocks everything)

- **Question:** Is `~/.ikigai/` (user-home, survives repo moves, invisible to git) or `life/data/` (repo-local, versionable, diffable) the canonical root?
- **Context:** Right now you have BOTH plus a phantom third root. 3 storage roots enumerated in critic gaps, 7 stores total
- **What blocks:** Every downstream data-mesh design decision depends on this. P2/P3 sequencing can't proceed without it
- **Options:**
  - A) `~/.ikigai/` canonical (survives repo moves; user-private)
  - B) `life/data/` canonical (versionable; CI-testable)
  - C) Declared registry: one root, multiple stores (config-driven)

## OQ-2 — Contracts naming

- **Question:** Which package owns the name `contracts` — `src/contracts/` (typed Pydantic, 0 importers, declared canonical in CLAUDE.md) or `vibe-ops/src/contracts/` (YAML, 2 real importers, actually load-bearing)?
- **Context:** Two packages named `contracts` is root cause audit rated only MED
- **What blocks:** Single source of truth for schema. P2 priority
- **Options:**
  - A) `src/contracts/` wins (Pydantic-first; needs migration of 2 real importers from `vibe-ops/src/contracts/`)
  - B) `vibe-ops/src/contracts/` wins (already wired; needs `src/contracts/` to either migrate or rename)
  - C) Different layers (schema models vs sync/wire contracts) needing distinct names

## OQ-3 — Is `tasks.jsonl` THE MESH INTERCHANGE, OR A BRIDGE?

- **Question:** Should `tasks.jsonl` be the single canonical interchange file for the data mesh, or a transient bridge during the migration to a proper store?
- **Context:** 3 processes append to one flat file with no reconciliation, no locking, no compaction story
- **What blocks:** Storage topology (OQ-1) and Phase 3 design
- **Options:**
  - A) The interchange: keep JSONL, add file-locking + compaction + schema enforcement
  - B) A bridge: migrate to SQLite + Chroma (federated) or single store; JSONL becomes audit log only
  - C) Hybrid: JSONL for write-heavy, SQLite for queries

## OQ-4 — Data-first gate interpretation

- **Question:** Memory says "no new code until 5+ manual logs prove workflow". Does repairing paths + unifying contracts count as "new code" or prerequisite plumbing?
- **Context:** Path fixes (Step 0) and contracts unification (Step 2) are arguably plumbing — they don't add new capability, they make existing code reachable. Or are they new code?
- **What blocks:** Sequencing Step 0 and Step 2
- **Options:**
  - A) Plumbing: any path correction is OK; does not violate data-first
  - B) Strict: ALL code changes blocked until 5+ manual logs (SONHO counter is currently 1/5 per [[ikigai-persona-vault-bootstrap]])
  - C) Hybrid: path fixes OK (low risk), contracts unification gated on logs

## OQ-5 — Federation vs single source

- **Question:** Does `vibe_ops.db` stay analytic/mesh store with operational SQLite as write master (federated, two schemas), or collapse into one store?
- **Context:** Currently 3 separate SQLite files (`vibe_ops.db`, `vibe_mesh.db` 0 bytes, `chroma_db/chroma.sqlite3`) + operational `SqliteRepository`. Plus `~/.ikigai/plan_entities.db` and `~/.ikigai/ikigai_checkpoints.db`
- **What blocks:** Storage topology (OQ-1) and contracts (OQ-2)
- **Options:**
  - A) Federated: 2-3 stores, defined roles, ETL between them
  - B) Single source: one SQLite per concern (vault mirror, runtime, mesh), no federation
  - C) Polyglot: SQLite for OLTP, Chroma for vector, JSONL for interchange — current state, just made explicit

## OQ-6 — MiniMax proxy — intended or accidental?

- **Question:** `deepagents_harness.py` points `ChatAnthropic` at `base_url=api.minimax.io` with model `MiniMax-M2.7-highspeed`. Was this intentional or accidental?
- **Context:** Different provider hostname. May be intentional dev/test config or accidental misconfiguration
- **What blocks:** OpenWiki cron (`openwiki-update.yml`) which uses this proxy daily
- **Options:**
  - A) Intentional: keep, document
  - B) Accidental: change to standard Anthropic base URL
  - C) Intentional but should be configurable via env var

## OQ-7 — UEID join key

- **Question:** Keep two UEID formats (contracts `^[a-z][a-z0-9]{2,30}_...` underscore vs ikigai `namespace:type:slug:uuid:hash`) or unify?
- **Context:** `tasks.jsonl` carries `ueid` written by both sides — mesh has no reliable join key
- **What blocks:** Storage topology (OQ-1) and tasks.jsonl design (OQ-3)
- **Options:**
  - A) Unify on 5-part `namespace:type:slug:uuid:hash` (ikigai format, more robust)
  - B) Unify on underscore `<prefix>_<slug>` (contracts format, simpler)
  - C) Keep both; add explicit `mesh_ueid` join field

## OQ-8 — Two MCP transports

- **Question:** Keep deliberate decoupling (ikigai stdio for AI kernel, gateway HTTP for 3 user-view forks) or unify?
- **Context:** Deep Agent already bridges to all 3 forks directly via 10 wrappers at `agents/tools.py:930-953`. Gateway is parallel path
- **What blocks:** Agent layer design (Layer 3) and Phase 3 mesh
- **Options:**
  - A) Keep decoupled: ikigai for AI, gateway for forks (current)
  - B) Unify on gateway: remove ikigai MCP server, route everything through gateway
  - C) Hybrid: ikigai for kernel tools, gateway for fork tools

## OQ-9 — 4 stub workflows: implement or deregister?

- **Question:** Are `quarterly_replan`, `test_de_fogo_rollup`, `correction_protocol`, `dream_falsification` planned capabilities (implement) or abandoned ideas (deregister)?
- **Context:** Stubs currently CRASH on invocation (verified bug). `langgraph.json` declares them
- **What blocks:** Step 7 sequencing
- **Options:**
  - A) Implement: build YAML workflows at `<root>/.claude/skills/...`
  - B) Deregister: remove from `langgraph.json`
  - C) Per-stub decision (some implement, some deregister)

## OQ-10 — mcp-gateway orphan: merge or discard?

- **Question:** ~1600 lines of gateway code in worktree `feat/data-model-unification`, never merged. Decision pending per memory [[ag3-gateway-orphan-2026-08-27]]
- **Context:** Unmerged since 2026-08-26
- **What blocks:** Step 7 sequencing, gateway path (Step 0)
- **Options:**
  - A) Merge: integrate the worktree (significant work — 1600 lines)
  - B) Discard: delete the worktree (lose 1600 lines of work)
  - C) Cherry-pick: review and pull only specific commits