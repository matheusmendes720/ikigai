# Deploy — WSL2 & Ubuntu VPS Cloud Agent Setup

> How to bootstrap a cloud venv agent environment on WSL2 or Ubuntu VPS for multi-agent orchestration.

---

## Prerequisites

- **WSL2** (Windows with WSL2 enabled) or **Ubuntu 22.04+** (VPS)
- **Python 3.11+**
- **uv** — `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
- **Git** — `apt install git` on Ubuntu
- **GitHub CLI** (optional but recommended) — `apt install gh` on Ubuntu

---

## One-Time Machine Setup

### 1. Clone the repo

```bash
# SSH is recommended
git clone git@github.com:YOUR_HANDLE/life.git
cd life
```

### 2. Install uv

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv

# Verify
uv --version
```

### 3. Install the active app

```bash
cd life-ops/operational

# Install all packages (core + cli + tui)
uv sync --all-packages

# Verify
uv run pav --help
```

### 4. Run the full quality gate

```bash
uv run ruff check packages/core/src/
uv run ruff format --check packages/core/src/
uv run mypy packages/core/src/
uv run pytest
```

### 5. Configure git hooks

```bash
python .github/scripts/setup_hooks.py
```

---

## Cloud Agent Workflow

### Start an agent session (SSH / tmux / screen)

```bash
# Always work inside tmux so sessions survive disconnects
tmux new -s life-agent

# Pull latest changes
git checkout main && git pull

# Activate the environment
cd life-ops/operational
source .venv/bin/activate   # or: eval $(uv run hook --unset)
```

### Daily agent routine

```bash
# 1. Check for changes
python .github/scripts/code_review.py --base main --review-format

# 2. Run the daily flow
uv run pav daily run

# 3. Run tests affected by today's changes
python .github/scripts/code_review.py --base main --test-only --missing

# 4. Open a branch for any changes
git checkout -b feature/your-feature-name

# 5. After changes — run the full review gate
python .github/scripts/code_review.py --base main --gate --strict

# 6. Commit (hooks validate branch name + pre-commit runs)
git add -u && git commit -m "feat: description"
```

### Multi-agent parallel work (git worktrees)

When multiple agents need to work on the same package simultaneously:

```bash
# Agent 1 — works on core
python .github/scripts/git_worktree_manager.py \
  --add operational-core \
  --branch feature/core-refactor \
  --path ../life-ops-core

# Agent 2 — works on tui
python .github/scripts/git_worktree_manager.py \
  --add operational-tui \
  --branch feature/tui-screens \
  --path ../life-ops-tui

# Each worktree is fully isolated — uv sync independently
# When done, merge each worktree's branch via PR
```

### Sync back to main

```bash
git checkout main && git pull
git checkout -b feature/your-feature
# ... make changes, commit ...
python .github/scripts/code_review.py --base main --gate --strict
gh pr create --fill   # uses PULL_REQUEST_TEMPLATE.md
```

---

## WSL2-Specific Notes

```powershell
# Install WSL2 + Ubuntu from PowerShell (Admin)
wsl --install -d Ubuntu-22.04

# Your files are at
\\wsl$\Ubuntu-22.04\home\YOUR_USER\code_space\life\

# Or from inside WSL
cd /mnt/c/code_space/life-oss/life
```

**Performance tip:** Keep repo on the WSL filesystem (`\\wsl$\...`), not on Windows NTFS — git is 5–10× faster on ext4.

---

## Ubuntu VPS Setup (DigitalOcean / AWS / etc.)

```bash
# Create a non-root user
adduser agent
usermod -aG sudo agent

# Switch to agent user
su - agent

# Install essentials
sudo apt update && sudo apt install -y \
  git curl build-essential python3.11 python3.11-venv \
  tmux gh

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Clone (use SSH key in GitHub Settings > SSH Keys)
git clone git@github.com:YOUR_HANDLE/life.git
cd life/life-ops/operational
uv sync --all-packages
```

### Running agents via tmux

```bash
# Start a tmux server (persists across SSH sessions)
tmux new -s agent-main -d

# Attach to session
tmux attach -t agent-main

# Multiple windows for parallel work
# Ctrl-B c  — new window
# Ctrl-B n  — next window
# Ctrl-B d  — detach
```

---

## Environment Variables

```bash
# Optional: override defaults
export PAV_DATA_DIR="$HOME/.life-operational"   # default: ~/.time-tasker
export PAV_LOG_LEVEL="DEBUG"                   # default: INFO
export PAV_DATASET="golden"                     # default: golden (use synthetic for testing)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `uv: command not found` | `source ~/.cargo/env` or add to PATH |
| `mypy: not found` | `uv sync --all-packages` first |
| `ModuleNotFoundError: No module named 'operational'` | `cd life-ops/operational && uv sync` |
| Git permission denied | Set up SSH key: `ssh-keygen -t ed25519 && gh ssh-key add` |
| Pre-commit hook fails | `uv run pre-commit install --install-hooks` |
