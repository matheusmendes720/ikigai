# 07 — Canvas: Sync Architecture (Vault ↔ SQLite ↔ Taskwarrior)

> **Categoria:** INDEX (Layer 2 — Architecture Canvas)
> **Anchor canônico:** `vibe-ops/src/middleware/sync_engine.py` + `data/review_queue/`
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Resumo

A camada de **sync** mantém **3 storages sincronizados**: vault markdown (Obsidian) ↔ SQLite (planning_entities, review_queue) ↔ Taskwarrior (TW). Implementa o **padrão de idempotency-via-upstream_id** (SHA256 de canonical JSON) que permite replay seguro. Review queue (`data/review_queue/`) é **append-only** — mudanças são eventos imutáveis com status transitions.

## §2 — Inventário

| Arquivo | Função | LOC | Notas |
|:--------|:-------|:---:|:------|
| `vibe-ops/src/middleware/sync_engine.py` | `SyncEngine(vault_path, db_path, tw_path)` | ~400 | Bidirecional sync |
| `data/review_queue/*.json` | Append-only queue | runtime | Atomic temp+rename |
| `src/mesh/queue.py` | Queue primitives | ~120 | reusado |
| `src/contracts/task_change.py` | TaskChange, PropagationEvent | ~150 | reusado |
| `src/ikigai/tools/vault_taskdog_sync.py` | Sync vault → taskdog | ~200 | Subprocess wrapper |

## §3 — SyncEngine class

```python
class SyncEngine:
    def __init__(self, vault_path, db_path, tw_path, tw_client=None):
        self.vault = Path(vault_path)        # Obsidian markdown root
        self.db = Path(db_path)              # SQLite
        self.tw = Path(tw_path)              # Taskwarrior data.location
        self.tw_client = tw_client or tasklib.TaskWarrior()
    
    def sync_obsidian_to_sqlite(self, folder="2_projeto"): ...
    def sync_sqlite_to_taskwarrior(self, policy_state="MAINTAIN"): ...
    def sync_taskwarrior_to_sqlite(self): ...
```

## §4 — sync_obsidian_to_sqlite (vault → SQLite)

```python
def sync_obsidian_to_sqlite(self, folder="2_projeto") -> int:
    """Iterates *.md under vault folder; parses frontmatter; UPSERT into planning_entities."""
    n = 0
    for md in self.vault.glob(f"{folder}/**/*.md"):
        frontmatter = parse_frontmatter(md)
        if not frontmatter:
            continue
        entity_type = frontmatter.get("type")
        payload_json = canonical_json(frontmatter)
        upstream_id = sha256(payload_json)[:12]  # idempotency key
        # UPSERT
        self.db.execute("""
            INSERT INTO planning_entities (entity_type, payload_json, upstream_id, synced_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(entity_type, upstream_id) DO UPDATE SET
                payload_json = excluded.payload_json,
                synced_at = excluded.synced_at
        """, (entity_type, payload_json, upstream_id, datetime.now()))
        n += 1
    return n
```

**Idempotency key:** SHA256(canonical_json(payload))[:12] — 12 hex chars. Mudar qualquer byte do frontmatter → novo upstream_id → nova row (histórico preservado).

**SQLite schema:**
```sql
CREATE TABLE planning_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    upstream_id TEXT NOT NULL,
    synced_at DATETIME NOT NULL,
    UNIQUE(entity_type, upstream_id)
);

CREATE TABLE roadmap_sync (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    synced_at DATETIME
);
```

## §5 — sync_sqlite_to_taskwarrior (SQLite → TW)

```python
def sync_sqlite_to_taskwarrior(self, policy_state="MAINTAIN") -> int:
    rows = self.db.execute("""
        SELECT pe.* FROM planning_entities pe
        JOIN roadmap_sync rs ON pe.id = rs.entity_id
        WHERE pe.entity_type = 'study_plan'
          AND rs.status = 'pending'
    """).fetchall()
    
    # Throttle: skip if RECOVER policy + heavy load
    if policy_state == "RECOVER" and self.daily_target_minutes > 60:
        return 0  # não sobrecarrega o usuário em RECOVER
    
    n = 0
    for row in rows:
        entity = StudyPlanEntity.model_validate_json(row["payload_json"])
        task_payload = TaskPayload(
            project=entity.tw_project_key,
            description=entity.title,
            tags=["study", f"policy:{policy_state.lower()}"],
            upstream_id=row["upstream_id"],  # idempotency
        )
        # Idempotent: filter TW by upstream_id, create OR update
        existing = self.tw_client.filter("project", entity.tw_project_key).filter("upstream_id", row["upstream_id"])
        if existing:
            existing[0].update(task_payload.as_dict())
        else:
            self.tw_client.tasks.add(**task_payload.as_dict())
        n += 1
    return n
```

**Throttle rule:** se `policy_state == "RECOVER"` e `daily_target_minutes > 60`, skip sync. Não sobrecarrega em recovery.

## §6 — sync_taskwarrior_to_sqlite (TW → SQLite)

```python
def sync_taskwarrior_to_sqlite(self) -> int:
    pending = self.db.execute("SELECT * FROM roadmap_sync WHERE status = 'pending'").fetchall()
    n = 0
    for row in pending:
        task = self.tw_client.get_task(uuid=row["tw_uuid"]) if row.get("tw_uuid") else None
        if task and task["status"] == "completed":
            self.db.execute(
                "UPDATE roadmap_sync SET status = 'completed', synced_at = ? WHERE id = ?",
                (datetime.now(), row["id"])
            )
            n += 1
    return n
```

**Single direction:** só lida com `completed` (TW→SQLite). Updates em descrição/datas não fluem de volta (single-source-of-truth: TW).

## §7 — Review Queue (atomic append-only)

`data/review_queue/<event_id>.json` — atomic write:

```python
# Pseudo-code (real impl in src/mesh/queue.py)
def enqueue(event: TaskChange) -> str:
    target = Path(f"data/review_queue/{event.event_id}.json")
    temp = target.with_suffix(".tmp")
    temp.write_text(event.model_dump_json(indent=2))
    temp.rename(target)  # atomic em POSIX; em Windows usa os.replace
    return event.event_id
```

**Invariante:** nunca deletar arquivo em `data/review_queue/`. Status muda via `ack()` que re-emite evento com novo status (não deleta).

## §8 — Cross-references

### Code
- `vibe-ops/src/middleware/sync_engine.py` — SyncEngine
- `src/mesh/queue.py` — atomic enqueue
- `src/contracts/task_change.py` — TaskChange
- `src/ikigai/tools/vault_taskdog_sync.py` — vault→taskdog wrapper

### Docs
- `docs/diagnostics/2026-08-28-phase3-decisions.md:D3-D6` — decisões de sync
- `src/operational/docs/architecture/08-INTERFACE-CLI.md` — sync CLI commands
- `docs/auto-performance-os/25-integration-deep-agent-sync.md` — sync flow canônico

### Memory
- `[[graph-orchestration-checkpoint-2026-08-27]]` — sync com TW é via PolicyEngine

## §9 — Fontes

- `vibe-ops/src/middleware/sync_engine.py` — SyncEngine class
- `src/mesh/queue.py` — atomic enqueue + replay_after_restart
- `src/contracts/task_change.py` — TaskChange model
- `data/review_queue/` — runtime storage
- `vibe-ops/architecture/ADR-004-hybrid-rag-strategy.md` — RAG + sync integration
