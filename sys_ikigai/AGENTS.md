# sys_ikigai

Bare-namespace kernel package: entities, gateway, vault, security, propagation,
state machines, adapters, plus the legacy `types`/`enums`/`exceptions`/
`constants` modules. Earns its file: distinct domain (kernel layer), complexity
score 10. Imported as `sys_ikigai.X`, never `src.sys_ikigai.X`.

## OVERVIEW
Kernel layer: the entities, the MCP gateway, the vault writer, the safety
primitives and the legacy primitives the rest of the repo still imports.

## STRUCTURE
```
sys_ikigai/
├── vault/            sole vault writer + sync engine
├── security/         kill switch + vault_write wrapper
├── gateway/          MCP gateway (HTTP+SSE front, mesh adapters back)
├── entities/         legacy entity models + plan/ contract shims
├── propagation/      markdown DB, SQLite mirror, triagem
├── state_machines/   8 entity state-machine factories
├── adapters/         drift / state-reducer / sqlite bridge
├── cli/              standalone `ikigai` Typer app
└── types.py enums.py exceptions.py constants.py   legacy primitives
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Write a vault markdown file | `vault/vault_write.py` | the only writer (ADR-012) |
| Read a vault file | `vault/vault_read.py` | read-only twin of vault_write |
| Enforce safety on writes | `security/vault_write_wrapper.py` | every write traverses it |
| Serve MCP over HTTP/SSE | `gateway/gateway.py` | stdlib only, no auth |
| Register a data-mesh adapter | `gateway/downstream.py` | `CliAdapter` + `TaskdogAdapter` (ADR-037) |
| Persist plan entities | `propagation/markdown_db.py` | canonical markdown store |
| Entity identity | `entities/ueid.py` | delegates to `src.contracts.common` |
| Legacy identifier | `types.py` | 5-part UEID — not for new code |

## CONVENTIONS
- Two model families coexist. `src/contracts/*` is canonical; the
  `sys_ikigai/entities/*` family is the legacy one — `PlanEntity` is
  deliberately mutable, assignment-validated, `extra="allow"`.
- `entities/plan/*.py` are one-line aliases to `src.contracts`
  (`Tarefa` -> `Task`, `Projeto` -> `Project`). New code imports the canonical
  contract directly.
- `entities/ueid.py` imports `_UEID_PATTERN` from `src.contracts.common`
  (ADR-033, single source of truth) and still accepts legacy 5-part fixtures.
- Module docstrings carry a task/ADR identifier (`M72`, `B3.4`, `W5.3`,
  `ADR-029`). Keep that convention when editing.
- Persistence is append-only or atomic: temp file in the same directory ->
  `fsync` -> `os.replace`.

## ANTI-PATTERNS
- Do not define new shared models here; they belong in `src/contracts/`.
- Do not use `sys_ikigai.types.UEID` (legacy 5-part) in new code, and do not
  pass IDs between the two model families without validating them.
- `sys_ikigai/cli/app.py` is a standalone legacy Typer app whose vector /
  regime / phase commands are archived stubs raising `NotImplementedError` —
  algorithm math lives in the canonical algorithm packages.
- `propagation/markdown_db.py::MarkdownDB.read` raises `ImportError` — the plan shims
  export only the short names (`Dream`, `Task`, ...), not the `*Entity` ones. Use
  `PlanEntity`; the full entity list is in `entities/AGENTS.md`.
- `state_machines/_sm_base.py` must stay free of sibling imports — that is
  what breaks the state-machine import cycle.
- `gateway/adapters/` is mostly duplicate stubs; only `taskdog_adapter.py`
  delegates to a real mesh adapter.
- `propagation` writes a generated `triagem.md`; the next drift scan
  overwrites it — never hand-edit it.

## COMMANDS
```bash
python -m sys_ikigai.vault.sync_cli status
python -m sys_ikigai.gateway.start_gateway        # see gateway/AGENTS.md
python -m pytest tests/ -v
```
