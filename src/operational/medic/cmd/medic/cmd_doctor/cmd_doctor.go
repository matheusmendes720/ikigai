// Package cmd_doctor implements `medic doctor`.
package cmd_doctor

import (
	"fmt"
	"os/exec"
	"runtime"
	"strings"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
)

// Cmd builds `medic doctor`.
func Cmd() *cobra.Command {
	var target string
	c := &cobra.Command{
		Use:   "doctor",
		Short: "Self-diagnose the medic install",
		Long: `medic doctor prints environment details useful for bug reports:

  - Go version, OS/arch
  - Whether the github CLI (gh) is on PATH
  - Whether key check tools (git, pytest, go, uv, ruff, cargo, npm) are present
  - medic version + config file location
`,
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load(target)
			if err != nil {
				return err
			}
			if target != "" {
				cfg.Target.Local = target
			}
			yellow := color.New(color.FgYellow).SprintFunc()
			green := color.New(color.FgGreen).SprintFunc()
			red := color.New(color.FgRed).SprintFunc()

			fmt.Fprintln(cmd.OutOrStdout(), "medic doctor")
			fmt.Fprintln(cmd.OutOrStdout(), strings.Repeat("─", 50))
			fmt.Fprintf(cmd.OutOrStdout(), "go version     %s\n", runtime.Version())
			fmt.Fprintf(cmd.OutOrStdout(), "os/arch        %s/%s\n", runtime.GOOS, runtime.GOARCH)
			fmt.Fprintf(cmd.OutOrStdout(), "target         %s\n", cfg.Target.Local)
			fmt.Fprintf(cmd.OutOrStdout(), "detected lang  %s\n", cfg.Target.Language)

			fmt.Fprintln(cmd.OutOrStdout(), "\ntools:")
			for _, t := range []string{"git", "gh", "go", "uv", "pip", "pytest", "ruff", "cargo", "npm", "node", "python", "python3"} {
				p, err := exec.LookPath(t)
				if err != nil {
					fmt.Fprintf(cmd.OutOrStdout(), "  %-10s %s\n", t, red("✗ missing"))
				} else {
					fmt.Fprintf(cmd.OutOrStdout(), "  %-10s %s\n", t, green("✓ "+p))
				}
			}

			fmt.Fprintln(cmd.OutOrStdout(), "\nconfig:")
			if cfg.GitHub.Repo == "" {
				fmt.Fprintf(cmd.OutOrStdout(), "  %-22s %s\n", "github.repo", yellow("(not set)"))
			} else {
				fmt.Fprintf(cmd.OutOrStdout(), "  %-22s %s\n", "github.repo", cfg.GitHub.Repo)
			}
			fmt.Fprintf(cmd.OutOrStdout(), "  %-22s %t\n", "github.allow_post", cfg.GitHub.AllowPost)
			fmt.Fprintf(cmd.OutOrStdout(), "  %-22s %t\n", "health.run_tests", cfg.Health.RunTests)
			fmt.Fprintf(cmd.OutOrStdout(), "  %-22s %t\n", "health.run_lint", cfg.Health.RunLint)
			fmt.Fprintf(cmd.OutOrStdout(), "  %-22s %t\n", "health.run_coverage", cfg.Health.RunCoverage)
			fmt.Fprintf(cmd.OutOrStdout(), "  %-22s %.0f%%\n", "health.min_coverage_pct", cfg.Health.MinCoveragePct)

			fmt.Fprintln(cmd.OutOrStdout(), "\n✓ done.")
			return nil
		},
	}
	c.Flags().StringVarP(&target, "target", "t", ".", "target path")
	return c
}
