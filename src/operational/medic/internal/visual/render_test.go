package visual

import (
	"strings"
	"testing"
)

func TestRenderText(t *testing.T) {
	f := NewFrame(4, 2)
	f.SetCell(0, 0, Cell{Rune: 'h'})
	f.SetCell(1, 0, Cell{Rune: 'i'})
	got := string(RenderText(f))
	// RenderText returns the same shape as Frame.String
	if !strings.HasPrefix(got, "hi") {
		t.Errorf("RenderText: %q, want prefix 'hi'", got)
	}
}

func TestRenderTSVFormat(t *testing.T) {
	f := NewFrame(2, 2)
	f.SetCell(0, 0, Cell{Rune: 'A', Fg: RGB{0xff, 0, 0}, Bold: true})
	got := string(RenderTSV(f))
	lines := strings.Split(strings.TrimRight(got, "\n"), "\n")
	if len(lines) != 2 {
		t.Fatalf("TSV lines = %d, want 2", len(lines))
	}
	// Row 0 has 2 cells; A is at col 0 with red fg
	if !strings.Contains(lines[0], "A") || !strings.Contains(lines[0], "#ff0000") {
		t.Errorf("TSV row 0 = %q, want A and #ff0000", lines[0])
	}
	if !strings.Contains(lines[0], "BOLD") && !strings.Contains(lines[0], "B") {
		// Implementation may emit "B" / "BI" / "BOLD" — accept any of these.
		// The point is to confirm Bold was emitted.
		_ = lines[0]
	}
	// Real check: the row should contain a token representing Bold.
	if !containsAny(lines[0], "BOLD", "B", "bold") {
		t.Errorf("TSV row 0 = %q, want Bold flag", lines[0])
	}
}

func TestRenderSVGStartsWithXML(t *testing.T) {
	f := NewFrame(2, 2)
	f.SetCell(0, 0, Cell{Rune: 'X'})
	got := RenderSVG(f)
	if !strings.HasPrefix(string(got), "<?xml") {
		t.Errorf("RenderSVG does not start with <?xml; got prefix %q", got[:min(40, len(got))])
	}
	if !strings.Contains(string(got), "<svg") {
		t.Errorf("RenderSVG missing <svg>: %q", got[:min(200, len(got))])
	}
}

func TestRenderSVGContainsCell(t *testing.T) {
	f := NewFrame(3, 1)
	f.SetCell(0, 0, Cell{Rune: 'A', Fg: RGB{0x12, 0x34, 0x56}})
	got := string(RenderSVG(f))
	if !strings.Contains(got, "A") {
		t.Errorf("SVG missing glyph 'A'")
	}
	if !strings.Contains(got, "#123456") {
		t.Errorf("SVG missing fg color #123456")
	}
}

func TestRenderSVGDimensions(t *testing.T) {
	f := NewFrame(120, 40)
	got := string(RenderSVG(f))
	// 120 cols × CellW (8) = 960 px; 40 rows × CellH (16) = 640 px
	if !strings.Contains(got, `width="960"`) {
		t.Errorf("SVG missing width=960: %s", got[:200])
	}
	if !strings.Contains(got, `height="640"`) {
		t.Errorf("SVG missing height=640: %s", got[:200])
	}
}

func TestAttrsString(t *testing.T) {
	// attrsString returns short codes: B (bold), I (italic), U (underline),
	// R (reverse). The exact format may grow, but the codes must be present.
	c := Cell{Bold: true, Italic: true}
	if got := attrsString(c); !strings.Contains(got, "B") || !strings.Contains(got, "I") {
		t.Errorf("attrsString(Bold+Italic) = %q, want B and I", got)
	}
	c2 := Cell{Underline: true}
	if got := attrsString(c2); !strings.Contains(got, "U") {
		t.Errorf("attrsString(Underline) = %q, want U", got)
	}
	c3 := Cell{Reverse: true}
	if got := attrsString(c3); !strings.Contains(got, "R") {
		t.Errorf("attrsString(Reverse) = %q, want R", got)
	}
	// Empty cell = empty string.
	c4 := Cell{}
	if got := attrsString(c4); got != "" {
		t.Errorf("attrsString(empty) = %q, want \"\"", got)
	}
}

func containsAny(s string, needles ...string) bool {
	for _, n := range needles {
		if strings.Contains(s, n) {
			return true
		}
	}
	return false
}
