# AGENTS.md — `sys_ikigai`

> Earned its file: score 13/20 — distinct domain (the bare-namespace kernel package).
> Parent: repo-root `AGENTS.md`. Scope: this subtree only.

## OVERVIEW

Kernel package of the Life OS: entities, vault primitives, propagation, security enforcement,
state machines, gateway, CLI. Imports are **bare namespace** (`from sys_ikigai.vault.vault_write
import vault_write`), never dotted-prefix; vendored into `src/ikigai` from the repo root.

## STRUCTURE

```
sys_ikigai/
├── entities/       # Pydantic v2 models (PlanEntity, IKIGAiRecord, vector/regime/skill)
│   └── plan/       # 6 one-line shims re-exporting src.contracts — deprecated
├── vault/          # vault_write/vault_read/lock/frontmatter codec + sync engine
├── security/       # kill switch + the single write-enforcement wrapper (ADR-029)
├── propagation/    # canonical MarkdownDB + append-only SQLite mirror + triagem
├── gateway/        # stdlib HTTP+SSE MCP gateway, stdio adapters, fork clients
│   ├── clients/    # 4 fork client factories (taskdog, calendar, tuiboard, native CLI)
│   └── adapters/   # 9 of 10 files are dead stubs (see ANTI-PATTERNS)
├── state_machines/ # 8 entity FSMs over `_sm_base` primitives
├── adapters/       # Layer-2 bridges (checkpoint, drift detector, state reducer)
├── cli/            # Typer app (version/health, vector, plan, regime, phase, sync)
├── constants.py    # 22 frozen NSM constants (SPEC §11) — comments in Portuguese
├── enums.py        # 8 enums (EntityType, VectorType, RegimeType, Phase, …)
├── exceptions.py   # 17 error types, all under IKIGAiError
└── types.py        # LEGACY 5-part UEID + ScoreValue
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Write to `vault/` | `vault/vault_write.py` | must be wrapped — see `security/` |
| Read `vault/` | `vault/vault_read.py` | 147 repo-wide refs — highest-centrality symbol |
| Entity models | `entities/base.py`, `entities/ikigai_record.py` | polymorphic roots: `extra="allow"`, `frozen=False` |
| Storage layout + mirror | `propagation/markdown_db.py`, `propagation/sqlite_adapter.py` | `vault_root/{dreams,goals,tasks,…}/<slug>.md`; mirror is append-only by DB trigger |
| Phase transitions | `state_machines/_sm_base.py` + `*_sm.py` | `_sm_base` must not import siblings |
| Kill switch | `security/kill_switch.py` | `IKIGAI_KILL_SWITCH=1` > vault file > data file |
| MCP gateway | `gateway/gateway.py` | `POST /call`, `GET /health`, `GET /events` (SSE) |
| Fork connectivity | `gateway/clients/README.md` | 4 forks over stdio JSON-RPC 2.0 |
| Operator CLI | `cli/app.py`, `vault/sync_cli.py` | Typer vs argparse |

## CONVENTIONS (deviations from repo defaults)

- **Sync-only MCP handlers.** `vault_write`/`vault_read` return dicts; they are never coroutines.
- **Stdlib-only gateway.** `http.server`/`socketserver`/`threading`/`queue`; JSON-RPC 2.0 with
  `Content-Length` framing is hand-rolled in `gateway/stdio_server_base.py` — no MCP SDK.
- **Two Pydantic modes.** Audit/immutable records use `frozen=True, extra="forbid"`; only the
  polymorphic roots (`PlanEntity`, `IKIGAiRecord`, `ProfileSnapshot`, `RegimeOverride`) use `extra="allow"`.
- **`__init__.py` is a re-export façade only**, with explicit `__all__` (44 modules).
- **Atomic write = tmp file in the same dir + `os.replace()`** — never `Path.rename()`, which
  raises `FileExistsError` on Windows.
- **Windows-first portability**: `msvcrt`/`fcntl` dual lock (`vault/lock.py`); `read1` for stderr
  on Windows pipes; WAL journal mode; `:memory:` uses one shared connection.
- **Docstrings are the spec** — they cite ADR-012/013/014/020/025/026/029/033 and SPEC
  D6/D8/D12–D14 and are often more load-bearing than the code.
- **`constants.py` comments are in Portuguese**; the rest of the subtree is English.

## ANTI-PATTERNS

- **NEVER write to `vault/` except through `vault_write`** (ADR-012), and every `vault_write` call
  must go through the `security/vault_write_wrapper.py` wrapper (ADR-029 §S2/R2). Drift invariant
  (e) enforces this in `agents/v2/*.py`.
- **Never extend the deprecation shims**: `entities/plan/*`, `adapters/sqlite_bridge.py`,
  `gateway/downstream.py`, and the 5-part `types.UEID` (canonical 4-part UEID:
  `src/contracts/common.py`).
- **Never call `pickle.loads`** — `adapters/checkpoint_adapter.py` uses `JsonPlusSerializer`; the
  `state_blob` payload must start with `{`/`[`.
- **`gateway/adapters/` is mostly dead.** 9 of 10 files are ~12-line stubs shadowing real code in
  `gateway/clients/` and `src/mesh/adapters/`; the hyphenated `solverforge-calendar*.py` files are
  **not importable** (live: `solverforge_calendar_adapter.py`, `taskdog_adapter.py`).
- **`_sm_base.py` must not import sibling modules**; `state_machines/__init__.py` breaks the cycle
  with deferred imports (`__init__ → _registry → *_sm → __init__`).
- **Do not write to `vault/`, `strategics/`, `archive/`, or `data/` from here** — read only.
