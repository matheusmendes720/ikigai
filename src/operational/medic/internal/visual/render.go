package visual

import (
	"fmt"
	"html"
	"strings"
)

// CellW is the on-screen width of one terminal cell in pixels.
const CellW = 8

// CellH is the on-screen height of one terminal cell in pixels.
const CellH = 16

// svgFontSize is the pixel font size used for glyph rendering. It is a
// fraction of CellH so glyphs visually fit inside the cell rectangle.
const svgFontSize = 13

// RenderSVG renders frame as a self-contained SVG document.
//
// The output uses one <rect> per cell (background) plus one <text> per
// non-blank cell (glyph + fg colour). A header comment describes the
// capture and a legend strip shows the 16 ANSI named colours.
//
// The document is XML-safe: all glyph and comment text is escaped. It
// opens directly in any browser without external CSS or fonts.
func RenderSVG(frame *Frame) []byte {
	if frame == nil {
		return []byte(`<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg"/>`)
	}
	w := frame.Cols * CellW
	h := frame.Rows * CellH + legendH

	var b strings.Builder
	b.Grow(w * h / 2)

	fmt.Fprintf(&b, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
	fmt.Fprintf(&b, "<!-- medic visual debug frame  cols=%d rows=%d hash=%s captured=%s -->\n",
		frame.Cols, frame.Rows, frame.Hash, frame.CapturedAt.Format("2006-01-02T15:04:05Z07:00"))
	fmt.Fprintf(&b, "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"%d\" height=\"%d\" viewBox=\"0 0 %d %d\">\n",
		w, h, w, h)
	fmt.Fprintf(&b, "  <rect x=\"0\" y=\"0\" width=\"%d\" height=\"%d\" fill=\"%s\"/>\n",
		w, frame.Rows*CellH, Named[0].String())

	// 1) Background rectangles. We emit one per cell to preserve per-cell
	//    backgrounds (useful for highlighted rows, status bars, etc.).
	for y := 0; y < frame.Rows; y++ {
		for x := 0; x < frame.Cols; x++ {
			c := frame.CellAt(x, y)
			if c.Bg == Named[0] {
				continue // default black: skip to keep file small
			}
			fmt.Fprintf(&b, "  <rect x=\"%d\" y=\"%d\" width=\"%d\" height=\"%d\" fill=\"%s\"/>\n",
				x*CellW, y*CellH, CellW, CellH, c.Bg.String())
		}
	}

	// 2) Foreground glyphs.
	for y := 0; y < frame.Rows; y++ {
		for x := 0; x < frame.Cols; x++ {
			c := frame.CellAt(x, y)
			if c.IsBlank() {
				continue
			}
			writeGlyph(&b, x, y, c)
		}
	}

	// 3) Legend.
	writeLegend(&b, w, frame.Rows*CellH)

	b.WriteString("</svg>\n")
	return []byte(b.String())
}

const legendH = 32

// writeGlyph emits one <text> element for cell (x, y).
func writeGlyph(b *strings.Builder, x, y int, c Cell) {
	fg := c.Fg
	bg := c.Bg
	if c.Reverse {
		fg, bg = bg, fg
	}
	// y for SVG <text> is the baseline; nudge down by ~75% of CellH.
	ty := y*CellH + CellH - 3
	tx := x*CellW + 1 // tiny left padding
	style := ""
	if c.Bold {
		style += " font-weight=\"bold\""
	}
	if c.Italic {
		style += " font-style=\"italic\""
	}
	if c.Underline {
		style += " text-decoration=\"underline\""
	}
	glyph := html.EscapeString(string(c.Rune))
	fmt.Fprintf(b, "  <text x=\"%d\" y=\"%d\" font-family=\"monospace\" font-size=\"%d\" fill=\"%s\"%s>%s</text>\n",
		tx, ty, svgFontSize, fg.String(), style, glyph)
}

// writeLegend emits a strip at the bottom showing the 16 ANSI named colours.
func writeLegend(b *strings.Builder, totalW, top int) {
	y := top + 4
	bw := 16
	bh := 12
	for i, c := range Named {
		bx := i*bw + 4
		fmt.Fprintf(b, "  <rect x=\"%d\" y=\"%d\" width=\"%d\" height=\"%d\" fill=\"%s\" stroke=\"#888\" stroke-width=\"0.5\"/>\n",
			bx, y, bw, bh, c.String())
	}
	fmt.Fprintf(b, "  <text x=\"4\" y=\"%d\" font-family=\"monospace\" font-size=\"10\" fill=\"#888\">medic visual frame legend (16 ANSI named colours)</text>\n",
		y+bh+10)
}

// RenderText is a thin convenience: returns the frame's plain-text dump.
// Each row is one line; trailing whitespace per row is preserved.
func RenderText(frame *Frame) []byte {
	if frame == nil {
		return nil
	}
	return []byte(frame.String())
}

// RenderTSV renders the frame as a tab-separated cell grid. One row per
// line; each cell is encoded as rune|Fg-hex|Bg-hex|attrs where attrs is
// "B", "I", "U", "R" joined. Useful for golden diffs and unit tests.
func RenderTSV(frame *Frame) []byte {
	if frame == nil {
		return nil
	}
	var b strings.Builder
	b.Grow(frame.Cols * frame.Rows * 12)
	for y := 0; y < frame.Rows; y++ {
		for x := 0; x < frame.Cols; x++ {
			c := frame.CellAt(x, y)
			if x > 0 {
				b.WriteByte('\t')
			}
			r := c.Rune
			if r == 0 {
				r = ' '
			}
			fmt.Fprintf(&b, "%s\t%s\t%s\t%s",
				string(r), c.Fg.String(), c.Bg.String(), attrsString(c))
		}
		b.WriteByte('\n')
	}
	return []byte(b.String())
}

// attrsString returns "B", "I", "U", "R" joined for the cell's attributes.
func attrsString(c Cell) string {
	var b strings.Builder
	if c.Bold {
		b.WriteByte('B')
	}
	if c.Italic {
		b.WriteByte('I')
	}
	if c.Underline {
		b.WriteByte('U')
	}
	if c.Reverse {
		b.WriteByte('R')
	}
	return b.String()
}