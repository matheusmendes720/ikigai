package health

import (
	"bytes"
	"context"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/shell"
)

// ---- Generic plumbing -------------------------------------------------------

type baseCheck struct {
	Exec *shell.Executor
	Cfg  *config.Config
}

func resolveBinary(name, fallback string) string {
	if p, err := exec.LookPath(name); err == nil {
		return p
	}
	return fallback
}

func inTarget(target string) string {
	abs, _ := filepath.Abs(target)
	return abs
}

// ---- Go test ----------------------------------------------------------------

type GoTestCheck struct{ baseCheck }

func (c *GoTestCheck) Name() string { return "go-test" }
func (c *GoTestCheck) Kind() string { return "test" }

func (c *GoTestCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	bin := c.Cfg.Target.TestCmd
	if bin == "" {
		bin = "go"
	}
	args := []string{"test", "-count=1", "-timeout", "5m", "./..."}
	if bin != "go" {
		// allow pre-built command like "task test"
		args = nil
	}
	res, err := c.Exec.Run(ctx, inTarget(target), bin, args...)
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  shell.Quote(append([]string{bin}, args...)...),
		Duration: res.Duration,
		Result:   res,
	}
	summary := shell.ParseTestOutput("go", res.Combined())
	if summary != nil {
		out.Summary = summary
		if summary.Failed > 0 {
			out.Severity = SeverityFail
			out.OK = false
			out.Err = fmt.Sprintf("%d/%d tests failed", summary.Failed, summary.Total)
		} else {
			out.Severity = SeverityOK
			out.OK = true
		}
	} else if !res.OK() {
		out.Severity = SeverityFail
		out.OK = false
		out.Err = fmt.Sprintf("exit %d", res.ExitCode)
		out.Notes = append(out.Notes, shell.FormatTail(res.Combined(), 30))
	} else {
		out.Severity = SeverityOK
		out.OK = true
	}
	return out, err
}

// ---- Coverage (framework-agnostic) -----------------------------------------

type CoverageCheck struct {
	baseCheck
	Framework string
}

func (c *CoverageCheck) Name() string { return "coverage" }
func (c *CoverageCheck) Kind() string { return "coverage" }

func (c *CoverageCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	dir := inTarget(target)
	var cmd string
	var args []string
	if c.Cfg.Target.CoverCmd != "" {
		parts := strings.Fields(c.Cfg.Target.CoverCmd)
		cmd = parts[0]
		if len(parts) > 1 {
			args = parts[1:]
		}
	} else {
		switch c.Framework {
		case "go":
			cmd, args = "go", []string{"test", "-cover", "-count=1", "./..."}
		case "pytest":
			// fall back to `pytest --cov=.`
			cmd, args = "pytest", []string{"--cov=.", "--cov-report=term", "-q"}
		case "cargo":
			cmd, args = "cargo", []string{"tarpaulin", "--print-summary"}
		}
	}
	res, err := c.Exec.Run(ctx, dir, cmd, args...)
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  shell.Quote(append([]string{cmd}, args...)...),
		Duration: res.Duration,
		Result:   res,
	}
	rep := shell.ParseCoverage(c.Framework, res.Combined())
	if rep != nil {
		out.Summary = rep
		if rep.Percent < c.Cfg.Health.MinCoveragePct {
			out.Severity = SeverityWarn
			out.OK = false
			out.Notes = append(out.Notes, fmt.Sprintf("below threshold %.0f%%", c.Cfg.Health.MinCoveragePct))
		} else {
			out.Severity = SeverityOK
			out.OK = true
		}
	} else if !res.OK() {
		out.Severity = SeverityFail
		out.OK = false
		out.Err = "coverage tool failed or missing"
	} else {
		out.Severity = SeverityWarn
		out.OK = true
		out.Notes = append(out.Notes, "no coverage % found in output")
	}
	return out, err
}

// ---- Pytest -----------------------------------------------------------------

type PytestCheck struct{ baseCheck }

func (c *PytestCheck) Name() string { return "pytest" }
func (c *PytestCheck) Kind() string { return "test" }

func (c *PytestCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	cmd := c.Cfg.Target.TestCmd
	if cmd == "" {
		cmd = "pytest"
	}
	var args []string
	if cmd == "pytest" {
		args = []string{"-q", "--tb=short"}
	}
	res, err := c.Exec.Run(ctx, inTarget(target), cmd, args...)
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  shell.Quote(append([]string{cmd}, args...)...),
		Duration: res.Duration,
		Result:   res,
	}
	sum := shell.ParseTestOutput("pytest", res.Combined())
	if sum != nil {
		out.Summary = sum
		if sum.Failed > 0 {
			out.Severity = SeverityFail
			out.OK = false
			out.Err = fmt.Sprintf("%d/%d tests failed", sum.Failed, sum.Total)
		} else {
			out.Severity = SeverityOK
			out.OK = true
		}
	} else if !res.OK() {
		out.Severity = SeverityFail
		out.OK = false
		out.Err = fmt.Sprintf("exit %d", res.ExitCode)
		out.Notes = append(out.Notes, shell.FormatTail(res.Combined(), 30))
	} else {
		out.Severity = SeverityOK
		out.OK = true
	}
	return out, err
}

