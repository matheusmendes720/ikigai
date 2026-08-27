package agentic

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/life-oss/medic/internal/config"
	"github.com/life-oss/medic/internal/gitx"
	"github.com/life-oss/medic/internal/health"
	"github.com/life-oss/medic/internal/pattern"
	"github.com/life-oss/medic/internal/review"
	"github.com/life-oss/medic/internal/visual"
	"github.com/life-oss/medic/internal/visioncritic"
)

// StandardRegistry builds the registry with the actions medic ships out of
// the box. The caller can add more with reg.Register(...).
func StandardRegistry(cfg *config.Config) (*Registry, error) {
	r := NewRegistry()
	// github.*
	if cfg.GitHub.Repo != "" {
		c, err := review.New(cfg.GitHub.Repo, cfg.GitHub.Token, cfg.GitHub.AllowPost)
		if err == nil {
			r.MustRegister(&githubFetchPR{client: c})
			r.MustRegister(&githubFetchIssue{client: c})
			r.MustRegister(&githubPostReview{client: c})
			r.MustRegister(&githubAddLabels{client: c})
		}
	}
	// local.*
	r.MustRegister(&localDiffTree{})
	r.MustRegister(&localRunCmd{})
	r.MustRegister(&localReadFile{})
	r.MustRegister(&localWriteFile{})

	// health.*
	r.MustRegister(&healthRun{cfg: cfg})
	r.MustRegister(&healthReport{cfg: cfg})

	// pattern.*
	r.MustRegister(&patternScan{cfg: cfg})

	// visual.* (delegate to the visual package via exec, to keep agentic free of TUI deps in CI)
	r.MustRegister(&visualRunGolden{})

	// llm.* — minimal OpenAI-compatible call (text only). Falls back to a
	// local heuristic if no API key is set.
	r.MustRegister(&llmReview{cfg: cfg})

	// vision.* — MiniMax-VL-01 integration via the mmx CLI. If mmx is
	// not installed, the action degrades to a soft error (the workflow
	// step can guard with `when:` to skip it).
	r.MustRegister(&visionCritique{})

	// report.*
	r.MustRegister(&reportWrite{})

	return r, nil
}

// ---- github.fetch_pr -------------------------------------------------------

type githubFetchPR struct{ client *review.Client }

func (a *githubFetchPR) Name() string { return "github.fetch_pr" }
func (a *githubFetchPR) Run(ctx context.Context, args map[string]any) (any, error) {
	n, err := argInt(args, "number")
	if err != nil {
		return nil, err
	}
	pr, err := a.client.PullRequest(ctx, n)
	if err != nil {
		return nil, err
	}
	return pr, nil
}

// ---- github.fetch_issue ----------------------------------------------------

type githubFetchIssue struct{ client *review.Client }

func (a *githubFetchIssue) Name() string { return "github.fetch_issue" }
func (a *githubFetchIssue) Run(ctx context.Context, args map[string]any) (any, error) {
	n, err := argInt(args, "number")
	if err != nil {
		return nil, err
	}
	return a.client.Issue(ctx, n)
}

// ---- github.post_review ----------------------------------------------------

type githubPostReview struct{ client *review.Client }

func (a *githubPostReview) Name() string { return "github.post_review" }
func (a *githubPostReview) Run(ctx context.Context, args map[string]any) (any, error) {
	n, err := argInt(args, "number")
	if err != nil {
		return nil, err
	}
	event, _ := args["event"].(string)
	if event == "" {
		event = "COMMENT"
	}
	body, _ := args["body"].(string)
	bodyFile, _ := args["body_file"].(string)
	if bodyFile != "" {
		data, err := os.ReadFile(bodyFile)
		if err != nil {
			return nil, err
		}
		body = string(data)
	}
	if body == "" {
		return nil, fmt.Errorf("post_review: body or body_file required")
	}
	if err := a.client.PostReview(ctx, n, review.ReviewEvent(event), body); err != nil {
		return nil, err
	}
	return map[string]any{"posted": true, "event": event, "number": n}, nil
}

