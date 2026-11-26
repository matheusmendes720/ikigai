# .github

CI workflows, the PR-review orchestrator and the repository's GitHub metadata.
A distinct domain: automation, not product code.

## OVERVIEW
Five CI jobs, one deploy workflow, and the review tooling under `scripts/`
(it has its own guide: `scripts/AGENTS.md`). Automation, not product code.

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| CI pipeline | `workflows/ci.yml` | 5 jobs: `code-review-checks`, `quality-gates` (5-package matrix), `harness`, `published-surface`, `container` |
| Deploy pipeline | `workflows/deploy.yml` | builds + publishes 2 GHCR images, SSH deploy, live surface probe |
| Review tooling | `scripts/` | the PR-review orchestrator — see `scripts/AGENTS.md` |
| Labels | `labels.yml` | canonical label set (27) |
| PR template | `PULL_REQUEST_TEMPLATE.md` | what a pull request must say |

## CONVENTIONS
- **The deploy ships ONE immutable artifact.** The image is built once on the
  runner and the server runs THAT image. Two images (canonical + harness,
  ADR-037 D7); tags are `sha-<commit>` only — no floating `latest`.
- **Plain SSH, not `appleboy/ssh-action`** (deploy.yml): the release CDN's
  504s killed six consecutive runs; the runner's own `ssh` downloads nothing.
  Values are interpolated into the remote script on the RUNNER, and the key
  never leaves the runner as a file with mode 600.
- **GHCR packages are private**: the job logs in with its own `GITHUB_TOKEN`
  (or an explicit PAT), never `docker compose pull`; a pull is retried 5x
  with a growing wait.
- **A deploy is green only if the service is healthy**: `docker compose up -d
  --wait --wait-timeout 240 db api ws sync bot`. The harness is deliberately
  NOT waited for — it measures the provider.
- **The remote script is READ, not copied** (`deploy_extract_script.py`
  extracts it from the workflow's heredoc): a copy would be a second version
  that drifts.
- **The published surface is probed from OUTSIDE the tailnet**: the page must
  answer 200 and the data door must answer 401 without Telegram's signature.
- **CI pins tool versions**: `pip install ruff==0.17.3` for every `ruff-only`
  package — an open range makes the gate move with the day.

## ANTI-PATTERNS
- **Never swallow the review report with `|| true`** (ci.yml): it hid
  `FileNotFoundError: 'ruff'` for weeks while the job stayed green and the
  report never printed. The report is not a gate, but a crash fails the job.
- **Never ship a floating image tag** (`latest`, a branch tag) — `sha-<commit>`
  only.
- **Never read a secret from a tracked file**: secrets come from the
  environment, the job's own token, or a file secret on the server.
- Stale, pre-ADR-037: `labels.yml` still carries `subsystem/operational`,
  `subsystem/vibe-ops`, `subsystem/life-cli`, `subsystem/taskwarrior`, and
  `project_board_setup.py`'s starter issues reference label names
  (`type/infrastructure`) that `labels.yml` does not define.

## COMMANDS
```bash
docker compose -f deploy/compose.yml config --quiet   # the container job
node --test "deploy/harness/test/*.test.mjs"          # the harness job
```
The review CLI, the deploy helpers and the board tooling: `scripts/AGENTS.md`.
