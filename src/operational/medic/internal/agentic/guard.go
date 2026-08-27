package agentic

import (
	"fmt"
	"reflect"
	"regexp"
	"strconv"
	"strings"
)

// EvalGuard evaluates a `when:` expression against the shared step outputs.
//
// Supported subset (intentionally small):
//   {{ .steps.<id>.ok }}                    → bool
//   {{ .steps.<id>.output.<field> }}        → any
//   eq / ne / and / or                      → combinators, written infix
//
// Examples:
//
//   when: '{{ .steps.health.ok }}'
//   when: '{{ .steps.fetch.output.kind }} eq "pr"'
//   when: '{{ .steps.a.ok }} and not {{ .steps.b.ok }}'
//
// Unknown identifiers yield false (fail-closed).
func EvalGuard(expr string, outputs map[string]any) bool {
	if expr == "" {
		return true
	}
	toks := lex(expr)
	v, err := parseExpr(toks)
	if err != nil || v == nil {
		return false
	}
	return asBool(v.eval(outputs))
}

// token is one element of a guard expression.
type token struct {
	kind string // id | str | num | punct | kw
	val  string
}

func lex(s string) []token {
	var out []token
	i := 0
	for i < len(s) {
		ch := s[i]
		switch {
		case ch == ' ' || ch == '\t' || ch == '\n':
			i++
		case ch == '{':
			// Expect {{ ...
			if i+1 < len(s) && s[i+1] == '{' {
				j := strings.Index(s[i+2:], "}}")
				if j < 0 {
					return out
				}
				body := strings.TrimSpace(s[i+2 : i+2+j])
				out = append(out, tokenize(body)...)
				i += 2 + j + 2
				continue
			}
			i++
		case ch == '(' || ch == ')' || ch == ',':
			out = append(out, token{kind: "punct", val: string(ch)})
			i++
		case ch == '"' || ch == '\'':
			j := i + 1
			for j < len(s) && s[j] != ch {
				if s[j] == '\\' && j+1 < len(s) {
					j += 2
					continue
				}
				j++
			}
			out = append(out, token{kind: "str", val: s[i+1 : j]})
			i = j + 1
		case (ch >= '0' && ch <= '9') || (ch == '-' && i+1 < len(s) && s[i+1] >= '0' && s[i+1] <= '9'):
			j := i + 1
			for j < len(s) && (s[j] >= '0' && s[j] <= '9' || s[j] == '.') {
				j++
			}
			out = append(out, token{kind: "num", val: s[i:j]})
			i = j
		case isIdentStart(ch):
			j := i
			for j < len(s) && isIdentPart(s[j]) {
				j++
			}
			word := s[i:j]
			if isKeyword(word) {
				out = append(out, token{kind: "kw", val: word})
			} else {
				out = append(out, token{kind: "id", val: word})
			}
			i = j
		default:
			// multi-char punct: eq, ne, and, or, not
			rest := s[i:]
			for _, op := range []string{" eq ", " ne ", " and ", " or ", " not "} {
				if strings.HasPrefix(rest, op) {
					out = append(out, token{kind: "kw", val: strings.TrimSpace(op)})
					i += len(op)
					goto next
				}
			}
			i++
		next:
		}
	}
	return out
}

func tokenize(body string) []token {
	// Split a single {{ ... }} body into tokens (no nested {{).
	return lexBody(body)
}

var reBodyTok = regexp.MustCompile(`(\{\{|\}\}|"[^"]*"|'[^']*'|[A-Za-z_.][A-Za-z0-9_.\-]*|\d+(?:\.\d+)?|==|!=|eq|ne|and|or|not|\(|\)|\s+)`)

func lexBody(body string) []token {
	var out []token
	for _, m := range reBodyTok.FindAllString(body, -1) {
		m = strings.TrimSpace(m)
		if m == "" {
			continue
		}
		switch {
		case m == "==" || m == "!=" || m == "eq" || m == "ne" || m == "and" || m == "or" || m == "not" || m == "(" || m == ")":
			out = append(out, token{kind: "kw", val: m})
		case len(m) >= 2 && (m[0] == '"' || m[0] == '\''):
			out = append(out, token{kind: "str", val: m[1 : len(m)-1]})
		case isDigit(m[0]) || (m[0] == '-' && len(m) > 1 && isDigit(m[1])):
			out = append(out, token{kind: "num", val: m})
		default:
			out = append(out, token{kind: "id", val: m})
		}
	}
	return out
}

