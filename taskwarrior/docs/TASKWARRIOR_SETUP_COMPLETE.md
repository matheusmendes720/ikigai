# Taskwarrior Setup Complete ✅

**Status:** Fully configured with hierarchical workflows, contexts, recurrence helpers, and strategic alignment.

## What's Installed

### Configuration (`.taskrc`)
- ✅ All UDAs: sonho_id, objetivo_id, objetivo_trimestre, meta_ciclo, tarefa_microciclo, bloco_tempo, ciclo, onda_numero, taxa_conclusao, barreira, teste_fogo_dimensao
- ✅ Custom reports: narrativa, relatorios, revisao, supervisao, blocos, sonho, objetivo, meta, tarefa, ready, blocked, active, waiting, teste_fogo, overdue
- ✅ Contexts: work, focus_today, week, review, ciclo, onda, teste_fogo, none
- ✅ Settings: colors, verbosity, dateformat, default.command=next

### Aliases & Functions
**WSL (source from repo or copy to `~/.task_aliases.sh`):**
- Repo file: `taskwarrior/scripts/task_aliases.sh` — source it from `~/.bashrc` (path-agnostic).
- Core: ta, tl, tn, td, tc, tld, tldt, tlh, tlo, tlp, tlt, ts, tst, tex, tim, th, thelp, thq, tcmd, tman, tall, tcomp, tready, tblocked, tactive, tw, tcal, tundo
- Contexts: tctxw, tctxft, tctxwk, tctxrev, tctxciclo, tctxonda, tctxtf, tctx0
- Recurrence: trecurd, trecurw, trecur15, trecurm, twd (working-day helper)
- Workflows: tm, te, twk, tstandup
- Hierarchy: tsonho, tobj, tmeta, tmicro, tbloco
- Info/ops: ti, tstart, tstop, tdiag

**PowerShell (`scripts/task-aliases.ps1`):**
- Same functions, all call WSL task via `wt` wrapper. **Auto-loaded** from your PowerShell profile (`$PROFILE`) so `th`, `thelp`, `tdiag`, `ta`, `tl`, `tm`, etc. work in every new PowerShell window without opening WSL.

### Hooks
- ✅ `~/.task/hooks/on-exit`: Time-based reminders (08h tm, 20h te, Sunday 20h twk)
- ✅ `~/.task/hooks/on-add`: Logs to `~/.task/hooks.log`, warns if +revisao without meta_ciclo

### Helper Scripts
- ✅ `taskwarrior/scripts/daily-review.sh`: Daily review automation
- ✅ `taskwarrior/scripts/weekly-review.sh`: Weekly review + export
- ✅ `taskwarrior/scripts/calculate-metrics.py`: Metrics calculation (--days support)
- ✅ `taskwarrior/scripts/working-days.py`: Working-day calculator
- ✅ `taskwarrior/scripts/backup-and-recur.sh`: Backup + recur templates
- ✅ `taskwarrior/scripts/generate-working-recur.sh`: Working-day recurrence generator

## Help commands

- **`th`** — Custom CLI tutorials from **taskwarrior/help** (hierarchy, workflows, filters, reports, contexts, recurrence, udas, aliases, blocks, metrics). Use `th` or `th <topic>` (e.g. `th hierarchy`, `th workflows`); `thq <topic>` for quick reference.
- **`thelp`** — Vanilla official helpers from the original Taskwarrior source: `task help` (same as `thelp` with no args, or `thelp <command>` for a specific command). **`tcmd`** lists all task commands; **`tman <page>`** opens man pages (e.g. `tman task`, `tman taskrc`).

## Full setup (WSL2 + PowerShell)

1. **Install Taskwarrior** in Ubuntu WSL2: `sudo apt install taskwarrior` (or build from source).
2. **(Optional)** Copy `taskwarrior/config/taskrc.template` to `~/.taskrc` (in WSL) and adjust (e.g. `context.work.read` to your sonho project).
3. **(Optional)** Copy `taskwarrior/scripts/on-add.sh` to `~/.task/hooks/on-add` and `chmod +x`; optionally copy `taskwarrior/config/hooks/on-exit` to `~/.task/hooks/on-exit` and `chmod +x` for time-based reminders.
4. **WSL aliases:** Add to `~/.bashrc`: `source "/path/to/produtividade/taskwarrior/scripts/task_aliases.sh"` (replace with your workspace path, or use a symlink / env var).
5. **PowerShell:** Aliases are loaded automatically from your profile (`Microsoft.PowerShell_profile.ps1`). If you move the repo, update the path in the profile to point at `taskwarrior\pwsh\task-aliases.ps1`. To load manually in a session: `. .\taskwarrior\pwsh\task-aliases.ps1`
6. **Verify:** Run `th` (custom overview), `thelp` (vanilla help), and `tdiag` (diagnostics).

## Quick Start

### WSL
```bash
source ~/.task_aliases.sh
# or, if using repo directly:
source "/path/to/produtividade/taskwarrior/scripts/task_aliases.sh"
tm          # Morning routine
twd 2026-01-06 15 "Meta 15d" +revisao meta_ciclo:1
tctxciclo   # Filter by ciclo
tdiag       # Check setup
```

### PowerShell
```powershell
. .\scripts\task-aliases.ps1
tm          # Morning routine
twd 2026-01-06 15 "Meta 15d" +revisao meta_ciclo:1
tctxciclo   # Filter by ciclo
tdiag       # Check setup
```

## Documentation
- `TASKWARRIOR_HOWTO.md`: Workflow mapping (daily/weekly/15d/30d → commands)
- `TASKWARRIOR_COMMAND_CHEATSHEET.md`: Complete command reference
- `TASKWARRIOR_COMPLETE_FEATURES.md`: Full feature documentation
- `TASKWARRIOR_STRATEGIC_WORKFLOWS.md`: Strategic system integration
- `TASKWARRIOR_PITFALLS_AND_WORKAROUNDS.md`: Limitations & solutions

## Sample Data
- 4 tasks created (including 1 recurring template)
- Backup: `backup-sample.json` in workspace root

## Next Steps
1. Use `tm`/`te` for daily routines
2. Use `twk` for weekly reviews
3. Use `twd` for working-day tasks (15d/45d cycles)
4. Use contexts (`tctxciclo`, `tctxonda`) to filter by hierarchy
5. Run `taskwarrior/scripts/backup-and-recur.sh` periodically for backups

**CENTRALIZED REPORTS & CHANGELOG SYSTEM COMPLETE!**
