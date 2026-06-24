// Package pattern detects UX / code / workflow patterns in a codebase and
// suggests improvements. It is the engine behind `medic patterns` and feeds
// the visual-improvement loop.
//
// Three families:
//
//   - UX      — derived from captured TUI frames (via internal/visual).
//   - Code    — AST-light heuristics over source files (works for any lang).
//   - Workflow— inferred from git history + GitHub PR/Issue signals.
package pattern

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/life-oss/medic/internal/gitx"
)

// Family is the pattern bucket.
type Family string

const (
	FamilyUX      Family = "ux"
	FamilyCode    Family = "code"
	FamilyWorkflow Family = "workflow"
)

// Severity of a finding.
type Severity string

const (
	SeverityInfo     Severity = "info"
	SeverityLow      Severity = "low"
	SeverityMedium   Severity = "medium"
	SeverityHigh     Severity = "high"
	SeverityCritical Severity = "critical"
)

// Finding mirrors review.Finding but is defined here so the pattern package
// has no review dependency.
type Finding struct {
	ID         string   `json:"id"`
	Family     Family   `json:"family"`
	Severity   Severity `json:"severity"`
	Path       string   `json:"path,omitempty"`
	Line       int      `json:"line,omitempty"`
	Title      string   `json:"title"`
	Rationale  string   `json:"rationale"`
	Suggestion string   `json:"suggestion,omitempty"`
	Rule       string   `json:"rule,omitempty"`
}

// Engine runs detectors.
type Engine struct {
	// MinSeverity filters out findings below this floor.
	MinSeverity Severity
	// Enabled families.
	EnableUX, EnableCode, EnableWorkflow bool
}

// NewEngine returns an Engine with all families on.
func NewEngine() *Engine {
	return &Engine{
		MinSeverity:   SeverityInfo,
		EnableUX:      true,
		EnableCode:    true,
		EnableWorkflow: true,
	}
}

// Scan runs the requested families against the target.
// target can be a directory (code/workflow) or a TUI-frame snapshot (ux).
func (e *Engine) Scan(ctx context.Context, target string) ([]Finding, error) {
	var out []Finding
	if e.EnableCode {
		fs, err := ScanCode(ctx, target)
		if err != nil {
			return nil, err
		}
		out = append(out, fs...)
	}
	if e.EnableWorkflow {
		fs, _ := ScanWorkflow(ctx, target)
		out = append(out, fs...)
	}
	return out, nil
}

// ---- Code patterns --------------------------------------------------------

// ScanCode walks target and applies code-pattern detectors.
func ScanCode(ctx context.Context, target string) ([]Finding, error) {
	var out []Finding
	skip := map[string]bool{
		".git": true, "node_modules": true, ".venv": true, "venv": true,
		"target": true, ".medic": true, "dist": true, "build": true,
		"__pycache__": true, ".pytest_cache": true, ".mypy_cache": true,
	}
	err := filepath.WalkDir(target, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if err := ctx.Err(); err != nil {
			return err
		}
		if d.IsDir() {
			if skip[d.Name()] {
				return filepath.SkipDir
			}
			return nil
		}
		ext := strings.ToLower(filepath.Ext(path))
		switch ext {
		case ".py", ".go", ".rs", ".ts", ".tsx", ".js", ".jsx":
			data, err := os.ReadFile(path)
			if err != nil {
				return nil
			}
			out = append(out, scanFile(string(data), path, ext)...)
		}
		return nil
	})
	return out, err
}

func scanFile(text, path, ext string) []Finding {
	var out []Finding
	out = append(out, scanTODOs(text, path)...)
	out = append(out, scanPrintDebugging(text, path, ext)...)
	out = append(out, scanLongLines(text, path)...)
	out = append(out, scanMagicNumbers(text, path)...)
	out = append(out, scanHardcodedPaths(text, path)...)
	out = append(out, scanEmptyHandlers(text, path, ext)...)
	return out
}