// ---- Ruff lint --------------------------------------------------------------

type RuffLintCheck struct{ baseCheck }

func (c *RuffLintCheck) Name() string { return "ruff" }
func (c *RuffLintCheck) Kind() string { return "lint" }

func (c *RuffLintCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	res, err := c.Exec.Run(ctx, inTarget(target), "ruff", "check", ".")
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  "ruff check .",
		Duration: res.Duration,
		Result:   res,
	}
	sum := shell.ParseLint("ruff", res.Combined())
	out.Summary = sum
	if sum.Errors > 0 {
		out.Severity = SeverityFail
		out.OK = false
		out.Err = fmt.Sprintf("%d ruff errors", sum.Errors)
	} else if sum.Warnings > 0 {
		out.Severity = SeverityWarn
		out.OK = true
	} else {
		out.Severity = SeverityOK
		out.OK = true
	}
	return out, err
}

// ---- ESLint (Node) ---------------------------------------------------------

type ESLintCheck struct{ baseCheck }

func (c *ESLintCheck) Name() string { return "eslint" }
func (c *ESLintCheck) Kind() string { return "lint" }

func (c *ESLintCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	res, err := c.Exec.Run(ctx, inTarget(target), "npx", "eslint", ".", "--max-warnings=0")
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  "npx eslint . --max-warnings=0",
		Duration: res.Duration,
		Result:   res,
	}
	sum := shell.ParseLint("eslint", res.Combined())
	out.Summary = sum
	if sum.Issues > 0 {
		out.Severity = SeverityFail
		out.OK = false
		out.Err = fmt.Sprintf("%d lint issues", sum.Issues)
	} else {
		out.Severity = SeverityOK
		out.OK = true
	}
	return out, err
}

// ---- Cargo test -------------------------------------------------------------

type CargoTestCheck struct{ baseCheck }

func (c *CargoTestCheck) Name() string { return "cargo-test" }
func (c *CargoTestCheck) Kind() string { return "test" }

func (c *CargoTestCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	res, err := c.Exec.Run(ctx, inTarget(target), "cargo", "test", "--quiet")
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  "cargo test --quiet",
		Duration: res.Duration,
		Result:   res,
	}
	sum := shell.ParseTestOutput("cargo", res.Combined())
	if sum != nil {
		out.Summary = sum
		if sum.Failed > 0 {
			out.Severity = SeverityFail
			out.OK = false
			out.Err = fmt.Sprintf("%d/%d tests failed", sum.Failed, sum.Total)
		} else {
			out.Severity = SeverityOK
			out.OK = true
		}
	} else if res.OK() {
		out.Severity = SeverityOK
		out.OK = true
	} else {
		out.Severity = SeverityFail
		out.OK = false
		out.Err = fmt.Sprintf("exit %d", res.ExitCode)
	}
	return out, err
}

// ---- npm test ---------------------------------------------------------------

type NpmTestCheck struct{ baseCheck }

func (c *NpmTestCheck) Name() string { return "npm-test" }
func (c *NpmTestCheck) Kind() string { return "test" }

func (c *NpmTestCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	res, err := c.Exec.Run(ctx, inTarget(target), "npm", "test", "--silent")
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  "npm test --silent",
		Duration: res.Duration,
		Result:   res,
	}
	sum := shell.ParseTestOutput("jest", res.Combined())
	if sum == nil {
		sum = shell.ParseTestOutput("", res.Combined())
	}
	if sum != nil {
		out.Summary = sum
		if sum.Failed > 0 {
			out.Severity = SeverityFail
			out.OK = false
			out.Err = fmt.Sprintf("%d/%d tests failed", sum.Failed, sum.Total)
		} else {
			out.Severity = SeverityOK
			out.OK = true
		}
	} else if res.OK() {
		out.Severity = SeverityOK
		out.OK = true
	} else {
		out.Severity = SeverityFail
		out.OK = false
		out.Err = fmt.Sprintf("exit %d", res.ExitCode)
	}
	return out, err
}

// ---- Dependencies -----------------------------------------------------------

type GoDepsCheck struct{ baseCheck }

func (c *GoDepsCheck) Name() string { return "go-deps" }
func (c *GoDepsCheck) Kind() string { return "deps" }

func (c *GoDepsCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	res, err := c.Exec.Run(ctx, inTarget(target), "go", "mod", "verify")
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  "go mod verify",
		Duration: res.Duration,
		Result:   res,
	}
	if res.OK() {
		out.OK = true
		out.Severity = SeverityOK
	} else {
		out.OK = false
		out.Severity = SeverityFail
		out.Err = "go mod verify failed"
	}
	return out, err
}

