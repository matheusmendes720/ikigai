// Package visioncritic shells out to MiniMax's MMX-CLI (mmx) to send a
// captured TUI frame to MiniMax-VL-01 — the ViT-MLP-LLM vision-language
// model — and parses the textual critique back into structured findings.
//
// The flow:
//
//	1. The visual package renders the frame as SVG (and/or PNG).
//	2. visioncritic writes the SVG to a temp file and invokes `mmx` with
//	   a prompt drawn from configs/medic/promts/visual-critic.txt.
//	3. mmx returns a markdown response which visioncritic parses into
//	   []Finding items (one per bullet).
//
// If `mmx` is not installed, every call returns ErrNotInstalled so the
// rest of medic keeps working (the workflow step degrades to a warning
// rather than a hard failure).
package visioncritic

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/life-oss/medic/internal/visual"
)

// ErrNotInstalled is returned when the `mmx` binary is not on PATH.
var ErrNotInstalled = errors.New("mmx not installed (run scripts/install_mmx.sh)")

// ErrNoAPIKey is returned when MINIMAX_API_KEY is unset.
var ErrNoAPIKey = errors.New("MINIMAX_API_KEY not set")

// Severity mirrors review.Severity but is redeclared here to avoid an
// import cycle (review → pattern would be cleaner; for now we duplicate
// the tiny type).
type Severity string

const (
	SevInfo     Severity = "info"
	SevLow      Severity = "low"
	SevMedium   Severity = "medium"
	SevHigh     Severity = "high"
	SevCritical Severity = "critical"
)

// Finding is one critique point returned by the vision model.
type Finding struct {
	ID         string   `json:"id"`
	Severity   Severity `json:"severity"`
	Title      string   `json:"title"`
	Detail     string   `json:"detail,omitempty"`
	Suggestion string   `json:"suggestion,omitempty"`
	Region     string   `json:"region,omitempty"` // e.g. "top-left", "row 5..9, col 0..40"
}

// Critique is the structured output of one mmx invocation.
type Critique struct {
	Image      string    `json:"image"`
	Model      string    `json:"model"`
	Raw        string    `json:"raw"`
	Summary    string    `json:"summary,omitempty"`
	Findings   []Finding `json:"findings"`
	DurationMs int64     `json:"duration_ms"`
	Err        string    `json:"error,omitempty"`
}

// Options tunes a Critique call.
type Options struct {
	// Model is the mmx model name. Empty → mmx default.
	Model string
	// Prompt is the user-prompt sent to mmx. If empty, DefaultPrompt is used.
	Prompt string
	// PromptFile points to a file with the prompt; overrides Prompt.
	PromptFile string
	// SystemPromptFile points to a system-prompt file passed via --system.
	SystemPromptFile string
	// ImageFormat is "svg" (default), "png", or "txt".
	ImageFormat string
	// Cols/Rows hint at the original frame dimensions (used in the prompt).
	Cols, Rows int
	// Timeout caps the mmx invocation. 0 → 60s.
	Timeout time.Duration
}

// Critic is the high-level façade.
type Critic struct {
	Binary string // mmx binary name; defaults to "mmx"
}

// New returns a Critic that will shell out to `mmx`.
func New() *Critic { return &Critic{Binary: "mmx"} }

// DefaultPrompt is what medic sends to mmx by default. Edit it freely;
// the response should be markdown bullets that parse cleanly into findings.
const DefaultPrompt = `You are a senior UX critic reviewing a screenshot of a terminal user interface (TUI).

Look at the image and report concrete, fixable issues. Focus on:

  1. Layout: ragged right edges, panels that touch, header/body alignment
  2. Typography: mixed box-drawing glyphs, wrong weight, missing emphasis
  3. Color: low contrast, focus indicators missing or invisible
  4. Information density: empty space, duplicated text, broken truncation
  5. Affordances: missing scroll indicators, no status bar, no clear focus

Return your response as markdown. Use this exact format:

## Summary
<one paragraph>

## Findings
- **[severity]** <title> — <one-line detail>
  - Suggestion: <one-line fix>
  - Region: <where in the image>

Severity is one of: info, low, medium, high, critical.
If there are no issues, write "## Findings\n- none".

Be terse, concrete, and actionable. Do not restate the obvious.`

