//go:build windows

package shell

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"sync"
	"time"
)

// PTYSession is a stub on Windows: full ConPTY support is delegated to the
// visual package which uses a different mechanism (run via winpty or by
// shelling out to a child terminal). For now, non-TTY command capture works
// via Executor; PTY-driven TUI capture works via the visual package.
type PTYSession struct {
	cmd    *exec.Cmd
	mu     sync.Mutex
	done   chan struct{}
	cols   int
	rows   int
	stub   bool
}

// ErrPTYUnsupported is returned when a PTY is required on Windows.
var ErrPTYUnsupported = errors.New("pty: interactive TUI capture on Windows requires ConPTY; run medic from WSL or use `medic visualize` with --record=yaml")

// StartPTY on Windows returns ErrPTYUnsupported. The visual package falls
// back to a different capture strategy on Windows.
func StartPTY(ctx context.Context, cols, rows int, cmd string, args ...string) (*PTYSession, error) {
	return nil, ErrPTYUnsupported
}

// Write is a no-op stub.
func (s *PTYSession) Write(p []byte) (int, error) { return 0, ErrPTYUnsupported }

// WriteString is a no-op stub.
func (s *PTYSession) WriteString(s2 string) (int, error) { return 0, ErrPTYUnsupported }

// Read is a no-op stub.
func (s *PTYSession) Read(buf []byte) (int, error) { return 0, ErrPTYUnsupported }

// Resize is a no-op stub.
func (s *PTYSession) Resize(cols, rows int) error { return nil }

// Cols returns the initial cols.
func (s *PTYSession) Cols() int { s.mu.Lock(); defer s.mu.Unlock(); return s.cols }

// Rows returns the initial rows.
func (s *PTYSession) Rows() int { s.mu.Lock(); defer s.mu.Unlock(); return s.rows }

// Done blocks until the child exits.
func (s *PTYSession) Done() <-chan struct{} { return s.done }

// Close terminates the PTY stub.
func (s *PTYSession) Close() error { return nil }

// Compile-time check
var _ = fmt.Sprintf
var _ time.Duration
