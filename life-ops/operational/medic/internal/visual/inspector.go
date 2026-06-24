package visual

import (
	"fmt"
	"sort"
	"strings"
	"unicode"
)

// WidgetKind classifies the role of a detected Widget.
type WidgetKind string

// Widget kinds returned by the inspector.
const (
	WidgetHeader    WidgetKind = "header"
	WidgetStatusBar WidgetKind = "status_bar"
	WidgetPanel     WidgetKind = "panel"
	WidgetList      WidgetKind = "list"
	WidgetTable     WidgetKind = "table"
	WidgetKPICard   WidgetKind = "kpi_card"
	WidgetText      WidgetKind = "text"
)

// Widget is a detected region of the frame with a guessed role.
//
// All coordinates are inclusive: top/left are 0-based, bottom/right are
// inside the widget's bounds.
type Widget struct {
	Kind     WidgetKind `json:"kind"`
	Title    string     `json:"title,omitempty"`
	Top      int        `json:"top"`
	Left     int        `json:"left"`
	Bottom   int        `json:"bottom"`
	Right    int        `json:"right"`
	Text     string     `json:"text,omitempty"`
	Children []*Widget  `json:"children,omitempty"`
}

// WidgetTree is the root of the detected widget hierarchy. The root has
// no bounding box and acts purely as a container; its children are the
// top-level widgets found in the frame.
type WidgetTree struct {
	FrameCols int       `json:"frame_cols"`
	FrameRows int       `json:"frame_rows"`
	Root      []*Widget `json:"root"`
}

// Inspect runs heuristic widget detection over frame and returns the
// resulting tree. The algorithm:
//
//  1. Scan each row to count border glyphs (─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼).
//  2. Group consecutive rows whose left/right borders line up into a
//     rectangle (a candidate panel).
//  3. Classify each rectangle by content + position:
//     - row 0..2                  → header
//     - bottom row of frame       → status bar
//     - bordered rect + list body → list
//     - bordered rect + big int   → kpi_card
//     - bordered rect + col grid  → table
//     - bordered rect             → panel
//     - bare text rows            → text
//
// Inspect never returns nil. If nothing is detected it returns a tree
// with a single "text" widget covering the whole frame.
func Inspect(frame *Frame) *WidgetTree {
	tree := &WidgetTree{FrameCols: frame.Cols, FrameRows: frame.Rows}
	if frame == nil || frame.Cols == 0 || frame.Rows == 0 {
		tree.Root = []*Widget{}
		return tree
	}
	// Build a "border mask" — for each cell, is it a border glyph?
	border := make([]bool, frame.Cols*frame.Rows)
	for y := 0; y < frame.Rows; y++ {
		for x := 0; x < frame.Cols; x++ {
			r := frame.CellAt(x, y).Rune
			if isBorderRune(r) {
				border[y*frame.Cols+x] = true
			}
		}
	}

	// Find horizontal lines (rows where >50% of cells are ─).
	hline := make([]bool, frame.Rows)
	for y := 0; y < frame.Rows; y++ {
		count := 0
		for x := 0; x < frame.Cols; x++ {
			if border[y*frame.Cols+x] {
				count++
			}
		}
		if count*2 >= frame.Cols {
			hline[y] = true
		}
	}

	// Find vertical edges (columns with long runs of │).
	vlines := verticalEdges(frame, border)

	// Group rectangles from hline + vlines.
	rects := groupRectangles(frame, hline, vlines)

	// Sort by (top, left) for stable output.
	sort.SliceStable(rects, func(i, j int) bool {
		if rects[i].Top != rects[j].Top {
			return rects[i].Top < rects[j].Top
		}
		return rects[i].Left < rects[j].Left
	})

	// Classify.
	for _, r := range rects {
		w := classify(frame, r)
		tree.Root = append(tree.Root, w)
	}

	// Status bar: last row of frame, if it contains text but no full border.
	if last := frame.Rows - 1; last >= 0 {
		if !hline[last] && hasNonBlank(frame, 0, last, frame.Cols-1, last) {
			tree.Root = append(tree.Root, &Widget{
				Kind:   WidgetStatusBar,
				Top:    last,
				Left:   0,
				Bottom: last,
				Right:  frame.Cols - 1,
				Text:   trimRight(rowText(frame, last)),
			})
		}
	}

	// Fallback: if we found nothing, emit one big text widget.
	if len(tree.Root) == 0 {
		text := strings.TrimRight(frame.String(), "\n")
		tree.Root = []*Widget{{
			Kind:   WidgetText,
			Top:    0,
			Left:   0,
			Bottom: frame.Rows - 1,
			Right:  frame.Cols - 1,
			Text:   text,
		}}
	}

	return tree
}

// rect is a 1-based-box candidate detected by the rectangle grouper.
// All fields are inclusive bounds.
type rect struct {
	Top, Left, Bottom, Right int
	Bordered                 bool
}

