# 01 — tuiboard fork: reverse-engineering audit

**Date:** 2026-08-28
**Source fork:** `C:/Users/mathe/code_space/life-oss/interfaces/tuiboard/`
**Upstream:** `github.com/NazzarenoGiannelli/tuiboard` v0.8.4 (per `package.json:3`)
**Runtime:** Bun 1.2+ + OpenTUI/Solid (TUI framework) + SolidJS (reactive store)
**MCP transport:** stdio JSON-RPC, protocol `2024-11-05`
**Phase 1 baseline:** `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` B-01 (gateways.yaml cwd paths MISSING) — fork is correctly placed under `life-oss/interfaces/tuiboard/` but `gateways.yaml:4` still points at the missing `apps/kanban/tuiboard` path.

---

## Component map

All components are Solid functional components that take `{ store, ... }` props (sometimes a `Board` / `Task` prop) and emit OpenTUI renderables (`<box>`, `<text>`, `<scrollbox>`, `<input>`). No class components. The store is the sole data source for cross-zone state.

### Entry + shell

| Component | File:line | Props | Key state | Key events |
|-----------|-----------|-------|-----------|------------|
| `App` (root) | `src/app.tsx:108-155` | none | `plannerItems` memo (109-111), `view` from args | `useKeyboard` (113) → `handleKey` |
| `TopBar` | `src/ui/Chrome.tsx:14-76` | `{ store }` | `activeStats()` (17-31) | `onMouseDown` on each board tab → `setActiveBoard` (48) |
| `BottomBar` | `src/ui/Chrome.tsx:78-124` | `{ store }` | `banner()` (79) | none (read-only status strip) |
| `ModalLayer` | `src/ui/Modal.tsx:32-41` | `{ store }` | `modal` memo (33) | delegates to `ModalRouter` |

### Dashboard views

| Component | File:line | Layout role |
|-----------|-----------|-------------|
| `Dashboard` | `src/views/Dashboard.tsx:36-47` | Switches `FourZoneLayout` ↔ `ZoomedLayout` on `ui.zoomed` |
| `FourZoneLayout` | `src/views/Dashboard.tsx:100-142` | Row+column split: left = planner+board, agents strip on bottom, agenda (or modal) on right |
| `ZoomedLayout` | `src/views/Dashboard.tsx:63-98` | Full-screen one zone via `BoardOnly`/`TimelineOnly`/`AgentsOnly`; modal overlays as `position:absolute` `zIndex:100` |
| `BoardOnly` | `src/views/BoardOnly.tsx:19-35` | Fullscreen kanban + planner (respects `ui.zoomed`) |
| `TimelineOnly` | `src/views/TimelineOnly.tsx:6-12` | Fullscreen agenda |
| `AgentsOnly` | `src/views/AgentsOnly.tsx:24-103` | Fullscreen session list — shows ALL sessions including archived |

### Zone components