var reTODO = regexp.MustCompile(`(?i)\b(TODO|FIXME|XXX|HACK)\b[^\n]*`)

func scanTODOs(text, path string) []Finding {
	var out []Finding
	scanner := bufio.NewScanner(strings.NewReader(text))
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		line := scanner.Text()
		if m := reTODO.FindString(line); m != "" {
			out = append(out, Finding{
				ID:        fmt.Sprintf("code.todo.%s.%d", path, lineNo),
				Family:    FamilyCode,
				Severity:  SeverityInfo,
				Path:      path,
				Line:      lineNo,
				Title:     "TODO marker",
				Rationale: "Unresolved TODO/FIXME markers accumulate technical debt.",
				Suggestion: "Open a tracking issue, reference its # here, and resolve before merge.",
				Rule:      "no-orphan-todo",
			})
		}
	}
	return out
}

var (
	rePrintPy = regexp.MustCompile(`(?m)^\s*print\s*\(`)
	rePrintGo = regexp.MustCompile(`(?m)^\s*fmt\.Println?\(`)
	rePrintJS = regexp.MustCompile(`(?m)^\s*console\.(log|debug|info)\(`)
)

func scanPrintDebugging(text, path, ext string) []Finding {
	var re *regexp.Regexp
	switch ext {
	case ".py":
		re = rePrintPy
	case ".go":
		re = rePrintGo
	case ".ts", ".tsx", ".js", ".jsx":
		re = rePrintJS
	default:
		return nil
	}
	var out []Finding
	scanner := bufio.NewScanner(strings.NewReader(text))
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		if re.MatchString(scanner.Text()) {
			out = append(out, Finding{
				ID:        fmt.Sprintf("code.print.%s.%d", path, lineNo),
				Family:    FamilyCode,
				Severity:  SeverityLow,
				Path:      path,
				Line:      lineNo,
				Title:     "Debug print statement left in source",
				Rationale: "Print/debug statements in non-debug code indicate incomplete instrumentation.",
				Suggestion: "Route through a structured logger; gate behind a verbose/debug flag.",
				Rule:      "no-debug-prints",
			})
		}
	}
	return out
}

func scanLongLines(text, path string) []Finding {
	var out []Finding
	scanner := bufio.NewScanner(strings.NewReader(text))
	scanner.Buffer(make([]byte, 1024*1024), 8*1024*1024)
	lineNo := 0
	count := 0
	for scanner.Scan() {
		lineNo++
		if len(scanner.Text()) > 200 {
			count++
		}
	}
	if count > 0 {
		out = append(out, Finding{
			ID:        fmt.Sprintf("code.long-lines.%s", path),
			Family:    FamilyCode,
			Severity:  SeverityInfo,
			Path:      path,
			Title:     fmt.Sprintf("%d lines exceed 200 chars", count),
			Rationale: "Very long lines hurt diffs and screen reading.",
			Suggestion: "Wrap / extract; let the formatter do it.",
			Rule:      "max-line-length-soft",
		})
	}
	return out
}

var reMagicNum = regexp.MustCompile(`(?m)\b(\d{3,})\b`)

func scanMagicNumbers(text, path string) []Finding {
	var out []Finding
	matches := reMagicNum.FindAllString(text, -1)
	if len(matches) >= 8 {
		out = append(out, Finding{
			ID:        fmt.Sprintf("code.magic-num.%s", path),
			Family:    FamilyCode,
			Severity:  SeverityInfo,
			Path:      path,
			Title:     fmt.Sprintf("%d multi-digit numeric literals", len(matches)),
			Rationale: "Many large numeric literals are usually a config block in disguise.",
			Suggestion: "Extract to a named constant or config entry.",
			Rule:      "named-constants",
		})
	}
	return out
}

var reHardcodedPath = regexp.MustCompile(`(?m)["'](/[a-z]+/[a-z]+|/usr/[a-z]+|C:\\[a-zA-Z]+)["']`)

