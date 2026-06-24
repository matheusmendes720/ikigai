// Package cmd_golden implements `medic golden` — generate SVG golden frames
// from a text description without running the real TUI. This lets you build
// an expected visual corpus for CI diffing before the TUI is complete.
//
// Text format (each frame is separated by "---FRAME---\n"):
//
//	cols: 120
//	rows: 40
//	[ANSI_CSI]<fg;bg;m>HIGHLIGHT_TEXT[ANSI_RESET]
//	┌─ Title ─────────────────────────────────────────────────┐
//	│ Content here with box-drawing and Unicode               │
//	│ [dim]dimmed text[/dim] [bold]bold[/bold]                │
//	└────────────────────────────────────────────────────────┘
//	footer text
//	---FRAME---
//	[next frame description]
package cmd_golden

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/spf13/cobra"
)

// Cmd builds `medic golden`.
func Cmd() *cobra.Command {
	var (
		outDir string
		name   string
	)
	c := &cobra.Command{
		Use:   "golden [description files...]",
		Short: "Generate SVG golden frames from text descriptions",
		Long: `medic golden reads one or more text description files (or stdin) and
emits SVG + .txt golden frames to --out.

Each description file contains one or more frame specs separated by the
token "---FRAME---". A frame spec has this grammar:

    cols: <int>        # frame width in columns (default: 120)
    rows: <int>        # frame height in rows (default: 40)
    font: <string>     # monospace font name (default: "monospace")
    scale: <float>     # cell width/height in CSS px (default: 10)
    ---                 # optional header separator
    <cell grid lines>   # rows of characters, ~cols wide each

ANSI escape codes are rendered as SVG spans with appropriate CSS:

    [ANSI_CSI]<fg;bg;m>  →  <tspan fill="..." background="..." font-weight="...">
    [ANSI_RESET]          →  </tspan>

Box-drawing chars (─ │ ┌ ┐ └ ┘ etc.) are rendered as SVG <line> or
<polyline> elements so they are crisp at any zoom level.

Output per frame:  <outDir>/<name>_NNNNNN.txt  (raw cell grid)
                   <outDir>/<name>_NNNNNN.svg  (rendered SVG)

Exit code 0 = all frames written. Exit code 1 = any frame failed.
`,
		Example: `  medic golden --name habit_summary --out .golden/frames <<'EOF'
cols: 120
rows: 24
┌─ Habit Engine ─────────────────────────────────────────────┐
│  Habit         Streak   H(t)      Q_HE      Status        │
│  ────────────────────────────────────────────────────────  │
│  Exercise        12     0.993    0.007    ● On track     │
│  Meditation       3     0.950    0.050    ● On track     │
│  Reading          0     0.000    1.000    ⚠ Fallen       │
└───────────────────────────────────────────────────────────┘
---FRAME---
cols: 120
rows: 24
┌─ Habit Engine ─────────────────────────────────────────────┐
│  [bold]Exercise streak +1 → 13[reset]                       │
└───────────────────────────────────────────────────────────┘
EOF`,
		RunE: func(cmd *cobra.Command, files []string) error {
			if outDir == "" {
				return fmt.Errorf("--out is required")
			}
			if err := os.MkdirAll(outDir, 0o755); err != nil {
				return fmt.Errorf("mkdir %s: %w", outDir, err)
			}

			var inputs []string
			if len(files) == 0 {
				// Read stdin — works on both Unix and Windows.
				info, err := os.Stdin.Stat()
				if err != nil || (info.Mode()&os.ModeCharDevice) != 0 {
					return fmt.Errorf("stdin: no data and no files provided (piping requires explicit '-' or files)")
				}
				data, err := os.ReadFile(os.Stdin.Name())
				if err != nil {
					return fmt.Errorf("stdin: %w", err)
				}
				inputs = append(inputs, string(data))
			} else {
				for _, f := range files {
					data, err := os.ReadFile(f)
					if err != nil {
						return fmt.Errorf("read %s: %w", f, err)
					}
					inputs = append(inputs, string(data))
				}
			}

			frameIdx := 0
			for inputIdx, input := range inputs {
				specs, err := parseMultiSpec(input)
				if err != nil {
					return fmt.Errorf("input[%d]: %w", inputIdx, err)
				}
				for _, spec := range specs {
					txtPath := framePath(outDir, name, frameIdx, "txt")
					svgPath := framePath(outDir, name, frameIdx, "svg")
					if err := writeTxt(txtPath, spec); err != nil {
						return fmt.Errorf("write txt %s: %w", txtPath, err)
					}
					if err := writeSvg(svgPath, spec); err != nil {
						return fmt.Errorf("write svg %s: %w", svgPath, err)
					}
					fmt.Fprintf(cmd.OutOrStdout(), "✓ %s\n  %s\n  %s\n",
						humanFrameIdx(frameIdx), txtPath, svgPath)
					frameIdx++
				}
			}
			return nil
		},
	}
	c.Flags().StringVarP(&outDir, "out", "o", "", "output directory (required)")
	c.Flags().StringVarP(&name, "name", "n", "frame", "base name for output files")
	return c
}

