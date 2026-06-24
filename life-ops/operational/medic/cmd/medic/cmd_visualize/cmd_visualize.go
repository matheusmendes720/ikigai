// Package cmd_visualize implements `medic visualize`.
//
// Architecture note: this package imports internal/visual directly (not via
// subprocess re-entry). The visual package has no heavy GUI dependencies
// — only standard library + creack/pty — so the import is safe even
// when building a static medic binary.
package cmd_visualize

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/shell"
	"github.com/life-oss/medic/internal/store"
	"github.com/life-oss/medic/internal/visual"
)

// Cmd builds `medic visualize`.
func Cmd() *cobra.Command {
	var (
		binary    string
		args      []string
		script    string
		golden    string
		out       string
		cols      int
		rows      int
		maxFrames int
		fps       int
		headless  bool
	)
	c := &cobra.Command{
		Use:   "visualize",
		Short: "Drive a TUI in a PTY and capture frames",
		Long: `medic visualize launches a TUI/CLI binary in a pseudo-terminal, runs a
keystroke script, captures each frame as SVG + raw cell grid, and diffs
against a golden directory. Output goes to .medic/visualize/<timestamp>/.

Used by agentic workflows to detect visual regressions.`,
		Example: `  medic visualize --binary ../apps/tui/bin/pav --script scripts/demo.yaml
  medic visualize --binary ../apps/cli/bin/typer --cols 120 --rows 40 --fps 8`,
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load(".")
			if err != nil {
				return err
			}
			if binary == "" {
				binary = cfg.Visual.Binary
			}
			if cols == 0 {
				cols = cfg.Visual.Cols
			}
			if rows == 0 {
				rows = cfg.Visual.Rows
			}
			if fps == 0 {
				fps = cfg.Visual.FrameRateMs
			}
			if out == "" {
				out = cfg.Visual.OutputDir
			}
			s, err := store.New(cfg.Target.Local)
			if err != nil {
				return err
			}
			dir, err := s.SnapshotDir("visualize")
			if err != nil {
				return err
			}
			fmt.Fprintf(cmd.OutOrStdout(), "→ capturing %s (cols=%d rows=%d fps=%d) → %s\n",
				binary, cols, rows, fps, dir)

			opts := visualizeOpts{
				Binary:    binary,
				Args:      args,
				Script:    script,
				GoldenDir: golden,
				OutDir:    dir,
				Cols:      cols,
				Rows:      rows,
				FPS:       fps,
				MaxFrames: maxFrames,
			}
			if headless || script == "" {
				return runHeadless(cmd.Context(), opts)
			}
			return runScripted(cmd.Context(), opts)
		},
	}
	c.Flags().StringVarP(&binary, "binary", "b", "", "binary to drive (required)")
	c.Flags().StringSliceVar(&args, "args", nil, "args passed to the binary")
	c.Flags().StringVarP(&script, "script", "s", "", "keystroke script (YAML)")
	c.Flags().StringVarP(&golden, "golden", "g", "", "golden frames dir (for diff)")
	c.Flags().StringVarP(&out, "out", "o", "", "output dir (default: .medic/visualize/<timestamp>)")
	c.Flags().IntVar(&cols, "cols", 120, "PTY cols")
	c.Flags().IntVar(&rows, "rows", 40, "PTY rows")
	c.Flags().IntVar(&maxFrames, "max-frames", 60, "stop after N frames (0=unlimited)")
	c.Flags().IntVar(&fps, "fps", 8, "capture rate (frames per second)")
	c.Flags().BoolVar(&headless, "headless", false, "run binary with no script, capture final output")
	return c
}

// visualizeOpts holds the parameters for a visualize run.
type visualizeOpts struct {
	Binary    string
	Args      []string
	Script    string
	GoldenDir string
	OutDir    string
	Cols      int
	Rows      int
	FPS       int
	MaxFrames int
}

