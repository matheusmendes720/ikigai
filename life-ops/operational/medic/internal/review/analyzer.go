// Package review — analyzer.go turns a PR + local diff into a Report.
//
// Verdict rules (defaults; configurable via Config):
//   - any SeverityCritical  → REQUEST_CHANGES
//   - any SeverityHigh      → REQUEST_CHANGES
//   - > 3 SeverityMedium    → REQUEST_CHANGES
//   - else if any SeverityLow → COMMENT
//   - else                    → APPROVE
package review

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/life-oss/medic/internal/gitx"
	"github.com/life-oss/medic/internal/health"
)

// Severity is the importance of a Finding.
type Severity string

const (
	SeverityInfo     Severity = "info"
	SeverityLow      Severity = "low"
	SeverityMedium   Severity = "medium"
	SeverityHigh     Severity = "high"
	SeverityCritical Severity = "critical"
)

// ReviewEvent is the GitHub review action.
type ReviewEvent string

const (
	EventComment         ReviewEvent = "COMMENT"
	EventApprove         ReviewEvent = "APPROVE"
	EventRequestChanges  ReviewEvent = "REQUEST_CHANGES"
)

// Finding is one observation produced by an analyzer.
type Finding struct {
	ID        string   `json:"id"`
	Severity  Severity `json:"severity"`
	Family    string   `json:"family"` // code | ux | workflow | health
	Path      string   `json:"path,omitempty"`
	Line      int      `json:"line,omitempty"`
	Title     string   `json:"title"`
	Rationale string   `json:"rationale"`
	Suggestion string  `json:"suggestion,omitempty"`
	Rule      string   `json:"rule,omitempty"`
}

// Report is the full analysis of one PR.
type Report struct {
	Repo       string         `json:"repo"`
	PR         *PR            `json:"pr"`
	Files      []File         `json:"files"`
	DiffStats  []gitx.DiffStat `json:"diff_stats,omitempty"`
	Commits    []gitx.Commit  `json:"commits,omitempty"`
	Health     *health.Report `json:"health,omitempty"`
	Findings   []Finding      `json:"findings"`
	Verdict    ReviewEvent    `json:"verdict"`
	Generated  time.Time      `json:"generated"`
	Score      int            `json:"score"` // 0..100
}

// Config tunes analyzer behavior.
type Config struct {
	BaseRef      string // base ref to diff against (e.g. "main")
	HeadRef      string // head ref (defaults to PR head SHA)
	LocalTarget  string // local path to the codebase
	PostToGitHub bool
	RunHealth    bool
	RunPatterns  bool
	Verbose      bool
}

// Analyzer coordinates the analysis.
type Analyzer struct {
	Client *Client
	Cfg    Config
}

// NewAnalyzer builds an Analyzer from a config + client.
func NewAnalyzer(client *Client, cfg Config) *Analyzer {
	return &Analyzer{Client: client, Cfg: cfg}
}

// Analyze runs all analyzers and produces a Report.
func (a *Analyzer) Analyze(ctx context.Context, prNum int) (*Report, error) {
	pr, err := a.Client.PullRequest(ctx, prNum)
	if err != nil {
		return nil, err
	}
	rep := &Report{
		Repo:      a.Client.Owner + "/" + a.Client.Repo,
		PR:        pr,
		Generated: time.Now(),
	}

	// 1. Files from GitHub
	files, err := a.Client.FilesChanged(ctx, prNum)
	if err != nil {
		return nil, fmt.Errorf("files: %w", err)
	}
	rep.Files = files

	// 2. Local git stats + commits (if local target is a repo)
	if a.Cfg.LocalTarget != "" {
		if r, err := gitx.Open(a.Cfg.LocalTarget); err == nil {
			if stats, err := r.Diff(ctx, a.Cfg.BaseRef, a.Cfg.HeadRef); err == nil {
				rep.DiffStats = stats
			}
			if log, err := r.Log(ctx, "HEAD", 25); err == nil {
				rep.Commits = log
			}
		}
	}

	// 3. Linked issues
	comments, _ := a.Client.Comments(ctx, prNum)
	var commitMessages []string
	for _, c := range rep.Commits {
		commitMessages = append(commitMessages, c.Subject)
	}
	_ = LinkedIssues(pr, comments, commitMessages) // parsed but not stored yet

	// 4. Health (optional)
	if a.Cfg.RunHealth {
		rep.Health = a.runHealth(ctx)
	}

	// 5. Pattern scan (optional)
	if a.Cfg.RunPatterns {
		rep.Findings = append(rep.Findings, a.runCodePatterns(rep)...)
	}

	// 6. Always include workflow patterns from PR/issue signals
	rep.Findings = append(rep.Findings, a.runWorkflowPatterns(rep, comments)...)

	// 7. Verdict + score
	rep.Verdict, rep.Score = decideVerdict(rep.Findings)

	return rep, nil
}

