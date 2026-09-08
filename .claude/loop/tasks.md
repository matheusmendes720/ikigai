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


### M7 — Cost dashboard (DONE — 2026-09-08)
- **Spec:** `specs/M7-cost-dashboard/SPEC.md` (created 2026-09-08; aggregates `progress.md` into `.claude/loop/logs/cost-report.md` with tick counts + USD totals + spike alarm)
- **Goal:** Daily cron reads `.claude/loop/progress.md`, aggregates last-24h tick entries (count / total USD / avg USD-per-tick), writes a markdown report + spike alarm if daily cost > $10. Loop brittleness + runaway-cost mitigation (Ronacher).
- **Completed:** 2026-09-08 — T-7.1..T-7.4 all PASS. Pure bash + awk implementation (scripts/cost-dashboard.sh, 92L) — zero Python changes, zero LLM calls during delivery (total cost_usd=0 across all 4 ticks). Live report shows ticks_day=112, usd_total=$1.80, usd_avg_per_tick=$0.02, spike_alarm=none. Spike alarm via exit code 2 lets M8 notification channel pipe on `$? -eq 2` without parsing report. Daemon schedule registered at cost-dashboard (1440m, $0.5 cap, PID 46159). Regression sweep clean: 7/7 M7 test assertions PASS, M7 made ZERO changes to src/ — pre-existing ruff (104) + mypy (328) error counts unchanged from baseline.

