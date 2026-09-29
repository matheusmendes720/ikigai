# M151 — `td` TUI textual para TaskdogAdapter

**Status:** 🔵 PLANNED
**Date:** 2026-09-29
**Author:** loop-orchestrator
**Branch:** master

## Contexto

Q4 fresh start. Mundo upstream (`pipx` taskdog, DB externo) foi
removido por decisão do usuário (regra: "o único sistema que importa
é esse que estamos trabalhando"). Nosso `data/taskdog/tasks.db`
está zerado (clean slate). `TaskdogAdapter` + MCP bridge prontos.

Falta: **interface de uso no dia-a-dia**. Studio LangGraph tem
BlockingError (M150 não resolveu). MCP bridge só é acessível via
Claude Code. **TUI textual in-process** resolve AGORA sem depender
de LLM nem de servidor web.

## O que já existe

`src/mesh/taskdog_cli.py` — argparse CLI read-only com `list`,
`show`, `status`. FUNCIONA (testado nesta sessão). Falta write path.

`TaskdogAdapter.apply_change()` — suporta 4 actions (CREATE/UPDATE/
DONE/DELETE). Acessa SQLite direto.

`src/mesh/queue.enqueue(TaskChange)` — entry do review queue.
Gera UUID, escreve `data/review_queue/<id>.json`, retorna id.

`src/mesh/review_queue_worker.run_once([adapters])` — consome queue,
aplica em todos os adapters.

## Spec

### Comandos novos no `taskdog_cli.py`

- `add --ueid UEID --title TITLE [--priority 1|2|3] [--due YYYY-MM-DD] [--description TEXT]`
- `done <ueid>`
- `update <ueid> [--priority N] [--status X] [--due YYYY-MM-DD]`

Todos os writes **vão pelo review queue** (ADR-014 intacto). CLI
enfileira `TaskChange` com `source_fork="cli"`. Worker propaga.

### Novo entry point: `td`

`src/bin/td` (Python script) — delega `python -m src.mesh.taskdog_cli`.
Adicionado a `pyproject.toml [project.scripts] td = "..."`.

### TUI live: `td tui`

Dashboard Rich com:
- Header: contagem por status (planned/in_progress/done/cancelled)
- Tabela: tasks ordenadas por prioridade + deadline
- Refresh a cada 2s (signal-based ou background thread)
- Keys: `q` quit, `r` refresh now, `+` add (form)

Usa `rich.live.Live` + `rich.table.Table` + `rich.panel.Panel`.

### Tests

`tests/test_m151_td_cli.py` — ~15 tests cobrindo:
- `add` enfileira TaskChange com campos corretos
- `done` enfileira DONE action
- `update` filtra campos vazios
- `td tui` inicia sem erro (smoke)
- Validação de UEID (regex)
- Validação de priority (1/2/3)
- Validação de due date (YYYY-MM-DD)

## Não-objetivos (fora de escopo)

- Editar tasks in-place (só via review queue)
- TUI web (Studio LangGraph continua quebrado)
- Sync com taskwarrior / calendar (já tem adapters)
- Migração das 770 tasks do backup (decisão do usuário)

## Critério de done

- [x] Spec escrita
- [ ] taskdog_cli.py com add/done/update + tests
- [ ] src/bin/td entry point
- [ ] pyproject.toml atualizado
- [ ] tests/test_m151_td_cli.py 100% PASS
- [ ] tui module funcional
- [ ] Commit + push

## Risco

**Baixo.** `apply_change` já é testado (M148). `enqueue` já é
testado. Só adiciona nova camada de CLI por cima. Risco de quebrar
read-only é mínimo.
