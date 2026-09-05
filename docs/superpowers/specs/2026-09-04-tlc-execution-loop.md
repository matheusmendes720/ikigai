# TLC Specs-Driven Execution Loop — dcode Harness

**Generated:** 2026-09-04
**Methodology source:** `tech-leads-club/agent-skills` → `tlc-spec-driven` v3.3.0 (Felipe Rodrigues)
**Phase auto-size:** Complex (multi-component, ambiguous, 38+ tasks across 5 waves + 11 ADRs)
**Companions:** `2026-09-04-dcode-harness-PLAN.md` + `2026-09-04-dcode-harness-TASKS.md`
**Status:** Loop ready; per-phase execution awaits Wave 1 ship decision

---

## 1. TLC 4-phase loop applied to dcode harness roadmap

```
┌──────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐
│ SPECIFY  │ → │  DESIGN  │ → │  TASKS  │ → │ EXECUTE │
└──────────┘   └──────────┘   └─────────┘   └─────────┘
   ✅ DONE        ✅ DONE        ✅ DONE       ⏳ READY
   (4 masters)  (master-01)    (TASKS.md)    (this file
                                              is the loop)
```

The 4 masters ARE the Specify phase (WHAT to build). Master-01 IS the Design phase (HOW). TASKS.md IS the Tasks phase (atomic breakdown). This document IS the Execute phase scaffolding (per-task discipline, gates, Verifier).

**Why one document for Execute:** the 4 masters + PLAN + TASKS already exist; this adds the EXECUTE layer that runs each task through TLC's per-task cycle without re-writing the others.

---

## 2. Test Coverage Matrix (codebase-sampled)

> **Guidelines found:** `life/CLAUDE.md` §"CI / Quality Gates" specifies `ruff check`, `ruff format --check`, `mypy src/`, `pytest -m "not e2e"` as canonical CI gates. `conftest.py` + `pytest.ini` are the test runner config. **AGENTS.md** not present at repo root. Strong defaults applied for layers without explicit guideline.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Pydantic contracts | unit | All 6 SONHO-tree models: 1:1 to ACs; frozen=True + extra="forbid" verified | `src/contracts/tests/test_*.py` | `pytest src/contracts/tests/` |
| Domain services (mesh) | unit | All 3 ForkAdapter implementations (create-only); all branch coverage | `src/mesh/tests/test_*.py` | `pytest src/mesh/tests/` |
| MCP tools (ikigai) | unit | All 12 IKIGAI_TOOLS + 7 fork tools (sf_* + tuiboard_*); failure paths | `src/ikigai/tests/test_*.py` | `pytest src/ikigai/tests/ -m "not e2e"` |
| CLI commands (interfaces) | integration | All 16 Typer commands: happy + edge + error paths | `interfaces/cli/tests/test_*.py` | `pytest interfaces/cli/tests/` |
| LangGraph v2 graph | e2e (smoke) | All 10 nodes invoked in sequence; checkpoint integrity | `src/ikigai/tests/test_v2_graph_smoke.py` | `pytest src/ikigai/tests/test_v2_graph_smoke.py` |
| Drift invariants | unit | All 9 invariants enforced; negative tests (must FAIL when invariant violated) | `src/ikigai/src/security/tests/test_drift_invariants.py` | `pytest src/ikigai/src/security/tests/` |
| ADR-013/019 boundary | unit | Grep-based check: no Python constants in `agents/v2/*.py`; prompt-template-only | `src/ikigai/src/security/tests/test_adr_019.py` | `pytest src/ikigai/src/security/tests/test_adr_019.py` |
| Cross-wave E2E smoke | e2e | Wave 3/4/5 smoke tests (B-G05, B.6, C.5) | `src/ikigai/tests/test_v2_*_smoke.py` | `pytest src/ikigai/tests/test_v2_*_smoke.py` |
| Entity / Config / Schema (drift_invariants.py registry) | none | Build gate only | n/a | build gate |