// ----------------------------------------------------------------------
// Parsing
// ----------------------------------------------------------------------

// Spec describes one frame's visual state.
type Spec struct {
	Cols  int
	Rows  int
	Font  string
	Scale float64
	// Grid is Rows slices of Cols cells.
	Grid [][]Cell
}

// Cell is the ANSI + rune state of one terminal cell.
type Cell struct {
	Rune  rune
	Fg    int // ANSI color 0-255, or -1 for default
	Bg    int
	Bold  bool
	Dim   bool
	Italic bool
	Underline bool
}

// parseMultiSpec splits a document by "---FRAME---" and parses each section.
func parseMultiSpec(doc string) ([]Spec, error) {
	parts := strings.Split(doc, "---FRAME---")
	var specs []Spec
	for i, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		spec, err := parseSpec(part)
		if err != nil {
			return nil, fmt.Errorf("frame %d: %w", i, err)
		}
		specs = append(specs, spec)
	}
	if len(specs) == 0 {
		return nil, fmt.Errorf("no frames found")
	}
	return specs, nil
}

// parseSpec parses a single frame spec.
func parseSpec(section string) (Spec, error) {
	spec := Spec{Cols: 120, Rows: 40, Font: "monospace", Scale: 10}
	lines := strings.Split(section, "\n")

	// Collect content lines (everything before the first box-drawing char
	// on the left margin, or after the header block).
	// Separate directive lines from content lines. Directives (key: value lines)
	// before any box-drawing content are metadata only; they do NOT become rows.
	var contentLines []string
	headerDone := false
	for _, ln := range lines {
		ln = strings.TrimRight(ln, "\r")
		trimmed := strings.TrimSpace(ln)
		// Directive lines (key: value) before any real content → metadata only.
		if !headerDone && isDirective(trimmed) {
			if err := applyDirective(&spec, trimmed); err != nil {
				return spec, fmt.Errorf("directive %q: %w", trimmed, err)
			}
			continue
		}
		// Skip blank lines before content starts.
		if !headerDone && trimmed == "" {
			continue
		}
		headerDone = true
		// This is real content — skip directive lines even if they appear later.
		if isDirective(trimmed) {
			continue
		}
		if trimmed != "" {
			contentLines = append(contentLines, ln)
		}
	}

	if len(contentLines) == 0 {
		return spec, fmt.Errorf("no content lines")
	}

	// Determine actual frame bounds.
	actualRows := len(contentLines)
	actualCols := 0
	for _, line := range contentLines {
		effLen := effectiveWidth(line)
		if effLen > actualCols {
			actualCols = effLen
		}
	}
	// Use the declared rows if larger than actual content (declared terminal size).
	// Otherwise use actual content rows.
	if spec.Rows < actualRows {
		spec.Rows = actualRows
	}
	// Use the declared cols if larger than actual content.
	if spec.Cols < actualCols {
		spec.Cols = actualCols
	}

	// Parse cells. Allocate for the full declared height (spec.Rows)
	// so the grid represents the entire terminal viewport.
	spec.Grid = make([][]Cell, spec.Rows)
	for r := 0; r < spec.Rows; r++ {
		if r < len(contentLines) {
			spec.Grid[r] = parseLine(contentLines[r], spec.Cols)
		} else {
			// Blank padding row for declared-but-empty rows.
			spec.Grid[r] = make([]Cell, spec.Cols)
			for c := 0; c < spec.Cols; c++ {
				spec.Grid[r][c] = Cell{Rune: ' ', Fg: 7, Bg: 0}
			}
		}
	}

	// Normalize: every row must have exactly spec.Cols cells (truncate or pad).
	for r := 0; r < spec.Rows; r++ {
		row := spec.Grid[r]
		if len(row) < spec.Cols {
			pad := make([]Cell, spec.Cols-len(row))
			for i := range pad {
				pad[i] = Cell{Rune: ' ', Fg: 7, Bg: 0}
			}
			spec.Grid[r] = append(row, pad...)
		} else if len(row) > spec.Cols {
			spec.Grid[r] = row[:spec.Cols]
		}
	}

	return spec, nil
}

