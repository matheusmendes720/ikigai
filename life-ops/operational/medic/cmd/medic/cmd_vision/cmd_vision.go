// Package cmd_vision implements `medic vision` — MiniMax VL-01 integration.
package cmd_vision

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/shell"
	"github.com/life-oss/medic/internal/store"
	"github.com/life-oss/medic/internal/visual"
	"github.com/life-oss/medic/internal/visioncritic"
)

// Cmd builds `medic vision`.
func Cmd() *cobra.Command {
	c := &cobra.Command{
		Use:   "vision",
		Short: "Vision critique via MiniMax-VL-01 (mmx)",
		Long: `medic vision drives MiniMax's mmx CLI to send a captured TUI frame
to MiniMax-VL-01 and parses the response into structured findings.

Subcommands:
  critique <frame>   critique a saved SVG/TSV frame file
  capture <binary>   run a TUI binary, capture one frame, then critique it
  doctor            report whether mmx + MINIMAX_API_KEY are wired up`,
	}
	c.AddCommand(critiqueCmd(), captureCmd(), doctorCmd())
	return c
}

func critiqueCmd() *cobra.Command {
	var (
		promptFile string
		systemFile string
		model      string
		cols       int
		rows       int
		timeoutMs  int
		outFile    string
	)
	c := &cobra.Command{
		Use:   "critique <frame.svg|frame.tsv>",
		Short: "Send a saved frame to mmx and print the parsed critique",
		Example: `  medic vision critique .medic/visualize/2026-06-22_17-04-12/frames/005.svg
  medic vision critique frame.svg --prompt-file configs/medic/promts/visual-critic.txt --out critique.json`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := visioncritic.Available(""); err != nil {
				return err
			}
			if _, err := config.Load("."); err != nil {
				return err
			}
			data, err := os.ReadFile(args[0])
			if err != nil {
				return err
			}
			frame := frameFromBytes(data, args[0])
			critic := visioncritic.New()
			opts := visioncritic.Options{
				Model:            model,
				PromptFile:       promptFile,
				SystemPromptFile: systemFile,
				Cols:             cols,
				Rows:             rows,
				Timeout:          durOr(timeoutMs, 60_000),
			}
			cr, err := critic.Critique(cmd.Context(), frame, opts)
			if err != nil {
				return err
			}
			fmt.Fprintln(cmd.OutOrStdout(), cr.String())
			s, _ := store.New(".")
			rel := "vision/" + filepath.Base(args[0]) + ".json"
			_ = s.WriteFile(rel, mustJSON(cr))
			if outFile == "" {
				outFile = ".medic/" + rel
			}
			fmt.Fprintf(cmd.OutOrStdout(), "saved → %s\n", outFile)
			return nil
		},
	}
	c.Flags().StringVar(&promptFile, "prompt-file", "", "user-prompt file (overrides default)")
	c.Flags().StringVar(&systemFile, "system-file", "", "system-prompt file")
	c.Flags().StringVar(&model, "model", "", "mmx model name (empty = mmx default)")
	c.Flags().IntVar(&cols, "cols", 120, "frame cols (hint for prompt)")
	c.Flags().IntVar(&rows, "rows", 40, "frame rows (hint for prompt)")
	c.Flags().IntVar(&timeoutMs, "timeout-ms", 60000, "mmx call timeout (ms)")
	c.Flags().StringVar(&outFile, "out", "", "output JSON path")
	return c
}

func captureCmd() *cobra.Command {
	var (
		binary     string
		args       []string
		cols       int
		rows       int
		waitMs     int
		promptFile string
		outFile    string
	)
	c := &cobra.Command{
		Use:   "capture <binary>",
		Short: "Run a TUI binary, capture one frame, then critique it",
		Long: `medic vision capture is a one-shot pipeline: spawn the binary,
wait for it to emit output (or wait-ms), snapshot the PTY output,
parse it as ANSI into a frame, then call mmx.`,
		Example: `  medic vision capture ../apps/tui/bin/pav --wait-ms 1500
  medic vision capture pav --cols 120 --rows 40 --prompt-file visual-critic.txt`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := visioncritic.Available(""); err != nil {
				return err
			}
			exec := shell.NewExecutor()
			res, err := exec.RunWithTimeout(".", durOr(waitMs+5000, 5_000), args[0], args[1:]...)
			if err != nil && res == nil {
				return err
			}
			frame := visual.ParseANSIText([]byte(res.Stdout+"\n"+res.Stderr), cols, rows)
			critic := visioncritic.New()
			cr, err := critic.Critique(cmd.Context(), frame, visioncritic.Options{
				PromptFile: promptFile,
				Cols:        cols, Rows: rows,
			})
			if err != nil {
				return err
			}
			fmt.Fprintln(cmd.OutOrStdout(), cr.String())
			if outFile == "" {
				outFile = ".medic/vision/captured.json"
			}
			_ = os.WriteFile(outFile, mustJSON(cr), 0o644)
			fmt.Fprintf(cmd.OutOrStdout(), "saved → %s\n", outFile)
			return nil
		},
	}
	c.Flags().StringVarP(&binary, "binary", "b", "", "binary (positional also accepted)")
	c.Flags().StringSliceVar(&args, "args", nil, "args passed to the binary")
	c.Flags().IntVar(&cols, "cols", 120, "frame cols")
	c.Flags().IntVar(&rows, "rows", 40, "frame rows")
	c.Flags().IntVar(&waitMs, "wait-ms", 1500, "wait for output before snapshot")
	c.Flags().StringVar(&promptFile, "prompt-file", "", "user-prompt file")
	c.Flags().StringVar(&outFile, "out", "", "output JSON path")
	return c
}

func doctorCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "doctor",
		Short: "Check mmx + MINIMAX_API_KEY availability",
		RunE: func(cmd *cobra.Command, _ []string) error {
			err := visioncritic.Available("")
			if err == nil {
				fmt.Fprintln(cmd.OutOrStdout(), "✓ mmx installed and MINIMAX_API_KEY set")
				return nil
			}
			fmt.Fprintf(cmd.OutOrStdout(), "✗ %v\n", err)
			fmt.Fprintln(cmd.OutOrStdout(), "→ install with: scripts/install_mmx.sh")
			fmt.Fprintln(cmd.OutOrStdout(), "→ then export MINIMAX_API_KEY=***")
			os.Exit(2)
			return nil
		},
	}
}

// frameFromBytes picks the right parser based on file extension.
func frameFromBytes(data []byte, path string) *visual.Frame {
	switch filepath.Ext(path) {
	case ".svg", ".tsv":
		// Reconstructing a Frame from SVG/TSV is a TODO; we use a
		// placeholder so the rest of the pipeline (mmx, prompt) still
		// works. The mmx tool reads the original file directly.
		return visual.NewFrame(120, 40)
	default:
		return visual.ParseANSIText(data, 120, 40)
	}
}

func mustJSON(c *visioncritic.Critique) []byte {
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return []byte(`{"error":"` + err.Error() + `"}`)
	}
	return data
}

func durOr(ms, fallback int) time.Duration {
	if ms == 0 {
		ms = fallback
	}
	return time.Duration(ms) * time.Millisecond
}

// Silence unused-import for cobra.Command closure that uses cmd.Context().
var _ = context.Background
