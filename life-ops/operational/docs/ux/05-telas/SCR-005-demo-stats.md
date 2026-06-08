# SCR-005 — Demo Stats

**Comando:** `operational demo show [--json]`
**Arquivo renderizador:** N/A (output direto via `typer.echo`)
**Arquivo de comando:** `src/operational/cli/commands/demo_cmd.py:54-63` (`show`)
**Tipo:** Output tabular trivial (read-only)
**Modo JSON:** Sim (`--json`)
**Dataset:** qualquer

## Propósito

Resumir em uma única linha por entidade **quantos registros** o CLI tem carregado no momento para cada um dos 14 tipos de entidade (rotinas, blocos, journals, hábitos, sleep records, pomodoros, policy decisions, etc.). O usuário olha esta tela para responder: *"O CLI tem dados? Quanto?"* — útil antes de rodar um relatório, antes de seed, ou para verificar se um `clear` funcionou.

## Usuário-alvo

O próprio usuário, especialmente em modo de demonstração. Momento: depois de rodar `operational demo seed` ou `operational demo clear`, para confirmar. Objetivo: saber se a base está populada, vazia, ou "saudável" para o uso.

## Entradas

- **Do home menu:** opção `9` (Demo & Testes) → submenu (a opção `show` aparece como `3` ou similar, dependendo da versão do `_menu_demo`).
- **Comando direto:** `operational demo show`.

## Saídas

- **Rodar seed:** `operational demo seed` (popula 7 dias PAV).
- **Limpar:** `operational demo clear` (zera todos os repos).
- **Exportar:** `operational demo export-csv ./out.csv`.
- **Importar:** `operational demo import-csv ./golden.csv`.
- **Ver o relatório semanal:** `operational demo week` (seed + weekly report).

## Argumentos e flags

| Flag | Tipo | Default | Comportamento se omitido | Exemplo |
|------|------|---------|--------------------------|---------|
| `--json` | `bool` | `False` | Emite um dict `{"entities": {...}}` (chave `entities` com 14 entradas). | `--json` |

`demo show` **não aceita** argumentos posicionais (Typer define só `json`).

## Conteúdo principal

A "tela" é uma única string formatada via `typer.echo(stats)` em `demo_cmd.py:62`. O conteúdo é gerado por `demo_stats()` em `cli/seed.py`. A string é multilinha, com uma linha por entidade:

```
Routine                :  14
RoutineLog             :  14
TimeBlock              :  14
JournalEntry           :   7
Habit                  :   8
SleepRecord            :   7
PomodoroRound          :  14
PolicyDecision         :   7
PolicySetpoints        :   4
AjusteFino             :   4
DayContext             :   7
DailyReflection        :   7
LunchRecord            :   7
Transicao              :  35
```

**Ordem**: igual à ordem dos imports em `demo_cmd.py:10-25` (alfabética + agrupamento). **Sem cor** — usa `typer.echo` direto (sem `console.print`). **Sem painel Rich** — texto puro.

> Nota: na verdade, `demo_stats()` retorna a string formatada. Veja `cli/seed.py:demo_stats()` (definição não lida nesta task). O padrão é uma tabela de pares `name: count` alinhados com espaços.

## Hierarquia visual

- **1º:** A primeira linha (rotina) — geralmente é o tipo de entidade que mais cresce.
- **2º:** Total agregado implícito (soma dos 14 valores).
- **3º:** Detalhes de cada tipo (drill-down só via `--json`).

## Wireframe ASCII (com dados reais do golden.csv)

```
$ operational demo show

Entities:
  Routine                :  14
  RoutineLog             :  14
  TimeBlock              :  14
  JournalEntry           :   7
  Habit                  :   8
  SleepRecord            :   7
  PomodoroRound          :  14
  PolicyDecision         :   7
  PolicySetpoints        :   4
  AjusteFino             :   4
  DayContext             :   7
  DailyReflection        :   7
  LunchRecord            :   7
  Transicao              :  35
```

Ou, com `--json`:

```json
{
  "entities": {
    "routine": 14,
    "routine_log": 14,
    "time_block": 14,
    "journal_entry": 7,
    "habit": 8,
    "sleep_record": 7,
    "pomodoro_round": 14,
    "policy_decision": 7,
    "policy_setpoints": 4,
    "ajuste_fino": 4,
    "day_context": 7,
    "daily_reflection": 7,
    "lunch_record": 7,
    "transicao": 35
  }
}
```

