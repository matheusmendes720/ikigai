// Package vision is the public façade for the MiniMax vision critic.
//
// It re-exports the essential types from internal/visioncritic behind a
// stable surface so external Go programs can call MiniMax-VL-01 without
// pulling in any of medic's internal packages.
package vision

import (
	"context"
	"time"

	"github.com/life-oss/medic/internal/visual"
	"github.com/life-oss/medic/internal/visioncritic"
)

// Finding is re-exported for downstream convenience.
type Finding = visioncritic.Finding

// Critique is the structured result of one vision-model invocation.
type Critique = visioncritic.Critique

// Options tunes a critique call.
type Options = visioncritic.Options

// Critic is the public client.
type Critic struct{ inner *visioncritic.Critic }

// New returns a Critic that shells out to the local `mmx` binary.
func New() *Critic { return &Critic{inner: visioncritic.New()} }

// Available reports whether `mmx` is installed and MINIMAX_API_KEY is set.
func Available() error { return visioncritic.Available("") }

// Critique sends a frame to MiniMax-VL-01 and returns parsed findings.
func (c *Critic) Critique(ctx context.Context, frame *visual.Frame, opts Options) (*Critique, error) {
	return c.inner.Critique(ctx, frame, opts)
}

// WithTimeout is a small sugar for Options{Timeout: ...}.
func WithTimeout(d time.Duration) func(*Options) {
	return func(o *Options) { o.Timeout = d }
}

// WithPromptFile loads the user prompt from a file.
func WithPromptFile(path string) func(*Options) {
	return func(o *Options) { o.PromptFile = path }
}

// WithSystemFile loads a system-prompt file.
func WithSystemFile(path string) func(*Options) {
	return func(o *Options) { o.SystemPromptFile = path }
}

// WithModel picks a specific mmx model.
func WithModel(model string) func(*Options) {
	return func(o *Options) { o.Model = model }
}

// WithSize hints the original frame size.
func WithSize(cols, rows int) func(*Options) {
	return func(o *Options) { o.Cols, o.Rows = cols, rows }
}

// ComposeOpts is a tiny helper that turns a list of options into an
// Options struct.
func ComposeOpts(mods ...func(*Options)) Options {
	var o Options
	for _, m := range mods {
		m(&o)
	}
	return o
}
