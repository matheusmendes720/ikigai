package shell

import (
	"bufio"
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// TestSummary is a generic test-runner summary detected by regex matching.
// We support: pytest, cargo test, go test, jest, vitest, mocha, rspec, maven.
type TestSummary struct {
	Framework string         `json:"framework"`
	Passed    int            `json:"passed"`
	Failed    int            `json:"failed"`
	Skipped   int            `json:"skipped"`
	Total     int            `json:"total"`
	Duration  string         `json:"duration,omitempty"`
	Raw       map[string]int `json:"raw,omitempty"` // framework-specific extras
}

// PytestSummaryLines = ["5 passed, 2 failed in 1.23s", "===== 5 passed in 0.42s ====="]
var (
	rePytest     = regexp.MustCompile(`(?m)(?:=+\s*)?(\d+)\s+passed`)
	rePytestFail = regexp.MustCompile(`(?m)(?:=+\s*)?(\d+)\s+failed`)
	rePytestSkip = regexp.MustCompile(`(?m)(?:=+\s*)?(\d+)\s+skipped`)
	rePytestErr  = regexp.MustCompile(`(?m)(?:=+\s*)?(\d+)\s+error`)
	rePytestDur  = regexp.MustCompile(`(?m)in\s+([\d.]+s)`)

	reGoTest   = regexp.MustCompile(`(?m)^(ok|FAIL|---)\s+(\S+)`)
	reGoPass   = regexp.MustCompile(`(?m)^--- PASS:\s+(\S+)`)
	reGoFail   = regexp.MustCompile(`(?m)^--- FAIL:\s+(\S+)`)
	reGoSkip   = regexp.MustCompile(`(?m)^--- SKIP:\s+(\S+)`)

	reCargoSummary = regexp.MustCompile(`(?m)test result:\s+(ok|FAILED)\.\s+(\d+)\s+passed;\s+(\d+)\s+failed;\s+(\d+)\s+ignored`)
	reJestSummary  = regexp.MustCompile(`(?m)Tests:\s+(\d+)\s+passed,\s+(\d+)\s+total`)
	reMavenSummary = regexp.MustCompile(`(?m)Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)`)
)

// ParseTestOutput inspects combined stdout+stderr and returns a summary if recognized.
func ParseTestOutput(frameworkHint, text string) *TestSummary {
	s := &TestSummary{Framework: detectFramework(frameworkHint, text), Raw: map[string]int{}}
	switch s.Framework {
	case "pytest":
		s.Passed = sumInts(rePytest.FindAllString(text, -1))
		s.Failed = sumInts(rePytestFail.FindAllString(text, -1))
		s.Skipped = sumInts(rePytestSkip.FindAllString(text, -1))
		// pytest's "errors" are a separate counter but often lumped with failed
		errs := sumInts(rePytestErr.FindAllString(text, -1))
		s.Raw["errors"] = errs
		s.Failed += errs
		if m := rePytestDur.FindStringSubmatch(text); m != nil {
			s.Duration = m[1]
		}
	case "go":
		// Heuristic from `go test -v` output
		s.Passed = len(reGoPass.FindAllString(text, -1))
		s.Failed = len(reGoFail.FindAllString(text, -1))
		s.Skipped = len(reGoSkip.FindAllString(text, -1))
	case "cargo":
		if m := reCargoSummary.FindStringSubmatch(text); m != nil {
			s.Passed = atoi(m[2])
			s.Failed = atoi(m[3])
			s.Skipped = atoi(m[4])
		}
	case "jest":
		if m := reJestSummary.FindStringSubmatch(text); m != nil {
			s.Total = atoi(m[2])
			s.Passed = atoi(m[1])
			s.Failed = s.Total - s.Passed
		}
	case "maven":
		if m := reMavenSummary.FindStringSubmatch(text); m != nil {
			s.Total = atoi(m[1])
			s.Failed = atoi(m[2]) + atoi(m[3])
			s.Skipped = atoi(m[4])
			s.Passed = s.Total - s.Failed - s.Skipped
		}
	default:
		return nil
	}
	s.Total = s.Passed + s.Failed + s.Skipped
	return s
}

func detectFramework(hint, text string) string {
	h := strings.ToLower(hint)
	switch {
	case strings.Contains(h, "pytest"), strings.Contains(text, "pytest"), strings.Contains(text, "===") && strings.Contains(text, "passed"):
		if strings.Contains(text, "passed") || strings.Contains(text, "failed") {
			return "pytest"
		}
	case strings.Contains(h, "go"), strings.Contains(text, "--- PASS:"), strings.Contains(text, "--- FAIL:"):
		return "go"
	case strings.Contains(h, "cargo"), strings.Contains(text, "test result:"):
		return "cargo"
	case strings.Contains(h, "jest"), strings.Contains(text, "Tests:") && strings.Contains(text, "Snapshots:"):
		return "jest"
	case strings.Contains(h, "maven"), strings.Contains(text, "Tests run:"):
		return "maven"
	}
	return ""
}

func sumInts(matches []string) int {
	total := 0
	for _, m := range matches {
		// pull first integer from the string
		re := regexp.MustCompile(`\d+`)
		if n := re.FindString(m); n != "" {
			total += atoi(n)
		}
	}
	return total
}

func atoi(s string) int {
	n, _ := strconv.Atoi(s)
	return n
}

// ParseCoverageLines finds coverage reports (pytest-cov, go test -cover, cargo tarpaulin).
type CoverageReport struct {
	Framework string  `json:"framework"`
	Percent   float64 `json:"percent"`
	File      string  `json:"file,omitempty"`
}

var (
	rePytestCovTotal   = regexp.MustCompile(`(?m)TOTAL\s+\d+\s+\d+\s+(\d+)%`)
	reGoCoverTotal     = regexp.MustCompile(`(?m)^total:\s+\(statements\)\s+(\d+\.\d+)%`)
	reCargoCoverTotal  = regexp.MustCompile(`(?m)^\s*(\d+\.\d+)%\s+coverage`)
	reCoverageFileLine = regexp.MustCompile(`(?m)^(\S+\.py)\s+\d+\s+\d+\s+(\d+)%`)
)

// ParseCoverage inspects output and returns the TOTAL line percent.
func ParseCoverage(frameworkHint, text string) *CoverageReport {
	fw := strings.ToLower(frameworkHint)
	switch {
	case strings.Contains(fw, "pytest"), strings.Contains(text, "---------- coverage:"):
		if m := rePytestCovTotal.FindStringSubmatch(text); m != nil {
			pct, _ := strconv.ParseFloat(m[1], 64)
			r := &CoverageReport{Framework: "pytest", Percent: pct}
			// Find worst-covered file
			worst := 100.0
			for _, fm := range reCoverageFileLine.FindAllStringSubmatch(text, -1) {
				p, _ := strconv.ParseFloat(fm[2], 64)
				if p < worst {
					worst = p
					r.File = fm[1]
				}
			}
			return r
		}
	case strings.Contains(fw, "go"), strings.Contains(text, "coverage:"):
		if m := reGoCoverTotal.FindStringSubmatch(text); m != nil {
			pct, _ := strconv.ParseFloat(m[1], 64)
			return &CoverageReport{Framework: "go", Percent: pct}
		}
	case strings.Contains(fw, "cargo"), strings.Contains(text, "Coverage"):
		if m := reCargoCoverTotal.FindStringSubmatch(text); m != nil {
			pct, _ := strconv.ParseFloat(m[1], 64)
			return &CoverageReport{Framework: "cargo", Percent: pct}
		}
	}
	return nil
}

// LintSummary captures linter counts.
type LintSummary struct {
	Tool     string `json:"tool"`
	Issues   int    `json:"issues"`
	Errors   int    `json:"errors"`
	Warnings int    `json:"warnings"`
}

var (
	reRuffIssue    = regexp.MustCompile(`(?m)^Found\s+(\d+)\s+error`)
	reRuffPerLine  = regexp.MustCompile(`(?m):(\d+):(\d+):\s+([A-Z]\d+)\s+(.+)`)
	reESLintIssues = regexp.MustCompile(`(?m)(\d+)\s+problems?\s+\((\d+)\s+errors?,\s+(\d+)\s+warnings?\)`)
	reGolangciLint = regexp.MustCompile(`(?m)^.+?:(\d+):(\d+):\s+(error|warning)`)
)

func ParseLint(tool, text string) *LintSummary {
	s := &LintSummary{Tool: tool}
	switch strings.ToLower(tool) {
	case "ruff":
		if m := reRuffIssue.FindStringSubmatch(text); m != nil {
			s.Errors = atoi(m[1])
		}
		// count each per-line occurrence
		s.Issues = len(reRuffPerLine.FindAllString(text, -1))
		if s.Issues > 0 && s.Errors == 0 {
			s.Errors = s.Issues
		}
	case "eslint":
		if m := reESLintIssues.FindStringSubmatch(text); m != nil {
			s.Issues = atoi(m[1])
			s.Errors = atoi(m[2])
			s.Warnings = atoi(m[3])
		}
	case "golangci-lint":
		matches := reGolangciLint.FindAllStringSubmatch(text, -1)
		s.Issues = len(matches)
		for _, m := range matches {
			if m[3] == "error" {
				s.Errors++
			} else {
				s.Warnings++
			}
		}
	default:
		// Unknown tool: count any "error:" / "warning:" labels
		s.Errors = strings.Count(text, "error:")
		s.Warnings = strings.Count(text, "warning:")
		s.Issues = s.Errors + s.Warnings
	}
	return s
}

// FormatTail returns the last N lines of text.
func FormatTail(text string, n int) string {
	scanner := bufio.NewScanner(strings.NewReader(text))
	lines := make([]string, 0, n)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	if len(lines) <= n {
		return strings.Join(lines, "\n")
	}
	return strings.Join(lines[len(lines)-n:], "\n")
}

// PrintBanner returns a colored banner for a check (used in non-TTY output).
func PrintBanner(name string) string {
	pad := strings.Repeat("─", max(0, 60-len(name)-2))
	return fmt.Sprintf("── %s %s", name, pad)
}
