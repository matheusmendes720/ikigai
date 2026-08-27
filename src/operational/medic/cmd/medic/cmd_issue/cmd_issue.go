// Package cmd_issue implements `medic issue`.
package cmd_issue

import (
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/review"
)

// Cmd builds `medic issue`.
func Cmd() *cobra.Command {
	var (
		target string
		repo   string
		format string
	)
	c := &cobra.Command{
		Use:   "issue <number>",
		Short: "Fetch and summarize a GitHub issue",
		Example: `  medic issue 88 --repo life-oss/life
  medic issue 88 --format json`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var num int
			fmt.Sscanf(args[0], "%d", &num)
			if num == 0 {
				return fmt.Errorf("invalid issue number %q", args[0])
			}
			cfg, err := config.Load(target)
			if err != nil {
				return err
			}
			if repo != "" {
				cfg.GitHub.Repo = repo
			}
			if cfg.GitHub.Repo == "" {
				return fmt.Errorf("--repo is required")
			}
			c, err := review.New(cfg.GitHub.Repo, cfg.GitHub.Token, false)
			if err != nil {
				return err
			}
			is, err := c.Issue(cmd.Context(), num)
			if err != nil {
				return err
			}
			if format == "json" {
				return printJSON(cmd, is)
			}
			fmt.Fprintf(cmd.OutOrStdout(), "#%d  %s\n", is.Number, is.Title)
			fmt.Fprintf(cmd.OutOrStdout(), "state=%s author=@%s  url=%s\n", is.State, is.Author, is.URL)
			if len(is.Labels) > 0 {
				fmt.Fprintf(cmd.OutOrStdout(), "labels: %v\n", is.Labels)
			}
			fmt.Fprintln(cmd.OutOrStdout(), "---")
			fmt.Fprintln(cmd.OutOrStdout(), is.Body)
			return nil
		},
	}
	c.Flags().StringVarP(&target, "target", "t", ".", "target path")
	c.Flags().StringVarP(&repo, "repo", "r", "", "GitHub repo")
	c.Flags().StringVarP(&format, "format", "f", "text", "text|json")
	return c
}

func printJSON(cmd *cobra.Command, v any) error {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	fmt.Fprintln(cmd.OutOrStdout(), string(data))
	return nil
}
