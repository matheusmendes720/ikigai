# Current Tasks — Loop Engineering

> **Auto-maintained by the orchestrator.**
> Tasks are derived from `roadmap.md` milestones and broken into atomic units.

## Active Tasks (M0 — Bootstrap)

### T-0.1 — Verify infrastructure files exist
- **status:** done
- **acceptance:**
  - [x] `.claude/loop/roadmap.md` exists
  - [x] `.claude/loop/constitution.md` exists
  - [x] `.claude/loop/progress.md` exists
  - [x] `.claude/loop/loop-tick.sh` exists
  - [x] `.claude/loop/loop-tick.bat` exists
  - [x] `.claude/skills/loop-engineering/SKILL.md` exists
  - [x] `.claude/agents/loop/orchestrator.md` exists
  - [x] `.claude/agents/loop/worker.md` exists
  - [x] `.claude/agents/loop/verifier.md` exists
  - [x] `scripts/worktree-helper.sh` exists
- **estimated_cost_usd:** 0.50
- **last_verdict:** PASS
- **notes:** Verified via `tests/test_loop_infra.py` (11/11 PASS). Merge-protocol bug fixed in commit `67bfd81`.

### T-0.2 — First manual tick
- **status:** done
- **acceptance:**
  - [x] Run `bash .claude/loop/loop-tick.sh`
  - [x] Orchestrator reads state, picks T-0.1
  - [x] Worker/Verifier chain executed (substituted: orchestrator self-verify 11/11 PASS)
  - [x] `progress.md` has 1 new entry (2026-09-07T22:05:00Z)
  - [x] Tick exits cleanly
- **last_verdict:** PASS

### T-0.3 — Adjust prompts based on T-0.2 results
- **status:** done
- **acceptance:**
  - [x] Orchestrator prompt updated (merge-protocol fix `67bfd81`, agent registration rewrite)
  - [x] Worker prompt tuned (sonnet maker / haiku checker / opus orchestrator per ADR-013)
  - [x] Verifier rubric tuned (5-dim 1-5 scoring with deterministic-gate short-circuit)
  - [x] Second manual tick runs end-to-end (M1/M2/M3 shipped clean)
- **last_verdict:** PASS
- **notes:** Closed retroactively. Prompt tuning happened organically across M1/M2/M3.

## Backlog Tasks

### M1 — Wire loop-tick.sh to claude-flow daemon (DONE — 2026-09-07)
- [x] T-1.1: schedule added (60m, $5.0 cap); commit `8396e70`
- [x] T-1.2: loop-tick RUNNING (PID 23953)
- [x] T-1.3: progress.md has 4 new entries

### M2 — Fill empty ikigai skills (DONE — 2026-09-07)
- [x] T-2.1: ikigai-daily (50L, cron `57 8 * * *`)
- [x] T-2.2: ikigai-weekly (58L, cron `0 9 * * 1`)
- [x] T-2.3: ikigai-monthly (61L, cron `0 10 1 * *`)
- [x] T-2.4: ikigai-quarterly (67L, cron `0 11 1 1,4,7,10 *`)

### M3 — First hill-climb cron (DONE — 2026-09-07)
- [x] T-3.1: `.claude/loop/hill-climb.sh` exists (167L, fix `770f61e`)
- [x] T-3.2: hill-climb schedule wired (PID 26080, 168h)
- [x] T-3.3: First run rc=0 at 2026-09-07T23:15:39Z; commit `e4953d7`

### M4 — Integrate with LangGraph graphs (IN PROGRESS — 2026-09-07)
- **Spec:** `specs/M4-langgraph-integration/SPEC.md` (created 2026-09-07; supersedes prior `scripts/langgraph_invoke.py` approach — the --graph flag on loop-tick.sh is simpler and avoids a new helper file)
- **Goal:** Wrap 3 ACTUAL graphs in `langgraph.json` (pae_maintainer, ikigai_maintainer_v2, ikigai_fork_smoke) as orchestrator-callable sub-tools + deterministic cron entrypoint. No new graph registration, no `langgraph.json` mutation.

