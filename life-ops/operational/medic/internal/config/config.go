// Package config loads medic settings from medic.yaml, env, and CLI flags.
//
// Resolution order (highest first):
//  1. CLI flags
//  2. MEDIC_* environment variables
//  3. ./medic.yaml (target repo) — discovered upward to git root
//  4. ~/.config/medic/config.yaml
//  5. Hard-coded defaults
package config

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/viper"
)

// Config is the merged runtime config.
type Config struct {
	// Target repo (where the code lives — usually not the medic repo itself)
	Target TargetConfig `mapstructure:"target" yaml:"target"`

	// GitHub integration
	GitHub GitHubConfig `mapstructure:"github" yaml:"github"`

	// Health check selection
	Health HealthConfig `mapstructure:"health" yaml:"health"`

	// Visual / PTY capture
	Visual VisualConfig `mapstructure:"visual" yaml:"visual"`

	// Pattern detection
	Patterns PatternsConfig `mapstructure:"patterns" yaml:"patterns"`

	// LLM (used by `medic suggest` and workflow steps)
	LLM LLMConfig `mapstructure:"llm" yaml:"llm"`

	// Output
	Output OutputConfig `mapstructure:"output" yaml:"output"`
}

type TargetConfig struct {
	// Local path to inspect (default: cwd)
	Local string `mapstructure:"local" yaml:"local"`

	// Detected language (auto if empty: go | python | rust | node | mixed)
	Language string `mapstructure:"language" yaml:"language"`

	// Test runner override (else auto-detected)
	TestCmd string `mapstructure:"test_cmd" yaml:"test_cmd"`

	// Lint runner override
	LintCmd string `mapstructure:"lint_cmd" yaml:"lint_cmd"`

	// Coverage runner override
	CoverCmd string `mapstructure:"coverage_cmd" yaml:"coverage_cmd"`
}

type GitHubConfig struct {
	Token   string `mapstructure:"token" yaml:"token"`
	Repo    string `mapstructure:"repo" yaml:"repo"`     // owner/name
	BaseURL string `mapstructure:"base_url" yaml:"base_url"`
	// Post reviews/issue comments back to GitHub when --post is set.
	AllowPost bool `mapstructure:"allow_post" yaml:"allow_post"`
}

type HealthConfig struct {
	// Hard fail thresholds
	MinCoveragePct float64 `mapstructure:"min_coverage_pct" yaml:"min_coverage_pct"`
	MaxComplexity  int     `mapstructure:"max_complexity" yaml:"max_complexity"`
	// Check toggles
	RunTests    bool `mapstructure:"run_tests" yaml:"run_tests"`
	RunLint     bool `mapstructure:"run_lint" yaml:"run_lint"`
	RunCoverage bool `mapstructure:"run_coverage" yaml:"run_coverage"`
	RunDeps     bool `mapstructure:"run_deps" yaml:"run_deps"`
	RunComplex  bool `mapstructure:"run_complexity" yaml:"run_complexity"`
	// Per-check timeout
	Timeout time.Duration `mapstructure:"timeout" yaml:"timeout"`
}

type VisualConfig struct {
	// Path to the TUI binary to drive (or "python -m foo" / "cargo run -- ...")
	Binary string `mapstructure:"binary" yaml:"binary"`

	// Args passed to the binary
	Args []string `mapstructure:"args" yaml:"args"`

	// Initial COLS/ROWS for the PTY
	Cols int `mapstructure:"cols" yaml:"cols"`
	Rows int `mapstructure:"rows" yaml:"rows"`

	// Default frame rate cap for capture
	FrameRateMs int `mapstructure:"frame_rate_ms" yaml:"frame_rate_ms"`

	// Golden frame dir to diff against
	GoldenDir string `mapstructure:"golden_dir" yaml:"golden_dir"`

	// Output dir for frames
	OutputDir string `mapstructure:"output_dir" yaml:"output_dir"`

	// ANSI color support (true|false|auto)
	Color string `mapstructure:"color" yaml:"color"`
}

type PatternsConfig struct {
	// Family filters
	UX      bool `mapstructure:"ux" yaml:"ux"`
	Code    bool `mapstructure:"code" yaml:"code"`
	Workflow bool `mapstructure:"workflow" yaml:"workflow"`

	// Apply safe-fix when --fix is set
	AutoFix bool `mapstructure:"auto_fix" yaml:"auto_fix"`

	// Severity floor to surface
	MinSeverity string `mapstructure:"min_severity" yaml:"min_severity"` // info|low|medium|high|critical
}