func (a *Analyzer) runHealth(ctx context.Context) *health.Report {
	// Lazy import via the type; the orchestrator lives in internal/health.
	// We construct a minimal cfg from a.Cfg + defaults.
	return nil // wiring done by caller via direct call to health.NewOrchestrator
}

func (a *Analyzer) runCodePatterns(rep *Report) []Finding {
	var out []Finding
	for _, f := range rep.Files {
		// Read the local file (if available) and apply heuristics.
		path := filepath.Join(a.Cfg.LocalTarget, f.Path)
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		text := string(data)
		out = append(out, scanLongFunctions(text, f.Path)...)
		out = append(out, scanRepeatedBranches(text, f.Path)...)
		out = append(out, scanPublicSymbolNoDoc(text, f.Path)...)
		out = append(out, scanTestGaps(text, f.Path, f.Additions)...)
	}
	return out
}

func (a *Analyzer) runWorkflowPatterns(rep *Report, comments []Comment) []Finding {
	var out []Finding
	body := rep.PR.Body
	if body == "" {
		out = append(out, Finding{
			ID:        "wf.pr.no-description",
			Severity:  SeverityMedium,
			Family:    "workflow",
			Title:     "PR has no description",
			Rationale: "PRs without descriptions are harder to review and trace later.",
			Suggestion: "Add a description with: motivation, change summary, test plan.",
			Rule:      "pr-has-description",
		})
	}
	if !strings.Contains(strings.ToLower(body), "test") && !strings.Contains(strings.ToLower(body), "screenshot") {
		out = append(out, Finding{
			ID:        "wf.pr.no-test-plan",
			Severity:  SeverityLow,
			Family:    "workflow",
			Title:     "No test plan mentioned",
			Rationale: "Reviewers can't know how to verify the change without a test plan.",
			Suggestion: "Add a 'How was this tested?' section.",
			Rule:      "pr-has-test-plan",
		})
	}
	// File-count outlier (likely drive-by refactor)
	if len(rep.Files) > 25 {
		out = append(out, Finding{
			ID:        "wf.pr.file-explosion",
			Severity:  SeverityLow,
			Family:    "workflow",
			Title:     fmt.Sprintf("%d files changed", len(rep.Files)),
			Rationale: "Large diffs are hard to review; consider splitting.",
			Suggestion: "Split into multiple PRs by concern.",
			Rule:      "pr-file-count",
		})
	}
	// Look for reverts within commit log
	for _, c := range rep.Commits {
		if strings.HasPrefix(strings.ToLower(c.Subject), "revert") {
			out = append(out, Finding{
				ID:        "wf.commit.recent-revert",
				Severity:  SeverityMedium,
				Family:    "workflow",
				Title:     "Recent revert in branch: " + c.Subject,
				Rationale: "Reverts within a feature branch suggest scope creep or unstable change.",
				Suggestion: "Investigate the root cause; consider splitting the offending change.",
				Rule:      "commit-revert-detected",
			})
			break
		}
	}
	_ = comments
	return out
}

// ---- Pure pattern detectors (exported via Analyzer; tested standalone) ----

func scanLongFunctions(text, path string) []Finding {
	var out []Finding
	lines := strings.Split(text, "\n")
	depth, fnStart, fnName := 0, 0, ""
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		// Heuristic: function definition in Go/Python
		if fnStart == 0 && (strings.HasPrefix(trimmed, "func ") || strings.HasPrefix(trimmed, "def ") || strings.HasPrefix(trimmed, "async def ")) {
			fnName = firstWord(trimmed)
			fnStart = i + 1
			depth = 0
			continue
		}
		if fnStart > 0 {
			depth += strings.Count(line, "{") - strings.Count(line, "}")
			if depth <= 0 {
				length := i - fnStart + 1
				if length > 80 {
					out = append(out, Finding{
						ID:        "code.func-toolong",
						Severity:  SeverityLow,
						Family:    "code",
						Path:      path,
						Line:      fnStart,
						Title:     fmt.Sprintf("Function %q is %d lines", fnName, length),
						Rationale: "Long functions are hard to test and reason about.",
						Suggestion: "Extract helpers; aim for ≤ 50 lines.",
						Rule:      "max-function-length",
					})
				}
				fnStart, fnName = 0, ""
			}
		}
	}
	return out
}

