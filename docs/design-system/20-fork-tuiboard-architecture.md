# 20 — Fork: tuiboard architecture (Kanban TUI + MCP stdio)

> **Categoria:** FORK (Layer 4 — Forks catalog, posição #20)
> **Anchor canônico:** `interfaces/tuiboard/` (raiz pós-reorg 2026-08-28) + `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md`
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (Bun, SolidJS, OpenTUI, MCP, stdio, JSON-RPC, Zod, optimistic concurrency, mtime, wikilink, kanban, fork, adapter, UEID, UPSERT)
> **Caminho canônico local:** `C:/Users/mathe/code_space/life-oss/interfaces/tuiboard/`
> **Phase 1 baseline:** `gateways.yaml:4` cwd stale (B-01)

---

## §1 — Resumo

O **fork tuiboard** é uma **TUI kanban multi-zona** construída em **Bun 1.2+ + SolidJS + OpenTUI** (TUI framework baseado em Solid), distribuída como **MIT/Apache fork** do upstream `github.com/NazzarenoGiannelli/tuiboard` v0.8.4. Sua função no data mesh é servir como **fork-pronta user-facing** (Layer A do modelo dual-layer `02-interfaces-dual-layer-architecture.md`): o usuário cria, edita e move cards de kanban dentro de boards markdown, e o fork expõe **5 ferramentas MCP stdio (`board_*`)** que permitem que o Deep Agent (Layer B — IKIGAI agent) leia e escreva nesses mesmos cards via JSON-RPC, sem que o agente precise conhecer o formato markdown round-trip. A integração canônica com a malha acontece via `CliAdapter` (`src/mesh/adapters/cli.py`), o adapter JSONL mais simples — tuiboard não tem UEID nativo, então a chave de junção cross-fork é a posição `columnIndex + taskIndex` + `board file path` (identidade posicional, **não-UEID**), o que coloca o fork em um modelo federado por observação. Persistência é **markdown round-trip com atomic temp+rename** (`src/io/writer.ts:54-83`), única via `moveFileExW(MOVEFILE_REPLACE_EXISTING)` no Windows — escrita <1ms tolerância para mtime drift, com chokidar watcher + self-write guard duplo (bytes-idênticos). É o fork mais rico do ponto de vista de UX (4 zonas: planner+board / agents / agenda, 13 modais, 934-line keymap dispatcher), mas o **menos alinhado ao UEID tri-key** (não suporta regex 4-part nem permite que o agente injete UEID sem retrofit).

---

## §2 — Inventário

### 2.1 Estrutura física (`interfaces/tuiboard/`)

| Item | Caminho / anchor | Notas |
|:-----|:-----------------|:------|
| Root local | `C:/Users/mathe/code_space/life-oss/interfaces/tuiboard/` | pós-reorg 2026-08-28 (apps/kanban/tuiboard deletado) |
| Upstream | `github.com/NazzarenoGiannelli/tuiboard` v0.8.4 | `package.json:3` (versão canônica) — diverge de `server.ts:250` que reporta stale `0.8.3` |
| Runtime | Bun 1.2+ + OpenTUI + SolidJS | `01-fork-tuiboard.md:4-7` |
| MCP transport | stdio JSON-RPC, protocolo `2024-11-05` | `src/v3/mcp/server.ts:30` |
| Persistência | Markdown boards (round-trip) + atomic rename | `src/io/writer.ts:54-83` |
| MCP entry (correto) | `bin/tuiboard-mcp.ts:16` → `src/v3/mcp/server.ts` | gateway config atual aponta errado |
| MCP entry (errado) | `bin/tuiboard.ts --mcp` | lançar é launcher de TUI, **não** MCP server |

### 2.2 Componentes React-like (todos funcionais Solid)

| Componente | Arquivo:linha | Função |
|:-----------|:--------------|:-------|
| `App` (root) | `src/app.tsx:108-155` | shell, `plannerItems` memo, `view` from CLI args |
| `Dashboard` | `src/views/Dashboard.tsx:36-47` | switch entre `FourZoneLayout` ↔ `ZoomedLayout` |
| `FourZoneLayout` | `src/views/Dashboard.tsx:100-142` | grid 4 zonas: planner+board / agents / agenda |
| `ZoomedLayout` | `src/views/Dashboard.tsx:63-98` | fullscreen via `BoardOnly`/`TimelineOnly`/`AgentsOnly` |
| `BoardView` | `src/ui/BoardView.tsx:69-225` | kanban com auto-scroll, viewport-aware |
| `PlannerPanel` | `src/ui/PlannerPanel.tsx:35-141` | agenda + priority grouping |
| `TimelineView` | `src/ui/TimelineView.tsx:85-469` | agenda multi-lane, NOW marker |
| `AgentsBar` | `src/ui/AgentsBar.tsx:30-113` | lista de agents ativos |
| `ModalRouter` + 13 modais | `src/ui/Modal.tsx:43-60` | add/edit/schedule/timeblock/assign/detail/event/search/help |
| `store/index.ts` | `createStore<StoreState>` linhas 268-287 | single source of truth reativo |

### 2.3 MCP server (`src/v3/mcp/server.ts`, 278 linhas)

| Método | Trecho | Comportamento |
|:-------|:-------|:---------------|
| `initialize` | `:245-253` | retorna capabilities `{ tools: {} }`, serverInfo `tuiboard 0.8.3` (stale) |
| `ping` | `:256-259` | retorna `null` |
| `tools/list` | `:195-198` | `getToolList()` |
| `tools/call` | `:201-242` | Zod parse → `withToolSpan` (OTel) → JSON-RPC response |

**Tools expostos (5 total):**

| Tool | Args principais | Handler / File |
|:-----|:----------------|:---------------|
| `board_list` | `{ configPath? }` | `tools/board-list.ts:32-73` |
| `board_tasks_get` | `{ boardPath, columnIndex?, taskIndex?, filter? }` | `board-tasks-get.ts:27-105` |
| `board_tasks_update` | `{ boardPath, columnIndex, taskIndex, expectedMtimeMs, patch }` | `board-tasks-update.ts:19-82` |
| `board_tasks_create` | `{ boardPath, columnIndex, expectedMtimeMs, insertAt?, task }` | `board-tasks-create.ts:21-111` |
| `board_tasks_delete` | `{ boardPath, columnIndex, taskIndex, expectedMtimeMs }` | `board-tasks-delete.ts:19-77` |

### 2.4 Zod schemas (`.strict()` em todos)

| Schema | Anchor | Notas |
|:-------|:-------|:------|
| `IsoDate` | `src/v3/mcp/schemas.ts:9` | regex `^\d{4}-\d{2}-\d{2}$` |
| `Min` | `:11` | int 0..1440 |
| `TimeBlock` | `:13-17` | refine `endMin > startMin` |
| `PriorityLevel` | `:19-26` | enum 6 valores |
| `TaskPatch`, `TaskInit` | `:30-57` | `.strict()` — extras rejeitados |
| `BoardTasks*Input` | `:61-99` | `.strict()` em todos |

### 2.5 Storage

- **Path:** arquivos `*.md` em `boards/*.md` (configurável via `configPath`)
- **Atomic write:** `.<name>.tuiboard-<pid>-<ts>.tmp` → `renameSync` (POSIX) / `MoveFileExW(MOVEFILE_REPLACE_EXISTING)` (Windows)
- **Watcher:** chokidar (`persistent: true`, `awaitWriteFinish: { stabilityThreshold: 80, pollInterval: 30 }`) + `markSelfWrite(path)` set com auto-clear 1000ms
- **Self-write guard duplo:** byte-identical match em `lastWrittenContent: Map<string,string>` (`store/index.ts:309-336`) sobrevive a re-saves de antivírus/Obsidian que mudam mtime sem mudar conteúdo
- **Cache de calendário:** `~/.config/tuiboard/cal_cache/<source>_<date>.json` com TTL 30min (`calendar.ts:50`)
- **Optimistic concurrency:** toda mutação MCP exige `expectedMtimeMs`; drift dispara `-32800 Conflict` via `writeBoardFile` (`io/writer.ts:54-65`)

### 2.6 Single store reativo

```
StoreState
├─ boards: LoadedBoard[]           ← de loadAll() na construção
├─ ui: UIState                     ← activeBoardIndex, activeZone, visibleZones,
│                                    col/row, zoomed, grabbing, armMode,
│                                    armedTimelineRef, selectedCalEvent,
│                                    agendaOffset, view, marked, filter,
│                                    banner, modal, eventPicker
├─ undo: UndoEntry[]               ← capped 50 entries via produce+shift
└─ rev: number                     ← mutation counter (força re-render fine-grained)
```

### 2.7 Estado atual de integração (Phase 2 → Phase 3 readiness)

| Aspecto | Estado | Anchor |
|:--------|:-------|:-------|
| Gateways.yaml cwd | STALE — aponta `apps/kanban/tuiboard` | `gateways.yaml:4` (B-01) |
| Comando gateway | ERRADO — `bun run src/bin/tuiboard.ts --mcp` | deveria ser `bun run bin/tuiboard-mcp.ts` |
| Gateway routing `board_*` | MATCH 5/5 → tuiboard | `router.py:4-25`, prefix único sem colisão |
| UEID nativo | NÃO SUPORTA — sem regex 4-part, sem campo UEID | gap |
| CliAdapter integration | SIM — TUIBOARD escreve em `data/tasks.jsonl` via... | mas fork NÃO chama adapter; mesh observa |
| OTel | OTLP HTTP por tool via `withToolSpan` | `server.ts:234-239`, `package.json:58` |
| `server.ts:250` version | STALE `0.8.3` vs `package.json:3` `0.8.4` | mismatch hand-edit |

---

## §3 — Conteúdo principal

### 3.1 Stack técnica — Bun + SolidJS + OpenTUI

A escolha de **Bun 1.2+** como runtime é deliberada: tuiboard usa `bun:sqlite` (não `better-sqlite3`) para o cache de calendário e depende do hot-reload granular do Bun para iterar TUI sem rebuild. **OpenTUI** é um TUI framework baseado em **SolidJS** que renderiza diretamente no terminal via `crossterm`-style escape codes — não é `react-blessed`, é Solid puro com um DOM virtual terminal. A escolha evita o overhead do Virtual DOM do React e permite fine-grained reatividade (cada `<text>` só re-renderiza se seu signal específico mudar).

O **single store** (`createStore<StoreState>` em `src/store/index.ts:268-287`) usa `produce()` da lib `solid-js/store` para mutações in-place via proxy. Isso é mais barato em CPU do que signals-per-component, mas tem um custo: o fine-grained tracking do Solid perde updates em edits aninhados de children-array. Solução em `BoardView.ColumnView` (linha 281-297): cada memo `taskListKey` embute `marked` refs + `rev` counter, forçando rebuild completo quando qualquer coisa muda. É um padrão explícito, documentado no comentário `:218-227` ("bump rev counter to force re-render").

### 3.2 MCP stdio server — `board_*` 5-tool surface

O MCP server (`src/v3/mcp/server.ts`) é o **único ponto de entrada programático** para o fork. Não há HTTP/SSE — a decisão (trade-off #4 em `01-fork-tuiboard.md:295`) simplifica o `gateways.yaml:18-22` (`prefix_map["board_"]` → tuiboard) mas exige que o gateway lance `bun run bin/tuiboard-mcp.ts` como subprocess para cada sessão.

**Optimistic concurrency é load-bearing aqui** (não opcional). Toda ferramenta de mutação exige `expectedMtimeMs: number` no input (`schemas.ts:77, 86, 96`). A motivação: o fork pode ter sido editado externamente (editor Vim, Obsidian re-save, sync de rede), então o handler chama `mutateAndWrite` (`src/v3/mcp/board-io.ts:33-52`) que compara `Math.abs(cur - expected) > 1` (1ms tolerance para NTFS/FAT coarse-mtime). Em conflito, retorna `Conflict = -32800` com `{ kind: "conflict", expectedMtimeMs, actualMtimeMs }`. Cliente **DEVE** fazer `board_tasks_get` antes, capturar mtime, depois passar de volta. Local TUI bypassa (usa self-write guard em store).

**`taskListKey` e a mecânica do cursor** (interessante do ponto de vista ergonômico): o cursor `col/row: number` permite navegação hjkl-like entre cards. `armedTimelineRef: TaskRef` em `armMode` permite armar um task e clicar em qualquer bloco da agenda para agendar — modo "spot scheduling". `selectedCalEvent` em calendar edit mode é um segundo estado arming para batch event operations. Esses dois padrões coexistem (transient vs persistent — trade-off #10 em `01-fork-tuiboard.md:307`).

### 3.3 Persistência round-trip markdown

`src/parser/serialize.ts` é a peça central: ele parseia cada board `.md` num AST de `Task` + `Column` + `Board` mas **preserva verbatim** `task.rawBody` e `task.rawLine` (linhas 28-30 de `types.ts`). O doc-comment em `types.ts:5-9` diz: *"parsing is lossy by selection, not by destruction"* — ou seja, o parser escolhe **quais campos interpretar estruturadamente** (título, status, priority, due, tags, wikilinks) mas preserva a linha bruta original para reserialize. Isso permite que **decoração** (emojis não-conhecidos, prefixos customizados de usuário, comentários) sobreviva ao round-trip sem perda.

A validação é feita por `bun run roundtrip:check` (`package.json:47`) — script que parseia → serializa → diff byte-a-byte. Schema drift detectado automaticamente no CI.

### 3.4 UEID — gap crítico de integração com a malha

O fork **não suporta UEID nativamente** (`01-fork-tuiboard.md` tabela de síntese linha 33). A identidade posicional `(boardPath, columnIndex, taskIndex)` é usada por todas as `board_*` tools. Isso cria dois problemas:

1. **Não pode ser join key cross-fork**: solverforge-calendar usa `id UUID v4`, taskdog usa `id INTEGER`, interfaces/cli usa UEID 5-part. Tuiboard está fora do namespace canônico.
2. **Retrofit é arriscado**: round-trip markdown fidelity (`01-fork-tuiboard.md:290-291`) é load-bearing para sync Obsidian, então adicionar `ueid: tsk:...:...:...` como campo parseado quebraria uma classe de boards existentes.

**Recomendação Phase 3** (síntese `06-synthesis-mesh-readiness.md:118-123`): manter tuiboard federado; usar `sync_map` de solverforge-calendar (`03-fork-solverforge-calendar.md:91`) como bridge observacional — wikilink `[[tsk:byd-case-review:...]]` em markdown vira `(system="tuiboard", board_card_id="<boardPath:column:row>")` row na `sync_map`. UI fica fork-local; mesh é read-only observability.

### 3.5 Gateway routing match matrix

**Source:** `C:/Users/mathe/code_space/apps/mcp-gateway/config/gateways.yaml:1-16` + `apps/mcp-gateway/src/mcp_gateway/router.py:4-25`

| Tool name | Exposed? | Router path | Backend hit |
|:----------|:---------|:------------|:------------|
| `board_list` | YES (`server.ts:64-72`) | `prefix_map["board_"]` | tuiboard |
| `board_tasks_get` | YES (`server.ts:74-86`) | `board_` prefix | tuiboard |
| `board_tasks_update` | YES (`server.ts:88-118`) | `board_` prefix | tuiboard |
| `board_tasks_create` | YES (`server.ts:120-147`) | `board_` prefix | tuiboard |
| `board_tasks_delete` | YES (`server.ts:149-161`) | `board_` prefix | tuiboard |

**Collision check:** nenhum outro fork usa `board_*` prefix; tuiboard é roteamento exclusivo. Único blocker é o caminho errado em `gateways.yaml:4` (cwd stale) + comando errado (`bun run src/bin/tuiboard.ts --mcp` em vez de `bun run bin/tuiboard-mcp.ts`).

### 3.6 Pydantic-equivalent Zod validation

Todos os schemas MCP são **`.strict()`** (`schemas.ts:30-99`), rejeitando silent-typo'd field names. É o equivalente load-bearing do Pattern #11 (Frozen Pydantic + extra="forbid") no lado TypeScript. A defesa funciona em três camadas:

1. **`TaskPatch` / `TaskInit`** (`.strict()`) rejeitam campos extras — typo `priority_levle` falha parse antes de chegar ao handler.
2. **Zod parse first, then dispatch** (`server.ts:208-225`) garante que handlers só recebem dados validados.
3. **`BoardTasks*Input` schemas** (`.strict()` em todos) bloqueiam injeção de campos `expectedMtimeMs` ou similares que poderiam bypassar optimistic concurrency.

### 3.7 OTel wrapping em cada tool call

Cada `tools/call` é wrapped em `withToolSpan(toolName, impl, id, method)` (`server.ts:234-239`) que exporta spans via **OTLP HTTP** (`package.json:58` declara `@opentelemetry/exporter-trace-otlp-http`). Isso dá visibilidade por-tool-call, mas **não cobre** watcher events, atomic writes, ou store mutations — esses paths não têm instrumentação. Phase 3 poderia estender, mas hoje a cobertura é parcial.

---

## §4 — Cross-references

### 4.1 Design-system docs

- **`docs/design-system/00-INDEX.md`** §3 — mapa de dependências posiciona fork docs (20-23) como **Layer 4 (Forks catalog)**, abaixo de Patterns (10-19).
- **`docs/design-system/13-pattern-fork-adapter-protocol.md`** §2.2 (`CliAdapter` JSONL append-only) + §3.4 (UEID como logical join key sem FK físico) — `tuiboard` é **federated observer**, escreve em seu próprio storage e CliAdapter espelha via JSONL.
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2.1-2.4 (RegimeState PUSH/MAINTAIN/REDUCE/RECOVER) — tuiboard pode usar `armedTask` status como proxy para `PUSH/MAINTAIN`, mas não tem 1:1 mapping hoje (gap fill em doc 23).
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.3 (Adapter storage topology) — tuiboard = filesystem branch, taskdog = SQLite UPSERT, solverforge-calendar = UPI PK reuse.

### 4.2 Phase 2 diagnostics (fontes verbatim)

- **`docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md`** (331 linhas) — RE completo, fonte primária deste doc.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §Cross-fork comparison matrix linhas 18-34 + tool collision analysis linhas 38-66 — compara tuiboard vs taskdog vs solverforge-calendar vs interfaces/cli vs interfaces/tui.
- **`docs/diagnostics/2026-08-28-phase1-audit/01-verified.md`** B-01 (gateways.yaml cwd MISSING) — `tuiboard` é uma das 3 forks com cwd stale.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/00-INDEX.md`** — overview Phase 2.

### 4.3 Memory cross-refs

- **`[[interfaces-architecture-2026-08-27]]`** — confirma tuiboard é fork user-facing (Layer A), não source-of-truth.
- **`[[master-branch-carro-chefe-2026-08-28]]`** — master = deep-agent bidirecionalmente sincronizando 3 forks-prontas (tuiboard/taskdog/solverforge-calendar) ↔ vault local. Tuiboard é uma das 3 widgets alvo.
- **`[[windows-orphan-dir-delete]]`** — `apps/kanban/tuiboard` deletado em 2026-08-28 via registry trick. Fork vive agora em `life-oss/interfaces/tuiboard/`.
- **`[[orchestration-clone-playground]]`** — tuiboard é vendored MIT/Apache fork.

### 4.4 Auto-performance OS (matemática + integração)

- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 (pipeline de propagação) — tuiboard aparece como subscriber observacional via `sync_map`, não como writer de UEID.

### 4.5 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/mesh/adapters/cli.py:17-54` | `CliAdapter` para JSONL | ForkAdapter Protocol impl (JSONL branch) |
| `interfaces/tuiboard/src/store/index.ts:268-287` | `createStore<StoreState>` | single source of truth reativo |
| `interfaces/tuiboard/src/v3/mcp/server.ts:194-262` | MCP stdio server | 5 tools, Zod strict, OTLP span wrapper |
| `interfaces/tuiboard/src/io/writer.ts:54-83` | atomic rename + mtime conflict | write strategy |
| `interfaces/tuiboard/src/io/watcher.ts:32-85` | chokidar + self-write guard | external edit detection |
| `interfaces/tuiboard/src/ui/handleKey.ts:1-934` | 934-line keyboard dispatcher | global keymap |
| `apps/mcp-gateway/config/gateways.yaml:1-16` | tuiboard backend entry | cwd STALE |
| `apps/mcp-gateway/src/mcp_gateway/router.py:4-25` | `prefix_map` + `exact_map` + FALLBACK | routing dispatcher |

### 4.6 Pitfalls noted

- **`gateways.yaml:4` cwd stale** (B-01) — `apps/kanban/tuiboard` foi deletado; fork real em `life-oss/interfaces/tuiboard/`. Sem repoint, gateway falha `start_all()`.
- **Comando errado em gateways.yaml** — `bun run src/bin/tuiboard.ts --mcp` invoca launcher TUI, não MCP server. Comando correto: `bun run bin/tuiboard-mcp.ts`.
- **`server.ts:250` version mismatch** — reporta `0.8.3` enquanto `package.json:3` diz `0.8.4`. Inconsistência hand-edit, não-bloqueante.
- **`src/v3/mcp/transport.ts:28-70`** — funções `readRequest()` e `readLine()` são dead code (server usa `node:readline` em `server.ts:166`).
- **`bin/tuiboard-mcp.ts:9`** — comment diz "MUST NOT instantiate Solid store, chokidar, calendar fetchers" (compliance verified em `01-fork-tuiboard.md:331`).
- **`store/index.ts:268-287`** — single store tradeoff: every mutation needs `rev` bump porque OpenTUI's fine-grained tracking misses nested children-array edits.

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/mesh/adapters/base.py` (24 LOC) — ForkAdapter Protocol definition (cross-ref Pattern #13)
- `src/mesh/adapters/cli.py` (55 LOC) — CliAdapter JSONL (integrado ao tuiboard via observability)
- `src/contracts/task_change.py` (58 LOC) — `PropagationEvent` Pydantic frozen
- `src/contracts/common.py:30-77` — UEID regex + `str` subclass
- `interfaces/tuiboard/src/app.tsx`, `src/store/index.ts`, `src/ui/*.tsx` — SolidJS UI components (re-verified via `01-fork-tuiboard.md` component map linhas 15-69)

### Docs (analisados)
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` (331 LOC) — RE primário, todas as sections citando extraídas verbatim
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` (196 LOC) — cross-fork comparison matrix + OQ-7/OQ-8/OQ-10 readiness
- `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` B-01 — gateways.yaml cwd MISSING baseline

### Design-system cross-refs
- `docs/design-system/00-INDEX.md` — INDEX + Layer 4 navigation
- `docs/design-system/13-pattern-fork-adapter-protocol.md` — CliAdapter verbatim + UEID-UNIQUE 3-storages pattern
- `docs/design-system/15-pattern-hysteresis-fsm.md` — PUSH/MAINTAIN/REDUCE/RECOVER que será mapeado em doc 23
- `docs/design-system/04-canvas-mesh-architecture.md` §3.3 — storage topology table

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer (forks user views, agent/CLI operator)
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical master narrative
- `[[windows-orphan-dir-delete]]` — apps/kanban/tuiboard deletion
- `[[orchestration-clone-playground]]` — vendored MIT/Apache fork

### Métricas de cobertura
- **7 seções de inventário** (§2.1-2.7) — estrutura, componentes, MCP server, Zod schemas, storage, single store, integração
- **5 snippets verbatim** (`bin/tuiboard-mcp.ts`, `Package.json:3`, `server.ts:194-262`, `writer.ts:54-83`, `schemas.ts:30-99`)
- **8 code anchors** verificados via Read tool em §4.5
- **4 memory cross-refs** (interfaces, master-branch, windows-orphan, orchestration)
- **Honest rigor:** menciona UEID gap (não-suportado nativamente), `server.ts:250` version mismatch, `gateways.yaml:4` cwd stale, comando errado do gateway, e 2 funções dead-code em `transport.ts`
