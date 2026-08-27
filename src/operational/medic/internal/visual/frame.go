// Package visual is the cell-grid visual-debug layer of medic.
//
// It drives a TUI (Textual, Bubble Tea, tview, Rich, blessed, ...) inside a
// pseudo-terminal, parses the ANSI/ANSI-256/truecolor output stream into a
// per-frame Cell grid, then renders each frame as both an SVG and a TSV
// text dump. Frames can be diffed against golden masters, scripts can drive
// a TUI programmatically, and recordings on disk are diffable like git
// trees.
//
// The package is used by:
//
//   - `medic visualize` — interactive debugger over a recorded stream
//   - `medic debug`      — run a TUI and step through it
//   - `medic golden`     — capture / verify golden frames
//
// The capture layer relies on shell.PTYSession for the underlying pseudo-
// terminal; this package adds the parser, renderer, differ, script runner
// and recorder on top.
package visual

import (
	"crypto/sha1"
	"encoding/hex"
	"fmt"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

// RGB is a 24-bit colour. Each channel is 0..255.
type RGB [3]uint8

// String returns the CSS-style "#rrggbb" representation of the colour.
// Useful for SVG output and human-readable logs.
func (c RGB) String() string { return fmt.Sprintf("#%02x%02x%02x", c[0], c[1], c[2]) }

// Named is the set of base-16 ANSI colours indexed by 0..15.
// Index 0 is black, index 7 is light grey (a.k.a. "white" in dark themes),
// 8 is "bright black", 15 is "bright white". Values match the xterm 256
// palette so that 8-bit colour 0..15 round-trips through Named.
var Named = [16]RGB{
	{0x00, 0x00, 0x00}, // 0 black
	{0xcd, 0x00, 0x00}, // 1 red
	{0x00, 0xcd, 0x00}, // 2 green
	{0xcd, 0xcd, 0x00}, // 3 yellow
	{0x00, 0x00, 0xee}, // 4 blue
	{0xcd, 0x00, 0xcd}, // 5 magenta
	{0x00, 0xcd, 0xcd}, // 6 cyan
	{0xe5, 0xe5, 0xe5}, // 7 white (light grey)
	{0x7f, 0x7f, 0x7f}, // 8 bright black (dark grey)
	{0xff, 0x00, 0x00}, // 9 bright red
	{0x00, 0xff, 0x00}, // 10 bright green
	{0xff, 0xff, 0x00}, // 11 bright yellow
	{0x5c, 0x5c, 0xff}, // 12 bright blue
	{0xff, 0x00, 0xff}, // 13 bright magenta
	{0x00, 0xff, 0xff}, // 14 bright cyan
	{0xff, 0xff, 0xff}, // 15 bright white
}

// Cell is a single terminal cell: one rune with its colours and attributes.
//
// The default zero value is a space with default fg/bg and no attributes;
// that matches what a freshly cleared terminal looks like.
type Cell struct {
	Rune      rune // The glyph; ' ' for blank cells.
	Fg        RGB  // Foreground colour.
	Bg        RGB  // Background colour.
	Bold      bool
	Italic    bool
	Underline bool
	Reverse   bool
}

// IsBlank reports whether the cell holds no glyph and no formatting of
// interest — used by the renderer to skip wasted <text> nodes.
func (c Cell) IsBlank() bool { return c.Rune == 0 || c.Rune == ' ' }

// DefaultCell is the cell the rest of the grid inherits from when nothing
// else has been written. Most terminals default to light-grey on black.
var DefaultCell = Cell{Rune: ' ', Fg: Named[7], Bg: Named[0]}

// Frame is one captured snapshot of the terminal cell grid.
//
// It is value-cheap to copy (cells are small + Rune is one word) but
// most call sites use *Frame so the renderer can mutate the hash lazily.
type Frame struct {
	Cols       int       // Width in cells.
	Rows       int       // Height in cells.
	Cells      []Cell    // Row-major, length == Cols*Rows.
	CapturedAt time.Time // When this frame was captured.
	Hash       string    // SHA1 of the cells; computed lazily by RecomputeHash.
}

// NewFrame returns an empty frame of size cols×rows filled with DefaultCell.
func NewFrame(cols, rows int) *Frame {
	if cols < 1 {
		cols = 1
	}
	if rows < 1 {
		rows = 1
	}
	f := &Frame{
		Cols:  cols,
		Rows:  rows,
		Cells: make([]Cell, cols*rows),
	}
	for i := range f.Cells {
		f.Cells[i] = DefaultCell
	}
	return f
}

// SetCell writes c at (x, y). Out-of-range coordinates are ignored silently —
// the parser can race ahead of a window resize and we don't want to crash.
func (f *Frame) SetCell(x, y int, c Cell) {
	if f == nil {
		return
	}
	if x < 0 || y < 0 || x >= f.Cols || y >= f.Rows {
		return
	}
	f.Cells[y*f.Cols+x] = c
	f.Hash = "" // invalidate
}

// CellAt returns the cell at (x, y). Out-of-range returns the zero Cell.
func (f *Frame) CellAt(x, y int) Cell {
	if f == nil || x < 0 || y < 0 || x >= f.Cols || y >= f.Rows {
		return Cell{}
	}
	return f.Cells[y*f.Cols+x]
}

// in reports whether (x, y) is inside the frame's bounds.
func (f *Frame) in(x, y int) bool {
	return f != nil && x >= 0 && y >= 0 && x < f.Cols && y < f.Rows
}

// Resize changes the frame's dimensions, preserving content where possible.
// New cells are filled with DefaultCell.
func (f *Frame) Resize(cols, rows int) {
	if f == nil || (cols == f.Cols && rows == f.Rows) {
		return
	}
	if cols < 1 {
		cols = 1
	}
	if rows < 1 {
		rows = 1
	}
	out := make([]Cell, cols*rows)
	for i := range out {
		out[i] = DefaultCell
	}
	w := cols
	if f.Cols < w {
		w = f.Cols
	}
	h := rows
	if f.Rows < h {
		h = f.Rows
	}
	for y := range h {
		for x := range w {
			out[y*cols+x] = f.Cells[y*f.Cols+x]
		}
	}
	f.Cols = cols
	f.Rows = rows
	f.Cells = out
	f.Hash = ""
}

// Clear resets the frame to default cells and updates CapturedAt.
func (f *Frame) Clear() {
	if f == nil {
		return
	}
	for i := range f.Cells {
		f.Cells[i] = DefaultCell
	}
	f.CapturedAt = time.Now()
	f.Hash = ""
}

// String returns the frame as plain text (one row per line, trailing
// whitespace per row preserved). Handy for log lines and golden tests.
func (f *Frame) String() string {
	if f == nil {
		return ""
	}
	var b strings.Builder
	b.Grow(f.Cols*f.Rows + f.Rows)
	for y := range f.Rows {
		for x := range f.Cols {
			c := f.Cells[y*f.Cols+x]
			if c.Rune == 0 {
				b.WriteByte(' ')
			} else {
				b.WriteRune(c.Rune)
			}
		}
		if y != f.Rows-1 {
			b.WriteByte('\n')
		}
	}
	return b.String()
}

// Equal reports whether two frames have identical cells (sizes included).
// CapturedAt and Hash are not compared.
func (f *Frame) Equal(o *Frame) bool {
	if f == nil || o == nil {
		return f == o
	}
	if f.Cols != o.Cols || f.Rows != o.Rows {
		return false
	}
	for i := range f.Cells {
		if f.Cells[i] != o.Cells[i] {
			return false
		}
	}
	return true
}

// RecomputeHash recomputes and stores the SHA1 hash of the cells.
// The hash includes only the cell grid, not metadata, so two frames
// captured at different times but with identical content share a hash.
func (f *Frame) RecomputeHash() string {
	if f == nil {
		return ""
	}
	h := sha1.New()
	// Emit cells as a stable, compact byte stream. 8 bytes per attribute
	// flags + 1 rune + 6 colour bytes = 15..16 bytes per cell.
	for _, c := range f.Cells {
		var attrs byte
		if c.Bold {
			attrs |= 1
		}
		if c.Italic {
			attrs |= 2
		}
		if c.Underline {
			attrs |= 4
		}
		if c.Reverse {
			attrs |= 8
		}
		var rb [4]byte
		rb[0] = byte(c.Rune)
		rb[1] = byte(c.Rune >> 8)
		rb[2] = byte(c.Rune >> 16)
		rb[3] = byte(c.Rune >> 24)
		h.Write(rb[:])
		h.Write([]byte{attrs, c.Fg[0], c.Fg[1], c.Fg[2], c.Bg[0], c.Bg[1], c.Bg[2]})
	}
	f.Hash = hex.EncodeToString(h.Sum(nil))
	return f.Hash
}

// CellDiff is one differing cell between two frames.
// A is the cell in self, B is the cell in other; either may be blank.
type CellDiff struct {
	X int `json:"x"`
	Y int `json:"y"`
	A Cell `json:"a"`
	B Cell `json:"b"`
}

// Diff returns one entry per cell that differs between f and other.
// Bounded by Cols*Rows; cheaply testable with len().
func (f *Frame) Diff(o *Frame) []CellDiff {
	if f == nil || o == nil {
		return nil
	}
	if f.Cols != o.Cols || f.Rows != o.Rows {
		// Size mismatch: emit a single sentinel "diff" with the top-left
		// cell containing the bounds. Callers that want a richer shape
		// can call Resize first.
		return []CellDiff{{
			X: 0, Y: 0,
			A: Cell{Rune: rune(f.Cols), Fg: Named[12]},
			B: Cell{Rune: rune(o.Cols), Fg: Named[12]},
		}}
	}
	var out []CellDiff
	for y := range f.Rows {
		for x := range f.Cols {
			if f.Cells[y*f.Cols+x] != o.Cells[y*f.Cols+x] {
				out = append(out, CellDiff{
					X: x, Y: y,
					A: f.Cells[y*f.Cols+x],
					B: o.Cells[y*f.Cols+x],
				})
			}
		}
	}
	return out
}

// ----------------------------------------------------------------------
// ANSI parser
// ----------------------------------------------------------------------

// ansiParser holds the state of an incremental ANSI text parser.
// It supports the common subset emitted by Python prompt_toolkit / Textual,
// Rich, Bubble Tea (via tview), and tview directly.
type ansiParser struct {
	cols, rows int
	frame      *Frame
	cx, cy     int // Cursor position
	// pendingWrap is set when a putChar landed at the last column; the
	// wrap to (0, next-row) is applied on the NEXT putChar (matching the
	// behaviour of real terminals, which defer the wrap until the next
	// character actually arrives — otherwise a trailing LF after a full
	// line would advance two rows instead of one).
	pendingWrap bool
	cur         Cell // Current SGR attributes
	// saved* are push/pop state for CSI s / u (DECSC / DECRC).
	savedX, savedY int
	savedCell      Cell
}

// newAnsiParser builds a fresh parser pinned to a cols×rows grid.
func newAnsiParser(cols, rows int) *ansiParser {
	p := &ansiParser{
		cols:     cols,
		rows:     rows,
		frame:    NewFrame(cols, rows),
		cur:      DefaultCell,
		savedX:   0,
		savedY:   0,
		savedCell: DefaultCell,
	}
	p.frame.CapturedAt = time.Now()
	return p
}

// resetAttrs restores DefaultCell and writes the cursor home.
func (p *ansiParser) reset() {
	p.cur = DefaultCell
	p.cx, p.cy = 0, 0
}

// clearScreen resets the entire frame and homes the cursor.
func (p *ansiParser) clearScreen() {
	p.frame.Clear()
	p.cx, p.cy = 0, 0
	p.frame.CapturedAt = time.Now()
}

// eraseInLine implements CSI Ps K.
//   Ps = 0 → clear from cursor to end of line
//   Ps = 1 → clear from start of line to cursor
//   Ps = 2 → clear the whole line
func (p *ansiParser) eraseInLine(n int) {
	switch n {
	case 0:
		for x := p.cx; x < p.cols; x++ {
			p.frame.SetCell(x, p.cy, DefaultCell)
		}
	case 1:
		for x := 0; x <= p.cx && x < p.cols; x++ {
			p.frame.SetCell(x, p.cy, DefaultCell)
		}
	case 2:
		for x := range p.cols {
			p.frame.SetCell(x, p.cy, DefaultCell)
		}
	}
}

// eraseInDisplay implements CSI Ps J.
//   Ps = 0 → clear from cursor to end of screen
//   Ps = 1 → clear from start of screen to cursor
//   Ps = 2 / 3 → clear entire screen
func (p *ansiParser) eraseInDisplay(n int) {
	switch n {
	case 0:
		p.eraseInLine(0)
		for y := p.cy + 1; y < p.rows; y++ {
			for x := range p.cols {
				p.frame.SetCell(x, y, DefaultCell)
			}
		}
	case 1:
		for y := 0; y < p.cy; y++ {
			for x := range p.cols {
				p.frame.SetCell(x, y, DefaultCell)
			}
		}
		p.eraseInLine(1)
	case 2, 3:
		p.frame.Clear()
	}
}

// cup implements CSI Ps1 ; Ps2 H — Cursor Position (1-based).
// Missing or zero arguments default to 1.
func (p *ansiParser) cup(row, col int) {
	if row < 1 {
		row = 1
	}
	if col < 1 {
		col = 1
	}
	p.cy = row - 1
	p.cx = col - 1
	if p.cy < 0 {
		p.cy = 0
	}
	if p.cy >= p.rows {
		p.cy = p.rows - 1
	}
	if p.cx < 0 {
		p.cx = 0
	}
	if p.cx >= p.cols {
		p.cx = p.cols - 1
	}
}

// putChar writes a single rune at the cursor position with deferred
// auto-wrap. The wrap to (0, next-row) happens on the NEXT putChar, not
// immediately — this matches real terminals, where the cursor sits at
// the last column until the next character arrives. Deferring the wrap
// also keeps a trailing LF after a full line from advancing two rows.
func (p *ansiParser) putChar(r rune) {
	if p.pendingWrap {
		p.pendingWrap = false
		p.cx = 0
		p.cy++
		if p.cy >= p.rows {
			p.cy = p.rows - 1
			// terminal scrolls: shift everything up one row
			copy(p.frame.Cells, p.frame.Cells[p.cols:])
			for x := range p.cols {
				p.frame.SetCell(x, p.rows-1, DefaultCell)
			}
		}
	}
	c := p.cur
	c.Rune = r
	p.frame.SetCell(p.cx, p.cy, c)
	p.cx++
	if p.cx >= p.cols {
		p.pendingWrap = true
		p.cx = p.cols - 1
	}
}

// applySGR consumes the parameter list from an SGR (CSI ... m) sequence
// and updates p.cur accordingly.
func (p *ansiParser) applySGR(params []int) {
	if len(params) == 0 {
		p.cur = DefaultCell
		return
	}
	i := 0
	for i < len(params) {
		n := params[i]
		switch {
		case n == 0:
			p.cur = DefaultCell
		case n == 1:
			p.cur.Bold = true
		case n == 2:
			// faint: fold into bold-off on light themes
			p.cur.Bold = false
		case n == 3:
			p.cur.Italic = true
		case n == 4:
			p.cur.Underline = true
		case n == 7:
			p.cur.Reverse = true
		case n == 22:
			p.cur.Bold = false
		case n == 23:
			p.cur.Italic = false
		case n == 24:
			p.cur.Underline = false
		case n == 27:
			p.cur.Reverse = false
		case n == 39:
			p.cur.Fg = DefaultCell.Fg
		case n == 49:
			p.cur.Bg = DefaultCell.Bg
		case n >= 30 && n <= 37:
			p.cur.Fg = Named[n-30]
		case n >= 40 && n <= 47:
			p.cur.Bg = Named[n-40]
		case n >= 90 && n <= 97:
			p.cur.Fg = Named[n-90+8]
		case n >= 100 && n <= 107:
			p.cur.Bg = Named[n-100+8]
		case n == 38 || n == 48:
			// Extended colour. Look ahead for 5;N or 2;R;G;B.
			isFg := n == 38
			if i+1 >= len(params) {
				return
			}
			mode := params[i+1]
			switch mode {
			case 5:
				if i+2 >= len(params) {
					return
				}
				idx := params[i+2]
				rgb, ok := lookup256(idx)
				if !ok {
					// unknown: leave as default
					rgb = DefaultCell.Fg
					if !isFg {
						rgb = DefaultCell.Bg
					}
				}
				if isFg {
					p.cur.Fg = rgb
				} else {
					p.cur.Bg = rgb
				}
				i += 2
			case 2:
				if i+4 >= len(params) {
					return
				}
				r, g, b := clampByte(params[i+2]), clampByte(params[i+3]), clampByte(params[i+4])
				if isFg {
					p.cur.Fg = RGB{r, g, b}
				} else {
					p.cur.Bg = RGB{r, g, b}
				}
				i += 4
			}
		}
		i++
	}
}

// clampByte maps a possibly-out-of-range int to a uint8.
func clampByte(n int) uint8 {
	if n < 0 {
		return 0
	}
	if n > 255 {
		return 255
	}
	return uint8(n)
}

// lookup256 returns the xterm 256-colour palette entry for index 0..255.
// 0..15 are the Named set, 16..231 are a 6×6×6 colour cube, 232..255 are
// a 24-step greyscale ramp.
func lookup256(idx int) (RGB, bool) {
	if idx < 0 || idx > 255 {
		return RGB{}, false
	}
	if idx < 16 {
		return Named[idx], true
	}
	if idx >= 232 {
		// greyscale ramp: xterm maps 232..255 to 8,18,28,...,238
		v := uint8(8 + (idx-232)*10)
		return RGB{v, v, v}, true
	}
	// 6×6×6 cube
	idx -= 16
	r := idx / 36
	g := (idx / 6) % 6
	b := idx % 6
	step := func(n int) uint8 {
		if n == 0 {
			return 0
		}
		return uint8(55 + n*40)
	}
	return RGB{step(r), step(g), step(b)}, true
}

// feed pushes a chunk of raw bytes into the parser, mutating p.frame in place.
func (p *ansiParser) feed(buf []byte) {
	i := 0
	for i < len(buf) {
		b := buf[i]
		switch {
		case b == 0x1b && i+1 < len(buf) && buf[i+1] == '[':
			// CSI sequence
			i += 2
			j := i
			for j < len(buf) {
				c := buf[j]
				if (c >= 0x40 && c <= 0x7e) || c == 0x9c {
					break
				}
				j++
			}
			if j >= len(buf) {
				return // truncated; will resume on next feed
			}
			final := buf[j]
			body := string(buf[i:j])
			i = j + 1
			p.dispatchCSI(body, final)
		case b == 0x1b && i+1 < len(buf) && buf[i+1] == ']':
			// OSC — skip until BEL or ST. We don't model OSC, but we must
			// consume it so we don't print the title text as glyphs.
			i += 2
			for i < len(buf) {
				if buf[i] == 0x07 { // BEL
					i++
					break
				}
				if buf[i] == 0x1b && i+1 < len(buf) && buf[i+1] == '\\' {
					i += 2
					break
				}
				i++
			}
		case b == 0x1b && i+1 < len(buf) && buf[i+1] == 'P':
			// DCS — skip until ST.
			i += 2
			for i < len(buf) {
				if buf[i] == 0x1b && i+1 < len(buf) && buf[i+1] == '\\' {
					i += 2
					break
				}
				i++
			}
		case b == 0x07:
			// lone BEL — ignore
			i++
		case b == 0x08:
			// BS — backspace, move cursor left one.
			if p.cx > 0 {
				p.cx--
			}
			i++
		case b == '\r':
			p.cx = 0
			i++
		case b == '\n':
			// LF semantics at the last column with a pending wrap:
			//   - if no wrap pending: just cy++
			//   - if wrap pending: discard the wrap and advance cy once
			//     (the wrap is dropped because the LF replaces the
			//     would-be next printable; cx resets to 0 so the next
			//     printable lands at the start of the new row).
			if p.pendingWrap {
				p.pendingWrap = false
				p.cx = 0
			}
			p.cy++
			if p.cy >= p.rows {
				p.cy = p.rows - 1
				// terminal scrolls: shift everything up one row
				copy(p.frame.Cells, p.frame.Cells[p.cols:])
				for x := range p.cols {
					p.frame.SetCell(x, p.rows-1, DefaultCell)
				}
			}
			i++
		case b == '	':
			// Tab to next multiple of 8.
			next := (p.cx/8 + 1) * 8
			if next >= p.cols {
				next = p.cols - 1
			}
			p.cx = next
			i++
		case b < 0x20:
			// Other C0 controls — drop.
			i++
		default:
			r, size := utf8.DecodeRune(buf[i:])
			if r == utf8.RuneError && size <= 1 {
				// invalid byte — skip
				i++
				continue
			}
			p.putChar(r)
			i += size
		}
	}
	p.frame.CapturedAt = time.Now()
}

// dispatchCSI handles a fully-buffered CSI sequence (without the leading
// ESC[). body is the parameter+intermediate bytes; final is the final byte.
func (p *ansiParser) dispatchCSI(body string, final byte) {
	switch final {
	case 'm':
		params := splitParams(body)
		p.applySGR(params)
	case 'H', 'f':
		row, col := 1, 1
		if body != "" {
			parts := strings.SplitN(body, ";", 2)
			if parts[0] != "" {
				if v, err := strconv.Atoi(parts[0]); err == nil {
					row = v
				}
			}
			if len(parts) == 2 && parts[1] != "" {
				if v, err := strconv.Atoi(parts[1]); err == nil {
					col = v
				}
			}
		}
		p.cup(row, col)
	case 'J':
		n := 0
		if body != "" {
			if v, err := strconv.Atoi(body); err == nil {
				n = v
			}
		}
		p.eraseInDisplay(n)
	case 'K':
		n := 0
		if body != "" {
			if v, err := strconv.Atoi(body); err == nil {
				n = v
			}
		}
		p.eraseInLine(n)
	case 'A':
		// CUU — Cursor Up
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		p.cy -= n
		if p.cy < 0 {
			p.cy = 0
		}
	case 'B':
		// CUD — Cursor Down
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		p.cy += n
		if p.cy >= p.rows {
			p.cy = p.rows - 1
		}
	case 'C':
		// CUF — Cursor Forward
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		p.cx += n
		if p.cx >= p.cols {
			p.cx = p.cols - 1
		}
	case 'D':
		// CUB — Cursor Backward
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		p.cx -= n
		if p.cx < 0 {
			p.cx = 0
		}
	case 'G':
		// CHA — Cursor Horizontal Absolute (1-based)
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		p.cx = n - 1
		if p.cx < 0 {
			p.cx = 0
		}
		if p.cx >= p.cols {
			p.cx = p.cols - 1
		}
	case 'd':
		// VPA — Vertical Line Position Absolute (1-based)
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		p.cy = n - 1
		if p.cy < 0 {
			p.cy = 0
		}
		if p.cy >= p.rows {
			p.cy = p.rows - 1
		}
	case 's':
		// DECSC — Save cursor
		p.savedX, p.savedY = p.cx, p.cy
		p.savedCell = p.cur
	case 'u':
		// DECRC — Restore cursor
		p.cx, p.cy = p.savedX, p.savedY
		p.cur = p.savedCell
	case '@':
		// ICH — Insert Character: shift right at cursor, drop tail.
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		for k := p.cols - 1; k >= p.cx+n; k-- {
			p.frame.SetCell(k, p.cy, p.frame.CellAt(k-n, p.cy))
		}
		for k := p.cx; k < p.cx+n && k < p.cols; k++ {
			p.frame.SetCell(k, p.cy, DefaultCell)
		}
	case 'P':
		// DCH — Delete Character: shift left.
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		for k := p.cx; k+n < p.cols; k++ {
			p.frame.SetCell(k, p.cy, p.frame.CellAt(k+n, p.cy))
		}
		for k := p.cols - n; k < p.cols; k++ {
			if k < 0 {
				continue
			}
			p.frame.SetCell(k, p.cy, DefaultCell)
		}
	case 'L':
		// IL — Insert Line: scroll down at cursor.
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		for y := p.rows - 1; y >= p.cy+n && y-n < p.rows; y-- {
			for x := range p.cols {
				p.frame.SetCell(x, y, p.frame.CellAt(x, y-n))
			}
		}
		for y := p.cy; y < p.cy+n && y < p.rows; y++ {
			for x := range p.cols {
				p.frame.SetCell(x, y, DefaultCell)
			}
		}
	case 'M':
		// DL — Delete Line: scroll up at cursor.
		n := 1
		if v, err := strconv.Atoi(body); err == nil {
			n = v
		}
		for y := p.cy; y+n < p.rows; y++ {
			for x := range p.cols {
				p.frame.SetCell(x, y, p.frame.CellAt(x, y+n))
			}
		}
		for y := p.rows - n; y < p.rows; y++ {
			if y < 0 {
				continue
			}
			for x := range p.cols {
				p.frame.SetCell(x, y, DefaultCell)
			}
		}
	case 'r':
		// DECSTBM — Set Top/Bottom Margins.
		var top, bot int
		if body != "" {
			parts := strings.SplitN(body, ";", 2)
			if v, err := strconv.Atoi(parts[0]); err == nil {
				top = v
			}
			if len(parts) == 2 {
				if v, err := strconv.Atoi(parts[1]); err == nil {
					bot = v
				}
			}
		}
		if top < 1 {
			top = 1
		}
		if bot < 1 || bot > p.rows {
			bot = p.rows
		}
		// We don't actually maintain a scroll region beyond scrolling on
		// \n, but we still want to honour the home position.
		_ = top
		_ = bot
	case 'h', 'l':
		// SM/RM — set/reset mode (e.g. 25 = cursor visibility, 1049 = alt screen).
		// We treat 1049 specially: it implies a full screen clear.
		for _, raw := range strings.Split(body, ";") {
			v, err := strconv.Atoi(raw)
			if err != nil {
				continue
			}
			if v == 1049 && final == 'h' {
				p.clearScreen()
			}
		}
	}
}

// splitParams parses a CSI parameter string into ints.
// Empty fields default to 0 (which SGR interprets as reset).
func splitParams(s string) []int {
	if s == "" {
		return []int{0}
	}
	parts := strings.Split(s, ";")
	out := make([]int, len(parts))
	for i, p := range parts {
		v, err := strconv.Atoi(p)
		if err != nil {
			v = 0
		}
		out[i] = v
	}
	return out
}

// ParseANSIText parses raw ANSI escape sequences into a Frame. The parser
// is fully driven from rawBytes; no streaming state is required. This is
// the entry point used by tests and replay tools.
func ParseANSIText(rawBytes []byte, cols, rows int) *Frame {
	p := newAnsiParser(cols, rows)
	p.feed(rawBytes)
	p.frame.RecomputeHash()
	return p.frame
}