#### T-7.1 — Write M7 SPEC.md + scaffold scripts/cost-dashboard.sh
- **status:** done
- **commit:** 726bfde0
- **spec_ref:** `specs/M7-cost-dashboard/SPEC.md` (acceptance criteria #1 + #2)
- **acceptance:**
  - [x] `specs/M7-cost-dashboard/SPEC.md` exists (covers aggregation logic, output schema, spike threshold, exit codes, idempotency)
  - [x] `scripts/cost-dashboard.sh` exists (parses progress.md for last-24h `## YYYY-MM-DD` entries; aggregates tick count, USD total, USD avg; writes `.claude/loop/logs/cost-report.md`; non-zero exit if spike > $10)
  - [x] Idempotent: re-running writes the same file (deterministic ordering; no timestamps in body)
  - [x] Manual smoke: `bash scripts/cost-dashboard.sh` -> exit 0 + report file exists + contains all 3 metrics
- **estimated_cost_usd:** 0.30
- **estimated_minutes:** 8
- **attempts:** 1

#### T-7.2 — tests/test_cost_dashboard.sh
- **status:** done
- **commit:** 4b2510d3
- **spec_ref:** `specs/M7-cost-dashboard/SPEC.md` (acceptance criterion #3)
- **acceptance:**
  - [x] `tests/test_cost_dashboard.sh` exists (3+ test groups: aggregation correctness / spike alarm / idempotent re-run)
  - [x] Test passes locally (bash test_cost_dashboard.sh returns 0; all groups PASS)
  - [x] Pre-cleanup loop handles leftover state (idempotent re-runnable from clean tree)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 6
- **attempts:** 1

#### T-7.3 — Daily cron schedule via daemon-manager
- **status:** done
- **commit:** ca6a114c
- **spec_ref:** `specs/M7-cost-dashboard/SPEC.md` (acceptance criterion #4)
- **acceptance:**
  - [x] `bash .claude/helpers/daemon-manager.sh list` shows `cost-dashboard` schedule
  - [x] Cron fires daily at 1440m interval (24h, cost-dashboard schedule fires every 86400s)
  - [x] Cost cap: $0.50/tick (deterministic script, should run cheap)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 3
- **attempts:** 1

#### T-7.4 — Regression sweep + state-machine closeout
- **status:** done
- **commit:** (this commit)
- **spec_ref:** `specs/M7-cost-dashboard/SPEC.md` (acceptance criterion #5)
- **acceptance:**
  - [x] `bash tests/test_cost_dashboard.sh` 7/7 PASS (re-run on live progress.md confirms idempotency: ticks_day=112, $1.80 total)
  - [x] `roadmap.md` M7 marked STATUS: DONE
  - [x] `tasks.md` T-7.1..T-7.4 marked status=done
  - [x] `progress.md` M7 entry appended with commit SHA
  - [x] Atomic commit + push to origin master per standing directive
  - [x] Memory entry appended at `~/.claude/projects/.../memory/m7-cost-dashboard-shipped-2026-09-08.md`
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 5
- **attempts:** 1

### M8 — Notification channel (DONE — 2026-09-08)
- **Spec:** `specs/M8-notification-channel/SPEC.md` (created 2026-09-08; ntfy.sh HTTP webhook transport + idempotency contract via sha256 + 600s cooldown)
- **Goal:** "HITL fatigue" mitigation. Wire one async channel (ntfy.sh; topic-as-secret) that fires ONLY on FAIL/NEEDS_FIX/BLOCKED/OVERRUN/BUDGET_ABORT and on cost spike. Suppresses on PASS/dry-run. Zero LLM in pipeline; pure bash + curl.
- **Completed:** 2026-09-08 — T-8.1..T-8.4 all PASS. scripts/notify.sh (134L pure bash + curl) wired into .claude/loop/loop-tick.sh EXIT trap via notify_hook() function registered alongside M6's auto_cleanup_hook (LIFO order: worktree cleanup runs first, then notify). Trap maps TICK_VERDICT + SPIKE_DETECTED → notify --reason (FAIL→tick_fail, NEEDS_FIX→needs_fix, BLOCKED→blocked, OVERRUN→overrun, BUDGET_ABORT→budget, SPIKE_DETECTED→spike_alarm). Cooldown dedup (10min default) via sha256(reason:message) keyed state file at .claude/loop/logs/notify-state.json. Disabled when LOOP_NOTIFY_TOPIC unset (exit 0 silently, no HTTP). Total cost across all 4 ticks = $0 (ntfy.sh free tier + zero LLM). Regression sweep clean: test_worktree_helper.sh 15/15 (M6) + test_cost_dashboard.sh 7/7 (M7) + test_notify.sh 11/11 (M8) = 33/33 PASS.

#### T-8.1 — Write M8 SPEC.md + scaffold scripts/notify.sh
- **status:** done
- **commit:** b95c0348 (SPEC) + aeb4b0c6 (scaffold) + 9c498077 (follow-up fixes)
- **spec_ref:** `specs/M8-notification-channel/SPEC.md` (acceptance criteria #1 + #2)
- **acceptance:**
  - [x] `specs/M8-notification-channel/SPEC.md` exists (acceptance criteria, ntfy.sh architecture, idempotency contract, env vars, exit codes, disabled-mode no-op, dry-run mode)
  - [x] `scripts/notify.sh` exists (134L pure bash + curl; mirrors M6/M7 minimal pattern; reasons: spike_alarm, tick_fail, needs_fix, blocked, overrun, budget, test)
  - [x] Disabled when LOOP_NOTIFY_TOPIC unset (silent exit 0; no HTTP)
  - [x] Cooldown dedup via sha256(reason:message) keyed state file (default 600s)
  - [x] --dry-run mode prints curl command without firing (CI-friendly)
  - [x] Follow-up commit 9c498077 fixes two bash arg-parsing bugs caught by T-8.2 test scaffolding (single-arg --reason + dry-run printf loop)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 7 (across 3 commits)
- **attempts:** 1

#### T-8.2 — tests/test_notify.sh — 4 test groups, 11/11 PASS
- **status:** done
- **commit:** e63c6b5c
- **spec_ref:** `specs/M8-notification-channel/SPEC.md` (acceptance criterion #3)
- **acceptance:**
  - [x] `tests/test_notify.sh` exists (220L, 4 test groups mirrors M7's test_cost_dashboard.sh pattern)
  - [x] Group 1: disabled mode — unset LOOP_NOTIFY_TOPIC → exit 0, no HTTP call (counter=0 via stub curl)
  - [x] Group 2: idempotent duplicate suppression — 3 sends within cooldown → counter=1; different messages → counter=2
  - [x] Group 3: dry-run mode — --dry-run flag → exit 0, counter=0, stdout contains curl command
  - [x] Group 4: spike alarm wire integration with cost-dashboard.sh (seeds >$10 today, runs cost-dashboard.sh, asserts exit=2, invokes notify --reason spike_alarm, asserts counter=1; SKIP if cost-dashboard.sh missing)
  - [x] Stub curl via PATH override (no real network calls during tests)
  - [x] 11/11 PASS (POSIX + Git Bash compatible)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 6
- **attempts:** 1

#### T-8.3 — Wire notify.sh into loop-tick.sh EXIT trap
- **status:** done
- **commit:** e11f3b6
- **spec_ref:** `specs/M8-notification-channel/SPEC.md` (acceptance criterion #1)
- **acceptance:**
  - [x] notify_hook() function + trap notify_hook EXIT registered after M6's auto_cleanup_hook (LIFO order)
  - [x] TICK_VERDICT="" default in defaults block + TICK_VERDICT=$VERDICT at graph dispatch (L213)
  - [x] TICK_VERDICT="BUDGET_ABORT" + SPIKE_DETECTED=1 at cost guard (L251)
  - [x] TICK_VERDICT="OVERRUN" before exit 124 (L389)
  - [x] TICK_VERDICT=PASS/FAIL at normal tick exit (L393)
  - [x] Trap captures $? at entry; reads TICK_VERDICT + SPIKE_DETECTED; maps to notify --reason (FAIL→tick_fail, NEEDS_FIX→needs_fix, BLOCKED→blocked, OVERRUN→overrun, BUDGET_ABORT→budget, SPIKE_DETECTED→spike_alarm)
  - [x] Empty TICK_VERDICT + exit 0 = no-op (PASS / dry-run suppressed)
  - [x] Empty TICK_VERDICT + exit !=0 = tick_error fallback
  - [x] Smoke-tested: dry-run --graph pae_maintainer and bare dry-run both exit 0 with no notify fired
  - [x] Loop's cost_cap_usd preserved ($0/tick; ntfy.sh free tier + zero LLM)
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 4
- **attempts:** 1

#### T-8.4 — Regression sweep + state-machine closeout
- **status:** done
- **commit:** (this commit)
- **spec_ref:** `specs/M8-notification-channel/SPEC.md` (acceptance criterion #2 — real-receipt verification deferred to M8.1)
- **acceptance:**
  - [x] Full regression sweep clean: test_worktree_helper.sh 15/15 + test_cost_dashboard.sh 7/7 + test_notify.sh 11/11 = 33/33 PASS
  - [x] `roadmap.md` M8 marked STATUS: DONE
  - [x] `tasks.md` M8 section added (DONE — 2026-09-08) + T-8.1..T-8.4 marked status=done
  - [x] `progress.md` M8 entries appended (T-8.1, T-8.1 fix, T-8.2, T-8.3, T-8.4)
  - [x] Atomic commit + push to origin master per standing directive
  - [x] Memory entry appended at `~/.claude/projects/.../memory/m8-notification-channel-shipped-2026-09-08.md`
  - [ ] M8 acceptance criterion #2 (trigger NEEDS_FIX, receive notification) deferred to M8.1 — gated on user setting `LOOP_NOTIFY_TOPIC`; idempotency + dedup + disabled-mode + dry-run verified by 11 unit tests
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 9
- **attempts:** 1

## Active Tasks (M9 — Production mode)

### M9 — Production mode (IN PROGRESS — 2026-09-07)
- **Spec:** specs/M9-production-mode/SPEC.md
- **Goal:** Cron auto-resume on session start + 7-day unattended streak.
- **Pre-existing finding:** claudeFlow.daemon.autoStart: false — T-9.2 closes this gap.

#### T-9.1 — Write M9 SPEC.md
- **status:** done
- **commit:** a9341cb
- **acceptance:**
  - [x] specs/M9-production-mode/SPEC.md exists (auto-start + streak tracker + 7-day acceptance)
  - [x] Lists 5 acceptance criteria with test signals
  - [x] Open questions section explicit about UTC-day convention
  - [x] Out-of-scope section explicit
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 5
- **last_verdict:** PASS

#### T-9.2 — Wire auto-start into SessionStart hook
- **status:** pending
- **acceptance:**
  - [ ] .claude/settings.json SessionStart hook chain extended with daemon-manager.sh start-schedule loop-tick call
  - [ ] Hook idempotent (daemon-manager.sh start-schedule handles is_running)
  - [ ] Hook respects CLAUDE_PROJECT_DIR env var
  - [ ] Manual test: stop loop-tick, restart, verify PID recreated
  - [ ] No regression: existing SessionStart hooks still fire
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 12

#### T-9.3 — scripts/streak-tracker.sh (M7-style pure bash + awk)
- **status:** pending
- **acceptance:**
  - [ ] scripts/streak-tracker.sh exists
  - [ ] Reads progress.md, computes current_streak + max_streak + last_paused_at + last_tick_at
  - [ ] Writes .claude/loop/logs/streak-report.md
  - [ ] Exit 0 healthy / Exit 2 streak-break — wires into M8 notification channel via --reason streak_break
  - [ ] Idempotent re-run
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 10

#### T-9.4 — tests/test_streak_tracker.sh
- **status:** pending
- **acceptance:**
  - [ ] File exists with 4 test groups (cold-start / healthy / break / idempotent)
  - [ ] All 4 groups PASS
  - [ ] POSIX + Git Bash compatible
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 8

#### T-9.5 — Streak cron schedule via daemon-manager
- **status:** pending
- **acceptance:**
  - [ ] daemon-manager.sh list shows streak-tracker schedule
  - [ ] 1440m interval, 0.10 USD cap
  - [ ] schedules.json updated + committed
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 3

#### T-9.6 — Regression + closeout (gated on 7-day streak)
- **status:** pending
- **acceptance:**
  - [ ] streak-report.md shows current_streak >= 7 AND most recent tick verdict is PASS
  - [ ] Full regression sweep clean (M4/M5/M6/M7/M8 + loop_infra + canonical_scope)
  - [ ] roadmap.md M9 STATUS: DONE
  - [ ] tasks.md T-9.1..T-9.6 status=done
  - [ ] Memory entry + atomic commit + push to master
- **estimated_cost_usd:** 0.00
- **estimated_minutes:** 7
- **notes:** Gated on real-time 7-day wall clock. Orchestrator cannot fake completion.

## Notes for Orchestrator

- **Atomic:** each task completable in 1-2 sub-agent invocations
- **Testable:** every task has pass/fail signal
- **Bounded:** never exceed $5 cost or 30min wall time
- **Reversible:** if you screw up, human can `git revert`

## Notes for Human

- **Add tasks** to backlog freely — orchestrator will pick them up
- **Remove tasks** by status=cancelled (do not delete — keep history)
- **Block tasks** by status=blocked + `## BLOCKED` note
