package main

import (
	"fmt"
	"strings"

	"github.com/life-oss/medic/internal/visual"
)

func main() {
	// 1) Plain text
	f := visual.ParseANSIText([]byte("hello world"), 20, 5)
	fmt.Printf("plain text=%q\n", strings.TrimRight(f.String(), "\n"))

	// 2) SGR fg colour + bold
	ansi := "\x1b[1;31mERROR\x1b[0m: failed\n"
	f2 := visual.ParseANSIText([]byte(ansi), 20, 3)
	c := f2.CellAt(0, 0)
	fmt.Printf("sgr E=%+v bold=%v fg=%s\n", c.Rune, c.Bold, c.Fg)

	// 3) 256-colour
	ansi256 := "\x1b[38;5;196mred256\x1b[0m\n"
	f3 := visual.ParseANSIText([]byte(ansi256), 20, 2)
	c3 := f3.CellAt(0, 0)
	fmt.Printf("256 E=%+v fg=%s\n", c3.Rune, c3.Fg)

	// 4) Truecolor
	ansiTrue := "\x1b[38;2;10;20;30mtrue\x1b[0m\n"
	f4 := visual.ParseANSIText([]byte(ansiTrue), 20, 2)
	c4 := f4.CellAt(0, 0)
	fmt.Printf("true E=%+v fg=%s\n", c4.Rune, c4.Fg)

	// 5) Cursor position + clear screen
	mixed := "\x1b[2J\x1b[10;5HAt-10-5"
	f5 := visual.ParseANSIText([]byte(mixed), 40, 20)
	r, _ := f5.CellAt(4, 9).Rune, 0
	fmt.Printf("cup cell=%q (expect 'A')\n", r)

	// 6) Box drawing — use a 4-wide, 5-tall frame so the trailing
	// LF doesn't trigger an autowrap-induced scroll that would
	// visually shift the box upward.
	box := "┌──┐\n│hi│\n└──┘\n"
	f6 := visual.ParseANSIText([]byte(box), 4, 5)
	fmt.Printf("box %dx%d first-cell=%q\n", f6.Cols, f6.Rows, f6.CellAt(0, 0).Rune)

	// 7) CompareFrames
	a := visual.NewFrame(5, 2)
	a.SetCell(0, 0, visual.Cell{Rune: 'a'})
	b := visual.NewFrame(5, 2)
	b.SetCell(0, 0, visual.Cell{Rune: 'b'})
	rep := visual.CompareFrames(a, b)
	fmt.Printf("diff report: %s\n", rep)

	// 8) RenderSVG
	svg := visual.RenderSVG(f6)
	fmt.Printf("svg len=%d starts=%q\n", len(svg), svg[:min(60, len(svg))])

	// 9) Script
	s := &visual.Script{Name: "demo"}
	s.Add(visual.ScriptStep{WaitMs: 100})
	s.Add(visual.ScriptStep{Key: "Enter"})
	s.Add(visual.ScriptStep{Text: "hello"})
	fmt.Printf("script steps=%d\n", len(s.Steps))
	if err := visual.SaveScript(s, "test_script.json"); err != nil {
		fmt.Println("save err:", err)
	} else {
		loaded, err := visual.LoadScript("test_script.json")
		if err != nil {
			fmt.Println("load err:", err)
		} else {
			fmt.Printf("round-tripped steps=%d name=%q\n", len(loaded.Steps), loaded.Name)
		}
	}

	// 10) Inspector
	tree := visual.Inspect(f6)
	fmt.Printf("inspected widgets=%d\n", len(tree.Root))
	for _, w := range tree.Root {
		fmt.Printf("  - %s @ (%d,%d)-(%d,%d)\n", w.Kind, w.Top, w.Left, w.Bottom, w.Right)
	}

	// 11) Recorder
	rec := visual.NewRecorder()
	if _, err := rec.Start("test_rec"); err != nil {
		fmt.Println("rec start err:", err)
	} else {
		rec.SetMeta(visual.RecordingMeta{Binary: "demo", Cols: 4, Rows: 3, Term: "xterm-256color"})
		rec.Record(f6)
		rec.Record(f6)
		rec.Record(f6)
		r, err := rec.Stop()
		if err != nil {
			fmt.Println("rec stop err:", err)
		} else {
			fmt.Printf("recording dir=%s frames=%d\n", r.Dir, r.Meta.Frames)
		}
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}