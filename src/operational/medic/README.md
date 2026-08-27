# medic 🩺 — A code-review & visual-debug toolkit for agentic workflows

`medic` is a versatile Go toolkit for **examining the overall health of a CLI / TUI application**,
automating **GitHub PR + Issue code review**, and **visual-debugging terminal applications**
during design iterations. It was built to support agentic tooling routines — workflows that
*read* a codebase, *analyze* it, *run* its checks, *screenshot* its TUIs, and *suggest* UX/workflow
improvements, all from a single binary.

It is intentionally a **standalone, polyglot** tool — most codebases medic inspects are *not* Go.
medic speaks to GitHub via the REST/GraphQL API, runs the project's own test runner
(`pytest`, `uv run pytest`, `cargo test`, `go test`, `npm test`, etc.), drives a TUI
in a PTY, captures its framebuffer as SVG/ANSI/PNG, and feeds the result to pattern
detectors that surface UX/code/workflow improvement suggestions.

---

## Five pillars

| Pillar | What it does | Commands |
|---|---|---|
| **review** | GitHub PR + Issue code review, file-level analysis, pattern flags | `medic review <PR>` · `medic issue <N>` |
| **health** | Suite tests, lint, coverage, dependency freshness, complexity | `medic health` · `medic health --json` |
| **visual** | Drive a TUI/CLI in a PTY, capture frames, diff runs | `medic visualize` · `medic debug <bin>` |
| **pattern** | UX / workflow / code-pattern detector with fix suggestions | `medic patterns` · `medic suggest` |
| **agentic** | Multi-step agentic workflows (YAML) — review → health → visualize → report | `medic workflow run` · `medic workflow list` |

Plus the **TUI dashboard** that ties them together: `medic dashboard`.

---

## Quickstart

```bash
cd life-ops/operational/medic
make build

# Run against the host project (this repo's Python kernel)
./bin/medic health        --target ../packages/core
./bin/medic review 42     --target .                 # PR #42
./bin/medic visualize     --target ../apps/tui --record tests/golden/recording.yaml
./bin/medic patterns      --target ../packages/core/src
./bin/medic workflow run  examples/workflow/pr-review.yaml
```

medic is configured via `medic.yaml` in the target repo (auto-discovered upward), env vars
(`MEDIC_*`), or flags. See `configs/medic/medic.example.yaml`.

---

## What "code-review connected with GitHub issues & PRs" looks like

```
$ ./bin/medic review 142 --repo life-oss/life --target ./packages/core
PR #142  ⤵  Implement PolicyEngine hysteresis
├─ diff  +412 / −87   files 9   commits 4
├─ health gate        ✅ tests · ✅ lint · ⚠ coverage 71% (−2.3)
├─ issue link         #138 (closes), #140 (depends on)
├─ pattern flags      • engine_method_too_long (policy_engine.py:84)  [SUGGEST]
│                      • repeated_branch_in_if (3 sites)              [SUGGEST]
│                      • fsm_state_added_without_test                   [BLOCK]
├─ TUI regression     ✅ recorded run matches golden frame
└─ verdict            REQUEST_CHANGES  (1 blocking flag)
```

`medic review` posts the verdict back as a PR review comment (and labels the PR) when
running with `--post`. Local mode writes `.medic/review-<PR>.md`.

---

## Visual-debug pipeline

`medic visualize` runs the project's TUI in a pseudo-terminal, drives it with a recorded
key-sequence script, captures each frame's cell grid (including RGB colors), and saves
**SVG renderings + raw cell dumps + diff against golden frames**.

```
$ ./bin/medic visualize --binary ../apps/tui/bin/pav --script scripts/demo.yaml --frames 40
frame 001  size 120×40  ok  t=0.42s
frame 002  size 120×40  ok  t=0.38s  diff-vs-golden: 0 cells
...
SVG bundle:  .medic/visualize/2026-06-22_17-04-12/
   ├── frames/001.svg … 040.svg
   ├── frames/001.txt … 040.txt      # raw cell grid (fgcolor, bgcolor, rune)
   ├── timeline.json                 # per-frame timing
   ├── diff.json                     # per-cell diff vs golden
   └── report.html                   # browser-friendly viewer
```

`medic debug` is the interactive REPL form — drop into a TUI binary and inspect live:

