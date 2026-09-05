# dcode Harness — Implementation Tasks

**Generated:** 2026-09-04
**Methodology:** spec-kit (manual application; per user choice 2026-09-04)
**Companion:** `2026-09-04-dcode-harness-PLAN.md`
**Status:** Tasks for review (not yet started)

---

## Conventions

- **Task ID format:** `[Wave].[Sequence]` for code tasks; `ADR-[NNN]` for ADRs; `DOC-[NNN]` for documentation tasks.
- **Acceptance criteria:** binary pass/fail; no fuzzy states.
- **Effort:** ranges per Diag 04/05/09/10 estimates (lower-bound = experienced solo dev; upper-bound = mid-experience solo dev).
- **Dependencies:** list of task IDs that must complete first.
- **Source:** Diag file or Master spec section where this task was identified.

---

## Wave 1 — Test hardening + audit log (5h)

### Task W1.1 — Add tests for `life mesh` commands

- **ID:** W1.1
- **Title:** Add integration tests for `life mesh show`, `life mesh list`, `life mesh propagate`
- **Source:** master-02 §2 (T01-T03), Diag 05
- **Dependencies:** none
- **Effort:** 1.5h
- **Files affected:** `interfaces/cli/tests/test_mesh_show.py` (already exists, expand), `interfaces/cli/tests/test_mesh_propagate.py` (new), `interfaces/cli/tests/test_mesh_list.py` (new)
- **Acceptance criteria:**
  - [ ] `pytest interfaces/cli/tests/test_mesh_show.py::test_show_joins_3_adapters -v` passes
  - [ ] `pytest interfaces/cli/tests/test_mesh_propagate.py -v` exits 0
  - [ ] `pytest interfaces/cli/tests/test_mesh_list.py -v` exits 0
  - [ ] All 3 tests use `tmp_path` fixture + `monkeypatch` (no global state mutations)
  - [ ] Coverage on `interfaces/cli/mesh_show.py` ≥ 80% (line coverage)
- **Out of scope:** adding new mesh features; just exercising existing ones

### Task W1.2 — Add tests for `life v2` entry commands

- **ID:** W1.2
- **Title:** Add integration tests for `life v2 daily`, `life v2 weekly` (and other v2 entry commands present in `interfaces/cli/v2.py`)
- **Source:** master-02 §2 (T07-T08), Diag 05
- **Dependencies:** none
- **Effort:** 1.5h
- **Files affected:** `interfaces/cli/tests/test_v2.py` (new), conftest updates if needed
- **Acceptance criteria:**
  - [ ] Each v2 entry command has ≥1 happy-path test + ≥1 error-path test
  - [ ] Tests mock the graph.invoke() call (do not require real Claude API)
  - [ ] `pytest interfaces/cli/tests/test_v2.py -v` exits 0
- **Out of scope:** implementing v2 suggest or v2 cycle --dry-run (those are W2.1, W2.2)

### Task W1.3 — Audit-log test for vault_write

- **ID:** W1.3
- **Title:** B-D09: write a test that verifies vault_write produces an audit-log entry on every call
- **Source:** master-02 §1 (B-D09), Diag 04
- **Dependencies:** none
- **Effort:** 2h
- **Files affected:** `src/ikigai/tests/test_vault_write_audit.py` (new)
- **Acceptance criteria:**
  - [ ] Test invokes vault_write with `actor="user"` and `actor="agent"`, both paths
  - [ ] Test asserts audit-log entry exists with matching `actor`, `vault_path`, `timestamp`
  - [ ] Test asserts failure on vault_write also produces failure entry (or skipped entry)
  - [ ] `pytest src/ikigai/tests/test_vault_write_audit.py -v` exits 0
- **Notes:** this is the B-D09 ABSENT drift invariant from master-02 §1 B-D*

**Wave 1 total: 5h. Single PR `wave-1-tests`. Ships in 1 working day.**

---

## Wave 2 — Skill entry points + v2 commands (11h)

### Task W2.1 — Implement `v2 suggest` command

- **ID:** W2.1
- **Title:** Add `v2 suggest` Typer command to `interfaces/cli/v2.py` (referenced by `daily.md:24`)
- **Source:** master-02 §2 (T09), Diag 05
- **Dependencies:** W1.2 (so the new command is tested)
- **Effort:** 3h
- **Files affected:** `interfaces/cli/v2.py`, `interfaces/cli/tests/test_v2.py`
- **Acceptance criteria:**
  - [ ] `life v2 suggest --context "<text>"` returns 1-3 task suggestions (LLM-generated or heuristic fallback)
  - [ ] Output supports `--json` flag
  - [ ] Has dedicated tests (happy + error + json-flag paths)
  - [ ] `daily.md:24` resolves to a callable (no more "DOES NOT EXIST" reference)
