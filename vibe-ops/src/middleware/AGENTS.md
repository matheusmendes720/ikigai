# src/middleware — vault↔code synchronization

## OVERVIEW
Sync layer between the Obsidian vault and the SQLite mesh — append-only by contract.

Three engines that move Obsidian frontmatter into SQLite and back. No `__init__.py` here
(imported as top-level `middleware.*`).

## WHERE TO LOOK
| Module | Class | Scope |
|--------|-------|-------|
| `bidirectional_sync.py` (573 LOC) | `BidirectionalSync` | vault→SQLite ingest, computed-field synthesis, severity inference, conflict table, frontmatter merge, advisory locking |
| `period_sync.py` (278 LOC) | `PeriodReportSync` | period reports only (ADR-006), multi-pass orphan recovery |
| `sync_engine.py` (161 LOC) | `SyncEngine` | generic frontmatter↔`planning_entities` + Taskwarrior bridge |

## CONVENTIONS
- **Append-only**: never deletes. Conflicts are emitted to `.sync-conflicts.md`.
- **Conflict policy is per-layer**: the generic sync is vault-wins for manual fields
  (`MANUAL_FIELD_PREFIXES`: `xp_`, `mastery_`, …) and code-wins for computed fields
  (`COMPUTED_FIELD_NAMES`); period reports are vault-wins for **every** field.
- **Manual fields are never overwritten** by computed values.
- **Idempotency**: `SyncEngine.compute_upstream_id()` = sha256 of canonical JSON, 12 chars;
  period reports use a 16-char `vault_hash` over the parsed payload.
- **Natural key differs**: period reports key on `(sonho_id, period, date_start)`, not
  `upstream_id`.
- **Advisory locking** guards concurrent writers in `bidirectional_sync.py`.
- Default scanned vault folders: `2_projeto`, `5_atomicas`, `3_indice`, `4_leitura`.

## ANTI-PATTERNS
- Never `DELETE` rows here — this layer is append-only by contract (sync, not CRUD).
- Never let a computed field overwrite a manual one.
- `period_sync.py` embeds a fallback copy of `migrations/004_period_reports.sql`; the file on
  disk is the source of truth — change both or neither.
- Do not import `middleware.*` from the operational CLI package; use the subprocess bridges
  `src/cli/period_sync_cli.py` / `src/scripts/vault_sync.py`.
- `bidirectional_sync.py` is the largest module in the tree (17 methods, one class) — split
  it only as a deliberate refactor, not opportunistically.
