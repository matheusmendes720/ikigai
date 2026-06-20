# Taskwarrior full setup

All Taskwarrior-related config, scripts, help, and docs for the produtividade workspace. See [SPEC.md](SPEC.md) for layout and how the main repo uses this folder.

## Quick start

- **WSL:** Copy `config/taskrc.template` to `~/.taskrc`. Source `scripts/task_aliases.sh` from `~/.bashrc`.
- **PowerShell:** Source `pwsh/task-aliases.ps1` from your profile: `. .\taskwarrior\pwsh\task-aliases.ps1` (from repo root).
- **Help:** `th` = custom CLI tutorials (topics 00–12); `thelp` = vanilla Taskwarrior help.

## Paths (from repo root)

| Path | Purpose |
|------|---------|
| taskwarrior/config/ | taskrc.template, hooks/on-exit |
| taskwarrior/scripts/ | Bash/Python scripts (daily-review, weekly-review, calculate-metrics, etc.) |
| taskwarrior/help/ | Help content and main-help.ps1/sh |
| taskwarrior/docs/ | TASKWARRIOR_*.md, VANILLA_USAGE_GUIDE.md |
| taskwarrior/pwsh/ | task-aliases.ps1 |

## Life OS

From main repo: `life task today`, `life task daily-review`, `life task weekly-review`, `life task metrics`. These use taskwarrior/scripts as the script directory.
