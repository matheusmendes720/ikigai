# Taskwarrior — full setup (spec)

## Purpose

Single folder containing the full Taskwarrior setup for the produtividade workspace: config (taskrc, hooks), scripts (Bash/Python), help system (custom CLI tutorials), docs, and PowerShell aliases. Can be opened as its own workspace or later extracted to a Git submodule.

## Scope

- **config/** — taskrc.template, hooks/on-exit (copy to ~/.taskrc and ~/.task/hooks/).
- **scripts/** — task_aliases.sh, daily-review.sh, weekly-review.sh, calculate-metrics.py, working-days.py, backup-and-recur.sh, generate-working-recur.sh, on-add.sh. Used by Life OS task central (task_scripts path).
- **help/** — content (00–12, quick refs), main-help.ps1, main-help.sh, format-markdown.*, CROSS_PLATFORM_HELP_GUIDE.md.
- **docs/** — TASKWARRIOR_*.md, VANILLA_USAGE_GUIDE.md (setup, howto, cheatsheet, workflows, pitfalls).
- **pwsh/** — task-aliases.ps1 (PowerShell aliases; source from profile: `. .\taskwarrior\pwsh\task-aliases.ps1`).

## How main repo uses it

- **life** — [life/config.py](../life/config.py) and [config/life.yaml](../config/life.yaml): `task_scripts` points at `taskwarrior/scripts` so `life task daily-review`, `life task weekly-review`, `life task metrics` run from there.
- **WSL:** Source `taskwarrior/scripts/task_aliases.sh` from ~/.bashrc.
- **PowerShell:** Source `taskwarrior/pwsh/task-aliases.ps1` from $PROFILE.
- **INDEX-TW.md** and **README** — Links to taskwarrior/config, taskwarrior/scripts, taskwarrior/help, taskwarrior/docs.

## Optional: Git submodule

To make this a Git submodule, create a new repo (e.g. produtividade-taskwarrior), push the contents of taskwarrior/, then from main: `git submodule add <url> taskwarrior`. Then update life config and .cursor/rules if the path changes.