| Component | File:line | Props | Reactive signals | Events |
|-----------|-----------|-------|------------------|--------|
| `BoardView` | `src/ui/BoardView.tsx:69-225` | `{ store, board }` | `scrollX` (75), `viewportW` (80), `visibleColumns` (88), `renderedColumns` (97-108) | `createEffect` (119-147) auto-scrolls active column |
| `ColumnView` (inner) | `src/ui/BoardView.tsx:253-435` | `{ store, board, column, columnIndex, active, zoomed, tasksVisible, boxId }` | `allTasks` (254-260), `openTasks` (261-263), `doneTasks` (264), `visibleTasks` (268-270), `taskListKey` (280-298), `cursorRow` (300) | `onClick` per `TaskRow` (399-408) — sets cursor, arms timeline if `armMode` |
| `PlannerPanel` | `src/ui/PlannerPanel.tsx:35-141` | `{ store }` | `items`, `groups` (40), `isActive` (41), `isZoomed` (42-44), `cursorRow` (45) | `onClickItem` (123-135) — cursor + arm-mode arming |
| `RenderGroups` (inner) | `src/ui/PlannerPanel.tsx:143-258` | groups + isMarkedFn + onClickItem | none — pure render | delegates to `TaskRow.onClick` |
| `TimelineView` | `src/ui/TimelineView.tsx:85-469` | `{ store, width? }` | `entries` (104-110), `calEntries` (120-122), `allDayEvents` (123-125), `nowMin` (129 via `useNowMin`), `rowMap` (130-135), `armedEntry` (138-147), `armedTask` (150-154), `cursorEntry` (191) | `onBlockClick` (201-264), `onEmptyRowClick` (273-333) |
| `TimelineRow` (inner) | `src/ui/TimelineView.tsx:514-649` | pair/rowIndex/cursorEntry/armedEntry/selectedCalKey/innerWidth/onBlockClick/onEmptyRowClick | `left/right` (515-516), `cellMouseDown` factory (559-568) | `onMouseDown` per lane box (587, 616, 639) |
| `RowContent` (inner) | `src/ui/TimelineView.tsx:660-786` | row/rowIndex/skipPrefix/laneWidth | pure (kind switch) | none |
| `AgentsBar` | `src/ui/AgentsBar.tsx:30-113` | `{ store, height? }` | `allShown` (35-37) | `onClick` per row (101-104) |
| `AgentRow` | `src/ui/AgentRow.tsx:37-84` | `{ session, cursor?, nameMaxChars?, onClick? }` | `ageStr` (38-40), `displayName` (42-45) | `onMouseDown` (55) |
| `TaskRow` | `src/ui/TaskRow.tsx:46-150` | `{ task, cursor?, marked?, grabbed?, contextTag?, contextColor?, hideDateSuffix?, availableWidth?, titleMaxChars?, onClick? }` | `status` (47), `suffix` (48), `titleColor` (49), `suffixColor` (50), `titleBudget` (55-72), `visibleTitle` (74-76) | `onMouseDown` (92) |

### Modal dialogs (`ModalRouter` at `src/ui/Modal.tsx:43-60`)

| Kind | File:line | Body |
|------|-----------|------|
| `add` | `src/ui/Modal.tsx:107-153` | `<input>` + `parseQuickAdd` → `addTask` |
| `edit` | `src/ui/Modal.tsx:157-185` | `<input>` prefilled with `displayTitle` |
| `schedule` | `src/ui/Modal.tsx:189-227` | `<input>` + `parseDateShortcut` |
| `timeblock` | `src/ui/Modal.tsx:231-272` | `<input>` + `parseTimeBlockShortcut` |
| `assign` | `src/ui/Modal.tsx:500-528` | `<input>` stripped of leading `@` |
| `confirm-delete` | `src/ui/Modal.tsx:532-551` | Read-only confirmation; y/Enter confirm |
| `detail` | `src/ui/Modal.tsx:555-631` | All parsed fields + wikilinks |
| `agent-detail` | `src/ui/Modal.tsx:692-796` | Session meta + last user/assistant + resume command preview |
| `event` (2-step) | `src/ui/Modal.tsx:349-420` | step 1: input → `peelEventInput`; step 2: `<For>` calendar picker |
| `event-edit` | `src/ui/Modal.tsx:429-474` | Single `<input>` → `confirmEventEdit` |
| `confirm-delete-event` | `src/ui/Modal.tsx:478-496` | Read-only event delete confirm |
| `search` | `src/ui/Modal.tsx:635-688` | `<input>` → first-match jump |
| `help` | `src/ui/Modal.tsx:800-866` | Static reference text |

All dialogs share `DialogShell` (71-103): rounded border box with `MODAL_WIDTH = AGENDA_WIDTH` so they drop into the Agenda's slot.

---

## Widget inventory

