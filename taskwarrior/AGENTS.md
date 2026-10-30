# taskwarrior

## OVERVIEW
Portable Taskwarrior configuration, hooks, aliases, tutorials, and operating guides; score 9 because Taskwarrior is a distinct integration domain.

## STRUCTURE
```
taskwarrior/
├── config/   # taskrc template and exit hook
├── scripts/  # Life OS reviews, recurrence helpers, metrics, and hooks
├── help/     # detailed and quick CLI tutorials
├── docs/     # setup, pitfalls, workflows, and command reference
└── pwsh/     # PowerShell aliases and helper commands
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Install local Taskwarrior settings | `config/taskrc.template` | Copy to `~/.taskrc`; defines UDAs, reports, and contexts |
| Change Taskwarrior exit behavior | `config/hooks/on-exit` | Installed under the user's Taskwarrior hook directory |
| Change Life OS task commands | `scripts/` | Daily/weekly review, recurrence, metrics, and aliases |
| Change custom help | `help/main-help.sh`, `help/main-help.ps1` | Detailed and quick topic routers |
| Change help formatting | `help/format-markdown.*`, `help/format-quick.py` | Detailed prose versus compact tables |
| Change shell shortcuts | `scripts/task_aliases.sh` | WSL/Git Bash aliases used from `~/.bashrc` |
| Change PowerShell shortcuts | `pwsh/task-aliases.ps1` | Mirrors the Bash alias surface for native Windows |
| Read operational guidance | `docs/` | Setup, pitfalls, strategic workflows, and complete feature lists |

## CONVENTIONS
- `config/taskrc.template` is a template, not a live user configuration; never overwrite `~/.taskrc` from repository code.
- UDA names and report names are integration contracts with the Life CLI and task content; keep spelling stable.
- Help has two deliberate forms: detailed tutorials and compact quick-reference tables.
- Help output forces UTF-8, strips ANSI when piped, paginates only on a TTY, caps width near 100 columns, and returns zero for successful help.
- Bash and PowerShell aliases mirror each other; update both surfaces when changing user-facing shortcuts.
- Hook payloads are pass-through data. `on-add.sh` warns about missing `meta_ciclo` but must emit the original payload unchanged.

## ANTI-PATTERNS
- NEVER mutate the user's `~/.taskrc` or installed hooks as a side effect of repository scripts.
- NEVER drop or reorder the JSON payload in `scripts/on-add.sh`; validation is warning-only.
- DO NOT make a successful help topic nonzero; the help router relies on zero for command chaining.
- DO NOT duplicate quick-reference content without updating the topic router and the corresponding detailed topic.
- Review scripts intentionally tolerate individual Taskwarrior query failures; inspect their output rather than treating a zero exit as proof that every query succeeded.
- Keep `.taskrc` custom fields aligned with the hierarchical objective vocabulary before changing report filters.
