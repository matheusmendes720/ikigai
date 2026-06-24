package visual

import (
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// FrameDiffReport describes the result of comparing two frames.
//
//   - Matching: cells that are identical in both frames.
//   - Changed:  cells whose content differs (one CellDiff per cell).
//   - Added:    cells that are non-blank in B but blank in A.
//   - Removed:  cells that are non-blank in A but blank in B.
//   - Score:    similarity 0..1; 1 = identical.
//
// The four diff categories are mutually exclusive (Changed is everything
// where both sides are non-blank or non-blank-in-different-way).
type FrameDiffReport struct {
	Cols     int        `json:"cols"`
	Rows     int        `json:"rows"`
	Matching []CellDiff `json:"matching"`
	Changed  []CellDiff `json:"changed"`
	Added    []CellDiff `json:"added"`
	Removed  []CellDiff `json:"removed"`
	Score    float64    `json:"score"`
}

// String returns a compact, human-readable summary suitable for log lines.
func (r FrameDiffReport) String() string {
	return fmt.Sprintf("frame-diff cols=%d rows=%d changed=%d added=%d removed=%d matching=%d score=%.3f",
		r.Cols, r.Rows, len(r.Changed), len(r.Added), len(r.Removed), len(r.Matching), r.Score)
}

// CompareFrames returns a FrameDiffReport comparing a and b.
//
// If sizes differ the report collapses into a single Changed entry and
// the score is 0. The caller may Resize one frame to the other first if
// they want a richer comparison.
func CompareFrames(a, b *Frame) FrameDiffReport {
	r := FrameDiffReport{}
	if a == nil || b == nil {
		r.Score = 0
		return r
	}
	r.Cols, r.Rows = a.Cols, a.Rows
	if a.Cols != b.Cols || a.Rows != b.Rows {
		r.Changed = []CellDiff{{
			X: 0, Y: 0,
			A: Cell{Rune: 'X', Fg: Named[12]},
			B: Cell{Rune: 'X', Fg: Named[12]},
		}}
		r.Cols, r.Rows = maxDim(a.Cols, b.Cols), maxDim(a.Rows, b.Rows)
		r.Score = 0
		return r
	}
	total := a.Cols * a.Rows
	if total == 0 {
		r.Score = 1
		return r
	}
	matching := 0
	for y := 0; y < a.Rows; y++ {
		for x := 0; x < a.Cols; x++ {
			ca := a.CellAt(x, y)
			cb := b.CellAt(x, y)
			if ca == cb {
				matching++
				continue
			}
			diff := CellDiff{X: x, Y: y, A: ca, B: cb}
			switch {
			case ca.IsBlank() && !cb.IsBlank():
				r.Added = append(r.Added, diff)
			case !ca.IsBlank() && cb.IsBlank():
				r.Removed = append(r.Removed, diff)
			default:
				r.Changed = append(r.Changed, diff)
			}
		}
	}
	r.Score = float64(matching) / float64(total)
	return r
}

// maxDim returns the larger of two ints; used by CompareFrames when the
// frames have mismatched sizes so the report still has meaningful bounds.
func maxDim(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// FrameSetDiff aggregates multiple FrameDiffReports across a paired set.
type FrameSetDiff struct {
	DirA    string            `json:"dir_a"`
	DirB    string            `json:"dir_b"`
	Frames  []FrameDiffReport `json:"frames"`
	Total   int               `json:"total_frames"`
	Changed int               `json:"changed_frames"`
	Score   float64           `json:"score"`
}

// CompareFrameSets walks dirA and dirB, pairs frame files by sorted index,
// and returns an aggregated FrameSetDiff.
//
// Frame files are recognised by the extensions .txt, .tsv, or .svg. The
// file's stem index is used for pairing (e.g. frame_001.txt pairs with
// frame_001.txt in the other dir). If the two dirs have different counts,
// the report pads with empty frames so callers can still see the gap.
func CompareFrameSets(dirA, dirB string) (*FrameSetDiff, error) {
	pairsA, err := indexFrames(dirA)
	if err != nil {
		return nil, fmt.Errorf("visual: index dirA: %w", err)
	}
	pairsB, err := indexFrames(dirB)
	if err != nil {
		return nil, fmt.Errorf("visual: index dirB: %w", err)
	}
	out := &FrameSetDiff{DirA: dirA, DirB: dirB}

	// Walk union of indices.
	all := make(map[string]struct{}, len(pairsA)+len(pairsB))
	for k := range pairsA {
		all[k] = struct{}{}
	}
	for k := range pairsB {
		all[k] = struct{}{}
	}
	keys := make([]string, 0, len(all))
	for k := range all {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, k := range keys {
		fa, faOK := pairsA[k]
		fb, fbOK := pairsB[k]
		var report FrameDiffReport
		switch {
		case faOK && fbOK:
			report = CompareFrames(fa, fb)
		case faOK:
			report = FrameDiffReport{
				Cols: fa.Cols, Rows: fa.Rows,
				Removed: allNonBlank(fa),
				Score:   0,
			}
		case fbOK:
			report = FrameDiffReport{
				Cols: fb.Cols, Rows: fb.Rows,
				Added: allNonBlank(fb),
				Score:  0,
			}
		}
		if !nearlyEqual(report.Score, 1.0) {
			out.Changed++
		}
		out.Frames = append(out.Frames, report)
	}
	out.Total = len(out.Frames)
	if out.Total > 0 {
		var sum float64
		for _, r := range out.Frames {
			sum += r.Score
		}
		out.Score = sum / float64(out.Total)
	} else {
		out.Score = 1
	}
	return out, nil
}

// allNonBlank returns one CellDiff per non-blank cell, with the "other"
// side left as the zero Cell. Used when one side of a frame-set pair is
// missing — those cells all count as added or removed.
func allNonBlank(f *Frame) []CellDiff {
	if f == nil {
		return nil
	}
	var out []CellDiff
	for y := 0; y < f.Rows; y++ {
		for x := 0; x < f.Cols; x++ {
			c := f.CellAt(x, y)
			if c.IsBlank() {
				continue
			}
			out = append(out, CellDiff{X: x, Y: y, A: c})
		}
	}
	return out
}

// nearlyEqual is a float comparison with a tiny epsilon to dodge
// representation noise when comparing many frame scores.
func nearlyEqual(a, b float64) bool { return math.Abs(a-b) < 1e-9 }

// indexFrames reads every .txt/.tsv frame in dir and returns them keyed
// by their stem (without extension). Mismatched sizes across files are
// preserved as-is; CompareFrames will report a 0 score.
func indexFrames(dir string) (map[string]*Frame, error) {
	out := make(map[string]*Frame)
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return out, nil
		}
		return nil, err
	}
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		ext := strings.ToLower(filepath.Ext(name))
		if ext != ".txt" && ext != ".tsv" {
			continue
		}
		stem := strings.TrimSuffix(name, filepath.Ext(name))
		f, err := readFrameFile(filepath.Join(dir, name))
		if err != nil {
			return nil, fmt.Errorf("visual: read %s: %w", name, err)
		}
		out[stem] = f
	}
	return out, nil
}