// isBorderRune returns true for the canonical Unicode box-drawing glyphs.
func isBorderRune(r rune) bool {
	switch r {
	case '─', '│',
		'┌', '┐', '└', '┘',
		'├', '┤', '┬', '┴', '┼',
		'═', '║',
		'╔', '╗', '╚', '╝',
		'╠', '╣', '╦', '╩', '╬':
		return true
	}
	return false
}

// verticalEdges returns the list of column indices that look like a
// vertical border (long run of │ spanning at least 3 rows).
func verticalEdges(frame *Frame, border []bool) []int {
	var out []int
	for x := 0; x < frame.Cols; x++ {
		run, maxRun := 0, 0
		for y := 0; y < frame.Rows; y++ {
			if border[y*frame.Cols+x] {
				run++
				if run > maxRun {
					maxRun = run
				}
			} else {
				run = 0
			}
		}
		if maxRun >= 3 {
			out = append(out, x)
		}
	}
	return out
}

// groupRectangles turns horizontal lines + vertical edges into a list of
// bounded rectangles. We pair consecutive hlines that share at least one
// vertical edge between them.
func groupRectangles(frame *Frame, hline []bool, vlines []int) []rect {
	var rects []rect
	// Pairwise: for each top hline, find the next hline below it that
	// shares a vline.
	for top := 0; top < frame.Rows; top++ {
		if !hline[top] {
			continue
		}
		// Find a bottom hline below top, sharing a vline.
		for bot := top + 3; bot < frame.Rows; bot++ {
			if !hline[bot] {
				continue
			}
			left, right := sharedEdge(frame, top, bot, vlines)
			if left < 0 || right < 0 || right <= left {
				continue
			}
			rects = append(rects, rect{
				Top: top, Left: left, Bottom: bot, Right: right,
				Bordered: true,
			})
			break // use first matching bottom line
		}
	}
	return rects
}

// sharedEdge returns the (left, right) vline pair that bracket rows
// top..bot. Returns (-1, -1) if no enclosing edges exist.
func sharedEdge(frame *Frame, top, bot int, vlines []int) (int, int) {
	if len(vlines) == 0 {
		return -1, -1
	}
	// Choose the smallest left and largest right that have border cells
	// in both rows.
	var left, right int = -1, -1
	for _, x := range vlines {
		hasTop := isBorderAt(frame, x, top)
		hasBot := isBorderAt(frame, x, bot)
		if !hasTop || !hasBot {
			continue
		}
		if left == -1 || x < left {
			left = x
		}
		if right == -1 || x > right {
			right = x
		}
	}
	return left, right
}

// isBorderAt returns true if the cell at (x, y) is a border glyph.
func isBorderAt(frame *Frame, x, y int) bool {
	if x < 0 || y < 0 || x >= frame.Cols || y >= frame.Rows {
		return false
	}
	return isBorderRune(frame.CellAt(x, y).Rune)
}

// classify turns a rect into a Widget by inspecting its contents.
func classify(frame *Frame, r rect) *Widget {
	text := rectText(frame, r)
	title := rectTitle(frame, r)

	w := &Widget{
		Top:    r.Top,
		Left:   r.Left,
		Bottom: r.Bottom,
		Right:  r.Right,
		Title:  title,
		Text:   text,
	}

	innerTop := r.Top + 1
	innerBot := r.Bottom - 1
	if innerBot < innerTop {
		w.Kind = WidgetPanel
		return w
	}

	// Decision tree:
	switch {
	case r.Top <= 2:
		w.Kind = WidgetHeader
	case looksLikeTable(frame, innerTop, innerBot, r.Left+1, r.Right-1):
		w.Kind = WidgetTable
	case looksLikeKPICard(frame, innerTop, innerBot, r.Left+1, r.Right-1):
		w.Kind = WidgetKPICard
	case looksLikeList(frame, innerTop, innerBot, r.Left+1, r.Right-1):
		w.Kind = WidgetList
	default:
		w.Kind = WidgetPanel
	}
	return w
}

// rectTitle returns the title candidate for a rect, conventionally the
// first non-blank line just inside its top border (between the borders).
func rectTitle(frame *Frame, r rect) string {
	if r.Top+1 >= r.Bottom {
		return ""
	}
	y := r.Top + 1
	var b strings.Builder
	for x := r.Left + 1; x < r.Right; x++ {
		c := frame.CellAt(x, y)
		if c.IsBlank() {
			break // stop at first blank — keeps titles short
		}
		b.WriteRune(c.Rune)
	}
	return strings.TrimSpace(b.String())
}

// rectText returns the joined text content of a rect, line by line,
// trimmed of trailing whitespace.
func rectText(frame *Frame, r rect) string {
	var lines []string
	for y := r.Top + 1; y < r.Bottom && y < frame.Rows; y++ {
		var line strings.Builder
		for x := r.Left + 1; x < r.Right && x < frame.Cols; x++ {
			c := frame.CellAt(x, y)
			if c.IsBlank() {
				line.WriteByte(' ')
			} else {
				line.WriteRune(c.Rune)
			}
		}
		lines = append(lines, trimRight(line.String()))
	}
	// drop empty leading/trailing lines
	for len(lines) > 0 && lines[0] == "" {
		lines = lines[1:]
	}
	for len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	return strings.Join(lines, "\n")
}

