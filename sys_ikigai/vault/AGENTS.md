# AGENTS.md — `sys_ikigai/vault`

> Earned its file: score 11/20 — distinct domain (the only sanctioned `vault/` write path).
> Parent: `sys_ikigai/AGENTS.md`. Scope: this directory only.

## OVERVIEW

Markdown source-of-truth primitives: the single write path, its read mirror, the file lock, the
lossless frontmatter codec, and the vault↔taskdog sync engine. 10 modules, ~1.8k LOC.

## WHERE TO LOOK

| File | Role |
|------|------|
| `vault_write.py` | The only writer. Rejects absolute paths, paths resolving outside `vault_root`, and empty body+frontmatter. Writes a tmp file in the same dir, then `os.replace()`. |
| `vault_read.py` | Read-only mirror of the same security model, shared reader lock. Highest-centrality symbol in the repo (147 refs). |
| `lock.py` | `VaultLock` — `msvcrt` on Windows, `fcntl` on POSIX; releases on exception (context-manager contract). |
| `frontmatter_to_dict.py` / `dict_to_frontmatter.py` | Lossless `IKIGAiRecord` ⇄ frontmatter codec: keeps `null` keys, tz-aware ISO datetimes, extra fields and the `custom` dict. |
| `frontmatter_compat.py` | Shim for `frontmatter` 3.x, which dropped `Post`/`loads`/`dumps`. |
| `task_io.py` | `data/tasks.jsonl` helpers. Lives inside `vault/` **on purpose** — it sits in the vault allowlist perimeter so file I/O does not trip the vault-write invariant scanner. `_write_tasks_to_data` now delegates to `CliAdapter.apply_change`. |
| `sync.py` | Sync engine: unidirectional vault→taskdog (D1), incremental diff against `data/sync-state.json`, per-action try/except isolation, atomic state writes. `TaskRecord` here is the vault-extraction shape, **not** `contracts.Task`. |
| `sync_cli.py` | argparse operator surface: `sync`, `reverse`, `status`, `list`, `validate`. |

## CONVENTIONS (deviations from parent)

- Two frontmatter codecs coexist on purpose: `vault/frontmatter_*.py` is record-specific and
  lossless; `propagation/frontmatter.py` is the generic YAML codec. Do not merge or cross-import.
- `sync.py` writes its state atomically (`.tmp` + rename), never in place.

## ANTI-PATTERNS

- **Never call `vault_write` directly.** Every caller must use the wrapper in
  `../security/vault_write_wrapper.py`; a direct call is a drift-invariant failure.
- **`sync_cli.py` `validate` and `list` are read-only** — they must not push, save state, or
  enqueue anything.
- **Do not add a second writer to `vault/`.** `vault_write` is the only sanctioned write path.
- Do not hand-edit `data/sync-state.json` — the engine owns that file's shape.

## COMMANDS

```bash
python -m sys_ikigai.vault.sync_cli status --json
python -m sys_ikigai.vault.sync_cli validate --json
python -m sys_ikigai.vault.sync_cli sync --dry-run
```
