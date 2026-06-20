# Aliases - Quick Reference

## Core Task Management

| Alias | Command | Description |
|-------|---------|-------------|
| `ta` | `task add` | Add new task |
| `tl` | `task list` | List tasks |
| `tn` | `task next` | Next tasks (by urgency) |
| `td` | `task done` | Complete task |
| `tc` | `task done` | Complete task (alternative) |
| `tall` | `task all` | All tasks |
| `tcomp` | `task completed` | Completed tasks |
| `tready` | `task ready` | Ready tasks |
| `tblocked` | `task blocked` | Blocked tasks |
| `tactive` | `task +ACTIVE list` | Active tasks |
| `tw` | `task waiting` | Waiting tasks |

## Date & Priority

| Alias | Command | Description |
|-------|---------|-------------|
| `tld` | `task due:today list` | Tasks due today |
| `tldt` | `task due:tomorrow list` | Tasks due tomorrow |
| `tlo` | `task +OVERDUE list` | Overdue tasks |
| `tlh` | `task priority:H list` | High priority tasks |

## Information

| Alias | Command | Description |
|-------|---------|-------------|
| `ti <id>` | `task <id> info` | Task information |
| `ts` | `task summary` | Summary statistics |
| `tst` | `task stats` | Detailed statistics |
| `tp` | `task projects` | List projects |
| `ttags` | `task tags` | List tags |
| `tcal` | `task calendar` | Calendar view |
| `tdiag` | `task diagnostics` | System diagnostics |

## Data Management

| Alias | Command | Description |
|-------|---------|-------------|
| `tex` | `task export` | Export tasks |
| `tim` | `task import` | Import tasks |
| `tundo` | `task undo` | Undo last action |

## Workflows

| Alias | Command | Description |
|-------|---------|-------------|
| `tm` | Morning routine | Narrativa, due:today, blocos |
| `te` | Evening routine | Completed today, plan tomorrow |
| `twk` | Weekly review | Relatorios + summary |
| `tstandup` | Standup | Daily standup view |

## Hierarchy

| Alias | Command | Description |
|-------|---------|-------------|
| `tsonho` | `task sonho` | View all Sonhos |
| `tobj` | `task objetivo` | View Objetivos |
| `tmeta` | `task meta` | View Metas (15-day) |
| `tmicro` | `task tarefa` | View Tarefas (5-day) |
| `tbloco` | `task blocos` | View Blocos de Tempo |

## Contexts

| Alias | Command | Description |
|-------|---------|-------------|
| `tctxw` | `task context work` | Work context |
| `tctxft` | `task context focus_today` | Focus today context |
| `tctxwk` | `task context week` | Week context |
| `tctxrev` | `task context review` | Review context |
| `tctxciclo` | `task context ciclo` | Ciclo context |
| `tctxonda` | `task context onda` | Onda context |
| `tctxtf` | `task context teste_fogo` | Teste de Fogo context |
| `tctx0` | `task context none` | Clear context |

## Recurrence

| Alias | Command | Description |
|-------|---------|-------------|
| `trecurd "<desc>"` | `task add recur:daily due:today+1d` | Daily recurrence |
| `trecurw "<desc>"` | `task add recur:weekly due:eow` | Weekly recurrence |
| `trecur15 "<desc>"` | `task add recur:2w due:today+15d` | 15-day recurrence |
| `trecurm "<desc>"` | `task add recur:monthly due:eom` | Monthly recurrence |
| `twd <start> <days> "<desc>"` | Working-day calculator | Calculate working days |

## Task Operations

| Alias | Command | Description |
|-------|---------|-------------|
| `tstart <id>` | `task <id> start` | Start task |
| `tstop <id>` | `task <id> stop` | Stop task |

## Help

| Alias | Command | Description |
|-------|---------|-------------|
| `th` | `task help` | Help (custom help system) |
| `th` | Custom help router | Custom help system |
| `th <topic>` | Custom help topic | Specific help topic |
| `thq` | Quick reference | Quick tabular reference |
