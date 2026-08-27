package agentic

import "testing"

func TestEvalGuard_True(t *testing.T) {
	// In real usage the engine stores each step's full result under its id;
	// when: '{{ .steps.health.ok }}' therefore reads `health.ok`.
	outputs := map[string]any{
		"health": map[string]any{
			"ok":     true,
			"output": map[string]any{"score": 90},
		},
		"diff": map[string]any{
			"ok":     false,
			"output": map[string]any{"score": 10},
		},
	}
	cases := []struct {
		expr string
		want bool
	}{
		{"", true},
		{"{{ .steps.health.ok }}", true},
		{"{{ .steps.health.output.score }} eq 90", true},
		{"{{ .steps.health.ok }} and {{ .steps.diff.ok }}", false},
		{"{{ .steps.health.ok }} or {{ .steps.diff.ok }}", true},
		{"not {{ .steps.health.ok }}", false},
		{"not {{ .steps.diff.ok }}", true},
		{"{{ .steps.nonexistent.ok }}", false},
		{"{{ .steps.health.output.score }} eq 50", false},
		{"{{ .steps.health.output.score }} ne 50", true},
	}
	for _, c := range cases {
		got := EvalGuard(c.expr, outputs)
		if got != c.want {
			t.Errorf("EvalGuard(%q) = %v, want %v", c.expr, got, c.want)
		}
	}
}
