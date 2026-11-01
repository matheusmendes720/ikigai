# taskwarrior

The full Taskwarrior workspace: config, scripts, help system, docs, PowerShell
aliases. Earns its file: score 9 (48 files, 6 subdirectories, 22 referencing
files) — a distinct domain (a complete external-tool setup, not product code).

## OVERVIEW
Self-contained Taskwarrior setup that can be opened as its own workspace or
extracted to a Git submodule (see `SPEC.md`). Mostly Portuguese-language
docs and a PT-BR domain vocabulary. **Taskwarrior was replaced by
`taskdog-server` as the task store (M83)**, but this folder is still the
`task_scripts` path that `life task daily-review|weekly-review|metrics` exec.

## WHERE TO LOOK
| Task | Path | Notes |
|------|------|-------|
| Layout contract | `SPEC.md` | scope + how the main repo consumes it |
| Config template | `config/taskrc.template` | copy to `~/.taskrc`; UDAs, reports, contexts |
| Hooks | `config/hooks/on-exit` | time-based reminders (08:00 Rotina Inicial, 20:00 Rotina Final) |
| Aliases (WSL) | `scripts/task_aliases.sh` | source from `~/.bashrc` |
| Aliases (PowerShell) | `pwsh/task-aliases.ps1` | source from `$PROFILE` |
| Review scripts | `scripts/daily-review.sh`, `weekly-review.sh` | `task narrativa` / `task relatorios` |
| Metrics | `scripts/calculate-metrics.py` | reads a `task export` JSON |
| Working-day offsets | `scripts/working-days.py` | skips weekends |
| Add-hook validation | `scripts/on-add.sh` | warns on `+revisao` without `meta_ciclo` |
| Help system | `help/main-help.sh`, `help/main-help.ps1` | `th` / `thq` routers |
| Help content | `help/content/00-overview.md` … `12-metrics.md` | 13 topics + 5 `-quick` variants |
| Formatters | `help/format-markdown.{py,sh,ps1}`, `help/format-quick.py` | ANSI formatters |
| Reference docs | `docs/TASKWARRIOR_*.md`, `docs/VANILLA_USAGE_GUIDE.md` | 7 files, ~5.7k lines |

## CONVENTIONS
- **5-level hierarchy emulated over Taskwarrior's flat Project→Task.** Projects
  carry the Sonho; UDAs carry the rest. Vocabulary: Sonho → Objetivo → Meta →
  Tarefa → Atividade.
- **UDAs**: `sonho_id, objetivo_id, objetivo_trimestre, meta_ciclo,
  tarefa_microciclo, bloco_tempo, ciclo, onda_numero, taxa_conclusao,
  barreira, teste_fogo_dimensao`.
- **Reports**: `narrativa, relatorios, revisao, supervisao, blocos, sonho,
  objetivo, meta, tarefa`. **Contexts**: `work, focus_today, week, review,
  ciclo, onda, teste_fogo, none`.
- **Help always exits 0** so it can be chained. UTF-8 via `LC_ALL/LANG=C.UTF-8`;
  ANSI is stripped when stdout is not a TTY; `TASK_HELP_FORCE_COLORS=1` forces
  colors for WSL→PowerShell interop; width is capped at 100 chars.
  `__H2_SECTION_BREAK__` is the marker the PowerShell splitter uses between H2
  sections.
- The alias vocabulary (`ta tl tn td tc tm te twk tsonho tobj tmeta tmicro
  tbloco tctx* trecur* twd th thq thelp tcmd tman …`) is duplicated *literally*
  in `help/format-markdown.py` and `help/format-markdown.ps1` — change both.
- Both formatters mutate module globals (`global RESET, BOLD, … = ''`) to
  disable ANSI when not a TTY. Deliberate, but not pure-function style.
- Shebangs differ by tree: `#!/usr/bin/env python3` in `help/`, `python` in
  `scripts/`.

## ANTI-PATTERNS
- **Never let `+revisao` through without `meta_ciclo`** — the on-add hook
  warns and the `revisao` report filters on it.
- **Never overload a single block** and **never optimize for a single
  metric** (explicit rules in the docs).
- **Never make `th`/`thq` fail.** Both return exit code 0 by contract.
- `scripts/on-add.sh` is a pass-through: it logs the payload to
  `~/.task/hooks.log` and re-emits it unchanged. Do not make it swallow or
  rewrite the payload.
- `scripts/weekly-review.sh` writes `week-tasks.json` into the *current
  working directory*, not into `taskwarrior/` — do not assume where it lands.
- `help/content/image/00-overview/1767793547417.png` (121 KB) is the only
  binary asset; the rest of `help/` is text.

## COMMANDS
```bash
th                      # overview topic
th <topic>              # 00-overview … 12-metrics
thq <topic>             # compact variant
python3 taskwarrior/scripts/calculate-metrics.py backup.json --days 30
python3 taskwarrior/scripts/working-days.py 2026-11-02 5
bash taskwarrior/scripts/daily-review.sh
bash taskwarrior/scripts/weekly-review.sh
```
