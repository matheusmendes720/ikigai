// Package gitx wraps common git operations used by review, pattern, and
// health packages. Pure helper layer — does not depend on GitHub.
package gitx

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/life-oss/medic/internal/shell"
)

// Repo represents a local clone we can inspect.
type Repo struct {
	Path string
}

// Open locates the .git dir starting at path and walking upward.
func Open(path string) (*Repo, error) {
	abs, err := filepath.Abs(path)
	if err != nil {
		return nil, err
	}
	for cur := abs; cur != filepath.Dir(cur); cur = filepath.Dir(cur) {
		if _, err := exec.Command("git", "-C", cur, "rev-parse", "--git-dir").Output(); err == nil {
			return &Repo{Path: cur}, nil
		}
	}
	return nil, errors.New("not a git repository")
}

// IsClean reports whether the working tree matches HEAD.
func (r *Repo) IsClean(ctx context.Context) (bool, error) {
	out, err := r.git(ctx, "status", "--porcelain")
	if err != nil {
		return false, err
	}
	return strings.TrimSpace(out) == "", nil
}

// CurrentBranch returns the active branch name (empty if detached).
func (r *Repo) CurrentBranch(ctx context.Context) (string, error) {
	out, err := r.git(ctx, "rev-parse", "--abbrev-ref", "HEAD")
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(out), nil
}

// CurrentSHA returns HEAD commit hash.
func (r *Repo) CurrentSHA(ctx context.Context) (string, error) {
	out, err := r.git(ctx, "rev-parse", "HEAD")
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(out), nil
}

// ChangedFiles returns a list of paths touched between two refs (default: HEAD~1..HEAD).
func (r *Repo) ChangedFiles(ctx context.Context, fromRef, toRef string) ([]string, error) {
	if fromRef == "" {
		fromRef = "HEAD~1"
	}
	if toRef == "" {
		toRef = "HEAD"
	}
	out, err := r.git(ctx, "diff", "--name-only", fromRef, toRef)
	if err != nil {
		return nil, err
	}
	var out2 []string
	for _, line := range strings.Split(out, "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			out2 = append(out2, line)
		}
	}
	return out2, nil
}

// DiffStats returns insertion/deletion counts per file for the given ref range.
type DiffStat struct {
	Path      string `json:"path"`
	Insertions int   `json:"insertions"`
	Deletions  int   `json:"deletions"`
}

// Diff returns the diff stats for from..to.
func (r *Repo) Diff(ctx context.Context, fromRef, toRef string) ([]DiffStat, error) {
	out, err := r.git(ctx, "diff", "--numstat", fromRef, toRef)
	if err != nil {
		return nil, err
	}
	var stats []DiffStat
	for _, line := range strings.Split(out, "\n") {
		fields := strings.Fields(line)
		if len(fields) < 3 {
			continue
		}
		stats = append(stats, DiffStat{
			Path:       fields[2],
			Insertions: atoiSafe(fields[0]),
			Deletions:  atoiSafe(fields[1]),
		})
	}
	return stats, nil
}

// CommitLog returns the most recent N commits as {SHA, Author, Date, Subject}.
type Commit struct {
	SHA     string `json:"sha"`
	Author  string `json:"author"`
	Date    string `json:"date"`
	Subject string `json:"subject"`
}

// Log returns the latest N commits reachable from ref (default HEAD).
func (r *Repo) Log(ctx context.Context, ref string, n int) ([]Commit, error) {
	if ref == "" {
		ref = "HEAD"
	}
	if n <= 0 {
		n = 20
	}
	format := "--pretty=format:%H%x1f%an%x1f%ad%x1f%s%x1e"
	out, err := r.git(ctx, "log", ref, "-n", fmt.Sprintf("%d", n), "--date=short", format)
	if err != nil {
		return nil, err
	}
	var commits []Commit
	for _, line := range strings.Split(out, "\x1e") {
		line = strings.TrimRight(line, "\n")
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, "\x1f", 4)
		if len(parts) < 4 {
			continue
		}
		commits = append(commits, Commit{
			SHA:     parts[0],
			Author:  parts[1],
			Date:    parts[2],
			Subject: parts[3],
		})
	}
	return commits, nil
}

// FilesTouchedIn returns the set of files modified by commits touching the given paths.
func (r *Repo) FilesTouchedIn(ctx context.Context, since string, paths []string) ([]string, error) {
	if since == "" {
		since = "HEAD~50"
	}
	args := []string{"log", since, "--name-only", "--pretty=format:"}
	args = append(args, "--", strings.Join(paths, ","))
	out, err := r.git(ctx, args...)
	if err != nil {
		return nil, err
	}
	seen := map[string]bool{}
	var files []string
	for _, line := range strings.Split(out, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || seen[line] {
			continue
		}
		seen[line] = true
		files = append(files, line)
	}
	return files, nil
}

func (r *Repo) git(ctx context.Context, args ...string) (string, error) {
	full := append([]string{"-C", r.Path}, args...)
	c := exec.CommandContext(ctx, "git", full...)
	out, err := c.CombinedOutput()
	if err != nil {
		return string(out), fmt.Errorf("git %s: %w", args[0], err)
	}
	return string(out), nil
}

func atoiSafe(s string) int {
	// "-" means binary file
	if s == "-" {
		return 0
	}
	n := 0
	for _, ch := range s {
		if ch < '0' || ch > '9' {
			return 0
		}
		n = n*10 + int(ch-'0')
	}
	return n
}

// HasBinaryOnPath is a tiny helper used by health/visual setup checks.
func HasBinaryOnPath(name string) bool {
	_, err := exec.LookPath(name)
	return err == nil
}

// ResolveBinary is similar to shell.Which but returns "" on failure.
func ResolveBinary(name string) string {
	p, err := shell.Which(name)
	if err != nil {
		return ""
	}
	return p
}