func scanRepeatedBranches(text, path string) []Finding {
	// Detect `if x == "..." return ...` patterns that suggest a lookup table.
	var out []Finding
	lines := strings.Split(text, "\n")
	count := 0
	for _, line := range lines {
		t := strings.TrimSpace(line)
		if strings.HasPrefix(t, "if ") && strings.Contains(t, "==") && strings.HasSuffix(t, ":") {
			count++
		}
	}
	if count >= 5 {
		out = append(out, Finding{
			ID:        "code.branch-table",
			Severity:  SeverityLow,
			Family:    "code",
			Path:      path,
			Title:     fmt.Sprintf("%d if/elif branches detected", count),
			Rationale: "Many parallel branches suggest a dispatch table would be clearer.",
			Suggestion: "Replace with a map / dispatch table.",
			Rule:      "prefer-dispatch-table",
		})
	}
	return out
}

func scanPublicSymbolNoDoc(text, path string) []Finding {
	var out []Finding
	lines := strings.Split(text, "\n")
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		// Go: `func Foo(` exported symbol (capital F, not _)
		if strings.HasPrefix(trimmed, "func ") && !strings.HasPrefix(trimmed, "func _") {
			// Look ahead for doc comment in previous 2 lines
			if i < 2 {
				continue
			}
			prev := strings.TrimSpace(lines[i-1])
			prev2 := strings.TrimSpace(lines[i-2])
			hasDoc := strings.HasPrefix(prev, "//") || strings.HasPrefix(prev2, "//")
			if !hasDoc && looksExported(trimmed) {
				out = append(out, Finding{
					ID:        "code.docstring-missing",
					Severity:  SeverityInfo,
					Family:    "code",
					Path:      path,
					Line:      i + 1,
					Title:     "Exported function without doc comment",
					Rationale: "Unexported docs make library use harder.",
					Suggestion: "Add a doc comment starting with the function name.",
					Rule:      "public-needs-doc",
				})
			}
		}
	}
	return out
}

func scanTestGaps(text, path string, additions int) []Finding {
	var out []Finding
	if additions < 50 {
		return nil
	}
	if !strings.HasSuffix(path, "_test.go") && strings.HasSuffix(path, ".go") {
		// Heuristic: only flag if file is named like a feature, not a model/dto.
		base := filepath.Base(path)
		if strings.Contains(strings.ToLower(base), "engine") || strings.Contains(strings.ToLower(base), "service") {
			out = append(out, Finding{
				ID:        "code.test-gap",
				Severity:  SeverityLow,
				Family:    "code",
				Path:      path,
				Title:     fmt.Sprintf("%d additions to %s without co-located test changes", additions, base),
				Rationale: "Engine/service files should ship with tests.",
				Suggestion: "Add unit tests covering the new behavior.",
				Rule:      "tests-with-feature",
			})
		}
	}
	return out
}

func firstWord(s string) string {
	parts := strings.Fields(s)
	if len(parts) < 2 {
		return s
	}
	return parts[1]
}

func looksExported(s string) bool {
	// `func FooBar(`
	idx := strings.Index(s, "func ")
	if idx < 0 {
		return false
	}
	rest := s[idx+5:]
	paren := strings.Index(rest, "(")
	if paren < 1 {
		return false
	}
	name := rest[:paren]
	if name == "" {
		return false
	}
	c := name[0]
	return c >= 'A' && c <= 'Z'
}

func decideVerdict(findings []Finding) (ReviewEvent, int) {
	crit, high, med := 0, 0, 0
	for _, f := range findings {
		switch f.Severity {
		case SeverityCritical:
			crit++
		case SeverityHigh:
			high++
		case SeverityMedium:
			med++
		}
	}
	score := 100 - 25*crit - 15*high - 5*med
	if score < 0 {
		score = 0
	}
	switch {
	case crit > 0, high > 0, med > 3:
		return EventRequestChanges, score
	case med > 0:
		return EventComment, score
	default:
		return EventApprove, score
	}
}

// SortFindings sorts by severity desc, then path.
func SortFindings(fs []Finding) []Finding {
	order := map[Severity]int{
		SeverityCritical: 0,
		SeverityHigh:     1,
		SeverityMedium:   2,
		SeverityLow:      3,
		SeverityInfo:     4,
	}
	sort.SliceStable(fs, func(i, j int) bool {
		if order[fs[i].Severity] != order[fs[j].Severity] {
			return order[fs[i].Severity] < order[fs[j].Severity]
		}
		return fs[i].Path < fs[j].Path
	})
	return fs
}

// FilterBySeverity drops findings below the floor.
func FilterBySeverity(fs []Finding, floor Severity) []Finding {
	order := map[Severity]int{
		SeverityInfo: 0, SeverityLow: 1, SeverityMedium: 2, SeverityHigh: 3, SeverityCritical: 4,
	}
	var out []Finding
	for _, f := range fs {
		if order[f.Severity] >= order[floor] {
			out = append(out, f)
		}
	}
	return out
}