| Widget | Where | Notes |
|--------|-------|-------|
| Board tabs (clickable) | `Chrome.tsx:42-65` | `[N name]` active vs ` N name  ` inactive; click sets active board |
| Banner (info/warn/error) | `Chrome.tsx:82-108` | Auto-dismiss (3s info, 6s error) via `flashBanner` |
| Cheat-sheet keybar | `Chrome.tsx:109-121` | Truncates with `truncate` on `wrapMode="none"` |
| Column boxes (rounded border + title) | `BoardView.tsx:332-352` | Border color active vs not; title shows `┤ name N ✓done ├` |
| Done-counter footer | `BoardView.tsx:417-430` | `✓ N done  (z to focus)` only when not zoomed |
| Kanban `TaskRow` | `TaskRow.tsx:78-149` | Cursor / mark / done / priority / title / suffix / contextTag |
| Planner section headers | `PlannerPanel.tsx:170-177` | `● Overdue`, `● Today`, `→ Tomorrow` |
| Planner bucket headers | `PlannerPanel.tsx:179-196` | `⏰ Agenda`, `🔺 Priority` |
| Planner subgroup headers | `PlannerPanel.tsx:226-232` | `— board · column —` per-board grouping |
| Agenda title chip | `TimelineView.tsx:355-356` | `┤ Agenda · <date> · N [◉ ARM] ├` |
| Agenda ARM-mode strip | `TimelineView.tsx:358-367` | Bold warm banner with click instructions |
| Agenda armed-task strip | `TimelineView.tsx:368-382` | Shows the current armed task + placement hint |
| Agenda selected-cal strip | `TimelineView.tsx:384-393` | e edit / d delete / Esc deselect |
| Agenda day-nav hint | `TimelineView.tsx:397-403` | `[ ] change day · \ today` |
| Agenda overflow warning | `TimelineView.tsx:404-410` | `⚠ N blocks hidden by 3-way overlap` |
| All-day event chip strip | `TimelineView.tsx:414-433` | Up to 8 chips + `+N` overflow |
| Timeline hour/row grid | `TimelineView.tsx:660-696` | Hour anchor `NN ────`, empty `···` |
| NOW marker (red bold line) | `TimelineView.tsx:664-674` | Recomputes every 60s via `useNowMin` (835-840) |
| Timeline band (head/body/fill) | `TimelineView.tsx:697-784` | Color = `boardColor(boardIndex)` |
| Agent rows | `AgentRow.tsx:47-83` | status glyph + name + branch + cwd-short + age |
| `<input>` modal fields | Modal.tsx (all modal kinds) | `focused` attr, `onInput`/`onSubmit` callbacks |
| DialogShell | `Modal.tsx:71-103` | Rounded border with title riding the top border |

Glyphs: see `src/ui/glyphs.ts:1-156`. Theme uses muted hex (`#7eb6d6` cyan, `#e8a05c` warm, `#e26a6a` red) not raw ANSI to avoid traffic-light clash with terminal themes. Backgrounds are mostly transparent.

---

## State diagram

`src/store/index.ts` defines a single `createStore<StoreState>` (lines 268-287) wrapping all reactive state.

```
StoreState
├─ boards: LoadedBoard[]             ← from loadAll() at construction
│   └─ { board: Board, mtimeMs }
├─ ui: UIState                       ← all cross-zone UI
│   ├─ activeBoardIndex: number      (setActiveBoard:806-813)
│   ├─ activeZone: "planner"|"board"|"timeline"|"agents"
│   │  (setActiveZone:820-825 → row=0 if not board)
│   ├─ visibleZones: 4×boolean        (derived: enabledZones ∧ desiredVisible ∧ lastFits)
│   ├─ enabledZones: 4×boolean        (from config.zones)
│   ├─ col: number,  row: number      (cursor)
│   ├─ zoomed: boolean                (toggleZoom:872-874)
│   ├─ grabbing: boolean              (toggleGrab:910-912)
│   ├─ armMode: boolean               (setArmMode:922-924)
│   ├─ armedTimelineRef?: TaskRef     (armTimeline:918-920)
│   ├─ selectedCalEvent?: SelectedCalEvent (selectCalEvent:1206-1214)
│   ├─ agendaOffset: number ∈ [-365,+365] (shiftAgendaDay:937-943)
│   ├─ view: "kanban"|"list"
│   ├─ marked: Record<string,true>    (toggleMark:974-984)
│   ├─ filter: "all"|"today"|"overdue"|"tomorrow"|"followup"
│   ├─ banner?: { kind, text, ts }    (flashBanner:367-382)
│   ├─ modal?: ModalKind              (openModal:1110-1112)
│   └─ eventPicker?: EventPicker      (event 2-step state:90-101)
├─ undo: UndoEntry[]                 ← capped at 50 entries
└─ rev: number                       ← mutation counter; bumped on every saveBoard
                                        (StoreState.rev:226; usage rationale at 218-227)

UIState invariants enforced by setters:
  • visibleZones = AND(enabledZones, desiredVisible, lastFits)    (computeVisible:261-266)
  • recomputeVisible() (829-833) bounces activeZone → "board" if just hidden
  • setActiveZone resets row=0 for vertical-list zones
  • undo capped at 50 entries via produce+shift loop (449-450)
```