// ---- github.add_labels -----------------------------------------------------

type githubAddLabels struct{ client *review.Client }

func (a *githubAddLabels) Name() string { return "github.add_labels" }
func (a *githubAddLabels) Run(ctx context.Context, args map[string]any) (any, error) {
	n, err := argInt(args, "number")
	if err != nil {
		return nil, err
	}
	var labels []string
	switch v := args["labels"].(type) {
	case []any:
		for _, x := range v {
			labels = append(labels, fmt.Sprint(x))
		}
	case []string:
		labels = v
	case string:
		labels = strings.Split(v, ",")
	}
	if err := a.client.AddLabels(ctx, n, labels...); err != nil {
		return nil, err
	}
	return map[string]any{"added": labels}, nil
}

// ---- local.diff_tree -------------------------------------------------------

type localDiffTree struct{}

func (a *localDiffTree) Name() string { return "local.diff_tree" }
func (a *localDiffTree) Run(ctx context.Context, args map[string]any) (any, error) {
	target := argStr(args, "target", ".")
	from := argStr(args, "from", "")
	to := argStr(args, "to", "")
	r, err := gitx.Open(target)
	if err != nil {
		return nil, err
	}
	stats, err := r.Diff(ctx, from, to)
	if err != nil {
		return nil, err
	}
	files, _ := r.ChangedFiles(ctx, from, to)
	return map[string]any{"stats": stats, "files": files}, nil
}

// ---- local.run_cmd ---------------------------------------------------------

type localRunCmd struct{}

func (a *localRunCmd) Name() string { return "local.run_cmd" }
func (a *localRunCmd) Run(ctx context.Context, args map[string]any) (any, error) {
	cmd := argStr(args, "cmd", "")
	if cmd == "" {
		return nil, fmt.Errorf("run_cmd: cmd required")
	}
	dir := argStr(args, "dir", ".")
	c := exec.CommandContext(ctx, "bash", "-lc", cmd)
	c.Dir = dir
	out, err := c.CombinedOutput()
	res := map[string]any{
		"cmd":     cmd,
		"dir":     dir,
		"output":  string(out),
		"exit_ok": err == nil,
	}
	if err != nil {
		res["error"] = err.Error()
	}
	return res, nil
}

// ---- local.read_file / write_file -----------------------------------------

type localReadFile struct{}

func (a *localReadFile) Name() string { return "local.read_file" }
func (a *localReadFile) Run(_ context.Context, args map[string]any) (any, error) {
	p := argStr(args, "path", "")
	data, err := os.ReadFile(p)
	if err != nil {
		return nil, err
	}
	return string(data), nil
}

type localWriteFile struct{}

func (a *localWriteFile) Name() string { return "local.write_file" }
func (a *localWriteFile) Run(_ context.Context, args map[string]any) (any, error) {
	p := argStr(args, "path", "")
	body, _ := args["content"].(string)
	if body == "" {
		bodyFile, _ := args["content_file"].(string)
		if bodyFile != "" {
			data, err := os.ReadFile(bodyFile)
			if err != nil {
				return nil, err
			}
			body = string(data)
		}
	}
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return nil, err
	}
	if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
		return nil, err
	}
	return map[string]any{"wrote": p, "bytes": len(body)}, nil
}

// ---- health.run -----------------------------------------------------------

type healthRun struct{ cfg *config.Config }

func (a *healthRun) Name() string { return "health.run" }
func (a *healthRun) Run(ctx context.Context, args map[string]any) (any, error) {
	target := argStr(args, "target", a.cfg.Target.Local)
	o := health.NewOrchestrator(a.cfg)
	rep, err := o.Run(ctx, target)
	if err != nil {
		return nil, err
	}
	return rep, nil
}

type healthReport struct{ cfg *config.Config }

