// Package cmd_ui implements `medic ui`.
//
// The "ui action" subcommand is the agentic integration point: from a YAML
// workflow you can call `medic ui action list` / `medic ui action run <name>`
// to drive a TUI binary without writing Go.
package cmd_ui

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

// Cmd builds `medic ui`.
func Cmd() *cobra.Command {
	c := &cobra.Command{
		Use:   "ui",
		Short: "UI utilities (action list/run) for workflows",
	}
	c.AddCommand(actionListCmd(), actionRunCmd())
	return c
}

func actionListCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "action list",
		Short: "List available UI actions",
		RunE: func(cmd *cobra.Command, _ []string) error {
			for _, a := range []string{
				"send-key — Send a key to the active TUI",
				"send-text — Send literal text",
				"resize — Resize the PTY",
				"shoot — Capture the current frame as SVG",
				"tree — Dump the widget tree",
				"wait — Sleep N ms",
				"assert-text — Assert the frame contains a substring (fails the step)",
				"assert-contains-glyph — Assert the frame contains a specific glyph",
			} {
				fmt.Fprintln(cmd.OutOrStdout(), "  - "+a)
			}
			return nil
		},
	}
}

func actionRunCmd() *cobra.Command {
	var args []string
	c := &cobra.Command{
		Use:   "action run <name>",
		Short: "Run a UI action with --args k=v,k=v",
		Example: `  medic ui action run shoot --args out=.medic/debug/frame.svg
  medic ui action run send-key --args key=Tab`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, _ []string) error {
			name := args[0]
			fmt.Fprintf(cmd.OutOrStdout(), "ui action %q with args %v (stub — wire internal/visual to enable)\n", name, args)
			_ = os.Stderr
			return nil
		},
	}
	c.Flags().StringSliceVar(&args, "args", nil, "args as k=v pairs")
	return c
}
