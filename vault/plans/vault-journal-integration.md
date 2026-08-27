---
name: vault-journal-integration
description: Conexão vault-journal (Rust) ↔ PAV MCP Gateway ↔ IKIGAI
type: spec
---

# vault-journal ↔ PAV Integration

## O que É vault-journal

`code_space/apps/vault-journal/` é um workspace Rust com 3 apps:

| App | Tech | Descrição |
|-----|------|-----------|
| `tui-journal` | Rust + ratatui | Terminal journal/notes TUI |
| `vault-tasks` | Rust + ratatui | Markdown task manager (lê qualquer vault) |
| `journalot` | Bash | Minimal journaling CLI, auto-commits git |

## Diagrama de Fluxo

```
┌─────────────────────────────────────────────────────────────┐
│  vault-journal/tui-journal (Rust TUI)                       │
│  DataProvider trait (sqlite.rs / json.rs)                    │
│  Entry { id: u32, date, title, content, tags, priority }   │
└──────────────────────┬──────────────────────────────────────┘
                       │ journal.db (SQLite)
┌──────────────────────▼──────────────────────────────────────┐
│  PAV MCP Gateway (Python)                                    │
│  ─────────────────────────────────────────────────────      │
│  src/pav/mcp_gateway.py                                     │
│  → Lê journal.db diretamente (sem subprocess)              │
│  → journal.db fica em ~/.journal.db (padrão tui-journal)   │
│                                                              │
│  tb_journal_insert() ← INSERT EntryDraft                    │
│  tb_journal_query(date) ← SELECT entries                   │
│  tb_journal_log_energy() ← INSERT energy reading            │
│  tb_journal_log_habit() ← INSERT habit log                 │
└──────────────────────┬──────────────────────────────────────┘
                       │ MCP stdio
┌──────────────────────▼──────────────────────────────────────┐
│  IKIGAI Agent (Python)                                      │
│  → ikigai_plan_cycle() lê QHEMetrics ← PAV                 │
│  → vault-tasks (Rust) pode ler vault/ markdown tasks       │
└─────────────────────────────────────────────────────────────┘
```

## Schema tui-journal — Entry

De `backend/src/lib.rs` + `backend/src/sqlite/sqlite_helper.rs`:

```rust
// Entry (Rust)
pub struct Entry {
    pub id: u32,                        // auto-increment (INTEGER PRIMARY KEY)
    pub date: DateTime<Utc>,            // timestamp
    pub title: String,
    pub content: String,                 // narrativa livre
    pub tags: Vec<String>,              // Rust: Vec<String>, SQLite: comma-separated
    pub priority: Option<u32>,
}

pub struct EntryDraft {
    pub date: DateTime<Utc>,
    pub title: String,
    pub content: String,
    pub tags: Vec<String>,
    pub priority: Option<u32>,
}
```

**SQLite schema** (`backend/src/sqlite/mod.rs` — inferido do helper):

```sql
CREATE TABLE entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,          -- ISO8601: "2026-08-27T14:30:00Z"
    title       TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL DEFAULT '',
    tags        TEXT,                    -- "tag1,tag2,tag3" (comma-separated)
    priority    INTEGER,                -- NULL ou u32
    created_at  TEXT,                   -- audit
    updated_at  TEXT                    -- audit
);
```

**Tags são comma-separated em SQLite**, não JSON. Converter ao ler/escrever.

## DataProvider Trait (Rust)

```rust
// backend/src/lib.rs
pub trait DataProvider {
    async fn load_all_entries(&self) -> Vec<Entry>;
    async fn add_entry(&self, entry: EntryDraft) -> Result<Entry, ModifyEntryError>;
    async fn restore_entry(&self, entry: Entry) -> Result<Entry, ModifyEntryError>;
    async fn remove_entry(&self, entry_id: u32) -> anyhow::Result<()>;
    async fn update_entry(&self, entry: Entry) -> Result<Entry, ModifyEntryError>;
    async fn get_export_object(&self, entries_ids: &[u32]) -> anyhow::Result<EntriesDTO>;
    async fn import_entries(&self, entries_dto: EntriesDTO) -> anyhow::Result<()>;
    async fn assign_priority_to_entries(&self, priority: u32) -> anyhow::Result<()>;
}

// Implementações:
// - SqliteDataProvide (sqlite.rs) — usa SQLite
// - JsonDataProvide (json.rs) — usa JSON files
```

## PAV Extended Schema

PAV precisa estender o journal.db com tabelas extras que tui-journal não tem:

```sql
-- Tabelas PAV (criadas por PAV MCP Gateway se não existirem)

CREATE TABLE IF NOT EXISTS energy_readings (
    id          TEXT PRIMARY KEY,       -- "erg_<date>_<time>"
    date        TEXT NOT NULL,          -- YYYY-MM-DD
    time        TEXT,                   -- HH:MM
    level       TEXT NOT NULL,          -- high | medium | low
    context     TEXT,
    logged_at   TEXT
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id              TEXT PRIMARY KEY,   -- "hst_<habit_id>_<date>"
    habit_id        TEXT NOT NULL,
    date            TEXT NOT NULL,
    completed       INTEGER NOT NULL,   -- 0 or 1
    effort_minutes  INTEGER,
    notes           TEXT,
    logged_at       TEXT
);

CREATE TABLE IF NOT EXISTS qhe_metrics (
    id              TEXT PRIMARY KEY,   -- "qhe_<date>"
    date            TEXT UNIQUE NOT NULL,
    habit_avg       REAL NOT NULL,
    consistency     REAL NOT NULL,
    streak_bonus    REAL NOT NULL,
    energy_ratio    REAL NOT NULL,
    qhe_score       REAL NOT NULL,
    regime_input    TEXT,
    created_at      TEXT
);

CREATE TABLE IF NOT EXISTS policy_decisions (
    id              TEXT PRIMARY KEY,
    date            TEXT UNIQUE NOT NULL,
    regime          TEXT NOT NULL,
    q_he            REAL NOT NULL,
    days_in_regime  INTEGER NOT NULL,
    hardwork_budget INTEGER,
    sleep_target    REAL,
    pomodoros       INTEGER,
    set_by          TEXT,
    created_at      TEXT
);
```

## PAV MCP Gateway — Ferramentas

```python
# src/pav/mcp_gateway.py
# journal.db path
JOURNAL_DB = Path.home() / ".journal.db"

# Tools:
pav_log_habit(habit_id, date, completed, effort_minutes, notes) → str
pav_log_energy(date, time, level, context) → str
pav_log_journal(date, block_start, block_end, content, tags) → str
pav_get_journal_blocks(date) → list[dict]
pav_get_habit_streak(habit_id) → dict
pav_list_habits(active_only) → list[dict]
pav_create_habit(name, frequency, description) → habit_id
pav_compute_qhe(date) → dict
pav_get_qhe_history(days) → list[dict]
pav_get_policy_decision(date) → dict
```

## vault-tasks — Leitor de Vault Markdown

`vault-tasks` pode ser tool do IKIGAI:

```
vault-tasks/src/lib.rs:
- Vaults tree (recursive vault traversal)
- VaultNode / FileEntryNode
- TaskManager (parse + filter + tag collection)

Ex: vault-tasks --vault life/vault/ list-tasks --tag sonho
```

Tool IKIGAI sugerida:
```python
@tool
def vault_tasks_list_tasks(vault_path: str, tag: str | None = None) -> str:
    """Lista tasks de um vault markdown via vault-tasks CLI."""
    # chama: vault-tasks --vault <path> list-tasks [--tag <tag>]
```

## journalot (Bash alternative)

`journalot/bin/journal` é CLI minimal:
- Usa editor externo
- Arquivos markdown puros (não SQLite)
- Auto-commits git

Se PAV precisar de journaling em markdown puro (sem SQLite), journalot é alternativa.

## CBT Prompts — De obsidian-chat-cbt-plugin

Fonte: `obsidian-chat-cbt-plugin/src/prompts/`

### system.ts (original — CBT therapist)
```typescript
const system = `...act as a kind, open Cognitive Behavioral Therapist...
  Ask questions one at a time...
  Identify negative thinking patterns (All-or-Nothing, Overgeneralization, Mental Filter)...
  Guide through cognitive restructuring...`
```

### summary.ts (original)
```typescript
const summary = (lang) =>
  `Create markdown table: belief | emotion | category | reframed`
```

### PAV adaptações

**journal_block_prompt** (time-block):
```
Você está fazendo um journal de operação pessoal.
Responda brevemente. Um ponto por vez.

1. O que você realizou neste bloco?
2. Qual sua energia? (high | medium | low)
3. Houve blockers?
4. O que aprendeu sobre seu ritmo?
```

**daily_summary_prompt**:
```
| Bloco | Energia | Realizado | Blockers | Ritmo |
|-------|---------|-----------|----------|-------|
```

## Questões em Aberto

- [x] vault-journal existe
- [x] tui-journal usa SQLite com Entry {id:u32, date, title, content, tags, priority}
- [x] DataProvider trait (sqlite + json backends)
- [x] journal.db path: ~/.journal.db
- [ ] PAV conecta direto no journal.db com schema estendido
- [ ] vault-tasks integrado como tool IKIGAI
- [ ] journalot como fallback (markdown puro)

## Status

- [x] vault-journal encontrado e estruturado
- [x] Schema Entry extraído de lib.rs e sqlite_helper.rs
- [x] DataProvider trait compreendido
- [x] PAV extended schema definido
- [ ] PAV MCP Gateway — criar
- [ ] vault-tasks como tool IKIGAI
- [ ] CBT prompts em src/pav/prompts/
- [ ] Testar: tui-journal log → journal.db → PAV → IKIGAI cycle
