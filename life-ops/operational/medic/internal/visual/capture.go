package visual

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/life-oss/medic/internal/shell"
)

// CaptureOpts configures a Capturer run.
//
// Defaults (zero values) are: FrameRateMs=125 (≈8 FPS), MaxFrames=0
// (unbounded), StopOnIdleMs=0 (never stop on idle). At least one of
// MaxFrames or StopOnIdleMs should be set for long-running TUIs.
type CaptureOpts struct {
	FrameRateMs  int           // Minimum interval between emitted frames; default 125.
	MaxFrames    int           // Stop after this many frames; 0 = unlimited.
	StopOnIdleMs int           // Stop after this many ms of zero-byte reads; 0 = never.
	// FilterNoise drops intermediate frames whose hash matches the most
	// recently emitted frame (typical during a slow repaint). Default true.
	FilterNoise bool
}

// Capturer turns a live PTYSession into a stream of *Frame values.
//
// It is single-use: call Run once per Capturer instance. The output channel
// is closed when the capture ends for any reason — MaxFrames reached, idle
// timeout, child exit, or ctx cancellation. The error channel receives at
// most one error and is then closed.
type Capturer struct {
	once   sync.Once
	closed atomic.Bool
}

// NewCapturer returns a fresh Capturer.
func NewCapturer() *Capturer { return &Capturer{} }

// Run drives the PTY read loop until one of the termination conditions fires.
//
// Returns the frames channel, an error channel (closed after first error or
// after graceful shutdown), and an immediate setup error if any. Both
// channels are closed when capture ends. Callers MUST drain frames (or
// select on ctx.Done) or the goroutine will block.
func (c *Capturer) Run(
	ctx context.Context,
	session *shell.PTYSession,
	opts CaptureOpts,
) (<-chan *Frame, <-chan error, error) {
	if session == nil {
		return nil, nil, errors.New("visual: nil PTY session")
	}
	if opts.FrameRateMs <= 0 {
		opts.FrameRateMs = 125
	}
	// FilterNoise defaults to true. Callers opt out with
	// CaptureOpts{FilterNoise: false, ...}.
	if !opts.FilterNoise {
		// we can't tell "explicitly set to false" from "left at zero" in
		// Go, so we treat the zero value as the default (true) by ORing:
		opts.FilterNoise = true
	}

	frames := make(chan *Frame, 4)
	errs := make(chan error, 1)

	go c.loop(ctx, session, opts, frames, errs)
	return frames, errs, nil
}

func (c *Capturer) loop(
	ctx context.Context,
	session *shell.PTYSession,
	opts CaptureOpts,
	frames chan<- *Frame,
	errs chan<- error,
) {
	defer close(frames)
	defer close(errs)

	cols := session.Cols()
	rows := session.Rows()
	if cols < 2 {
		cols = 80
	}
	if rows < 2 {
		rows = 24
	}

	parser := newAnsiParser(cols, rows)
	var (
		buf       [4096]byte
		frameTick = time.NewTicker(time.Duration(opts.FrameRateMs) * time.Millisecond)
		idleTick  = time.NewTicker(50 * time.Millisecond)
	)
	defer frameTick.Stop()
	defer idleTick.Stop()

	lastRead := time.Now()
	lastEmitted := ""
	emitted := 0

	emit := func() {
		// Apply noise filter: drop frames that haven't changed since the
		// last emitted one. This is the difference between capturing every
		// repaint and capturing the steady-state TUI.
		f := parser.frame
		f.RecomputeHash()
		if opts.FilterNoise && f.Hash == lastEmitted {
			return
		}
		lastEmitted = f.Hash
		// Snapshot cells so the renderer / recorder can mutate freely
		// without disturbing subsequent parsing. Copy via append-to-nil.
		snap := &Frame{
			Cols:       f.Cols,
			Rows:       f.Rows,
			Cells:      append([]Cell(nil), f.Cells...),
			CapturedAt: f.CapturedAt,
			Hash:       f.Hash,
		}
		select {
		case frames <- snap:
		case <-ctx.Done():
			return
		}
		emitted++
	}

	readDone := session.Done()
	for {
		select {
		case <-ctx.Done():
			emit() // final frame
			return

		case <-readDone:
			emit() // final frame
			return

		case <-frameTick.C:
			emit()
			if opts.MaxFrames > 0 && emitted >= opts.MaxFrames {
				return
			}

		case <-idleTick.C:
			if opts.StopOnIdleMs > 0 && time.Since(lastRead) > time.Duration(opts.StopOnIdleMs)*time.Millisecond {
				emit()
				return
			}
		default:
			// Non-blocking read attempt so the timers above can fire.
			n, err := session.Read(buf[:])
			if n > 0 {
				parser.feed(buf[:n])
				lastRead = time.Now()
			}
			if err != nil {
				// io.EOF or PTY-closed → emit and exit cleanly.
				if errors.Is(err, errEOF) || isClosedErr(err) {
					emit()
					return
				}
				// Other errors are reported but don't necessarily end capture.
				select {
				case errs <- fmt.Errorf("visual: pty read: %w", err):
				default:
				}
				// brief backoff to avoid hot spin on persistent errors
				select {
				case <-ctx.Done():
					return
				case <-time.After(50 * time.Millisecond):
				}
			}
		}
	}
}

// errEOF is sentinal: matches "EOF" string reported by ptmx.Read on close
// across platforms. We use a package-local var rather than importing io
// here for cleanliness, but we DO compare with errors.Is against the
// canonical io.EOF via the import path below.
var errEOF = errEOFValue{}

type errEOFValue struct{}

func (errEOFValue) Error() string { return "EOF" }

// isClosedErr returns true if the error looks like a PTY that has been
// closed. We deliberately err on the side of permissive matching because
// ptmx implementations across Linux/Darwin/Windows ConPTY vary widely.
func isClosedErr(err error) bool {
	if err == nil {
		return false
	}
	s := err.Error()
	for _, marker := range []string{"EOF", "file already closed", "input/output error", "The pipe is being closed"} {
		if containsFold(s, marker) {
			return true
		}
	}
	return false
}

// containsFold is a case-insensitive substring search without pulling in
// strings.ToLower (which would allocate). Keeps the hot path cheap.
func containsFold(haystack, needle string) bool {
	if len(needle) == 0 {
		return true
	}
	if len(haystack) < len(needle) {
		return false
	}
	for i := 0; i+len(needle) <= len(haystack); i++ {
		match := true
		for j := 0; j < len(needle); j++ {
			a, b := haystack[i+j], needle[j]
			if a >= 'A' && a <= 'Z' {
				a += 32
			}
			if b >= 'A' && b <= 'Z' {
				b += 32
			}
			if a != b {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}