**Layer-type rationale (strong defaults applied):**
- Domain/services layer: 1:1 AC mapping + every listed edge case has a test
- Route/CLI/e2e layer: every command has happy + edge + error paths
- Entity/config layer: build gate only (no behavior to test)
- ADRs are enforced by drift detector (special "test" is a grep-based invariant)

---

## 3. Gate Check Commands (codebase-sampled)

> **Discovered from:** `life/.github/workflows/ci.yml` (canonical CI matrix per CLAUDE.md §CI).

| Gate Level | When to Use | Command |
| --- | --- | --- |
| **Quick** | After tasks with unit tests only (single file changes, drift invariants, contract tests) | `uv run pytest -x -m "not e2e"` |
| **Full** | After tasks with e2e/integration tests (smoke, multi-level E2E) | `uv run pytest -x` (e2e included) |
| **Build** | After phase completion or config/entity-only tasks; final commit before Verifier | `uv run ruff check src/ interfaces/ && uv run ruff format --check src/ interfaces/ && uv run mypy src/ && uv run pytest -m "not e2e"` |
| **Atomic-commit** | Before every commit (Conventional Commits format) | `python3 <tlc-skill-dir>/scripts/check_commit.py --message "<msg>"` |

**Notes:**
- The atomic-commit gate uses TLC's `check_commit.py` script (lives inside the tlc-spec-driven skill dir, not the project).
- The user can wire it as a `commit-msg` git hook to enforce at the git level (no agent dependency). Skip if a pre-commit framework is already configured.
- A non-zero exit on any gate means STOP. Fix before proceeding.

---

## 4. Per-phase Test Hypotheses + Defensive Code + Expected Results

Each wave below follows TLC's pattern: hypothesis → defensive code → expected result. The Verifier at end of each wave runs **discrimination sensor** (inject behavior-level fault, confirm tests kill it).

### Wave 1 — Test hardening (5h) — `wave-1-tests` PR

**Hypothesis 1.1:** Adding tests for `life mesh show/list/propagate` will surface pre-existing bugs that were masked by lack of coverage (especially UEID regex edge cases — see ADR-023 pending decision).

**Hypothesis 1.2:** The audit-log test for `vault_write` will reveal at least one missing transition_validator path (the B-D09 ABSENT drift invariant per master-04 §1).

**Hypothesis 1.3:** Adding tests for `life v2 daily/weekly/monthly/quarterly` will reveal that some entry points currently raise `NotImplementedError` when invoked (referenced-but-unwired per Diag 05).

**Defensive code patterns:**
- `tmp_path` fixture + `monkeypatch` for filesystem + env-var isolation (no global state mutation across tests)
- Each test asserts on `exit_code == 0` AND a specific value (no "no error thrown" tautologies)
- Audit-log test uses a fresh `data/audit/` directory per test (no cross-test contamination)
- Mock `make_v2_graph().invoke()` to avoid real Claude API cost in unit tests

**EARS Acceptance Criteria (Wave 1 deliverable):**

```
AC-W1.1 (ubiquitous): The repository SHALL pass `pytest interfaces/cli/tests/test_mesh_*.py` with 3+ new tests, exit 0.
AC-W1.2 (event-driven): WHEN `vault_write(vault_path, body, actor="user")` is invoked THEN the system SHALL append an entry to `data/audit/vault_write.log` within 100ms.
AC-W1.3 (event-driven): WHEN `vault_write(vault_path, body, actor="agent")` is invoked THEN the system SHALL route through transition_validator BEFORE writing.
AC-W1.4 (unwanted-behavior): IF a test mutates `os.environ["VAULT_ROOT"]` THEN the test SHALL restore it via monkeypatch teardown (no global state pollution).
AC-W1.5 (state-driven): WHILE Wave 1 PR is open, the drift detector SHALL continue returning 8/8 PASS (no regression).
```

**Expected results (Wave 1 done):**
- Test count: +6 (3 mesh + 2 v2 + 1 audit-log)
- Drift detector: 8/8 PASS (unchanged)
- Build gate: green
- 0 new bugs introduced; pre-existing bugs documented as findings (NOT fixed in Wave 1)

---

### Wave 2 — Skill entry points + v2 commands (11h) — `wave-2-skills` PR

