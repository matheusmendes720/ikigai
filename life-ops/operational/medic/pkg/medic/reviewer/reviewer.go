// Package reviewer is the public entry point for medic's PR/Issue reviewer.
package reviewer

import (
	"context"
	"os"

	"github.com/life-oss/medic/internal/review"
)

// Reviewer is the public façade around internal/review.
type Reviewer struct {
	client    *review.Client
	LocalRoot string
	AllowPost bool
}

// New creates a Reviewer. token may be empty (rate-limited anonymous access).
func New(repo, token string) (*Reviewer, error) {
	c, err := review.New(repo, token, false)
	if err != nil {
		return nil, err
	}
	return &Reviewer{client: c}, nil
}

// NewFromEnv reads repo + token from environment (GITHUB_REPOSITORY + GITHUB_TOKEN).
func NewFromEnv() (*Reviewer, error) {
	repo := os.Getenv("GITHUB_REPOSITORY")
	if repo == "" {
		repo = os.Getenv("MEDIC_GITHUB_REPO")
	}
	tok := os.Getenv("GITHUB_TOKEN")
	if tok == "" {
		tok = os.Getenv("MEDIC_GITHUB_TOKEN")
	}
	return New(repo, tok)
}

// EnablePost lets the Reviewer call mutating GitHub APIs.
func (r *Reviewer) EnablePost() {
	r.AllowPost = true
	r.client.AllowPost = true
}

// SetLocalRoot tells the analyzer where the working tree lives (for diff_tree + patterns).
func (r *Reviewer) SetLocalRoot(p string) { r.LocalRoot = p }

// ReviewPR fetches a PR and produces a Report.
func (r *Reviewer) ReviewPR(ctx context.Context, prNum int) (*review.Report, error) {
	az := review.NewAnalyzer(r.client, review.Config{
		LocalTarget: r.LocalRoot,
		RunHealth:   true,
		RunPatterns: true,
	})
	return az.Analyze(ctx, prNum)
}

// FetchIssue returns an issue or PR by number (uses issue API).
func (r *Reviewer) FetchIssue(ctx context.Context, num int) (*review.Issue, error) {
	return r.client.Issue(ctx, num)
}

// PostComment posts a comment on an issue/PR (requires EnablePost).
func (r *Reviewer) PostComment(ctx context.Context, num int, body string) error {
	return r.client.PostIssueComment(ctx, num, body)
}

// PostReview posts a PR review event (requires EnablePost).
func (r *Reviewer) PostReview(ctx context.Context, num int, event review.ReviewEvent, body string) error {
	return r.client.PostReview(ctx, num, event, body)
}
