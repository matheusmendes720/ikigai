# Writing patterns

This is a guide for adding new code / UX / workflow patterns to medic.
Patterns are *small, focused* detectors that look for one anti-pattern,
return a `Finding`, and propose a concrete `Suggestion`. They run in
isolation — each is responsible for one thing.

## Anatomy of a `pattern.Finding`

```go
type Finding struct {
    ID         string   // unique stable ID; "<family>.<rule>.<path>.<line>"
    Family     Family   // FamilyCode | FamilyUX | FamilyWorkflow
    Severity   Severity // info|low|medium|high|critical
    Path       string   // source path (for code/workflow)
    Line       int      // line number (0 if not applicable)
    Title      string   // one-line summary
    Rationale  string   // why this is a problem
    Suggestion string   // how to fix (1 line preferred)
    Rule       string   // stable short rule id, e.g. "no-debug-prints"
}
```

## Rules of thumb

1. **One rule, one finding.** If a detector returns several locations for
   the same pattern, return one finding per location — not one finding
   with many sites.

2. **Stable IDs.** Prefer IDs that don't include line numbers in the
   "rule" portion. The path+line goes in `Path`/`Line`. IDs are used in
   SARIF and `medic suggest --fix`; they must be stable.

3. **Severity is a function of impact, not detection confidence.**
   "I think this might be a bug" → info. "This breaks on Windows" →
   high. Avoid `medium` for everything.

4. **Suggestion must be actionable.** "Refactor this" is useless. "Extract
   to a dispatch table keyed by state name" is actionable.

5. **Don't repeat the title in the rationale.** Title is the headline;
   rationale is the explanation.

6. **False positives are worse than false negatives.** A noisy pattern
   trains users to ignore everything. When in doubt, raise the severity
   floor (`patterns.min_severity: medium`) instead of downgrading the rule.

## Code-pattern detectors

A detector is just a function:

```go
func scanFooBrackets(text, path string) []Finding {
    var out []Finding
    scanner := bufio.NewScanner(strings.NewReader(text))
    line := 0
    for scanner.Scan() {
        line++
        lineText := scanner.Text()
        if strings.Contains(lineText, "bar(") {
            out = append(out, Finding{
                ID:        fmt.Sprintf("code.foo-bar.%s.%d", path, line),
                Family:    FamilyCode,
                Severity:  SeverityLow,
                Path:      path,
                Line:      line,
                Title:     "Use bar() instead of foo() in this context",
                Rationale: "bar() handles edge cases foo() does not.",
                Suggestion: "Replace foo() with bar().",
                Rule:      "prefer-bar-over-foo",
            })
        }
    }
    return out
}
```

Register it in `scanFile` (or `scanCode` for cross-file patterns). The
engine calls `ScanCode(target)` which walks the tree.

## UX-pattern detectors

UX signals arrive as a `pattern.UXSignal`:

```go
type UXSignal struct {
    Frame       any    // *visual.Frame
    Cols, Rows  int
    TitleText   string
    HasBorders  bool
    BorderChar  string
    LowContrast bool
    Align       string
}
```

The visual package derives this when it captures a frame. Detectors live
in `ScanUX(sig)`. Add new fields to `UXSignal` when you need new
information; the visual inspector will fill them.

## Workflow-pattern detectors

Workflow patterns run against git history. Use `gitx.Open(target)` to
get a `*gitx.Repo`, then `r.Log(ctx, "HEAD", n)` for commits, or
`r.Diff(ctx, from, to)` for changes.

Examples already shipped:
- recent-revert (looks for revert commits in the last 20)
- no-conventional-commits (subject without feat:/fix:/chore:/… prefix)

## Testing a pattern

The fastest feedback loop is the seed repo:

```bash
scripts/seed_test_repo.sh /tmp/medic-demo
./bin/medic patterns --target /tmp/medic-demo --family code
```

Then add a case to your detector until it fires once on the seed data
without producing too many false positives.

## Auto-fix (`--fix`)

If your pattern has a deterministic, mechanical fix, you can implement
it in `internal/pattern/fix.go` and gate it behind
`patterns.auto_fix: true`. Otherwise, only suggest — humans should apply
risky changes.

## Performance

- Pattern detectors run synchronously in the workflow step
  `pattern.scan`. Keep them fast (< 100ms per file).
- Avoid reading the same file twice in one detector — share a single
  scanner.
- For cross-file patterns, prefer indexing once at the start of
  `ScanCode` and passing it down.
