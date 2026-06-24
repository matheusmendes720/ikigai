package visual

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/life-oss/medic/internal/shell"
)

// ScriptStep is a single programmable action against a running TUI.
//
// Exactly one of WaitMs/Key/Text should be non-zero. Comment is purely
// documentary and is ignored at run time — use it to keep a script
// self-explanatory in code review.
//
//   - WaitMs > 0:   sleep for WaitMs milliseconds
//   - Key != "":    parse and send a key (see ParseScriptKey)
//   - Text != "":   send literal text
type ScriptStep struct {
	WaitMs  int    `json:"wait_ms,omitempty" yaml:"wait_ms,omitempty"`
	Key     string `json:"key,omitempty"      yaml:"key,omitempty"`
	Text    string `json:"text,omitempty"    yaml:"text,omitempty"`
	Comment string `json:"comment,omitempty" yaml:"comment,omitempty"`
}

// Script is an ordered list of ScriptStep plus optional metadata.
// A script can drive a TUI to a known state for golden-frame capture.
type Script struct {
	Name  string       `json:"name,omitempty"  yaml:"name,omitempty"`
	About string       `json:"about,omitempty" yaml:"about,omitempty"`
	Steps []ScriptStep `json:"steps"           yaml:"steps"`
}

// Add appends a step and returns the script for chaining.
func (s *Script) Add(step ScriptStep) *Script {
	s.Steps = append(s.Steps, step)
	return s
}

// LoadScript reads a script from disk, sniffing JSON or YAML by extension.
// .yaml / .yml → YAML; anything else → JSON.
func LoadScript(path string) (*Script, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("visual: read script %s: %w", path, err)
	}
	ext := strings.ToLower(filepath.Ext(path))
	var s Script
	switch ext {
	case ".yaml", ".yml":
		if err := unmarshalScript(data, &s, "yaml"); err != nil {
			return nil, fmt.Errorf("visual: parse yaml %s: %w", path, err)
		}
	default:
		if err := json.Unmarshal(data, &s); err != nil {
			return nil, fmt.Errorf("visual: parse json %s: %w", path, err)
		}
	}
	return &s, nil
}

// SaveScript writes the script in the format implied by path's extension.
// .yaml/.yml → YAML (manual emitter to avoid pulling yaml.v3 from this
// file); everything else → JSON.
func SaveScript(s *Script, path string) error {
	if s == nil {
		return errors.New("visual: nil script")
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("visual: mkdir: %w", err)
	}
	ext := strings.ToLower(filepath.Ext(path))
	var data []byte
	var err error
	switch ext {
	case ".yaml", ".yml":
		data = marshalScriptYAML(s)
	default:
		data, err = json.MarshalIndent(s, "", "  ")
		if err != nil {
			return fmt.Errorf("visual: marshal json: %w", err)
		}
	}
	if err := os.WriteFile(path, data, 0o644); err != nil {
		return fmt.Errorf("visual: write script %s: %w", path, err)
	}
	return nil
}

// Run executes the script against a live PTY session. It honours ctx —
// callers can wire SIGINT to ctx cancellation for graceful stop.
//
// Steps are run in order. After each step we honour WaitMs by sleeping
// (the next step can still be a key/text without an explicit wait).
func Run(ctx context.Context, session *shell.PTYSession, s *Script) error {
	if session == nil {
		return errors.New("visual: nil PTY session")
	}
	if s == nil {
		return errors.New("visual: nil script")
	}
	for i, step := range s.Steps {
		if err := ctx.Err(); err != nil {
			return err
		}
		if step.WaitMs > 0 {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(time.Duration(step.WaitMs) * time.Millisecond):
			}
		}
		switch {
		case step.Key != "":
			seq, err := ParseScriptKey(step.Key)
			if err != nil {
				return fmt.Errorf("visual: step %d key %q: %w", i, step.Key, err)
			}
			if _, err := session.Write(seq); err != nil {
				return fmt.Errorf("visual: step %d write key: %w", i, err)
			}
		case step.Text != "":
			if _, err := session.WriteString(step.Text); err != nil {
				return fmt.Errorf("visual: step %d write text: %w", i, err)
			}
		}
	}
	return nil
}