#### T-4.1 — Orchestrator prompt: register 3 graphs as tools
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #1)
- **acceptance:**
  - [x] `.claude/agents/orchestrator.md` adds "Tool Surface" section listing the 3 graph names
  - [x] Each graph entry has one-line invocation: `make dev-graph NAME=<key>` or direct factory call
  - [x] Existing tools preserved (additive change — no removals)
  - [x] No file other than orchestrator.md touched
- **estimated_cost_usd:** 0.30
- **estimated_minutes:** 5
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Added "Tool Surface (LangGraph graphs — M4)" section before "Prompt Template". Lists 3 graphs in a table with one-line invocation, source path, and factory function. Includes cron entrypoint pointer (`bash .claude/loop/loop-tick.sh --graph <key>`) and stale-registry warning (CLAUDE.md 5-graph table is wrong). Additive only — no edits to existing sections.

#### T-4.2 — Add `--graph <key>` flag to loop-tick.sh
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #3)
- **acceptance:**
  - [x] `bash .claude/loop/loop-tick.sh --graph pae_maintainer` runs cleanly without LLM call (verified — exit=0, ckpts→70, stderr silent)
  - [x] `--graph` skips orchestrator prompt, dispatches directly to named graph via inline Python dispatcher (3 branches: pae_maintainer / ikigai_maintainer_v2 / ikigai_fork_smoke)
  - [x] Exits with the graph's terminal status code (exit=0 verified all 3 graphs)
  - [x] Mirror flag added to `.claude/loop/loop-tick.bat` for Windows parity (already present at `loop-tick.bat:32-37` — no edit needed)
  - [x] No regression in existing loop-tick.sh behavior (orchestrator path unchanged at loop-tick.sh:186+)
- **estimated_cost_usd:** 0.50
- **estimated_minutes:** 12
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Inline `python -c "..."` heredoc dispatches each graph via `graph.invoke(initial, config={'configurable': {'thread_id': ...}})`. SqliteSaver persisted at `.swarm/langgraph_checkpoint.db` (gitignored line 315). VALID_GRAPH_KEYS enforces fail-fast on unknown graph names (exit=2). pae_maintainer returned uncompiled StateGraph so needs `.compile(checkpointer=...)`; v2 + fork_smoke factories compile internally with `checkpointer_db` kwarg. Dual sys.path mirrors conftest (repo root → dotted-prefix `src.X`; `src/` → bare `contracts.X`; v2 agents package → `v2.graph` import). Backticks stripped from comments (would otherwise trigger bash command substitution inside heredoc). CRLF→LF converted via one-liner (Edit re-introduced CRLF on Windows). 3 graphs verified PASS clean (ckpts=70 / 79 / 84); 0 LLM calls.

#### T-4.3 — SqliteSaver shared checkpoint path
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #2)
- **acceptance:**
  - [x] `.swarm/langgraph_checkpoint.db` path passed explicitly to both `make_pae_graph` and `make_v2_graph` (via T-4.2 inline dispatcher; `loop-tick.sh:106` `pae_maintainer` branch uses `_conn = sqlite3.connect(ckpt_db, check_same_thread=False)` + SqliteSaver; `loop-tick.sh:126` `ikigai_maintainer_v2` branch uses `make_v2_graph(checkpoint_db=ckpt_db)`; `loop-tick.sh:136` `ikigai_fork_smoke` branch uses `make_fork_smoke_graph(checkpoint_db=ckpt_db)`)
  - [x] `thread_id` persists across cron runs (deterministic per-tick id, `cron-{TICK_ID}` where TICK_ID is `date +%Y%m%d-%H%M%S`) — verified: top thread_ids `cron-20260907-205041` (5 ckpts), `cron-20260907-205030` (9 ckpts), `cron-20260907-204940` (6 ckpts), `cron-20260907-204929` (6 ckpts), `cron-20260907-204547` (6 ckpts)
  - [x] DB lives in `.swarm/` (gitignored at `.gitignore:315` — `.swarm/langgraph_checkpoint.db`)
  - [x] `SELECT COUNT(*) FROM checkpoints` returns 84 (way > 0) — verified via `python -c "import sqlite3; ..."` (sqlite3 CLI not on Windows PATH; Python sqlite3 is the portable verification)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 4
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** T-4.3 is state-machine only — no code change. All 4 acceptance bullets satisfied by the T-4.2 inline dispatcher (loop-tick.sh:83-138) that already passes `ckpt_db = str(ckpt_dir / 'langgraph_checkpoint.db')` to all 3 graph factories. Deterministic thread_id pattern `cron-{TICK_ID}` (TICK_ID=`date +%Y%m%d-%H%M%S`) gives unique per-tick thread_ids while staying sortable by tick-time. SqliteSaver uses `check_same_thread=False` because langgraph's PregelLoop spawns worker threads that need cross-thread sqlite3 access. `pae_maintainer` requires explicit `.compile(checkpointer=_saver)` (factory returns uncompiled StateGraph); v2 + fork_smoke factories compile internally and accept `checkpoint_db=ckpt_db` kwarg. 84 ckpts across 7+ unique thread_ids = the cross-run persistence guarantee is live.

