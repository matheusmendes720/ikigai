package visioncritic

import (
	"os"
	"strings"
	"testing"
)

func TestParseCritique_Empty(t *testing.T) {
	sum, fs := ParseCritique("")
	if sum != "" {
		t.Errorf("empty summary: %q", sum)
	}
	if len(fs) != 0 {
		t.Errorf("empty findings: %d", len(fs))
	}
}

func TestParseCritique_WellFormed(t *testing.T) {
	raw := `## Summary
The dashboard has a clear hierarchy but the contrast on secondary text is too low.

## Findings
- **[high]** Low contrast on secondary text — body text against background is below WCAG AA
  - Suggestion: Bump body fg from #999 to #ccc
  - Region: middle panel
- **[medium]** Ragged right edge in the timeline — columns don't align to the right border
  - Suggestion: Set fixed width on each column
- **[info]** Title bar could use a status indicator
- none
`
	sum, fs := ParseCritique(raw)
	if !strings.Contains(sum, "clear hierarchy") {
		t.Errorf("summary: %q", sum)
	}
	if len(fs) != 3 {
		t.Fatalf("findings: %d, want 3", len(fs))
	}
	if fs[0].Severity != SevHigh {
		t.Errorf("f0 severity: %s, want high", fs[0].Severity)
	}
	if !strings.Contains(fs[0].Title, "Low contrast") {
		t.Errorf("f0 title: %q", fs[0].Title)
	}
	if fs[0].Suggestion != "Bump body fg from #999 to #ccc" {
		t.Errorf("f0 suggestion: %q", fs[0].Suggestion)
	}
	if fs[0].Region != "middle panel" {
		t.Errorf("f0 region: %q", fs[0].Region)
	}
	if fs[1].Severity != SevMedium {
		t.Errorf("f1 severity: %s", fs[1].Severity)
	}
	if fs[1].Region != "" {
		t.Errorf("f1 region should be empty: %q", fs[1].Region)
	}
	if fs[2].Severity != SevInfo {
		t.Errorf("f2 severity: %s", fs[2].Severity)
	}
	// "none" must not produce a finding
	for _, f := range fs {
		if f.Title == "none" {
			t.Errorf("'none' leaked into findings: %+v", f)
		}
	}
}

func TestParseCritique_NoSeverityDefaultsToInfo(t *testing.T) {
	raw := `## Findings
- Plain bullet without severity
`
	_, fs := ParseCritique(raw)
	if len(fs) != 1 {
		t.Fatalf("findings: %d", len(fs))
	}
	if fs[0].Severity != SevInfo {
		t.Errorf("severity: %s, want info", fs[0].Severity)
	}
}

func TestParseCritique_CriticalSeverity(t *testing.T) {
	raw := `## Findings
- **[critical]** Layout is broken
`
	_, fs := ParseCritique(raw)
	if len(fs) != 1 || fs[0].Severity != SevCritical {
		t.Errorf("critical: %+v", fs)
	}
}

func TestParseCritique_Score(t *testing.T) {
	cases := []struct {
		name    string
		sevs    []Severity
		wantMin int
		wantMax int
	}{
		{"empty", nil, 100, 100},
		{"one info", []Severity{SevInfo}, 99, 99},
		{"one low", []Severity{SevLow}, 97, 97},
		{"one med", []Severity{SevMedium}, 90, 90},
		{"one high", []Severity{SevHigh}, 75, 75},
		{"one crit", []Severity{SevCritical}, 60, 60},
		{"mixed", []Severity{SevHigh, SevMedium, SevLow}, 62, 62},
		{"floor", []Severity{SevCritical, SevCritical, SevCritical}, 0, 0},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			cr := &Critique{}
			for _, s := range c.sevs {
				cr.Findings = append(cr.Findings, Finding{Severity: s, Title: "x"})
			}
			got := cr.Score()
			if got < c.wantMin || got > c.wantMax {
				t.Errorf("score = %d, want in [%d,%d]", got, c.wantMin, c.wantMax)
			}
		})
	}
}

