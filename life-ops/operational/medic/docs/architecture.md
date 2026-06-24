# medic — architecture

medic is a Go toolkit organised as five cooperating pillars, with the
public `medic` CLI fronting them and a stable SDK (`pkg/medic`) for
embedding.

## Bird's-eye

```
                ┌─────────────────────────────────────┐
                │          medic CLI (cobra)          │
                │  health · review · issue · …        │
                └────────────────┬────────────────────┘
                                 │
                ┌────────────────▼────────────────────┐
                │            internal/*               │
                │ config · shell · gitx               │
                │ review · health · pattern           │
                │ visual · agentic · ui · report      │
                │ store                               │
                └────────────────┬────────────────────┘
                                 │
                ┌────────────────▼────────────────────┐
                │            pkg/medic/*              │
                │  reviewer · healthcheck             │
                │  visualdebug · agentflow            │
                └─────────────────────────────────────┘
```

The CLI is thin. Every command is a cobra wrapper that loads the
`config.Config`, builds the appropriate internal package's orchestrator,
runs it, and emits a `report.Bundle` through `report.Render`.

## Pillar responsibilities

| Pillar | Files | Inputs | Outputs |
|---|---|---|---|
| **review** | `internal/review/{client,analyzer,report}.go` | GitHub PR/Issue refs + local git diff | Markdown / SARIF / JSON verdict |
| **health** | `internal/health/{health,checks}.go` | target dir + auto-detected language | Checked list (test/lint/coverage/deps/complexity) |
| **visual** | `internal/visual/{frame,capture,render,diff,script,inspector,recorder}.go` | binary + script + golden dir | SVG frames + cell grid + diff |
| **pattern** | `internal/pattern/pattern.go` | target dir + git history | `[]Finding{Family,Severity,…}` |
| **agentic** | `internal/agentic/{engine,guard,actions}.go` | YAML workflow + registered actions | `RunResult{Steps,OK,Duration}` |

## Data flow (review pipeline)

```
config.Config ─► review.Analyzer.Analyze(ctx, pr)
  ├─► Client.PullRequest   (GitHub API)
  ├─► Client.FilesChanged  (GitHub API)
  ├─► gitx.Repo.Diff/Log   (local git)
  ├─► health.Orchestrator  (pytest/ruff/etc.)
  ├─► pattern.Engine.Scan  (heuristics)
  └─► decideVerdict        (rules in analyzer.go)
                │
                ▼
        review.Report  ─►  report.Render  ─►  text/markdown/sarif/html
                                          └►  store.WriteFile → .medic/
                                          └►  client.PostReview (optional)
```

## Config resolution

```
defaults < ./medic.yaml (target) < ~/.config/medic/config.yaml
        < /etc/medic < MEDIC_* env < CLI flags
```

Each level overrides the previous. Viper handles the merge.

## Why a polyglot tool in Go?

medic inspects Python / Rust / Node / Go projects. Writing each check in
each language would multiply maintenance. Go gives a single static binary,
fast startup (matters for CI), easy cross-compilation, and a small surface
area for a security-sensitive tool that handles tokens and reads code.

## Adding a new check

1. Implement the `health.Check` interface.
2. Register it in `internal/health/health.go:defaultsFor` under the right
   language bucket.
3. Optional: add a `pattern.Finding` rule in `internal/pattern/pattern.go`.

## Adding a new workflow action

1. Implement `agentic.Action` (Name + Run).
2. Register it in `internal/agentic/actions.go:StandardRegistry`.

That's it — `medic workflow list` will pick it up, and YAML can reference
it by name.
