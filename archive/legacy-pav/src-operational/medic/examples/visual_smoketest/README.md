# visual_smoketest — exercise every public entry point of `internal/visual`

A throwaway Go program that runs through 11 numbered sub-tests, one per
visual package API, and prints PASS-style lines for each.

## Run

```bash
go run ./examples/visual_smoketest
```

Expected output (abbreviated):

```
plain text="hello world         …"
sgr    E=69 bold=true fg=#cd0000      ← SGR 1;31 (bold + named red)
256    E=114 fg=#ff0000               ← 38;5;196 → truecolor lookup
true   E=116 fg=#0a141e              ← 38;2;10;20;30 exact truecolor
cup    cell='A'                      ← 2J + 10;5H CUP positioning
box    4x5 first-cell='┌'             ← box drawing preserved across LF
diff   score=0.900  changed=1        ← CompareFrames
svg    len=2666 starts="<?xml …"     ← RenderSVG output
script steps=3 / round-tripped       ← Script JSON save+load
inspected widgets=1                  ← Inspect → WidgetTree
recording dir=test_rec frames=3      ← Recorder → frames/*.txt
```

## What each step covers

| # | API exercised | What it proves |
|---|---|---|
| 1 | `ParseANSIText` (plain) | ASCII stream lands in cells |
| 2 | `ParseANSIText` (SGR named) | bold + 8-color foreground parsed |
| 3 | `ParseANSIText` (SGR 256) | `38;5;196` resolves to `#ff0000` |
| 4 | `ParseANSIText` (SGR truecolor) | `38;2;R;G;B` exact preservation |
| 5 | `ParseANSIText` (CUP) | `2J` + `H` positioning |
| 6 | `ParseANSIText` (box drawing) | Multi-byte UTF-8 survives LF wrap |
| 7 | `CompareFrames` | Cell-level diff + score |
| 8 | `RenderSVG` | XML + `<rect>` + `<text>` per cell |
| 9 | `Script` + `SaveScript` + `LoadScript` | Round-trip persistence |
| 10 | `Inspect` | Heuristic widget detection from borders |
| 11 | `Recorder` | Frames + meta.json + timeline.json on disk |

## Cleaning up

The smoketest writes to `./test_rec/` and `./test_script.json`. Clean up:

```bash
rm -rf test_rec test_script.json
```

## When it fails

If a single line says "expected X got Y", the parser/render/recorder has
drifted from the test. Run `go test ./internal/visual/...` for finer-grained
feedback. The visual package has unit tests covering:

- Frame construction, resize, clear, equal, diff, hash
- Cell classification (blank/non-blank), RGB color encoding
- ANSI parser edge cases (SGR, CUP, clear, box drawing, deferred wrap)
- RenderSVG output structure and dimensions
- RenderTSV column layout
- CompareFrames score computation
- Recorder Start/Record/Stop lifecycle

If those pass but the smoketest fails, the bug is at a layer above the
visual package — usually a `pkg/medic/visualdebug` wiring issue.