type PyDepsCheck struct{ baseCheck }

func (c *PyDepsCheck) Name() string { return "py-deps" }
func (c *PyDepsCheck) Kind() string { return "deps" }

func (c *PyDepsCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	// Try `uv lock --check` first (modern), fall back to pip
	if _, lerr := exec.LookPath("uv"); lerr == nil {
		res, err := c.Exec.Run(ctx, inTarget(target), "uv", "lock", "--check")
		out := &CheckResult{
			Name:     c.Name(),
			Kind:     c.Kind(),
			Command:  "uv lock --check",
			Duration: res.Duration,
			Result:   res,
		}
		if res.OK() {
			out.OK = true
			out.Severity = SeverityOK
		} else {
			out.Severity = SeverityWarn
			out.OK = true
			out.Notes = append(out.Notes, "uv lock drift; consider `uv lock`")
		}
		return out, err
	}
	// pip check
	res, err := c.Exec.Run(ctx, inTarget(target), "pip", "check")
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  "pip check",
		Duration: res.Duration,
		Result:   res,
	}
	if res.OK() {
		out.OK = true
		out.Severity = SeverityOK
	} else {
		out.Severity = SeverityWarn
		out.OK = true
		out.Err = "dependency conflicts"
	}
	return out, err
}

type CargoDepsCheck struct{ baseCheck }

func (c *CargoDepsCheck) Name() string { return "cargo-deps" }
func (c *CargoDepsCheck) Kind() string { return "deps" }

func (c *CargoDepsCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	res, err := c.Exec.Run(ctx, inTarget(target), "cargo", "deny", "check")
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  "cargo deny check",
		Duration: res.Duration,
		Result:   res,
	}
	if res.OK() {
		out.Severity = SeverityOK
		out.OK = true
	} else {
		out.Severity = SeverityWarn
		out.OK = true
		out.Notes = append(out.Notes, "cargo deny advisories")
	}
	return out, err
}

// ---- Complexity (heuristic: long files, long funcs) ------------------------

type ComplexityCheck struct{ baseCheck }

func (c *ComplexityCheck) Name() string { return "complexity" }
func (c *ComplexityCheck) Kind() string { return "complexity" }

func (c *ComplexityCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	// Heuristic: walk the source tree, count lines per file; flag > 600 lines.
	type entry struct {
		Path  string `json:"path"`
		Lines int    `json:"lines"`
	}
	var files []entry
	skip := map[string]bool{".git": true, "node_modules": true, ".venv": true, "venv": true, "target": true, ".medic": true, "dist": true, "build": true}
	_ = filepath.WalkDir(inTarget(target), func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			if skip[d.Name()] {
				return filepath.SkipDir
			}
			return nil
		}
		// Cheap line count: count \n in file
		data, err := os.ReadFile(path)
		if err != nil || len(data) == 0 {
			return nil
		}
		lines := bytes.Count(data, []byte("\n")) + 1
		if lines > 600 {
			files = append(files, entry{Path: path, Lines: lines})
		}
		return nil
	})
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  "(internal heuristic: files > 600 lines)",
		Severity: SeverityOK,
		OK:       true,
	}
	if len(files) > 0 {
		out.Summary = map[string]any{
			"oversized_files": files,
			"count":           len(files),
		}
		if len(files) > c.Cfg.Health.MaxComplexity {
			out.Severity = SeverityWarn
			out.Notes = append(out.Notes, fmt.Sprintf("%d files exceed 600 LOC (threshold %d)", len(files), c.Cfg.Health.MaxComplexity))
		}
	}
	_ = ctx
	_ = runtime.GOOS // keep import
	return out, nil
}

// ---- Generic run check ------------------------------------------------------

type GenericRunCheck struct {
	baseCheck
	NameStr string
	Cmd     string
	Args    []string
}

func (c *GenericRunCheck) Name() string { return c.NameStr }
func (c *GenericRunCheck) Kind() string { return "smoke" }

func (c *GenericRunCheck) Run(ctx context.Context, target string, _ *config.Config) (*CheckResult, error) {
	res, err := c.Exec.Run(ctx, inTarget(target), c.Cmd, c.Args...)
	out := &CheckResult{
		Name:     c.Name(),
		Kind:     c.Kind(),
		Command:  shell.Quote(append([]string{c.Cmd}, c.Args...)...),
		Duration: res.Duration,
		Result:   res,
	}
	if res.OK() {
		out.OK = true
		out.Severity = SeverityOK
	} else {
		out.OK = false
		out.Severity = SeverityFail
		out.Err = fmt.Sprintf("exit %d", res.ExitCode)
	}
	return out, err
}