Reactive plumbing (why `rev` exists):
- `BoardView.ColumnView` reads `state.rev` inside `allTasks` memo (259) and `taskListKey` memo (281-297) to force re-renders when OpenTUI's fine-grained tracking of nested children-array edits misses them.
- `TaskRow.taskListKey` ALSO embeds marked-refs so selection changes rebuild the list (BoardView.tsx:283-297 comment: "Fold the current selection into the key too. OpenTUI doesn't reliably re-render a per-row `marked` prop on a store change, so a selection change … must rebuild the list to repaint the ● dots").

Mutation pipeline (e.g. `toggleDone`, `store/index.ts:466-510`):
```
setState (produce mutate in place) → pushUndo (capture inverse)
  → saveBoard (bump rev → serialize → atomic write → record self-write for watcher guard)
```

Persistence path is symmetric: `saveBoard` (`store/index.ts:392-440`) calls `serializeBoard` + `writeBoardFile` + records `lastWrittenContent` so the watcher can recognize our own echoed writes.

---

## MCP tool inventory

Server: `bin/tuiboard-mcp.ts` (entry stub, 17 lines) → `src/v3/mcp/server.ts` (278 lines).

**Transport:** stdio JSON-RPC, one JSON object per line on stdin (matches MCP stdio spec). `initObservability()` (`src/v3/observability/init.ts`) bootstraps OTel before the server loop.

**Protocol:** `2024-11-05`, `serverInfo: { name: "tuiboard", version: "0.8.3" }` (server.ts:248-250). Note version mismatch with `package.json` v0.8.4 — server.ts has stale 0.8.3.

**Methods supported** (server.ts:194-262):
- `initialize` (245-253) — returns capabilities `{ tools: {} }`
- `ping` (256-259) — returns `null`
- `tools/list` (195-198) — calls `getToolList()`
- `tools/call` (201-242) — validates via Zod, wraps in `withToolSpan` (OTel), returns `{ content: [{ type: "text", text: JSON.stringify(result) }] }`

**Tools** (5 total, `server.ts:62-162`, `getToolList()`):

| Tool | Input schema | Handler | File |
|------|--------------|---------|------|
| `board_list` | `{ configPath?: string }` | `handleBoardList` | `tools/board-list.ts:32-73` |
| `board_tasks_get` | `{ boardPath: string, columnIndex?: int, taskIndex?: int, filter?: "all"\|"today"\|"overdue"\|"tomorrow" }` | `handleBoardTasksGet` | `tools/board-tasks-get.ts:27-105` |
| `board_tasks_update` | `{ boardPath, columnIndex, taskIndex, expectedMtimeMs, patch: TaskPatch }` | `handleBoardTasksUpdate` | `tools/board-tasks-update.ts:19-82` |
| `board_tasks_create` | `{ boardPath, columnIndex, expectedMtimeMs, insertAt?, task: TaskInit }` | `handleBoardTasksCreate` | `tools/board-tasks-create.ts:21-111` |
| `board_tasks_delete` | `{ boardPath, columnIndex, taskIndex, expectedMtimeMs }` | `handleBoardTasksDelete` | `tools/board-tasks-delete.ts:19-77` |

**Zod schemas** (`src/v3/mcp/schemas.ts`):
- `IsoDate` regex `^\d{4}-\d{2}-\d{2}$` (line 9)
- `Min` int 0..1440 (line 11)
- `TimeBlock` refines `endMin > startMin` (lines 13-17)
- `PriorityLevel` enum 6 values (lines 19-26)
- `TaskPatch` (30-43) and `TaskInit` (45-57) both `.strict()` — extra fields rejected
- `BoardTasks*Input` schemas all `.strict()` (61-99) — strict enforcement is a load-bearing guard against silently-typo'd field names

**Validation flow** (server.ts:208-225): Zod parse first, then dispatch. Parse failure → `InvalidParams` with `err.message`.

**Mutating tools use optimistic concurrency**: every write takes `expectedMtimeMs` (schemas.ts:77, 86, 96). `mutateAndWrite` (`src/v3/mcp/board-io.ts:33-52`) calls `writeBoardFile(..., { expectedMtimeMs })` which throws `ConflictError` if disk mtime differs (`io/writer.ts:54-65`). On conflict the tool returns JSON-RPC error code `Conflict = -32800` (`errors.ts:14`) with `{ kind: "conflict", expectedMtimeMs, actualMtimeMs }` (board-tasks-update.ts:73-79).

