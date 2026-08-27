# Visual Debug Pipeline — Terminal Application Debugger

> **Status:** 🟡 Draft — enabled by `medic` (life-ops/operational/medic/).
> **Related:** `ARCHITECTURAL_REFRAMING_2026-06-07.md` (Neovim RPC analogy), `10-RUST-INTEGRATION.md` (shared memory ring buffer for chart data).

---

## 1. Core problem

TUIs are the hardest class of application to debug visually. You cannot attach a DOM inspector or take a heap snapshot mid-frame. A TUI bug typically manifests as:
- **Bad layout** — panel overlaps another, content clipped at the wrong boundary
- **Colour / style mismatch** — a cell has unexpected bold or wrong foreground
- **Cursor position drift** — the cursor is not where the algorithm thinks it is
- **Animation stutter** — refresh rate below 30 fps, dropped frames
- **ANSI sequence corruption** — a malformed escape sequence clears or wraps unexpectedly

All four of these require **seeing the frame at pixel level**, not just reading the code.

---

## 2. The pipeline architecture

The visual debug pipeline is a **five-stage relay**:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          medic visual debug pipeline                          │
│                                                                              │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐         │
│  │  capture   │───▶│  parse     │───▶│  serialise │───▶│  compare  │         │
│  │  frame     │    │  ANSI      │    │  (SVG/PNG) │    │  golden   │         │
│  └────────────┘    └────────────┘    └────────────┘    └────────────┘         │
│       │                                           │              │          │
│       │     ┌──────────────────────────────────────┘              │          │
│       │     │                                                  ▼          │
│       ▼     ▼                                         ┌──────────────────┐  │
│  ┌────────────┐                                       │  MiniMax VL-01   │  │
│  │  live     │                                       │  vision critic   │  │
│  │  replay   │◀──────────────────────────────────────│  (mmx describe)  │  │
│  │  (ratatui)│  shared ring-buffer mmap             └──────────────────┘  │
│  └────────────┘    /tmp/opchart.dat                                   │    │
│       │                                                             │    │
│       ▼                                                             ▼    │
│  ┌────────────┐                                         ┌──────────────────┐ │
│  │  diff      │                                         │  findings → JSON  │ │
│  │  viewer    │                                         │  + markdown      │ │
│  └────────────┘                                         └──────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1 — Capture (`internal/visual/`)

The `Frame` type from `medic/internal/visual/frame.go` is the canonical capture surface.

```go
// Frame is a 2-D grid of Cells, plus cursor state.
type Frame struct {
    cells  [][]Cell        // rows × cols
    cursor Cursor          // cx, cy, pendingWrap
    width  int
    height int
}

// Cell is one terminal cell.
type Cell struct {
    rune   rune
    bg, fg RGB
    bold, italic, underline, strikethrough bool
    inverse, hidden, blink bool
}

// CaptureFromTerminal(pid int) (*Frame, error)
//  — Uses os.ReadFile("/proc/<pid>/fd/1") on Linux to read the TTY's canonical buffer
//  — On Windows: uses winapi ReadConsoleOutput
//  — On macOS: uses iokit to read the pty buffer
```

A frame capture is deterministic: given the same TTY buffer + ANSI parse, you always get the same `Frame` struct. This is the property that makes frame comparison possible.

### Stage 2 — Parse ANSI (`internal/visual/frame.go`)

`ParseANSIText(data []byte, cols, rows int) (*Frame, error)` implements:
- Full SGR (Select Graphic Rendition): bold, italic, underline, 256-color, truecolor
- CUP (Cursor Position) — `ESC[<row>;<col>H`
- ED (Erase Display) — `ESC[2J` clears entire frame
- EL (Erase Line) — `ESC[2K`
- Auto-wrap with **deferred wrap** semantics (matches real xterm behavior)
- Box-drawing characters: `─│┌┐└┘├┤┬┴┼` — parsed as single cells, not multi-column

The parser is tested against 11 sub-cases in `frame_test.go`:
```
plain text | bold+color | 256-color | truecolor | CUP | clear-screen
box-drawing | attribute reset | nested | trailing-LF | double-wrap
```

### Stage 3 — Serialise (`internal/visual/render.go`)

Three serialisation targets from the same `Frame`:

| Format | Function | Use case |
|---|---|---|
| **SVG** | `RenderSVG(frame, width, height int) ([]byte, error)` | Human review, MiniMax input, diff viewer |
| **PNG** | `RenderPNG(frame) ([]byte, error)` | Binary diff, CI artifacts |
| **TSV** | `RenderTSV(frame) string` | Text-mode diff, `diff` tool compatible |

SVG is the primary format: it's lossless, renders text as actual text (not rasterised), and is ~10 KB per frame vs ~200 KB for PNG.

```go
// RenderSVG renders a Frame as a self-contained SVG.
// Cell size: 9px wide × 18px tall (xterm metric).
// Font: "JetBrains Mono", fallback "Courier New", 13px.
func RenderSVG(f *Frame, cellW, cellH int) ([]byte, error)
```

### Stage 4 — Compare (`internal/visual/diff.go`)

