// Package shell runs external commands (for tests, lint, deps) and drives
// pseudo-terminals (for TUI capture + debug). It's the foundation for both
// the health and visual pillars.
package shell

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// Result captures the outcome of a command run.
type Result struct {
	Cmd      string        `json:"cmd"`
	Args     []string      `json:"args"`
	Dir      string        `json:"dir"`
	Stdout   string        `json:"stdout"`
	Stderr   string        `json:"stderr"`
	ExitCode int           `json:"exit_code"`
	Started  time.Time     `json:"started"`
	Duration time.Duration `json:"duration_ns"`
	Err      error         `json:"-"`
}

// OK returns true if exit code == 0 and no exec error.
func (r *Result) OK() bool { return r.Err == nil && r.ExitCode == 0 }

// Combined returns stdout+stderr joined.
func (r *Result) Combined() string {
	if r.Stderr == "" {
		return r.Stdout
	}
	if r.Stdout == "" {
		return r.Stderr
	}
	return r.Stdout + "\n" + r.Stderr
}

// Executor runs commands. Safe for concurrent use.
type Executor struct {
	Env     []string
	Timeout time.Duration
	Stdin   io.Reader
	mu      sync.Mutex
}

// NewExecutor returns an Executor with sensible defaults.
func NewExecutor() *Executor {
	return &Executor{
		Env:     os.Environ(),
		Timeout: 10 * time.Minute,
	}
}

// Run executes cmd with args in dir. Captures stdout/stderr.
func (e *Executor) Run(ctx context.Context, dir string, cmd string, args ...string) (*Result, error) {
	e.mu.Lock()
	defer e.mu.Unlock()

	if dir == "" {
		dir = "."
	}
	if abs, err := filepath.Abs(dir); err == nil {
		dir = abs
	}

	c := exec.CommandContext(ctx, cmd, args...)
	c.Dir = dir
	c.Env = append([]string{}, e.Env...)
	if e.Stdin != nil {
		c.Stdin = e.Stdin
	}

	var stdout, stderr bytes.Buffer
	c.Stdout = &stdout
	c.Stderr = &stderr

	start := time.Now()
	err := c.Run()
	res := &Result{
		Cmd:      cmd,
		Args:     args,
		Dir:      dir,
		Stdout:   stdout.String(),
		Stderr:   stderr.String(),
		Started:  start,
		Duration: time.Since(start),
	}
	if err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			res.ExitCode = exitErr.ExitCode()
		} else if errors.Is(err, context.DeadlineExceeded) {
			res.Err = fmt.Errorf("timeout after %s", e.Timeout)
			res.ExitCode = -1
		} else {
			res.Err = err
			res.ExitCode = -1
		}
	}
	return res, res.Err
}

// RunWithTimeout is a convenience around Run with a per-call timeout.
func (e *Executor) RunWithTimeout(dir string, timeout time.Duration, cmd string, args ...string) (*Result, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	return e.Run(ctx, dir, cmd, args...)
}

// Which returns the absolute path to cmd, or an error if not found.
func Which(cmd string) (string, error) {
	p, err := exec.LookPath(cmd)
	if err != nil {
		return "", fmt.Errorf("which %s: %w", cmd, err)
	}
	return p, nil
}

// HasAll returns nil if every binary is on PATH.
func HasAll(bins ...string) error {
	var missing []string
	for _, b := range bins {
		if _, err := exec.LookPath(b); err != nil {
			missing = append(missing, b)
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("missing binaries on PATH: %s", strings.Join(missing, ", "))
	}
	return nil
}

// Quote joins args for shell display (does NOT shell-escape).
func Quote(parts ...string) string {
	return strings.Join(parts, " ")
}