// isDirective returns true for "key: value" lines.
// A line is a directive if it contains a ':' and does not start with a
// box-drawing character.
func isDirective(s string) bool {
	s = strings.TrimSpace(s)
	if s == "" {
		return false
	}
	if isBoxDrawing(rune(s[0])) {
		return false
	}
	return strings.ContainsRune(s, ':')
}

// applyDirective mutates spec according to a "key: value" line.
func applyDirective(spec *Spec, line string) error {
	line = strings.TrimSpace(line)
	idx := strings.IndexByte(line, ':')
	if idx < 0 {
		return fmt.Errorf("no colon in directive")
	}
	key := strings.TrimSpace(line[:idx])
	val := strings.TrimSpace(line[idx+1:])
	switch strings.ToLower(key) {
	case "cols":
		n, err := strconv.Atoi(val)
		if err != nil {
			return fmt.Errorf("bad cols %q: %w", val, err)
		}
		spec.Cols = n
	case "rows":
		n, err := strconv.Atoi(val)
		if err != nil {
			return fmt.Errorf("bad rows %q: %w", val, err)
		}
		spec.Rows = n
	case "font":
		spec.Font = val
	case "scale":
		f, err := strconv.ParseFloat(val, 64)
		if err != nil {
			return fmt.Errorf("bad scale %q: %w", val, err)
		}
		spec.Scale = f
	}
	return nil
}

// parseLine parses one text line into a slice of Cells, padded to width cols.
func parseLine(line string, cols int) []Cell {
	cells := make([]Cell, 0, len(line))

	// Track ANSI state across the line.
	fg := -1
	bg := -1
	bold := false
	dim := false
	italic := false
	underline := false

	i := 0
	for i < len(line) {
		r := rune(line[i])

		// ANSI escape sequence?
		if r == 0x1B && i+1 < len(line) && line[i+1] == '[' {
			// Parse CSI sequence.
			end := i + 2
			for end < len(line) && line[end] >= 0x40 && line[end] <= 0x7E {
				end++
			}
			seq := line[i+2 : end]
			if len(seq) > 0 && seq[len(seq)-1] >= 0x40 {
				// It's a CSI. Apply it.
				fg, bg, bold, dim, italic, underline = applyAnsi(seq, fg, bg, bold, dim, italic, underline)
			}
			i = end
			continue
		}

		// Markdown-style inline markup: [dim]...[dim] [bold]...[bold]
		if r == '[' {
			end := findBracket(line[i:])
			if end > 0 {
				tag := line[i+1 : i+end-1]
				if tag == "bold" {
					bold = true
					i += end
					continue
				}
				if tag == "/bold" {
					bold = false
					i += end
					continue
				}
				if tag == "dim" {
					dim = true
					i += end
					continue
				}
				if tag == "/dim" {
					dim = false
					i += end
					continue
				}
				if tag == "italic" {
					italic = true
					i += end
					continue
				}
				if tag == "/italic" {
					italic = false
					i += end
					continue
				}
				if tag == "underline" {
					underline = true
					i += end
					continue
				}
				if tag == "/underline" {
					underline = false
					i += end
					continue
				}
				// Not a recognised tag; treat '[' as a literal char.
			}
		}

		// Tab → advance to next multiple of 8.
		if r == '\t' {
			cells = append(cells, Cell{Rune: '\t', Fg: fg, Bg: bg, Bold: bold, Dim: dim, Italic: italic, Underline: underline})
			i++
			continue
		}

		// Box-drawing chars.
		if isBoxDrawing(r) {
			cells = append(cells, Cell{Rune: r, Fg: fg, Bg: bg, Bold: bold, Dim: dim, Italic: italic, Underline: underline})
			i++
			continue
		}

		// Regular character.
		cells = append(cells, Cell{Rune: r, Fg: fg, Bg: bg, Bold: bold, Dim: dim, Italic: italic, Underline: underline})
		i++
	}

	// Pad to cols.
	for len(cells) < cols {
		cells = append(cells, Cell{Rune: ' ', Fg: fg, Bg: bg, Bold: bold, Dim: dim, Italic: italic, Underline: underline})
	}

	return cells
}