func scanHardcodedPaths(text, path string) []Finding {
	var out []Finding
	matches := reHardcodedPath.FindAllString(text, -1)
	if len(matches) > 0 {
		out = append(out, Finding{
			ID:        fmt.Sprintf("code.hardcoded-path.%s", path),
			Family:    FamilyCode,
			Severity:  SeverityMedium,
			Path:      path,
			Title:     fmt.Sprintf("%d hardcoded paths", len(matches)),
			Rationale: "Hardcoded paths break portability across OSes and user setups.",
			Suggestion: "Use $XDG_DATA_HOME / %APPDATA% / os.UserConfigDir().",
			Rule:      "no-hardcoded-paths",
		})
	}
	return out
}

var (
	rePass     = regexp.MustCompile(`(?m)^\s*pass\s*$`)
	reEmptyJS  = regexp.MustCompile(`(?m)\{\s*\}`)
	reEmptyGo  = regexp.MustCompile(`(?m)\{\s*\}`)
)

func scanEmptyHandlers(text, path, ext string) []Finding {
	var re *regexp.Regexp
	switch ext {
	case ".py":
		re = rePass
	case ".go", ".ts", ".tsx", ".js", ".jsx", ".rs":
		re = reEmptyGo
	default:
		return nil
	}
	_ = reEmptyJS
	var out []Finding
	matches := re.FindAllString(text, -1)
	if len(matches) >= 3 {
		out = append(out, Finding{
			ID:        fmt.Sprintf("code.empty.%s", path),
			Family:    FamilyCode,
			Severity:  SeverityLow,
			Path:      path,
			Title:     fmt.Sprintf("%d empty handlers/blocks", len(matches)),
			Rationale: "Empty handlers often indicate unfinished features or bug masking.",
			Suggestion: "Implement, raise NotImplementedError, or delete.",
			Rule:      "no-empty-handlers",
		})
	}
	return out
}

// ---- Workflow patterns ----------------------------------------------------

// ScanWorkflow inspects git history for workflow anti-patterns.
func ScanWorkflow(ctx context.Context, target string) ([]Finding, error) {
	var out []Finding
	r, err := gitx.Open(target)
	if err != nil {
		return nil, nil // not a git repo: silently skip
	}
	commits, err := r.Log(ctx, "HEAD", 200)
	if err != nil {
		return nil, nil
	}
	// Detect revert-within-window
	for i, c := range commits {
		if strings.HasPrefix(strings.ToLower(c.Subject), "revert") && i < 20 {
			out = append(out, Finding{
				ID:        "wf.recent-revert",
				Family:    FamilyWorkflow,
				Severity:  SeverityMedium,
				Title:     "Recent revert in history: " + c.Subject,
				Rationale: "Reverts within a feature branch suggest unstable scope or hot fix.",
				Suggestion: "Investigate the underlying bug; add a regression test.",
				Rule:      "no-recent-revert",
			})
			break
		}
	}
	// Detect drive-by commits (no conventional prefix / huge churn)
	for _, c := range commits {
		subject := strings.TrimSpace(c.Subject)
		if subject == "" {
			continue
		}
		first := strings.SplitN(subject, ":", 2)[0]
		if !looksConventional(first) && len(subject) > 80 {
			out = append(out, Finding{
				ID:        "wf.commit.no-convention",
				Family:    FamilyWorkflow,
				Severity:  SeverityInfo,
				Title:     "Commit without conventional prefix: " + truncate(subject, 80),
				Rationale: "Non-conventional commits defeat changelog automation.",
				Suggestion: "Use Conventional Commits: feat:, fix:, chore:, refactor:.",
				Rule:      "conventional-commits",
			})
		}
	}
	return out, nil
}

