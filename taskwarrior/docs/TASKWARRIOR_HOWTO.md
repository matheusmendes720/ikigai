# Taskwarrior HOWTO – Strategic Workflow Mapping

This links your hierarchy (Sonho → Objetivo → Meta → Tarefa → Atividade) and review cadences to concrete commands, reports, and aliases in WSL/Pwsh.

## Daily (Diário)
- Morning: `tm` (narrativa, due:today, blocos), `task narrative`, `tld`, `tbloco`.
- Work: `tstart <id>`, `tstop <id>`, `td <id>`; check active `tactive`.
- Evening: `te` (completed today, plan tomorrow).
- Help: `th` or `task help`.

## Weekly (Semanal, #relatorios)
- Review: `twk` or `task relatorios`; summary: `task modified.after:today-7d summary`.
- Exports: `taskwarrior/scripts/weekly-review.sh` (also writes week-tasks.json).

## Quinzenal (15d, #revisao)
- Report: `task revisao` (requires meta_ciclo).
- Guard: on-add warns if +revisao missing meta_ciclo.

## Mensal (#supervisao)
- Report: `task supervisao` (last 30d, pending).
- Sonhos: `task sonho` for project-level view. ^tr-8ypufzdaj

## Status & readiness
- Ready: `task ready` or `task ready` report.
- Blocked: `task blocked`.
- Waiting: `task waiting`.
- Active: `task active`.
- Overdue: `task overdue`; High priority: `tlh`.

## Blocos de tempo
- Today: `task blocos` or `task bloco_tempo:<Manhã|Tarde|Noite> due:today`.

## Hierarchy filters
- `tsonho`, `tobj`, `tmeta`, `tmicro`, `tbloco`.
- Examples: `task sonho_id:<id> list`, `task meta_ciclo:1 list`, `task tarefa_microciclo:1 list`.

## Contexts
- Available: `work` (project:sonho:publicar-livro), `focus_today` (due:today), `week` (next 7d), `review` (+relatorios or +revisao or +supervisao), `ciclo` (meta_ciclo.any:), `onda` (onda_numero.any:), `teste_fogo` (+teste_fogo), `none`.
- Set: `task context <name>` or aliases: `tctxw`, `tctxft`, `tctxwk`, `tctxrev`, `tctxciclo`, `tctxonda`, `tctxtf`.
- Clear: `task context none` or `tctx0`.
- List: `task context list`.

## Recurrence & generation
- Calendar-based helpers: `trecurd "<desc>"` (daily), `trecurw "<desc>"` (weekly), `trecur15 "<desc>"` (15d), `trecurm "<desc>"` (monthly).
- Working-day helper: `twd <start YYYY-MM-DD> <working-days> "<desc>" [mods]` (e.g., `twd 2026-01-06 15 "Meta 15d úteis" +revisao meta_ciclo:1`).
- Manual: `task add recur:daily due:today+1d "<desc>"`, `task add recur:weekly due:eow "<desc>"`, etc.
- Working-day calculator: `python3 taskwarrior/scripts/working-days.py 2026-01-06 15`.

## Backups & exports
- Quick backup: `taskwarrior/scripts/backup-and-recur.sh` (writes `backup-YYYYMMDD_HHMMSS.json`).
- Manual: `tex > backup.json`; restore `tim backup.json`.

## Metrics
- Simple metrics: `python3 taskwarrior/scripts/calculate-metrics.py backup.json [--days N]` (prints total/pending/waiting/completion rate).
- Daily: `taskwarrior/scripts/daily-review.sh`.
- Weekly: `taskwarrior/scripts/weekly-review.sh`.

## Hooks (enabled)
- `~/.task/hooks/on-exit`: time-based reminders (tm/te/twk).
- `~/.task/hooks/on-add`: logs to `~/.task/hooks.log`, warns if +revisao without meta_ciclo (pass-through, v2-safe).

## Aliases
- Core: `ta tl tn td tc tld tldt tlh tlo tlp tlt ts tst tex tim th tall tcomp tready tblocked tactive tw tcal tundo`.
- Info/ops: `ti <id>`, `tstart <id>`, `tstop <id>`.
- Contexts: `tctxw`, `tctxft`, `tctxwk`, `tctxrev`, `tctxciclo`, `tctxonda`, `tctxtf`, `tctx0`.
- Recurrence: `trecurd`, `trecurw`, `trecur15`, `trecurm`, `twd <start> <days> "<desc>"`.
- Workflows: `tm`, `te`, `twk`, `tstandup`.
- Hierarchy: `tsonho`, `tobj`, `tmeta`, `tmicro`, `tbloco`.
- Diag: `tdiag`.

## Tips
- Use `task news` after upgrades (2.6.x notice).
- For contexts, remember they persist; run `task context none` to clear.
- Use `th` instead of `task --help` (the latter runs default report). 
