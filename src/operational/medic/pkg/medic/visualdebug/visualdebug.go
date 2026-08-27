// Package visualdebug wraps internal/visual for external consumers.
package visualdebug

import (
	"context"
	"fmt"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/shell"
	"github.com/life-oss/medic/internal/visual"
)

// Options tunes a Session.
type Options struct {
	Binary    string
	Args      []string
	Cols      int
	Rows      int
	FrameRate int // fps; converted to ms internally
	OutDir    string
}

// Session drives a TUI binary in a PTY and captures frames.
type Session struct {
	opts Options
}

// New builds a Session with defaults applied.
func New(opts Options) (*Session, error) {
	if opts.Binary == "" {
		return nil, fmt.Errorf("visualdebug: binary required")
	}
	if opts.Cols == 0 {
		opts.Cols = 120
	}
	if opts.Rows == 0 {
		opts.Rows = 40
	}
	if opts.FrameRate == 0 {
		opts.FrameRate = 8
	}
	return &Session{opts: opts}, nil
}

// Run executes a keystroke script and saves captured frames to outDir.
//
// It spawns the binary in a PTY, runs each script step (wait_ms, key, text),
// captures frames at the configured rate, and writes them to
// <outDir>/frames/NNN.txt + .svg. A meta.json + timeline.json are emitted on
// close.
//
// On Windows the PTY is currently unsupported; on that platform this method
// returns an error explaining the limitation.
func (s *Session) Run(ctx context.Context, scriptPath, outDir string) error {
	if outDir == "" {
		outDir = s.opts.OutDir
	}
	if outDir == "" {
		outDir = ".medic/visualize"
	}
	script, err := visual.LoadScript(scriptPath)
	if err != nil {
		return fmt.Errorf("visualdebug: load script: %w", err)
	}
	rec := visual.NewRecorder()
	recording, err := rec.Start(outDir)
	if err != nil {
		return fmt.Errorf("visualdebug: recorder: %w", err)
	}
	defer recording.Close()

	// Spawn binary in PTY
	sess, err := shell.StartPTY(ctx, s.opts.Cols, s.opts.Rows, s.opts.Binary, s.opts.Args...)
	if err != nil {
		return fmt.Errorf("visualdebug: pty: %w", err)
	}
	defer sess.Close()

	// Capturer
	frameMs := 1000 / s.opts.FrameRate
	if frameMs <= 0 {
		frameMs = 125
	}
	capt := visual.NewCapturer()
	frames, errs, runErr := capt.Run(ctx, sess, visual.CaptureOpts{
		FrameRateMs: frameMs,
		FilterNoise: true,
	})
	if runErr != nil {
		return runErr
	}

	// Drive script in a goroutine; main goroutine drains frames.
	scriptDone := make(chan error, 1)
	go func() {
		scriptDone <- visual.Run(ctx, sess, script)
	}()

	for f := range frames {
		if err := rec.Record(f); err != nil {
			return err
		}
	}
	// Capture finished (child exited or ctx cancelled); wait for script.
	if err := <-scriptDone; err != nil {
		// script errors are non-fatal (e.g. ctx canceled), surface for debug
		fmt.Printf("(visualdebug) script runner: %v\n", err)
	}
	if e, ok := <-errs; ok {
		return e
	}
	if _, err := rec.Stop(); err != nil {
		return err
	}
	return nil
}

// ConfigFromTarget is a helper for callers that want to derive Options from
// the target repo's medic.yaml.
func ConfigFromTarget(target string) (*Options, error) {
	cfg, err := config.Load(target)
	if err != nil {
		return nil, err
	}
	return &Options{
		Binary:    cfg.Visual.Binary,
		Cols:      cfg.Visual.Cols,
		Rows:      cfg.Visual.Rows,
		FrameRate: 1000 / maxInt(cfg.Visual.FrameRateMs, 1),
		OutDir:    cfg.Visual.OutputDir,
	}, nil
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
