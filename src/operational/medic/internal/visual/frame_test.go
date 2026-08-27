package visual

import (
	"strings"
	"testing"
)

// ---- RGB -----------------------------------------------------------------

func TestRGBString(t *testing.T) {
	c := RGB{0xcd, 0x00, 0x00}
	if got := c.String(); got != "#cd0000" {
		t.Errorf("RGB.String() = %q, want #cd0000", got)
	}
}

// ---- Cell.IsBlank --------------------------------------------------------

func TestCellIsBlank(t *testing.T) {
	cases := []struct {
		name string
		cell Cell
		want bool
	}{
		{"zero", Cell{}, true},
		{"space", Cell{Rune: ' '}, true},
		{"letter", Cell{Rune: 'a'}, false},
		{"box", Cell{Rune: '─'}, false},
		{"bolded-space", Cell{Rune: ' ', Bold: true}, true}, // rune check wins
	}
	for _, c := range cases {
		if got := c.cell.IsBlank(); got != c.want {
			t.Errorf("%s: IsBlank() = %v, want %v", c.name, got, c.want)
		}
	}
}

// ---- NewFrame / SetCell / CellAt ----------------------------------------

func TestNewFrameDimensions(t *testing.T) {
	f := NewFrame(10, 3)
	if f.Cols != 10 || f.Rows != 3 {
		t.Fatalf("cols/rows: got %d×%d, want 10×3", f.Cols, f.Rows)
	}
	if len(f.Cells) != 30 {
		t.Errorf("cells len = %d, want 30", len(f.Cells))
	}
	// All cells start blank with default fg/bg
	if !f.CellAt(0, 0).IsBlank() {
		t.Errorf("cell (0,0) not blank after NewFrame")
	}
}

func TestSetCellAndCellAt(t *testing.T) {
	f := NewFrame(5, 5)
	c := Cell{Rune: 'x', Fg: RGB{0xff, 0, 0}, Bold: true}
	f.SetCell(2, 3, c)
	got := f.CellAt(2, 3)
	if got.Rune != 'x' || got.Fg != (RGB{0xff, 0, 0}) || !got.Bold {
		t.Errorf("CellAt(2,3) = %+v, want %+v", got, c)
	}
	// Out of bounds → zero cell (no panic)
	if got := f.CellAt(-1, 0); got != (Cell{}) {
		t.Errorf("CellAt(-1,0) = %+v, want zero", got)
	}
	if got := f.CellAt(100, 100); got != (Cell{}) {
		t.Errorf("CellAt(oob) = %+v, want zero", got)
	}
}

// ---- Resize / Clear ------------------------------------------------------

func TestResizeGrowsAndShrinks(t *testing.T) {
	f := NewFrame(4, 4)
	f.SetCell(2, 2, Cell{Rune: 'z'})
	f.Resize(8, 8)
	if f.Cols != 8 || f.Rows != 8 {
		t.Errorf("after Resize: %d×%d, want 8×8", f.Cols, f.Rows)
	}
	if f.CellAt(2, 2).Rune != 'z' {
		t.Errorf("data lost on grow")
	}
	f.Resize(2, 2)
	if f.CellAt(2, 2) != (Cell{}) {
		t.Errorf("data outside new bounds survived")
	}
}

func TestClear(t *testing.T) {
	f := NewFrame(3, 3)
	f.SetCell(1, 1, Cell{Rune: 'q', Bold: true})
	f.Clear()
	if !f.CellAt(1, 1).IsBlank() {
		t.Errorf("Clear left a non-blank cell")
	}
	if f.CellAt(1, 1).Bold {
		t.Errorf("Clear left Bold set")
	}
}

// ---- String --------------------------------------------------------------

func TestFrameStringMultiline(t *testing.T) {
	f := NewFrame(4, 2)
	f.SetCell(0, 0, Cell{Rune: 'h'})
	f.SetCell(1, 0, Cell{Rune: 'i'})
	got := f.String()
	// Frame.String emits "hi\n    " — note: spaces, not blank lines, for
	// unset cells, and a single \n between rows (no trailing \n).
	if !strings.HasPrefix(got, "hi") {
		t.Errorf("expected first row to start with 'hi', got %q", got)
	}
	if !strings.Contains(got, "\n") {
		t.Errorf("expected at least one newline between rows, got %q", got)
	}
}

// ---- Equal + Diff --------------------------------------------------------

func TestFrameEqualAndDiff(t *testing.T) {
	a := NewFrame(5, 2)
	b := NewFrame(5, 2)
	if !a.Equal(b) {
		t.Errorf("two blank frames not equal")
	}
	a.SetCell(0, 0, Cell{Rune: 'x'})
	if a.Equal(b) {
		t.Errorf("frames with different cells reported equal")
	}
	diffs := a.Diff(b)
	if len(diffs) != 1 {
		t.Fatalf("Diff len = %d, want 1", len(diffs))
	}
	if diffs[0].X != 0 || diffs[0].Y != 0 {
		t.Errorf("diff coords = (%d,%d), want (0,0)", diffs[0].X, diffs[0].Y)
	}
	// A had rune 'x'; B had the default (blank). Check that Diff captured the change.
	if diffs[0].A.Rune != 'x' {
		t.Errorf("diff A rune = %d, want 'x'", diffs[0].A.Rune)
	}
	if diffs[0].B.Rune != ' ' {
		t.Errorf("diff B rune = %d, want blank", diffs[0].B.Rune)
	}
}

// ---- RecomputeHash (stable + changes on edit) ---------------------------