**Error codes** (`src/v3/mcp/errors.ts:7-16`):
| Code | Name | Usage |
|------|------|-------|
| `-32700` | ParseError | Bad JSON on stdin |
| `-32600` | InvalidRequest | Method not a string |
| `-32601` | MethodNotFound | Unknown method/tool |
| `-32602` | InvalidParams | Zod parse failure or column/task lookup miss |
| `-32603` | InternalError | Unhandled exception |
| `-32800` | Conflict | Optimistic concurrency mtime mismatch |
| `-32801` | NotFound | Board file ENOENT |

**OTel wrapping** (server.ts:234-239): every `tools/call` is wrapped in `withToolSpan(toolName, impl, id, method)` → exports spans via OTLP HTTP (per `package.json:58`).

**Tool-to-handler map** (server.ts:45-59):
```
TOOL_HANDLERS (Zod parsers): board_list, board_tasks_get, board_tasks_update, board_tasks_create, board_tasks_delete
TOOL_IMPL    (executors):    same five keys
```

---

## Gateway routing match matrix

**Config:** `C:/Users/mathe/code_space/apps/mcp-gateway/config/gateways.yaml:1-16`

Three backends declared:

| Backend | cwd | Command | Tool prefixes |
|---------|-----|---------|---------------|
| `tuiboard` | `C:/Users/mathe/code_space/apps/kanban/tuiboard` | `bun run src/bin/tuiboard.ts --mcp` | `board_` |
| `taskdog` | `C:/Users/mathe/code_space/apps/dev-tools/taskdog` | `python -m taskdog_mcp.main` | `taskdog_`, plus exact: `list_tasks`, `get_task`, `create_task`, `update_task`, `delete_task`, `archive_task`, `restore_task` |
| `solverforge-calendar` | `C:/Users/mathe/code_space/apps/calendar/solverforge-calendar` | `cargo run --bin solverforge-calendar-mcp` | `calendars_`, `events_`, `projects_`, `dependencies_`, `google_`, `upi_` |

**Router** (`apps/mcp-gateway/src/mcp_gateway/router.py:4-25`):
- prefixes ending in `_` → `prefix_map` (`startswith` match)
- exact tokens → `exact_map`
- FALLBACK: any unmatched tool routes to `solverforge-calendar` (router.py:24)

**Matrix for `board_*` (5 tuiboard tools):**

| Tool name | Exposed by tuiboard MCP? | Router path | Backend hit |
|-----------|--------------------------|-------------|-------------|
| `board_list` | YES (`server.ts:64-72`) | `prefix_map["board_"]` → "tuiboard" (router.py:10, 19-22) | tuiboard |
| `board_tasks_get` | YES (`server.ts:74-86`) | matches `board_` prefix | tuiboard |
| `board_tasks_update` | YES (`server.ts:88-118`) | matches `board_` prefix | tuiboard |
| `board_tasks_create` | YES (`server.ts:120-147`) | matches `board_` prefix | tuiboard |
| `board_tasks_delete` | YES (`server.ts:149-161`) | matches `board_` prefix | tuiboard |

**Cross-prefix collisions checked:**
- `taskdog_` exact-list does not contain any `board_*` token → no clash
- solverforge prefixes (`calendars_`, `events_`, `projects_`, `dependencies_`, `google_`, `upi_`) — none start with `board_`
- No collision possible: every `board_*` tool MUST route to tuiboard

**Conclusion:** All 5 `board_*` tools declared in `getToolList()` are correctly routed. The gateways.yaml:4 cwd path is MISSING (Phase 1 B-01 finding); fork actually lives at `life-oss/interfaces/tuiboard/` per reorg. Until repointed, the gateway will fail to launch the tuiboard backend on `start_all()` (`apps/mcp-gateway/src/mcp_gateway/process_manager.py:17-19`).

**Process manager behaviour** (process_manager.py:21-35):
- `_start_with_restart` wraps `client.start()` + `rpc("initialize", ...)` then `await asyncio.sleep(1)` in a loop
- Crashed backends auto-restart after `restart_delay` (default 5s)
- `send()` (37-43) raises `RuntimeError` if backend is not running (EOFError)

---

## Persistence story

