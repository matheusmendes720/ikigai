// Package cmd_health implements `medic health`.
package cmd_health

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/health"
	"github.com/life-oss/medic/internal/report"
	"github.com/life-oss/medic/internal/store"
)

// Cmd builds the `medic health` command.
func Cmd() *cobra.Command {
	var (
		target string
		format string
		out    string
		skip   []string
	)
	c := &cobra.Command{
		Use:   "health",
		Short: "Run health checks (tests, lint, coverage, deps, complexity)",
		Long: `medic health detects the target language and runs the corresponding checks:
  python → pytest + ruff + coverage + pip/uv lock check
  go     → go test + go cover + go mod verify + LOC heuristic
  rust   → cargo test + cargo deny
  node   → npm test + eslint
The report is written to .medic/ in the target repo and printed to stdout.`,
		Example: `  medic health
  medic health --target ../packages/core --format markdown --out report.md
  medic health --skip coverage`,
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load(target)
			if err != nil {
				return err
			}
			if target != "" {
				cfg.Target.Local = target
			}
			if len(skip) > 0 {
				applySkip(cfg, skip)
			}
			o := health.NewOrchestrator(cfg)
			rep, err := o.Run(cmd.Context(), cfg.Target.Local)
			if err != nil {
				return err
			}
			if out == "" {
				out = filepath.Join(cfg.Target.Local, ".medic", "health."+format)
			}
			if format == "" {
				format = "text"
			}
			body, err := report.Render(report.Bundle{Health: rep}, report.Format(format))
			if err != nil {
				return err
			}
			if out != "" && out != "-" {
				s, _ := store.New(cfg.Target.Local)
				_ = s.WriteFile(filepath.Join("health."+format), []byte(body))
				if format == "json" {
					data, _ := json.MarshalIndent(rep, "", "  ")
					_ = os.WriteFile(out, data, 0o644)
				}
			}
			fmt.Fprintln(cmd.OutOrStdout(), body)
			if !rep.OK {
				color.Red("✗ health gate failed (score %d/100)", rep.Score)
				os.Exit(2)
			}
			color.Green("✓ health gate passed (score %d/100)", rep.Score)
			return nil
		},
	}
	c.Flags().StringVarP(&target, "target", "t", ".", "target path")
	c.Flags().StringVarP(&format, "format", "f", "text", "text|json|markdown|html")
	c.Flags().StringVarP(&out, "out", "o", "", "output path (default .medic/health.<format>)")
	c.Flags().StringSliceVar(&skip, "skip", nil, "checks to skip (test|lint|coverage|deps|complexity)")
	return c
}

func applySkip(cfg *config.Config, skip []string) {
	for _, s := range skip {
		switch s {
		case "test":
			cfg.Health.RunTests = false
		case "lint":
			cfg.Health.RunLint = false
		case "coverage":
			cfg.Health.RunCoverage = false
		case "deps":
			cfg.Health.RunDeps = false
		case "complexity":
			cfg.Health.RunComplex = false
		}
	}
}