```go
// Diff returns a visual diff of two frames.
// Only cells that differ are highlighted; identical cells are omitted.
func Diff(a, b *Frame) *DiffResult

type DiffResult struct {
    OnlyA   []*Cell  // in A, not in B
    OnlyB   []*Cell  // in B, not in A
    Changed []*Change // position + before/after for each changed cell
    HashA, HashB string  // fowler-noll-vo on frame content
}
```

`DiffResult` feeds both the text-mode diff viewer and the MiniMax critic.

### Stage 5 — Vision critic (`internal/visioncritic/`)

```
mmx describe <frame.svg> "You are a senior UX critic reviewing a terminal UI.
Focus on: layout (ragged edges, overflow), colour (contrast, accessibility),
typography (font size, hierarchy), alignment, consistency.
Report concrete, fixable issues with [severity] [title] [suggestion]."
```

Returns a parsed `Critique` struct:
```go
type Critique struct {
    Summary   string
    Score     int        // 0-100
    Verdict   Verdict    // APPROVE | COMMENT | REQUEST_CHANGES
    Findings  []Finding
    Raw       string     // unparsed mmx output
    Model     string
    DurationMs int
}
```

---

## 3. Shared ring buffer (Rust TUI integration)

When the Rust TUI (`apps/tui-rs/`) is the active interface, the shared ring buffer (`/tmp/opchart.dat`) is the capture source for the debug pipeline:

```
Go opcore process                    Rust op-tui process
      │                                     │
      │  mmap /tmp/opchart.dat (read-write) │
      │◀─────────────────────────────────── │
      │  write last 60 DayContext as msgpack │
      │                                     │
      ▼                                     ▼
medic capture reads                sparkline widget reads
frame from TTY buffer              from ring buffer (0-syscall)
```

The ring buffer is a **60-slot mmap** of `DayContext` msgpack-encoded structs, written by the Go core (the authority) and read by both the Rust TUI sparkline widget and the medic capture tool. This means the debug pipeline has zero intrusion into the Rust TUI itself — it reads what the Rust widget already reads.

---

## 4. CLI commands

The `medic visual` subcommand group exposes the pipeline:

```bash
# Capture a live TUI frame
medic visual capture <pid>                  # attach to TTY, capture current frame
medic visual capture --tui pav             # find pav TUI pid, capture

# Parse a raw ANSI stream
medic visual parse <file.ans> --cols 120 --rows 40

# Render as SVG/PNG/TSV
medic visual render frame.svg               # default: SVG
medic visual render frame.png
medic visual render --tsv frame.tsv

# Compare two frames
medic visual diff golden.svg candidate.svg  # outputs diff.svg + diff.txt

# Vision critic
medic visual critic frame.svg               # MiniMax VL-01 on SVG
medic visual critic --prompt-file configs/medic/promts/visual-critic.txt frame.svg

# Batch critique (swarm mode)
medic visual batch .medic/visualize/latest/frames/   # every *.svg → critique
medic visual batch --parallel 4 .medic/visualize/latest/frames/

# Workflow (agentic integration)
medic workflow run visual-critic.yaml
```

---

## 5. medic `visual-critic` workflow (agentic swarm)

```yaml
# examples/workflow/visual-critic.yaml — already written
- id: capture
  use: visual.capture
  args:
    source: ../apps/tui/target/debug/pav
    wait-ms: 1500
    out: .medic/visualize/latest/frame.svg

- id: vision_doctor
  use: system.available
  args:
    binary: mmx
    env: MINIMAX_API_KEY

- id: critic
  use: vision.critique
  when: vision_doctor.ok
  args:
    path: .medic/visualize/latest/frame.svg
    prompt_file: configs/medic/promts/visual-critic.txt
    out: .medic/vision/frame.json
```

The `batch` subcommand runs N critics in parallel — one per frame, all writing to `.medic/vision/<frame>.json`. A final aggregation step merges findings by severity.

---

## 6. Golden frame library

`examples/visual_smoketest/` generates a **golden frame corpus** — a set of known-correct frames for regression testing:

```
.golden/
├── box-drawing/        # ┌─┐ │ │ └─┘ borders
│   ├── 3x3.svg
│   ├── 4x5.svg
│   └── unicode-wide.svg  # CJK chars, double-width
├── color/
│   ├── truecolor.svg     # 24-bit colour gradient
│   ├── 256-color.svg     # 256-color palette
│   └── sgr-reset.svg     # nested bold+italic+color reset
├── layout/
│   ├── ragged-right.svg  # panel overflow at right edge
│   └── underflow.svg     # panel shorter than declared height
├── animation/
│   └── 10-frame-scroll/  # scrolling log, frame 0..9
└── interaction/
    ├── cursor-position.svg
    └── selection.svg
```

Every PR that changes TUI layout must pass `medic visual diff .golden/ candidate/`. Any new visual artefact is added to `.golden/` with a PR review.

---

## 7. Design constraints

| Rule | Rationale |
|---|---|
| Frame capture must be deterministic | Non-deterministic captures cannot be compared |
| ANSI parser must match xterm behavior exactly | xterm is the reference terminal; deviation = bug |
| SVG is the canonical diff format | Lossless, text-searchable, renders in browser |
| MiniMax critic is advisory only | The critic supplements human review; it does not gate merges |
| Ring buffer is read-only for Rust TUI | Write access from Rust would corrupt Go state |
| Frame captures do not touch the network | Local-only; `mmx` call is the only external dependency |