func isIdentStart(c byte) bool { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_' }
func isIdentPart(c byte) bool  { return isIdentStart(c) || (c >= '0' && c <= '9') || c == '.' || c == '-' }
func isDigit(c byte) bool      { return c >= '0' && c <= '9' }
func isKeyword(w string) bool {
	switch w {
	case "eq", "ne", "and", "or", "not", "==", "!=":
		return true
	}
	return false
}

// ---- AST ------------------------------------------------------------------

type expr interface{ eval(map[string]any) any }

type litExpr struct{ v any }

func (l litExpr) eval(_ map[string]any) any { return l.v }

type pathExpr struct{ parts []string }

func (p pathExpr) eval(outputs map[string]any) any {
	v := any(outputs)
	for _, part := range p.parts {
		switch cur := v.(type) {
		case map[string]any:
			v = cur[part]
		default:
			// Use reflection for struct fields as a courtesy.
			rv := reflect.ValueOf(cur)
			if rv.Kind() == reflect.Struct {
				f := rv.FieldByName(part)
				if f.IsValid() {
					v = f.Interface()
					continue
				}
			}
			return nil
		}
	}
	return v
}

type notExpr struct{ inner expr }

func (n notExpr) eval(o map[string]any) any { return !asBool(n.inner.eval(o)) }

type binExpr struct {
	op       string
	left     expr
	right    expr
}

func (b binExpr) eval(o map[string]any) any {
	lv := b.left.eval(o)
	rv := b.right.eval(o)
	switch b.op {
	case "and":
		return asBool(lv) && asBool(rv)
	case "or":
		return asBool(lv) || asBool(rv)
	case "eq", "==":
		return equalish(lv, rv)
	case "ne", "!=":
		return !equalish(lv, rv)
	}
	return nil
}

func equalish(a, b any) bool {
	if a == nil || b == nil {
		return a == b
	}
	af, aok := toFloat(a)
	bf, bok := toFloat(b)
	if aok && bok {
		return af == bf
	}
	return fmt.Sprintf("%v", a) == fmt.Sprintf("%v", b)
}

func toFloat(v any) (float64, bool) {
	switch x := v.(type) {
	case float64:
		return x, true
	case int:
		return float64(x), true
	case int64:
		return float64(x), true
	case string:
		f, err := strconv.ParseFloat(x, 64)
		if err == nil {
			return f, true
		}
	}
	return 0, false
}

func asBool(v any) bool {
	switch x := v.(type) {
	case bool:
		return x
	case nil:
		return false
	case string:
		return x != "" && x != "false" && x != "0"
	case float64:
		return x != 0
	case int:
		return x != 0
	}
	return false
}

// parseExpr builds the AST. We support: and > or > not > cmp > path > lit.
func parseExpr(toks []token) (expr, error) {
	pos := 0
	e, err := parseOr(toks, &pos)
	if err != nil {
		return nil, err
	}
	return e, nil
}

func parseOr(toks []token, pos *int) (expr, error) {
	left, err := parseAnd(toks, pos)
	if err != nil {
		return nil, err
	}
	for *pos < len(toks) && toks[*pos].val == "or" {
		*pos++
		right, err := parseAnd(toks, pos)
		if err != nil {
			return nil, err
		}
		left = binExpr{op: "or", left: left, right: right}
	}
	return left, nil
}

func parseAnd(toks []token, pos *int) (expr, error) {
	left, err := parseNot(toks, pos)
	if err != nil {
		return nil, err
	}
	for *pos < len(toks) && toks[*pos].val == "and" {
		*pos++
		right, err := parseNot(toks, pos)
		if err != nil {
			return nil, err
		}
		left = binExpr{op: "and", left: left, right: right}
	}
	return left, nil
}

func parseNot(toks []token, pos *int) (expr, error) {
	if *pos < len(toks) && toks[*pos].val == "not" {
		*pos++
		inner, err := parseCmp(toks, pos)
		if err != nil {
			return nil, err
		}
		return notExpr{inner: inner}, nil
	}
	return parseCmp(toks, pos)
}

func parseCmp(toks []token, pos *int) (expr, error) {
	left, err := parsePrimary(toks, pos)
	if err != nil {
		return nil, err
	}
	if *pos < len(toks) {
		switch toks[*pos].val {
		case "eq", "==", "ne", "!=":
			op := toks[*pos].val
			*pos++
			right, err := parsePrimary(toks, pos)
			if err != nil {
				return nil, err
			}
			return binExpr{op: op, left: left, right: right}, nil
		}
	}
	return left, nil
}

func parsePrimary(toks []token, pos *int) (expr, error) {
	if *pos >= len(toks) {
		return nil, fmt.Errorf("unexpected end")
	}
	t := toks[*pos]
	*pos++
	switch t.kind {
	case "num":
		if strings.Contains(t.val, ".") {
			f, _ := strconv.ParseFloat(t.val, 64)
			return litExpr{v: f}, nil
		}
		n, _ := strconv.Atoi(t.val)
		return litExpr{v: n}, nil
	case "str":
		return litExpr{v: t.val}, nil
	case "id":
		// Strip the Go-template-like ".steps." prefix; the engine stores
		// each step's result flat under outputs[stepID], not nested under
		// a "steps" key. Users write .steps.<id>.<field>; we treat that
		// as <id>.<field>.
		raw := t.val
		raw = strings.TrimPrefix(raw, ".")
		raw = strings.TrimPrefix(raw, "steps.")
		parts := strings.Split(raw, ".")
		// Filter empty parts (from leading dot or double dots)
		out := parts[:0]
		for _, p := range parts {
			if p != "" {
				out = append(out, p)
			}
		}
		return pathExpr{parts: out}, nil
	case "kw":
		if t.val == "(" {
			inner, err := parseOr(toks, pos)
			if err != nil {
				return nil, err
			}
			if *pos < len(toks) && toks[*pos].val == ")" {
				*pos++
			}
			return inner, nil
		}
	}
	return litExpr{v: nil}, nil
}