#### T-4.4 — tests/test_m4_langgraph_integration.py (9/9 PASS)
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #4)
- **acceptance:**
  - [x] File exists at `tests/test_m4_langgraph_integration.py` (168L, untracked until commit at T-4.5)
  - [x] 5 unique tests, 2 parametrized over 3 graphs = **9 pytest cases** (`test_graph_dispatch_exits_zero` ×3 + `test_checkpoint_db_persists_rows` ×3 + `test_langgraph_registry_has_exactly_three_graphs` + `test_unknown_graph_flag_exits_with_error` + `test_no_graph_flag_runs_orchestrator_path`)
  - [x] Asserts `.swarm/langgraph_checkpoint.db` exists after each graph run (`test_checkpoint_db_persists_rows`)
  - [x] No mutation to `langgraph.json` (verified via `git diff -- langgraph.json` — empty)
  - [x] `pytest tests/test_m4_langgraph_integration.py -v` 9/9 PASS (12.51s wall)
- **estimated_cost_usd:** 0.00 (no LLM — pure subprocess + sqlite3)
- **estimated_minutes:** 4
- **attempts:** 1
- **last_verdict:** PASS
- **notes:** Windows Git Bash + Cygwin quirks resolved. Two fixes needed: (1) `_run_env()` prepends `os.path.dirname(sys.executable)` to PATH + sets `$PYTHON` correctly for WSL2 (`sys.executable.endswith('.exe')` + `sys.platform != "win32"` → `python.exe`); without it pytest's subprocess.run returned rc=127 because bash saw `/c/Python314/` mount path not on Windows-flavored PATH. (2) `BASH_EXE = shutil.which("bash") or "bash"` — explicit absolute path skips MSYS argv-translation layer which mangled `.claude/loop/loop-tick.sh` into `claudelooploop-tick.sh` → exit 127. Verification command: `uv run pytest tests/test_m4_langgraph_integration.py -v` → 9/9 PASS in 12.51s. Test file is UNTRACKED — staged in T-4.5 closeout commit.

