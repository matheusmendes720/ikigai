# sys_ikigai/vault

Vault access layer: the only writer, its read twin, locking, frontmatter
helpers, and the vault->fork sync engine. Earns its file: distinct domain
(sole vault writer), complexity score 11, 34 importing files.

## OVERVIEW
Markdown source of truth. `vault_write` is the single write path, `vault_read`
its read-only twin, `sync.py` the diff engine that pushes vault tasks to a
fork.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Write a vault note | `vault_write.py` | only writer; audit log + sha256 |
| Read a vault note | `vault_read.py` | same traversal guard + lock |
| Cross-process locking | `lock.py` | `msvcrt.locking` / `fcntl.flock` |
| YAML frontmatter | `frontmatter_compat.py` | PyYAML-based shim |
| dict <-> frontmatter | `dict_to_frontmatter.py`, `frontmatter_to_dict.py` | re-exported by `src/ikigai/src/strategics/loader.py` |
| Vault -> taskdog sync | `sync.py` | incremental diff vs `data/sync-state.json` |
| Sync CLI | `sync_cli.py` | `sync`, `reverse`, `status`, `list`, `validate` |
| Mesh task slice IO | `task_io.py` | thin shim over `CliAdapter.apply_change` |

## CONVENTIONS
- Atomic writes: `tempfile.mkstemp` in the target directory -> write ->
  `flush` -> `os.fsync` -> `os.replace`. `Path.rename()` is avoided on
  purpose: on Windows it raises `FileExistsError` when the target exists.
- `VaultLock` releases on both the normal path and exceptions.
- `vault_write` serializes frontmatter by hand with `yaml.safe_dump`
  (`sort_keys=False`, block style). The upstream `frontmatter` package no
  longer ships `loads`/`dumps`/`Post`.
- `sync.py` diffs incrementally against `data/sync-state.json` and isolates
  each per-task push in its own try/except, so one bad task does not abort the
  run.
- The sync direction is one-way (vault -> fork); `reverse` is the explicit
  opposite command.

## ANTI-PATTERNS
- `vault_write` is the ONLY vault writer. Everything else (deep agent, forks,
  CLI) goes through it, and through `security/vault_write_wrapper` for
  enforcement.
- `vault_write` rejects absolute paths, paths resolving outside `vault_root`,
  an empty body AND empty frontmatter, and any `actor` outside
  `{"user", "agent", "system"}`.
- An audit-log write failure must not fail the write — the file is already on
  disk. `vault_write.py` swallows that exception deliberately.
- Never `import frontmatter` for `loads`/`dumps`/`Post`; use
  `frontmatter_compat` or `yaml.safe_dump`.
- `TaskRecord` in `sync.py` is deprecated and warns on construction; new
  plan-output code uses `contracts.Task`.
- `task_io._write_tasks_to_data` must not grow a parallel `open("a")` writer —
  it delegates to `CliAdapter.apply_change`, which owns the schema and lock.
- `sync_cli --dry-run` must not push to taskdog or save state; `reverse
  --dry-run` must not enqueue a `TaskChange` or save state.
- Module docstrings still say `ikigai.vault.sync_cli` — the real package path
  is `sys_ikigai.vault.sync_cli`.

## COMMANDS
```bash
python -m sys_ikigai.vault.sync_cli sync   [--dry-run] [--human|--json]
python -m sys_ikigai.vault.sync_cli reverse [--dry-run] [--human|--json]
python -m sys_ikigai.vault.sync_cli status | list | validate
```