// readFrameFile parses a single TSV dump back into a Frame. Used by
// CompareFrameSets when frames live on disk rather than in memory.
//
// Format (per line, tab-separated columns):
//
//	rune\tfg-hex\tbg-hex\tattrs
//
// attrs is a string of "B", "I", "U", "R" characters. Empty cell means
// a space. We don't enforce uniform column counts across rows; extra
// columns are ignored, missing columns become blank cells.
func readFrameFile(path string) (*Frame, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	// First pass: figure out rows and cols.
	lines := strings.Split(strings.ReplaceAll(string(data), "\r\n", "\n"), "\n")
	// Drop trailing empty line from final newline.
	if len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	maxCols := 0
	for _, line := range lines {
		if line == "" {
			continue
		}
		n := strings.Count(line, "\t") / 4 // each cell has 4 fields, joined by 3 tabs
		if n == 0 {
			n = strings.Count(line, "\t") + 1
		}
		if n > maxCols {
			maxCols = n
		}
	}
	if maxCols == 0 {
		maxCols = 80
	}
	frame := NewFrame(maxCols, max(len(lines), 1))
	for y, line := range lines {
		if y >= frame.Rows {
			break
		}
		parseFrameLine(frame, y, line)
	}
	frame.RecomputeHash()
	return frame, nil
}

// parseFrameLine writes one TSV row into frame at row y.
func parseFrameLine(frame *Frame, y int, line string) {
	if line == "" {
		return
	}
	// Split into per-cell groups of 4 fields.
	fields := strings.Split(line, "\t")
	for x := 0; x*4+3 < len(fields); x++ {
		glyph := fields[x*4]
		fg := fields[x*4+1]
		bg := fields[x*4+2]
		attrs := fields[x*4+3]
		runes := []rune(glyph)
		var r rune = ' '
		if len(runes) > 0 {
			r = runes[0]
		}
		c := Cell{Rune: r, Fg: parseHex(fg), Bg: parseHex(bg)}
		for _, ch := range attrs {
			switch ch {
			case 'B':
				c.Bold = true
			case 'I':
				c.Italic = true
			case 'U':
				c.Underline = true
			case 'R':
				c.Reverse = true
			}
		}
		if x < frame.Cols {
			frame.SetCell(x, y, c)
		}
	}
}

// parseHex parses a "#rrggbb" string into RGB. "#000" or "" → zero.
func parseHex(s string) RGB {
	if len(s) < 7 || s[0] != '#' {
		return Named[0]
	}
	var rgb RGB
	for i := 0; i < 3; i++ {
		hi := unhex(s[1+i*2])
		lo := unhex(s[2+i*2])
		if hi < 0 || lo < 0 {
			return Named[0]
		}
		rgb[i] = uint8(hi<<4 | lo)
	}
	return rgb
}

// unhex returns the int value of a hex digit, or -1 on error.
func unhex(c byte) int {
	switch {
	case c >= '0' && c <= '9':
		return int(c - '0')
	case c >= 'a' && c <= 'f':
		return int(c-'a') + 10
	case c >= 'A' && c <= 'F':
		return int(c-'A') + 10
	}
	return -1
}