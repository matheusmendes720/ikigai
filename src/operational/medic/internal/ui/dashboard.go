// Package ui provides the tview dashboard for medic.
//
// The Dashboard binds key health/review/pattern snapshots into a tview App
// with three panes:
//
//   ┌─ left:  Pillar list (Health, Review, Patterns, Visual) ──┐
//   ├─ middle: detail for selected pillar                       ┤
//   ├─ right:  recent activity / logs                           ┤
//   └─ bottom: status / shortcuts bar                            ┘
//
// Bindings:
//
//   q       quit
//   r       refresh current pillar
//   R       refresh all
//   1..4    switch pillar
//   :       command palette
package ui

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/gdamore/tcell/v2"
	"github.com/rivo/tview"
)

// Snapshot is a per-pillar display payload. Different pillars fill different
// fields; all are optional.
type Snapshot struct {
	Health    any    `json:"health,omitempty"`
	Review    any    `json:"review,omitempty"`
	Patterns  any    `json:"patterns,omitempty"`
	Visual    any    `json:"visual,omitempty"`
	Title     string `json:"title,omitempty"`
	Generated time.Time `json:"generated"`
}

// Loader is what the dashboard calls to (re)populate itself.
type Loader func(ctx context.Context) (Snapshot, error)

// App is the dashboard.
type App struct {
	tv     *tview.Application
	pages  *tview.Pages
	list   *tview.TextView
	body   *tview.TextView
	log    *tview.TextView
	status *tview.TextView
	loader Loader
	mu     sync.Mutex
	snap   Snapshot
}

// New builds the dashboard.
func New(loader Loader) *App {
	a := &App{loader: loader, tv: tview.NewApplication()}
	a.pages = tview.NewPages()

	a.list = tview.NewTextView().SetDynamicColors(true).SetWrap(false)
	a.list.SetBorder(true).SetTitle(" Pillars ")

	a.body = tview.NewTextView().SetDynamicColors(true).SetScrollable(true).SetChangedFunc(func() { a.tv.Draw() })
	a.body.SetBorder(true).SetTitle(" Detail ")

	a.log = tview.NewTextView().SetDynamicColors(true).SetScrollable(true).SetChangedFunc(func() { a.tv.Draw() })
	a.log.SetBorder(true).SetTitle(" Activity ")

	a.status = tview.NewTextView().SetDynamicColors(true)
	a.status.SetTextAlign(tview.AlignLeft)

	flex := tview.NewFlex().
		AddItem(a.list, 24, 0, true).
		AddItem(tview.NewFlex().SetDirection(tview.FlexRow).
			AddItem(a.body, 0, 3, false).
			AddItem(a.log, 0, 2, false), 0, 1, false).
		AddItem(a.status, 0, 1, false)

	a.pages.AddPage("main", flex, true, true)

	a.tv.SetInputCapture(func(e *tcell.EventKey) *tcell.EventKey {
		switch e.Key() {
		case tcell.KeyEsc, tcell.Key('q'):
			a.tv.Stop()
			return nil
		case tcell.Key('r'):
			go a.refresh(false)
			return nil
		case tcell.Key('R'):
			go a.refresh(true)
			return nil
		case tcell.Key('1'):
			a.selectPillar(0)
			return nil
		case tcell.Key('2'):
			a.selectPillar(1)
			return nil
		case tcell.Key('3'):
			a.selectPillar(2)
			return nil
		case tcell.Key('4'):
			a.selectPillar(3)
			return nil
		}
		return e
	})
	a.tv.SetRoot(a.pages, true).SetFocus(a.list)
	return a
}

// Run blocks until the user quits.
func (a *App) Run(ctx context.Context) error {
	go a.refresh(true)
	go a.tick(ctx)
	return a.tv.Run()
}

func (a *App) tick(ctx context.Context) {
	t := time.NewTicker(2 * time.Second)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			a.tv.QueueUpdateDraw(func() { a.status.SetText(time.Now().Format("15:04:05  medic 🩺 ready  —  [r] refresh  [R] reload  [q] quit")) })
		}
	}
}

func (a *App) refresh(all bool) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.appendLog(fmt.Sprintf("[gray]%s[white] refreshing…", time.Now().Format("15:04:05")))
	snap, err := a.loader(context.Background())
	if err != nil {
		a.appendLog(fmt.Sprintf("[red]loader error: %v", err))
		return
	}
	a.snap = snap
	a.tv.QueueUpdateDraw(func() { a.render() })
	a.appendLog("[green]refresh ok")
}

func (a *App) selectPillar(i int) {
	// Pillar selection is purely visual here — the body shows the whole
	// snapshot. A more elaborate UI would paginate.
	a.tv.QueueUpdateDraw(func() {
		a.body.ScrollToBeginning()
		a.body.Highlight()
		fmt.Fprintf(a.body, "[yellow]selected pillar #%d[white]\n\n", i+1)
	})
}

func (a *App) render() {
	a.list.SetText(strings.Join([]string{
		"[::b]Pillars[-:-:-]",
		" 1. Health",
		" 2. Review",
		" 3. Patterns",
		" 4. Visual",
		"",
		"[gray]Shortcuts:[-]",
		" [yellow]r[white] refresh",
		" [yellow]R[white] reload all",
		" [yellow]q[white] quit",
	}, "\n"))
	fmt.Fprintf(a.body, "[::b]%s[-:-:-]\n\n", a.snap.Title)
	if a.snap.Generated.IsZero() {
		fmt.Fprintf(a.body, "[gray]no data yet — press R to load[-]\n")
	} else {
		fmt.Fprintf(a.body, "[gray]snapshot @ %s[-]\n\n", a.snap.Generated.Format(time.RFC3339))
		if a.snap.Health != nil {
			fmt.Fprintf(a.body, "[yellow]Health[-]\n  %s\n\n", summarize(a.snap.Health))
		}
		if a.snap.Review != nil {
			fmt.Fprintf(a.body, "[yellow]Review[-]\n  %s\n\n", summarize(a.snap.Review))
		}
		if a.snap.Patterns != nil {
			fmt.Fprintf(a.body, "[yellow]Patterns[-]\n  %s\n\n", summarize(a.snap.Patterns))
		}
		if a.snap.Visual != nil {
			fmt.Fprintf(a.body, "[yellow]Visual[-]\n  %s\n\n", summarize(a.snap.Visual))
		}
	}
}

func summarize(v any) string {
	return fmt.Sprintf("%v", v)
}

func (a *App) appendLog(line string) {
	a.tv.QueueUpdateDraw(func() {
		fmt.Fprintf(a.log, "%s\n", line)
		a.log.ScrollToEnd()
	})
}

// Stop signals the app to quit.
func (a *App) Stop() { a.tv.Stop() }