**Hypothesis 2.1:** The 4 unwired skill entry points will need different binding patterns (some YAML manifest, some programmatic, some hybrid). Forcing one pattern will fail for at least 1 of the 4.

**Hypothesis 2.2:** `v2 suggest` will surface that the LLM call is best-effort, not deterministic; a heuristic fallback is required (per master-02 §2 W2.1 acceptance criteria note).

**Hypothesis 2.3:** `v2 cycle --dry-run` will reveal that graph introspection needs a new node type (a "planner-only" node that emits trajectory without executing).

**Defensive code patterns:**
- Each new command has ≥1 happy-path + ≥1 error-path + ≥1 json-flag-path test (3 tests per command × 3 new commands = 9 new tests)
- `--dry-run` is implemented as a flag that ONLY suppresses `vault_write` and `taskdog_write` side-effects, NOT `vault_read` or `ikigai_read_tasks` reads
- Skill binding uses a registry pattern (`SKILL_BINDINGS: dict[str, Callable]`) so adding a binding is O(1) lookup
- `v2 suggest` falls back to heuristic (most-recent SONHO + due-soonest task) when LLM unavailable

**EARS Acceptance Criteria (Wave 2 deliverable):**

```
AC-W2.1 (event-driven): WHEN user invokes `life v2 suggest --context "<text>"` THEN the system SHALL return 1-3 task suggestions as JSON.
AC-W2.2 (event-driven): WHEN user invokes `life v2 cycle --dry-run` THEN the system SHALL emit the planned graph trajectory WITHOUT invoking any vault_write or taskdog_write side-effects.
AC-W2.3 (ubiquitous): The system SHALL resolve all 7 expected entry points (daily/weekly/monthly/quarterly/suggest/cycle/help) to real callables.
AC-W2.4 (state-driven): WHILE the LLM API is unavailable, `v2 suggest` SHALL return heuristic suggestions (not raise).
AC-W2.5 (unwanted-behavior): IF `life v2 daily` is invoked without graph state THEN the system SHALL raise a clear error referencing the missing state file (not generic 500).
```

**Expected results (Wave 2 done):**
- 4 unwired skill entry points → wired
- 9 new tests added (3 per command × 3 new commands)
- 0 skill markdown files reference non-existent commands
- Drift detector: 8/8 PASS (still no regression)
- Build gate: green

---

### Wave 3 — Scenario A critical path (32-44h) — `wave-3-scenario-a` PR series

**Hypothesis 3.1:** Fixing pytest collection infra (`consider_namespace_packages = true`) will surface 2-4 OTHER namespace-related issues that were silently broken (master-04 §4: B-G01 has sub-detail missing).

**Hypothesis 3.2:** Migrating `observe.py:56-61` QHE constants to prompt-template will reveal ≥2 other hardcoded algorithm constants elsewhere in `src/ikigai/src/agents/v2/` (the cross-cited violation per master-04 §9).

**Hypothesis 3.3:** The E2E smoke (chat → tag_and_persist → commit_node → vault + taskdog.exe → fork reflects) will fail at the `fork reflects` step because `data/taskdog/tasks.db` does NOT exist (master-01 §6 verdict: "mesh v1 create flow has NEVER persisted to either taskdog or solverforge calendar adapter DB").

**Defensive code patterns:**
- QHE constants migration uses grep + atomic-rename pattern (`DEFAULT_QHE_*` → `prompt_template_ref()`)
- Drift detector extended with ADR-019 enforcement (regex: `re.search(r"DEFAULT_(QHE|REGIME|SCORE)_", agents_v2_path)` MUST be empty)
- `data/tasks.jsonl` writer unification: ALL writers go through CliAdapter (atomic temp+fsync+rename, 14-field schema); `_write_tasks_to_data` becomes a thin wrapper around CliAdapter
- E2E smoke has fallback: if real taskdog.exe unavailable, mock the subprocess call but assert the wrapper would have called it with correct args

**EARS Acceptance Criteria (Wave 3 deliverable):**