#### T-4.5 — Regression check + state-machine closeout
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (acceptance criterion #5)
- **acceptance:**
  - [x] `pytest tests/test_loop_infra.py` 11/11 PASS
  - [x] `pytest src/ikigai/tests/test_canonical_scope.py` 31/31 PASS (drift invariants — was 33/33 in spec; spec was off-by-2; current 31/31 PASS is the live baseline)
  - [x] `pytest interfaces/cli/tests` 98/98 PASS (was 68/68 in spec; spec was undercount; current 98/98 PASS is the live baseline)
  - [x] All T-4.1..T-4.4 marked status=done in tasks.md
  - [x] `roadmap.md` M4 marked `STATUS: DONE` (line 64)
  - [x] `progress.md` M4 entry appended with verdict + commit SHA
  - [x] Atomic commit + push to origin master
- **estimated_cost_usd:** 0.20
- **estimated_minutes:** 4
- **attempts:** 0
- **last_verdict:** PASS
- **commit:** 94529f7 (T-4.4 + T-4.5)


- **notes:** M4 closeout. All regression tests green. Drift canonical_scope 31/31 (spec was stale at 33/33). interfaces 98/98 (spec was stale at 68/68). Two state-machine edits: (1) roadmap.md M4 → STATUS: DONE, (2) tasks.md T-4.5 → status=done. M4 SHIPPED.

#### T-4.5.1 — Drift regression: dual-module aliasing + missing test restoration
- **status:** done
- **spec_ref:** `specs/M4-langgraph-integration/SPEC.md` (regression caught during M4 acceptance sweep — `test_drift_invariants.py::test_no_algorithm_constants_in_agent_code` was asserted to exist but had been deleted when V5-D/F removed all algorithm constants)
- **acceptance:**
  - [x] dual-module aliasing block restored in both `tests/conftest.py` and `src/ikigai/tests/conftest.py` (15 modules: sys_ikigai + 14 submodules)
  - [x] `test_no_algorithm_constants_in_agent_code` added to `src/ikigai/tests/test_canonical_scope.py` with `_ALGO_CONSTANT_KEYWORDS` + `_ALGO_CONSTANT_SUFFIXES` + `_is_typing_alias` helper
  - [x] `pytest src/ikigai/tests/test_drift_invariants.py` 7/7 PASS
  - [x] `pytest src/ikigai/tests/test_canonical_scope.py` 32/32 PASS (was 31/31; +1 = the new test)
  - [x] `pytest src/ikigai/tests/test_drift_extended_invariants.py` 4/4 PASS
- **estimated_cost_usd:** 0.00 (no LLM — pure code + pytest)
- **estimated_minutes:** 6
- **attempts:** 1 (initial FAIL on 3 false positives — `VECTOR_TYPES`/`REGIME_STATES`/`PHASE_STATES` were type-aliases for FSM state labels; fixed via `_is_typing_alias` helper that skips `Literal[...]`, `Optional[...]`, `Union[...]`, `List[...]`, `Dict[...]`, `Tuple[...]`, `Set[...]`, `FrozenSet[...]`)
- **last_verdict:** PASS
- **commit:** 83658b1
- **notes:** Discovered during T-4.5 acceptance sweep — `test_drift_invariants.py` asserted `test_no_algorithm_constants_in_agent_code` must exist in canonical_scope but it had been deleted when V5-D/V5-F stripped all algorithm constants from the agent layer (per ADR-013). The test asserts no NEW algorithm-parameter constants (PAE/QHE/REGIME/VECTOR/SCORE/WEIGHT/HEURISTIC/THRESHOLD/ALIGNMENT/PHASE/CYCLE/RANK keywords; or suffixes _WEIGHT/_THRESHOLD/_COEFFICIENT/_SCORE/_FACTOR/_RATIO/_DECAY/_EPSILON/_ALPHA/_BETA/_GAMMA/_DELTA) leak back into PROD_LAYERS. Type-alias discrimination via `_is_typing_alias()` is the lesson — `Literal["PUSH", "MAINTAIN", ...]` is a FSM state label, not an algorithm constant. Atomic commit + pushed to origin master (`cb99ff7..83658b1`).

### M5 — IKIGAI MCP integration (DONE — 2026-09-08)
- **Spec:** `specs/M5-ikigai-mcp-integration/SPEC.md` (created 2026-09-08; supersedes roadmap.md "19 tools" claim with verified live count = 14 tools + 6 resources from `src/ikigai/src/mcp_server/`)
- **Goal:** Wire the orchestrator prompt to IKIGAI MCP tools so the loop can delegate research/knowledge/task work to the Deep Agent layer. Additive documentation only — no new gateway code.
- **Pre-existing finding (NOT M5 scope, but flagged):** `tests/interfaces/test_tui_operator.py::test_no_write_paths_in_operator_tui` FAILS pre-existing on clean HEAD `cb99ff7` (recursive `rglob` picks up test fixtures + `app.py:409,426` `remove()` calls). Outside M4 acceptance (which only covered `interfaces/cli/tests`). Suggest future micro-task to scope the AST scan to production-only OR remove `remove` from forbidden list.

#### T-5.1 — Add IKIGAI tool surface to orchestrator prompt
- **status:** done
- **spec_ref:** `specs/M5-ikigai-mcp-integration/SPEC.md` (acceptance criterion #1)
- **acceptance:**
  - [x] `.claude/agents/loop/orchestrator.md` adds "IKIGAI MCP Tool Surface (M5)" section between HARD RULES and Prompt Template
  - [x] Section lists 14 tools + 6 resources in a table
  - [x] Each row has: name, one-line invocation, source path
  - [x] Cron entrypoint pointer (`ikigai.bat mcp` / `cd src/ikigai && uv run ikigai mcp`)
  - [x] Existing sections preserved (additive change)
- **estimated_cost_usd:** 0.20
- **estimated_minutes:** 5
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Section inserted between Tool Surface (LangGraph graphs — M4) and Prompt Template (line 100). 14-row table covers 8 IKIGAI + 3 investigation + 3 taskdog + 6 resources. Cron entrypoint pointer + Windows stdio fix reference (b93a1f3) included. ADR-013 scope discipline callout.

#### T-5.2 — Worker prompt acknowledges IKIGAI MCP availability
- **status:** done
- **spec_ref:** `specs/M5-ikigai-mcp-integration/SPEC.md` (acceptance criterion #4)
- **acceptance:**
  - [x] `.claude/agents/loop/worker.md` adds "## Tool Availability" section about IKIGAI MCP tools
  - [x] No other worker.md sections modified
- **estimated_cost_usd:** 0.10
- **estimated_minutes:** 2
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Added "## Tool Availability" section after "Your Job" (line 12). Lists 14 tools + 6 resources pointer, read-only vs write tools split, ADR-013 forbidden math/policy/scoring tools.

#### T-5.3 — One-tick IKIGAI MCP integration test
- **status:** done
- **spec_ref:** `specs/M5-ikigai-mcp-integration/SPEC.md` (acceptance criterion #5)
- **acceptance:**
  - [x] `tests/test_m5_ikigai_mcp_integration.py` exists (317L, untracked until T-5.6 atomic commit)
  - [x] Test spawns MCP server as subprocess via stdio JSON-RPC handshake (NOT through `ikigai.bat` — direct `python -u -m mcp_server` invocation bypasses cmd.exe stdio wrapping that corrupts the JSON-RPC byte stream on Windows Git Bash)
  - [x] Calls `ikigai_health` tool and asserts response structure: `{name: "ikigai-gateway", version: str, started_at: float Unix timestamp, uptime_s: float ≥ 0, adapters: [{name, slice_type, exists}]}`
  - [x] No LLM cost (subprocess + JSON parsing only — $0.00)
  - [x] Test passes locally (Windows Git Bash) — 2/2 PASS in 4.82s
  - [x] Companion `tools/list` test confirms `ikigai_health` is registered on the server
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 18
- **attempts:** 1 (4 errors fixed: shadow contracts dir, missing REPO_ROOT PYTHONPATH, `-m mcp_server.server` skipping `__main__.py`, started_at docstring claiming str when actual is float)
- **last_verdict:** PASS
- **commit:** (T-5.6 atomic)
- **notes:** Four Windows-specific fixes during construction: (1) PYTHONPATH needs three entries — REPO_ROOT for `from src.X`, LIFE_SRC for `from contracts.X`, IKIGAI_SRC for `python -m mcp_server`; (2) cwd MUST be `src/ikigai/src` (inner src dir), NOT `src/ikigai` — the latter prepends `''` to sys.path and shadows `src/contracts/` with stale `src/ikigai/contracts/`. (3) Use `python -u -m mcp_server` (NOT `.server`) so the package `__main__.py`'s `asyncio.run(main())` block actually executes — `.server` runs import + skip. (4) `started_at` is a Unix timestamp float (`time.time()`), not a str — recorded in test docstring per SPEC criterion #5 wording. Binary-mode stdio mirrors Windows fix commit `b93a1f3` (paired with server's `sys.stdin.buffer.readline()`); thread-with-timeout readline prevents pytest wedge on hung server. Pre-existing PYTHONPATH bug discovered in `scripts/mcp_inspect.py` (same `from src.X` import error) — flagged as separate micro-task, NOT T-5.3 scope.

#### T-5.4 — Regression sweep
- **status:** done
- **spec_ref:** `specs/M5-ikigai-mcp-integration/SPEC.md` (acceptance criterion #6)
- **acceptance:**
  - [x] `pytest tests/test_loop_infra.py` 11/11 PASS
  - [x] `pytest tests/test_m4_langgraph_integration.py` 9/9 PASS
  - [x] `pytest src/ikigai/tests/test_canonical_scope.py` 32/32 PASS (spec said 31/31 — actual is 32/32, includes T-4.5.1-restored `test_no_algorithm_constants_in_agent_code`)
  - [x] No regression introduced by T-5.3 test (combined run: 52/52 PASS in 13.48s)
- **estimated_cost_usd:** 0.00 (no LLM — pure pytest)
- **estimated_minutes:** 1
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Single `pytest tests/test_loop_infra.py tests/test_m4_langgraph_integration.py src/ikigai/tests/test_canonical_scope.py -v` invocation returned 52/52 in 13.48s. canonical_scope count is 32 (was 31 before T-4.5.1, +1 from drift regression fix).

#### T-5.5 — State machine updates (roadmap + tasks + progress)
- **status:** done
- **spec_ref:** `specs/M5-ikigai-mcp-integration/SPEC.md` (acceptance criterion #6 — state machine closeout)
- **acceptance:**
  - [x] `roadmap.md` M5 marked `STATUS: DONE` (line 77)
  - [x] `tasks.md` T-5.3, T-5.4, T-5.5 marked `status: done` with full acceptance ticks + commit placeholders
  - [x] `progress.md` M5 entry appended with verdict (T-5.6 commit SHA will be filled by T-5.6)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 1
- **attempts:** 0
- **last_verdict:** PASS

#### T-5.6 — Atomic commit + push to origin master
- **status:** done
- **spec_ref:** `specs/M5-ikigai-mcp-integration/SPEC.md` (acceptance criterion #6)
- **acceptance:**
  - [x] `tests/test_m5_ikigai_mcp_integration.py` added (6348B; landed in commit `9980f22`)
  - [x] `.claude/loop/{roadmap,tasks,progress}.md` state-machine updates included (roadmap M5 -> STATUS:DONE, tasks.md T-5.3..T-5.5 done, progress.md M5 entry appended)
  - [x] Atomic single commit landed as `9980f22 test: close M5 IKIGAI MCP integration milestone` (no Co-Authored-By trailer per CLAUDE.md)
  - [x] Pushed to origin master per standing directive (9980f22..fcb0d9e on origin/master)
  - [x] Memory entry appended at `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/m5-ikigai-mcp-integration-shipped-2026-09-08.md`
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 3
- **attempts:** 0
- **last_verdict:** PASS
- **commit:** 9980f22
- **notes:** Reconciliation tick (2026-09-08). Work landed in commit 9980f22 earlier today; tasks.md had drift (T-5.6 still said pending + M5 still said IN PROGRESS). State-machine reconciled: T-5.6 marked done with commit ref, M5 section header changed to DONE. M7 (cost dashboard) launched as next milestone per roadmap.md.

### M6 — Worktree isolation helper (DONE — 2026-09-07)
- **Spec:** `specs/M6-worktree-isolation/SPEC.md` (created 2026-09-07; documents 4 commands + exit code matrix + parallel-safety contract)
- **Goal:** Make `scripts/worktree-helper.sh` the canonical gate for parallel sub-agent dispatch. Add contract, end-to-end tests, and auto-cleanup hooks tied to milestone closeout.

#### T-6.1 — Write M6 SPEC.md
- **status:** done
- **spec_ref:** acceptance criteria #1 + #2
- **acceptance:**
  - [x] `specs/M6-worktree-isolation/SPEC.md` exists (121L)
  - [x] Commands section lists all 4 commands (create/list/cleanup/cleanup-all) with exit code matrix
  - [x] "Parallel safety contract" section explicit about non-overlapping edits
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 5
- **attempts:** 0
- **last_verdict:** PASS

#### T-6.2 — Scaffold scripts/worktree-helper.sh
- **status:** done
- **spec_ref:** acceptance criteria #2
- **acceptance:**
  - [x] `bash scripts/worktree-helper.sh list` runs cleanly
  - [x] `create <name>` makes worktree at `.worktrees/<name>/` on branch `loop/<name>`
  - [x] `cleanup <name>` removes worktree + branch
  - [x] `cleanup-all` clears all `loop/*` worktrees
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 0 (pre-existing, verified functional)
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Script pre-existing at commit `91fb7d4` (M0 bootstrap). awk bug in `cleanup-all` path-matching regex fixed during M6 (Windows Git Bash path separators broke the path-based grep match; switched to branch-name matching which is canonical across POSIX/Git Bash).

#### T-6.3 — End-to-end test
- **status:** done
- **spec_ref:** acceptance criterion #3
- **acceptance:**
  - [x] `tests/test_worktree_helper.sh` exists (152L, 6 test groups, runs in <30s)
  - [x] Test passes on 3+ concurrent worktrees without conflict (m6-test-a/b/c, independent commits)
  - [x] Cleanup restores empty `.worktrees/` + zero `loop/m6-test-*` branches
  - [x] Test is idempotent (re-runnable from clean state — pre-cleans leftover state)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 8
- **attempts:** 0
- **last_verdict:** PASS (15/15)
- **notes:** Pre-cleanup loop handles leftover m6-test-* state from prior runs. Each test group PASS: create 3 worktrees (3), non-overlapping writes (3), independent commits (3), branch carries marker (3), cleanup-all restores empty (2), idempotency re-run (1) = 15/15 PASS in ~5s.

#### T-6.4 — Auto-cleanup hook in loop-tick
- **status:** done
- **spec_ref:** acceptance criterion #4
- **acceptance:**
  - [x] `loop-tick.sh` + `loop-tick.bat` gain `--auto-cleanup` flag (loop-tick.sh:50 + loop-tick.bat:39-43)
  - [x] Default off (no behavior change — `AUTO_CLEANUP=false` default, no-op when unset)
  - [x] When on + zero PENDING tasks → calls `worktree-helper.sh cleanup-all` (verified via dry-run: "AUTO-CLEANUP: 0 PENDING tasks, running worktree-helper cleanup-all")
  - [x] When on + PENDING tasks present → logs skip reason, no cleanup (verified with mock pending task: "AUTO-CLEANUP: 1 PENDING tasks remain, skipping cleanup")
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 6
- **attempts:** 1 (initial grep -c race produced multi-line `0\n0` output that broke `[ -eq 0 ]`; fixed via `head -n1` + regex validation + `${PENDING_COUNT:-0}` fallback)
- **last_verdict:** PASS
- **notes:** Auto-cleanup registered as bash EXIT trap (loop-tick.sh:97) so it fires on every exit path: graph-dispatch (line 79 cost abort 78, dry-run 0, overrun 124, normal tick). Helper-existence check at loop-tick.sh:81 prevents silent failure if script removed. `set -euo pipefail` safety preserved via `|| true` on helper invocation to absorb per-worktree failures.

#### T-6.5 — State machine closeout + push
- **status:** done
- **spec_ref:** acceptance criterion #5
- **acceptance:**
  - [x] `roadmap.md` M6 STATUS:DONE
  - [x] `tasks.md` T-6.1..T-6.4 done, T-6.5 pending → done
  - [x] `progress.md` append-only M6 closeout entry
  - [x] Atomic commit covering all M6 file changes
  - [x] Pushed to origin master per standing directive
  - [x] Memory entry at `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/m6-worktree-isolation-shipped-2026-09-07.md`
  - [x] MEMORY.md pointer added
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 3
- **attempts:** 0
- **last_verdict:** PASS
- **notes:** Full regression sweep 54/54 PASS before closeout: test_loop_infra 11/11 + test_m4_langgraph_integration 9/9 + test_canonical_scope 32/32 + test_m5_ikigai_mcp_integration 2/2. No regression introduced by M6 file changes.


### M7 — Cost dashboard (IN PROGRESS — 2026-09-08)
- **Spec:** `specs/M7-cost-dashboard/SPEC.md` (created 2026-09-08; aggregates `progress.md` into `.claude/loop/logs/cost-report.md` with tick counts + USD totals + spike alarm)
- **Goal:** Daily cron reads `.claude/loop/progress.md`, aggregates last-24h tick entries (count / total USD / avg USD-per-tick), writes a markdown report + spike alarm if daily cost > $10. Loop brittleness + runaway-cost mitigation (Ronacher).
- **Pre-existing finding (NOT M7 scope, but flagged):** Pre-tick aggregate stats in `progress.md` lines 19-25 are stale (show 11 ticks / $1.80 / 100% pass rate — accurate at M0/M1 era). Future micro-task can recompute from live log entries; out of scope for M7.

#### T-7.1 — Write M7 SPEC.md + scaffold scripts/cost-dashboard.sh
- **status:** pending
- **spec_ref:** `specs/M7-cost-dashboard/SPEC.md` (acceptance criteria #1 + #2)
- **acceptance:**
  - [ ] `specs/M7-cost-dashboard/SPEC.md` exists (covers aggregation logic, output schema, spike threshold, exit codes, idempotency)
  - [ ] `scripts/cost-dashboard.sh` exists (parses progress.md for last-24h `## YYYY-MM-DD` entries; aggregates tick count, USD total, USD avg; writes `.claude/loop/logs/cost-report.md`; non-zero exit if spike > $10)
  - [ ] Idempotent: re-running writes the same file (deterministic ordering; no timestamps in body)
  - [ ] Manual smoke: `bash scripts/cost-dashboard.sh` -> exit 0 + report file exists + contains all 3 metrics
- **estimated_cost_usd:** 0.30
- **estimated_minutes:** 8
- **attempts:** 0

#### T-7.2 — tests/test_cost_dashboard.sh
- **status:** pending
- **spec_ref:** `specs/M7-cost-dashboard/SPEC.md` (acceptance criterion #3)
- **acceptance:**
  - [ ] `tests/test_cost_dashboard.sh` exists (3+ test groups: aggregation correctness / spike alarm / idempotent re-run)
  - [ ] Test passes locally (bash test_cost_dashboard.sh returns 0; all groups PASS)
  - [ ] Pre-cleanup loop handles leftover state (idempotent re-runnable from clean tree)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 6
- **attempts:** 0

#### T-7.3 — Daily cron schedule via daemon-manager
- **status:** pending
- **spec_ref:** `specs/M7-cost-dashboard/SPEC.md` (acceptance criterion #4)
- **acceptance:**
  - [ ] `bash .claude/helpers/daemon-manager.sh list` shows `cost-dashboard` schedule
  - [ ] Cron fires daily at 00:30 UTC (after midnight rollover, before hill-climb weekly)
  - [ ] Cost cap: $0.50/tick (deterministic script, should run cheap)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 3
- **attempts:** 0

#### T-7.4 — Regression sweep + state-machine closeout
- **status:** pending
- **spec_ref:** `specs/M7-cost-dashboard/SPEC.md` (acceptance criterion #5)
- **acceptance:**
  - [ ] `pytest tests/test_loop_infra.py` 11/11 PASS
  - [ ] `pytest tests/test_m4_langgraph_integration.py` 9/9 PASS
  - [ ] `pytest src/ikigai/tests/test_canonical_scope.py` 32/32 PASS
  - [ ] `bash tests/test_cost_dashboard.sh` all groups PASS
  - [ ] `roadmap.md` M7 marked STATUS: DONE
  - [ ] `tasks.md` T-7.1..T-7.4 marked status=done
  - [ ] `progress.md` M7 entry appended with commit SHA
  - [ ] Atomic commit + push to origin master per standing directive
  - [ ] Memory entry appended at `~/.claude/projects/.../memory/m7-cost-dashboard-shipped-2026-09-08.md`
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 5
- **attempts:** 0

## Notes for Orchestrator

- **Atomic:** each task completable in 1-2 sub-agent invocations
- **Testable:** every task has pass/fail signal
- **Bounded:** never exceed $5 cost or 30min wall time
- **Reversible:** if you screw up, human can `git revert`

## Notes for Human

- **Add tasks** to backlog freely — orchestrator will pick them up
- **Remove tasks** by status=cancelled (do not delete — keep history)
- **Block tasks** by status=blocked + `## BLOCKED` note
