# Getting Started

Welcome to Algorithmic Life OS. This guide gets you from zero to a running local development environment in under 10 minutes.

---

## 1 — Clone the Repository

```bash
git clone git@github.com:matheusmendes/life.git
cd life
```

> Use HTTPS if you haven't set up SSH keys: `git clone https://github.com/matheusmendes/life.git`

---

## 2 — Install the Active App

The active application is **`life-ops/operational/`** — the PAV productivity kernel. It uses `uv` for package management.

```bash
cd life-ops/operational

# Install all packages (core + cli + tui)
uv sync --all-packages

# Verify CLI
uv run pav --help

# Launch the TUI
uv run pav home
```

---

## 3 — Run the Quality Gates

Before writing any code, verify the full test suite passes:

```bash
cd life-ops/operational

# Lint
uv run ruff check packages/core/src/
uv run ruff format --check packages/core/src/

# Type check
uv run mypy packages/core/src/

# Tests
uv run pytest
```

---

## 4 — Configure Git Hooks

Install pre-commit hooks so every commit is automatically checked:

```bash
cd life-ops/operational
uv run pre-commit install --install-hooks
```

Hooks run: `trailing-whitespace`, `end-of-file-fixer`, `ruff check`, `ruff format`, `mypy --strict`.

---

## 5 — Make Your First Change

```bash
# Create a branch
git checkout -b docs/your-fix

# Make changes, then run the review gate
python .github/scripts/code_review.py --base main --gate --strict

# Commit (hooks validate automatically)
git add -u && git commit -m "docs: describe your change"

# Push and open a PR
git push -u origin docs/your-fix
gh pr create --fill
```

---

## Quick Command Reference

| Command | What it does |
|---------|-------------|
| `uv run pav daily run` | Run the daily PAV flow |
| `uv run pav habit log --name sleep --streak 5` | Log a habit |
| `uv run pytest` | Run full test suite |
| `uv run pytest -k "test_name"` | Run a single test |
| `uv run ruff check src/` | Lint |
| `uv run mypy src/` | Type check |
| `python .github/scripts/code_review.py --base main --review-format` | Full review report |

---

## What's Next?

- [CLI Reference](CLI-Reference) — all available commands
- [Architecture Overview](../ARCHITECTURE_INDEX.md) — how the system fits together
- [PAV Kernel Docs](../life-ops/operational/README.md) — algorithms, entities, state machines
- [Deployment Guide](Deployment-WSL2-Ubuntu-VPS) — cloud agent setup for WSL2 or VPS
