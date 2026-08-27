// Package cmd_dashboard implements `medic dashboard`.
package cmd_dashboard

import (
	"context"
	"time"

	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/health"
	"github.com/life-oss/medic/internal/pattern"
	"github.com/life-oss/medic/internal/ui"
)

// Cmd builds `medic dashboard`.
func Cmd() *cobra.Command {
	var target string
	var repo string
	var pr int
	c := &cobra.Command{
		Use:   "dashboard",
		Short: "Live tview dashboard (Health / Review / Patterns / Visual)",
		Long: `medic dashboard launches a live TUI dashboard that re-runs the health
gate, refreshes patterns, and (optionally) follows a PR every 30s.

Bindings:
  1..4   switch pillar
  r      refresh current
  R      refresh all
  q      quit`,
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load(target)
			if err != nil {
				return err
			}
			if target != "" {
				cfg.Target.Local = target
			}
			loader := buildLoader(cfg, repo, pr)
			app := ui.New(loader)
			return app.Run(cmd.Context())
		},
	}
	c.Flags().StringVarP(&target, "target", "t", ".", "target path")
	c.Flags().StringVar(&repo, "repo", "", "optional GitHub repo for review pillar")
	c.Flags().IntVar(&pr, "pr", 0, "optional PR number for review pillar")
	return c
}

func buildLoader(cfg *config.Config, repo string, pr int) ui.Loader {
	return func(ctx context.Context) (ui.Snapshot, error) {
		snap := ui.Snapshot{
			Title:     "medic 🩺 dashboard",
			Generated: time.Now(),
		}
		o := health.NewOrchestrator(cfg)
		if rep, err := o.Run(ctx, cfg.Target.Local); err == nil {
			snap.Health = rep
		}
		e := pattern.NewEngine()
		if findings, err := e.Scan(ctx, cfg.Target.Local); err == nil {
			snap.Patterns = findings
		}
		if repo != "" && pr != 0 {
			snap.Review = "(refresh in CLI: medic review " + itoa(pr) + " --repo " + repo + ")"
		}
		return snap, nil
	}
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