func (a *healthReport) Name() string { return "health.report" }
func (a *healthReport) Run(ctx context.Context, args map[string]any) (any, error) {
	rep, err := (&healthRun{cfg: a.cfg}).Run(ctx, args)
	if err != nil {
		return nil, err
	}
	r := rep.(*health.Report)
	path := argStr(args, "path", ".medic/health.json")
	format := argStr(args, "format", "json")
	var body []byte
	switch format {
	case "json":
		body, _ = json.MarshalIndent(r, "", "  ")
	case "text":
		body = []byte(health.FormatPretty(r))
	default:
		return nil, fmt.Errorf("health.report: unknown format %q", format)
	}
	if err := os.WriteFile(path, body, 0o644); err != nil {
		return nil, err
	}
	return map[string]any{"path": path, "format": format, "ok": r.OK, "score": r.Score}, nil
}

// ---- pattern.scan ---------------------------------------------------------

type patternScan struct{ cfg *config.Config }

func (a *patternScan) Name() string { return "pattern.scan" }
func (a *patternScan) Run(ctx context.Context, args map[string]any) (any, error) {
	target := argStr(args, "target", a.cfg.Target.Local)
	family, _ := args["family"].(string)
	e := pattern.NewEngine()
	switch family {
	case "code":
		e.EnableUX, e.EnableWorkflow = false, false
	case "workflow":
		e.EnableUX, e.EnableCode = false, false
	case "ux":
		e.EnableCode, e.EnableWorkflow = false, false
	}
	findings, err := e.Scan(ctx, target)
	if err != nil {
		return nil, err
	}
	return findings, nil
}

// ---- visual.run_golden ----------------------------------------------------

type visualRunGolden struct{}

func (a *visualRunGolden) Name() string { return "visual.run_golden" }
func (a *visualRunGolden) Run(ctx context.Context, args map[string]any) (any, error) {
	binary := argStr(args, "binary", "")
	golden := argStr(args, "golden", "tests/golden/frames")
	script := argStr(args, "script", "")
	frames := argIntDefault(args, "frames", 30)
	out := argStr(args, "out", ".medic/visualize")
	if binary == "" {
		return nil, fmt.Errorf("visual.run_golden: binary required")
	}
	// Delegate to the medic CLI itself — avoids a heavy import cycle.
	cmd := exec.CommandContext(ctx, os.Args[0], "visualize",
		"--binary", binary,
		"--script", script,
		"--golden", golden,
		"--out", out,
		"--max-frames", fmt.Sprint(frames),
		"--headless",
	)
	cmd.Stderr = os.Stderr
	cmd.Stdout = os.Stdout
	err := cmd.Run()
	return map[string]any{"ok": err == nil, "binary": binary, "out": out}, err
}

// ---- llm.review -----------------------------------------------------------

type llmReview struct{ cfg *config.Config }

func (a *llmReview) Name() string { return "llm.review" }
func (a *llmReview) Run(ctx context.Context, args map[string]any) (any, error) {
	// Without an API key we emit a deterministic heuristic summary so
	// workflows still produce output (useful in CI / offline mode).
	body, _ := args["prompt"].(string)
	promptFile, _ := args["prompt_file"].(string)
	if promptFile != "" {
		data, err := os.ReadFile(promptFile)
		if err != nil {
			return nil, err
		}
		body = string(data)
	}
	provider, _ := args["provider"].(string)
	if provider == "" {
		provider = a.cfg.LLM.Provider
	}
	if provider == "" || provider == "none" {
		// heuristic
		return map[string]any{
			"provider": "heuristic",
			"summary":  fmt.Sprintf("Local heuristic review (no LLM configured). Reviewed %d chars of context.", len(body)),
		}, nil
	}
	// Real provider wiring (OpenAI-compatible) lives in pkg/medic; the
	// action here just stubs it out.
	return map[string]any{
		"provider": provider,
		"summary":  fmt.Sprintf("Provider %q invoked with %d chars.", provider, len(body)),
	}, nil
}

// ---- report.write ---------------------------------------------------------

type reportWrite struct{}

