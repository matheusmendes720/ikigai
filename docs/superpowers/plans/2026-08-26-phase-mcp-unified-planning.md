> **[SUPERSEDED 2026-08-28 — ADR superseded; see master-branch-carro-chefe-2026-08-28]**
> This implementation plan (solverforge-calendar MCP UPI extension + mcp-gateway
> router + HTTP+SSE dual-transport) was authored 2026-08-26, the day of the
> AI-native pivot. It treats solverforge-calendar as the canonical UPI surface
> + gateway as the chokepoint. Post-pivot, solverforge-calendar is one of three
> forks-prontas widgets, not the canonical sync target — deep-agent owns the
> sync logic. The MCP-gateway concept is preserved as transport; the UPI layer
> becomes an MCP contract consumed by external apps rather than a kernel feature.

# Phase MCP: Unified Planning MCP Servers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose Unified Planning Item (UPI) CRUD + sync tools via the existing `solverforge-calendar-mcp` binary, wire them into the `mcp-gateway` router, and activate HTTP+SSE dual-transport.

**Architecture:** The `solverforge-calendar-mcp` binary already has a full MCP server using `rmcp`. We extend it with UPI tools that sit on top of the Phase 1 sync layer (`TuiboardReader → TuiboardTransformer → TuiboardWriter`). The gateway config gets a new `upi_` prefix route so LangChain agents can call `upi_sync`, `upi_list`, etc. HTTP+SSE transport is activated via the `http` feature flag.

**Tech Stack:** Rust (`rmcp` for MCP), Python (`FastAPI` for gateway), `rusqlite`, `regex`

---

## Global Constraints

- All MCP tool names use underscores (not dots): `upi_sync`, `upi_list`, `board_tasks_get` (tuiboard)
- UPI IDs are ULIDs: 26-char Crockford Base32 strings from `ulid::Ulid::new().to_string()`
- `SOLVERFORGE_DATA_DIR` env var controls where the SQLite DB lives (defaults to `dirs::data_dir()`)
- Solverforge HTTP transport listens on `127.0.0.1:3737` when `SOLVERFORGE_MCP_TRANSPORT=http`
- Gateway routes unknown tools to solverforge-calendar by default

---

## File Structure

```
apps/calendar/solverforge-calendar/
├── src/bin/solverforge-calendar-mcp.rs    # Extend with UPI tools + HTTP transport
├── src/sync/
│   ├── mod.rs                             # TuiboardWriter exported
│   ├── tuiboard_writer.rs                 # write_deltas() + WriteStats
│   └── ...

apps/mcp-gateway/
├── config/gateways.yaml                   # Add upi_ prefix route
└── ...

life-ops/life/.git/sdd/                   # SDD ledger
```

---

## Tasks

### Task 1: Add UPI DB helpers to `src/db.rs`

**Files:**
- Modify: `apps/calendar/solverforge-calendar/src/db.rs`

**Interfaces:**
- Consumes: `UnifiedPlanningItem`, `PlanningStatus`, `Dependency` from `models_unified.rs`
- Produces: new `db_*` functions callable from the MCP handler

Expose these from `db.rs` (add to existing DB module):

```rust
// List UPIs with optional filters
pub fn load_unified_items(conn: &Connection, limit: i64, offset: i64) -> Result<Vec<UnifiedPlanningItem>>;

// Get one UPI by ID
pub fn get_unified_item(conn: &Connection, id: &str) -> Result<Option<UnifiedPlanningItem>>;

// Update a UPI's status (used by upi_update tool)
pub fn update_unified_item_status(conn: &Connection, id: &str, status: &str) -> Result<()>;

// Full upsert (used by upi_upsert tool)
pub fn upsert_unified_item(conn: &Connection, item: &UnifiedPlanningItem) -> Result<()>;

// Get sync_map entry for wikilink resolution
pub fn get_sync_map_entry(conn: &Connection, board_path: &str, card_id: &str) -> Result<Option<String>>;

// FTS title search (stub using LIKE — vector search comes later)
pub fn search_unified_items_by_title(conn: &Connection, query: &str, limit: i64) -> Result<Vec<UnifiedPlanningItem>>;
```

- [ ] **Step 1: Read existing `src/db.rs`** to understand the pattern used for `load_calendars`, `get_event`, etc.

- [ ] **Step 2: Add function signatures** for all 6 functions above after the last existing DB function

