# AGENTS.md — `sys_ikigai/propagation`

> Earned its file: score 9/20 — distinct domain (canonical storage layout + append-only mirror).
> Parent: `sys_ikigai/AGENTS.md`. Scope: this directory only.

## OVERVIEW

Storage for plan entities: the canonical markdown database, the SQLite mirror that keeps the
vault queryable, the generic frontmatter codec, and the drift triage report. 5 modules, ~1.1k LOC.

## WHERE TO LOOK

| File | Role |
|------|------|
| `markdown_db.py` | `MarkdownDB` — canonical source of truth for plan entities. Layout under `vault_root/`: `dreams/`, `goals/`, `objectives/`, `projects/`, `tasks/`, `deliverables/`, `routines/`, `habits/`, `ikigai_state/`, `meta/` — one `<slug>.md` per entity. |
| `sqlite_adapter.py` | `SQLiteAdapter` — internal mirror of the vault. **Append-only at the DB level**, enforced by the triggers `plan_entities_no_delete` and `plan_entities_no_update` (`RAISE(ABORT, …)`). API: `upsert`, `get_by_ueid`, `list_by_type`, `list_all`. |
| `frontmatter.py` | Generic codec: `frontmatter_to_dict`, `dict_to_frontmatter`, `serialize_to_markdown`, `parse_from_markdown`, plus `coerce_typed_values`. |
| `triagem.py` | `Triagem` + `DriftEntry` — the drift report (markdown vs mirror). |

## CONVENTIONS (deviations from parent)

- **Two frontmatter codecs coexist on purpose.** `propagation/frontmatter.py` is the generic YAML
  codec; `../vault/frontmatter_to_dict.py` + `../vault/dict_to_frontmatter.py` are the
  record-specific, lossless `IKIGAiRecord` codec. Do not merge them and do not cross-import.
- The SQLite mirror is *derived* state — the markdown vault stays canonical.

## ANTI-PATTERNS

- **Never `DELETE` or `UPDATE` `plan_entities`.** The triggers abort the statement. The one
  allowed `UPDATE` is archival (`archived_at`); every other change belongs in
  `plan_entities_history`.
- Never treat the SQLite mirror as the source of truth — a rebuild from markdown must stay
  possible.
- Do not store raw `pickle` in the mirror; use JSON, as `../adapters/checkpoint_adapter.py` does.

## COMMANDS

```bash
python -m sys_ikigai.cli.app sync index --help     # markdown ⇄ SQLite index surface
python -m sys_ikigai.cli.app sync vault-to-taskdog --help
```