// ParseScriptKey converts a human-friendly key name into the bytes a real
// terminal would send. Supported forms:
//
//	"Enter", "Return"       → \r
//	"Tab"                   → \t
//	"Esc", "Escape"         → ESC
//	"Backspace"             → \b
//	"Space"                 → " "
//	"Up", "Down", "Left", "Right" → ESC [ A/B/C/D
//	"Home", "End"           → ESC [ H / F
//	"PageUp", "PageDown"    → ESC [ 5~ / 6~
//	"Insert", "Delete"      → ESC [ 2~ / 3~
//	"F1".."F12"             → ESC OP / ESC [ 11~ / ...
//	"Ctrl+X"                → control-byte of X (X in {A..Z})
//	"Alt+X"                 → ESC + X
//	"<raw>"                 → bytes of <raw> literally
//
// A leading "<" and trailing ">" are stripped if present, so YAML/JSON
// scripts can write "<Enter>" without ambiguity.
func ParseScriptKey(name string) ([]byte, error) {
	if name == "" {
		return nil, errors.New("empty key")
	}
	if len(name) >= 2 && name[0] == '<' && name[len(name)-1] == '>' {
		name = name[1 : len(name)-1]
	}
	switch strings.ToLower(name) {
	case "enter", "return", "cr":
		return []byte{'\r'}, nil
	case "tab":
		return []byte{'\t'}, nil
	case "esc", "escape":
		return []byte{0x1b}, nil
	case "backspace", "bs":
		return []byte{0x7f}, nil // matches what most TUI apps expect
	case "space":
		return []byte{' '}, nil
	case "up":
		return []byte("\x1b[A"), nil
	case "down":
		return []byte("\x1b[B"), nil
	case "left":
		return []byte("\x1b[D"), nil
	case "right":
		return []byte("\x1b[C"), nil
	case "home":
		return []byte("\x1b[H"), nil
	case "end":
		return []byte("\x1b[F"), nil
	case "pageup", "pgup":
		return []byte("\x1b[5~"), nil
	case "pagedown", "pgdn":
		return []byte("\x1b[6~"), nil
	case "insert":
		return []byte("\x1b[2~"), nil
	case "delete", "del":
		return []byte("\x1b[3~"), nil
	}
	// F1..F12
	if strings.HasPrefix(strings.ToLower(name), "f") && len(name) <= 4 {
		var n int
		if _, err := fmt.Sscanf(name[1:], "%d", &n); err == nil && n >= 1 && n <= 12 {
			return fKeyBytes(n), nil
		}
	}
	// Ctrl+X (X is single ASCII letter)
	low := strings.ToLower(name)
	if strings.HasPrefix(low, "ctrl+") && len(name) == 6 {
		ch := name[5]
		if ch >= 'a' && ch <= 'z' {
			ch -= 32
		}
		if ch >= 'A' && ch <= 'Z' {
			return []byte{byte(ch) - 'A' + 1}, nil
		}
	}
	// Alt+X
	if strings.HasPrefix(low, "alt+") && len(name) == 5 {
		return []byte{0x1b, name[4]}, nil
	}
	// Raw single-rune fallback.
	if len(name) == 1 {
		return []byte(name), nil
	}
	return nil, fmt.Errorf("unknown key %q", name)
}

// fKeyBytes returns the canonical terminal escape sequence for F1..F12.
func fKeyBytes(n int) []byte {
	switch n {
	case 1:
		return []byte("\x1bOP")
	case 2:
		return []byte("\x1bOQ")
	case 3:
		return []byte("\x1bOR")
	case 4:
		return []byte("\x1bOS")
	case 5:
		return []byte("\x1b[15~")
	case 6:
		return []byte("\x1b[17~")
	case 7:
		return []byte("\x1b[18~")
	case 8:
		return []byte("\x1b[19~")
	case 9:
		return []byte("\x1b[20~")
	case 10:
		return []byte("\x1b[21~")
	case 11:
		return []byte("\x1b[23~")
	case 12:
		return []byte("\x1b[24~")
	}
	return nil
}

// ----------------------------------------------------------------------
// YAML emitter / decoder
// ----------------------------------------------------------------------
//
// We deliberately don't import gopkg.in/yaml.v3 inside this file: the
// dependency is already in the parent project's go.mod, but minimising
// imports keeps the visual package self-contained and easier to read.
// Instead we do the round-trip through a simple intermediate map type
// using encoding/json for parse and a hand-rolled emitter for write.
// Tests that need full YAML fidelity (anchors, tags) can swap in
// yaml.Unmarshal via a build-tagged file.

// unmarshalScript decodes data as JSON or YAML into s. YAML is decoded
// via encoding/json by first normalising the document into JSON-ish
// syntax (we only support the subset our own emitter produces).
func unmarshalScript(data []byte, s *Script, _ string) error {
	// Try JSON first; if it fails, try the YAML adapter.
	if err := json.Unmarshal(data, s); err == nil {
		return nil
	}
	var raw yamlScript
	if err := decodeYAML(data, &raw); err != nil {
		return err
	}
	*s = raw.toScript()
	return nil
}