- [ ] **Step 3: Implement `load_unified_items`** — SELECT from `unified_planning_items` WHERE `deleted_at IS NULL`, limit/offset, map rows to `UnifiedPlanningItem`:
```rust
pub fn load_unified_items(conn: &Connection, limit: i64, offset: i64) -> Result<Vec<UnifiedPlanningItem>> {
    let mut stmt = conn.prepare(
        "SELECT id, title, description, status, all_day, start_at, end_at, time_block,
                calendar_id, project_id, ikigai, provenance, blocked_by, tags, rrule,
                created_at, updated_at, deleted_at
         FROM unified_planning_items
         WHERE deleted_at IS NULL
         ORDER BY updated_at DESC
         LIMIT ? OFFSET ?"
    )?;
    let rows = stmt.query_map([limit, offset], |row| {
        Ok(UnifiedPlanningItem {
            id: row.get(0)?,
            title: row.get(1)?,
            description: row.get(2)?,
            status: serde_json::from_str(&row.get::<_, String>(3)?).unwrap_or(PlanningStatus::Pending),
            // ... etc
        })
    })?;
    rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
}
```

- [ ] **Step 4: Implement `get_unified_item`** — SELECT WHERE id = ? AND deleted_at IS NULL, return Option

- [ ] **Step 5: Implement `update_unified_item_status`** — UPDATE unified_planning_items SET status = ?, updated_at = now WHERE id = ?

- [ ] **Step 6: Implement `upsert_unified_item`** — INSERT OR REPLACE (needs all 17 fields)

- [ ] **Step 7: Implement `get_sync_map_entry`** — SELECT upi_id FROM sync_map WHERE board_path = ? AND board_card_id = ?

- [ ] **Step 8: Implement `search_unified_items_by_title`** — SELECT ... WHERE title LIKE '%query%' AND deleted_at IS NULL (FTS is Phase 5, this is the interim stub)

- [ ] **Step 9: Run `cargo check --lib`** — 0 errors

- [ ] **Step 10: Commit**

```bash
git add src/db.rs
git commit -m "feat(db): add UnifiedPlanningItem CRUD helpers"
```

---

### Task 2: Add UPI tools to `solverforge-calendar-mcp.rs`

**Files:**
- Modify: `apps/calendar/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs`

**Interfaces:**
- Consumes: `db::load_unified_items`, `db::get_unified_item`, `db::update_unified_item_status`, `db::upsert_unified_item`, `db::search_unified_items_by_title`
- Produces: 5 new MCP tools: `upi_sync`, `upi_list`, `upi_get`, `upi_update`, `upi_search`

Add these input types and tools to the MCP binary:

```rust
// ── UPI Tools ─────────────────────────────────────────────────────────

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
struct UpiListInput {
    #[serde(default = "default_limit")]
    limit: i64,
    #[serde(default)]
    offset: Option<i64>,
}
fn default_limit() -> i64 { 50 }

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
struct UpiGetInput {
    id: String,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
struct UpiUpdateInput {
    id: String,
    #[serde(default)]
    status: Option<String>,  // "pending" | "in_progress" | "done" | "blocked" | "cancelled"
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
struct UpiSearchInput {
    query: String,
    #[serde(default = "default_limit")]
    limit: i64,
}

#[derive(Debug, Deserialize, Serialize, JsonSchema)]
struct UpiSyncInput {
    #[serde(default)]
    boards_dir: Option<String>,  // defaults to SOLVERFORGE_DATA_DIR/boards
}
```

Add these 5 tools inside the existing `impl McpServer` block, after the `google_sync` tool:

```rust
#[tool(name = "upi_sync", description = "Run the full tuiboard→UPI sync pipeline: parse boards, transform to UnifiedPlanningItem, upsert to SQLite, resolve wikilinks")]
async fn upi_sync(&self, params: Parameters<UpiSyncInput>) -> Result<CallToolResult, ErrorData> {
    let input = params.0;
    let db_path = std::path::PathBuf::from(
        std::env::var("SOLVERFORGE_DATA_DIR")
            .unwrap_or_else(|_| dirs::data_dir().unwrap().join("solverforge").to_string_lossy().to_string())
    );
    let boards_dir = input.boards_dir.map(std::path::PathBuf::from)
        .unwrap_or_else(|| db_path.join("boards"));

    let writer = tuiboard_writer::TuiboardWriter::new(db_path.join("unified_planning.db"))
        .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))?;

    let reader = tuiboard_parser::TuiboardReader::new(boards_dir);
    let deltas = reader.read_deltas(None)
        .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))?;

    let stats = writer.write_deltas(deltas)
        .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))?;

    let json = serde_json::to_value(&stats).unwrap();
    Ok(CallToolResult::success(vec![ContentBlock::json(json).unwrap()]))
}

#[tool(name = "upi_list", description = "List UnifiedPlanningItems with pagination")]
async fn upi_list(&self, params: Parameters<UpiListInput>) -> Result<CallToolResult, ErrorData> {
    let UpiListInput { limit, offset } = params.0;
    let conn = self.db.clone();
    let offset = offset.unwrap_or(0);
    tokio::task::spawn_blocking(move || {
        db::load_unified_items(&*conn.lock().unwrap(), limit, offset)
            .map(|v| {
                let json = serde_json::to_value(v).unwrap();
                CallToolResult::success(vec![ContentBlock::json(json).unwrap()])
            })
            .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))
    })
    .await
    .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))?
}

#[tool(name = "upi_get", description = "Get a single UnifiedPlanningItem by ID")]
async fn upi_get(&self, params: Parameters<UpiGetInput>) -> Result<CallToolResult, ErrorData> {
    let UpiGetInput { id } = params.0;
    let conn = self.db.clone();
    tokio::task::spawn_blocking(move || {
        db::get_unified_item(&*conn.lock().unwrap(), &id)
            .map(|opt| {
                let json = serde_json::to_value(opt).unwrap();
                CallToolResult::success(vec![ContentBlock::json(json).unwrap()])
            })
            .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))
    })
    .await
    .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))?
}

#[tool(name = "upi_update", description = "Update a UnifiedPlanningItem's status")]
async fn upi_update(&self, params: Parameters<UpiUpdateInput>) -> Result<CallToolResult, ErrorData> {
    let UpiUpdateInput { id, status } = params.0;
    let conn = self.db.clone();
    tokio::task::spawn_blocking(move || {
        if let Some(s) = status {
            db::update_unified_item_status(&*conn.lock().unwrap(), &id, &s)
                .map(|_| CallToolResult::success(vec![ContentBlock::json(serde_json::json!({"updated": true, "id": id})).unwrap()]))
                .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))
        } else {
            Err(ErrorData::new(rmcp::model::ErrorCode::INVALID_PARAMS, Cow::Borrowed("status is required"), None))
        }
    })
    .await
    .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))?
}

#[tool(name = "upi_search", description = "Search UnifiedPlanningItems by title (LIKE query, FTS in Phase 5)")]
async fn upi_search(&self, params: Parameters<UpiSearchInput>) -> Result<CallToolResult, ErrorData> {
    let UpiSearchInput { query, limit } = params.0;
    let conn = self.db.clone();
    tokio::task::spawn_blocking(move || {
        db::search_unified_items_by_title(&*conn.lock().unwrap(), &query, limit)
            .map(|v| {
                let json = serde_json::to_value(v).unwrap();
                CallToolResult::success(vec![ContentBlock::json(json).unwrap()])
            })
            .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))
    })
    .await
    .map_err(|e| ErrorData::new(rmcp::model::ErrorCode::INTERNAL_ERROR, e.to_string(), None))?
}
```

- [ ] **Step 1: Read the top of `src/bin/solverforge-calendar-mcp.rs`** to see imports and how `tuiboard_writer` would be imported

- [ ] **Step 2: Add import** for the sync module:
```rust
use solverforge_calendar::sync::{tuiboard_writer, tuiboard_parser};
```

- [ ] **Step 3: Add input types** (UpiListInput, UpiGetInput, UpiUpdateInput, UpiSearchInput, UpiSyncInput) after the Google input types

- [ ] **Step 4: Add the 5 tool implementations** after `google_sync`

- [ ] **Step 5: Run `cargo check --bin solverforge-calendar-mcp 2>&1`** — expect 0 errors (warnings OK)

- [ ] **Step 6: Commit**

```bash
git add src/bin/solverforge-calendar-mcp.rs
git commit -m "feat(mcp): add 5 UPI tools — upi_sync, upi_list, upi_get, upi_update, upi_search"
```

---

### Task 3: Wire UPI tools into mcp-gateway router

**Files:**
- Modify: `apps/mcp-gateway/config/gateways.yaml`

**Interfaces:**
- Consumes: new `upi_sync`, `upi_list`, `upi_get`, `upi_update`, `upi_search` tools from solverforge-calendar
- Produces: updated `gateways.yaml` with `upi_` prefix route

- [ ] **Step 1: Read `apps/mcp-gateway/config/gateways.yaml`** to understand the current structure