```
AC-W3.1 (event-driven): WHEN `pytest src/ikigai/tests/ -v` is invoked THEN the system SHALL collect all tests without import errors.
AC-W3.2 (ubiquitous): The agents/v2/ directory SHALL NOT contain any `DEFAULT_QHE_*`, `DEFAULT_REGIME_*`, or `DEFAULT_SCORE_*` Python constants (drift invariant per ADR-019).
AC-W3.3 (event-driven): WHEN `make_v2_graph().invoke(state)` is called with stub state THEN the system SHALL traverse all 10 nodes sequentially without exception.
AC-W3.4 (event-driven): WHEN `life v2 daily` is invoked THEN the system SHALL write a vault file with actor="user" AND trigger Path 1 taskdog subprocess.
AC-W3.5 (state-driven): WHILE the tasks.jsonl write is in flight, the system SHALL guarantee atomicity (no partial-line state visible to readers).
AC-W3.6 (event-driven): WHEN an E2E smoke invokes `life v2 daily` THEN the system SHALL complete the full chain (vault + taskdog + fork reflect) in <2 minutes.
AC-W3.7 (unwanted-behavior): IF API 529 rate-limit occurs during graph invoke THEN the system SHALL retry up to 3 times with exponential backoff (1s, 2s, 4s).
AC-W3.8 (unwanted-behavior): IF taskdog.exe subprocess fails THEN the system SHALL enqueue the task to data/review_queue/ for later retry (not silent loss).
```

**Expected results (Wave 3 done):**
- Drift detector: 8 → 9 PASS (B-D09 added)
- Build gate: green
- E2E smoke runtime: <2 minutes
- `data/tasks.jsonl` writers: 2 → 1 (unified on CliAdapter)
- Scenario A functional: `life v2 daily` writes task to taskdog.exe + vault

---

### Wave 4 — Scenario B sub-agents + stateful subgraphs (70-92h) — `wave-4-scenario-b` PR series

**Hypothesis 4.1:** The sub-agent dispatch protocol will reveal that current LangGraph subgraphs don't carry actor context — each sub-agent defaults to actor="agent" without a mechanism to override.

**Hypothesis 4.2:** Stateful subgraph checkpoint reading will surface WAL-mode contention when 4 threads run concurrently (per `data/ikigai_checkpoints.db` pattern with 4 threads).

**Hypothesis 4.3:** The cross-cycle memory layer will reveal that "weekly" needs to read from BOTH "daily" checkpoints AND "weekly" prior checkpoints (2 sources, not 1).

**Defensive code patterns:**
- Sub-agent dispatch has bounded timeout (default 60s) + bounded recursion depth (max 3) + bounded output size (max 8KB)
- Checkpoint schema uses version field (`schema_version: int`) so future schema migrations don't break old checkpoints
- Memory layer is append-only (no overwrites); each cycle adds, never replaces
- Drift invariant (e): `vault_write(actor="agent")` MUST route through transition_validator BEFORE writing (closes ADR-018 enforcement gap)

**EARS Acceptance Criteria (Wave 4 deliverable):**

```
AC-W4.1 (event-driven): WHEN a sub-agent is dispatched THEN the system SHALL pass actor context (user/agent) + bounded timeout + bounded output size.
AC-W4.2 (state-driven): WHILE 4 LangGraph threads write checkpoints concurrently, the system SHALL preserve WAL mode integrity (no `database is locked` errors).
AC-W4.3 (event-driven): WHEN `life v2 weekly` is invoked after `life v2 daily` THEN the weekly rollup SHALL include the daily's outputs.
AC-W4.4 (ubiquitous): The checkpoint schema SHALL include `schema_version: int` for forward compatibility.
AC-W4.5 (unwanted-behavior): IF a sub-agent exceeds timeout THEN the system SHALL terminate it and emit a SPEC_DEVIATION marker.
AC-W4.6 (event-driven): WHEN `vault_write(actor="agent")` is invoked THEN the system SHALL route through transition_validator (drift invariant e).
AC-W4.7 (event-driven): WHEN the multi-level E2E smoke runs daily→weekly→monthly→quarterly THEN the system SHALL complete in <5 minutes.
```