- **Notes:** heuristic fallback acceptable; full LLM integration optional per available budget

### Task W2.2 — Implement `v2 cycle --dry-run` flag

- **ID:** W2.2
- **Title:** Add `--dry-run` flag to `v2 cycle` command (referenced by weekly/monthly/quarterly skills)
- **Source:** master-02 §2 (T10), Diag 05
- **Dependencies:** W1.2
- **Effort:** 3h
- **Files affected:** `interfaces/cli/v2.py`, `interfaces/cli/tests/test_v2.py`
- **Acceptance criteria:**
  - [ ] `life v2 cycle --dry-run` shows intended graph trajectory WITHOUT invoking graph.invoke()
  - [ ] `life v2 cycle` (no flag) behaves identically to before
  - [ ] Tests cover both paths
  - [ ] `weekly.md`, `monthly.md`, `quarterly.md` no longer reference a non-existent flag
- **Notes:** may require graph introspection node (lightweight)

### Task W2.3 — Wire 4 unwired skill entry points

- **ID:** W2.3
- **Title:** Wire `daily`, `weekly`, `monthly`, `quarterly` skill hooks (4 of 7 expected entry points unwired per Diag 05)
- **Source:** master-02 §2 (T11-T16), Diag 05
- **Dependencies:** W1.2, W2.1, W2.2
- **Effort:** 5h
- **Files affected:** `interfaces/cli/v2.py`, skill YAML files at `.claude/skills/*/SKILL.md`
- **Acceptance criteria:**
  - [ ] All 7 expected entry points (`v2 daily`, `v2 weekly`, `v2 monthly`, `v2 quarterly`, `v2 suggest`, `v2 cycle`, `v2 help`) resolve to real functions
  - [ ] Each entry point has at least 1 dedicated test
  - [ ] No skill markdown references a non-existent command
  - [ ] `mcp_inspect.py --tool-count 15` (unchanged from current state)
- **Out of scope:** adding new entry points beyond the 7 expected

**Wave 2 total: 11h. Single PR `wave-2-skills`. Ships in 1-2 working days.**

---

## Wave 3 — Scenario A: Critical path to functional MVP (32-44h)

### Task W3.0 — ADR-023 UEID canonical adjudication (URGENT)

- **ID:** ADR-023
- **Title:** Adjudicate UEID canonical format (4-part vs 5-part): drift detector enforces 4-part regex, CLAUDE.md/memory claim 5-part
- **Source:** master-04 §3, master-01 §7 (gap 3)
- **Dependencies:** none
- **Effort:** 1-2h (decision) + 1h (regex fix if needed)
- **Files affected:** `code-docs/adr/ADR-023-ueid-canonical-format.md` (new), `src/contracts/common.py` (potentially), `src/contracts/task.py` (potentially)
- **Acceptance criteria:**
  - [ ] ADR-023 written + Accepted by user
  - [ ] Drift detector regex matches the canonical format (4-part OR 5-part per decision)
  - [ ] CLAUDE.md updated if 4-part chosen (to align with detector)
  - [ ] memory references updated if 5-part chosen (to align with detector)
- **Why first:** blocks downstream UEID work; 1-2h decision without any code changes yet

### Task W3.1 — Fix pytest collection infra