**Layer 1 — Atomic file write** (`src/io/writer.ts:54-83`):
- Strategy: write to `.<filename>.tuiboard-<pid>-<ts>.tmp` → `renameSync` over original
- On Windows: `renameSync` maps to `MoveFileExW(MOVEFILE_REPLACE_EXISTING)` (writer.ts:13-17)
- mtime conflict check BEFORE rename: `Math.abs(cur - expectedMtimeMs) > 1` → `ConflictError`
- Tolerance 1ms covers coarse-mtime filesystems (NTFS, FAT)

**Layer 2 — Round-trip serializer** (`src/parser/serialize.ts`): invoked from `saveBoard` (store/index.ts:399) and `mutateAndWrite` (board-io.ts:46). Round-trip fidelity enforced by `bun run roundtrip:check` (`package.json:47`).

**Layer 3 — File watcher** (`src/io/watcher.ts:32-85`):
- chokidar `persistent: true`, `awaitWriteFinish: { stabilityThreshold: 80, pollInterval: 30 }` (watcher.ts:60-62)
- Debounce 150ms (default) — coalesces editor save bursts
- `markSelfWrite(path)` adds to a `Set` + auto-clears after 1000ms (watcher.ts:79-83)

**Layer 4 — In-store self-write guard** (store/index.ts:309-336):
- `lastWrittenContent: Map<string,string>` caches exact bytes we wrote
- On watcher event, `if (lastWrittenContent.get(filepath) === content) return` — byte-identical guard survives Obsidian/vault-sync re-saving identical content with a fresh mtime
- Real external edit → re-parse, swap `board` + `mtimeMs`, `setState("rev", r+1)`, banner "Reloaded … after external edit"

**Layer 5 — Conflict recovery** (store/index.ts:415-439):
- On `ConflictError` from `saveBoard`: flash warning banner, re-read file, swap in-memory state, leave the in-flight mutation lost
- The MCP tool path (`board-io.ts:48-51`) DOES NOT auto-recover — it surfaces the conflict back to the caller as `-32800 Conflict`

**Caches (calendar only):**
- `~/.config/tuiboard/cal_cache/<source>_<date>.json` (calendar.ts:49)
- TTL 30 minutes (CACHE_TTL_MS, calendar.ts:50)
- `calendarStore.refresh(true)` (store/index.ts:964) bypasses cache for manual `r` key

**NO app-level persistence** for UI state. State is in-memory; SIGINT tears down the store via `dispose()` (`store/index.ts:1285-1289`) which closes watcher + agents + calendar.

---

## Trade-offs

**1. Single-store + produce vs separate signals.** All reactive state lives in one `createStore` (store/index.ts:268-287). Mutations use `produce()` (Solid proxy-mutation). Trade-off: cheaper fine-grained updates than context-per-zone, but every mutation needs to bump the top-level `rev` counter because OpenTUI/Solid's deep-tracking misses nested children-array edits (see comments at store/index.ts:218-227, 255-260, 977-983).

**2. Round-trip markdown fidelity over a clean DOM.** `Task.rawBody` + `Task.rawLine` (types.ts:28-30) preserved verbatim so the serializer can rebuild on edit (`types.ts:5-9` doc-comment: "parsing is lossy by selection, not by destruction"). Trade-off: schema drift must be guarded by `bun run roundtrip:check` + extensive parser tests; unknown emoji / decorative content survive.

**3. Optimistic concurrency on writes.** MCP mutations require `expectedMtimeMs`; `writeBoardFile` rejects on mtime drift. Trade-off: client must always do a `board_tasks_get` first to fetch the mtime, then pass it back — no "fire and forget" updates. Local TUI mutations auto-bypass this (the watcher self-write guard is byte-level, not mtime-level).

**4. Stdio-only MCP transport.** No HTTP/SSE exposed. Trade-off: simple to wire into any agent, but `gateways.yaml` must spawn it as a child process per session (`process_manager.py:25`).

**5. Three layers of MCP coexistence.** (a) tuiboard's own stdio server (this fork), (b) gateway process-manager that spawns it (apps/mcp-gateway/src/mcp_gateway/process_manager.py:13-14), (c) Deep Agent stdio bridge mentioned in CLAUDE.md. Trade-off: explicit redundancy, but consistent tool name surface across both paths.