**Expected results (Wave 4 done):**
- Drift detector: 9 → 10 PASS (invariant e added)
- Multi-level E2E runtime: <5 minutes
- 4 threads checkpoint without `database is locked`
- Scenario B functional: state persists across daily↔weekly↔monthly↔quarterly

---

### Wave 5 — Scenario C on-the-fly eficaz (12+ weeks) — continuous iteration

**Hypothesis 5.1:** Collecting 5+ SONHO logs will reveal that empirical algorithm tuning has 2 distinct sub-patterns: (a) threshold tuning (when to push vs recover), (b) ordering tuning (which SONHO gets attention first).

**Hypothesis 5.2:** Re-dispatching Plan C (investigation_queue + 3 MCP tools) will hit the same documentation-only trap as last time UNLESS shipped with drift invariant check (master-03 §6 top-5 gap 1).

**Hypothesis 5.3:** Real-world debugging (API rate limits, vault conflicts, taskdog hangs) will surface ≥3 latent issues that the Wave 3/4 tests missed.

**Defensive code patterns:**
- All algorithm tuning goes through prompt-template ONLY (ADR-019); drift detector verifies no Python constants in `agents/v2/*.py`
- Plan C ships with same rigor as Plan A: 6 Pydantic contracts + drift invariant (h) + 3 MCP tools + e2e smoke
- SONHO log collection is friction-zero: `/sonho-log` slash command with template pre-populated
- Real-world debugging findings are captured as fix tasks, NOT silently patched

**EARS Acceptance Criteria (Wave 5 deliverable — progressive):**

```
AC-W5.1 (state-driven): WHILE algorithm tuning is in progress, the system SHALL forbid new Python constants in agent code (ADR-019 enforced by drift detector).
AC-W5.2 (event-driven): WHEN 5+ SONHO logs are collected THEN the system SHALL enable W5.10 (empirical algorithm tuning).
AC-W5.3 (event-driven): WHEN `life mesh show <sonho-ueid>` is invoked THEN the system SHALL traverse the full SONHO tree (6 tiers).
AC-W5.4 (ubiquitous): The drift detector SHALL return 12/12 PASS (10 baseline + Plan A invariant d + Plan C invariant h).
AC-W5.5 (event-driven): WHEN a prompt-template change is proposed THEN the system SHALL require a SONHO log evidence citation.
AC-W5.6 (unwanted-behavior): IF API 529 rate-limit occurs in steady state THEN the system SHALL retry with exponential backoff (1s, 2s, 4s, 8s, 16s) before escalating.
AC-W5.7 (event-driven): WHEN vault_write conflicts with concurrent write THEN the system SHALL retry with VaultLock (per vault_write security model).
```

**Expected results (Wave 5 done — Scenario C):**
- 5+ SONHO logs collected
- Drift detector: 10 → 12 PASS
- Algorithm-tuning CLI produces 1 prompt-template update per week
- Kill switch tested end-to-end (real-world drill)
- Plan C shipped (NOT documentation-only)

---

## 5. Requirement Traceability Matrix (per wave)

> **Format:** `[REQ-ID]` → master spec source → wave → task IDs that implement it → AC pattern from §4.

