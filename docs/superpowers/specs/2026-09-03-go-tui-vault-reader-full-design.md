# Go TUI Vault Reader — Comprehensive Design (Full Breakdown)

> **Status:** DESIGN — captured 2026-09-03 for future implementation, NO code yet
> **Verdict:** DEFERRED per `/btw` (single-user local system); trigger conditions in §27
> **Companion:** lightweight summary at `2026-09-03-go-tui-rewrite-deferred.md`
> **Audience:** future implementer (you, in 6+ months) reading from cold start

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Architecture Overview](#3-architecture-overview)
4. [Project Structure](#4-project-structure)
5. [Build System & Toolchain](#5-build-system--toolchain)
6. [Core TUI Engine — Bubble Tea Model/Update/View](#6-core-tui-engine--bubble-tea-modelupdateview)
7. [Vault Tree — Glow Integration](#7-vault-tree--glow-integration)
8. [Cobra CLI Surface](#8-cobra-cli-surface)
9. [Filesystem Watching — fsnotify](#9-filesystem-watching--fsnotify)
10. [Python Backend IPC (HTTP + SSE)](#10-python-backend-ipc-http--sse)
11. [Configuration System](#11-configuration-system)
12. [State Management & Persistence](#12-state-management--persistence)
13. [Error Handling & Recovery](#13-error-handling--recovery)
14. [Logging & Observability](#14-logging--observability)
15. [Testing Strategy](#15-testing-strategy)
16. [Build, Release & Distribution](#16-build-release--distribution)
17. [Security](#17-security)
18. [Performance](#18-performance)
19. [Accessibility](#19-accessibility)
20. [i18n / pt-BR Native Support](#20-i18n--pt-br-native-support)
21. [Theme System](#21-theme-system)
22. [Key Bindings & Input Modes](#22-keybindings--input-modes)
23. [Plugin System (Extensibility)](#23-plugin-system-extensibility)
24. [Search & Filter](#24-search--filter)
25. [Multi-Fork Coordination](#25-multi-fork-coordination)
26. [Migration from Python TUI](#26-migration-from-python-tui)
27. [Trigger Conditions for Revival](#27-trigger-conditions-for-revival)
28. [Verification Matrix](#28-verification-matrix)
29. [Edge Cases & Failure Modes](#29-edge-cases--failure-modes)
30. [Future Extensions](#30-future-extensions)

---

## 1. Executive Summary

**One-liner:** A Go rewrite of the operator TUI (`interfaces/tui/operator/`) that adds native vault markdown rendering (Glow), filesystem push updates (fsnotify), and a single static binary distribution — replacing 250 LOC of Python polling with a feature-rich, cross-platform TUI client to the Python MCP backend.

**Why:** current Python TUI is functional but lacks the vault tree viewer (the only feature that genuinely wins with Go/Glow), uses polling instead of push updates, and requires a Python venv to run.

**Why deferred:** single-user local system → static binary advantage is theoretical; CLI + skills cover 95% of daily use; 2-language drift cost > Glow vault rendering benefit.

**Compass:** when this spec gets revived, the implementer should be able to start coding with zero follow-up design questions. Every subsystem below is concrete enough to implement.

---

## 2. Goals & Non-Goals

### Goals (P0 — must ship in v1)

- **G1.** Render `vault/**/*.md` natively in TUI using Glow
- **G2.** Push-based filesystem updates (fsnotify) replacing 5s polling
- **G3.** Single static binary — no Python runtime, no venv
- **G4.** Cross-platform Win/Mac/Linux via `go build`
- **G5.** Cobra CLI surface mirroring `life v2 cycle|score|regime` Typer commands
- **G6.** HTTP+SSE IPC with Python `UnifiedMCPGateway` (no Go deep-agent SDK)
- **G7.** TUI tabs for Adapters / Backend / Queue (port from Python)
- **G8.** Production-grade error handling — no crashes on backend disconnect, vault corruption, or invalid config

### Non-Goals (forever out of scope)

- **NG1.** Replace Python Deep Agent harness — Python is canonical per attribution §7
- **NG2.** Replace `vault_write` MCP — sole vault writer invariant
- **NG3.** Replace `IKIGAI_TOOLS` MCP server — 15 tools, drift detector enforced
- **NG4.** Replace data mesh adapters — Python stays
- **NG5.** Add new dependencies beyond Charm stack + Cobra + fsnotify + BoltDB

### Future Goals (v2+, deferred until v1 ships)

- **F1.** Multi-window support (split panes)
- **F2.** Plugin system for custom commands
- **F3.** Theme marketplace
- **F4.** Telemetry export (OpenTelemetry)
- **F5.** Native installer (msi/dmg/deb)

---

## 3. Architecture Overview

### High-level diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Go TUI Binary (static)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Bubble Tea │  │   Glow       │  │   Cobra CLI    │  │
│  │   TUI Engine │←→│   Renderer   │  │   Interface    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
│         │                 │                    │            │
│  ┌──────▼─────────────────▼────────────────────▼──────┐   │
│  │              Domain Layer (pure logic)               │   │
│  │  vault tree · fork state · task model · filter     │   │
│  └──────┬──────────────────────────────────────────────┘   │
│         │                                                    │
│  ┌──────▼───────┐  ┌─────────────┐  ┌────────────────┐    │
│  │   fsnotify   │  │   BoltDB    │  │   HTTP/SSE     │    │
│  │   Watcher    │  │   Cache     │  │   Client       │    │
│  └──────────────┘  └─────────────┘  └────────┬───────┘    │
└──────────────────────────────────────────────┼────────────┘
                                                │
                          ┌─────────────────────▼───────────┐
                          │   Python UnifiedMCPGateway       │
                          │   (localhost:8765 HTTP + SSE)    │
                          │   15 MCP tools · vault_write     │
                          └───────────────────────────────────┘
```

### Layering rules

| Layer | Allowed imports | Forbidden imports |
|------|-----------------|-------------------|
| `cmd/` | `internal/*`, standard library | domain logic inline |
| `internal/tui/` | `internal/domain/`, Bubble Tea | HTTP client, fsnotify direct |
| `internal/domain/` | standard library only | Bubble Tea, HTTP, fsnotify |
| `internal/vault/` | `internal/domain/`, Glow | TUI types |
| `internal/ipc/` | standard library, JSON | Bubble Tea, vault tree |
| `internal/fswatch/` | fsnotify, standard library | anything else |
| `internal/persist/` | BoltDB, standard library | anything else |

**Rule:** pure domain logic (testable without I/O), I/O at the edges.

### Component responsibilities

| Component | Responsibility | LOC budget |
|-----------|---------------|------------|
| `cmd/operator/main.go` | entrypoint, flag parsing, mode dispatch | 100 |
| `cmd/operator/cli.go` | Cobra root + subcommands | 200 |
| `internal/tui/` | Bubble Tea program, models, views | 1500 |
| `internal/tui/components/` | reusable widgets (tree, table, log) | 800 |
| `internal/vault/` | Glow wrapper, markdown rendering | 300 |
| `internal/domain/` | pure types + functions | 600 |
| `internal/ipc/` | HTTP/SSE client, request/response types | 500 |
| `internal/fswatch/` | fsnotify wrapper, debounce, event types | 200 |
| `internal/persist/` | BoltDB wrapper, schema | 300 |
| `internal/config/` | config loader, validation | 250 |
| `internal/observ/` | structured logger, metrics | 150 |
| **Total** | | **~5000 LOC** |

---

## 4. Project Structure

```
go-tui/
├── cmd/
│   └── operator/
│       ├── main.go              # entrypoint
│       ├── cli.go               # Cobra root command
│       ├── cmd_cycle.go         # life v2 cycle subcommand
│       ├── cmd_score.go         # life v2 score subcommand
│       ├── cmd_regime.go        # life v2 regime subcommand
│       └── cmd_watch.go         # file watch utility
├── internal/
│   ├── tui/
│   │   ├── app.go               # root Bubble Tea model
│   │   ├── update.go            # Update() dispatcher
│   │   ├── view.go              # View() dispatcher
│   │   ├── keys.go              # keymap
│   │   ├── tabs.go              # tab container
│   │   ├── messages.go          # internal message types
│   │   └── components/
│   │       ├── tree.go          # vault tree widget
│   │       ├── viewer.go        # markdown viewer (Glow)
│   │       ├── logview.go       # log pane
│   │       ├── statusbar.go     # status bar
│   │       ├── tabs.go          # tab strip
│   │       ├── modal.go         # modal dialog
│   │       ├── table.go         # tabular widget
│   │       ├── list.go          # scrollable list
│   │       └── spinner.go       # loading indicator
│   ├── domain/
│   │   ├── vault.go             # VaultNode, VaultTree types
│   │   ├── task.go              # Task model (mirrors contracts/task.py)
│   │   ├── fork.go              # ForkAdapter port
│   │   ├── filter.go            # filter AST + eval
│   │   └── errors.go            # domain error types
│   ├── vault/
│   │   ├── tree.go              # vault tree builder
│   │   ├── render.go            # Glow wrapper
│   │   ├── search.go            # grep/ripgrep integration
│   │   └── frontmatter.go       # YAML frontmatter parser
│   ├── ipc/
│   │   ├── client.go            # HTTP client (POST /call)
│   │   ├── sse.go               # SSE consumer
│   │   ├── retry.go             # exponential backoff
│   │   ├── health.go            # /health polling
│   │   └── types.go             # Request/Response DTOs
│   ├── fswatch/
│   │   ├── watcher.go           # fsnotify wrapper
│   │   ├── debounce.go          # event coalescing
│   │   └── filter.go            # ignore patterns (.gitignore-style)
│   ├── persist/
│   │   ├── bolt.go              # BoltDB wrapper
│   │   ├── schema.go            # bucket schema
│   │   ├── migrations.go        # schema versioning
│   │   └── cache.go             # vault read cache
│   ├── config/
│   │   ├── loader.go            # TOML config + env vars
│   │   ├── schema.go            # config types
│   │   ├── defaults.go          # built-in defaults
│   │   └── validate.go          # validation
│   └── observ/
│       ├── logger.go            # structured logger (slog)
│       ├── metrics.go           # counters, histograms
│       └── trace.go             # OpenTelemetry optional
├── test/
│   ├── integration/             # E2E with Python backend
│   ├── fixtures/                # test vault trees
│   └── mocks/                   # mock IPC server
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CONFIG.md
│   ├── KEYBINDINGS.md
│   └── THEMES.md
├── scripts/
│   ├── build.sh                 # cross-compile script
│   ├── release.sh               # GitHub Actions local
│   └── lint.sh                  # golangci-lint runner
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── go.mod
├── go.sum
├── Makefile
├── README.md
├── LICENSE
└── CHANGELOG.md
```

### Naming conventions

- **Packages:** lowercase, single-word preferred (`vault`, `ipc`, `fswatch`)
- **Files:** snake_case (`vault_tree.go`, `http_client.go`)
- **Types:** PascalCase (`VaultNode`, `IPCClient`)
- **Functions:** PascalCase exported, camelCase unexported
- **Errors:** `ErrXxx` sentinel (`ErrVaultNotFound`)
- **Constants:** PascalCase or UPPER_SNAKE for enums (`SeverityHigh`)

---

## 5. Build System & Toolchain

### Go version

- **Minimum:** Go 1.22 (for `log/slog` stable, range-over-int, improved error wrapping)
- **Target:** Go 1.23 latest stable
- **Module path:** `github.com/matheusmendes720/ikigai-go-tui`

### Direct dependencies (v1)

| Module | Purpose | Version pin |
|--------|---------|-------------|
| `github.com/charmbracelet/bubbletea` | TUI framework | v1.x latest |
| `github.com/charmbracelet/bubbles` | UI components | v0.x latest |
| `github.com/charmbracelet/lipgloss` | styling | v1.x latest |
| `github.com/charmbracelet/glow` | markdown rendering | v2.x latest |
| `github.com/spf13/cobra` | CLI framework | v1.8.x |
| `github.com/fsnotify/fsnotify` | filesystem events | v1.7.x |
| `go.etcd.io/bbolt` | embedded KV store | v1.3.x |
| `github.com/BurntSushi/toml` | config parser | v1.x |
| `github.com/charmbracelet/log` | structured logging | v1.x |

### Indirect dependencies (auto-resolved)

- `github.com/yuin/goldmark` (Glow uses for markdown parsing)
- `github.com/alecthomas/chroma` (syntax highlighting)
- `golang.org/x/sys` (platform-specific)
- `google.golang.org/genproto` (SSE parsing)

**Rule:** NO new major dependencies after v1 without ADR. Lint rule: `go.mod` diff must be reviewed.

### Build targets

```bash
# Local dev
make build                    # → ./bin/operator
make run                      # ./bin/operator

# Cross-compile
make build-all                # all 3 OS × 2 arch (Win, Mac, Linux × amd64, arm64)
make build-linux-amd64        # single target
make build-darwin-arm64       # Apple Silicon
make build-windows-amd64.exe  # Windows

# Release
make release VERSION=0.1.0    # tag + GitHub release
```

### Makefile targets

```makefile
.PHONY: build test lint fmt vet run release

BINARY := operator
VERSION := $(shell git describe --tags --always --dirty)
LDFLAGS := -s -w -X main.version=$(VERSION)

build:
	go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY) ./cmd/operator

build-all:
	GOOS=linux  GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY)-linux-amd64      ./cmd/operator
	GOOS=linux  GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY)-linux-arm64      ./cmd/operator
	GOOS=darwin GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY)-darwin-amd64     ./cmd/operator
	GOOS=darwin GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY)-darwin-arm64     ./cmd/operator
	GOOS=windows GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY)-windows-amd64.exe ./cmd/operator
	GOOS=windows GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY)-windows-arm64.exe ./cmd/operator

test:
	go test ./... -race -timeout 60s

test-integration:
	go test ./test/integration/... -tags=integration -timeout 300s

lint:
	golangci-lint run --timeout 5m

fmt:
	gofmt -s -w .
	goimports -w .

vet:
	go vet ./...

run: build
	./bin/$(BINARY)

release:
	@./scripts/release.sh $(VERSION)
```

### CI pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.23'
      - run: go test ./... -race
      - uses: golangci/golangci-lint-action@v6
        with:
          version: v1.59
  test-matrix:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.23'
      - run: go test ./...
      - run: go build ./cmd/operator
```

### Release pipeline

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  release:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest,  archive: tar.gz
          - os: macos-latest,   archive: tar.gz
          - os: windows-latest, archive: zip
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
      - run: make build-all
      - uses: softprops/action-gh-release@v2
        with:
          files: bin/*
          generate_release_notes: true
```

---

## 6. Core TUI Engine — Bubble Tea Model/Update/View

### The Elm Architecture in Bubble Tea

Every screen implements three functions:
```go
type Model interface {
    Init() tea.Cmd
    Update(msg tea.Msg) (tea.Model, tea.Cmd)
    View() string
}
```

### Root app structure

```go
// internal/tui/app.go
package tui

type App struct {
    width, height int
    activeTab     TabIndex
    tabs          []Tab
    
    vaultTree   *vault.Tree
    viewer      vault.Viewer
    logger      *observ.Logger
    config      *config.Config
    
    // Subscriptions
    fsEvents    <-chan fswatch.Event
    sseEvents   <-chan ipc.SSEEvent
    tickEvents  <-chan time.Time
}

func New(cfg *config.Config, logger *observ.Logger) (*App, error) {
    // Wire fsnotify → fsEvents
    // Wire SSE consumer → sseEvents
    // Wire tick (1s status bar refresh) → tickEvents
    // Init vault tree builder
    return &App{...}, nil
}

func (a *App) Init() tea.Cmd {
    return tea.Batch(
        a.loadVaultTree(),
        a.spawnWatcher(),
        a.spawnSSE(),
        a.tickEvery(time.Second),
    )
}

func (a *App) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd
    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        a.width, a.height = msg.Width, msg.Height
    case tea.KeyMsg:
        cmd := a.handleKey(msg)
        if cmd != nil { cmds = append(cmds, cmd) }
    case fswatch.Event:
        cmd := a.handleFSEvent(msg)
        if cmd != nil { cmds = append(cmds, cmd) }
    case ipc.SSEEvent:
        cmd := a.handleSSEEvent(msg)
        if cmd != nil { cmds = append(cmds, cmd) }
    case vault.TreeLoadedMsg:
        a.vaultTree = msg.Tree
    case errorMsg:
        a.logger.Error("ui error", "err", msg.err)
    }
    return a, tea.Batch(cmds...)
}

func (a *App) View() string {
    if a.width == 0 { return "loading..." }
    return lipgloss.JoinVertical(0,
        a.tabs.View(),
        a.activeTab().View(),
        a.statusbar.View(),
    )
}
```

### Message types

```go
// internal/tui/messages.go
package tui

// Async results
type vaultTreeLoadedMsg struct{ Tree *vault.Tree }
type vaultRenderedMsg struct{ Content string }
type ipcResponseMsg struct{ Result ipc.Response }
type ipcErrorMsg struct{ Err error }

// Internal events
type fsEventMsg struct{ Event fswatch.Event }
type sseEventMsg struct{ Event ipc.SSEEvent }
type tickMsg struct{ Time time.Time }

// Error wrapper
type errorMsg struct{ err error }
func (e errorMsg) Error() string { return e.err.Error() }
```

### Key bindings (default)

```go
// internal/tui/keys.go
package tui

type keyMap struct {
    Quit       key.Binding
    Help       key.Binding
    Tab1       key.Binding  // Adapters
    Tab2       key.Binding  // Backend
    Tab3       key.Binding  // Queue
    Tab4       key.Binding  // Vault (extended)
    Tab5       key.Binding  // Logs
    Up         key.Binding
    Down       key.Binding
    Left       key.Binding
    Right      key.Binding
    Enter      key.Binding
    Esc        key.Binding
    Search     key.Binding
    Refresh    key.Binding
    Save       key.Binding
    Open       key.Binding
    NextTab    key.Binding
    PrevTab    key.Binding
}

var defaultKeys = keyMap{
    Quit:    key.NewBinding(key.WithKeys("ctrl+c"), key.WithHelp("ctrl+c", "quit")),
    Help:    key.NewBinding(key.WithKeys("?"),     key.WithHelp("?",     "help")),
    Tab1:    key.NewBinding(key.WithKeys("1"),     key.WithHelp("1",     "adapters")),
    Tab2:    key.NewBinding(key.WithKeys("2"),     key.WithHelp("2",     "backend")),
    Tab3:    key.NewBinding(key.WithKeys("3"),     key.WithHelp("3",     "queue")),
    Tab4:    key.NewBinding(key.WithKeys("4"),     key.WithHelp("4",     "vault")),
    Tab5:    key.NewBinding(key.WithKeys("5"),     key.WithHelp("5",     "logs")),
    NextTab: key.NewBinding(key.WithKeys("tab"),   key.WithHelp("tab",   "next tab")),
    PrevTab: key.NewBinding(key.WithKeys("shift+tab"), key.WithHelp("⇧tab", "prev tab")),
    Up:      key.NewBinding(key.WithKeys("up", "k"), key.WithHelp("↑/k",   "up")),
    Down:    key.NewBinding(key.WithKeys("down", "j"), key.WithHelp("↓/j", "down")),
    Search:  key.NewBinding(key.WithKeys("/"),     key.WithHelp("/",     "search")),
    Refresh: key.NewBinding(key.WithKeys("ctrl+r"), key.WithHelp("ctrl+r", "refresh")),
}
```

### Tab container

```go
// internal/tui/components/tabs.go
package components

type Tabs struct {
    titles []string
    active int
    width  int
}

func (t Tabs) View() string {
    var items []string
    for i, title := range t.titles {
        style := tabInactive
        if i == t.active {
            style = tabActive
        }
        items = append(items, style.Render(fmt.Sprintf(" %d %s ", i+1, title)))
    }
    return lipgloss.JoinHorizontal(0, items...)
}
```

### Component: vault tree widget

```go
// internal/tui/components/tree.go
package components

type Tree struct {
    root     *vault.TreeNode
    cursor   int
    expanded map[string]bool
    width    int
    height   int
    styles   TreeStyles
}

func (t *Tree) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "j", "down":  t.cursor++
        case "k", "up":    t.cursor--
        case "l", "right": t.expand()
        case "h", "left":  t.collapse()
        case "enter":      return t, t.select()
        }
    case vault.TreeReloadedMsg:
        t.root = msg.Tree
    }
    return t, nil
}

func (t *Tree) View() string {
    var rows []string
    t.flatten(t.root, 0, &rows)
    visible := rows[t.scrollOffset : min(t.scrollOffset+t.height, len(rows))]
    return lipgloss.JoinVertical(0, visible...)
}
```

---

## 7. Vault Tree — Glow Integration

### Architecture

```
Vault file tree (filesystem)
       ↓ walkdir + ignore
domain.VaultTree (pure)
       ↓ render
Glow markdown renderer (per-file)
       ↓ style
lipgloss.Style (terminal-aware)
       ↓ render
Bubble Tea string output
```

### Vault tree builder

```go
// internal/vault/tree.go
package vault

import (
    "io/fs"
    "path/filepath"
    "github.com/charmbracelet/glow/v2"
)

type TreeNode struct {
    Path     string
    Name     string
    IsDir    bool
    Children []*TreeNode
    Size     int64
    ModTime  time.Time
}

func BuildTree(root string, ignore IgnorePatterns) (*TreeNode, error) {
    info, err := os.Stat(root)
    if err != nil { return nil, err }
    root_node := &TreeNode{Path: root, Name: info.Name(), IsDir: info.IsDir()}
    if !info.IsDir() { return root_node, nil }
    
    err = filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
        if err != nil { return err }
        rel, _ := filepath.Rel(root, path)
        if ignore.Match(rel) { return filepath.SkipDir }
        // ... insert into tree
    })
    return root_node, err
}
```

### Ignore patterns

```go
// internal/vault/ignore.go
package vault

type IgnorePatterns struct {
    patterns []globPattern
}

func NewIgnorePatterns(rules []string) IgnorePatterns {
    // Compiles glob patterns from .gitignore-style lines
    // Supports: *, **, ?, negation (!), comments (#)
}

func (i IgnorePatterns) Match(path string) bool {
    // Returns true if path should be ignored
}
```

Default ignores:
- `.git/**`
- `node_modules/**`
- `__pycache__/**`
- `.venv/**`
- `*.swp`
- `*.tmp`
- `~$*` (Office lock files)
- `.DS_Store`

### Markdown rendering with Glow

```go
// internal/vault/render.go
package vault

import (
    "github.com/charmbracelet/glow/v2"
    "github.com/charmbracelet/glow/v2/utils"
    "github.com/charmbracelet/glamour"
)

type Renderer struct {
    style   glamour.TermRenderer
    glamourTheme string
}

func NewRenderer(width int, theme string) (*Renderer, error) {
    s, err := glamour.NewTermRenderer(
        glamour.WithStylePath(theme),
        glamour.WithWordWrap(width),
    )
    if err != nil { return nil, err }
    return &Renderer{style: s}, nil
}

func (r *Renderer) Render(markdown []byte) (string, error) {
    return r.style.Render(string(markdown))
}

func (r *Renderer) SetWidth(w int) error {
    return r.style.SetWordWrap(w)
}
```

### Frontmatter parsing

```go
// internal/vault/frontmatter.go
package vault

import "gopkg.in/yaml.v3"

type Frontmatter struct {
    Title    string                 `yaml:"title"`
    Date     time.Time              `yaml:"date"`
    Tags     []string               `yaml:"tags"`
    Status   string                 `yaml:"status"`
    UEID     string                 `yaml:"ueid"`
    Custom   map[string]interface{} `yaml:",inline"`
}

type ParsedFile struct {
    Frontmatter *Frontmatter
    Body        string
}

func ParseFile(path string) (*ParsedFile, error) {
    raw, err := os.ReadFile(path)
    if err != nil { return nil, err }
    
    if !bytes.HasPrefix(raw, []byte("---\n")) {
        return &ParsedFile{Body: string(raw)}, nil
    }
    
    parts := bytes.SplitN(raw[4:], []byte("\n---\n"), 2)
    if len(parts) != 2 {
        return &ParsedFile{Body: string(raw)}, nil  // malformed, treat as plain
    }
    
    var fm Frontmatter
    if err := yaml.Unmarshal(parts[0], &fm); err != nil {
        return nil, fmt.Errorf("frontmatter parse: %w", err)
    }
    return &ParsedFile{Frontmatter: &fm, Body: string(parts[1])}, nil
}
```

### Vault search (grep integration)

```go
// internal/vault/search.go
package vault

type SearchResult struct {
    Path    string
    Line    int
    Column  int
    Content string
    Context []string  // ±2 lines
}

type Searcher struct {
    rgPath string  // ripgrep binary, fallback to internal
}

func (s *Searcher) Search(root, query string, opts SearchOptions) ([]SearchResult, error) {
    if s.rgPath != "" {
        return s.searchWithRipgrep(root, query, opts)
    }
    return s.searchInternal(root, query, opts)
}
```

Uses `os/exec` to call `rg` if available; falls back to in-process Aho-Corasick for environments without ripgrep.

---

## 8. Cobra CLI Surface

### Root command

```go
// cmd/operator/cli.go
package main

import "github.com/spf13/cobra"

var rootCmd = &cobra.Command{
    Use:   "operator",
    Short: "IKIGAI operator TUI and CLI",
    Long:  "Operator interface to the IKIGAI MCP gateway. TUI mode for interactive use, subcommands for scripts.",
    Version: version,
}

func init() {
    rootCmd.PersistentFlags().StringP("config", "c", "", "config file (default $XDG_CONFIG_HOME/operator/config.toml)")
    rootCmd.PersistentFlags().String("log-level", "info", "log level: debug|info|warn|error")
    rootCmd.PersistentFlags().String("gateway", "http://127.0.0.1:8765", "MCP gateway URL")
    
    rootCmd.AddCommand(cycleCmd, scoreCmd, regimeCmd, tuiCmd, versionCmd)
}
```

### Subcommand: `cycle`

```go
// cmd/operator/cmd_cycle.go
var cycleCmd = &cobra.Command{
    Use:   "cycle",
    Short: "Run an IKIGAI planning cycle",
    Args:  cobra.NoArgs,
    RunE: func(cmd *cobra.Command, args []string) error {
        client := ipc.NewClient(gatewayURL())
        defer client.Close()
        
        result, err := client.Call(cmd.Context(), "ikigai_run_cycle", map[string]interface{}{
            "thread": threadFlag,
            "human_in_the_loop": humanFlag,
        })
        if err != nil { return err }
        return json.NewEncoder(cmd.OutOrStdout()).Encode(result)
    },
}
```

### Subcommand: `score`

```go
// cmd/operator/cmd_score.go
var scoreCmd = &cobra.Command{
    Use:   "score",
    Short: "Observe IKIGAI scoring (PAV-written, read-only)",
    Args:  cobra.NoArgs,
    RunE: func(cmd *cobra.Command, args []string) error {
        client := ipc.NewClient(gatewayURL())
        result, err := client.Call(cmd.Context(), "ikigai_score", map[string]interface{}{
            "date": dateFlag,
        })
        if err != nil { return err }
        return json.NewEncoder(cmd.OutOrStdout()).Encode(result)
    },
}
```

### Subcommand: `tui`

```go
// cmd/operator/cmd_tui.go
var tuiCmd = &cobra.Command{
    Use:   "tui",
    Short: "Launch interactive TUI",
    Args:  cobra.NoArgs,
    RunE: func(cmd *cobra.Command, args []string) error {
        cfg, err := config.Load(configFlag)
        if err != nil { return err }
        logger := observ.NewLogger(logLevelFlag)
        
        app, err := tui.New(cfg, logger)
        if err != nil { return err }
        
        p := tea.NewProgram(app, tea.WithAltScreen(), tea.WithMouseCellMotion())
        return p.Start()
    },
}
```

### Flag conventions

| Flag | Short | Type | Default | Purpose |
|------|-------|------|---------|---------|
| `--config` | `-c` | string | XDG path | config file |
| `--log-level` | | string | info | log verbosity |
| `--gateway` | | string | localhost:8765 | MCP gateway URL |
| `--vault-root` | | string | ./vault | vault directory |
| `--theme` | | string | auto | color theme |
| `--json` | | bool | false | JSON output (for scripting) |
| `--no-color` | | bool | false | disable color |

---

## 9. Filesystem Watching — fsnotify

### Watcher

```go
// internal/fswatch/watcher.go
package fswatch

import "github.com/fsnotify/fsnotify"

type Event struct {
    Path      string
    Op        Op
    Timestamp time.Time
    Size      int64
}

type Op uint8

const (
    Create Op = 1 << iota
    Modify
    Remove
    Rename
    Chmod
)

type Watcher struct {
    fs        *fsnotify.Watcher
    out       chan Event
    root      string
    ignore    IgnorePatterns
    debouncer *Debouncer
}

func New(root string, ignore IgnorePatterns) (*Watcher, error) {
    fs, err := fsnotify.NewWatcher()
    if err != nil { return nil, err }
    
    w := &Watcher{
        fs: fs, root: root, ignore: ignore,
        out: make(chan Event, 1024),
        debouncer: NewDebouncer(100 * time.Millisecond),
    }
    
    if err := w.addRecursive(root); err != nil {
        fs.Close()
        return nil, err
    }
    
    go w.run()
    return w, nil
}

func (w *Watcher) Events() <-chan Event { return w.out }
func (w *Watcher) Close() error { return w.fs.Close() }

func (w *Watcher) run() {
    for {
        select {
        case ev, ok := <-w.fs.Events:
            if !ok { return }
            if w.ignore.Match(ev.Name) { continue }
            w.debouncer.Push(convert(ev))
        case err, ok := <-w.fs.Errors:
            if !ok { return }
            // log error, don't crash
        case ev := <-w.debouncer.Out():
            select {
            case w.out <- ev:
            default:  // drop if buffer full
            }
        }
    }
}
```

### Debouncing

```go
// internal/fswatch/debounce.go
package fswatch

type Debouncer struct {
    window time.Duration
    pending map[string]Event  // path -> latest event
    out chan Event
    mu sync.Mutex
    timer *time.Timer
}

func NewDebouncer(window time.Duration) *Debouncer {
    d := &Debouncer{
        window: window,
        pending: make(map[string]Event),
        out: make(chan Event, 256),
    }
    go d.run()
    return d
}

func (d *Debouncer) Push(ev Event) {
    d.mu.Lock()
    d.pending[ev.Path] = ev
    if d.timer != nil { d.timer.Stop() }
    d.timer = time.AfterFunc(d.window, d.flush)
    d.mu.Unlock()
}

func (d *Debouncer) flush() {
    d.mu.Lock()
    defer d.mu.Unlock()
    for _, ev := range d.pending {
        select {
        case d.out <- ev:
        default:
        }
    }
    d.pending = make(map[string]Event)
}

func (d *Debouncer) Out() <-chan Event { return d.out }
```

### Why debouncing

Text editors (vim, vscode) emit 10+ filesystem events per save (write tmp, rename, chmod). We coalesce to 1 event per save within the window.

---

## 10. Python Backend IPC (HTTP + SSE)

### Wire protocol

The Go TUI talks to Python `UnifiedMCPGateway` via HTTP POST + SSE.

**Request:**
```json
POST /call HTTP/1.1
Content-Type: application/json
{
    "namespace": "ikigai",
    "tool": "ikigai_score",
    "arguments": {"date": "2026-09-03"}
}
```

**Response (regular tool):**
```json
HTTP/1.1 200 OK
Content-Type: application/json
{
    "result": {
        "score_vec": {...},
        "meta_vector": 0.71,
        "rationale": "..."
    }
}
```

**Response (long-running, SSE):**
```
HTTP/1.1 200 OK
Content-Type: text/event-stream

event: progress
data: {"step": "score_vectors", "complete": false}

event: progress
data: {"step": "commit", "complete": true}

event: done
data: {"result": {...}}
```

### Client

```go
// internal/ipc/client.go
package ipc

type Client struct {
    baseURL string
    http    *http.Client
    health  chan HealthStatus
}

func NewClient(baseURL string) *Client {
    return &Client{
        baseURL: baseURL,
        http: &http.Client{
            Timeout: 30 * time.Second,
        },
        health: make(chan HealthStatus, 8),
    }
}

type Response struct {
    Result json.RawMessage `json:"result"`
    Error  *ResponseError  `json:"error,omitempty"`
}

type ResponseError struct {
    Code    string `json:"code"`
    Message string `json:"message"`
}

func (c *Client) Call(ctx context.Context, tool string, args map[string]interface{}) (*Response, error) {
    body, _ := json.Marshal(map[string]interface{}{
        "namespace": "ikigai",
        "tool": tool,
        "arguments": args,
    })
    req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/call", bytes.NewReader(body))
    if err != nil { return nil, err }
    req.Header.Set("Content-Type", "application/json")
    
    resp, err := c.http.Do(req)
    if err != nil { return nil, err }
    defer resp.Body.Close()
    
    if resp.StatusCode != 200 {
        return nil, fmt.Errorf("gateway returned %d", resp.StatusCode)
    }
    
    var out Response
    if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
        return nil, err
    }
    return &out, nil
}
```

### SSE consumer

```go
// internal/ipc/sse.go
package ipc

type SSEEvent struct {
    Event string
    Data  json.RawMessage
}

func (c *Client) Subscribe(ctx context.Context, topics []string) (<-chan SSEEvent, error) {
    body, _ := json.Marshal(map[string]interface{}{"topics": topics})
    req, _ := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/subscribe", bytes.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Accept", "text/event-stream")
    
    resp, err := c.http.Do(req)
    if err != nil { return nil, err }
    
    out := make(chan SSEEvent, 64)
    go func() {
        defer close(out)
        defer resp.Body.Close()
        scanner := bufio.NewScanner(resp.Body)
        var event, data string
        for scanner.Scan() {
            line := scanner.Text()
            switch {
            case strings.HasPrefix(line, "event: "):
                event = strings.TrimPrefix(line, "event: ")
            case strings.HasPrefix(line, "data: "):
                data = strings.TrimPrefix(line, "data: ")
            case line == "":
                if data != "" {
                    select {
                    case out <- SSEEvent{Event: event, Data: json.RawMessage(data)}:
                    case <-ctx.Done(): return
                    }
                    event, data = "", ""
                }
            }
        }
    }()
    return out, nil
}
```

### Retry with exponential backoff

```go
// internal/ipc/retry.go
package ipc

func (c *Client) CallWithRetry(ctx context.Context, tool string, args map[string]interface{}, maxAttempts int) (*Response, error) {
    var lastErr error
    backoff := 100 * time.Millisecond
    
    for attempt := 1; attempt <= maxAttempts; attempt++ {
        resp, err := c.Call(ctx, tool, args)
        if err == nil { return resp, nil }
        lastErr = err
        
        if !isRetryable(err) {
            return nil, err
        }
        
        select {
        case <-ctx.Done(): return nil, ctx.Err()
        case <-time.After(backoff):
        }
        backoff = min(backoff*2, 5*time.Second)
    }
    return nil, fmt.Errorf("max retries exceeded: %w", lastErr)
}

func isRetryable(err error) bool {
    // Network errors, 5xx, timeout: retry
    // 4xx (except 408, 429): no retry
    var netErr net.Error
    if errors.As(err, &netErr) && netErr.Timeout() { return true }
    return strings.Contains(err.Error(), "502") || strings.Contains(err.Error(), "503")
}
```

### Health monitoring

```go
// internal/ipc/health.go
package ipc

type HealthStatus int

const (
    HealthUnknown HealthStatus = iota
    HealthOK
    HealthDegraded
    HealthDown
)

func (c *Client) MonitorHealth(ctx context.Context) <-chan HealthStatus {
    out := make(chan HealthStatus, 8)
    go func() {
        defer close(out)
        for {
            select {
            case <-ctx.Done(): return
            default:
            }
            
            status := c.probeHealth(ctx)
            select {
            case out <- status:
            case <-ctx.Done(): return
            }
            time.Sleep(5 * time.Second)
        }
    }()
    return out
}

func (c *Client) probeHealth(ctx context.Context) HealthStatus {
    req, _ := http.NewRequestWithContext(ctx, "GET", c.baseURL+"/health", nil)
    resp, err := c.http.Do(req)
    if err != nil { return HealthDown }
    defer resp.Body.Close()
    if resp.StatusCode == 200 { return HealthOK }
    if resp.StatusCode >= 500 { return HealthDown }
    return HealthDegraded
}
```

---

## 11. Configuration System

### Format: TOML

```toml
# ~/.config/operator/config.toml or $XDG_CONFIG_HOME/operator/config.toml

[gateway]
url = "http://127.0.0.1:8765"
health_interval_seconds = 5
request_timeout_seconds = 30
max_retries = 3

[vault]
root = "./vault"
ignore = [".git/**", "node_modules/**", "__pycache__/**", ".venv/**", "*.swp", "*.tmp"]
debounce_ms = 100

[ui]
theme = "auto"                    # auto, light, dark, solarized, monokai, dracula
mouse_enabled = true
tab_bar_position = "top"          # top, bottom, hidden
status_bar_visible = true

[logging]
level = "info"                    # debug, info, warn, error
file = ""                         # empty = stderr
max_size_mb = 10
max_backups = 3

[persistence]
db_path = "~/.local/share/operator/state.db"
cache_size_mb = 50

[keybindings]
profile = "default"               # default, vim, emacs
custom = { "ctrl+s" = "save" }    # user overrides
```

### Loader

```go
// internal/config/loader.go
package config

type Config struct {
    Gateway    GatewayConfig    `toml:"gateway"`
    Vault      VaultConfig      `toml:"vault"`
    UI         UIConfig         `toml:"ui"`
    Logging    LoggingConfig    `toml:"logging"`
    Persistence PersistenceConfig `toml:"persistence"`
    Keybindings KeybindingsConfig `toml:"keybindings"`
}

func Load(path string) (*Config, error) {
    cfg := DefaultConfig()
    
    // Layer 1: defaults (built-in)
    // Layer 2: TOML file (if exists)
    if path != "" {
        if _, err := os.Stat(path); err == nil {
            if err := loadTOML(path, cfg); err != nil { return nil, err }
        }
    }
    
    // Layer 3: env vars (OPERATOR_GATEWAY_URL, etc.)
    loadEnv(cfg)
    
    // Layer 4: CLI flags (caller merges after Load)
    
    // Validate
    if err := cfg.Validate(); err != nil { return nil, err }
    return cfg, nil
}
```

### Env var mapping

| Env var | Config field |
|---------|--------------|
| `OPERATOR_GATEWAY_URL` | `gateway.url` |
| `OPERATOR_VAULT_ROOT` | `vault.root` |
| `OPERATOR_THEME` | `ui.theme` |
| `OPERATOR_LOG_LEVEL` | `logging.level` |
| `OPERATOR_CONFIG` | (file path) |
| `NO_COLOR` | (force no color) |

### Defaults

```go
func DefaultConfig() *Config {
    return &Config{
        Gateway: GatewayConfig{
            URL:                    "http://127.0.0.1:8765",
            HealthIntervalSeconds:  5,
            RequestTimeoutSeconds:  30,
            MaxRetries:             3,
        },
        Vault: VaultConfig{
            Root:       "./vault",
            Ignore:     []string{".git/**", "node_modules/**", "__pycache__/**", ".venv/**", "*.swp", "*.tmp"},
            DebounceMs: 100,
        },
        UI: UIConfig{
            Theme:           "auto",
            MouseEnabled:    true,
            TabBarPosition:  "top",
            StatusBarVisible: true,
        },
        Logging: LoggingConfig{
            Level:      "info",
            MaxSizeMB:  10,
            MaxBackups: 3,
        },
        Persistence: PersistenceConfig{
            DBPath:     "~/.local/share/operator/state.db",
            CacheSizeMB: 50,
        },
        Keybindings: KeybindingsConfig{Profile: "default"},
    }
}
```

### Validation

```go
func (c *Config) Validate() error {
    if c.Gateway.URL == "" { return ErrEmptyGateway }
    if _, err := url.Parse(c.Gateway.URL); err != nil { return ErrInvalidGatewayURL }
    if c.Vault.Root == "" { return ErrEmptyVaultRoot }
    if _, err := os.Stat(c.Vault.Root); err != nil { return ErrVaultNotFound }
    if c.Logging.Level != "" && !validLogLevels[c.Logging.Level] { return ErrInvalidLogLevel }
    return nil
}
```

---

## 12. State Management & Persistence

### What to persist

| Key | Type | Purpose | TTL |
|-----|------|---------|-----|
| `vault_cache:<path>` | bytes | rendered markdown cache | invalidate on fs change |
| `recent_files` | []string | recently opened | none |
| `tab_state` | json | per-tab UI state (cursor, filters) | none |
| `last_session` | json | last open file, tab, theme | none |
| `gateway_history` | []RequestLog | last N API calls | 1 day |
| `error_log` | []string | recent errors for `/diagnose` | 1 week |

### BoltDB schema

```
state.db (BoltDB)
├── bucket: vault_cache
│   ├── key: <sha256(path)> → bytes (rendered markdown)
├── bucket: vault_meta
│   ├── key: <sha256(path)> → json {mod_time, size, frontmatter}
├── bucket: recent
│   ├── key: 0..N → json {path, opened_at}
├── bucket: tabs
│   ├── key: <tab_name> → json {cursor, filter, scroll}
├── bucket: session
│   └── key: last → json {file, tab, theme}
├── bucket: gateway
│   ├── key: <request_id> → json {tool, args, result, latency_ms, timestamp}
└── bucket: errors
    └── key: <uuid> → json {time, level, msg, stack}
```

### Wrapper

```go
// internal/persist/bolt.go
package persist

type Store struct {
    db *bolt.DB
}

func Open(path string) (*Store, error) {
    db, err := bolt.Open(path, 0600, &bolt.Options{Timeout: 5 * time.Second})
    if err != nil { return nil, err }
    s := &Store{db: db}
    if err := s.migrate(); err != nil { db.Close(); return nil, err }
    return s, nil
}

func (s *Store) Close() error { return s.db.Close() }

// Generic key-value
func (s *Store) Put(bucket, key string, value []byte) error {
    return s.db.Update(func(tx *bolt.Tx) error {
        b, err := tx.CreateBucketIfNotExists([]byte(bucket))
        if err != nil { return err }
        return b.Put([]byte(key), value)
    })
}

func (s *Store) Get(bucket, key string) ([]byte, error) {
    var out []byte
    err := s.db.View(func(tx *bolt.Tx) error {
        b := tx.Bucket([]byte(bucket))
        if b == nil { return ErrBucketNotFound }
        out = b.Get([]byte(key))
        return nil
    })
    return out, err
}
```

### Schema migrations

```go
// internal/persist/migrations.go
package persist

const currentSchemaVersion = 3

var migrations = []Migration{
    {Version: 1, Up: func(tx *bolt.Tx) error { /* create buckets */ }},
    {Version: 2, Up: func(tx *bolt.Tx) error { /* add vault_meta */ }},
    {Version: 3, Up: func(tx *bolt.Tx) error { /* add recent */ }},
}

func (s *Store) migrate() error {
    return s.db.Update(func(tx *bolt.Tx) error {
        vb := tx.Bucket([]byte("_schema"))
        v := vb.Get([]byte("version"))
        current := 0
        if v != nil { current = binary.BigEndian.Uint32(v) }
        
        for _, m := range migrations {
            if m.Version <= current { continue }
            if err := m.Up(tx); err != nil { return err }
        }
        
        newV := make([]byte, 4)
        binary.BigEndian.PutUint32(newV, currentSchemaVersion)
        return vb.Put([]byte("version"), newV)
    })
}
```

### Cache eviction

```go
// LRU cache for rendered markdown
type renderCache struct {
    mu sync.RWMutex
    m map[string]*list.Element
    l *list.List
    cap int64
    size int64
}

func newRenderCache(maxBytes int64) *renderCache { ... }
func (c *renderCache) Get(key string) ([]byte, bool) { ... }
func (c *renderCache) Put(key string, value []byte) { ... }
```

---

## 13. Error Handling & Recovery

### Error hierarchy

```go
// internal/domain/errors.go
package domain

type Error struct {
    Kind    ErrorKind
    Message string
    Cause   error
    Context map[string]interface{}
}

type ErrorKind int

const (
    ErrUnknown ErrorKind = iota
    ErrNotFound
    ErrPermission
    ErrCorrupted
    ErrNetwork
    ErrTimeout
    ErrCancel
    ErrInvalidInput
    ErrBackendUnavailable
    ErrConfigInvalid
    ErrVersionMismatch
)

func (e *Error) Error() string { return e.Message }
func (e *Error) Unwrap() error { return e.Cause }
func (e *Error) Is(target error) bool { ... }
```

### Recovery strategies

| Error | Strategy |
|-------|----------|
| `ErrBackendUnavailable` | Show "gateway down" status bar; auto-retry on next call; never crash TUI |
| `ErrVaultNotFound` | First-run: create empty vault dir; show prompt to configure |
| `ErrCorrupted` | Show file with raw text + error message; don't crash |
| `ErrPermission` | Show clear message; suggest chmod; don't retry |
| `ErrNetwork` | Retry with backoff (3 attempts); then show error |
| `ErrConfigInvalid` | Fall back to defaults; show warning; continue |
| `ErrVersionMismatch` | Show "operator v1 requires gateway v2" message; exit gracefully |

### Graceful degradation

```go
// In update loop
case ipc.ResponseError:
    switch err.Kind {
    case ipc.ErrBackendDown:
        a.backendStatus = StatusDown
        a.logger.Warn("backend unavailable", "err", err)
        // Show in status bar, continue
    case ipc.ErrToolNotFound:
        a.flashError(fmt.Sprintf("tool %q not found", err.Tool))
    default:
        a.flashError(err.Error())
    }
    return a, nil  // NEVER propagate IPC errors as crashes
```

### Panic recovery

```go
func main() {
    defer func() {
        if r := recover(); r != nil {
            logger.Error("panic", "panic", r, "stack", debug.Stack())
            fmt.Fprintln(os.Stderr, "operator crashed:", r)
            fmt.Fprintln(os.Stderr, "logs at:", logPath)
            os.Exit(1)
        }
    }()
    
    code := run()
    os.Exit(code)
}

func run() int {
    // ... wire app, start TUI ...
    return 0
}
```

In Bubble Tea, errors are values not exceptions, so panics only happen in:
- library bugs
- out-of-memory
- nil derefs

Recovery must be robust but never hide real bugs.

---

## 14. Logging & Observability

### Structured logging with `log/slog`

```go
// internal/observ/logger.go
package observ

type Logger struct {
    slog *slog.Logger
}

func NewLogger(level, filePath string) (*Logger, error) {
    var w io.Writer = os.Stderr
    if filePath != "" {
        f, err := os.OpenFile(filePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
        if err != nil { return nil, err }
        w = f
    }
    
    var lvl slog.Level
    switch strings.ToLower(level) {
    case "debug": lvl = slog.LevelDebug
    case "info":  lvl = slog.LevelInfo
    case "warn":  lvl = slog.LevelWarn
    case "error": lvl = slog.LevelError
    }
    
    h := slog.NewJSONHandler(w, &slog.HandlerOptions{Level: lvl})
    return &Logger{slog: slog.New(h)}, nil
}

func (l *Logger) Info(msg string, args ...any) { l.slog.Info(msg, args...) }
func (l *Logger) Warn(msg string, args ...any) { l.slog.Warn(msg, args...) }
func (l *Logger) Error(msg string, args ...any) { l.slog.Error(msg, args...) }
func (l *Logger) Debug(msg string, args ...any) { l.slog.Debug(msg, args...) }
```

### Log rotation

```go
// Uses lumberjack for size-based rotation
import "gopkg.in/natefinch/lumberjack.v2"

func NewLogger(level, filePath string) (*Logger, error) {
    var w io.Writer
    if filePath == "" {
        w = os.Stderr
    } else {
        w = &lumberjack.Logger{
            Filename:   filePath,
            MaxSize:    10,   // MB
            MaxBackups: 3,
            MaxAge:     30,   // days
            Compress:   true,
        }
    }
    ...
}
```

### Metrics (basic, optional)

```go
// internal/observ/metrics.go
package observ

type Metrics struct {
    IPCRequests       *atomic.Int64
    IPCErrors         *atomic.Int64
    VaultRenders      *atomic.Int64
    FSWatcherEvents   *atomic.Int64
    CacheHits         *atomic.Int64
    CacheMisses       *atomic.Int64
    ActiveGoroutines  func() int
}

func (m *Metrics) Snapshot() map[string]int64 {
    return map[string]int64{
        "ipc_requests":      m.IPCRequests.Load(),
        "ipc_errors":        m.IPCErrors.Load(),
        "vault_renders":     m.VaultRenders.Load(),
        "fs_watcher_events": m.FSWatcherEvents.Load(),
        "cache_hits":        m.CacheHits.Load(),
        "cache_misses":      m.CacheMisses.Load(),
        "goroutines":        int64(m.ActiveGoroutines()),
    }
}
```

Exposed via `/diagnose` command in TUI.

### Debug mode

```bash
operator tui --log-level debug 2>debug.log
```

Debug logs include:
- every IPC request/response (truncated to 1KB)
- every fsnotify event (debounced)
- every cache hit/miss
- every renderer call (with timing)

---

## 15. Testing Strategy

### Test pyramid

```
       ╱╲
      ╱  ╲         E2E tests (real Python backend)
     ╱ 5% ╲        - 10 tests, runs in CI on schedule
    ╱──────╲
   ╱        ╲      Integration tests (mocks + real subsystems)
  ╱   25%    ╲     - 80 tests
 ╱────────────╲
╱              ╲   Unit tests (pure logic, no I/O)
╱     70%       ╲  - 500+ tests
╱────────────────╲
```

### Unit tests (domain layer, no I/O)

```go
// internal/domain/filter_test.go
package domain_test

func TestFilter_Eval(t *testing.T) {
    tests := []struct{
        expr string
        task domain.Task
        want bool
    }{
        {`tag == "revenue"`, taskWithTags("revenue"), true},
        {`priority > 3`, taskWithPriority(4), true},
        {`due < "2026-09-01"`, taskDue("2026-08-15"), true},
    }
    for _, tt := range tests {
        t.Run(tt.expr, func(t *testing.T) {
            f, err := domain.ParseFilter(tt.expr)
            if err != nil { t.Fatal(err) }
            if got := f.Eval(tt.task); got != tt.want {
                t.Errorf("got %v want %v", got, tt.want)
            }
        })
    }
}
```

### Integration tests (mock IPC server)

```go
// test/integration/cli_test.go
//go:build integration

func TestCLI_CycleCommand(t *testing.T) {
    srv := mocks.NewGatewayServer()
    srv.OnCall("ikigai_run_cycle", mock.AnyArgs).Return(ipc.Response{
        Result: json.RawMessage(`{"cycle_id": "c-123", "tasks_created": 5}`),
    })
    srv.Start(t)
    defer srv.Close()
    
    cmd := exec.Command("./bin/operator", "cycle", "--gateway", srv.URL())
    out, err := cmd.CombinedOutput()
    require.NoError(t, err)
    require.Contains(t, string(out), `"cycle_id": "c-123"`)
}
```

### E2E tests (real Python backend)

```go
//go:build e2e

func TestE2E_VaultTreeRenders(t *testing.T) {
    // Assumes Python MCP gateway running on :8765 with seed data
    requireEnv(t, "E2E_GATEWAY_URL")
    
    cfg := config.Load("")
    app := tui.New(cfg, observ.NoopLogger{})
    
    // Wait for vault tree to load
    deadline := time.Now().Add(10 * time.Second)
    for app.VaultTree() == nil && time.Now().Before(deadline) {
        time.Sleep(100 * time.Millisecond)
    }
    require.NotNil(t, app.VaultTree())
    require.Greater(t, app.VaultTree().Size(), 0)
}
```

### Snapshot tests (UI rendering)

```go
import "github.com/charmbracelet/x/exp/teatest"

func TestView_Tab1(t *testing.T) {
    app := setupTestApp()
    out := teatest.Run(t, app, teatest.WithInitialTermSize(120, 40))
    out.WaitFinished(t, teatest.WithFinalTimeout(3*time.Second))
    out.RequireEqualVisual(t, "testdata/tab1.golden")
}
```

### Test data

- **Vault fixtures:** `test/fixtures/vault/` — sample markdown tree with various frontmatter
- **IPC mocks:** `test/mocks/gateway.go` — mock HTTP server with predefined responses
- **Snapshot files:** `testdata/*.golden` — visual regression baselines

### Coverage targets

| Package | Target | Minimum |
|---------|--------|---------|
| `internal/domain/` | 90% | 85% |
| `internal/vault/` | 85% | 80% |
| `internal/ipc/` | 85% | 80% |
| `internal/fswatch/` | 80% | 75% |
| `internal/persist/` | 80% | 75% |
| `internal/config/` | 85% | 80% |
| `internal/tui/` | 70% | 65% |
| `cmd/operator/` | 70% | 60% |

### CI test runs

```yaml
# PR builds: unit + integration
go test ./... -race -timeout 60s
go test -tags=integration ./test/integration/... -timeout 120s

# Schedules (nightly): E2E
go test -tags=e2e ./test/e2e/... -timeout 300s
```

---

## 16. Build, Release & Distribution

### Cross-compile matrix

| Target | OS | Arch | Use case |
|--------|----|------|----------|
| `operator-linux-amd64` | Linux | amd64 | Linux dev |
| `operator-linux-arm64` | Linux | arm64 | Raspberry Pi, AWS Graviton |
| `operator-darwin-amd64` | macOS | amd64 | Intel Mac (legacy) |
| `operator-darwin-arm64` | macOS | arm64 | Apple Silicon (current) |
| `operator-windows-amd64.exe` | Windows | amd64 | Windows 11+ |
| `operator-windows-arm64.exe` | Windows | arm64 | Surface Pro X |

### Build optimizations

```bash
# Strip debug info, embed version
go build -ldflags="-s -w -X main.version=$(git describe)" -trimpath
```

- `-s -w` strips symbol table (~30% smaller)
- `-trimpath` removes filesystem paths from binary
- `-X` injects version string

### Distribution

- **GitHub Releases:** primary distribution channel
- **Homebrew tap:** `brew install matheusmendes720/tap/operator` (v2+)
- **Scoop bucket:** `scoop install operator` (Windows, v2+)
- **apt repo:** `apt install operator` (Linux, v3+)
- **Docker:** static scratch image (v3+)

### Checksums

```bash
# Generate SHA256 for each binary
sha256sum operator-* > SHA256SUMS
```

Users verify with:
```bash
sha256sum -c SHA256SUMS
```

### Signing (future, v2+)

- **macOS:** `codesign --sign "Developer ID" operator-darwin-arm64`
- **Windows:** Authenticode signing with cert
- **Linux:** GPG detached signatures

---

## 17. Security

### Threat model

| Threat | Mitigation |
|--------|------------|
| Malicious vault file (e.g., weird markdown) | Glow sandboxes rendering; no JS, no embedded HTML by default |
| Vault file path traversal (vault_root/../etc/passwd) | Resolve + check root; reject escape |
| IPC request injection (manipulated args) | Validate types at JSON decode; whitelist tool names |
| Config file injection | TOML parses strings, no eval; reject unknown fields |
| Network MITM (HTTP gateway) | Loopback-only default; require explicit `--allow-remote` for non-loopback |
| Local privilege escalation (setuid) | Never run setuid; refuse if effective UID != real UID |
| BoltDB corruption (power loss) | BoltDB is crash-safe by default (WAL) |
| Secrets in logs | Strip Authorization headers; redact vault content >10KB in debug |
| Replay attacks on SSE | Include timestamp + nonce; reject events >5min old |

### Local-only by default

```go
func (c *Config) Validate() error {
    u, _ := url.Parse(c.Gateway.URL)
    if u == nil { return ErrInvalidURL }
    
    // Block non-loopback unless explicit flag
    isLoopback := u.Hostname() == "localhost" || u.Hostname() == "127.0.0.1" || u.Hostname() == "::1"
    if !isLoopback && !c.AllowRemote {
        return fmt.Errorf("non-loopback gateway requires AllowRemote=true")
    }
    return nil
}
```

### Input validation

```go
// Vault path resolution
func resolveVaultPath(root, requested string) (string, error) {
    abs, err := filepath.Abs(filepath.Join(root, requested))
    if err != nil { return "", err }
    cleanRoot, _ := filepath.Abs(root)
    if !strings.HasPrefix(abs, cleanRoot) {
        return "", errors.New("path traversal attempt")
    }
    return abs, nil
}
```

### BoltDB permissions

```go
db, err := bolt.Open(path, 0600, ...)  // owner read/write only
```

### Secrets handling

- API keys (if any) read from env var only, never logged
- Config file mode 0600 (user-only)
- BoltDB file mode 0600

---

## 18. Performance

### Targets

| Metric | Target | Hard ceiling |
|--------|--------|--------------|
| Cold start (binary → TUI) | <100ms | <500ms |
| Vault tree load (10k files) | <500ms | <2s |
| Markdown render (10KB file) | <50ms | <200ms |
| fsnotify event → UI update | <150ms (debounced) | <500ms |
| IPC request round-trip | <50ms (loopback) | <5s timeout |
| Memory idle | <30MB | <80MB |
| Memory with 1000 file cache | <150MB | <500MB |

### Optimizations

#### Concurrent vault tree build
```go
func BuildTree(root string) (*TreeNode, error) {
    root_node := &TreeNode{Path: root, Name: filepath.Base(root)}
    var wg sync.WaitGroup
    sem := make(chan struct{}, 16)  // concurrency limit
    errs := make(chan error, 64)
    
    filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
        if err != nil { return err }
        rel, _ := filepath.Rel(root, path)
        if ignore.Match(rel) { return filepath.SkipDir }
        
        sem <- struct{}{}
        wg.Add(1)
        go func() {
            defer wg.Done()
            defer func() { <-sem }()
            info, err := d.Info()
            if err != nil { errs <- err; return }
            // ... insert into tree (needs lock)
        }()
        return nil
    })
    wg.Wait()
    close(errs)
    return root_node, nil
}
```

#### Render cache
```go
type renderCache struct {
    mu sync.RWMutex
    cache map[string]cachedRender
}

type cachedRender struct {
    markdown []byte
    rendered string
    mtime time.Time
}

func (c *renderCache) Get(path string, mtime time.Time) (string, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    e, ok := c.cache[path]
    if !ok || !e.mtime.Equal(mtime) { return "", false }
    return e.rendered, true
}
```

#### Lazy subtree expansion
```go
// Don't pre-render entire tree; render only visible nodes
type lazyNode struct {
    Path string
    expanded bool
    children []*lazyNode  // populated on expand
}

func (n *lazyNode) Expand() error {
    if n.expanded { return nil }
    // Walk dir, populate children
    n.expanded = true
    return nil
}
```

#### fsnotify coalescing
Already covered in §9. 100ms window prevents thrash.

### Profiling

```bash
# CPU profile
operator tui --cpuprofile=/tmp/cpu.prof
go tool pprof /tmp/cpu.prof

# Memory profile
operator tui --memprofile=/tmp/mem.prof
go tool pprof /tmp/mem.prof

# Trace
operator tui --trace=/tmp/trace.out
go tool trace /tmp/trace.out
```

---

## 19. Accessibility

### Standards

- **WCAG 2.2 AA** for terminal UI (modified for TTY context)
- **Screen reader support:** bubble tea doesn't have native SR; provide text-mode fallback
- **Color independence:** all information conveyed by color MUST also be conveyed by text/icon
- **Keyboard only:** every action MUST have a keyboard binding (no mouse-only)

### Screen reader mode (best effort)

```bash
operator tui --accessibility=sr
```

- Skip box-drawing characters
- Use text labels instead of icons
- Increase contrast
- Add aria-like hints: `[HEADING level=1] My Title`
- Verbose status messages

### Keyboard-only navigation

Every interaction has a key binding. Mouse is optional.

| Action | Binding | Mouse equivalent |
|--------|---------|------------------|
| Switch tab | `1`-`5` | Click tab |
| Move cursor | `j/k`, arrows | Click |
| Open file | `Enter` | Double-click |
| Back | `Esc` | n/a |
| Search | `/` | n/a |
| Quit | `ctrl+c`, `q` | n/a |

### Color independence

```go
// Instead of just red for errors:
fmt.Println("✗ " + red("error") + ": " + msg)
// Use:
fmt.Println("ERROR: " + msg)  // text label primary, color secondary
```

### High contrast mode

```toml
[ui]
high_contrast = true
```

Forces maximum-contrast colors (black on white or white on black), thicker borders.

### Reduced motion

```bash
operator tui --no-animations
```

Disables spinner, smooth-scroll, fade effects.

---

## 20. i18n / pt-BR Native Support

### Primary language: pt-BR

The user is Brazilian; vault content is mostly Portuguese. Native pt-BR in TUI strings (status bar, modals, help text) is mandatory.

### Message catalogs

```go
// internal/i18n/catalog.go
package i18n

type Catalog struct {
    translations map[string]map[string]string  // lang -> key -> text
}

var Default = Catalog{
    translations: map[string]map[string]string{
        "en": {
            "tab.adapters": "Adapters",
            "tab.backend":  "Backend",
            "tab.queue":    "Queue",
            "tab.vault":    "Vault",
            "tab.logs":     "Logs",
            "status.connecting": "Connecting to gateway...",
            "error.gateway_down": "Gateway unreachable. Retrying in %s.",
            "search.placeholder": "Type to search...",
            "help.title":    "Keyboard Shortcuts",
            "save.success":  "Saved %s",
        },
        "pt-BR": {
            "tab.adapters": "Adaptadores",
            "tab.backend":  "Backend",
            "tab.queue":    "Fila",
            "tab.vault":    "Cofre",
            "tab.logs":     "Logs",
            "status.connecting": "Conectando ao gateway...",
            "error.gateway_down": "Gateway indisponível. Tentando em %s.",
            "search.placeholder": "Digite para buscar...",
            "help.title":    "Atalhos de Teclado",
            "save.success":  "Salvo %s",
        },
    },
}

func (c Catalog) T(lang, key string, args ...interface{}) string {
    msgs, ok := c.translations[lang]
    if !ok { msgs = c.translations["en"] }
    text, ok := msgs[key]
    if !ok { return key }  // fallback to key
    return fmt.Sprintf(text, args...)
}
```

### Language detection

```go
func DetectLanguage() string {
    // 1. Config: ui.language
    // 2. Env: LANG, LC_ALL, LANGUAGE
    // 3. Default: "pt-BR"
    
    if cfg.UI.Language != "" { return cfg.UI.Language }
    
    for _, env := range []string{"LC_ALL", "LANG", "LANGUAGE"} {
        if v := os.Getenv(env); v != "" {
            if strings.HasPrefix(v, "pt") { return "pt-BR" }
            if strings.HasPrefix(v, "en") { return "en" }
        }
    }
    return "pt-BR"  // primary user language
}
```

### Configurable

```toml
[ui]
language = "pt-BR"  # pt-BR | en
```

### Future languages

v2+: Spanish (es), French (fr). Community contributions.

---

## 21. Theme System

### Built-in themes

| Theme | Background | Foreground | Accent |
|-------|-----------|------------|--------|
| `dark` (default) | #1a1a1a | #e0e0e0 | #7aa2f7 |
| `light` | #fafafa | #1a1a1a | #2e7de6 |
| `auto` | follows terminal | follows terminal | follows terminal |
| `solarized-dark` | #002b36 | #93a1a1 | #268bd2 |
| `solarized-light` | #fdf6e3 | #586e75 | #268bd2 |
| `monokai` | #272822 | #f8f8f2 | #a6e22e |
| `dracula` | #282a36 | #f8f8f2 | #bd93f9 |
| `gruvbox-dark` | #282828 | #ebdbb2 | #fabd2f |
| `nord` | #2e3440 | #d8dee9 | #88c0d0 |

### Theme structure

```go
// internal/ui/theme/theme.go
package theme

type Theme struct {
    Name       string
    Background lipgloss.AdaptiveColor
    Foreground lipgloss.AdaptiveColor
    Accent     lipgloss.AdaptiveColor
    Error      lipgloss.AdaptiveColor
    Warning    lipgloss.AdaptiveColor
    Success    lipgloss.AdaptiveColor
    Border     lipgloss.AdaptiveColor
    Muted      lipgloss.AdaptiveColor
    Highlight  lipgloss.AdaptiveColor
    
    Code map[string]string  // syntax highlight colors
}

func Load(name string) (*Theme, error) {
    switch name {
    case "auto":       return autoTheme(), nil
    case "dark":       return darkTheme(), nil
    // ... etc
    default:
        return loadCustomTheme(name)
    }
}
```

### Adaptive colors

```go
var autoBg = lipgloss.AdaptiveColor{
    Light: "#fafafa",
    Dark:  "#1a1a1a",
}
// Lipgloss picks based on terminal background
```

### Custom theme files

Users can place custom themes at:
- `~/.config/operator/themes/<name>.toml`
- Or `themes/<name>.toml` in vault

```toml
# themes/mycompany.toml
name = "mycompany"
[colors]
background = "#ffffff"
foreground = "#000000"
accent = "#ff5722"
error = "#f44336"
warning = "#ff9800"
success = "#4caf50"
```

---

## 22. Key Bindings & Input Modes

### Default profile

```toml
[keybindings.default]
quit       = "ctrl+c"
help       = "?"
tab_1      = "1"
tab_2      = "2"
tab_3      = "3"
tab_4      = "4"
tab_5      = "5"
next_tab   = "tab"
prev_tab   = "shift+tab"
up         = "up,k"
down       = "down,j"
left       = "left,h"
right      = "right,l"
enter      = "enter"
escape     = "esc"
search     = "/"
refresh    = "ctrl+r"
save       = "ctrl+s"
open       = "o"
new        = "n"
delete     = "d"
edit       = "e"
back       = "q,esc"
copy       = "y"
paste      = "p"
undo       = "u"
redo       = "ctrl+r"
```

### Vim profile

```toml
[keybindings.vim]
quit       = ":q"
help       = ":help"
search     = "/"
next_tab   = "gt"
prev_tab   = "gT"
up         = "k"
down       = "j"
left       = "h"
right      = "l"
enter      = "enter"
escape     = "esc"
refresh    = ":r"
save       = ":w"
open       = "o"
new        = "o"          # in tree view
back       = "q"
copy       = "y"
paste      = "p"
```

### Emacs profile

```toml
[keybindings.emacs]
quit       = "ctrl+x,ctrl+c"
up         = "ctrl+p"
down       = "ctrl+n"
left       = "ctrl+b"
right      = "ctrl+f"
enter      = "ctrl+m"
escape     = "ctrl+g"
search     = "ctrl+s"
save       = "ctrl+x,ctrl+s"
```

### Custom overrides

```toml
[keybindings.custom]
"ctrl+shift+s" = "save"
"alt+enter"    = "enter"
"f5"           = "refresh"
```

### Input modes

```go
type Mode int

const (
    ModeNormal Mode = iota
    ModeSearch
    ModeEdit
    ModeCommand  // vim-style
    ModeInsert   // vim-style
    ModeVisual   // vim-style
)

type keyHandler func(msg tea.KeyMsg) (tea.Model, tea.Cmd)

var handlers = map[Mode]keyHandler{
    ModeNormal: handleNormal,
    ModeSearch: handleSearch,
    ModeEdit:   handleEdit,
    ModeCommand: handleCommand,
    // ...
}
```

### Mouse support (optional)

```go
tea.WithMouseCellMotion()  // enable in main
```

Mouse events handled in component Update:
- Click → cursor move + select
- Double-click → enter
- Scroll → cursor move + view scroll

---

## 23. Plugin System (Extensibility)

### v1: built-in only

No external plugin support in v1. Simpler.

### v2: Go plugin system

```go
// Plugin interface
type Plugin interface {
    Name() string
    Version() string
    Init(ctx Context) error
    Commands() []Command
    Views() []View
    Keybindings() []Keybinding
}

// Load via Go's plugin package
import "plugin"

func LoadPlugin(path string) (Plugin, error) {
    p, err := plugin.Open(path)
    if err != nil { return nil, err }
    
    sym, err := p.Lookup("Plugin")
    if err != nil { return nil, err }
    
    return sym.(Plugin), nil
}
```

Use case: users build custom commands (e.g., `myorg-deploy`) that hook into the TUI.

### v3: WebAssembly plugins

More portable than Go plugins (no version skew). Plugins written in Rust, AssemblyScript, etc., compiled to WASM.

```go
import "github.com/tetratelabs/wazero"

func LoadWASMPPlugin(wasmBytes []byte) (Plugin, error) {
    ctx := context.Background()
    runtime := wazero.NewRuntime(ctx)
    
    _, err := runtime.InstantiateModule(ctx, wasmBytes, wazero.NewModuleConfig())
    if err != nil { return nil, err }
    
    // Export "register" function, call it to register plugin
}
```

**Defer to v3** — adds significant complexity.

---

## 24. Search & Filter

### Search modes

1. **Filename search** — `/` opens search box, fuzzy match on file names
2. **Content search** — `ctrl+f` opens content search, calls ripgrep
3. **Frontmatter filter** — `:` opens filter expression editor
4. **Tag filter** — `#` opens tag picker

### Filter expression language

```ebnf
expr  = or
or    = and ("||" and)*
and   = not ("&&" not)*
not   = "!" atom | atom
atom  = "(" expr ")" | comparison
comparison = field op value
field  = "tag" | "priority" | "status" | "due" | "title" | "path"
op     = "==" | "!=" | "<" | ">" | "<=" | ">=" | "~" | "in"
value  = string | number | date | list
```

Examples:
```
tag == "revenue" && priority >= 4
status == "open" || status == "in_progress"
due < "2026-09-01"
title ~ "BYD"
tag in ["revenue", "client"]
```

### Parser

```go
// internal/domain/filter.go
package domain

type FilterExpr interface {
    Eval(task Task) bool
    String() string
}

type OrExpr struct{ Left, Right FilterExpr }
type AndExpr struct{ Left, Right FilterExpr }
type NotExpr struct{ Inner FilterExpr }
type CompareExpr struct {
    Field string
    Op string
    Value interface{}
}

func ParseFilter(s string) (FilterExpr, error) { ... }
func (e OrExpr) Eval(t Task) bool { return e.Left.Eval(t) || e.Right.Eval(t) }
func (e CompareExpr) Eval(t Task) bool {
    switch e.Field {
    case "tag":
        return slices.Contains(t.Tags, e.Value.(string))
    case "priority":
        return compareInt(t.Priority, e.Op, e.Value.(int))
    // ...
    }
}
```

### Search UI

```
┌─ vault/ikigai/closing-2026/04-relatórios-diários/ ──────────┐
│ > /byd case                                              ✕  │
└──────────────────────────────────────────────────────────────┘
```

Incremental search (as-you-type), debounced 100ms.

### Results

```
12 matches in 8 files:
> vault/ikigai/closing-2026/04-relatórios-diários/2026-09-01.md
  L14: review BYD Camacari case study
  L42: - [ ] Send BYD case analysis
> vault/ikigai/closing-2026/01-q3-2026/plano-trimestral.md
  L8: BYD case deliverable D3
...
```

`Enter` to navigate to file+line. `Tab` to switch between filename/content search.

---

## 25. Multi-Fork Coordination

### The 4 forks

| Fork | Backend | Connection | TUI integration |
|------|---------|-----------|-----------------|
| CLI | `python -m life.cli` | subprocess + JSON-RPC | read-only view |
| taskdog | `taskdog.exe` (Rust) | HTTP + SSE | bidirectional |
| solverforge-calendar | `solverforge-calendar-cli.exe` | HTTP | read-only |
| tuiboard | `bun run tuiboard-mcp.ts` | JSON-RPC | read+write |

### Fork status indicators

```
┌─ Adapters ──────────────────────────────────────┐
│ CLI         [ONLINE]    12 tasks               │
│ taskdog     [ONLINE]    5 pending              │
│ solverforge [DEGRADED]  3 events (1 fail)     │
│ tuiboard    [OFFLINE]   -- (bun not found)     │
└────────────────────────────────────────────────┘
```

### Fork view

- Shows each fork's connection status, last sync time, queue depth
- Health ping every 5s
- Click a fork → drill into its events

### Cross-fork view (mesh)

```bash
operator mesh show <ueid>  # join task from all 4 forks
```

Output:
```
UEID: tsk:byd-case-review:abc12345:0123456789abcdef
┌─ CLI ──────────────────────────────────────────┐
│ Status: in_progress                           │
│ Updated: 2026-09-02 14:23                      │
└────────────────────────────────────────────────┘
┌─ taskdog ──────────────────────────────────────┐
│ ID: 42                                         │
│ Status: pending                                │
│ Project: BYD Case                              │
└────────────────────────────────────────────────┘
┌─ solverforge-calendar ──────────────────────────┐
│ UPI: tsk-42                                    │
│ Scheduled: 2026-09-05                          │
└────────────────────────────────────────────────┘
┌─ tuiboard ─────────────────────────────────────┐
│ Board: Projects                                │
│ Card: #42                                      │
└────────────────────────────────────────────────┘
```

### Fork adapters (Go side)

```go
// internal/adapters/cli.go
type CLIAdapter struct {
    binPath string
    cmd *exec.Cmd
}

func (a *CLIAdapter) Read(ueid string) (Task, error) {
    out, err := exec.Command(a.binPath, "show", ueid, "--json").Output()
    if err != nil { return Task{}, err }
    return parseTaskJSON(out)
}

// Similar for taskdog, solverforge-calendar, tuiboard
```

### Or just delegate to Python

Actually — for v1, fork reads go through Python `UnifiedMCPGateway` (single source of truth). Go doesn't talk to forks directly. This keeps fork logic in one place (Python).

```go
// Cross-fork view via Python
func (c *Client) MeshShow(ueid string) (MeshView, error) {
    resp, err := c.Call(ctx, "mesh_show", map[string]interface{}{"ueid": ueid})
    // ...
}
```

This simplifies Go side considerably.

---

## 26. Migration from Python TUI

### Coexistence phase (v1.0)

Both Python TUI and Go TUI coexist. Users choose.

```bash
life tui              # Python TUI (legacy)
operator tui           # Go TUI (new)
```

Python TUI gets SUPERSEDED trailer in `interfaces/tui/operator/README.md`.

### Feature parity gate

Before deprecating Python TUI, Go TUI MUST have:
- ✅ All 3 tabs functioning (Adapters, Backend, Queue)
- ✅ Equivalent key bindings (or documented migration map)
- ✅ Polling-based fallback (fsnotify → 5s poll if fsnotify fails)
- ✅ All CLI subcommands (`life v2 cycle|score|regime`) work via Go

### Deprecation phase (v1.1, ~3 months later)

1. Add deprecation warning to Python TUI
2. Python TUI shows banner: "use operator tui instead"
3. Python TUI launches Go TUI on startup unless `--keep-python` flag

### Removal phase (v2.0)

1. Python TUI archived
2. `interfaces/tui/operator/` moved to `archive/legacy-python-tui/`
3. `life tui` command delegates to `operator tui`

### Migration guide

Document at `docs/migration/python-tui-to-go-tui.md`:

```markdown
# Python TUI → Go TUI Migration Guide

## Command mapping

| Python | Go | Notes |
|--------|----|-----|
| `life tui` | `operator tui` | TUI launch |
| `life mesh show <ueid>` | `operator mesh show <ueid>` | now reads via Python gateway |
| `life v2 cycle` | `operator cycle` | |
| `life v2 score` | `operator score` | |

## Key binding changes

| Python | Go | Default |
|--------|----|-----|
| ctrl+q (quit) | ctrl+c | same |
| F1 (help) | ? | changed |
| tab (next) | tab | same |
| / (search) | / | same |

## New features

- Native vault markdown rendering (Glow)
- Push-based filesystem updates (fsnotify)
- Single static binary (no venv)
- pt-BR UI strings
- Search across file content (not just names)
```

---

## 27. Trigger Conditions for Revival

Reopen this spec when **ANY** of these become true:

1. **External user demo requirement** — someone outside this machine needs to install + run the system
2. **Vault tree viewer becomes daily-driver** — user navigates `vault/` 5+ times/day
3. **Cross-platform packaging pain** — `uv` install failures on Windows/Mac cost real time
4. **Python TUI proves inadequate** — Textual 5s polling causes user-visible lag
5. **Plugin system demand** — external contributors want to extend the TUI (Go plugins make this easier)
6. **Charm stack maturity** — Glow adds features we want (e.g., image embedding, table of contents nav)
7. **Distribution channel** — Homebrew tap or apt repo becomes viable

When triggered: re-read this spec → update Phase numbers → start with §5 build system.

---

## 28. Verification Matrix

### Unit tests

| Test | Command | Expected |
|------|---------|----------|
| Domain logic | `go test ./internal/domain/... -v` | 90%+ coverage |
| Filter parser | `go test ./internal/domain/ -run TestFilter` | pass |
| Tree builder | `go test ./internal/vault/ -run TestTree` | pass |
| IPC retry | `go test ./internal/ipc/ -run TestRetry` | pass |
| BoltDB schema | `go test ./internal/persist/ -run TestSchema` | pass |

### Integration tests

| Test | Command | Expected |
|------|---------|----------|
| CLI subcommands | `go test -tags=integration ./test/integration/...` | 80%+ pass |
| Mock gateway | `go test ./test/integration/... -run TestGateway` | pass |
| fsnotify → UI | `go test ./test/integration/... -run TestFSNotify` | pass |
| Config loading | `go test ./test/integration/... -run TestConfig` | pass |

### E2E tests (nightly)

| Test | Setup | Expected |
|------|-------|----------|
| Vault tree renders | real Python gateway + seed vault | tree shown |
| Cycle command | real Python gateway | cycle completes |
| Cross-platform build | 6 targets | all 6 binaries |
| Vault file edit → TUI update | vim edits vault | TUI updates within 200ms |

### Smoke tests (manual)

- Run `operator tui` → all 3 tabs visible
- Press `4` → vault tab shows tree
- Press `/` → search box appears
- Type "byd" → results filter
- Press Enter → file opens, markdown renders
- Edit file in external editor → TUI updates without manual refresh
- Restart TUI → recent files preserved
- Switch theme → colors update

### Quality gates

| Gate | Command | Threshold |
|------|---------|-----------|
| Lint | `golangci-lint run` | 0 issues |
| Vet | `go vet ./...` | clean |
| Race | `go test -race ./...` | 0 races |
| Coverage | `go test -cover ./...` | ≥80% overall |
| Format | `gofmt -l .` | no diff |
| Cyclomatic complexity | `gocyclo -over 15` | 0 functions |

---

## 29. Edge Cases & Failure Modes

### Vault file edge cases

| Case | Handling |
|------|----------|
| Binary file in vault (image, PDF) | Show "binary file" placeholder; don't crash |
| Huge file (>10MB) | Show first 100KB + "truncated" message; ask user to confirm before full view |
| Symlink loop | Detect via visited-set; skip with warning |
| Permission denied | Show red "permission denied" with chmod suggestion |
| File deleted during render | fsnotify catches it; show "file no longer exists" |
| Malformed frontmatter | Treat as plain markdown; log warning |
| Empty file | Show "(empty file)" |
| No newlines | Show as one long line with overflow indicator |

### fsnotify edge cases

| Case | Handling |
|------|----------|
| Watcher fails on some files | Log warning; continue watching rest |
| Too many open files | Increase ulimit; warn user |
| fsnotify buffer overflow | Reduce watch scope; fall back to polling |
| Editor creates backup files | Filter via ignore patterns (*.swp, *~) |
| Rapid-fire saves | Debounce handles it |

### IPC edge cases

| Case | Handling |
|------|----------|
| Gateway not running | Show "gateway down" in status bar; queue commands locally |
| Gateway crash mid-request | Retry with backoff; eventually show error |
| Slow response (>30s) | Show progress indicator; allow cancel |
| SSE stream disconnect | Auto-reconnect; show reconnecting status |
| Tool returns partial result | Show partial + warning |
| Concurrent tool calls | Serialize; queue UI feedback |
| Gateway version mismatch | Show clear error; exit gracefully |

### Config edge cases

| Case | Handling |
|------|----------|
| Missing config file | Use defaults; show "no config found, using defaults" |
| Malformed TOML | Show parse error with line number; exit |
| Unknown fields | Warn but continue (forward compatibility) |
| Empty vault path | Show config error; don't proceed |
| Vault root doesn't exist | Offer to create; or show error with mkdir command |
| Read-only home dir | Fall back to /tmp; warn |

### Persistence edge cases

| Case | Handling |
|------|----------|
| BoltDB corrupted | Backup + recreate; warn user |
| Disk full | Catch write errors; show "disk full" |
| Concurrent access (multiple instances) | BoltDB locks; second instance shows "already running" |
| Schema version too new | Show "operator version too old, please upgrade" |

### Terminal edge cases

| Case | Handling |
|------|----------|
| Terminal too small (<80x24) | Show "terminal too small, resize to 80x24 minimum" |
| No color support | Fall back to ASCII (no lipgloss) |
| Non-UTF8 locale | Force UTF-8; warn |
| Mouse not supported | Hide mouse hints |
| Resize mid-action | Recompute layout; preserve cursor where possible |
| Window blurred/background | Pause animations; freeze non-essential updates |

---

## 30. Future Extensions

### v1.1 (3 months after v1.0)

- Search results highlighting in markdown viewer
- Bookmark/favorites system
- Recent files menu
- Themes marketplace (download from URL)

### v1.2 (6 months)

- Multi-window support (split panes)
- Diff viewer (compare two vault files)
- Notes linking (click `[[link]]` to navigate)

### v2.0 (12 months)

- WebAssembly plugin system
- Embedded mini-editor (for quick edits)
- Cloud sync (optional, for users who want backup)

### v3.0 (24+ months)

- Web companion (mirror TUI in browser)
- Mobile app (read-only vault viewer)
- Collaborative editing (CRDTs)

---

## Appendix A: Reference implementations

- **Bubble Tea examples:** https://github.com/charmbracelet/bubbletea/tree/main/examples
- **Glow source:** https://github.com/charmbracelet/glow
- **Cobra tutorial:** https://github.com/spf13/cobra/blob/main/site/content/user_guide.md
- **fsnotify examples:** https://github.com/fsnotify/fsnotify#example
- **BoltDB docs:** https://pkg.go.dev/go.etcd.io/bbolt

## Appendix B: Python side changes needed

For Go TUI to work, Python side needs:

1. **MCP gateway HTTP+SSE** — already exists at `src/ikigai/src/ikigai/gateway/gateway.py`
2. **Stable JSON schema** for IPC — freeze at v1.0; document at `docs/ipc-schema.md`
3. **Health endpoint** at `GET /health` — already exists
4. **CORS** — not needed (loopback only)
5. **Auth** — none for loopback; gateway validates localhost source

## Appendix C: Why Go (not Rust, not Zig, not C++)

| Lang | Pros | Cons | Verdict |
|------|------|------|---------|
| **Go** | Static binary, fast compile, easy cross-compile, Charm ecosystem | Larger binaries than Rust | ✅ Chosen |
| Rust | Smaller binaries, faster, safer | Steeper learning curve, slower compile | ❌ Overkill for CLI |
| Zig | Smallest binaries, fast compile | Immature ecosystem, no Charm | ❌ |
| C++ | Mature, fast | Build hell, manual memory | ❌ |

## Appendix D: Open questions

1. **Should Go TUI handle writes to vault?** No — `vault_write` MCP stays sole writer. Go TUI is read-only for vault; writes go through Python gateway.
2. **Should we vendor Charm libraries?** No — use upstream; pin versions in go.mod
3. **Should we add a mobile companion?** v3.0, far future
4. **Where to host?** GitHub Releases + Homebrew tap (v2+)

---

*Spec written 2026-09-03 — comprehensive drill-down per user request "lets full drill dow complete go from the ground basics to fully robust and most extended features breakdown". Captured for future revival; NO implementation work begun. Verdict: DEFER per `/btw`.*
