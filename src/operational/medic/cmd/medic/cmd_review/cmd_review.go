// Package cmd_review implements `medic review`.
package cmd_review

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/health"
	"github.com/life-oss/medic/internal/pattern"
	"github.com/life-oss/medic/internal/report"
	"github.com/life-oss/medic/internal/review"
	"github.com/life-oss/medic/internal/store"
)

// Cmd builds `medic review`.
func Cmd() *cobra.Command {
	var (
		target   string
		repo     string
		post     bool
		format   string
		out      string
		baseRef  string
		headRef  string
		skipHealth bool
		skipPatterns bool
	)
	c := &cobra.Command{
		Use:   "review <pr-number>",
		Short: "Code review a GitHub PR with optional health + patterns",
		Long: `medic review fetches the PR, lists changed files, optionally runs the
target's health gate, scans code/workflow patterns, decides a verdict
(COMMENT / APPROVE / REQUEST_CHANGES), and writes the markdown report.

With --post (and allow_post=true in medic.yaml), the report is posted back
to the PR as a review.`,
		Example: `  medic review 142 --target ./packages/core --repo life-oss/life
  medic review 142 --post --format markdown`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var prNum int
			fmt.Sscanf(args[0], "%d", &prNum)
			if prNum == 0 {
				return fmt.Errorf("invalid PR number %q", args[0])
			}
			cfg, err := config.Load(target)
			if err != nil {
				return err
			}
			if target != "" {
				cfg.Target.Local = target
			}
			if repo != "" {
				cfg.GitHub.Repo = repo
			}
			if post {
				cfg.GitHub.AllowPost = true
			}
			if cfg.GitHub.Repo == "" {
				return fmt.Errorf("--repo is required (or set github.repo in medic.yaml)")
			}
			client, err := review.New(cfg.GitHub.Repo, cfg.GitHub.Token, cfg.GitHub.AllowPost)
			if err != nil {
				return err
			}
			az := review.NewAnalyzer(client, review.Config{
				BaseRef:     baseRef,
				HeadRef:     headRef,
				LocalTarget: cfg.Target.Local,
				PostToGitHub: post,
				RunHealth:   !skipHealth,
				RunPatterns: !skipPatterns,
			})
			rep, err := az.Analyze(cmd.Context(), prNum)
			if err != nil {
				return err
			}
			// Run health if requested
			if !skipHealth {
				hOrch := health.NewOrchestrator(cfg)
				if hRep, herr := hOrch.Run(cmd.Context(), cfg.Target.Local); herr == nil {
					rep.Health = hRep
				}
			}
			// Run patterns if requested
			if !skipPatterns {
				engine := pattern.NewEngine()
				if findings, perr := engine.Scan(cmd.Context(), cfg.Target.Local); perr == nil {
					for _, f := range findings {
						rep.Findings = append(rep.Findings, review.Finding{
							ID: f.ID, Severity: review.Severity(f.Severity),
							Family: string(f.Family), Path: f.Path, Line: f.Line,
							Title: f.Title, Rationale: f.Rationale, Suggestion: f.Suggestion, Rule: f.Rule,
						})
					}
				}
			}
			rep.Findings = review.SortFindings(rep.Findings)
			if format == "" {
				format = "markdown"
			}
			body, err := report.Render(report.Bundle{Review: rep}, report.Format(format))
			if err != nil {
				return err
			}
			out = pickOut(out, cfg.Target.Local, prNum, format)
			if out != "-" {
				s, _ := store.New(cfg.Target.Local)
				_ = s.WriteFile(filepath.Join(fmt.Sprintf("review-%d.%s", prNum, format)), []byte(body))
				if format == "json" {
					data, _ := json.MarshalIndent(rep, "", "  ")
					_ = os.WriteFile(out, data, 0o644)
				}
			}
			fmt.Fprintln(cmd.OutOrStdout(), body)
			if post && cfg.GitHub.AllowPost {
				if err := client.PostReview(cmd.Context(), prNum, rep.Verdict, body); err != nil {
					color.Red("post review failed: %v", err)
				} else {
					color.Green("✓ posted review as %s", rep.Verdict)
				}
			}
			return nil
		},
	}
	c.Flags().StringVarP(&target, "target", "t", ".", "target path")
	c.Flags().StringVarP(&repo, "repo", "r", "", "GitHub repo (owner/name)")
	c.Flags().BoolVar(&post, "post", false, "post review back to GitHub")
	c.Flags().StringVarP(&format, "format", "f", "markdown", "text|json|markdown|sarif|html")
	c.Flags().StringVarP(&out, "out", "o", "", "output path")
	c.Flags().StringVar(&baseRef, "base", "main", "base ref for diff")
	c.Flags().StringVar(&headRef, "head", "HEAD", "head ref for diff")
	c.Flags().BoolVar(&skipHealth, "skip-health", false, "skip health gate")
	c.Flags().BoolVar(&skipPatterns, "skip-patterns", false, "skip pattern scan")
	return c
}

func pickOut(out, target string, pr int, format string) string {
	if out != "" {
		return out
	}
	return filepath.Join(target, ".medic", fmt.Sprintf("review-%d.%s", pr, format))
}
