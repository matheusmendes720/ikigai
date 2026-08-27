// Package agentic runs declarative YAML agentic workflows.
//
// A workflow is a list of Steps. Each Step has a `use:` reference to a
// registered Action (e.g. github.fetch_pr, health.run, visual.run_golden,
// llm.review). Steps can guard with `when:` (Go-template-ish expressions over
// the shared StepContext), retry on failure, and reference prior step output
// via the `.steps.<id>.output` path.
package agentic

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sync"
	"time"

	"gopkg.in/yaml.v3"
)

// Workflow is the top-level YAML definition.
type Workflow struct {
	Name        string         `yaml:"name"`
	Description string         `yaml:"description,omitempty"`
	Defaults    StepDefaults   `yaml:"defaults,omitempty"`
	Steps       []Step         `yaml:"steps"`
}

// StepDefaults sets values applied to every step unless overridden.
type StepDefaults struct {
	Timeout time.Duration `yaml:"timeout,omitempty"`
	Retries int           `yaml:"retries,omitempty"`
}

// Step is one unit of work.
type Step struct {
	ID         string                 `yaml:"id"`
	Use        string                 `yaml:"use"`
	When       string                 `yaml:"when,omitempty"`
	Args       map[string]any         `yaml:"args,omitempty"`
	Timeout    time.Duration          `yaml:"timeout,omitempty"`
	Retries    int                    `yaml:"retries,omitempty"`
	ParallelWith []string             `yaml:"parallel_with,omitempty"` // siblings to run with
}

// StepResult is the outcome of one step.
type StepResult struct {
	ID      string         `json:"id"`
	OK      bool           `json:"ok"`
	Output  any            `json:"output,omitempty"`
	Err     string         `json:"error,omitempty"`
	Started time.Time      `json:"started"`
	Duration time.Duration `json:"duration_ns"`
}

// RunResult is the full trace.
type RunResult struct {
	Workflow string       `json:"workflow"`
	Steps    []StepResult `json:"steps"`
	OK       bool         `json:"ok"`
	Started  time.Time    `json:"started"`
	Duration time.Duration `json:"duration_ns"`
}

// Action is the contract a step uses.
type Action interface {
	Name() string
	Run(ctx context.Context, args map[string]any) (any, error)
}

// Registry holds actions by name.
type Registry struct {
	mu      sync.RWMutex
	actions map[string]Action
}

// NewRegistry returns an empty registry.
func NewRegistry() *Registry {
	return &Registry{actions: map[string]Action{}}
}

// Register adds an action.
func (r *Registry) Register(a Action) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.actions[a.Name()] = a
}

// MustRegister panics on duplicate registration.
func (r *Registry) MustRegister(a Action) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.actions[a.Name()]; ok {
		panic("agentic: duplicate action " + a.Name())
	}
	r.actions[a.Name()] = a
}

// Get fetches an action by name.
func (r *Registry) Get(name string) (Action, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	a, ok := r.actions[name]
	return a, ok
}

// Names returns the registered action names (unsorted).
func (r *Registry) Names() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]string, 0, len(r.actions))
	for n := range r.actions {
		out = append(out, n)
	}
	return out
}

// Engine runs workflows.
type Engine struct {
	Registry *Registry
	// Verbose toggles per-step logs.
	Verbose bool
	// Logger writes step status (default: os.Stderr).
	Logger func(string)
}

// NewEngine builds an engine.
func NewEngine(reg *Registry) *Engine {
	return &Engine{
		Registry: reg,
		Logger: func(s string) {
			fmt.Fprintln(os.Stderr, s)
		},
	}
}

// Load reads a workflow YAML from disk.
func Load(path string) (*Workflow, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var w Workflow
	if err := yaml.Unmarshal(data, &w); err != nil {
		return nil, err
	}
	if err := w.Validate(); err != nil {
		return nil, err
	}
	return &w, nil
}

// Validate sanity-checks the workflow.
func (w *Workflow) Validate() error {
	if w.Name == "" {
		return errors.New("workflow: missing name")
	}
	if len(w.Steps) == 0 {
		return errors.New("workflow: no steps")
	}
	seen := map[string]bool{}
	for _, s := range w.Steps {
		if s.ID == "" {
			return fmt.Errorf("workflow: step missing id")
		}
		if seen[s.ID] {
			return fmt.Errorf("workflow: duplicate step id %q", s.ID)
		}
		seen[s.ID] = true
		if s.Use == "" {
			return fmt.Errorf("workflow: step %q missing use:", s.ID)
		}
	}
	return nil
}

// Run executes the workflow sequentially. (Parallel branches are queued but
// processed serially in this version; future: parallel-with fan-out.)
func (e *Engine) Run(ctx context.Context, w *Workflow) (*RunResult, error) {
	if err := w.Validate(); err != nil {
		return nil, err
	}
	res := &RunResult{
		Workflow: w.Name,
		Started:  time.Now(),
	}
	// Mutable shared step outputs (used by `when:` evaluation later).
	outputs := map[string]any{}
	allOK := true
	for _, s := range w.Steps {
		if s.When != "" && !EvalGuard(s.When, outputs) {
			res.Steps = append(res.Steps, StepResult{
				ID:      s.ID,
				OK:      true,
				Started: time.Now(),
				Err:     "skipped (when: false)",
			})
			if e.Verbose {
				e.Logger(fmt.Sprintf("step %s ⊘ skipped (when: false)", s.ID))
			}
			continue
		}
		sr := e.runStep(ctx, s, w.Defaults, outputs)
		res.Steps = append(res.Steps, sr)
		if !sr.OK {
			allOK = false
			if e.Verbose {
				e.Logger(fmt.Sprintf("step %q failed: %s", s.ID, sr.Err))
			}
		}
		outputs[s.ID] = sr.Output
	}
	res.OK = allOK
	res.Duration = time.Since(res.Started)
	return res, nil
}

func (e *Engine) runStep(ctx context.Context, s Step, def StepDefaults, outputs map[string]any) StepResult {
	start := time.Now()
	// Resolve timeout
	timeout := s.Timeout
	if timeout == 0 {
		timeout = def.Timeout
	}
	if timeout == 0 {
		timeout = 5 * time.Minute
	}
	// Resolve retries
	retries := s.Retries
	if retries == 0 {
		retries = def.Retries
	}

	sr := StepResult{ID: s.ID, Started: start}
	cctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	act, ok := e.Registry.Get(s.Use)
	if !ok {
		sr.Err = fmt.Sprintf("unknown action %q", s.Use)
		sr.Duration = time.Since(start)
		return sr
	}

	var lastErr error
	for attempt := 0; attempt <= retries; attempt++ {
		out, err := act.Run(cctx, s.Args)
		if err == nil {
			sr.OK = true
			sr.Output = out
			sr.Duration = time.Since(start)
			if e.Verbose {
				e.Logger(fmt.Sprintf("step %s ✔ (%s)", s.ID, sr.Duration))
			}
			return sr
		}
		lastErr = err
		sr.Err = err.Error()
		if e.Verbose {
			e.Logger(fmt.Sprintf("step %s attempt %d failed: %v", s.ID, attempt+1, err))
		}
		// simple backoff
		select {
		case <-cctx.Done():
			sr.Err = cctx.Err().Error()
			sr.Duration = time.Since(start)
			return sr
		case <-time.After(time.Duration(attempt+1) * 200 * time.Millisecond):
		}
	}
	sr.Duration = time.Since(start)
	if lastErr != nil {
		sr.Err = lastErr.Error()
	}
	return sr
}
