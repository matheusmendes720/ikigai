# DIGEST — interfaces/ + sys_ikigai/ subtree

## LOCATIONS WRITTEN

| Path | Score | Role |
|------|-------|------|
| `interfaces/cli/AGENTS.md` | 8 | Typer consumer CLI over `data/`; 21 commands |
| `sys_ikigai/AGENTS.md` | 14 | Bare-namespace kernel: entities, gateway, vault, security |
| `sys_ikigai/entities/AGENTS.md` | 14 | Legacy entity family (20 exports) + `plan/` shims |
| `sys_ikigai/gateway/AGENTS.md` | 9 | Local stdlib JSON-RPC gateway (HTTP+SSE), not MCP |
| `sys_ikigai/security/AGENTS.md` | 8 | Kill switch (ADR-029), `vault_write` wrapper, PAE validator |
| `sys_ikigai/vault/AGENTS.md` | 9 | Sole vault writer + read twin + `VaultLock` + sync engine |

Scores: `interfaces/cli/` (12 files, 66.7% code, 0 subdirs, 1 export) = own config + module boundary + symbols 66 + refs 112/37 = **8**.
`sys_ikigai/` (82 files, 8 subdirs, 92.7% code, no own config, 0 exports) = files + subdirs + code + module boundary + symbols 362 + refs 546/113 = **14**.
`sys_ikigai/entities/` (23 files, 1 subdir, 95.7% code, no own config, 20 exports) = files + code + module boundary + symbols 47 + exports + refs 53/26 = **14**.
`sys_ikigai/gateway/` (14 files, 1 subdir, 92.9% code, 6 exports) = code + module boundary + symbols 72 + refs 24/9 = **9**.
`sys_ikigai/security/` (6 files, 0 subdirs, 66.7% code, own config, 0 exports) = own config + module boundary + symbols 34 + refs 22/11 = **8**.
`sys_ikigai/vault/` (11 files, 0 subdirs, 90.9% code, 0 exports) = code + module boundary + symbols 56 + refs 66/30 = **9**.
Weights: files 3 (>20), subdirs 2 (>5), code 2 (>70%), own config 1, module boundary 2, symbols 2 (>30), exports 2 (>10), refs 3 (>20). Module boundary = package `__init__.py`; refs = reference sites to the dotted import path in tracked files outside the dir (files in parens); symbols = functions+classes; exports = `__all__` size.

## LOCATIONS CONSIDERED AND SKIPPED (covered by the parent file)

