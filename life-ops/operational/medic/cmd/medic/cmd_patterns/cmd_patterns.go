// Package cmd_patterns implements `medic patterns`.
package cmd_patterns

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/pattern"
)

// Cmd builds `medic patterns`.
func Cmd() *cobra.Command {
	var (
		target string
		family string
		minSev string
	)
	c := &cobra.Command{
		Use:   "patterns",
		Short: "Detect code/UX/workflow patterns and suggest improvements",
		Long: `medic patterns scans the target codebase (and git history) for
patterns that indicate code smell, missing tests, hardcoded paths,
debug-print leftovers, and workflow anti-patterns (reverts, no-conventional-commits).

Output is a JSON / text table of findings, each with a rule ID, severity,
and an actionable suggestion.`,
		Example: `  medic patterns
  medic patterns --family code
  medic patterns --min-severity medium --target ./packages/core`,
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load(target)
			if err != nil {
				return err
			}
			if target != "" {
				cfg.Target.Local = target
			}
			e := pattern.NewEngine()
			switch family {
			case "code":
				e.EnableUX, e.EnableWorkflow = false, false
			case "workflow":
				e.EnableUX, e.EnableCode = false, false
			case "ux":
				e.EnableCode, e.EnableWorkflow = false, false
			}
			if minSev != "" {
				e.MinSeverity = pattern.Severity(minSev)
			}
			findings, err := e.Scan(cmd.Context(), cfg.Target.Local)
			if err != nil {
				return err
			}
			fmt.Fprintln(cmd.OutOrStdout(), pattern.FormatTable(findings))
			fmt.Fprintf(cmd.OutOrStdout(), "\n%d findings\n", len(findings))
			return nil
		},
	}
	c.Flags().StringVarP(&target, "target", "t", ".", "target path")
	c.Flags().StringVarP(&family, "family", "f", "all", "all|code|workflow|ux")
	c.Flags().StringVar(&minSev, "min-severity", "info", "info|low|medium|high|critical")
	return c
}
