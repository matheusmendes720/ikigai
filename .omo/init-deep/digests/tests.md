# DIGEST — subtree `tests/`

Scope owner: writer node for `tests/`. Input: chunk reports `c14.md`, `c15.md`, `c16.md`, all spot-checked against the real tree.

## LOCATIONS WRITTEN

| Path | Score | Role |
|------|-------|------|
| `tests/AGENTS.md` | 15 | Suite root: session bootstrap (`tests/conftest.py`), milestone naming, hermetic-fixture rules, shell-suite mechanics, drift-guard map. 63 lines. |
| `tests/mesh/AGENTS.md` | 10 | Phase 3 mesh conformance: 3 fork adapters, review queue, agent consumer/propagator, read-side CLIs, dual-module patching rule. 67 lines. |
| `tests/gateway/clients/AGENTS.md` | 9 | Fork MCP E2E: real subprocess + hand-rolled `Content-Length` JSON-RPC against `solverforge_calendar` / `tuiboard` (7 tools). 36 lines. |

### Scoring detail (matrix applied per directory)

| Directory | Files | Subdirs | Code% | Own cfg | `__init__` | Syms | Exports | Refs | Total | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `tests` | 79 | 11 | 94% | yes | no | 978 | >10 | 155 (conftest inherited) | **15** | create — distinct domain |
| `tests/mesh` | 14 | 1 | 100% | yes | no | 186 | 186 | 29 (files touching `src.mesh`) | **10** | create — distinct domain |
| `tests/gateway/clients` | 12 | 0 | 100% | yes | yes | 37 | 37 | 8 (helper importers) | **9** | create — distinct domain |
| `tests/mesh/adapters` | 4 | 0 | 100% | no | no | 32 | 32 | 14 | 6 | skip (parent covers) |
| `tests/contracts` | 11 | 0 | 100% | no | no | 45 | 45 | 0 | 6 | skip (parent covers) |
| `tests/interfaces` | 4 | 0 | 100% | yes | no | 31 | 31 | 0 | 7 | skip (parent covers) |
| `tests/integration` | 3 | 0 | 100% | no | yes | 10 | 10 | 0 | 4 | skip |
| `tests/smoke` | 6 | 0 | 0% | no | no | 0 | 0 | 0 | 1 | skip (shell/batch pairs, described in parent) |
| `tests/gateway` | 3 | 0 | 100% | no | yes | 6 | 6 | 0 | 4 | skip |
| `tests/ikigai` | 1 | 0 | 100% | yes | no | 4 | 4 | 0 | 3 | skip |
| `tests/ikigai/agents/v2` | 3 | 0 | 100% | yes | yes | 19 | 19 | 0 | 6 | skip — also depth 4 > limit |
| `tests/ikigai/security` | 1 | 0 | 100% | no | no | 13 | 13 | 0 | 2 | skip |
| `tests/loop` | 2 | 0 | 50% | no | no | 8 | 8 | 0 | 2 | skip |
| `tests/mcp_server` | 3 | 0 | 100% | no | yes | 14 | 14 | 0 | 4 | skip |
| `tests/solverforge_calendar` | 4 | 0 | 100% | yes | yes | 13 | 13 | 0 | 6 | skip |
| `tests/tuiboard` | 4 | 0 | 100% | no | yes | 13 | 13 | 0 | 4 | skip |

All 16 directories were scored; nothing below the depth limit was left unscored.

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **`tests/` is the entire test surface.** 155 tracked files (143 `.py`, 12 shell/batch), ~24k LOC, 11 sub-suites, ~1,100 test functions. Entry point for the suite: `pytest tests/ -v`.
2. **`tests/conftest.py` is the dual-tree identity resolver.** It puts the repo root on `sys.path` (which resolves BOTH `from src.contracts.X` via `<repo>/src/` and `from sys_ikigai.X` via `<repo>/sys_ikigai/`), then pre-registers legacy `ikigai.*` aliases in `sys.modules` pointing at the `sys_ikigai.*` objects so the W4.7/W6.X drift guards see one module identity. It also redirects `tempfile.tempdir` + `TMPDIR/TEMP/TMP` to `data/pytest-tmp/` (Windows stale-lock workaround), sets `TASKDOG_HTTP_ENABLED=0` autouse, and forces `asyncio_mode=auto`.
3. **`pytest.ini` supplies the other half of the path story:** `pythonpath = src src/ikigai/src`, `testpaths = tests`. Because both the repo root and `src/` end up on `sys.path`, `src.mesh.X` and `mesh.X` are two distinct module objects with separate globals — monkeypatching in tests must patch BOTH.
4. **Shell/batch suites are NOT pytest-collected.** 12 non-Python files: `tests/test_dispatch.sh`, `test_cost_dashboard.sh`, `test_notify.sh`, `test_streak_tracker.sh`, `test_worktree_helper.sh`, `tests/loop/test_notify_wrap.sh`, and 6 in `tests/smoke/` (3 `.sh` / `.bat` pairs). Each is `set -euo pipefail`, sandboxed in `mktemp -d`, and exits 1 on failure.
5. **Milestone naming dominates the root suite:** 34 `test_m<NNN>_<topic>.py` files (M4, M5, M117–M148, M151, M158) where `NNN` is the milestone/spec id, not the module under test. New features normally add a new `test_mNNN_*` file.
6. **The three MCP-bridge test families** (`test_m142`–`test_m148`, ~2.2k LOC) pin one module, `.claude/loop/mcp_bridge.py`: exactly 36 wrappers, 8 read-only, 6 write-side, OTel span prefix `loop.mcp.`, and `_call()` raising `RuntimeError` when `_server is None`.
7. **Drift guards inside `tests/` mirror the `src/ikigai` drift net** (ADR-012 vault_write as sole writer, ADR-014/033 UEID 4-part single source) and are append-only: `test_ueid_regex_single_source.py`, `test_tasks_jsonl_single_writer_path.py`, `tests/gateway/clients/test_vault_write_conformance.py`, `tests/mesh/test_review_queue_autoisolate.py`.
8. **Real-LLM and optional-dependency tests skip rather than fail** (22 files call `pytest.skip`): keys are `ANTHROPIC_API_KEY`, `CLAUDE_API_KEY` (hermes proxy `sk-test-*`), `MINIMAX_API_KEY`, `IKIGAI_FAKE_LLM`; CI never pays for a real Anthropic call.
9. **Duplication worth knowing before editing:** 53 of 143 Python test files still carry their own `sys.path.insert` preamble (31 with `# noqa: E402`) and spell `REPO_ROOT` 14 different ways. The conftest already does this centrally — new files should not add another copy.

## VERIFICATION

- All three files exist on disk and are within the 30-80 line band (63 / 67 / 36).
- No file under `tests/` had a pre-existing `AGENTS.md`; all three were created with `Write`.
- Nothing outside `tests/` was written except this digest file.