// findBracket returns the index past the closing ']' in s (which starts with '[').
// Returns 0 if no match.
func findBracket(s string) int {
	depth := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '[' {
			depth++
		}
		if s[i] == ']' {
			depth--
			if depth == 0 {
				return i + 1 // position AFTER the closing bracket
			}
		}
	}
	return 0
}

// applyAnsi applies an ANSI SGR (Select Graphic Rendition) sequence and
// returns the updated style state.
func applyAnsi(seq string, fg, bg int, bold, dim, italic, underline bool) (int, int, bool, bool, bool, bool) {
	if seq == "" || seq[len(seq)-1] < 0x40 {
		return fg, bg, bold, dim, italic, underline
	}
	// Strip the final "m" which terminates SGR.
	if seq[len(seq)-1] == 'm' {
		seq = seq[:len(seq)-1]
	}
	if seq == "" {
		// Reset.
		return -1, -1, false, false, false, false
	}
	// Parse semicolon-separated numbers.
	parts := strings.Split(seq, ";")
	for _, p := range parts {
		n, err := strconv.Atoi(p)
		if err != nil {
			continue
		}
		switch {
		case n == 0:
			fg, bg, bold, dim, italic, underline = -1, -1, false, false, false, false
		case n == 1:
			bold = true
		case n == 2:
			dim = true
		case n == 3:
			italic = true
		case n == 4:
			underline = true
		case n == 22:
			bold = false
		case n == 23:
			italic = false
		case n == 24:
			underline = false
		case n == 39:
			fg = -1
		case n == 49:
			bg = -1
		case n >= 30 && n <= 37:
			fg = n - 30
		case n == 38:
			fg = 0 // extended color — simplified
		case n >= 40 && n <= 47:
			bg = n - 40
		case n >= 90 && n <= 97:
			fg = n - 90 + 8
		case n >= 100 && n <= 107:
			bg = n - 100 + 8
		}
	}
	return fg, bg, bold, dim, italic, underline
}

func isBoxDrawing(r rune) bool {
	switch r {
	case '─', '│', '┌', '┐', '└', '┘',
 '├', '┤', '┬', '┴', '┼',
 '═', '║',
 '╔', '╗', '╚', '╝',
 '╠', '╣', '╦', '╩', '╬',
 '╭', '╮', '╯', '╰',
 '░', '▒', '▓', '█', '▄', '▀', '■', '□', '▪', '▫',
 '←', '→', '↑', '↓', '↔', '↕',
 '✓', '✗', '✔', '✘', '⚠', '●', '○', '◎',
 ' ', '　':
		return true
	}
	return false
}

func hasBoxDrawing(s string) bool {
	for _, r := range s {
		if isBoxDrawing(r) {
			return true
		}
	}
	return false
}

// effectiveWidth returns the display width of s (East Asian wide chars count as 2).
func effectiveWidth(s string) int {
	w := 0
	for _, r := range s {
		if r == 0x1B {
			continue // skip ANSI
		}
		// Count box-drawing and wide chars as 1 cell.
		w += 1
	}
	return w
}

// ----------------------------------------------------------------------
// Text output
// ----------------------------------------------------------------------

func writeTxt(path string, spec Spec) error {
	var b strings.Builder
	for _, row := range spec.Grid {
		for _, cell := range row {
			if cell.Rune == 0 || cell.Rune == ' ' {
				b.WriteByte(' ')
			} else {
				b.WriteRune(cell.Rune)
			}
		}
		b.WriteByte('\n')
	}
	return os.WriteFile(path, []byte(b.String()), 0o644)
}

// ----------------------------------------------------------------------
// SVG output
// ----------------------------------------------------------------------

// ansiPalette maps ANSI color indices to CSS rgb() strings.
var ansiPalette = [258]string{
	"#000000", "#CC0000", "#4E9A06", "#C4A000",
	"#3465D4", "#75507B", "#06989A", "#D3D7CF",
	"#555753", "#EF2929", "#8AE234", "#FCE94F",
	"#729FCF", "#AD7FA8", "#34E2E2", "#EEEEEC",
}

// fgHex returns the CSS color for a foreground ANSI index.
func fgHex(fg int) string {
	if fg < 0 {
		return "#000000"
	}
	if fg < 258 {
		return ansiPalette[fg]
	}
	return "#000000"
}

