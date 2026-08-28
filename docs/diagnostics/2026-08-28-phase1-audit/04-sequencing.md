# 04 — Sequencing (8 Steps)

**Source:** `docs/diagnostics/2026-08-28-ultracode-verified.md` §4
**Note:** Per Q2 scope, this is the ROADMAP. No actual code is modified.

---

## Step 0 — Path fixes (~1 day)

- **Action:** Land P1 quick-win path fixes: `gateways.yaml:4,9,14` + `langgraph_entry.py:25-27` + `server.py:289` + `operational/__main__.py:9`
- **Rationale:** Cannot design data mesh against system whose entry points fail at import. Converts audit guesses into observations
- **Dependencies:** none
- **Effort:** 1 day

## Step 1 — Freeze datastore census (~1 day)

- **Action:** Enumerate 3 roots, 7 stores, owners. Bring OQ-1 (storage topology) and OQ-3 (`tasks.jsonl` role) as explicit Phase 3 decisions
- **Rationale:** Storage topology question blocks Phase 3 design. Census is observation, not design
- **Dependencies:** Step 0 (need working entry points to observe)
- **Effort:** 1 day

## Step 2 — Resolve `contracts` namespace collision (~1 week)

- **Action:** Decide which package wins: `src/contracts/` (Pydantic models) vs `vibe-ops/src/contracts/` (YAML, 2 real importers) vs `vibe-ops/src/schemas/pydantic_v2.py` (3 importers)
- **Rationale:** First irreversible design act. Whichever package wins becomes mesh's schema authority
- **Dependencies:** Step 1 (need storage topology decision first)
- **Effort:** 3-5 days (decision + migration of 3 tasks.jsonl writers)

## Step 3 — Migrate 3 `tasks.jsonl` writers (~3 days)

- **Action:** Migrate `daily_consolidator.py`, `_write_tasks_to_data`, `_read_tasks_from_data` onto winning contract
- **Rationale:** De facto already agree on 14 field names. Cheaper than it looks — convergence exists
- **Dependencies:** Step 2 (need winning contract)
- **Effort:** 2-3 days

## Step 4 — Retire `vibe-ops/src/schemas/pydantic_v2.py` (~1 day)

- **Action:** Repoint 3 importers (`daily_loop.py:4`, `sync_engine.py:9`, `policy_engine.py:3`) to canonical
- **Rationale:** Removes last parallel shape definition
- **Dependencies:** Step 3 (need migrated writers)
- **Effort:** 1 day

## Step 5 — Single PolicyEngine (~2 days)

- **Action:** Fold 118L stub into 827L canonical FSM. Repoint `main.py:86`. Fix `daily_loop.py:33` signature drift. Re-test regime agreement between `run-daily` and `status`
- **Rationale:** Safe because Step 4 gave both engines one `PolicyDecision` shape
- **Dependencies:** Step 4
- **Effort:** 2 days

## Step 6 — Seed sensor (~1 week)

- **Action:** Populate `data/vibe_ops.db` `habit_states` + `study_sessions` + keep populating. Rewire `score_vectors.py:_compute_passion_score` and `observe.py:_read_qhe_from_operational` off hardcoded 0.65
- **Rationale:** Deliberately after contracts — seeding into unowned schema means migrating rows twice
- **Dependencies:** Step 5 (need stable schema)
- **Effort:** 3-4 days (depends on whether manual logs exist per data-first gate)

## Step 7 — Repair langgraph_entry imports + take 4-stub decision + mcp-gateway merge/discard (~1 week)

- **Action:**
  - Repair `langgraph_entry.py:25-27, 32` fully
  - Decision: implement YAML workflows at `<root>/.claude/skills/...` OR deregister 4 stub graphs from `langgraph.json`
  - mcp-gateway orphan worktree merge-or-discard call
- **Rationale:** Decision-gated, not effort-gated
- **Dependencies:** Step 0 (PR-1 path resolution)
- **Effort:** 2-5 days depending on stub decision + mcp-gateway merge work

## Step 8 — Hygiene sweep (~2 days)

- **Action:**
  - Move session leftovers (`session-ses_*.md` 1.1MB, 2 `.txt` 142KB) to `logs/` and gitignore
  - Quarantine `data/boulder.json` (stale since 2026-06-30, points at `.omo/plans/` which was renamed to `vault/`)
  - Delete or xfail 2 orphan test files: `tests/core/test_services.py` (942L) and `tests/e2e/test_cli_workflow.py` (66L)
  - Remove empty `tests/{tui,ui,property}/` and `tests/unit/cli/`
  - Delete 3 zero-byte files: `vibe-ops/src/pipeline/study_manager.py`, `pipeline/code_review_sync.py`, `storage/vector_store.py`
  - CLAUDE.md factual corrections (entity count 15→29, pomodoro states 8→7, layering lie)
  - `ci.yml:56-65` — add `src/contracts` and `interfaces/cli` to quality-gates matrix
- **Rationale:** Last because none of it blocks anything, but CI additions stop next contracts layer from silently reaching zero importers
- **Dependencies:** Step 7
- **Effort:** 2 days

---

## Total effort (rough): ~3-4 weeks

This is observation + decision + migration work. Code-change-only quick wins (Step 0) are ~1 day. The slow parts are storage topology decisions (Step 1) and mcp-gateway orphan merge (Step 7).

---

## What's intentionally deferred past Phase 1

- Design proposals (storage topology, contracts naming, UEID, MCP transports) — see `05-open-questions.md`
- Code patches (per Q2 scope: no patch plans)
- Implementation of any single priority item (Steps 0-8 are roadmap only)