- **ID:** W3.1 (also roadmap A.1 / B-G01)
- **Title:** Fix `src.ikigai.src.*` namespace mismatch + conftest cleanup
- **Source:** master-02 §1 (B-G01), Diag 03
- **Dependencies:** none
- **Effort:** 2-6h
- **Files affected:** `pyproject.toml`, `conftest.py` files, possibly `pytest.ini`
- **Acceptance criteria:**
  - [x] `pytest src/ikigai/tests/ -v` collects all tests (currently blocked) — RESOLVED 2026-09-04 (multi-tree now collections without `ModuleNotFoundError: No module named 'src.ikigai.src'`)
  - [x] `consider_namespace_packages = true` in pytest config OR src-prefix removed from imports (per user's call on B-G01) — RESOLVED via conftest `sys.path.append(str(_IKIGAI_SRC))` where `_IKIGAI_SRC = <repo>/src/ikigai/src/` (not `<repo>/src/ikigai/` — parent of nested `src/` subdir was the trap)
  - [x] No import-time side effects (no `os.chdir`, no env-var mutation) — conftest only does sys.path mutation + tempfile.tempdir redirect (Windows appdata lock fix)
  - [ ] All Wave 1 + Wave 2 tests pass after this fix — 30/33 pass in target multi-tree combo (`tests/ikigai/agents/v2/` + `src/ikigai/tests/test_v2_interface_dispatch.py` + `test_vault_write_audit_log.py`); 3 pre-existing assertion failures in `test_v2_interface_dispatch.py` (exit_code 1 on score/regime/suggest) — out of scope
- **Notes:** Plan A Task 9 followup COMPLETE 2026-09-04. Memory entry `multi-tree-conftest-namespace-fix-2026-09-04.md`. 4 conftest files touched (tests/conftest.py, tests/ikigai/conftest.py, tests/ikigai/agents/v2/conftest.py, src/ikigai/tests/conftest.py).

### Task W3.2 — Migrate QHE constants to prompt-template

- **ID:** W3.2
- **Title:** Move `observe.py:56-61` hardcoded `DEFAULT_QHE_PUSH=0.85` / `DEFAULT_QHE_RECOVER=0.60` to prompt-template lookup
- **Source:** master-01 §7 (gap 2), master-04 §9 (ADR-019 constraint), Diag 04 + 09 + 10 cross-citation
- **Dependencies:** none (can run in parallel with W3.1)
- **Effort:** 2-4h
- **Files affected:** `src/ikigai/src/agents/v2/observe.py`, `src/ikigai/src/prompts/observe.md` (new), drift detector update
- **Acceptance criteria:**
  - [ ] `observe.py` no longer contains hardcoded numerical constants for algorithm thresholds
  - [ ] Prompt template at `prompts/observe.md` references the algorithm values
  - [ ] Drift detector verifies prompt-template-only pattern (no Python constants in `agents/v2/*.py`)
  - [ ] ADR-019 reference added to comment
- **Why first (within W3):** prevents algorithm-mistakes from propagating to the rest of the v2 graph

### Task W3.3 — Smoke test `make_v2_graph().invoke()` with real Claude

- **ID:** W3.3 (also roadmap A.2 / B-G02)
- **Title:** Wire up an end-to-end smoke test that runs the v2 graph with a stub state and verifies it reaches commit_node
- **Source:** master-02 §1 (B-G02), Diag 03
- **Dependencies:** W3.1
- **Effort:** 4h
- **Files affected:** `src/ikigai/tests/test_v2_graph_smoke.py` (new)
- **Acceptance criteria:**
  - [ ] `pytest src/ikigai/tests/test_v2_graph_smoke.py -v` exits 0
  - [ ] Smoke test invokes all 10 nodes sequentially (observe → score_vectors → heuristics → balance → decompose → plan → tag_and_persist → reflect → commit → surface_intentions)
  - [ ] Each node has a stub state fixture
  - [ ] API 529 retry logic present (per Diag 03 risk flag)
- **Risk:** API rate limits; pre-cache prompts; have offline smoke (FAKE_LLM stub documented as W4.x)

### Task W3.4 — Write ADR-014 (Skill binding mechanism)

- **ID:** ADR-014
- **Title:** Decide how skills (daily/weekly/monthly/quarterly) bind to graph entry points
- **Source:** master-04 §2
- **Dependencies:** none (can write while W3.3 is in progress)
- **Effort:** 10-12h
- **Files affected:** `code-docs/adr/ADR-014-skill-binding-mechanism.md` (new)
- **Acceptance criteria:**
  - [ ] ADR-014 specifies skill→entry-point contract (YAML manifest, programmatic, hybrid?)
  - [ ] ADR references W2.3 work + lists 4 unwired entry points as motivation
  - [ ] ADR identifies actor for each binding (user vs agent)
  - [ ] ADR reviewed + Accepted by user

### Task W3.5 — Wire `daily` skill as entry point

- **ID:** W3.5 (also roadmap A.3 / B-G03)
- **Title:** Implement skill binding per ADR-014, focusing on `daily` as the first binding
- **Source:** master-02 §1 (B-G03)
- **Dependencies:** W3.3, W3.4 (ADR-014 Accepted)
- **Effort:** 8h (note: ADR-014 is 10-12h, this is just the daily binding after ADR is decided)
- **Files affected:** `interfaces/cli/v2.py`, `src/ikigai/src/agents/v2/__init__.py`, skill YAML
- **Acceptance criteria:**
  - [ ] `life v2 daily` triggers `make_v2_graph(entry_point="observe").invoke(state)`
  - [ ] Skill manifest in `.claude/skills/daily/SKILL.md` references the entry point
  - [ ] Test: invoking daily runs graph + writes to vault with actor="user"
  - [ ] Drift detector invariant: actor="agent" routes through transition_validator (per W4.6)

### Task W3.6 — CLI wrapper triggers graph → taskdog task

- **ID:** W3.6 (also roadmap A.5 / B-G04)
- **Title:** Wire the CLI wrapper so `life v2 daily` writes both to vault AND to taskdog.exe (Path 1)
- **Source:** master-02 §1 (B-G04), master-01 §6 (cross-layer integration)
- **Dependencies:** W3.5
- **Effort:** 8h
- **Files affected:** `interfaces/cli/v2.py`, `src/ikigai/src/tools/taskdog.py`
- **Acceptance criteria:**
  - [ ] After vault write, CLI calls Path 1 taskdog subprocess (harness @tool → taskdog.exe)
  - [ ] Returns success when both vault + taskdog succeed
  - [ ] Returns partial-success when vault succeeds + taskdog fails (logged to review_queue)
  - [ ] Test: E2E mock of both paths

### Task W3.7 — Unify `data/tasks.jsonl` writers

- **ID:** W3.7
- **Title:** Refactor `_write_tasks_to_data` to use CliAdapter pattern (atomic temp+fsync+rename, 14-field schema)
- **Source:** master-01 §7 (gap 1), master-03 §6 (top-5 gap 2), Diag 06
- **Dependencies:** none (can run in parallel with W3.x)
- **Effort:** 4-6h
- **Files affected:** `src/ikigai/src/agents/v2/...` (find _write_tasks_to_data), `src/mesh/adapters/cli.py`
- **Acceptance criteria:**
  - [ ] Only ONE writer path remains for `data/tasks.jsonl`
  - [ ] Schema is the 14-field schema (not 6-field)
  - [ ] All writes use atomic temp+fsync+rename
  - [ ] Drift detector invariant: single writer verified (can grep for `open(.*tasks.jsonl.*"a")`)
- **Why ship before W3.8:** prevents E2E smoke from hitting corruption risk

### Task W3.8 — E2E smoke: chat → tag_and_persist → commit_node → vault + taskdog.exe → fork reflects

- **ID:** W3.8 (also roadmap A.6 / B-G05)
- **Title:** Compose the Wave 3 pieces into a single end-to-end smoke test
- **Source:** master-02 §1 (B-G05)
- **Dependencies:** W3.5, W3.6, W3.7
- **Effort:** 4h
- **Files affected:** `src/ikigai/tests/test_v2_e2e_smoke.py` (new)
- **Acceptance criteria:**
  - [ ] Test invokes `life v2 daily` end-to-end (mock or real Claude)
  - [ ] Vault write succeeds with actor="user"
  - [ ] taskdog.exe receives the task (mock if real binary unavailable)
  - [ ] Fork (taskdog SQLite) reflects the new task within 1 second
  - [ ] Drift detector returns 9/9 PASS

**Wave 3 total: 34-50h. Ships in 4-6 working days. PR series `wave-3-scenario-a`.**

---

## Wave 4 — Scenario B: Sub-agents + stateful subgraphs (32-44h)

### Task W4.1 — Write ADR-015 (Sub-agent dispatch protocol)

- **ID:** ADR-015
- **Title:** Decide the sub-agent dispatch protocol (how sub-agents are spawned, what context they receive, how their outputs are aggregated)
- **Source:** master-04 §2
- **Dependencies:** none (can write while W3 is in progress)
- **Effort:** 8-12h
- **Files affected:** `code-docs/adr/ADR-015-sub-agent-dispatch-protocol.md` (new)
- **Acceptance criteria:**
  - [ ] ADR-015 specifies sub-agent lifecycle (spawn, run, collect, terminate)
  - [ ] ADR identifies failure modes (timeout, recursion, partial output)
  - [ ] ADR reviewed + Accepted by user
  - [ ] Spike / prototype referenced in ADR (per Diag 04 risk flag)

### Task W4.2 — Write ADR-016 (Stateful subgraph strategy)

- **ID:** ADR-016
- **Title:** Decide how subgraphs maintain state across daily↔weekly↔monthly↔quarterly (locks checkpoint schema)
- **Source:** master-04 §2
- **Dependencies:** none (can write while W3 is in progress; locks schema for ADR-017)
- **Effort:** 16-20h
- **Files affected:** `code-docs/adr/ADR-016-stateful-subgraph-strategy.md` (new)
- **Acceptance criteria:**
  - [ ] ADR-016 specifies checkpoint schema (which fields persisted, which ephemeral)
  - [ ] ADR identifies SqliteSaver usage + thread-id strategy
  - [ ] ADR reviewed + Accepted by user
  - [ ] Used as constraint by ADR-017 (next)

### Task W4.3 — Write ADR-017 (Memory layer across cycles)

- **ID:** ADR-017
- **Title:** Decide the cross-cycle memory layer (depends on ADR-016 checkpoint schema)
- **Source:** master-04 §2
- **Dependencies:** ADR-016 Accepted
- **Effort:** 8-12h
- **Files affected:** `code-docs/adr/ADR-017-memory-layer-across-cycles.md` (new)
- **Acceptance criteria:**
  - [ ] ADR-017 references ADR-016 schema and builds on it
  - [ ] ADR specifies memory layer (vault frontmatter vs SQLite vs hybrid)
  - [ ] ADR reviewed + Accepted by user

### Task W4.4 — Sub-agent dispatch node in v2 graph

- **ID:** W4.4 (also roadmap B.1 / B-N10)
- **Title:** Implement the sub-agent dispatch node (B-N10) per ADR-015
- **Source:** master-02 §1 (B-N10)
- **Dependencies:** ADR-015 Accepted, W3.8 (so E2E smoke exists)
- **Effort:** 12-16h
- **Files affected:** `src/ikigai/src/agents/v2/subgraph.py` (new), `src/ikigai/src/agents/v2/graph.py`
- **Acceptance criteria:**
  - [ ] Sub-agent dispatch node exists in v2 graph (10th node → 11th node)
  - [ ] Mock sub-agent test (avoid real Claude cost)
  - [ ] Failure mode tests (timeout, recursion, partial output)
  - [ ] `make_v2_graph()` returns 11-node graph

### Task W4.5 — Stateful subgraph consumer

- **ID:** W4.5 (also roadmap B.2 / B-N11)
- **Title:** Implement the stateful subgraph consumer (B-N11) per ADR-016
- **Source:** master-02 §1 (B-N11)
- **Dependencies:** ADR-016 Accepted, W4.4
- **Effort:** 12-16h
- **Files affected:** `src/ikigai/src/agents/v2/checkpoint.py` (new), `src/ikigai/src/agents/v2/state.py`
- **Acceptance criteria:**
  - [ ] SqliteSaver checkpoint reading wired (per ADR-016 schema)
  - [ ] Multi-thread test (4 threads per `data/ikigai_checkpoints.db` pattern)
  - [ ] WAL mode preserved
  - [ ] `data/ikigai_checkpoints.db` grows with state per cycle

### Task W4.6 — Memory layer implementation

- **ID:** W4.6 (also roadmap B.4)
- **Title:** Implement the cross-cycle memory layer per ADR-017
- **Source:** master-02 §1 (B.4)
- **Dependencies:** ADR-017 Accepted, W4.5
- **Effort:** 8-12h
- **Files affected:** `src/ikigai/src/agents/v2/memory.py` (new)
- **Acceptance criteria:**
  - [ ] Daily→weekly rollup works (daily state visible in weekly invocation)
  - [ ] Weekly→monthly→quarterly rollup works
  - [ ] Memory layer is append-only (no overwrites)
  - [ ] Drift detector invariant: memory schema enforced

### Task W4.7 — Drift invariant (e): vault_write actor="agent" routes through transition_validator

- **ID:** DOCUMENT-014 (also roadmap B.5)
- **Title:** Add drift invariant that catches direct vault_write calls with actor="agent" without transition_validator
- **Source:** master-04 §6 (B-D05), Diag 04
- **Dependencies:** ADR-018 Accepted
- **Effort:** 6-8h
- **Files affected:** `src/ikigai/src/security/drift_invariants.py` (extend), `src/ikigai/tests/test_drift_invariants.py`
- **Acceptance criteria:**
  - [ ] Drift invariant (e) added
  - [ ] Test asserts vault_write(actor="agent", vault_path="/tmp/foo") without prior transition_validator raises
  - [ ] Drift detector runs invariant (e) and reports PASS
  - [ ] `drift_invariants.py` registry has 10 entries (9 → 10)

### Task W4.8 — E2E multi-level smoke

- **ID:** W4.8 (also roadmap B.6)
- **Title:** Compose Wave 4 into an end-to-end multi-level smoke test (daily → weekly → monthly → quarterly)
- **Source:** master-02 §1 (B.6)
- **Dependencies:** W4.4, W4.5, W4.6, W4.7
- **Effort:** 8h
- **Files affected:** `src/ikigai/tests/test_v2_multi_level_smoke.py` (new)
- **Acceptance criteria:**
  - [ ] Test invokes daily, then weekly, then monthly, then quarterly in sequence
  - [ ] Each level reads from previous level's checkpoint
  - [ ] Drift detector returns 10/10 PASS
  - [ ] Total runtime <5 minutes

**Wave 4 total: 70-92h. Ships in 8-12 working days. PR series `wave-4-scenario-b`.**

---

## Wave 5 — Scenario C: On-the-fly eficaz (12+ weeks)

### Task W5.1 — Write ADR-018 (Kill switch + review queue wiring)

- **ID:** ADR-018
- **Title:** Decide how the kill switch integrates with review queue (Scenario C gate)
- **Source:** master-04 §2, Diag 02
- **Dependencies:** none (can write while W4 is in progress)
- **Effort:** 9-11h
- **Files affected:** `code-docs/adr/ADR-018-kill-switch-review-queue.md` (new)
- **Acceptance criteria:**
  - [ ] ADR-018 specifies kill switch activation (file flag, env var, vault file)
  - [ ] ADR specifies review_queue integration (kill switch entries go to review_queue)
  - [ ] ADR reviewed + Accepted by user

### Task W5.2 — Write ADR-019 (Empirical algorithm tuning approach)

- **ID:** ADR-019
- **Title:** Decide how algorithm tuning happens via prompt-template ONLY (per `algorithm-scope-reframed-2026-08-30`)
- **Source:** master-04 §2, master-04 §9 (critical constraint)
- **Dependencies:** W3.2 complete (so the precedent exists)
- **Effort:** 6-8h
- **Files affected:** `code-docs/adr/ADR-019-empirical-algorithm-tuning.md` (new)
- **Acceptance criteria:**
  - [ ] ADR-019 explicitly references `algorithm-scope-reframed-2026-08-30`, `algorithm-gate-dropped-2026-09-03`, ADR-013
  - [ ] ADR forbids new Python constants in agent code (closes `observe.py:56-61` loophole)
  - [ ] ADR reviewed + Accepted by user
- **Notes:** this is the constraining ADR; ADR-019 + W3.2 together close the algorithm-math-in-agent violation

### Task W5.3 — ADR-020..024 (Implicit decisions to formalize)

- **ID:** ADR-020, ADR-021, ADR-022, ADR-023, ADR-024
- **Title:** Create 5 ADRs promoting implicit decisions to formal status
- **Source:** master-04 §3
- **Dependencies:** ADR-023 (UEID adjudication) MUST be in Wave 3, others can be in Wave 5
- **Effort:** 12-20h total (2-4h each)
- **Files affected:** `code-docs/adr/ADR-020..024-*.md` (5 new files)
- **Acceptance criteria:**
  - [ ] ADR-020: Deep-Agent as canonical carro-chefe (promotes memory)
  - [ ] ADR-021: Default-deny external folder access (promotes Plan B)
  - [ ] ADR-022: Two-queue architecture (notes Plan C investigation_queue is unexecuted)
  - [ ] ADR-023: UEID canonical format (URGENT — see W3.0)
  - [ ] ADR-024: PAV kernel archive (clarifies read-only archive)
  - [ ] All 5 reviewed + Accepted by user

### Task W5.4 — Write ADR-014 follow-up: extend for monthly/quarterly bindings

- **ID:** W5.4 (also roadmap A.3 / B-G03 extension)
- **Title:** Extend ADR-014 binding mechanism to monthly + quarterly (only daily was Wave 3)
- **Source:** master-02 §1 (B-G03)
- **Dependencies:** ADR-014 Accepted, W3.5 (daily binding done)
- **Effort:** 6-8h (split with W5.5)
- **Files affected:** `interfaces/cli/v2.py`, skill YAML files
- **Acceptance criteria:**
  - [ ] `life v2 monthly` and `life v2 quarterly` trigger their respective entry points
  - [ ] All 4 cycles (daily/weekly/monthly/quarterly) have bindings
  - [ ] Drift detector: 11/11 PASS

### Task W5.5 — Re-dispatch Plan C: investigation_queue + 3 MCP tools

- **ID:** W5.5
- **Title:** Re-execute the Plan C plan (was documentation-only per master-03 §6)
- **Source:** master-03 §6 (top-5 gap 1), Plan C plan document
- **Dependencies:** W3.x complete (so Plan C ships against a stable backend)
- **Effort:** 3-7d
- **Files affected:** `data/investigation_queue/` (new directory), `src/ikigai/src/mcp_server/server.py` (3 new MCP tools)
- **Acceptance criteria:**
  - [ ] `data/investigation_queue/` directory exists with atomic write pattern
  - [ ] IKIGAI_TOOLS count: 12 → 15 (Plan C's 3 tools added)
  - [ ] Drift invariant (h): investigation_queue append-only verified
  - [ ] `mcp_inspect.py --tool-count 15` (was 15, becomes 15 still — Plan C brings to 18, but only after Plan A 6 contracts locked)

### Task W5.6 — SONHO data collection ritual

- **ID:** W5.6 (also roadmap C.3)
- **Title:** Friction-zero SONHO logging triggered on each `dcode daily` run
- **Source:** master-02 §1 (C.3)
- **Dependencies:** W3.5 (daily binding done)
- **Effort:** ongoing (user action), 1d setup
- **Files affected:** `.claude/commands/sonho-log.md` (new)
- **Acceptance criteria:**
  - [ ] `/sonho-log` slash command opens a friction-free template
  - [ ] 5+ SONHO logs collected in `vault/ikigai/closing-2026/01-q3-2026/04-relatórios-diários/`
  - [ ] Each log includes: dream, observation, gap, action
- **Why ongoing:** gates Wave 5.10 (algorithm tuning)

### Task W5.7 — `mesh show` SONHO tree traversal

- **ID:** W5.7 (also roadmap C.6)
- **Title:** Extend `life mesh show <ueid>` to traverse the full SONHO tree (parent→children)
- **Source:** master-02 §3 (master-03 capability matrix row "Read tree")
- **Dependencies:** W5.5 (Plan C shipped; investigation queue can be linked to SONHO nodes)
- **Effort:** 2-3d
- **Files affected:** `src/mesh/__init__.py`, `interfaces/cli/mesh_show.py`
- **Acceptance criteria:**
  - [ ] `life mesh show <sonho-ueid>` returns full tree (6 tiers)
  - [ ] Tree output respects hierarchy (parent→child)
  - [ ] Test covers all 6 tiers

### Task W5.8 — Drift invariant (d) — full SONHO tree coverage

- **ID:** DOCUMENT-015 (also roadmap C.7, master-04 §6 B-D04 STUBBED)
- **Title:** De-stub the B-D04 drift invariant (was STUBBED per master-02)
- **Source:** master-04 §6, Diag 04
- **Dependencies:** Plan A Task 10 ref (drift_invariants.py registry), W5.7
- **Effort:** 1d
- **Files affected:** `src/ikigai/src/security/drift_invariants.py`
- **Acceptance criteria:**
  - [ ] Drift invariant (d) is no longer STUBBED
  - [ ] Test asserts all 6 SONHO-tree tiers have at least 1 entity in vault/
  - [ ] Drift detector returns 12/12 PASS

### Task W5.9 — Operator TUI SONHOs tab

- **ID:** W5.9 (also roadmap C.8)
- **Title:** Add 5th tab "SONHOs" to operator TUI (currently 4 tabs: Tasks/Adapters/Backend/Queue)
- **Source:** master-02 §2 (frontend)
- **Dependencies:** W5.7 (mesh show traversal), W5.8 (drift invariant d)
- **Effort:** 2-3d
- **Files affected:** `interfaces/tui/operator/app.py`, `interfaces/tui/operator/data.py`
- **Acceptance criteria:**
  - [ ] 5th tab "SONHOs" displays the full tree
  - [ ] Tab respects Plan A A.4 SONHO seed templates
  - [ ] No regression on existing 4 tabs

### Task W5.10 — Empirical algorithm tuning (post-SONHO-5)

- **ID:** W5.10 (also roadmap C.4)
- **Title:** Tune algorithm parameters via prompt-template iteration ONLY (per ADR-019)
- **Source:** master-04 §2 (ADR-019), master-02 §1 (C.4)
- **Dependencies:** 5+ SONHO logs collected (W5.6), ADR-019 Accepted (W5.2)
- **Effort:** 4-8 weeks (iterative)
- **Files affected:** `src/ikigai/src/prompts/*.md` (only)
- **Acceptance criteria:**
  - [ ] 1 prompt-template update per week (at minimum)
  - [ ] NO new Python constants in agent code (ADR-019 enforcement)
  - [ ] Drift detector verifies prompt-template-only pattern
  - [ ] Each prompt change references a SONHO log evidence

### Task W5.11 — Real-world debugging

- **ID:** W5.11 (also roadmap C.5)
- **Title:** Address API rate limits, vault conflicts, taskdog hangs discovered during W5.6+ usage
- **Source:** master-02 §1 (C.5)
- **Dependencies:** W5.2 (feedback loop live)
- **Effort:** 1 week (continuous)
- **Files affected:** various (depends on findings)
- **Acceptance criteria:**
  - [ ] API 529 retry logic documented + tested
  - [ ] Vault conflict resolution path exists
  - [ ] taskdog hang detection + recovery exists
- **Out of scope:** preventive design (only addresses observed issues)

### Task W5.12 — Spec fills (13 GAP tasks)

- **ID:** DOC-013 (aggregates 13 sub-tasks)
- **Title:** Write spec stubs for 13 GAP tasks identified in master-04 §4
- **Source:** master-04 §4
- **Dependencies:** none (parallel work)
- **Effort:** 13-19h
- **Files affected:** `docs/superpowers/specs/2026-09-04-*.md` (13 new files)
- **Acceptance criteria:**
  - [ ] B-G01 spec (now satisfied by W3.1)
  - [ ] B-G03 spec (now satisfied by W3.5)
  - [ ] B-N10 spec (now satisfied by W4.4)
  - [ ] B-N11 spec (now satisfied by W4.5)
  - [ ] B-M14 spec
  - [ ] B-D04 spec (now satisfied by W5.8)
  - [ ] B-D05 spec (now satisfied by W4.7)
  - [ ] B-T02 spec (transition matrix per-tier)
  - [ ] B-T03 spec (audit log shape)
  - [ ] B-T04 spec (phase FSM)
  - [ ] B-T02/T03/T04 spec orphans (5 subprocess-wiring sub-tasks under B-N01/N05/N08)
  - [ ] All 13 spec stubs reviewed + Accepted

### Task W5.13 — Spec orphan cleanup (SUPERSEDED trailers)

- **ID:** DOC-014
- **Title:** Add SUPERSEDED trailers to 8 spec orphans identified in master-04 §5
- **Source:** master-04 §5
- **Dependencies:** none (mechanical)
- **Effort:** 2-3h
- **Files affected:** `docs/superpowers/specs/*` (8 files)
- **Acceptance criteria:**
  - [ ] 3 SUPERSEDED specs have trailer
  - [ ] 1 stale §4 (deleted agentic_writer reference) has trailer
  - [ ] 1 harness reference (non-existent module) has trailer
  - [ ] 1 Go TUI design (forward-looking) has trailer
  - [ ] 2 SUPERSEDED plans have trailer
  - [ ] 1 archive reference has trailer

### Task W5.14 — Implementation orphan specs (10 stubs)

- **ID:** DOC-015 (aggregates 10 sub-tasks)
- **Title:** Write spec stubs for 10 implementation orphans identified in master-04 §6
- **Source:** master-04 §6
- **Dependencies:** none (parallel work)
- **Effort:** 4-8h
- **Files affected:** `docs/superpowers/specs/2026-09-04-*.md` (10 new files)
- **Acceptance criteria:**
  - [ ] `tools_v2.py` spec
  - [ ] `legacy_reference/` trailer
  - [ ] `FAKE_LLM` stub spec (testing pattern)
  - [ ] hardcoded QHE constants spec (now satisfied by W3.2; doc references W3.2 fix)
  - [ ] kill switch semantics spec
  - [ ] `planning.py` migration drift spec
  - [ ] `interfaces/tui/operator/` README fix (now done in memory)
  - [ ] `taskdog_mcp/` Path 3 spec (notes on-disk OFF state)
  - [ ] `review_queue` standalone spec (already covered by ADR-012 + Plan A; refactor to standalone)
  - [ ] `investigation_queue` spec (now satisfied by W5.5)

**Wave 5 total: ~12 weeks + 4-8 weeks calibration. Continuous iteration, no single ship event.**

---

## Task dependency graph (compact)

```
URGENT: W3.0 (ADR-023 UEID)
W1 (5h) ── standalone
W2 (11h) ── depends on W1
W3.1 ── standalone (fix pytest)
W3.2 ── standalone (QHE constants, parallels W3.1)
W3.3 ── depends on W3.1 (smoke test)
W3.4 (ADR-014) ── standalone, parallels W3.3
W3.5 ── depends on W3.3 + ADR-014
W3.6 ── depends on W3.5
W3.7 ── standalone (data fix), parallels W3.x
W3.8 ── depends on W3.5, W3.6, W3.7
W4.1 (ADR-015) ── standalone, parallels W3.x
W4.2 (ADR-016) ── standalone, parallels W3.x
W4.3 (ADR-017) ── depends on ADR-016
W4.4 ── depends on ADR-015 + W3.8
W4.5 ── depends on ADR-016 + W4.4
W4.6 ── depends on ADR-017 + W4.5
W4.7 ── depends on ADR-018
W4.8 ── depends on W4.4, W4.5, W4.6, W4.7
W5.1 (ADR-018) ── standalone, parallels W4.x
W5.2 (ADR-019) ── depends on W3.2
W5.3 (ADR-020..024) ── W3.0 first, others parallel
W5.4 ── depends on ADR-014 + W3.5
W5.5 ── depends on W3.x (Plan C independent of sub-agent work)
W5.6 ── depends on W3.5 (daily binding)
W5.7 ── depends on W5.5
W5.8 ── depends on Plan A ref + W5.7
W5.9 ── depends on W5.7, W5.8
W5.10 ── depends on W5.6 (5+ SONHO logs) + ADR-019
W5.11 ── depends on W5.2 (feedback loop live)
W5.12 ── standalone (spec fills)
W5.13 ── standalone (cleanup)
W5.14 ── standalone (orphan specs)
```

## Critical path

```
W3.0 → W3.1 → W3.3 → W3.5 → W3.6 → W3.8 → W4.4 → W4.5 → W4.6 → W4.8 → W5.2 → W5.6 → W5.10
```

**Critical path length: 1.5h + 4h + 4h + 8h + 8h + 4h + 12h + 12h + 8h + 8h + 6h + ongoing + 4-8 weeks = ~12 weeks focused + 4-8 weeks calibration.**

## Open questions for user

1. **W3.0 (ADR-023 UEID):** decide NOW (1-2h) or defer to W3?
2. **Wave 1 ship today:** independent low-risk PR; can run while ADRs are being drafted.
3. **W3.2 (QHE constants) before W3.5:** yes, prevents algorithm-mistakes propagating.
4. **Plan C re-dispatch timing:** W3 (independent) or W5 (after Scenario A proven)?
5. **B-N10 → B-N11 sequential vs parallel:** assume sequential per master-02; confirm.
6. **Two vs three developer team:** assume single + occasional parallel spike authors.
