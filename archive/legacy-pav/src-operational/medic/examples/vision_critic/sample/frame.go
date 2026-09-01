// Package sample provides a synthetic TUI frame used by the
// examples/vision_critic demo. It is intentionally small — the goal
// is to give the vision model something to look at, not to be a
// real PAV screen.
package sample

import (
	"strings"

	"github.com/life-oss/medic/internal/visual"
)

// Frame returns a 120x40 frame that looks like a small dashboard with
// intentional UX flaws (low contrast, ragged right edge, missing
// status bar) so the vision model has something to critique.
func Frame() *visual.Frame {
	f := visual.NewFrame(120, 40)

	// Title bar (1 row tall, with a thin border).
	drawBox(f, 0, 0, 120, 1, '─', '│')
	f.SetCell(2, 0, visual.Cell{Rune: 'D', Fg: visual.Named[4]})
	f.SetCell(3, 0, visual.Cell{Rune: 'A'})
	f.SetCell(4, 0, visual.Cell{Rune: 'S'})
	f.SetCell(5, 0, visual.Cell{Rune: 'H'})
	f.SetCell(6, 0, visual.Cell{Rune: 'B'})
	f.SetCell(7, 0, visual.Cell{Rune: 'O'})
	f.SetCell(8, 0, visual.Cell{Rune: 'A'})
	f.SetCell(9, 0, visual.Cell{Rune: 'R'})
	f.SetCell(10, 0, visual.Cell{Rune: 'D'})

	// Three KPI cards (12 rows tall each, 38 cols wide). Borders are
	// box-drawing; the "value" text is bold-coloured but the label
	// is grey-on-grey (intentional low-contrast flaw).
	drawBox(f, 0, 2, 38, 14, '─', '│')
	f.SetCell(2, 3, visual.Cell{Rune: 'Q', Fg: visual.Named[8]})
	f.SetCell(3, 3, visual.Cell{Rune: '_'})
	f.SetCell(4, 3, visual.Cell{Rune: 'H'})
	f.SetCell(5, 3, visual.Cell{Rune: 'E'})
	f.SetCell(7, 9, visual.Cell{Rune: '0', Fg: visual.Named[2], Bold: true})
	f.SetCell(8, 9, visual.Cell{Rune: '.'})
	f.SetCell(9, 9, visual.Cell{Rune: '8', Fg: visual.Named[2], Bold: true})
	f.SetCell(10, 9, visual.Cell{Rune: '1'})
	// Low-contrast label (intentional flaw)
	f.SetCell(2, 12, visual.Cell{Rune: 'l', Fg: visual.Named[8]})
	f.SetCell(3, 12, visual.Cell{Rune: 'a'})
	f.SetCell(4, 12, visual.Cell{Rune: 'b'})
	f.SetCell(5, 12, visual.Cell{Rune: 'e'})
	f.SetCell(6, 12, visual.Cell{Rune: 'l'})

	drawBox(f, 40, 2, 78, 14, '─', '│')
	drawBox(f, 80, 2, 120, 14, '─', '│')

	// A "list" panel with ragged right edge (intentional flaw).
	drawBox(f, 0, 16, 60, 36, '─', '│')
	row := 17
	for _, item := range []string{"Morning run", "Read 30m", "Deep work", "Lunch", "Review"} {
		f.SetCell(2, row, visual.Cell{Rune: '·', Fg: visual.Named[4]})
		// Note: the text is intentionally 3 columns short of the border
		// to create the ragged-right edge.
		for i, c := range item {
			f.SetCell(4+i, row, visual.Cell{Rune: c, Fg: visual.Named[7]})
		}
		row++
	}

	// A "metrics" panel with no visible status bar (intentional flaw).
	drawBox(f, 62, 16, 120, 36, '─', '│')
	f.SetCell(64, 17, visual.Cell{Rune: 'S'})
	f.SetCell(65, 17, visual.Cell{Rune: 't'})
	f.SetCell(66, 17, visual.Cell{Rune: 'r'})
	f.SetCell(67, 17, visual.Cell{Rune: 'e'})
	f.SetCell(68, 17, visual.Cell{Rune: 'a'})
	f.SetCell(69, 17, visual.Cell{Rune: 'k'})

	return f
}

// RenderSVG is a tiny helper so the example can also write a preview
// when mmx isn't available.
func RenderSVG(f *visual.Frame) []byte { return visual.RenderSVG(f) }

// drawBox strokes a rectangle with horizontal and vertical borders.
// (Used to build the synthetic frame; we don't go through the ANSI
// parser for setup.)
func drawBox(f *visual.Frame, x, y, w, h int, horiz, vert rune) {
	for cx := x; cx < x+w; cx++ {
		f.SetCell(cx, y, visual.Cell{Rune: horiz, Fg: visual.Named[7]})
		f.SetCell(cx, y+h-1, visual.Cell{Rune: horiz, Fg: visual.Named[7]})
	}
	for cy := y; cy < y+h; cy++ {
		f.SetCell(x, cy, visual.Cell{Rune: vert, Fg: visual.Named[7]})
		f.SetCell(x+w-1, cy, visual.Cell{Rune: vert, Fg: visual.Named[7]})
	}
}

// PlainDump returns a string view of the frame for debugging.
func PlainDump(f *visual.Frame) string { return strings.TrimRight(f.String(), "\n") }
