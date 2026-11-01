# DIGEST — tests/ subtree

## LOCATIONS WRITTEN

| Path | Score | Role |
|------|-------|------|
| `tests/AGENTS.md` | 13 | Subtree root — the repo's entire pytest + shell test surface: session bootstrap, milestone naming, drift guards, hermetic rules |
| `tests/mesh/AGENTS.md` | 8 | Fork-boundary conformance — 184 tests over the fork adapters, review queue, agent propagation and the read-side CLIs |

Scores: `tests/` = file count 52 (>20) + subdirs 9 (>5) + code ratio 88% (>70%) + own conftest + symbol density + reference centrality.
`tests/mesh/` = code ratio 93% + own conftest + symbol density (165 tests) + reference centrality (mesh boundary referenced by 109 non-test files).
Both fall in the 8-15 band and are distinct domains.

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `tests/contracts/` | 7 | `tests/AGENTS.md` WHERE TO LOOK — 44 tests over the 11 Pydantic v2 contract modules |
| `tests/interfaces/` | 6 | notify router (6 tests) + its own conftest |
| `tests/mesh/adapters/` | 5 | `tests/mesh/AGENTS.md` STRUCTURE |
| `tests/gateway/` | 4 | gateway boot + `/health` smoke (1 test) |
| `tests/integration/` | 4 | cross-fork create flow (1 test) |
| `tests/ikigai/security/` | 3 | phase-transition validator (6 tests) |
| `tests/loop/` | 2 | bash notify-wrap smoke + its pytest wrapper |
| `tests/smoke/` | 1 | 3 platform-paired `.sh`/`.bat` vault<->taskdog sync suites |

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **`tests/conftest.py` is the dual-tree identity resolver, not just a `sys.path` bootstrap.** Three import roots are live at the same time: the repo root (prepended by the conftest) plus `src` and `src/ikigai/src` (from `pytest.ini`'s `pythonpath`). Consequence: `from src.contracts.X` and `from contracts.X` are *distinct module objects* with separate globals — monkeypatch both.
2. **The conftest pre-registers 14 legacy `ikigai.*` aliases** in `sys.modules` (`setdefault`) pointing at the canonical `sys_ikigai.*` modules, so `importlib.import_module("ikigai.X")` resolves to the same object. One stale entry in `_ALIAS_MODULES` (a module that no longer exists) raises `ModuleNotFoundError` at conftest import and aborts the whole pytest session.
3. **`pytest.ini` is the effective pytest config, not `pyproject.toml`.** It sets `pythonpath = src src/ikigai/src` and `testpaths = tests`; because the ini file wins, the `unit`/`integration`/`smoke`/`e2e` markers declared in `[tool.pytest.ini_options]` are never registered (and no test uses them).
4. **Temp isolation is forced by the conftest**: `tempfile.tempdir` and `TMPDIR`/`TEMP`/`TMP` point at `data/pytest-tmp/` (gitignored) to dodge the Windows `PermissionError [WinError 5]` on stale pytest temp dirs; `asyncio_mode = "auto"` disables pytest-asyncio collection.
5. **Canonical test scale (verified at `b28b3356`)**: 85 tracked files — 71 Python, 9 shell, 3 batch, 2 markdown — 15 505 lines, 1 467 test functions (742 module-level + 725 inside classes), one flat root suite of 35 Python modules plus 9 sub-suites. The previously published "96 files / 852 test functions" and "155 files / 143 Python / 11 sub-suites" numbers were stale.
6. **Shell suites are standalone, not pytest-collected**: 9 `.sh` + 3 `.bat` under `tests/`, run as `bash tests/<file>.sh` from the repo root, exit code 1 on failure. They copy the production script into a `mktemp -d` sandbox.
7. **The `.claude/loop/mcp_bridge.py` MCP bridge surface is pinned at exactly 36 wrapped tools**; the `== 36` guard is copy-pasted into `test_m142`, `test_m144`, `test_m145` and `test_m148`, and the 8 ADR-013 PAV-math tool names are pinned as forbidden.
8. **`tests/` has no `__init__.py`**; `tests/gateway/` and `tests/integration/` do.
9. **`tests/conftest.py` is the only place `data/` writes are neutralised for the whole suite** via the autouse `TASKDOG_HTTP_ENABLED=0` fixture; `tests/mesh/conftest.py` adds the per-test `src.mesh.queue.QUEUE_DIR` redirect.

## VERIFICATION

- `tests/AGENTS.md` — 76 lines (30-80 band), sections OVERVIEW / STRUCTURE / WHERE TO LOOK / CONVENTIONS / ANTI-PATTERNS / COMMANDS.
- `tests/mesh/AGENTS.md` — 71 lines (30-80 band), same section set.
- No content line is shared between the parent and the child (only headings and table chrome).
- Every path named in both files was checked against the working tree.