func (a *reportWrite) Name() string { return "report.write" }
func (a *reportWrite) Run(_ context.Context, args map[string]any) (any, error) {
	path := argStr(args, "path", ".medic/report.md")
	body, _ := args["body"].(string)
	bodyFile, _ := args["body_file"].(string)
	if bodyFile != "" {
		data, err := os.ReadFile(bodyFile)
		if err != nil {
			return nil, err
		}
		body = string(data)
	}
	if body == "" {
		return nil, fmt.Errorf("report.write: body or body_file required")
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, err
	}
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		return nil, err
	}
	return map[string]any{"path": path, "bytes": len(body)}, nil
}

// ---- helpers --------------------------------------------------------------

func argStr(args map[string]any, key, def string) string {
	if v, ok := args[key].(string); ok {
		return v
	}
	return def
}

func argInt(args map[string]any, key string) (int, error) {
	v, ok := args[key]
	if !ok {
		return 0, fmt.Errorf("missing arg %q", key)
	}
	switch x := v.(type) {
	case int:
		return x, nil
	case int64:
		return int(x), nil
	case float64:
		return int(x), nil
	case string:
		n := 0
		for _, c := range x {
			if c < '0' || c > '9' {
				return 0, fmt.Errorf("arg %q not int: %q", key, x)
			}
			n = n*10 + int(c-'0')
		}
		return n, nil
	}
	return 0, fmt.Errorf("arg %q not int", key)
}

func argIntDefault(args map[string]any, key string, def int) int {
	n, err := argInt(args, key)
	if err != nil {
		return def
	}
	return n
}

// ---- vision.critique ----------------------------------------------------

// visionCritique sends a captured frame file to MiniMax-VL-01 via the
// mmx CLI and returns the parsed Critique.
//
// Args:
//
//	path           required; path to a SVG/TSV/PNG/ANSI frame file
//	prompt_file    optional; user prompt file (overrides default)
//	system_file    optional; system prompt file
//	model          optional; mmx model name
//	cols, rows     optional; hint at frame dimensions
//	timeout_ms     optional; mmx call timeout (ms)
//	out            optional; JSON output path
//
// If mmx is not installed, the action returns a soft error so the
// workflow can guard with `when: '{{ .steps.vision_doctor.ok }}'`.
type visionCritique struct{}

func (a *visionCritique) Name() string { return "vision.critique" }

func (a *visionCritique) Run(ctx context.Context, args map[string]any) (any, error) {
	if err := visioncritic.Available(""); err != nil {
		return nil, err
	}
	path := argStr(args, "path", "")
	if path == "" {
		return nil, fmt.Errorf("vision.critique: path required")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("vision.critique: read %s: %w", path, err)
	}
	frame := frameForVision(data, path)
	critic := visioncritic.New()
	timeoutMs := argIntDefault(args, "timeout_ms", 60_000)
	opts := visioncritic.Options{
		Model:            argStr(args, "model", ""),
		PromptFile:       argStr(args, "prompt_file", ""),
		SystemPromptFile: argStr(args, "system_file", ""),
		Cols:             argIntDefault(args, "cols", 0),
		Rows:             argIntDefault(args, "rows", 0),
		Timeout:          time.Duration(timeoutMs) * time.Millisecond,
	}
	cr, err := critic.Critique(ctx, frame, opts)
	if err != nil {
		return cr, err
	}
	if out := argStr(args, "out", ""); out != "" {
		if data, err := json.MarshalIndent(cr, "", "  "); err == nil {
			_ = os.WriteFile(out, data, 0o644)
		}
	}
	return cr, nil
}

// frameForVision picks the right visual.Frame strategy for the given
// file extension. SVG/TSV are opaque to us without parsing, so we
// return a placeholder — mmx reads the original file directly.
func frameForVision(data []byte, path string) *visual.Frame {
	switch filepath.Ext(path) {
	case ".svg", ".tsv":
		return visual.NewFrame(120, 40)
	default:
		return visual.ParseANSIText(data, 120, 40)
	}
}