| REQ-ID | Source | Wave | Implemented by | AC pattern |
| --- | --- | --- | --- | --- |
| **DCODE-01** | master-02 §1 (A.1) | W3 | W3.1 | AC-W3.1 |
| **DCODE-02** | master-02 §1 (A.2) | W3 | W3.3 | AC-W3.3 |
| **DCODE-03** | master-02 §1 (A.3) | W3 | W3.5 | AC-W3.4 |
| **DCODE-04** | master-02 §1 (A.5) | W3 | W3.6 | AC-W3.4 |
| **DCODE-05** | master-02 §1 (A.6) | W3 | W3.8 | AC-W3.6 |
| **DCODE-06** | master-04 §2 (ADR-019 constraint) | W3 | W3.2 | AC-W3.2 |
| **DCODE-07** | master-01 §7 (gap 1) | W3 | W3.7 | AC-W3.5 |
| **DCODE-08** | master-04 §4 (B-D09 ABSENT) | W1 | W1.3 | AC-W1.2, AC-W1.3 |
| **DCODE-09** | master-02 §1 (B-N10) | W4 | W4.4 | AC-W4.1, AC-W4.5 |
| **DCODE-10** | master-02 §1 (B-N11) | W4 | W4.5 | AC-W4.2, AC-W4.4 |
| **DCODE-11** | master-02 §1 (B.4) | W4 | W4.6 | AC-W4.3 |
| **DCODE-12** | master-04 §6 (B-D05) | W4 | W4.7 | AC-W4.6 |
| **DCODE-13** | master-02 §1 (B.6) | W4 | W4.8 | AC-W4.7 |
| **DCODE-14** | master-04 §2 (ADR-018) | W5 | W5.1, W5.3 | AC-W5.6 |
| **DCODE-15** | master-04 §2 (ADR-019) | W5 | W5.2, W5.10 | AC-W5.1, AC-W5.5 |
| **DCODE-16** | master-03 §6 (Plan C unexecuted) | W5 | W5.5 | AC-W5.4 |
| **DCODE-17** | master-02 §1 (C.3) | W5 | W5.6 | AC-W5.2 |
| **DCODE-18** | master-02 §3 (C.6) | W5 | W5.7 | AC-W5.3 |
| **DCODE-19** | master-04 §6 (B-D04 STUBBED) | W5 | W5.8 | AC-W5.4 |
| **DCODE-20** | master-02 §3 (C.8) | W5 | W5.9 | (extends DCODE-18) |

**Coverage:** 20 traceable requirements, all mapped to wave + task + AC pattern. Zero unmapped.

---

## 6. Interdependence Hierarchy (requirements tree)

The user's request explicitly asks for "all test hypotheses between the interdependence hierarchy of the requirements tree at each sequential phase." This section makes that tree explicit.

```
ROOT: dcode harness functional end-to-end
│
├── DCODE-08 (audit log)          [W1, no deps]
│   └── enables: DCODE-12 (drift invariant e) [W4]
│
├── DCODE-01 (pytest infra fix)   [W3, no deps]
│   └── enables: DCODE-02 (graph smoke) [W3]
│       └── enables: DCODE-03 (skill binding) [W3]
│           └── enables: DCODE-04 (CLI wrapper) [W3]
│               └── enables: DCODE-05 (E2E smoke) [W3]
│                   └── enables: DCODE-13 (multi-level E2E) [W4]
│
├── DCODE-06 (QHE constants fix)  [W3, no deps — can parallel with DCODE-01]
│   └── enables: DCODE-15 (ADR-019) [W5]
│       └── enables: DCODE-19 (drift invariant d full SONHO coverage) [W5]
│
├── DCODE-07 (tasks.jsonl unify)  [W3, no deps — can parallel with DCODE-01]
│   └── enables: DCODE-05 (E2E smoke) [W3] — prevents data corruption in E2E
│
├── DCODE-09 (sub-agent dispatch) [W4, depends on DCODE-05]
│   └── enables: DCODE-10 (stateful subgraph) [W4]
│       └── enables: DCODE-11 (memory layer) [W4]
│           └── enables: DCODE-13 (multi-level E2E) [W4]
│
├── DCODE-14 (ADR-018 kill switch) [W5, depends on DCODE-08]
│   └── enables: DCODE-12 (drift invariant e) [W4] — back-fills the invariant
│
├── DCODE-16 (Plan C re-dispatch) [W5, independent — can run anytime after W3]
│   └── enables: DCODE-19 (drift invariant d) [W5]
│
├── DCODE-17 (SONHO log collection) [W5, depends on DCODE-03]
│   └── enables: DCODE-15 (algorithm tuning) [W5] — gates W5.10
│
├── DCODE-18 (mesh show SONHO tree) [W5, depends on DCODE-16]
│   └── enables: DCODE-20 (TUI SONHOs tab) [W5]
│       └── enables: DCODE-19 (drift invariant d) [W5]
│
└── DCODE-19 (drift invariant d)  [W5, depends on DCODE-15 + DCODE-18 + DCODE-16]
    └── enables: DCODE-20 (TUI SONHOs tab) [W5]
```