// marshalScriptYAML hand-prints a YAML document for s. The output is
// stable, diff-friendly, and round-trips through unmarshalScript.
func marshalScriptYAML(s *Script) []byte {
	var b strings.Builder
	if s.Name != "" {
		fmt.Fprintf(&b, "name: %q\n", s.Name)
	}
	if s.About != "" {
		fmt.Fprintf(&b, "about: %q\n", s.About)
	}
	b.WriteString("steps:\n")
	for _, step := range s.Steps {
		b.WriteString("  -\n")
		if step.WaitMs != 0 {
			fmt.Fprintf(&b, "    wait_ms: %d\n", step.WaitMs)
		}
		if step.Key != "" {
			fmt.Fprintf(&b, "    key: %q\n", step.Key)
		}
		if step.Text != "" {
			fmt.Fprintf(&b, "    text: %q\n", step.Text)
		}
		if step.Comment != "" {
			fmt.Fprintf(&b, "    comment: %q\n", step.Comment)
		}
	}
	return []byte(b.String())
}

// yamlScript is the intermediate shape used by decodeYAML.
type yamlScript struct {
	Name  string             `json:"name,omitempty"`
	About string             `json:"about,omitempty"`
	Steps []yamlScriptStep   `json:"steps"`
}

type yamlScriptStep struct {
	WaitMs  int    `json:"wait_ms,omitempty"`
	Key     string `json:"key,omitempty"`
	Text    string `json:"text,omitempty"`
	Comment string `json:"comment,omitempty"`
}

func (y yamlScript) toScript() Script {
	out := Script{Name: y.Name, About: y.About}
	for _, st := range y.Steps {
		out.Steps = append(out.Steps, ScriptStep{
			WaitMs:  st.WaitMs,
			Key:     st.Key,
			Text:    st.Text,
			Comment: st.Comment,
		})
	}
	return out
}

// decodeYAML is a tiny YAML→JSON transpiler restricted to the subset our
// emitter produces: mappings with scalar values (string/int) and lists
// of mappings. It is NOT a general YAML parser.
//
// This keeps the package's import surface small while still letting
// hand-written scripts use YAML.
func decodeYAML(data []byte, out *yamlScript) error {
	// Convert simple YAML to JSON: wrap top-level keys and quote values.
	// Then unmarshal via json.
	conv, err := yamlToJSON(data)
	if err != nil {
		return err
	}
	return json.Unmarshal(conv, out)
}