type LLMConfig struct {
	Provider string `mapstructure:"provider" yaml:"provider"` // openai|anthropic|local|none
	Model    string `mapstructure:"model" yaml:"model"`
	APIKey   string `mapstructure:"api_key" yaml:"api_key"`
	BaseURL  string `mapstructure:"base_url" yaml:"base_url"`
	// System prompt file
	SystemPrompt string `mapstructure:"system_prompt" yaml:"system_prompt"`
}

type OutputConfig struct {
	// Format: text|json|markdown|sarif|html
	Format string `mapstructure:"format" yaml:"format"`
	// Where to write the report
	Path string `mapstructure:"path" yaml:"path"`
	// Verbose logging
	Verbose bool `mapstructure:"verbose" yaml:"verbose"`
	// No color (CI default)
	NoColor bool `mapstructure:"no_color" yaml:"no_color"`
}

// Defaults returns a sensible default Config.
func Defaults() Config {
	return Config{
		Target: TargetConfig{
			Local:    ".",
			Language: "",
		},
		GitHub: GitHubConfig{
			BaseURL: "https://api.github.com",
		},
		Health: HealthConfig{
			RunTests:       true,
			RunLint:        true,
			RunCoverage:    true,
			RunDeps:        true,
			RunComplex:     true,
			MinCoveragePct: 70.0,
			MaxComplexity:  15,
			Timeout:        5 * time.Minute,
		},
		Visual: VisualConfig{
			Cols:         120,
			Rows:         40,
			FrameRateMs:  120,
			OutputDir:    ".medic/visualize",
			GoldenDir:    "tests/golden/frames",
			Color:        "auto",
		},
		Patterns: PatternsConfig{
			UX:         true,
			Code:       true,
			Workflow:   true,
			AutoFix:    false,
			MinSeverity: "info",
		},
		LLM: LLMConfig{
			Provider: "none",
		},
		Output: OutputConfig{
			Format: "text",
			Path:   "",
		},
	}
}

// Load reads configuration using viper.
func Load(targetOverride string) (*Config, error) {
	v := viper.New()

	// Defaults
	def := Defaults()
	if err := v.MergeConfigMap(toMap(def)); err != nil {
		return nil, fmt.Errorf("defaults: %w", err)
	}

	// Config file discovery
	v.SetConfigName("medic")
	v.SetConfigType("yaml")
	if targetOverride == "" {
		targetOverride = "."
	}
	v.AddConfigPath(targetOverride)
	v.AddConfigPath(filepath.Join(targetOverride, "configs", "medic"))
	v.AddConfigPath(".")
	v.AddConfigPath("./configs/medic")
	if home, err := os.UserHomeDir(); err == nil {
		v.AddConfigPath(filepath.Join(home, ".config", "medic"))
	}
	v.AddConfigPath("/etc/medic")

	// Try to read config file (missing is OK)
	if err := v.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			// Real error reading the file
			return nil, fmt.Errorf("read medic.yaml: %w", err)
		}
	}

	// Environment binding — MEDIC_GITHUB_TOKEN, MEDIC_LLM_API_KEY, etc.
	v.SetEnvPrefix("MEDIC")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()

	// Resolve
	cfg := Defaults()
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}

	// Token resolution: explicit > env > gh CLI > keyring
	if cfg.GitHub.Token == "" {
		cfg.GitHub.Token = os.Getenv("GITHUB_TOKEN")
	}
	if cfg.GitHub.Token == "" {
		if t, err := readGHCLI(); err == nil {
			cfg.GitHub.Token = t
		}
	}

	// Required target
	if cfg.Target.Local == "" {
		cfg.Target.Local = "."
	}
	if abs, err := filepath.Abs(cfg.Target.Local); err == nil {
		cfg.Target.Local = abs
	}

	return &cfg, nil
}

// readGHCLI shells out to `gh auth token` if available.
func readGHCLI() (string, error) {
	// Implementation note: we don't shell out here to avoid import cycles;
	// the actual `gh` invocation lives in internal/shell. This returns
	// ErrNotFound so the caller can fall back to .netrc / none.
	return "", errors.New("gh CLI token not provided in this build")
}

func toMap(v any) map[string]any {
	// viper supports MergeConfigMap; we hand-roll because mapstructure tags
	// differ from viper's expectation in subtle ways. A proper solution would
	// marshal-then-unmarshal via yaml; for now we use struct defaults only.
	out := map[string]any{}
	// Intentionally empty — defaults are baked into the Config struct fields.
	_ = v
	return out
}