**Hypotheses at each dependency edge (testable):**

| Edge | Hypothesis | Test | Expected result |
| --- | --- | --- | --- |
| DCODE-08 → DCODE-12 | Audit log invariant will catch a missing transition_validator path during W4 | `test_drift_invariant_e` injects bypass, asserts FAIL | Test kills mutation, drift detector invariant e = PASS |
| DCODE-01 → DCODE-02 | Pytest infra fix will reveal OTHER namespace-related issues | `pytest src/ikigai/tests/ -v` after fix | Collection passes; potential secondary findings documented |
| DCODE-02 → DCODE-03 | Smoke test will expose that entry_point binding is not yet wired | `test_v2_graph_smoke` invokes with entry_point="daily" | Failure mode: NotImplementedError → fixed by W3.5 |
| DCODE-06 → DCODE-15 | Migrating QHE constants will reveal ≥2 other hardcoded algorithm constants | `grep -r "DEFAULT_" src/ikigai/src/agents/v2/` | ≥2 additional findings; each becomes a fix task |
| DCODE-07 → DCODE-05 | tasks.jsonl unification will prevent data corruption in E2E | `test_v2_e2e_smoke` writes 100 tasks concurrently | All 100 atomic, no partial-line state visible |
| DCODE-09 → DCODE-10 | Sub-agent dispatch will reveal actor context gap | `test_sub_agent_dispatch` mocks no actor override | Test fails → fix: add actor param to dispatch |
| DCODE-10 → DCODE-11 | Stateful subgraph will surface WAL contention with 4 threads | `test_stateful_subgraph` spawns 4 threads concurrently | 4 successful checkpoints, 0 `database is locked` |
| DCODE-16 → DCODE-19 | Plan C re-dispatch will fail same trap unless drift invariant check present | `validate_tasks.py 2026-09-04-investigation-queue-tasks.md` | Validates BEFORE code is written |
| DCODE-17 → DCODE-15 | Without 5+ SONHO logs, empirical tuning will produce no signal | `sonho_log_count >= 5` gate before W5.10 starts | W5.10 cannot START until gate passes |

---

## 7. Verifier Checklist (per-wave closure)