**6. Self-write guard belt-and-braces.** TWO mechanisms: `chokidar.awaitWriteFinish` + `selfWrites.delete()` in the watcher (watcher.ts:42), AND byte-identical content check in the store (store/index.ts:319). Trade-off: extra code, but survives Windows antivirus / Obsidian re-save quirks that mutate mtime without changing content.

**7. Zone architecture.** `enabledZones ∧ desiredVisible ∧ lastFits` triple AND (store/index.ts:261-266) means the same `applyResponsiveFits` call cannot accidentally show a zone the config has disabled, and the user can persist F-key intent across resizes. Trade-off: three boolean states per zone to keep in sync.

**8. Hard-coded layout constants.** `COL_WIDTH = 42` (BoardView.tsx:33), `AGENDA_WIDTH` (ui/layout.ts), `COL_GAP = 1` (BoardView.tsx:48). Trade-off: simpler to reason about than dynamic sizing, but resizing requires touching every component that references the constant.

**9. Inline keyboard dispatcher.** `handleKey.ts` is a 934-line single file with nested zone-specific handlers (`handlePlannerZone`, `handleTimelineZone`, `handleBoardZone`, `handleAgentsZone`) and a shared `dispatchTaskAction` (630-766). Trade-off: easy to scan per-key behaviour, but additions create "spooky action at a distance" — e.g. lowercase `c` was repurposed from clipboard to calendar arm mode (`dispatchTaskAction:680` notes the conflict with `Shift+C`).

**10. Two event-picker patterns.** Calendar arm mode (transient, `armedTimelineRef` per task) vs. persistent `armMode` flag for batch scheduling (store/index.ts:178-181). Trade-off: two concepts to teach the user, but they solve different ergonomic needs ("schedule this one task" vs. "schedule many in a row").

---

## Cross-references

- Phase 1 audit: `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` B-01 (gateways.yaml cwd paths MISSING)
- Phase 2 sister docs: `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md` (CLI), `05-interfaces-tui.md` (TUI overview), `03-fork-solverforge-calendar.md` (parallel fork audit)
- Original CLAUDE.md: `C:/Users/mathe/code_space/life-oss/interfaces/tuiboard/CLAUDE.md`
- Upstream: `github.com/NazzarenoGiannelli/tuiboard` v0.8.4 (`package.json:3`)
- Gateway config (Phase 1 finding B-01): `C:/Users/mathe/code_space/apps/mcp-gateway/config/gateways.yaml:1-16`
- Gateway router: `apps/mcp-gateway/src/mcp_gateway/router.py:4-25`
- Gateway process manager: `apps/mcp-gateway/src/mcp_gateway/process_manager.py:8-47`

Memory references:
- [[interfaces-architecture-2026-08-27]] — confirms tuiboard is a fork, not source-of-truth
- [[windows-orphan-dir-delete]] — used 2026-08-28 to clear `apps/kanban/tuiboard` (the OLD location Phase 1 B-01 says is missing)

Pitfalls noted:
- `server.ts:250` reports `version: "0.8.3"` while `package.json:3` says `0.8.4` — server version is stale (likely hand-edited).
- MCP server cannot be reached via `bin/tuiboard.ts --mcp` because `bin/tuiboard.ts` is the LAUNCHER (sets TUIBOARD_READY_FLAG, OpenTUI preload), not the MCP entry. MCP entry is `bin/tuiboard-mcp.ts:16` → `src/v3/mcp/server.ts`. The gateway command `["bun", "run", "src/bin/tuiboard.ts", "--mcp"]` is wrong — should be `["bun", "run", "bin/tuiboard-mcp.ts"]` or `["bun", "run", "src/v3/mcp/server.ts"]`. This is a Phase 2 finding beyond Phase 1 B-01.
- Transport helper `readRequest()` (`src/v3/mcp/transport.ts:28-61`) is dead — the server uses `node:readline` instead (server.ts:166). Dead code.
- `transport.ts:66-70` `readLine()` returns `null` with a "will be overridden" comment — also dead.
- MCP server `bin/tuiboard-mcp.ts:13-14` runs `initObservability()` BEFORE importing the server — OTel must init before any other module loads; this is correct but undocumented.
- `bin/tuiboard-mcp.ts:9` doc comment says "MUST NOT instantiate the Solid store, chokidar, or calendar fetchers" — but the v3 server imports `js-yaml` + `node:fs` + `node:path` directly and does not touch Solid. Compliance verified.