func TestHashStableAndChanges(t *testing.T) {
	f := NewFrame(4, 4)
	h1 := f.RecomputeHash()
	h2 := f.RecomputeHash()
	if h1 == "" {
		t.Errorf("hash is empty")
	}
	if h1 != h2 {
		t.Errorf("hash not stable across calls: %s vs %s", h1, h2)
	}
	f.SetCell(0, 0, Cell{Rune: 'p'})
	if f.RecomputeHash() == h1 {
		t.Errorf("hash unchanged after edit")
	}
}

// ---- ParseANSIText -------------------------------------------------------

func TestParseANSITextPlain(t *testing.T) {
	// Use cols=10 so "hello" fits without auto-wrap-induced scroll.
	f := ParseANSIText([]byte("hello"), 10, 1)
	if f.CellAt(0, 0).Rune != 'h' {
		t.Errorf("plain text: cell (0,0) = %d, want 'h' (104)", f.CellAt(0, 0).Rune)
	}
	if f.CellAt(4, 0).Rune != 'o' {
		t.Errorf("plain text: cell (4,0) = %d, want 'o' (111)", f.CellAt(4, 0).Rune)
	}
	// Cells past the input should remain blank (default fg)
	if f.CellAt(5, 0).Rune != ' ' {
		t.Errorf("plain text: cell (5,0) = %d, want blank", f.CellAt(5, 0).Rune)
	}
}

func TestParseANSITextSGRNamed(t *testing.T) {
	// Bold + named red fg
	f := ParseANSIText([]byte("\x1b[1;31mERROR\x1b[0m ok"), 10, 1)
	c := f.CellAt(0, 0)
	if c.Rune != 'E' || !c.Bold {
		t.Errorf("SGR bold/red: got %+v", c)
	}
	if c.Fg != (RGB{0xcd, 0, 0}) {
		t.Errorf("SGR red fg = %s, want #cd0000", c.Fg)
	}
	// After reset, cell at index 6 ('o') should be default fg
	if f.CellAt(6, 0).Rune != 'o' {
		t.Errorf("post-reset rune wrong")
	}
}

func TestParseANSITextSGR256(t *testing.T) {
	// 38;5;196 → bright red in 256-color palette
	f := ParseANSIText([]byte("\x1b[38;5;196mX\x1b[0m"), 2, 1)
	c := f.CellAt(0, 0)
	if c.Rune != 'X' {
		t.Errorf("256-color rune wrong: %+v", c)
	}
	// 256 palette entry 196 should be #ff0000
	want := RGB{0xff, 0, 0}
	if c.Fg != want {
		t.Errorf("256 fg = %s, want %s", c.Fg, want)
	}
}

func TestParseANSITextSGRTrueColor(t *testing.T) {
	f := ParseANSIText([]byte("\x1b[38;2;10;20;30mT\x1b[0m"), 2, 1)
	c := f.CellAt(0, 0)
	if c.Fg != (RGB{10, 20, 30}) {
		t.Errorf("truecolor fg = %s, want #0a141e", c.Fg)
	}
}

func TestParseANSITextClearScreen(t *testing.T) {
	f := ParseANSIText([]byte("AB\x1b[2J"), 4, 2)
	// After 2J, the screen is cleared → cells are blank
	for y := 0; y < f.Rows; y++ {
		for x := 0; x < f.Cols; x++ {
			if !f.CellAt(x, y).IsBlank() {
				t.Errorf("after 2J, cell (%d,%d) not blank: %+v", x, y, f.CellAt(x, y))
			}
		}
	}
}

func TestParseANSITextCUP(t *testing.T) {
	// Move cursor to (row 2, col 1) 1-based in ANSI, so cell (col 0, row 1)
	f := ParseANSIText([]byte("\x1b[2;1HAB"), 10, 3)
	if f.CellAt(0, 1).Rune != 'A' {
		t.Errorf("CUP(2,1): cell (0,1) = %+v, want A", f.CellAt(0, 1))
	}
}

func TestParseANSITextBoxDrawing(t *testing.T) {
	box := "┌──┐\n│hi│\n└──┘\n"
	// Use cols=4 rows=5 so the trailing LF doesn't trigger scroll-past-bottom.
	f := ParseANSIText([]byte(box), 4, 5)
	if f.CellAt(0, 0).Rune != '┌' {
		t.Errorf("box top-left: %+v, want ┌", f.CellAt(0, 0))
	}
	if f.CellAt(1, 0).Rune != '─' {
		t.Errorf("box top-edge: %+v, want ─", f.CellAt(1, 0))
	}
	if f.CellAt(1, 1).Rune != 'h' {
		t.Errorf("box interior: %+v, want h", f.CellAt(1, 1))
	}
}

func TestParseANSITextAttrBoldItalicUnderlineReverse(t *testing.T) {
	f := ParseANSIText([]byte("\x1b[1;3;4;7mZ\x1b[0m"), 2, 1)
	c := f.CellAt(0, 0)
	if !c.Bold || !c.Italic || !c.Underline || !c.Reverse {
		t.Errorf("attrs not set: %+v", c)
	}
}

func TestParseANSITextResetsAttrs(t *testing.T) {
	f := ParseANSIText([]byte("\x1b[1mA\x1b[0mB"), 4, 1)
	if !f.CellAt(0, 0).Bold {
		t.Errorf("A not bold")
	}
	if f.CellAt(1, 0).Bold {
		t.Errorf("B still bold after reset")
	}
}
