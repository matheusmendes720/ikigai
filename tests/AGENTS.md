# tests/ — Root Test Suite

**Score:** 12 (155 files, 100% code, 1570 module-level symbols, 1435 exports)
**Role:** the repo's pytest suite (1229 test functions). Owns the dual-import bootstrap every test depends on.

## OVERVIEW

One flat milestone suite at the top level (74 Python modules, 5 shell suites) plus 11
subpackages. Naming is `test_m<NNN>_<slug>.py` for milestone work and `test_<feature>.py`
otherwise; 63 modules open with a `"""M<NNN> tests — <what>"""` docstring line naming
their milestone and scope.

## STRUCTURE

```
tests/
├── conftest.py            # repo-root sys.path bootstrap + autouse isolation
├── contracts/             # one file per src/contracts/* model        -> no file (parent covers)
├── gateway/               # MCP stdio transport + fork clients E2E    -> gateway/AGENTS.md
│                          #   clients/ -> gateway/clients/AGENTS.md
├── ikigai/                # agents/v2 dispatcher, security validator
├── integration/           # 3-fork propagation, investigation queue
├── interfaces/            # CLI notify router, TUI operator, skills
├── loop/                  # shell notify-wrap, driven by pytest
├── mcp_server/            # vault_write actor, investigation lifecycle
├── mesh/                  # Phase 3 mesh CLI, adapters, queue        -> mesh/AGENTS.md
├── smoke/                 # 3 shell scripts + Windows .bat twins
├── solverforge_calendar/  # fork MCP server E2E
└── tuiboard/              # fork MCP server E2E
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Import bootstrap | `conftest.py` | repo root on `sys.path`; legacy `ikigai.*` aliases pre-registered in `sys.modules` |
| Windows temp fix | `conftest.py` | `tempfile.tempdir` -> `data/pytest-tmp/`; avoids `PermissionError [WinError 5]` |
| HTTP-daemon isolation | `conftest.py` | autouse `TASKDOG_HTTP_ENABLED=0`; otherwise the live daemon shadows SQLite fixtures |
| Canonical contract tests | `contracts/` | one file per `src/contracts/*` model |
| Fork MCP E2E | `gateway/clients/` | real subprocess + hand-rolled JSON-RPC over stdio |
| Phase 3 mesh CLI | `mesh/` | queue, adapters, review-queue CLI, dep graph |
| Smoke scripts | `smoke/` | each `.sh` has a byte-for-byte Windows `.bat` twin |
| Taskdog bridge battery | `test_mcp_bridge_taskdog_battery.py` | 561 LOC; the largest module |

## CONVENTIONS

- `sys.path` bootstrap lives in `conftest.py`, not per package `__init__.py`: pytest
  resolves the test module's package chain before conftest bodies run.
- Two import identities coexist repo-wide and both must be patched when monkeypatching:
  the dotted `src.*` form and the bare `sys_ikigai.*` / `mesh.*` form. Patching only
  one silently no-ops.
- 111 of 143 Python modules carry `from __future__ import annotations`; the 32 that
  omit it are mostly under `tests/contracts/`.
- Isolation primitives: `tmp_path` (default), `monkeypatch`, `capsys`. Fixed sleeps are
  banned — only `tests/gateway/test_start_gateway.py` and
  `tests/test_paperclip_heartbeat_http.py` still use `time.sleep`.
- Class-based tests are rare: only `test_m147_windows_stdio.py` and
  `test_mcp_bridge_taskdog_battery.py` use `class Test*`; everything else is function-style.
- Subpackages with `__init__.py` (`gateway/`, `gateway/clients/`, `ikigai/agents/`,
  `ikigai/agents/v2/`, `integration/`, `mcp_server/`, `solverforge_calendar/`,
  `tuiboard/`) are importable packages; the rest are rootdir-relative.

## ANTI-PATTERNS

- NEVER let the taskdog HTTP daemon reach a test. `TASKDOG_HTTP_ENABLED=0` is autouse
  repo-wide; removing it turns "expected 3 tasks, got 69" into a failure.
- NEVER write to the real `data/review_queue/`, `data/taskdog/`, or `vault/` from a test.
  Patch `QUEUE_DIR`, `TASKDOG_DB`, `UPI_DB`, and `TASKS_JSONL` to tmp paths.
- NEVER call a real LLM from CI. The judge stubs unless `--use-llm` is passed AND
  `ANTHROPIC_API_KEY` is set; `IKIGAI_FAKE_LLM` short-circuits it.
- NEVER touch the real `reports/baselines/.passphrase`. Use a temp passphrase fixture.
- NEVER add a PAV-math tool to the loop bridge. ADR-013 forbids these 8 names:
  `ikigai_observe_pav_state`, `ikigai_score_vectors`, `ikigai_heuristics`, `ikigai_balance`,
  `ikigai_plan`, `ikigai_reflect`, `ikigai_tag_and_persist`, `ikigai_commit_summary`.
- NEVER swallow `KeyboardInterrupt` or `SystemExit` in a graceful fallback.
- NEVER weaken a drift test to make a change pass. Drift tests are append-only.
- NEVER let a fork module write to `vault/`; `vault_write` is the only writer.
