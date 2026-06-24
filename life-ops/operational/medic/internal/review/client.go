// Package review connects to GitHub for PR + Issue code review, performs
// file-level analysis (linked to local git diffs), and produces a markdown
// report that can be posted back as a review comment.
package review

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"

	"github.com/google/go-github/v62/github"
	"golang.org/x/oauth2"
)

// Client wraps the go-github library with our conventions.
type Client struct {
	GH      *github.Client
	Owner   string
	Repo    string
	AllowPost bool
}

// New creates a Client. token may be empty (rate-limited anonymous calls work
// for public repos).
func New(repo, token string, allowPost bool) (*Client, error) {
	parts := strings.SplitN(repo, "/", 2)
	if len(parts) != 2 {
		return nil, fmt.Errorf("repo must be owner/name, got %q", repo)
	}
	c := &Client{Owner: parts[0], Repo: parts[1], AllowPost: allowPost}
	ts := oauth2.StaticTokenSource(&oauth2.Token{AccessToken: token})
	tc := oauth2.NewClient(context.Background(), ts)
	c.GH = github.NewClient(tc)
	if base := os.Getenv("MEDIC_GITHUB_BASE_URL"); base != "" {
		u, err := url.Parse(base)
		if err == nil {
			c.GH.BaseURL = u
		}
	}
	return c, nil
}

// PR is the slim representation of a pull request we work with.
type PR struct {
	Number   int
	Title    string
	Author   string
	Branch   string
	Base     string
	Body     string
	SHA      string
	State    string
	Draft    bool
	Labels   []string
	URL      string
	Created  string
	IssueRefs []string // "owner/repo#NNN"
}

// PullRequest fetches a PR by number.
func (c *Client) PullRequest(ctx context.Context, num int) (*PR, error) {
	gpr, _, err := c.GH.PullRequests.Get(ctx, c.Owner, c.Repo, num)
	if err != nil {
		return nil, fmt.Errorf("get PR #%d: %w", num, err)
	}
	pr := &PR{
		Number: num,
		Title:  gpr.GetTitle(),
		Author: gpr.GetUser().GetLogin(),
		Branch: gpr.GetHead().GetRef(),
		Base:   gpr.GetBase().GetRef(),
		Body:   gpr.GetBody(),
		SHA:    gpr.GetHead().GetSHA(),
		State:  gpr.GetState(),
		Draft:  gpr.GetDraft(),
		URL:    gpr.GetHTMLURL(),
		Created: gpr.GetCreatedAt().Format("2006-01-02"),
	}
	for _, l := range gpr.Labels {
		pr.Labels = append(pr.Labels, l.GetName())
	}
	return pr, nil
}

// Files returns PR changed files (path, additions, deletions, sha).
type File struct {
	Path      string `json:"path"`
	Additions int    `json:"additions"`
	Deletions int    `json:"deletions"`
	SHA       string `json:"sha"`
}

// FilesChanged returns the list of files changed in the PR.
func (c *Client) FilesChanged(ctx context.Context, num int) ([]File, error) {
	opt := &github.ListOptions{PerPage: 100}
	var out []File
	for {
		page, resp, err := c.GH.PullRequests.ListFiles(ctx, c.Owner, c.Repo, num, opt)
		if err != nil {
			return nil, err
		}
		for _, f := range page {
			out = append(out, File{
				Path:      f.GetFilename(),
				Additions: f.GetAdditions(),
				Deletions: f.GetDeletions(),
				SHA:       f.GetSHA(),
			})
		}
		if resp.NextPage == 0 {
			break
		}
		opt.Page = resp.NextPage
	}
	return out, nil
}

// Comment is a representation of an issue/PR comment.
type Comment struct {
	Author string
	Body   string
	URL    string
	Created string
}

// Comments lists all issue/PR comments.
func (c *Client) Comments(ctx context.Context, num int) ([]Comment, error) {
	opt := &github.IssueListCommentsOptions{ListOptions: github.ListOptions{PerPage: 100}}
	var out []Comment
	for {
		page, resp, err := c.GH.Issues.ListComments(ctx, c.Owner, c.Repo, num, opt)
		if err != nil {
			return nil, err
		}
		for _, c := range page {
			out = append(out, Comment{
				Author:  c.GetUser().GetLogin(),
				Body:    c.GetBody(),
				URL:     c.GetHTMLURL(),
				Created: c.GetCreatedAt().Format("2006-01-02"),
			})
		}
		if resp.NextPage == 0 {
			break
		}
		opt.Page = resp.NextPage
	}
	return out, nil
}