```
$ ./bin/medic debug --binary ../apps/tui/bin/pav
(medic) ▌ type a key, "tree" to dump the widget tree, "shoot" to capture,
          "exit" to leave
> tree
└── App[0,0 120×40]
    ├── Header[0,0 120×3]    text="PAV — Dashboard"
    ├── Container[0,3 120×34]
    │   ├── KPICard[2,4 30×5]      "Q_HE 0.81"
    │   ├── RegimeBar[2,10 30×3]   color=green glyph="━━━━━"
    │   └── …
> shoot
saved → .medic/debug/2026-06-22T17-08-00.svg
> exit
```

This is the foundation of the agentic **visual-improvement loop**: capture a frame, run
pattern detection on the captured widget tree + colors + glyphs, suggest layout/typography
improvements, apply them, re-capture, diff.

---

## Pattern detection (`medic patterns`)

Patterns are categorized into three buckets:

- **UX patterns** — captured from TUI widget trees: low-contrast colors, oversized
  panels, missing focus indicators, broken table alignment, ragged right edges, etc.
- **Workflow patterns** — inferred from PR / issue / commit history: missing
  acceptance criteria, no reproduction script on bug reports, long-lived branches,
  drive-by refactors, reverts within 24h, etc.
- **Code patterns** — AST/heuristic flags on the source: long methods, repeated
  conditional branches, missing tests for new FSM states, public symbols without
  docstrings, etc.

Each pattern produces a `Finding{ID, Severity, Locations, Rationale, Suggestion}`.
Suggestions can be auto-applied when `--fix` is set (only safe-fixes).

---

## Agentic workflows

`medic workflow` runs a YAML-described multi-step agentic loop:

```yaml
name: pr-review
steps:
  - id: fetch
    use: github.fetch_pr          # args: { number: 142, repo: life-oss/life }
  - id: diff
    use: local.diff_tree          # args: { target: ./packages/core }
  - id: health
    use: health.run               # args: { target: ./packages/core, fail_fast: true }
  - id: patterns
    use: pattern.scan             # args: { target: ./packages/core/src, family: code }
  - id: visualize
    use: visual.run_golden        # args: { binary: ../apps/tui/bin/pav, golden: tests/golden/dashboard.json }
  - id: llm_review
    use: llm.review               # args: { provider: openai, model: gpt-4o, prompt: configs/prompts/pr-review.txt }
  - id: report
    use: report.write             # args: { path: .medic/review-142.md, format: markdown }
  - id: post
    when: "{{ .steps.health.ok }}"
    use: github.post_review       # args: { event: REQUEST_CHANGES, body_file: .medic/review-142.md }
```

The workflow engine supports `when:` guards (`when: '{{ .steps.X.ok }}'`), step outputs
(`.steps.<id>.output`), retries, timeouts, and parallel branches.

---

## Embedding

Everything in `internal/` is also exported through `pkg/medic/`:

```go
import "github.com/life-oss/medic/pkg/medic/reviewer"
import "github.com/life-oss/medic/pkg/medic/healthcheck"
import "github.com/life-oss/medic/pkg/medic/visualdebug"
import "github.com/life-oss/medic/pkg/medic/agentflow"

r, _ := reviewer.New("life-oss/life", os.Getenv("GITHUB_TOKEN"))
report, _ := r.ReviewPR(ctx, 142, reviewer.Target{Local: "./packages/core"})
```

See `examples/basic/`, `examples/workflow/`, and `examples/github-action/`.

---

## Why "medic"?

A *medic* examines the patient, runs the diagnostics, points at the wound, applies
the bandage, and reports back. Same shape as the job: examine a CLI/TUI codebase,
run health & visual diagnostics, point at UX / code / workflow wounds, suggest fixes,
post the report.

---

## Layout

```
medic/
├── cmd/medic/                cobra entrypoints (root + 11 subcommands)
├── internal/
│   ├── config/               viper loader + env override
│   ├── shell/                PTY executor + parser + debug shell
│   ├── review/               GitHub client + PR/issue analyzers
│   ├── health/               checker orchestrator (test/lint/deps/coverage)
│   ├── visual/               PTY frame capture + cell dump + SVG
│   ├── pattern/              UX/workflow/code pattern engine
│   ├── agentic/              YAML workflow engine
│   ├── ui/                   tview dashboard, palette, widgets
│   ├── gitx/                 git helpers (diff_tree, blame, log scan)
│   ├── report/               markdown / SARIF / html emitters
│   └── store/                local .medic/ persistence
├── pkg/medic/                public SDK (reviewer, healthcheck, visualdebug, agentflow)
├── examples/                 basic / workflow / github-action
├── configs/medic/            medic.example.yaml + prompt templates
├── scripts/                  dev helpers
├── docs/                     architecture + writing-patterns guide
└── testdata/                 golden frames + fixture repos
```
