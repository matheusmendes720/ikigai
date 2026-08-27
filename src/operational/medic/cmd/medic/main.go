// Command medic is the entry point for the medic toolkit.
//
//	medic health              # run all health checks
//	medic review 142          # analyze PR #142
//	medic issue 88            # fetch and summarize issue #88
//	medic visualize           # drive a TUI and capture frames
//	medic debug               # interactive TUI debug REPL
//	medic patterns            # scan code/workflow patterns
//	medic dashboard           # live TUI dashboard
//	medic workflow run f.yaml # run an agentic workflow
//	medic ui action list      # list available UI actions
//	medic doctor              # self-diagnose the medic install
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/spf13/cobra"

	"github.com/life-oss/medic/cmd/medic/cmd_dashboard"
	"github.com/life-oss/medic/cmd/medic/cmd_debug"
	"github.com/life-oss/medic/cmd/medic/cmd_doctor"
	"github.com/life-oss/medic/cmd/medic/cmd_golden"
	"github.com/life-oss/medic/cmd/medic/cmd_health"
	"github.com/life-oss/medic/cmd/medic/cmd_issue"
	"github.com/life-oss/medic/cmd/medic/cmd_patterns"
	"github.com/life-oss/medic/cmd/medic/cmd_review"
	"github.com/life-oss/medic/cmd/medic/cmd_ui"
	"github.com/life-oss/medic/cmd/medic/cmd_visualize"
	"github.com/life-oss/medic/cmd/medic/cmd_vision"
	"github.com/life-oss/medic/cmd/medic/cmd_workflow"
)

func main() {
	root := &cobra.Command{
		Use:           "medic",
		Short:         "medic 🩺 — code review + visual debug toolkit for CLI/TUI apps",
		Long:          "medic examines the overall health of a CLI/TUI application, automates GitHub PR + Issue review, drives TUIs in a PTY for visual debugging, and runs declarative agentic workflows.",
		Version:       "0.1.0",
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	root.AddCommand(cmd_health.Cmd())
	root.AddCommand(cmd_review.Cmd())
	root.AddCommand(cmd_issue.Cmd())
	root.AddCommand(cmd_visualize.Cmd())
	root.AddCommand(cmd_golden.Cmd())
	root.AddCommand(cmd_debug.Cmd())
	root.AddCommand(cmd_patterns.Cmd())
	root.AddCommand(cmd_dashboard.Cmd())
	root.AddCommand(cmd_workflow.Cmd())
	root.AddCommand(cmd_ui.Cmd())
	root.AddCommand(cmd_doctor.Cmd())
	root.AddCommand(cmd_vision.Cmd())

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	if err := root.ExecuteContext(ctx); err != nil {
		fmt.Fprintf(os.Stderr, "medic: %v\n", err)
		os.Exit(1)
	}
}