func TestParseCritique_Verdict(t *testing.T) {
	cases := []struct {
		score int
		want  string
	}{
		{100, "APPROVE"},
		{80, "APPROVE"},
		{79, "COMMENT"},
		{50, "COMMENT"},
		{49, "REQUEST_CHANGES"},
		{0, "REQUEST_CHANGES"},
	}
	for _, c := range cases {
		cr := &Critique{}
		for i := 0; i < 100-c.score; i++ {
			cr.Findings = append(cr.Findings, Finding{Severity: SevInfo, Title: "x"})
		}
		if got := cr.Verdict(); got != c.want {
			t.Errorf("score %d → verdict %s, want %s", c.score, got, c.want)
		}
	}
}

func TestParseCritique_CountBySeverity(t *testing.T) {
	cr := &Critique{
		Findings: []Finding{
			{Severity: SevHigh, Title: "a"},
			{Severity: SevHigh, Title: "b"},
			{Severity: SevLow, Title: "c"},
		},
	}
	cnt := cr.CountBySeverity()
	if cnt["high"] != 2 || cnt["low"] != 1 {
		t.Errorf("counts: %+v", cnt)
	}
}

func TestAvailable_NotInstalled(t *testing.T) {
	// Save and clear PATH so mmx cannot be found.
	orig := os.Getenv("PATH")
	t.Setenv("PATH", "")
	_ = orig
	if err := Available("mmx"); err == nil {
		t.Errorf("Available() with no mmx on PATH = nil, want error")
	}
}

func TestCritique_String(t *testing.T) {
	cr := &Critique{
		Image:   "/tmp/frame.svg",
		Model:   "MiniMax-VL-01",
		Summary: "Looks clean",
		Findings: []Finding{
			{Severity: SevMedium, Title: "Tab order unclear", Detail: "Tab cycles unexpectedly", Suggestion: "Set explicit focus chain"},
		},
		DurationMs: 4200,
	}
	out := cr.String()
	if !strings.Contains(out, "score=90/100") {
		t.Errorf("expected score=90 in: %s", out)
	}
	if !strings.Contains(out, "APPROVE") {
		t.Errorf("expected APPROVE verdict in: %s", out)
	}
	if !strings.Contains(out, "Tab order") {
		t.Errorf("expected finding title in: %s", out)
	}
	if !strings.Contains(out, "Set explicit focus chain") {
		t.Errorf("expected suggestion in: %s", out)
	}
}

func TestToReview(t *testing.T) {
	f := Finding{
		ID:         "v-1",
		Severity:   SevHigh,
		Title:      "X",
		Detail:     "Y",
		Suggestion: "Z",
		Region:     "top-left",
	}
	r := f.ToReview()
	if r.ID != "v-1" || r.Severity != "high" || r.Region != "top-left" {
		t.Errorf("ToReview: %+v", r)
	}
}

func TestSlug(t *testing.T) {
	cases := map[string]string{
		"Hello World":       "hello-world",
		"  ragged  -- edge ": "ragged-edge",
		"MixedCASE123":       "mixedcase123",
		"":                   "",
	}
	for in, want := range cases {
		if got := slug(in); got != want {
			t.Errorf("slug(%q) = %q, want %q", in, got, want)
		}
	}
}

// TestBuildFindingIDIncrements ensures each call yields a unique ID.
func TestBuildFindingIDIncrements(t *testing.T) {
	idCounter = 0
	f1 := &Finding{Title: "alpha"}
	f2 := &Finding{Title: "beta"}
	a := buildFindingID(f1)
	b := buildFindingID(f2)
	if a == b {
		t.Errorf("IDs collided: %s vs %s", a, b)
	}
	if !strings.HasPrefix(a, "vision-1-") {
		t.Errorf("first ID prefix: %s", a)
	}
	if !strings.HasPrefix(b, "vision-2-") {
		t.Errorf("second ID prefix: %s", b)
	}
}

// env helpers removed — use os.Setenv / t.Setenv directly.
