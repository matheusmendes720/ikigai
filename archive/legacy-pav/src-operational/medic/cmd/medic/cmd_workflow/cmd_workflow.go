// Package cmd_workflow implements `medic workflow`.
package cmd_workflow

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/agentic"
	"github.com/life-oss/medic/internal/config"
)

// Cmd builds `medic workflow`.
func Cmd() *cobra.Command {
	c := &cobra.Command{
		Use:   "workflow",
		Short: "Run declarative agentic workflows (YAML)",
		Long: `medic workflow runs multi-step agentic pipelines described in YAML.

Subcommands:
  run <file>     execute a workflow
  list           list built-in actions
  validate       parse + validate a workflow without running`,
	}
	c.AddCommand(runCmd(), listCmd(), validateCmd())
	return c
}

func runCmd() *cobra.Command {
	var target string
	var verbose bool
	var out string
	c := &cobra.Command{
		Use:   "run <file>",
		Short: "Run a workflow YAML file",
		Args:  cobra.ExactArgs(1),
		Example: `  medic workflow run examples/workflow/pr-review.yaml
  medic workflow run ./my-flow.yaml --target ./packages/core --verbose`,
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := config.Load(target)
			if err != nil {
				return err
			}
			if target != "" {
				cfg.Target.Local = target
			}
			w, err := agentic.Load(args[0])
			if err != nil {
				return err
			}
			reg, err := agentic.StandardRegistry(cfg)
			if err != nil {
				return err
			}
			eng := agentic.NewEngine(reg)
			eng.Verbose = verbose
			rep, err := eng.Run(cmd.Context(), w)
			if err != nil {
				return err
			}
			body, _ := json.MarshalIndent(rep, "", "  ")
			if out != "" {
				if err := os.WriteFile(out, body, 0o644); err != nil {
					return err
				}
				fmt.Fprintf(cmd.OutOrStdout(), "wrote %s (%d steps, ok=%v)\n", out, len(rep.Steps), rep.OK)
			} else {
				fmt.Fprintln(cmd.OutOrStdout(), string(body))
			}
			if !rep.OK {
				os.Exit(3)
			}
			return nil
		},
	}
	c.Flags().StringVarP(&target, "target", "t", ".", "target path")
	c.Flags().BoolVar(&verbose, "verbose", false, "verbose step logging")
	c.Flags().StringVarP(&out, "out", "o", "", "output JSON path")
	return c
}

func listCmd() *cobra.Command {
	c := &cobra.Command{
		Use:   "list",
		Short: "List built-in workflow actions",
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, _ := config.Load(".")
			reg, err := agentic.StandardRegistry(cfg)
			if err != nil {
				return err
			}
			fmt.Fprintln(cmd.OutOrStdout(), "Built-in actions:")
			for _, a := range sortedActions(reg) {
				fmt.Fprintf(cmd.OutOrStdout(), "  %s\n", a)
			}
			return nil
		},
	}
	return c
}

func sortedActions(reg *agentic.Registry) []string {
	names := reg.Names()
	for i := 1; i < len(names); i++ {
		for j := i; j > 0 && names[j-1] > names[j]; j-- {
			names[j-1], names[j] = names[j], names[j-1]
		}
	}
	return names
}

func validateCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "validate <file>",
		Short: "Parse + validate a workflow YAML",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			w, err := agentic.Load(args[0])
			if err != nil {
				return err
			}
			fmt.Fprintf(cmd.OutOrStdout(), "✓ valid: %s (%d steps)\n", w.Name, len(w.Steps))
			for _, s := range w.Steps {
				fmt.Fprintf(cmd.OutOrStdout(), "  - %s: %s\n", s.ID, s.Use)
				if s.When != "" {
					fmt.Fprintf(cmd.OutOrStdout(), "      when: %s\n", s.When)
				}
			}
			return nil
		},
	}
}

// Compile-time check: the engine is reachable.
var _ = (*agentic.Engine)(nil)
var _ = (*context.Context)(nil)
