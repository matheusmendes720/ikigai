# medic — Visual Interface (TUI capture + golden frames)

medic's visual interface pillar drives real CLI/TUI binaries inside a PTY,
captures every rendered frame, and diffs them against a corpus of expected
(SVG golden) frames. This enables fully automated visual regression testing.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  medic visualize                                │
│                                                                 │
│  binary + args ──► PTY master ──► PTY slave ──► target process │
│                          │                                     │
│                     ┌────▼──────────┐                          │
│                     │  Capturer     │  reads cell grid          │
│                     │  (frame.go)   │  from PTY slave          │
│                     └────┬──────────┘                          │
│                          │ captures every frameMs               │
│                     ┌────▼──────────┐                          │
│                     │  Recorder     │  writes frames/          │
│                     │  (recorder.go)│  frame_000001.txt        │
│                     └────┬──────────┘  frame_000002.txt        │
│                          │ .DiffAgainst(golden)                │
│                     ┌────▼──────────┐                          │
│                     │  DIFF         │  FrameSetDiff            │
│                     └───────────────┘  changed / added / removed│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 medic golden                                    │
│  text spec ──► parser ──► Grid[Rows][Cols]Cell ──► renderers  │
│                                    │                │          │
│                              Spec.Grid         Spec.Grid        │
│                                    │                │          │
│                              ┌────▼──┐      ┌──────▼──┐       │
│                              │  TXT  │      │   SVG   │       │
│                              │writer │      │ writer  │       │
│                              └───────┘      └─────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## `medic visualize` — PTY capture pipeline

```bash
medic visualize [binary] [args...] [flags]
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--out dir` | `frames/` | Output directory for captured frames |
| `--cols N` | `80` | PTY width in characters |
| `--rows N` | `24` | PTY height in rows |
| `--fps N` | `10` | Maximum frames per second (0 = no limit) |
| `--max-frames N` | `0` | Stop after N frames (0 = unlimited) |
| `--script path` | — | Keystroke script (YAML) to automate the TUI |
| `--golden dir` | — | Golden frame corpus to diff against |

### Keystroke scripting

`--script` takes a YAML file with a sequence of time-keyed keypresses:

```yaml
# examples/visual_smoketest/script.yaml
steps:
  - keys: ["h", "a", "b", "i", "t", "\n"]
    delay_ms: 50
  - keys: ["q"]
    delay_ms: 100
```

### Output

Each captured session produces:

```
frames/
  meta.json           # {binary, args, cols, rows, fps, captured_at}
  frame_000001.txt    # cell grid: "RUNE FG BG" per cell, space-separated
  frame_000002.txt
  ...
  frame_000001.svg    # rendered SVG (if Renderer is wired)
```

### Diff output

When `--golden dir` is provided and frames differ:

```
medic visualize pav --golden golden/ --out diff_run/
# Exit code 0 if identical, non-zero if any diffs found.
# diff_run/report.md shows: changed frames, added frames, removed frames.
```

## `medic golden` — Golden frame generation

```bash
medic golden [specfile]... [flags]
```

Reads one or more frame specification files (or stdin) and emits `.txt` + `.svg`
golden frames. No binary execution required — pure text-to-visual rendering.

### Spec format

```
cols: 80
rows: 24
font: JetBrains Mono
scale: 1.0

┌─ Habit Engine ────────────────────────────────┐
│  Exercise       12     0.993  ●  │
│  Meditation      3     0.950  ●  │
└──────────────────────────────────────────────┘

---FRAME---

cols: 80
rows: 5

[bold]Exercise streak +1 → 13[/bold]

---FRAME---

cols: 40
rows: 5

┌─ Home ─────┐
│ 12:30      │
└────────────┘
```

### Directives (top of each frame block)

| Directive | Type | Description |
|-----------|------|-------------|
| `cols: N` | int | Terminal width for this frame |
| `rows: N` | int | Terminal height for this frame |
| `font: name` | string | CSS font family (default: Courier New) |
| `scale: N` | float | Pixel scale factor (default: 1.0) |

### Markdown-style inline markup

| Tag | Effect |
|-----|--------|
| `[bold]`...`[/bold]` | Bold text |
| `[dim]`...`[/dim]` | Dim/faint text |
| `[italic]`...`[/italic]` | Italic (rendered as underline in SVG) |
| `[underline]`...`[/underline]` | Underlined text |

ANSI CSI escape sequences (`\x1b[1m`, `\x1b[2m`, etc.) are parsed and applied
to the cell's foreground/background colours.

### Box-drawing characters

All Unicode box-drawing characters are rendered in the cell grid:
`─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬╭╮╯╰░▒▓█▄▀■□▪▫`

Wide characters (East Asian) count as 2 cells wide.

### Output files

```
outdir/
  {name}_000001.txt   # annotated cell grid (RUNE FG BG per cell)
  {name}_000001.svg   # rendered SVG
  {name}_000002.txt
  {name}_000002.svg
  ...
```

Use `--name prefix` to set the filename prefix (default: `frame`).

## Frame file format (`.txt`)

Each line: `RUNE FG BG` separated by single spaces.

```
┌ ─ 0 0
─ 0 0
─ 0 0
│ 0 0
H 7 0
a 7 0
b 7 0
i 7 0
t 7 0
  7 0
E 7 0
n 7 0
g 7 0
i 7 0
n 7 0
e 7 0
  7 0
─ 0 0
...
```

- `RUNE`: actual Unicode character or space
- `FG`: ANSI foreground colour index (0–255)
- `BG`: ANSI background colour index (0–255)

Lines with `#` are comments (preserved from the spec).

## Visual debug loop

```bash
# 1. Generate expected frames from a text description
medic golden spec.txt --name dashboard --out golden/

# 2. Run the real TUI and capture frames
medic visualize ./pav home --out captures/

# 3. Diff captured against golden
medic visualize ./pav home --golden golden/ --out diff/

# Exit code: 0 if identical, 1 if different
```

## Adding a new renderer

1. Implement `Renderer` interface in `pkg/medic/visual/renderer.go`:
   ```go
   type Renderer interface {
       RenderFrame(path string, spec Spec) error
   }
   ```
2. Register it in `cmd/medic/cmd_visualize/cmd_visualize.go:runScripted`
   by passing it to `recorder.Start`.
3. The `.txt` cell-grid writer is always included; SVG is the reference renderer.

## Why cell-grid over pixel screenshots?

Cell-grid capture (1) is deterministic — same TUI state always produces the same
grid, (2) is text-diffable, (3) has zero image-processing dependencies,
(4) makes visual diffs readable as character-level deltas, and (5) works for
any terminal emulator without a display server.