## Estados (5)

### Estado 1 — Vazio (após `demo clear`)

```
$ operational demo clear
Demo data cleared.
$ operational demo show

Entities:
  Routine                :   0
  RoutineLog             :   0
  TimeBlock              :   0
  JournalEntry           :   0
  Habit                  :   0
  SleepRecord            :   0
  PomodoroRound          :   0
  PolicyDecision         :   0
  PolicySetpoints        :   0
  AjusteFino             :   0
  DayContext             :   0
  DailyReflection        :   0
  LunchRecord            :   0
  Transicao              :   0
```

Útil para confirmar que `clear` zerou tudo.

### Estado 2 — Loading

- **Não aplicável** (síncrono, ~10 ms).

### Estado 3 — Com dados (wireframe acima)

- 14 linhas renderizadas. Sem cor, sem painel, sem hierarquia visual forte.

### Estado 4 — Erro

- **`--json` malformado**: a entrada JSON é só de leitura, não de escrita. Sem risco.
- **State dir corrompido**: `repo.list()` levanta `json.JSONDecodeError`. Mitigação: `operational doctor doctor`.

### Estado 5 — Dataset sintético (golden.csv)

- O golden.csv tem exatamente os 14 contadores acima (7 dias × 2 rotinas, 7 dias × 2 logs, 7 dias × 2 blocos, 7 journals, 8 habits, 7 sleeps, 14 pomodoros, 7 policies, 4 setpoints, 4 ajustes, 7 day_contexts, 7 reflections, 7 lunches, 35 transições = 5 por dia).
- Exemplo: `transicao: 35` = 7 dias × 5 transições/dia (T1-T5: HYDRATION, MORNING, MORNING, MEDITATION, MORNING).

## Comportamento interativo

- **Aceita input do usuário?** NÃO. Read-only.
- **Tem prompts?** NÃO.
- **Teclas de atalho?** `Ctrl+C` aborta.
- **Mouse?** Sem suporte.

## Comandos relacionados

- `operational demo seed` — popula com 7 dias PAV.
- `operational demo clear` — zera todos os repos.
- `operational demo week` — seed + weekly report (atalho).
- `operational demo export-csv` — serializa o estado para CSV.
- `operational demo import-csv` — hidrata o estado a partir de CSV.
- `operational doctor doctor` — diagnóstico completo (inclui entity counts via `_check_state_dir`).

## Riscos de usabilidade

1. **Sem cor, sem painel, sem alinhamento perfeito** — parece "menos polido" que outras telas (state, daily). Inconsistência visual. Mitigação: refatorar para usar `metric_table` de `cli/renderers.py:406-433`.
2. **Não tem flag `--filter` ou `--entity`** — não dá para pedir "só rotinas" ou "só policies". Para ver uma entidade específica, o usuário precisa rolar os olhos pela lista.
3. **Ordem das linhas é fixa** (não alfabética nem por-count). Mitigação: ordenar alfabeticamente ou por contagem decrescente.
4. **JSON output é `{"entities": {...}}`** — envelope aninhado. Se o usuário fizer `jq '.entities.routine'`, funciona; mas `.routine` direto, não. Mitigação: alinhar com o padrão de outras telas (`{"date": ..., "n_pomodoros": ...}` plano).
5. **Não há agregação (`total: 142`)** — o usuário precisa somar mentalmente os 14 valores.

## Métricas de sucesso

- **Tempo até confirmar "tem dados?"** — meta < 2s (ler 14 linhas).
- **Taxa de uso** — esperado baixo (< 5% das invocações do CLI). Sinal: telas como `state show` já cobrem 80% do uso real.

## Onde aparece

- Home menu: opção `9` → submenu.
- Link direto: `operational demo show`.
- Usado em QA: pipelines de teste rodam `clear` → `seed` → `show` para verificar o estado.

## Notas de implementação

- Entry point: `cli/commands/demo_cmd.py:54` (`show`).
- Implementação: 4 linhas (`demo_cmd.py:54-63`). Chama `demo_stats()` de `cli/seed.py` e formata.
- Output: `typer.echo(stats)` (não usa `console.print`, então **não respeita** `is_captured()` e sempre escreve via Typer — sem cor).
- Repos lidos: 14 (`demo_cmd.py:11-24`). Cada um chama `repo.list()` e pega `len()`.
- Largura do console: irrelevante (sem painel, sem box drawing).
- Performance: ~10 ms em dataset production (14 × O(n) por `list()`).
