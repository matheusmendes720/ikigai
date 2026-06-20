#!/bin/bash
# Taskwarrior aliases for WSL (mirrors scripts/task-aliases.ps1)
# Source from ~/.bashrc: source "/path/to/produtividade/@scripts/taskwarrior/task_aliases.sh"

TASK_SCRIPTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
TASK_HELP_ROOT="$TASK_SCRIPTS_ROOT/help"

# Core task aliases
ta()  { task add "$@"; }
tl()  { task list "$@"; }
tn()  { task next "$@"; }
td()  { task done "$@"; }
tc()  { task done "$@"; }
tld() { task due:today list "$@"; }
tldt(){ task due:tomorrow list "$@"; }
tlh() { task priority:H list "$@"; }
tlo() { task +OVERDUE list "$@"; }
tlp() { task projects "$@"; }
tlt() { task tags "$@"; }
ts()  { task summary "$@"; }
tst() { task stats "$@"; }
tex() { task export "$@"; }
tim() { task import "$@"; }

# Help: th = custom CLI tutorials (this repo), thelp = vanilla task help
th() {
    local topic="${1:-overview}"
    "$TASK_HELP_ROOT/main-help.sh" "$topic"
}
thq() {
    local topic="${1:-overview}"
    "$TASK_HELP_ROOT/main-help.sh" --quick "$topic"
}
thelp() { task help "$@"; }
tcmd() { task commands "$@"; }
tman() {
    [ -n "$1" ] || { echo "Usage: tman <page> (e.g. task, taskrc)"; return 1; }
    man "task-$1" 2>&1
}

# Lists and status
tall()    { task all "$@"; }
tcomp()   { task completed "$@"; }
tready()  { task ready "$@"; }
tblocked(){ task blocked "$@"; }
tactive() { task +ACTIVE list "$@"; }
tw()      { task waiting "$@"; }
tcal()    { task calendar "$@"; }
tundo()   { task undo "$@"; }

# Contexts
tctxw()    { task context work "$@"; }
tctxft()   { task context focus_today "$@"; }
tctxwk()   { task context week "$@"; }
tctxrev()  { task context review "$@"; }
tctxciclo(){ task context ciclo "$@"; }
tctxonda() { task context onda "$@"; }
tctxtf()   { task context teste_fogo "$@"; }
tctx0()    { task context none "$@"; }

# Recurrence helpers
trecurd() { task add recur:daily due:today+1d "$@"; }
trecurw() { task add recur:weekly due:eow "$@"; }
trecur15(){ task add recur:2w due:today+15d "$@"; }
trecurm() { task add recur:monthly due:eom "$@"; }

# Working-day due: twd <start-date> <days> [rest of task add args]
twd() {
    local start="$1" days="$2"
    shift 2 2>/dev/null || true
    local due
    if [ -f "$TASK_SCRIPTS_ROOT/working-days.py" ]; then
        due="$(python3 "$TASK_SCRIPTS_ROOT/working-days.py" "$start" "$days")"
    else
        due="$start"
    fi
    task add "due:$due" "$@"
}

# Workflows
tm() {
    echo "-- Rotina Inicial (manhã) --"
    task narrativa
    task due:today list
    task blocos
}
te() {
    echo "-- Rotina Final (noite) --"
    task completed end:today
    task due:tomorrow list
}
twk() {
    echo "-- Revisão Semanal --"
    task relatorios
    task modified.after:today-7d summary
}
tstandup() {
    echo "-- Standup Diário --"
    task +narrativa due:today list
}

# Info and ops
ti()     { task "$@" info; }
tstart() { task "$@" start; }
tstop()  { task "$@" stop; }

# Hierarchy reports
tsonho() { task sonho "$@"; }
tobj()   { task objetivo "$@"; }
tmeta()  { task meta "$@"; }
tmicro() { task tarefa "$@"; }
tbloco() { task blocos "$@"; }

tdiag() { task diag "$@"; }