// looksLikeList returns true when the interior is several short lines of
// mostly non-blank text with no aligned columns.
func looksLikeList(frame *Frame, top, bot, left, right int) bool {
	if bot-top < 1 || right-left < 1 {
		return false
	}
	nonBlank := 0
	for y := top; y <= bot; y++ {
		if rowHasContent(frame, y, left, right) {
			nonBlank++
		}
	}
	// 3+ non-blank rows with at least 30% density = list-ish.
	return nonBlank >= 3 && nonBlank*3 >= (bot-top+1)*2
}

// looksLikeKPICard returns true when the interior has one large number
// (or short token) centred in mostly empty space.
func looksLikeKPICard(frame *Frame, top, bot, left, right int) bool {
	if bot-top > 4 || right-left > 30 {
		return false
	}
	// Pull interior text and count digits + non-blank cells.
	text := rectText(frame, rect{Top: top - 1, Left: left - 1, Bottom: bot + 1, Right: right + 1})
	if text == "" {
		return false
	}
	digits := 0
	letters := 0
	for _, r := range text {
		if unicode.IsDigit(r) {
			digits++
		}
		if unicode.IsLetter(r) {
			letters++
		}
	}
	total := digits + letters
	if total == 0 {
		return false
	}
	// A KPI card has 2+ digits in a small box, or a single short token.
	return (digits >= 2 && total <= 8) || (total <= 4 && (bot-top) <= 2)
}

// looksLikeTable returns true when several rows show at least 2 aligned
// columns separated by ≥3 spaces.
func looksLikeTable(frame *Frame, top, bot, left, right int) bool {
	if bot-top < 2 || right-left < 8 {
		return false
	}
	rowsWithCols := 0
	for y := top; y <= bot; y++ {
		if rowHasColumns(frame, y, left, right) {
			rowsWithCols++
		}
	}
	return rowsWithCols >= 3
}

// rowHasColumns returns true when row y has at least 2 "words" with a
// gap of 3+ spaces between them.
func rowHasColumns(frame *Frame, y, left, right int) bool {
	inWord := false
	gap := 0
	words := 0
	for x := left; x <= right && x < frame.Cols; x++ {
		c := frame.CellAt(x, y)
		if !c.IsBlank() {
			if !inWord && gap >= 3 {
				words++
			}
			inWord = true
			gap = 0
		} else {
			if inWord {
				words++
			}
			inWord = false
			gap++
		}
	}
	if inWord {
		words++
	}
	return words >= 2
}

// rowHasContent returns true if the row has any non-blank cell in [l, r].
func rowHasContent(frame *Frame, y, l, r int) bool {
	for x := l; x <= r && x < frame.Cols; x++ {
		if !frame.CellAt(x, y).IsBlank() {
			return true
		}
	}
	return false
}

// hasNonBlank reports whether any cell in the rectangle [l..r] × [t..b] is non-blank.
func hasNonBlank(frame *Frame, l, t, r, b int) bool {
	for y := t; y <= b && y < frame.Rows; y++ {
		for x := l; x <= r && x < frame.Cols; x++ {
			if !frame.CellAt(x, y).IsBlank() {
				return true
			}
		}
	}
	return false
}

// rowText returns the text of a single row, trimmed of trailing whitespace.
func rowText(frame *Frame, y int) string {
	var b strings.Builder
	for x := 0; x < frame.Cols; x++ {
		c := frame.CellAt(x, y)
		if c.IsBlank() {
			b.WriteByte(' ')
		} else {
			b.WriteRune(c.Rune)
		}
	}
	return trimRight(b.String())
}

// trimRight drops trailing spaces from s.
func trimRight(s string) string {
	for len(s) > 0 && s[len(s)-1] == ' ' {
		s = s[:len(s)-1]
	}
	return s
}

// PrintTree pretty-prints t to stdout. Indentation reflects nesting.
func PrintTree(t *WidgetTree) {
	if t == nil {
		fmt.Println("(empty tree)")
		return
	}
	fmt.Printf("frame %dx%d\n", t.FrameCols, t.FrameRows)
	printChildren(t.Root, 0)
}

func printChildren(ws []*Widget, depth int) {
	indent := strings.Repeat("  ", depth)
	for _, w := range ws {
		title := w.Title
		if title == "" && w.Text != "" {
			// First line of text as a stand-in title.
			title = firstLine(w.Text)
			if len(title) > 40 {
				title = title[:40] + "…"
			}
		}
		fmt.Printf("%s- %s @ (%d,%d)-(%d,%d) %q\n",
			indent, w.Kind, w.Top, w.Left, w.Bottom, w.Right, title)
		if len(w.Children) > 0 {
			printChildren(w.Children, depth+1)
		}
	}
}

// firstLine returns the first line of s with trailing whitespace stripped.
func firstLine(s string) string {
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		s = s[:i]
	}
	return trimRight(s)
}