// Critique sends a frame to mmx and parses the response.
func (c *Critic) Critique(ctx context.Context, frame *visual.Frame, opts Options) (*Critique, error) {
	if opts.Timeout == 0 {
		opts.Timeout = 60 * time.Second
	}
	if opts.Prompt == "" && opts.PromptFile == "" {
		opts.Prompt = DefaultPrompt
	}
	if opts.PromptFile != "" {
		data, err := os.ReadFile(opts.PromptFile)
		if err != nil {
			return nil, fmt.Errorf("read prompt file: %w", err)
		}
		opts.Prompt = string(data)
	}
	// 1. Render the frame to an image file the vision model can ingest.
	imgPath, cleanup, err := c.writeImage(frame, opts)
	if err != nil {
		return nil, err
	}
	defer cleanup()

	// 2. Build the mmx command.
	args := []string{"describe", "--prompt", opts.Prompt, imgPath}
	if opts.Model != "" {
		args = append(args, "--model", opts.Model)
	}
	if opts.SystemPromptFile != "" {
		args = append(args, "--system", "@"+opts.SystemPromptFile)
	}
	if opts.Cols > 0 && opts.Rows > 0 {
		args = append(args, "--hint", fmt.Sprintf("cols=%d,rows=%d", opts.Cols, opts.Rows))
	}

	bin, err := exec.LookPath(c.Binary)
	if err != nil {
		return nil, fmt.Errorf("%w: %s", ErrNotInstalled, c.Binary)
	}
	cctx, cancel := context.WithTimeout(ctx, opts.Timeout)
	defer cancel()
	cmd := exec.CommandContext(cctx, bin, args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	start := time.Now()
	err = cmd.Run()
	dur := time.Since(start)

	out := &Critique{
		Image:      imgPath,
		Raw:        stdout.String(),
		DurationMs: dur.Milliseconds(),
	}
	if exitErr, ok := err.(*exec.ExitError); ok {
		out.Err = strings.TrimSpace(stderr.String())
		if out.Err == "" {
			out.Err = exitErr.Error()
		}
	} else if err != nil {
		out.Err = err.Error()
		return out, err
	}

	out.Summary, out.Findings = ParseCritique(out.Raw)
	return out, nil
}

// writeImage serialises frame to the requested format. SVG is the most
// faithful (true colors, real fonts, vector); PNG keeps mmx's
// documentation happier if you have it pre-installed.
func (c *Critic) writeImage(frame *visual.Frame, opts Options) (string, func(), error) {
	dir, err := os.MkdirTemp("", "medic-vision-")
	if err != nil {
		return "", nil, fmt.Errorf("mktemp: %w", err)
	}
	cleanup := func() { _ = os.RemoveAll(dir) }
	format := opts.ImageFormat
	if format == "" {
		format = "svg"
	}
	var data []byte
	var fname string
	switch format {
	case "svg":
		data = visual.RenderSVG(frame)
		fname = "frame.svg"
	case "png":
		// No PNG encoder in the stdlib; we render SVG and ask the caller
		// (or mmx) to convert. Until then, fall back to SVG bytes saved
		// with a .png suffix is misleading — so emit SVG instead.
		data = visual.RenderSVG(frame)
		fname = "frame.svg"
	case "txt", "tsv":
		data = visual.RenderTSV(frame)
		fname = "frame.tsv"
	default:
		cleanup()
		return "", nil, fmt.Errorf("unsupported image format %q", format)
	}
	path := filepath.Join(dir, fname)
	if err := os.WriteFile(path, data, 0o644); err != nil {
		cleanup()
		return "", nil, fmt.Errorf("write image: %w", err)
	}
	return path, cleanup, nil
}

// ParseCritique extracts Summary + []Finding from the markdown response.
// It is intentionally tolerant: if the model didn't follow the format,
// we still return a best-effort finding list.
func ParseCritique(raw string) (string, []Finding) {
	var summary string
	var findings []Finding
	lines := strings.Split(raw, "\n")
	section := "" // "summary" | "findings" | ""
	var current *Finding // pending finding being annotated with metadata
	flush := func() {
		if current != nil {
			findings = append(findings, *current)
			current = nil
		}
	}
	for _, ln := range lines {
		trim := strings.TrimSpace(ln)
		switch {
		case strings.HasPrefix(trim, "## Summary"):
			section = "summary"
			flush()
			continue
		case strings.HasPrefix(trim, "## Findings"):
			section = "findings"
			flush()
			continue
		case strings.HasPrefix(trim, "## "):
			section = ""
			flush()
			continue
		}
		if section == "summary" && summary == "" && trim != "" {
			summary = trim
			continue
		}
		if section == "findings" {
			switch {
			case strings.HasPrefix(ln, "- "):
				// New finding at column 0.
				flush()
				f := parseFindingBullet(ln[2:])
				if f != nil {
					current = f
				}
			case strings.HasPrefix(ln, "  - Suggestion:") || strings.HasPrefix(ln, "    - Suggestion:"):
				if current != nil {
					current.Suggestion = strings.TrimSpace(strings.TrimPrefix(trim[len("- "):], "Suggestion:"))
				}
			case strings.HasPrefix(ln, "  - Region:") || strings.HasPrefix(ln, "    - Region:"):
				if current != nil {
					current.Region = strings.TrimSpace(strings.TrimPrefix(trim[len("- "):], "Region:"))
				}
			}
		}
	}
	flush()
	if summary == "" {
		// Fallback: use the first non-heading line as the summary.
		for _, ln := range lines {
			t := strings.TrimSpace(ln)
			if t != "" && !strings.HasPrefix(t, "#") {
				summary = t
				break
			}
		}
	}
	return summary, findings
}

var (
	reSeverity = regexp.MustCompile(`\[(critical|high|medium|low|info)\]`)
	reRegion   = regexp.MustCompile(`Region:\s*(.+)$`)
	reSuggest  = regexp.MustCompile(`Suggestion:\s*(.+)$`)
)

func parseFindingBullet(body string) *Finding {
	if strings.TrimSpace(strings.ToLower(body)) == "none" {
		return nil
	}
	sevMatch := reSeverity.FindStringSubmatch(body)
	if sevMatch == nil {
		// Allow entries without severity; treat as info.
		sevMatch = []string{"", "info"}
	}
	body = strings.Replace(body, sevMatch[0], "", 1)
	body = strings.TrimSpace(body)

	// Split on "—" or "-" for title / detail
	var title, detail string
	for _, sep := range []string{" — ", " - ", " —", " -"} {
		if i := strings.Index(body, sep); i >= 0 {
			title = strings.TrimSpace(body[:i])
			detail = strings.TrimSpace(body[i+len(sep):])
			break
		}
	}
	if title == "" {
		title = body
	}

	f := &Finding{
		Severity: Severity(sevMatch[1]),
		Title:    title,
		Detail:   detail,
	}
	// Look for indented sub-bullets on subsequent lines. The caller
	// (ParseCritique) passes one bullet at a time, so the indent data
	// isn't here — but the suggestion/region pattern often appears on
	// the same bullet line. We accept that.
	if m := reRegion.FindStringSubmatch(body); m != nil {
		f.Region = strings.TrimSpace(m[1])
	}
	if m := reSuggest.FindStringSubmatch(body); m != nil {
		f.Suggestion = strings.TrimSpace(m[1])
		// Re-derive title as everything before "Suggestion:"
		if i := strings.Index(body, "Suggestion:"); i > 0 {
			head := strings.TrimSpace(body[:i])
			head = strings.TrimRight(head, " -—")
			if head != "" {
				f.Title = head
			}
		}
	}
	f.ID = buildFindingID(f)
	return f
}

var idCounter int64

func buildFindingID(f *Finding) string {
	idCounter++
	return fmt.Sprintf("vision-%d-%s", idCounter, slug(f.Title))
}

var reSlug = regexp.MustCompile(`[^a-z0-9]+`)

func slug(s string) string {
	s = strings.ToLower(s)
	s = reSlug.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-")
	if len(s) > 32 {
		s = s[:32]
	}
	return s
}

// Available returns nil if mmx is installed and MINIMAX_API_KEY is set,
// otherwise the relevant error. Useful for doctor/health checks.
func Available(binary string) error {
	if binary == "" {
		binary = "mmx"
	}
	if _, err := exec.LookPath(binary); err != nil {
		return fmt.Errorf("%w: %s", ErrNotInstalled, binary)
	}
	if os.Getenv("MINIMAX_API_KEY") == "" {
		return ErrNoAPIKey
	}
	return nil
}

// ReadResponse loads a previously-saved Critique JSON (used by the
// workflow step when re-running without re-invoking mmx).
func ReadResponse(path string) (*Critique, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var c Critique
	if err := json.Unmarshal(data, &c); err != nil {
		return nil, err
	}
	return &c, nil
}

// Write serialises a Critique to JSON.
func (c *Critique) Write(w io.Writer) error {
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}
	_, err = w.Write(data)
	return err
}