// LinkedIssues parses the PR body + commit messages for "Closes #N", "Refs #N", etc.
// and returns the referenced issue numbers.
func LinkedIssues(pr *PR, comments []Comment, commits []string) []int {
	seen := map[int]bool{}
	add := func(body string) {
		for _, n := range extractRefs(body) {
			seen[n] = true
		}
	}
	add(pr.Body)
	for _, c := range comments {
		add(c.Body)
	}
	for _, msg := range commits {
		add(msg)
	}
	var out []int
	for n := range seen {
		out = append(out, n)
	}
	return out
}

// extractRefs returns all "#NNN" references in body.
func extractRefs(body string) []int {
	var out []int
	for i := 0; i < len(body); i++ {
		if body[i] == '#' {
			j := i + 1
			for j < len(body) && body[j] >= '0' && body[j] <= '9' {
				j++
			}
			if j > i+1 {
				n := 0
				for k := i + 1; k < j; k++ {
					n = n*10 + int(body[k]-'0')
				}
				out = append(out, n)
			}
		}
	}
	return out
}

// Issue is a slim issue representation.
type Issue struct {
	Number int
	Title  string
	State  string
	Author string
	Body   string
	Labels []string
	URL    string
	Created string
}

// Issue fetches a single issue.
func (c *Client) Issue(ctx context.Context, num int) (*Issue, error) {
	gi, _, err := c.GH.Issues.Get(ctx, c.Owner, c.Repo, num)
	if err != nil {
		return nil, err
	}
	is := &Issue{
		Number:  num,
		Title:   gi.GetTitle(),
		State:   gi.GetState(),
		Author:  gi.GetUser().GetLogin(),
		Body:    gi.GetBody(),
		URL:     gi.GetHTMLURL(),
		Created: gi.GetCreatedAt().Format("2006-01-02"),
	}
	for _, l := range gi.Labels {
		is.Labels = append(is.Labels, l.GetName())
	}
	return is, nil
}

// PostReview posts a PR review (COMMENT / APPROVE / REQUEST_CHANGES).
func (c *Client) PostReview(ctx context.Context, num int, event ReviewEvent, body string) error {
	if !c.AllowPost {
		return errors.New("posting is disabled; pass --post and set allow_post=true in medic.yaml")
	}
	ev := string(event)
	review := &github.PullRequestReviewRequest{
		Event: &ev,
		Body:  &body,
	}
	_, _, err := c.GH.PullRequests.CreateReview(ctx, c.Owner, c.Repo, num, review)
	if err != nil {
		return fmt.Errorf("post review: %w", err)
	}
	return nil
}

// PostIssueComment posts a plain comment on an issue or PR.
func (c *Client) PostIssueComment(ctx context.Context, num int, body string) error {
	if !c.AllowPost {
		return errors.New("posting is disabled; pass --post and set allow_post=true in medic.yaml")
	}
	_, _, err := c.GH.Issues.CreateComment(ctx, c.Owner, c.Repo, num, &github.IssueComment{Body: &body})
	return err
}

// AddLabels adds labels to a PR (idempotent).
func (c *Client) AddLabels(ctx context.Context, num int, labels ...string) error {
	if !c.AllowPost {
		return errors.New("label mutation disabled; set allow_post=true")
	}
	if len(labels) == 0 {
		return nil
	}
	ls := make([]string, len(labels))
	copy(ls, labels)
	_, _, err := c.GH.Issues.AddLabelsToIssue(ctx, c.Owner, c.Repo, num, ls)
	return err
}

// SetCommitStatus sets a status check on the PR's head SHA.
func (c *Client) SetCommitStatus(ctx context.Context, sha, state, desc string) error {
	if !c.AllowPost {
		return errors.New("status mutation disabled; set allow_post=true")
	}
	if sha == "" {
		return nil
	}
	st := state
	_, _, err := c.GH.Repositories.CreateStatus(ctx, c.Owner, c.Repo, sha, &github.RepoStatus{
		State:       &st,
		Description: &desc,
		Context:     stringPtr("medic/review"),
	})
	return err
}

// HTTPStatusFromError returns the HTTP status code embedded in an error
// returned by go-github, or 0 if none.
func HTTPStatusFromError(err error) int {
	if err == nil {
		return 0
	}
	var rerr *github.ErrorResponse
	if errors.As(err, &rerr) && rerr.Response != nil {
		return rerr.Response.StatusCode
	}
	// Fallback: check for raw http error
	var gerr error
	gerr = err
	if gerr != nil {
		type unwrap interface{ Unwrap() error }
		for {
			u, ok := gerr.(unwrap)
			if !ok {
				break
			}
			gerr = u.Unwrap()
			if gerr == nil {
				break
			}
			if rerr, ok := gerr.(*github.ErrorResponse); ok && rerr.Response != nil {
				return rerr.Response.StatusCode
			}
		}
	}
	if errors.Is(err, http.ErrServerClosed) {
		return http.StatusServiceUnavailable
	}
	return 0
}

func stringPtr(s string) *string { return &s }