| Path | Score | Covered by |
|------|-------|-------------|
| `interfaces/` | 5 | Root `AGENTS.md` STRUCTURE (`interfaces/ cli (Typer)` — the only published consumer surface) |
| `sys_ikigai/adapters/` | 4 | `sys_ikigai/AGENTS.md` STRUCTURE — drift detector, SQLite bridge, state reducer |
| `sys_ikigai/state_machines/` | 6 | `sys_ikigai/AGENTS.md` STRUCTURE — 8 factories + `_sm_base` + `_registry`; 16 `__all__` names |
| `sys_ikigai/propagation/` | 6 | `sys_ikigai/AGENTS.md` STRUCTURE — markdown DB, SQLite mirror, triagem, frontmatter |
| `sys_ikigai/cli/` | 4 | `sys_ikigai/AGENTS.md` STRUCTURE — one legacy standalone Typer app |
| `sys_ikigai/entities/plan/` | 4 | `sys_ikigai/entities/AGENTS.md` WHERE TO LOOK — 6 one-line shims onto `src/contracts` |
| `sys_ikigai/gateway/adapters/` | 4 | `sys_ikigai/gateway/AGENTS.md` WHERE TO LOOK — 4 adapter modules, 3 stubs |

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **The published client surface is one Typer app with 21 commands.** `interfaces/cli/read_tasks.py` has 8 (`list`, `done`, `stats`, `mesh-show`, `task-add`, `plan-add`, `plan-list`, `deep-agent-tasks`); the `server` sub-app (`interfaces/cli/__init__.py:42`) adds 5; the `kill-switch` sub-app (`interfaces/cli/read_tasks.py:230`) adds 5; the standalone `interfaces/cli/notify_cli.py` adds 3.
2. **`sys_ikigai/gateway` is a local JSON-RPC bridge, not the MCP transport.** `sys_ikigai/gateway/gateway.py` (361 lines) serves `POST /call`, `GET /health`, `GET /events` (SSE) on `GatewayConfig` default `127.0.0.1:8765`, stdlib only, no auth. `sys_ikigai/gateway/downstream.py::register_default_adapters` registers 2 adapters; only `sys_ikigai/gateway/adapters/taskdog_adapter.py` (123 lines) is real — it delegates to `src.mesh.adapters.taskdog.TaskdogAdapter` for `taskdog_list_tasks` and `taskdog_create_task`; the other 3 modules there are 12-line stubs. The published MCP surface remains `src/transport/mcp_server.py`.
3. **`sys_ikigai/vault` is the only write path and `sys_ikigai/security` its only enforcement layer.** `sys_ikigai/vault/vault_write.py` (168 lines) is the sole writer, `sys_ikigai/vault/vault_read.py` (70) its twin, `sys_ikigai/vault/lock.py` gives `VaultLock`; `sys_ikigai/security/vault_write_wrapper.py` (474 lines) exposes `make_wrapped_vault_write` and `install_wrapper` and loads the 5 tuning keys of `sys_ikigai/security/algorithm_constants.json`. The drift net pins both: `src/ikigai/tests/test_drift_invariants.py:133` (wrapper loads that JSON) and `:215` (canonical API + `LEGAL_CALLERS`); both package `__init__.py` files are doc-only (0 exports).
4. **Only the legacy model family lives in `sys_ikigai`; the canonical one is `src/contracts`.** `sys_ikigai/entities/__init__.py` exports 20 names in `__all__` (short aliases such as `Task`, `Project`, `Goal`); `sys_ikigai/entities/plan/*.py` (7 files, 0 symbols) are one-line shims onto `src/contracts`. `sys_ikigai/entities/ueid.py` imports `_UEID_PATTERN` from `src.contracts.common` while `sys_ikigai/types.py` keeps a legacy 5-part `UEID`; 22 tracked `.py` files outside `sys_ikigai/entities/` import the legacy family.
5. **The purged PC-only surfaces are absent from the tracked tree but gitignored leftovers survive on disk.** At HEAD `8c983626`, `git ls-files` returns nothing for `interfaces/tui`, `src/tuiboard`, `sys_ikigai/gateway/stdio_adapter.py`, `sys_ikigai/gateway/stdio_server_base.py`, `sys_ikigai/gateway/clients/` or `.claude/loop/mcp_bridge.py`; `git check-ignore -v` shows the on-disk copies are ignored (`.gitignore:591 /interfaces/tui/`). `src/ikigai/tests/test_canonical_scope.py:46-49` keeps `src/tuiboard` and `interfaces/tui` in `RETIRED_PATHS`; its grep at line 119 scans `src/ tests/ sys_ikigai/ interfaces/`.

## VERIFICATION

- `git ls-files interfaces/` → 12 files, all under `interfaces/cli/`; `git ls-files sys_ikigai/` → 82 files, 8 subdirs; the purged paths are untracked; `git ls-files --others --exclude-standard` → no untracked non-ignored file under either dir.
- Symbols/exports/refs from an AST pass over the tracked `.py` files, the package `__init__.py` (`__all__` when present) and a text scan for the dotted import path; command names from the `@…command` decorators.
- `sys_ikigai/security/algorithm_constants.json` → 5 keys; its AGENTS.md says 494 lines for `kill_switch.py`, the live file is 495.
- Every path named above was checked against the live tree.
