//go:build !windows

package shell

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"sync"
	"syscall"
	"time"

	"github.com/creack/pty"
)

// PTYSession is an interactive pseudo-terminal session with a child process.
//
// It is used by:
//   - the visual debugger to drive a TUI and capture its cell grid
//   - the agentic workflows to script interactive commands
type PTYSession struct {
	cmd     *exec.Cmd
	ptmx    *os.File
	cols    int
	rows    int
	mu      sync.Mutex
	done    chan struct{}
	capture bool
}

// StartPTY launches cmd in a fresh PTY sized cols×rows.
func StartPTY(ctx context.Context, cols, rows int, cmd string, args ...string) (*PTYSession, error) {
	if cols <= 0 {
		cols = 120
	}
	if rows <= 0 {
		rows = 40
	}
	c := exec.CommandContext(ctx, cmd, args...)
	c.Env = append(os.Environ(),
		fmt.Sprintf("TERM=xterm-256color"),
		fmt.Sprintf("COLUMNS=%d", cols),
		fmt.Sprintf("LINES=%d", rows),
	)
	ptmx, err := pty.StartWithSize(c, &pty.Winsize{Rows: uint16(rows), Cols: uint16(cols)})
	if err != nil {
		return nil, fmt.Errorf("pty start: %w", err)
	}
	s := &PTYSession{
		cmd:  c,
		ptmx: ptmx,
		cols: cols,
		rows: rows,
		done: make(chan struct{}),
	}
	go func() {
		_ = c.Wait()
		close(s.done)
	}()
	return s, nil
}

// Write sends raw bytes to the PTY (keystrokes, paste).
func (s *PTYSession) Write(p []byte) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.ptmx.Write(p)
}

// WriteString is a sugar over Write.
func (s *PTYSession) WriteString(s2 string) (int, error) { return s.Write([]byte(s2)) }

// Read reads up to len(buf) bytes from the PTY. Blocks.
func (s *PTYSession) Read(buf []byte) (int, error) { return s.ptmx.Read(buf) }

// Resize changes the PTY window size.
func (s *PTYSession) Resize(cols, rows int) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.cols, s.rows = cols, rows
	return pty.Setsize(s.ptmx, &pty.Winsize{Rows: uint16(rows), Cols: uint16(cols)})
}

// Cols returns current width.
func (s *PTYSession) Cols() int { s.mu.Lock(); defer s.mu.Unlock(); return s.cols }

// Rows returns current height.
func (s *PTYSession) Rows() int { s.mu.Lock(); defer s.mu.Unlock(); return s.rows }

// Done blocks until the child exits.
func (s *PTYSession) Done() <-chan struct{} { return s.done }

// Close terminates the PTY.
func (s *PTYSession) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.ptmx != nil {
		_ = s.ptmx.Close()
		s.ptmx = nil
	}
	if s.cmd != nil && s.cmd.Process != nil {
		_ = s.cmd.Process.Signal(syscall.SIGTERM)
		select {
		case <-s.done:
		case <-time.After(2 * time.Second):
			_ = s.cmd.Process.Kill()
		}
	}
	return nil
}
