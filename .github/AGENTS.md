# .github

## OVERVIEW
Repository automation, CI policy, issue metadata, and wiki publication; score 10 because this is a distinct GitHub-operations domain.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Change CI gates | `workflows/ci.yml` | PR review job, package quality matrix, MCP contract job |
| Change scheduled documentation | `workflows/openwiki-update.yml` | Regenerates the OpenWiki and static visualizer daily |
| Change PR review automation | `scripts/code_review.py` | Master changed-file review orchestrator |
| Change strict type review | `scripts/type_review.py` | Mypy-focused helper for changed Python files |
| Change test-gap review | `scripts/test_review.py` | Maps source files to tests and reports missing coverage |
| Change issue/project automation | `scripts/project_board.py`, `scripts/project_board_setup.py` | Labels, Projects v2 setup, starter issues |
| Change issue intake | `ISSUE_TEMPLATE/*.yml`, `ISSUE_TEMPLATE/issue_metrics.py` | Structured forms and read-only issue reports |
| Change repository labels | `labels.yml` | Authoritative label definitions used by the sync helper |
| Change contributor instructions | `PULL_REQUEST_TEMPLATE.md` | Human-facing PR checklist |
| Change public wiki content | `wiki/` | GitHub wiki source mirrored from repository documentation |

## CONVENTIONS
- CI selects package-specific environments: Poetry for `src/ikigai`, uv for `vibe-ops` and `interfaces/cli`, and ruff-only for `src/contracts` and `src/mesh`.
- For the IKIGAI package, invoke mypy by module identity (`-p src.ikigai.src`), never with a filesystem path.
- The quality-gates matrix intentionally excludes the archived PAV package; do not add it back without an explicit architecture decision.
- `labels.yml` is the label registry; synchronization must go through `project_board.py --sync-labels`.
- GitHub API helpers use `GITHUB_TOKEN`, `REPO_OWNER`, and `REPO_NAME`; the project-board setup helper additionally uses the authenticated `gh` CLI.
- The OpenWiki workflow regenerates `openwiki/`, `AGENTS.md`, `CLAUDE.md`, `docs/openwiki-visualizer/`, and the workflow itself; review generated diffs as automation output.

## ANTI-PATTERNS
- NEVER invoke mypy with a path in the `src/ikigai` CI entry; duplicate module identities abort the job.
- NEVER treat `src/operational/` as canonical CI code; it is archived under `archive/legacy-pav/`.
- DO NOT use `wiki/home.md` as current architecture truth; it still describes pre-pivot PAV paths as active.
- DO NOT hand-edit labels in the GitHub UI when a repository definition exists in `labels.yml`.
- DO NOT expose tokens in workflow logs or helper output.
- Reviewer helpers currently retain legacy default package paths; pass the intended package explicitly instead of reviving those paths.