// Score returns a 0..100 health score for the critique (100 = no issues).
// Critical = -40, high = -25, medium = -10, low = -3, info = -1.
func (c *Critique) Score() int {
	score := 100
	for _, f := range c.Findings {
		switch f.Severity {
		case SevCritical:
			score -= 40
		case SevHigh:
			score -= 25
		case SevMedium:
			score -= 10
		case SevLow:
			score -= 3
		case SevInfo:
			score -= 1
		}
	}
	if score < 0 {
		score = 0
	}
	return score
}

// Verdict maps a score to a review-style verdict.
func (c *Critique) Verdict() string {
	switch {
	case c.Score() < 50:
		return "REQUEST_CHANGES"
	case c.Score() < 80:
		return "COMMENT"
	default:
		return "APPROVE"
	}
}

// CountBySeverity returns {severity: count}.
func (c *Critique) CountBySeverity() map[string]int {
	out := map[string]int{}
	for _, f := range c.Findings {
		out[string(f.Severity)]++
	}
	return out
}

// AsReviewFindings converts Vision findings into review.Finding so they
// can flow through the same pipeline as code findings. Provided here as
// a small adapter to keep the dependency graph clean (caller passes the
// conversion).
type ReviewFinding struct {
	ID, Title, Detail, Suggestion, Severity, Region string
}