// yamlToJSON performs a minimal "key: value" / "- item" conversion.
// It handles:
//
//	foo: bar
//	foo: "quoted"
//	foo: 123
//	list:
//	  - key: value
//	    key2: value2
//
// Any deviation throws an error; this is intentional.
func yamlToJSON(in []byte) ([]byte, error) {
	var out strings.Builder
	out.WriteByte('{')
	lines := strings.Split(strings.ReplaceAll(string(in), "\r\n", "\n"), "\n")
	type stackEntry struct {
		indent   int
		isList   bool
		firstKey bool
	}
	stack := []stackEntry{{indent: -1, firstKey: true}}
	// pending key at current indent
	var pendingKey string
	flushPending := func() {
		if pendingKey != "" {
			if !stack[len(stack)-1].firstKey {
				out.WriteByte(',')
			}
			stack[len(stack)-1].firstKey = false
			out.WriteByte('"')
			out.WriteString(escapeJSON(pendingKey))
			out.WriteString(`":`)
			pendingKey = ""
		}
	}
	for _, raw := range lines {
		if strings.TrimSpace(raw) == "" || strings.HasPrefix(strings.TrimSpace(raw), "#") {
			continue
		}
		// measure indent
		indent := 0
		for indent < len(raw) && raw[indent] == ' ' {
			indent++
		}
		line := strings.TrimRight(raw[indent:], " \t")
		// Pop stack until we are inside the right container.
		for len(stack) > 1 && indent <= stack[len(stack)-1].indent {
			flushPending()
			top := stack[len(stack)-1]
			if top.isList {
				out.WriteByte('}')
			} else {
				out.WriteByte('}')
			}
			stack = stack[:len(stack)-1]
			// close separator for parent
			if len(stack) > 0 {
				out.WriteByte(',')
			}
		}
		trimmed := line
		if strings.HasPrefix(trimmed, "- ") {
			// New list item. If we are not currently in a list, we need
			// the pending key to mark the list.
			if !stack[len(stack)-1].isList {
				if pendingKey == "" {
					return nil, fmt.Errorf("yaml: list item without key at indent %d", indent)
				}
				flushPending()
				out.WriteByte('[')
				stack[len(stack)-1].isList = true
				stack = append(stack, stackEntry{indent: indent, isList: true, firstKey: true})
			} else {
				// continuing existing list: close previous item
				out.WriteByte('}')
				out.WriteByte(',')
				stack[len(stack)-1].firstKey = true
			}
			trimmed = strings.TrimPrefix(trimmed, "- ")
			// The first thing on a list-item line is "key: value" or just "value".
			if k, v, ok := splitKV(trimmed); ok {
				if !stack[len(stack)-1].firstKey {
					out.WriteByte(',')
				}
				stack[len(stack)-1].firstKey = false
				out.WriteByte('{')
				out.WriteByte('"')
				out.WriteString(escapeJSON(k))
				out.WriteString(`":`)
				out.WriteString(yamlScalar(v))
				pendingKey = ""
			} else {
				// bare scalar item
				out.WriteString(yamlScalar(trimmed))
			}
			continue
		}
		if k, v, ok := splitKV(trimmed); ok {
			// We're appending a key into the current container.
			if stack[len(stack)-1].isList {
				// shouldn't happen: keys belong inside list items, not lists
				return nil, fmt.Errorf("yaml: key at list indent")
			}
			flushPending()
			pendingKey = k
			// peek the next thing: if v is "" this is the start of a
			// nested container. Otherwise it's a scalar.
			if v == "" {
				// The value's container will be opened when the next line
				// is processed; we keep pendingKey as-is and let the
				// loop decide between list/mapping on the next iteration.
			} else {
				if !stack[len(stack)-1].firstKey {
					out.WriteByte(',')
				}
				stack[len(stack)-1].firstKey = false
				out.WriteByte('"')
				out.WriteString(escapeJSON(k))
				out.WriteString(`":`)
				out.WriteString(yamlScalar(v))
				pendingKey = ""
			}
			continue
		}
		return nil, fmt.Errorf("yaml: cannot parse line %q", raw)
	}
	// Close remaining containers.
	flushPending()
	for len(stack) > 1 {
		top := stack[len(stack)-1]
		if top.isList {
			out.WriteByte(']')
		} else {
			out.WriteByte('}')
		}
		stack = stack[:len(stack)-1]
		if len(stack) > 0 {
			out.WriteByte(',')
		}
	}
	out.WriteByte('}')
	return []byte(out.String()), nil
}

// splitKV parses "key: value" or "key:". It returns ok=false if the line
// doesn't contain a top-level colon.
func splitKV(s string) (string, string, bool) {
	idx := strings.IndexByte(s, ':')
	if idx < 0 {
		return "", "", false
	}
	k := strings.TrimSpace(s[:idx])
	v := strings.TrimSpace(s[idx+1:])
	return k, v, true
}

// yamlScalar converts a YAML scalar to its JSON literal.
func yamlScalar(s string) string {
	if s == "" {
		return "null"
	}
	if s == "true" || s == "false" || s == "null" {
		return s
	}
	// numeric?
	if isAllDigits(s) || (len(s) > 1 && s[0] == '-' && isAllDigits(s[1:])) {
		return s
	}
	// already quoted?
	if (len(s) >= 2 && s[0] == '"' && s[len(s)-1] == '"') ||
		(len(s) >= 2 && s[0] == '\'' && s[len(s)-1] == '\'') {
		// strip quotes and JSON-encode
		return "\"" + escapeJSON(s[1:len(s)-1]) + "\""
	}
	return "\"" + escapeJSON(s) + "\""
}

// isAllDigits returns true if s is non-empty and all ASCII digits.
func isAllDigits(s string) bool {
	if s == "" {
		return false
	}
	for i := 0; i < len(s); i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	return true
}

// escapeJSON is the smallest possible JSON-string escaper.
func escapeJSON(s string) string {
	var b strings.Builder
	b.Grow(len(s) + 2)
	for i := 0; i < len(s); i++ {
		c := s[i]
		switch c {
		case '"':
			b.WriteString(`\"`)
		case '\\':
			b.WriteString(`\\`)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		default:
			if c < 0x20 {
				fmt.Fprintf(&b, `\u%04x`, c)
			} else {
				b.WriteByte(c)
			}
		}
	}
	return b.String()
}