// runHeadless runs the binary with no script and saves combined output.
// Used in CI or when --headless is set.
func runHeadless(ctx context.Context, o visualizeOpts) error {
	exec := shell.NewExecutor()
	res, err := exec.Run(ctx, ".", o.Binary, o.Args...)
	if err != nil && res == nil {
		return err
	}
	stdoutPath := filepath.Join(o.OutDir, "stdout.txt")
	stderrPath := filepath.Join(o.OutDir, "stderr.txt")
	combined := res.Stdout + "\n--- stderr ---\n" + res.Stderr
	if err := os.WriteFile(stdoutPath, []byte(combined), 0o644); err != nil {
		return err
	}
	_ = os.WriteFile(stderrPath, []byte(res.Stderr), 0o644)
	fmt.Fprintf(os.Stderr, "  stdout %d bytes → %s\n  stderr %d bytes → %s\n  exit %d\n",
		len(res.Stdout), stdoutPath, len(res.Stderr), stderrPath, res.ExitCode)
	return nil
}

// runScripted parses the script, launches the PTY, runs the keystrokes,
// captures frames, and optionally diffs against golden.
func runScripted(ctx context.Context, o visualizeOpts) error {
	// 1. Parse keystroke script.
	script, err := visual.LoadScript(o.Script)
	if err != nil {
		return fmt.Errorf("script: %w", err)
	}

	// 2. Start PTY.
	sess, err := shell.StartPTY(ctx, o.Cols, o.Rows, o.Binary, o.Args...)
	if err != nil {
		return fmt.Errorf("pty start: %w", err)
	}
	defer sess.Close()

	// 3. Wire capture → recorder.
	capturer := visual.NewCapturer()
	recorder := visual.NewRecorder()

	_, err = recorder.Start(o.OutDir)
	if err != nil {
		return fmt.Errorf("recorder start: %w", err)
	}

	recorder.SetMeta(visual.RecordingMeta{
		Binary: o.Binary,
		Args:   o.Args,
		Cols:   o.Cols,
		Rows:   o.Rows,
		Script: o.Script,
	})

	frameRateMs := 1000
	if o.FPS > 0 {
		frameRateMs = 1000 / o.FPS
	}
	frames, errCh, setupErr := capturer.Run(ctx, sess, visual.CaptureOpts{
		FrameRateMs:  frameRateMs,
		MaxFrames:    o.MaxFrames,
		FilterNoise:  true,
		StopOnIdleMs: 2000,
	})
	if setupErr != nil {
		return fmt.Errorf("capturer: %w", setupErr)
	}

	// 4. Run script in parallel with frame capture.
	scriptErrCh := make(chan error, 1)
	go func() {
		scriptErrCh <- visual.Run(ctx, sess, script)
		close(scriptErrCh)
	}()

	// 5. Drain frames into recorder.
	var captureErr error
	frameIdx := 0
	for {
		select {
		case f, ok := <-frames:
			if !ok {
				goto afterFrames
			}
			if err := recorder.Record(f); err != nil {
				captureErr = fmt.Errorf("record frame %d: %w", frameIdx, err)
				goto afterFrames
			}
			frameIdx++
		case err := <-errCh:
			if err != nil {
				captureErr = err
				goto afterFrames
			}
		case err := <-scriptErrCh:
			// Script finished. Keep capturing until PTY closes or MaxFrames reached.
			if err != nil {
				fmt.Fprintf(os.Stderr, "script error (continuing): %v\n", err)
			}
		case <-ctx.Done():
			captureErr = ctx.Err()
			goto afterFrames
		}
	}
afterFrames:

	// 6. Stop and flush.
	rec, err := recorder.Stop()
	if err != nil {
		return fmt.Errorf("recorder stop: %w", err)
	}
	fmt.Fprintf(os.Stderr, "✓ captured %d frames → %s\n", rec.Meta.Frames, rec.Dir)

	// 7. Diff against golden if available.
	if captureErr == nil && o.GoldenDir != "" {
		diff, err := rec.DiffAgainst(o.GoldenDir)
		if err != nil {
			fmt.Fprintf(os.Stderr, "diff error (non-fatal): %v\n", err)
		} else if diff.Changed > 0 {
			scorePct := float64(diff.Score * 100)
			fmt.Fprintf(os.Stderr, "⚠ %d/%d frames differ from golden (avg score %.1f%%)\n",
				diff.Changed, diff.Total, scorePct)
		} else {
			fmt.Fprintf(os.Stderr, "✓ all %d frames match golden\n", diff.Total)
		}
	}

	return captureErr
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