After the LAST task of each wave commits, a fresh **Verifier** sub-agent runs automatically (TLC's `validate.md` flow). **Author ≠ verifier** to break the mental-model loop.

**Verifier runs:**

1. **Spec-anchored AC check** — for each AC in §4, re-derive the spec-defined expected outcome and confirm the test assertion matches it (not just that an assertion exists). Evidence-or-zero: each criterion cites `file:line + assertion expression`.

2. **Discrimination sensor** — inject behavior-level faults in a scratch worktree (never mutate the real tree; never `git stash`). Mutations chosen per risk:
   - Wave 1: flip a boolean in audit-log check (e.g., `actor == "user"` → `actor != "user"`); confirm test kills it
   - Wave 2: change `v2 suggest` heuristic fallback to return empty list; confirm test kills it
   - Wave 3: change atomic write to non-atomic (remove fsync); confirm test kills it
   - Wave 4: remove sub-agent timeout; confirm test catches the hanging case
   - Wave 5: change prompt-template reference to hardcoded Python constant; confirm drift detector catches it

3. **Code quality check** (TLC `coding-principles.md`):
   - Minimum code; surgical changes; no scope creep; matches existing patterns
   - Spec-anchored outcome check (asserted values match spec outcomes)
   - Per-layer Coverage Expectation met
   - Every test maps to a spec requirement

4. **Write `.specs/features/dcode-harness-w[N]/validation.md`** with PASS/FAIL + per-AC evidence + sensor result.

5. **Return compact verdict** to orchestrator:
   ```
   ## Validation: dcode-harness W[N] - [PASS ✅ | FAIL ❌]
   **Spec-anchored check**: [N/N ACs matched | M spec-precision gaps]
   **Gate**: [X passed, 0 failed]
   **Sensor**: [N mutations, N killed, N survived]
   **Report**: .specs/features/dcode-harness-w[N]/validation.md
   **Ranked gaps** (if FAIL): [...]
   ```

6. **Distill lessons** (only grounded failures; clean PASS records nothing):
   - Surviving mutant → fix task → re-verify (bounded to 3 iterations before escalating)
   - Spec-precision gap → flag in report + add to spec as new AC

---

## 8. Critical-path execution order (TLC worker-batch packing)

TLC's packing rule: phases into ~7-task batches; never split a phase across workers; batches run sequentially.

For the dcode harness roadmap:
- **Batch 1** (W1: 3 tasks, 5h) — single worker, inline OK
- **Batch 2** (W2: 3 tasks, 11h) — single worker, inline OK
- **Batch 3** (W3: 9 tasks incl. 1 ADR, 32-44h) — single worker, inline OK (≤8 tasks after ADR-023 splits out)
- **Batch 4** (W4: 8 tasks incl. 3 ADRs, 70-92h) — split: Batch 4a (W4.1-W4.4: 4 tasks, ~40h) + Batch 4b (W4.5-W4.8: 4 tasks, ~50h)
- **Batch 5** (W5: 14 tasks incl. 5 ADRs, 12+ weeks) — split: Batch 5a (ADRs: 5 tasks, ~40h) + Batch 5b (impl + spec fills: 9 tasks, ~12 weeks)

**Sub-agent offer trigger:** >8 tasks per batch → offer sub-agents; ≤8 → execute inline. For this roadmap, Batch 4 and Batch 5 cross the threshold → sub-agent dispatch.

---

## 9. Decision log (mini-STATE.md)

Per TLC's `memory.md`, the project maintains `.specs/STATE.md` with:
- `## Decisions` — locked at Design; supersedes require new AD-NNN
- `## Handoff` — snapshot for resume

**Active decisions binding this execution loop:**

| AD-NNN | Decision | Source | Status |
| --- | --- | --- | --- |
| AD-007 | vault_write = canonical writer | ADR-007 | active |
| AD-011 | HTTP+SSE backend topology | ADR-011 | active |
| AD-012 | vault_write sole vault writer | ADR-012 | active |
| AD-013 | agent = planner-only, math out | ADR-013 | active |
| (PEND-023) | UEID canonical 4 vs 5 part | master-04 §3 | **pending decision** |
| (PEND-019) | Algorithm tuning = prompt-template only | master-04 §9 | **pending ADR write** |
| (PEND-016) | Stateful subgraph strategy | master-04 §2 | **pending ADR write** |
| (PEND-015) | Sub-agent dispatch protocol | master-04 §2 | **pending ADR write** |
| (PEND-014) | Skill binding mechanism | master-04 §2 | **pending ADR write** |
| (PEND-018) | Kill switch + review queue | master-04 §2 | **pending ADR write** |

**The 5 pending ADRs are the execution loop's hard gates.** Each must be Accepted before its dependent wave task can start. Critical-path ADR-023 first (1-2h), then ADR-016 → ADR-015 → ADR-017 → ADR-014 → ADR-018 → ADR-019.

---

## 10. Open questions for user (TLC loop gating)

1. **Wave 1 ship today** — independent low-risk PR; can run while ADRs drafted. **Recommended.**
2. **ADR-023 UEID decision NOW** — 1-2h unblocks downstream work. **Recommended.**
3. **Sub-agent dispatch for Wave 4/5** — confirm offer-then-confirm pattern. **Default: yes.**
4. **Bounded 3-iteration fix→re-verify** — escalate after 3 rounds. **Default: yes.**
5. **Conventional Commits format enforced** — wire `check_commit.py` as `commit-msg` hook. **Default: yes.**
6. **`.specs/` directory location** — TLC standard is repo root. CLAUDE.md says avoid root files. **Recommend:** keep `.specs/` at root (TLC runtime memory, not working files); add to `.gitignore` if undesired.

---

**Loop ready.** Awaiting user decision on Wave 1 ship + ADR-023 to begin Wave 1 execution.