// ToReview converts a Vision finding to a ReviewFinding-style map.
func (f Finding) ToReview() ReviewFinding {
	return ReviewFinding{
		ID:         f.ID,
		Title:      f.Title,
		Detail:     f.Detail,
		Suggestion: f.Suggestion,
		Severity:   string(f.Severity),
		Region:     f.Region,
	}
}

// String renders a Critique as a one-paragraph summary + bulleted findings.
func (c *Critique) String() string {
	var sb strings.Builder
	fmt.Fprintf(&sb, "Vision critique: image=%s model=%s score=%s verdict=%s duration=%dms\n",
		c.Image, c.Model, c.FormatScore(), c.Verdict(), c.DurationMs)
	if c.Err != "" {
		fmt.Fprintf(&sb, "  error: %s\n", c.Err)
	}
	if c.Summary != "" {
		fmt.Fprintf(&sb, "  summary: %s\n", c.Summary)
	}
	for _, f := range c.Findings {
		fmt.Fprintf(&sb, "  - [%s] %s", f.Severity, f.Title)
		if f.Detail != "" {
			fmt.Fprintf(&sb, " — %s", f.Detail)
		}
		if f.Suggestion != "" {
			fmt.Fprintf(&sb, "\n      Suggestion: %s", f.Suggestion)
		}
		if f.Region != "" {
			fmt.Fprintf(&sb, "\n      Region: %s", f.Region)
		}
		fmt.Fprintln(&sb)
	}
	return sb.String()
}

// Itoa is a tiny helper used by callers formatting scores; kept here so
// visioncritic has no dependency on strconv.
func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}

// FormatScore returns "score/100" (e.g. "82/100").
func (c *Critique) FormatScore() string { return itoa(c.Score()) + "/100" }

// Compile-time guard.
var _ = errors.Is
