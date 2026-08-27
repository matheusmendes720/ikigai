// Package cmd_debug implements `medic debug`.
package cmd_debug

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/shell"
	"github.com/life-oss/medic/internal/store"
)

// Cmd builds `medic debug`.
func Cmd() *cobra.Command {
	var (
		binary string
		args   []string
		cols   int
		rows   int
	)
	c := &cobra.Command{
		Use:   "debug",
		Short: "Interactive TUI debug REPL",
		Long: `medic debug drops you into an interactive REPL that runs a TUI in a PTY
and exposes commands to inspect it:

  tree    dump the captured widget tree
  shoot   capture the current frame as SVG
  resize  resize the PTY (e.g. resize 120 40)
  send    send a key (e.g. send Tab)
  text    send literal text
  shell   run a host shell command
  exit    quit`,
		Example: `  medic debug --binary ../apps/tui/bin/pav`,
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load(".")
			if err != nil {
				return err
			}
			if binary == "" {
				binary = cfg.Visual.Binary
			}
			if binary == "" {
				return fmt.Errorf("--binary is required (or set visual.binary in medic.yaml)")
			}
			if cols == 0 {
				cols = cfg.Visual.Cols
			}
			if rows == 0 {
				rows = cfg.Visual.Rows
			}
			s, _ := store.New(cfg.Target.Local)
			outDir, _ := s.Sub("debug")
			return runREPL(cmd.Context(), binary, args, cols, rows, outDir)
		},
	}
	c.Flags().StringVarP(&binary, "binary", "b", "", "binary to debug")
	c.Flags().StringSliceVar(&args, "args", nil, "args passed to the binary")
	c.Flags().IntVar(&cols, "cols", 120, "PTY cols")
	c.Flags().IntVar(&rows, "rows", 40, "PTY rows")
	return c
}

func runREPL(ctx context.Context, binary string, args []string, cols, rows int, outDir string) error {
	// For now we don't spin up a real PTY on Windows; we run as a plain subprocess
	// and capture its stream. Future: wire internal/shell.PTYSession on Unix.
	exec := shell.NewExecutor()
	_ = exec
	_ = outDir
	fmt.Fprintf(os.Stderr, "(medic debug) binary=%s cols=%d rows=%d  (PTY stub on Windows)\n", binary, cols, rows)
	fmt.Fprintln(os.Stderr, "commands: tree | shoot | resize W H | send <key> | text <str> | shell <cmd> | exit")

	in := bufio.NewScanner(os.Stdin)
	for {
		fmt.Fprintf(os.Stderr, "(medic) ▌ ")
		if !in.Scan() {
			break
		}
		line := strings.TrimSpace(in.Text())
		if line == "" {
			continue
		}
		parts := strings.Fields(line)
		switch parts[0] {
		case "exit", "quit", "q":
			return nil
		case "tree":
			fmt.Fprintln(os.Stderr, "  └─ (widget tree detection runs against a captured frame; use `shoot` first)")
		case "shoot":
			ts := nowStamp()
			path := filepath.Join(outDir, "shoot-"+ts+".txt")
			data := []byte("(stub frame — replace with visual.Frame rendering once internal/visual is built)\n")
			if err := os.WriteFile(path, data, 0o644); err != nil {
				fmt.Fprintf(os.Stderr, "  save error: %v\n", err)
				continue
			}
			fmt.Fprintf(os.Stderr, "  saved → %s\n", path)
		case "resize":
			if len(parts) != 3 {
				fmt.Fprintln(os.Stderr, "  usage: resize <cols> <rows>")
				continue
			}
			fmt.Fprintf(os.Stderr, "  resized to %sx%s (stub)\n", parts[1], parts[2])
		case "send":
			if len(parts) < 2 {
				fmt.Fprintln(os.Stderr, "  usage: send <key>")
				continue
			}
			fmt.Fprintf(os.Stderr, "  sent key %q (stub)\n", parts[1])
		case "text":
			if len(parts) < 2 {
				fmt.Fprintln(os.Stderr, "  usage: text <text>")
				continue
			}
			fmt.Fprintf(os.Stderr, "  sent text %q (stub)\n", strings.Join(parts[1:], " "))
		case "shell":
			if len(parts) < 2 {
				fmt.Fprintln(os.Stderr, "  usage: shell <cmd>")
				continue
			}
			out, err := exec.Run(ctx, ".", parts[1], parts[2:]...)
			if err != nil && out == nil {
				fmt.Fprintf(os.Stderr, "  shell error: %v\n", err)
				continue
			}
			fmt.Fprintln(os.Stderr, indent(out.Combined(), "  "))
		case "help", "?":
			fmt.Fprintln(os.Stderr, "  tree | shoot | resize W H | send <key> | text <str> | shell <cmd> | exit")
		default:
			fmt.Fprintf(os.Stderr, "  unknown: %s\n", parts[0])
		}
		_ = io.EOF
	}
	return nil
}

func indent(s, p string) string {
	var sb strings.Builder
	for _, line := range strings.Split(s, "\n") {
		sb.WriteString(p)
		sb.WriteString(line)
		sb.WriteString("\n")
	}
	return sb.String()
}

func nowStamp() string {
	return strings.ReplaceAll(strings.ReplaceAll(now().Format("15:04:05"), ":", "-"), ".", "-")
}

var now = func() time.Time { return time.Now() }