func writeSvg(path string, spec Spec) error {
	cw := spec.Scale  // cell width px
	ch := spec.Scale  // cell height px
	fontSize := cw * 0.7
	fw := cw * 0.55  // monospace char advance (approximate)

	width := float64(spec.Cols) * cw
	height := float64(spec.Rows) * ch

	var b bytes.Buffer
	b.WriteString(`<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="` + fmt.Sprintf("%.1f", width) + `" height="` + fmt.Sprintf("%.1f", height) + `"
     viewBox="0 0 ` + fmt.Sprintf("%.1f", width) + ` ` + fmt.Sprintf("%.1f", height) + `">
<style>
  text { font-family: "` + spec.Font + `, Courier New, monospace"; font-size: ` + fmt.Sprintf("%.1f", fontSize) + `px; }
</style>
<rect width="100%" height="100%" fill="#000000"/>
`)

	for y, row := range spec.Grid {
		var x int
		runStart := 0
		runCells := []Cell{}

			flushRun := func() {
				if len(runCells) == 0 {
					return
				}
				cell := runCells[0]
				fg := fgHex(cell.Fg)
				style := `fill="` + fg + `"`
				if cell.Bold {
					style += ` font-weight="bold"`
				}
				if cell.Dim {
					style += ` opacity="0.5"`
				}
				if cell.Italic {
					style += ` font-style="italic"`
				}
				if cell.Underline {
					style += ` text-decoration="underline"`
				}

				// Collect run text.
				var txt strings.Builder
				for _, c := range runCells {
					if c.Rune == '	' {
						txt.WriteByte(' ')
					} else {
						txt.WriteRune(c.Rune)
					}
				}
				text := txt.String()

				xPos := float64(runStart) * fw
				if len(text) > 0 {
					b.WriteString(fmt.Sprintf(`<text x="%.1f" y="%.1f" %s>%s</text>`+"\n",
						xPos, float64(y)*ch+ch*0.85, style, esc(text)))
				}
			}

			for x = 0; x < spec.Cols && x < len(row); x++ {
			cell := row[x]
			if cell.Rune == ' ' && !cell.Bold && !cell.Dim && cell.Fg < 0 && cell.Bg < 0 && !cell.Italic && !cell.Underline {
				flushRun()
				runCells = nil
				runStart = int(x) + 1
				continue
			}
			runCells = append(runCells, cell)
		}
		flushRun()

		// Render box-drawing on top of text (after text so borders are crisp).
		for x = 0; x < spec.Cols && x < len(row); x++ {
			cell := row[x]
			if !isBoxDrawing(cell.Rune) {
				continue
			}
			r := cell.Rune
			px := float64(x) * cw
			py := float64(y) * ch
			fg := fgHex(cell.Fg)
			stroke := `stroke="` + fg + `"`
			strokeWidth := `stroke-width="1"`

			switch r {
			case '─', '═':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth))
			case '│', '║':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '┌':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '┐':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '└':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '┘':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '├':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth,
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth))
			case '┤':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth,
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth))
			case '┬':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '┴':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '┼':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth,
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth))
			case '╔':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '╗':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '╚':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '╝':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth,
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth))
			case '╠', '╣', '╦', '╩', '╬':
				b.WriteString(fmt.Sprintf(
					`<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>
 <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s %s/>`+"\n",
					px+cw/2, py, px+cw/2, py+ch, stroke, strokeWidth,
					px, py+ch/2, px+cw, py+ch/2, stroke, strokeWidth))
			case ' ', '　':
				// no-op
			default:
				// Other box chars as a single dot marker.
				b.WriteString(fmt.Sprintf(
					`<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>`+"\n",
					px+cw/2, py+ch/2, cw/4, fg))
			}
		}
	}

	b.WriteString("</svg>\n")
	return os.WriteFile(path, b.Bytes(), 0o644)
}

// escXML returns s with XML special chars escaped.
func esc(s string) string {
	s = strings.ReplaceAll(s, "&", "&amp;")
	s = strings.ReplaceAll(s, "<", "&lt;")
	s = strings.ReplaceAll(s, ">", "&gt;")
	s = strings.ReplaceAll(s, `"`, "&quot;")
	return s
}

// ----------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------

func framePath(dir, name string, idx int, ext string) string {
	return filepath.Join(dir, fmt.Sprintf("%s_%06d.%s", name, idx, ext))
}

var frameIdxRE = regexp.MustCompile(`_(\d+)\.`)

func humanFrameIdx(idx int) string {
	return fmt.Sprintf("frame %03d", idx)
}