- [ ] **Step 2: Add `upi_` to solverforge-calendar tool_prefixes:**
```yaml
  - name: solverforge-calendar
    command: ["cargo", "run", "--bin", "solverforge-calendar-mcp"]
    cwd: "C:/Users/mathe/code_space/apps/calendar/solverforge-calendar"
    tool_prefixes:
      - "calendars_"
      - "events_"
      - "projects_"
      - "dependencies_"
      - "google_"
      - "upi_"        # ← new
```

- [ ] **Step 3: Run gateway tests**
```bash
cd apps/mcp-gateway && python -m pytest tests/ -v
```
Expected: all 10 tests pass

- [ ] **Step 4: Commit**

```bash
cd apps/mcp-gateway && git add config/gateways.yaml && git commit -m "feat(gateway): route upi_* tools to solverforge-calendar"
```

---

### Task 4: Fix unused-code warnings in solverforge-calendar-mcp

**Files:**
- Modify: `apps/calendar/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs`

- [ ] **Step 1: Prefix the unused `params` in `google_sync`** with underscore:
```rust
async fn google_sync(&self, _params: Parameters<GoogleSyncInput>) -> Result<CallToolResult, ErrorData> {
```

- [ ] **Step 2: Remove the unused `exec_json` function** (lines ~222-225) or mark it `#[allow(dead_code)]` if it may be used later

- [ ] **Step 3: Run `cargo check --bin solverforge-calendar-mcp 2>&1 | grep -E "warning|error"`** — expect only warnings from third-party deps

- [ ] **Step 4: Commit**

```bash
git add src/bin/solverforge-calendar-mcp.rs && git commit -m "fix(mcp): remove dead code and unused variable warnings"
```

---

### Task 5: Write tests for UPI MCP tools

**Files:**
- Create: `apps/calendar/solverforge-calendar/tests/test_upi_mcp.rs`

**Interfaces:**
- Consumes: `solverforge-calendar-mcp` binary (uses stdio transport)
- Produces: integration tests covering all 5 UPI tools

- [ ] **Step 1: Write test for `upi_list`** — spawn binary over stdio, call `upi_list`, assert non-empty result structure:
```rust
#[tokio::test]
async fn test_upi_list_returns_array() {
    let child = Command::new("cargo")
        .args(["run", "--bin", "solverforge-calendar-mcp"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();

    // Send initialize + tools/call for upi_list over stdio JSON-RPC
    let (mut stdout, _) = child.stdin.unwrap().split();
    // ... JSON-RPC handshake ...
    // assert result is an array
}
```
(Use the same stdio JSON-RPC testing pattern as the gateway's `test_integration.py`)

- [ ] **Step 2: Write test for `upi_get` with a known ID** — call `upi_list` first to get an ID, then `upi_get` with that ID, assert round-trip

- [ ] **Step 3: Write test for `upi_update`** — call `upi_list`, pick first item, call `upi_update` with a new status, then `upi_get` and assert status changed

- [ ] **Step 4: Write test for `upi_search`** — search for a known title substring, assert results contain it

- [ ] **Step 5: Write test for `upi_sync`** — call `upi_sync`, assert `WriteStats` JSON with expected fields (`upserted`, `wikilinks_resolved`, etc.)

- [ ] **Step 6: Run tests**
```bash
cd apps/calendar/solverforge-calendar && cargo test --test test_upi_mcp
```
Expected: all 5 tests pass

- [ ] **Step 7: Commit**

```bash
git add tests/test_upi_mcp.rs && git commit -m "test(mcp): add UPI tool integration tests"
```

---

## Self-Review Checklist

- [ ] Spec coverage: All 5 UPI tools have tests
- [ ] No placeholders: every function body is complete
- [ ] Type consistency: `db.rs` return types match what `solverforge-calendar-mcp.rs` calls with
- [ ] Gateway route: `upi_` prefix covers all 5 new tools
- [ ] `cargo check --bin solverforge-calendar-mcp` → 0 errors before each commit
- [ ] Tests cover: list, get (round-trip), update (round-trip), search, sync

---

## Post-MCP Phase Roadmap (for future plans)

| Phase | What's needed |
|-------|---------------|
| Phase 2 | solverforge event → UPI ingestion (events already in DB, need to surface via upi_) |
| Phase 3 | taskdog → UPI ingestion |
| Phase 4 | Bidirectional write-back: UPI → tuiboard, UPI → taskdog |
| Phase 5 | FTS (SQLite FTS5) for upi_search; Qdrant/ChromaDB vector embedding |
| Phase 6 | ikigai vectors in UPI — surface via `ikigai_` tools |

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-08-26-phase-mcp-unified-planning.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
