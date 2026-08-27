// Package agentflow wraps internal/agentic for external consumers.
package agentflow

import (
	"context"
	"fmt"

	"github.com/life-oss/medic/internal/agentic"
	"github.com/life-oss/medic/internal/config"
)

// Engine is the public façade over internal/agentic.
type Engine struct {
	inner *agentic.Engine
	reg   *agentic.Registry
	cfg   *config.Config
}

// NewEngine builds an engine from a target repo.
func NewEngine(target string) (*Engine, error) {
	cfg, err := config.Load(target)
	if err != nil {
		return nil, err
	}
	if target != "" {
		cfg.Target.Local = target
	}
	reg, err := agentic.StandardRegistry(cfg)
	if err != nil {
		return nil, err
	}
	return &Engine{
		inner: agentic.NewEngine(reg),
		reg:   reg,
		cfg:   cfg,
	}, nil
}

// Register adds a custom action.
func (e *Engine) Register(a agentic.Action) { e.reg.Register(a) }

// LoadFile reads a workflow YAML from disk and validates it.
func (e *Engine) LoadFile(path string) (*agentic.Workflow, error) {
	return agentic.Load(path)
}

// Run executes a workflow.
func (e *Engine) Run(ctx context.Context, w *agentic.Workflow) (*agentic.RunResult, error) {
	if w == nil {
		return nil, fmt.Errorf("agentflow: nil workflow")
	}
	return e.inner.Run(ctx, w)
}

// Verbose toggles step logging.
func (e *Engine) Verbose(v bool) { e.inner.Verbose = v }

// Names lists registered actions.
func (e *Engine) Names() []string { return e.reg.Names() }