func looksConventional(prefix string) bool {
	known := []string{"feat", "fix", "chore", "docs", "refactor", "test", "perf", "build", "ci", "style"}
	p := strings.ToLower(strings.TrimSpace(prefix))
	// Allow optional scope: feat(scope)
	if i := strings.Index(p, "("); i >= 0 {
		p = p[:i]
	}
	for _, k := range known {
		if p == k {
			return true
		}
	}
	return false
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "…"
}

// ---- UX patterns ---------------------------------------------------------

// UXSignal is the data the UX detector expects (a captured frame + summary).
type UXSignal struct {
	Frame       any    // *visual.Frame (interface to avoid import cycle)
	Cols        int    `json:"cols"`
	Rows        int    `json:"rows"`
	TitleText   string `json:"title_text,omitempty"`
	HasBorders  bool   `json:"has_borders"`
	BorderChar  string `json:"border_char,omitempty"`
	LowContrast bool   `json:"low_contrast"`
	Align       string `json:"align,omitempty"` // ragged | aligned
}

// ScanUX inspects a UXSignal (typically derived from a captured frame).
func ScanUX(sig UXSignal) []Finding {
	var out []Finding
	if sig.Cols == 0 || sig.Rows == 0 {
		out = append(out, Finding{
			ID:        "ux.dimensions-unknown",
			Family:    FamilyUX,
			Severity:  SeverityMedium,
			Title:     "Frame dimensions unknown",
			Rationale: "Capturing a frame at a known size is required for diffing.",
			Suggestion: "Pass --cols and --rows, or rely on TUI's auto-detect.",
			Rule:      "ux-known-size",
		})
		return out
	}
	if !sig.HasBorders {
		out = append(out, Finding{
			ID:        "ux.no-borders",
			Family:    FamilyUX,
			Severity:  SeverityLow,
			Title:     "Layout uses no borders",
			Rationale: "Borders help users scan structured layouts; pure spaces can blur panels.",
			Suggestion: "Add 1-cell borders around panels (use box-drawing glyphs).",
			Rule:      "ux-use-borders",
		})
	}
	if sig.LowContrast {
		out = append(out, Finding{
			ID:        "ux.low-contrast",
			Family:    FamilyUX,
			Severity:  SeverityHigh,
			Title:     "Low-contrast text detected",
			Rationale: "Low-contrast text is unreadable for users with visual impairments and on poor displays.",
			Suggestion: "Use fg/bg pairs with luminance delta ≥ 4.5:1 (WCAG AA).",
			Rule:      "ux-wcag-aa",
		})
	}
	if sig.Align == "ragged" {
		out = append(out, Finding{
			ID:        "ux.ragged",
			Family:    FamilyUX,
			Severity:  SeverityLow,
			Title:     "Ragged right edge in layout",
			Rationale: "Ragged edges make tabular content harder to scan.",
			Suggestion: "Pad cells to a fixed width; use tview's table primitive or column layout.",
			Rule:      "ux-align-columns",
		})
	}
	if sig.Rows > 0 && sig.Rows < 20 {
		out = append(out, Finding{
			ID:        "ux.too-short",
			Family:    FamilyUX,
			Severity:  SeverityMedium,
			Title:     fmt.Sprintf("Layout only %d rows tall", sig.Rows),
			Rationale: "Below 20 rows, status bars and panels compete for space.",
			Suggestion: "Use a layout that collapses secondary panels below 24 rows.",
			Rule:      "ux-min-rows",
		})
	}
	return out
}

// ---- Output ----------------------------------------------------------------

// FormatTable returns a text table of findings.
func FormatTable(fs []Finding) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%-12s %-10s %-30s %s\n", "FAMILY", "SEVERITY", "RULE", "TITLE"))
	sb.WriteString(strings.Repeat("─", 80) + "\n")
	for _, f := range fs {
		title := truncate(f.Title, 60)
		fmt.Fprintf(&sb, "%-12s %-10s %-30s %s\n", string(f.Family), string(f.Severity), truncate(f.Rule, 30), title)
	}
	return sb.String()
}
