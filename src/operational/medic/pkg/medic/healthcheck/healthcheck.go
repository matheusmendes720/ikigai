// Package healthcheck wraps internal/health for external consumers.
package healthcheck

import (
	"context"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/health"
)

// Checker is the public façade.
type Checker struct {
	cfg *config.Config
}

// New builds a Checker rooted at target.
func New(target string) (*Checker, error) {
	cfg, err := config.Load(target)
	if err != nil {
		return nil, err
	}
	if target != "" {
		cfg.Target.Local = target
	}
	return &Checker{cfg: cfg}, nil
}

// Run executes the default check set for the detected language.
func (c *Checker) Run(ctx context.Context) (*health.Report, error) {
	return health.NewOrchestrator(c.cfg).Run(ctx, c.cfg.Target.Local)
}

// Skip toggles a check off (test|lint|coverage|deps|complexity).
func (c *Checker) Skip(name string) {
	switch name {
	case "test":
		c.cfg.Health.RunTests = false
	case "lint":
		c.cfg.Health.RunLint = false
	case "coverage":
		c.cfg.Health.RunCoverage = false
	case "deps":
		c.cfg.Health.RunDeps = false
	case "complexity":
		c.cfg.Health.RunComplex = false
	}
}

// SetMinCoverage overrides the coverage gate.
func (c *Checker) SetMinCoverage(pct float64) { c.cfg.Health.MinCoveragePct = pct }
