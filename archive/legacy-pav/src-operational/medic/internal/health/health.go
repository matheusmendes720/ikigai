// Package health runs a battery of health checks against a target repo:
// tests, lint, coverage, dependencies, complexity. Results feed into the
// review pipeline (as a gate) and the dashboard.
package health

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/shell"
)

// Report aggregates results of all checks.
type Report struct {
	Target    string         `json:"target"`
	Language  string         `json:"language"`
	Generated time.Time      `json:"generated"`
	Checks    []*CheckResult `json:"checks"`
	OK        bool           `json:"ok"`
	Score     int            `json:"score"` // 0..100
}

// CheckResult is the outcome of one Check.
type CheckResult struct {
	Name     string         `json:"name"`
	Kind     string         `json:"kind"` // test|lint|coverage|deps|complexity
	OK       bool           `json:"ok"`
	Severity Severity       `json:"severity"` // ok|warn|fail
	Summary  any            `json:"summary,omitempty"`
	Notes    []string       `json:"notes,omitempty"`
	Command  string         `json:"command"`
	Duration time.Duration  `json:"duration_ns"`
	Result   *shell.Result  `json:"raw,omitempty"`
	Err      string         `json:"error,omitempty"`
}

// Severity of a check outcome.
type Severity string

const (
	SeverityOK   Severity = "ok"
	SeverityWarn Severity = "warn"
	SeverityFail Severity = "fail"
)

// Check is the interface each health check implements.
type Check interface {
	Name() string
	Kind() string
	Run(ctx context.Context, target string, cfg *config.Config) (*CheckResult, error)
}

// Orchestrator runs a list of checks against a target.
type Orchestrator struct {
	executor *shell.Executor
	checks   []Check
	cfg      *config.Config
}

// NewOrchestrator builds the default check set for the detected language.
func NewOrchestrator(cfg *config.Config) *Orchestrator {
	exec := shell.NewExecutor()
	lang := cfg.Target.Language
	if lang == "" {
		lang = detectLanguage(cfg.Target.Local)
	}
	cfg.Target.Language = lang
	o := &Orchestrator{executor: exec, cfg: cfg}
	for _, c := range defaultsFor(lang, cfg, exec) {
		o.checks = append(o.checks, c)
	}
	return o
}

// Add appends a custom check.
func (o *Orchestrator) Add(c Check) { o.checks = append(o.checks, c) }

// Checks returns the registered checks.
func (o *Orchestrator) Checks() []Check { return o.checks }

// Run executes every registered check and aggregates a Report.
func (o *Orchestrator) Run(ctx context.Context, target string) (*Report, error) {
	if target == "" {
		target = o.cfg.Target.Local
	}
	rep := &Report{
		Target:    target,
		Language:  o.cfg.Target.Language,
		Generated: time.Now(),
	}
	for _, c := range o.checks {
		// Per-check timeout
		cctx, cancel := context.WithTimeout(ctx, o.cfg.Health.Timeout)
		res, _ := c.Run(cctx, target, o.cfg)
		cancel()
		if res == nil {
			res = &CheckResult{Name: c.Name(), Kind: c.Kind(), OK: false, Severity: SeverityFail, Err: "check returned nil"}
		}
		rep.Checks = append(rep.Checks, res)
	}
	rep.OK, rep.Score = aggregate(rep)
	return rep, nil
}

func aggregate(r *Report) (bool, int) {
	if len(r.Checks) == 0 {
		return true, 100
	}
	failed, warn := 0, 0
	score := 100
	for _, c := range r.Checks {
		switch c.Severity {
		case SeverityFail:
			failed++
			score -= 25
		case SeverityWarn:
			warn++
			score -= 8
		}
	}
	if score < 0 {
		score = 0
	}
	return failed == 0, score
}

func defaultsFor(lang string, cfg *config.Config, exec *shell.Executor) []Check {
	mk := func(c Check) Check { return c }
	_ = mk
	switch lang {
	case "go":
		return []Check{
			&GoTestCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
			&CoverageCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}, Framework: "go"},
			&GoDepsCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
			&ComplexityCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
		}
	case "python":
		return []Check{
			&PytestCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
			&CoverageCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}, Framework: "pytest"},
			&RuffLintCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
			&PyDepsCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
		}
	case "rust":
		return []Check{
			&CargoTestCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
			&CoverageCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}, Framework: "cargo"},
			&CargoDepsCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
		}
	case "node":
		return []Check{
			&NpmTestCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
			&ESLintCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}},
		}
	default:
		return []Check{
			&GenericRunCheck{baseCheck: baseCheck{Exec: exec, Cfg: cfg}, NameStr: "smoke", Cmd: "true"},
		}
	}
}

// detectLanguage guesses the project language from common manifest files.
func detectLanguage(target string) string {
	checks := []struct {
		file string
		lang string
	}{
		{"go.mod", "go"},
		{"Cargo.toml", "rust"},
		{"pyproject.toml", "python"},
		{"setup.py", "python"},
		{"requirements.txt", "python"},
		{"package.json", "node"},
		{"pom.xml", "java"},
		{"build.gradle", "java"},
	}
	for _, c := range checks {
		if _, err := os.Stat(filepath.Join(target, c.file)); err == nil {
			return c.lang
		}
	}
	return "mixed"
}

// FormatPretty returns a human-friendly report.
func FormatPretty(rep *Report) string {
	var sb strings.Builder
	fmt.Fprintf(&sb, "Health report — %s (%s)\n", rep.Target, rep.Language)
	fmt.Fprintf(&sb, "Score: %d/100   OK=%v\n\n", rep.Score, rep.OK)
	for _, c := range rep.Checks {
		icon := "✓"
		switch c.Severity {
		case SeverityWarn:
			icon = "⚠"
		case SeverityFail:
			icon = "✗"
		}
		fmt.Fprintf(&sb, "  %s %-14s %-10s  %s\n", icon, c.Name, c.Kind, c.Err)
		if c.Summary != nil {
			fmt.Fprintf(&sb, "      %+v\n", c.Summary)
		}
		if len(c.Notes) > 0 {
			for _, n := range c.Notes {
				fmt.Fprintf(&sb, "      · %s\n", n)
			}
		}
	}
	return sb.String()
}
