# SCR-008 — Routine Create (Form de Criação de Rotina)

**Comando:** `operational routine create [name] [period] [type] [flags]`
**Arquivo renderizador:** `cli/commands/routine_cmd.py:41-82` (sem renderizador externo; usa `make_console` direto)
**Arquivo de comando:** `src/operational/cli/commands/routine_cmd.py`
**Tipo:** Form com 3 argumentos posicionais + 4 flags de tempo. Aceita modo totalmente não-interativo (só flags) ou modo interativo quando invocado pelo Home Menu flow.
**Modo JSON:** Sim — `--json` retorna a entidade `Routine` serializada via `format_as_json`.
**Validação:** Pydantic v2 via factory `make_routine` (`meta/factories.py:28-64`) → construtor `Routine` (`entities/routine.py:80`) com validators `_validate_times` e `_validate_days_of_week`.

## Propósito

Registrar uma **rotina planejada** (PAV §3) — uma atividade recorrente atrelada a um período (MANHA/TARDE/NOITE) e a um tipo (ENTRY/CORE/TRANSITION/EXIT) com janela de tempo. Rotinas são o **esqueleto canônico de um dia típico**; blocos são o que de fato aconteceu; rotinas dizem o que **deveria** acontecer. Valor gerado:

- O dashboard diário compara rotinas planejadas vs. blocos executados → "estou no plano?".
- A política operacional usa rotinas ativas no dia para definir o regime (PUSH/MAINTAIN/...).
- O OKR V3 (Reflect) ancora "deu certo / deu errado" em rotinas cumpridas.

## Usuário-alvo

- **Primário:** practitioner PAV definindo a estrutura do próprio dia. Cadastra 3-8 rotinas fixas (ex: acordar 06:00-06:50, almoço 12:00-12:30, hardwork 14:00-17:00, shutdown 21:00-22:00).
- **Momento de uso:** setup inicial (uma vez) e ajustes pontuais (mudar horário de workout, adicionar meditação da tarde).
- **Frequência:** baixa-média — 1× por semana, talvez. Não é cadastro diário.

## Entradas

- **Do Home Menu:** opção `1` (Iniciar Manhã) invoca `routine create "Acordar" MANHA ENTRY` (`home.py:182`).
- **Comando direto:** `operational routine create "Morning workout" MANHA CORE --start-hour 6 --end-hour 7`.
- **Auto-trigger:** nenhum.

## Saídas

- **Persiste em:** `routines.json` no diretório de estado (via `cli.state.routines` — `InMemoryRepository` com auto-save).
- **Confirmação:** duas linhas — `✓ Rotina criada: <name> (<period> · <type>)` + linha `dim` com `id` e `start→end` (`routine_cmd.py:77-82`).
- **Redireciona:** volta ao shell / menu (sem próximo passo sugerido).

## Modos de uso

### Modo 1: Flags (não-interativo) — produção / scripts

```bash
operational routine create "Morning workout" MANHA CORE \
    --start-hour 6 --start-minute 0 \
    --end-hour 7 --end-minute 0
# Saída:
#   ✓ Rotina criada: Morning workout (MANHA · CORE)
#   id: rou_20260608_064200  ·  06:00:00→07:00:00
```

### Modo 2: Mínimo (só argumentos posicionais)

```bash
operational routine create "Lunch" TARDE TRANSITION
# Aceita defaults: start=06:00, end=06:50, period=TARDE, type=TRANSITION
# AVISO: defaults fazem o start/end ficarem descolados do "almoço" — útil só em testes.
```

### Modo 3: JSON (machine-readable)

```bash
operational routine create "Wake" MANHA ENTRY --start-hour 5 --end-hour 6 --json
# Saída: {"id": "rou_...", "name": "Wake", "period": "MANHA", ...}
```

> **Nota:** a invocação via Home Menu flow (`home.py:182`) é **não-interativa** — passa argumentos posicionais fixos. Os prompts da rotina (nome, período, tipo) **não existem no comando**; eles existem no flow do menu (`_flow_morning`, `_flow_afternoon`, `_flow_evening`) que monta os args antes de chamar `_run_cmd`.

## Argumentos e flags (TODOS)

| Parâmetro | Tipo | Default | Obrigatório | Validação Pydantic | Exemplo |
|---|---|---|---|---|---|
| `name` | str | (sem default) | **sim** (Argument) | `min_length=1, max_length=100` (`routine.py`) | `"Morning workout"` |
| `period` | `Period` (enum) | `MANHA` | não (Argument) | enum strict | `MANHA` \| `TARDE` \| `NOITE` |
| `routine_type` | `RoutineType` (enum) | `CORE` | não (Argument) | enum strict | `ENTRY` \| `CORE` \| `TRANSITION` \| `EXIT` |
| `--start-hour`, `-sh` | int | `6` | não (Option) | `0 ≤ x ≤ 23` | `6` |
| `--start-minute`, `-sm` | int | `0` | não (Option) | `0 ≤ x ≤ 59` | `30` |
| `--end-hour`, `-eh` | int | `6` | não (Option) | `0 ≤ x ≤ 23` | `7` |
| `--end-minute`, `-em` | int | `50` | não (Option) | `0 ≤ x ≤ 59` | `0` |
| `--json` | bool | `False` | não (Option) | — | — |

**Validação cruzada (`model_validator` em `entities/routine.py:162-178`):**

```python
@model_validator(mode="after")
def _validate_times(self) -> "Routine":
    if self.end_time <= self.start_time:
        raise ValueError("end_time must be > start_time")
    return self
```

> **⚠ Atenção:** rotinas **não cruzam meia-noite** — `23:00→01:00` é rejeitado. Para rotinas noturnas longas, use o dia seguinte (rotina de dormir com start 22:00 end 23:30).

## Wireframe passo-a-passo

### Estado: Criação bem-sucedida via comando direto

```
$ operational routine create "Morning workout" MANHA CORE \
    --start-hour 6 --end-hour 7

╭─ Input Summary ─────────────────────────────────────────────╮
│  Criando rotina                                             │
│    name        : Morning workout                            │
│    period      : MANHA                                      │
│    type        : CORE                                       │
│    start       : 06:00                                      │
│    end         : 07:00                                      │
╰─────────────────────────────────────────────────────────────╯
  ✓ Rotina criada: Morning workout (MANHA · CORE)
    id: rou_20260608_064200  ·  06:00:00→07:00:00
```

O "Input Summary" é renderizado por `maybe_print_input_summary` (`routine_cmd.py:53-63`) — só aparece se a flag `OPERATIONAL_INPUT_SUMMARY` ou similar estiver setada; em produção é silencioso.

### Estado: Invocação via Home Menu (flow Manhã)

```
# _flow_morning() em home.py:182:
$ operational routine create "Acordar" MANHA ENTRY
# Saída (mesma, mas com defaults 06:00→06:50):
  ✓ Rotina criada: Acordar (MANHA · ENTRY)
    id: rou_20260608_070200  ·  06:00:00→06:50:00
```

### Estado: Erro de validação (`end <= start`)

```bash
$ operational routine create "Bad" MANHA CORE --start-hour 8 --end-hour 8
# Pydantic ValidationError → typer.BadParameter:
╭─ Error ─────────────────────────────────────────────────────╮
│  ValueError: end_time must be > start_time                   │
│   start: 08:00, end: 08:00                                   │
╰─────────────────────────────────────────────────────────────╯
# Exit code: 1
```

> **⚠ Atenção:** o horário de fim é `--end-hour` (não `--end`). Se você esquecer `-eh` e usar `--end-hour 7` com `-sh 7`, dá erro de validação silenciosa (default `--end-hour=6`).

### Estado: Período inválido

```bash
$ operational routine create "Test" MADRUGADA CORE --start-hour 6 --end-hour 7
# Typer: invalid value: 'MADRUGADA' for 'Period'; must be MANHA, TARDE, or NOITE
# Exit code: 2
```

Typer valida enums **antes** do código Python rodar — erro vem como `BadParameter` com lista de opções válidas.

### Estado: Nome vazio (rejeitado por Pydantic)

```bash
$ operational routine create "" MANHA CORE --start-hour 6 --end-hour 7
# Pydantic: String should have at least 1 character
# Exit code: 1
```

> **⚠ Atenção:** Typer Argument com `name: str = typer.Argument(...)` **não tem validação Pydantic embutida** — o `min_length` é checado quando `Routine(...)` é construído na factory. A mensagem de erro vem de `pydantic.ValidationError` (mais verbosa).

## Validação e erros

| Cenário | Comportamento | Onde é validado |
|---|---|---|
| `name` vazio | Pydantic `min_length=1` rejeita | `entities/routine.py` construtor |
| `name` >100 chars | Pydantic `max_length=100` rejeita | idem |
| `period` inválido (não enum) | Typer `BadParameter` antes de rodar | Typer binding |
| `routine_type` inválido | Typer `BadParameter` antes de rodar | idem |
| `start_hour` fora de 0-23 | Pydantic `Field(ge=0, le=23)` rejeita | construtor |
| `start_minute` fora de 0-59 | Pydantic `Field(ge=0, le=59)` rejeita | idem |
| `end <= start` | `model_validator` rejeita com mensagem | `entities/routine.py:162-178` |
| `end == start` | idem (boundary é strict `>`) | idem |
| Horário cruzando meia-noite | Pydantic aceita `time(23, 30) → time(0, 30)`? **NÃO** — model_validator rejeita | idem |
| Routine duplicada (mesmo id) | `routines.upsert()` substitui (id é `rou_<timestamp>`, então colisão é improvável) | `state.py:upsert` |

## Estados (5)

| Estado | Notas |
|---|---|
| **Vazio** (sem dados) | Não aplicável — Typer exige `name`; sem nome não há command |
| **Loading** | Não aplicável — operação síncrona (in-memory dict + JSON dump) |
| **Com dados (sucesso)** | Wireframe "Criação bem-sucedida" acima |
| **Erro de validação** | Wireframe "end <= start" ou "Período inválido" acima |
| **Cancelamento (Ctrl+C)** | Não tratado no nível do command. Typer propaga `KeyboardInterrupt` → shell. Nada é persistido se a factory não chegou a chamar `routines.upsert`. |

## Comportamento interativo

- **Tipo de prompt:** este comando **não tem prompts** — todos os inputs vêm via Argument/Option. A "interatividade" do home menu é no flow, não no command.
- **Validação inline:** Typer faz em duas camadas: (1) parsing de tipos/enums antes do código rodar; (2) Pydantic na construção da entidade. Falhas em (1) saem com `BadParameter` (exit 2); falhas em (2) saem com `ValidationError` (exit 1).
- **Defaults:** Enter não existe (não há `Prompt.ask` no command). Defaults só se aplicam quando flag é omitida.
- **Histórico:** não aplicável.
- **Ctrl+C:** sai com `KeyboardInterrupt`; nada persistido.
- **Ctrl+D:** mesma rota.
- **Timeout:** não há.

## Comandos relacionados

- `routine list` — Rich Table de todas as rotinas, ordenadas por período e horário (`routine_cmd.py:85-143`).
- `routine list --period MANHA` — filtra por período.
- `routine list --json` — saída estruturada.
- `state show` — dashboard que mostra rotinas ativas hoje vs. blocos logados.
- `routine show <id>` — **não existe ainda**; o list é o único leitor atual.

> **Gap conhecido:** não há comando de update/soft-delete para rotinas. Para remover, edite `routines.json` direto ou use `routine list --json` + script externo.

## Riscos de usabilidade

Específicos deste form:

1. **Defaults pouco úteis** — `start=06:00, end=06:50` é um placeholder de teste, não um almoço. Esquecer `-sh/-eh` cria rotinas com horário arbitrário.
2. **Sem validação visual prévia** — Typer só reclama no `BadParameter` (exit 2). Não há preview "você está prestes a criar Manhã 06:00-06:50 — confirma?".
3. **Flags separadas para hora e minuto** — `--start-hour 6 --start-minute 0` é verboso vs. `--start 06:00`. Decisão consciente da arquitetura para evitar parsing de string; mas é UX-rugoso.
4. **Sem `days_of_week` na CLI** — o campo existe na entity (`routine.py:days_of_week: set[Weekday]`) e tem validator (`_validate_days_of_week`), mas o command não expõe flag para ele. **Não é possível cadastrar "rotina só de fim de semana"** via CLI; precisaria de override via factory ou editar JSON.
5. **Sem flag `--mandatory`/`--optional`** — entity tem `mandatory: bool = True`, mas a CLI assume sempre `True`. Para criar opcional, precisa de override.
6. **`--json` mistura erros humanos e máquinas** — se a validação falhar, `--json` ainda imprime o erro em texto (não em JSON). Consumidores piping precisam lidar com ambos.
7. **ID baseado em timestamp** — duas rotinas criadas no mesmo segundo colidem (`rou_20260608_064200`). Improvável em uso humano, mas possível em scripts.

## Métricas de sucesso

- **Tempo médio de cadastro via CLI direta:** target <10s (copy-paste de template).
- **Taxa de erro de horário (end < start):** target <5% após usuário conhecer o comando.
- **Uso via Home Menu flow vs. direto:** target 70% flow / 30% direto. (Setup é raro; ajustes pontuais são via CLI direta.)

## Onde aparece

- **Home Menu opção `1` (Iniciar Manhã)** — `home.py:182` chama `_run_cmd(["routine", "create", "Acordar", "MANHA", "ENTRY"])`.
- **Home Menu opção `2` (Iniciar Tarde)** — `home.py:206-207` chama com prompt "Nome da rotina CORE" + `TARDE`.
- **Home Menu opção `3` (Encerrar Dia)** — `home.py:232` chama `["routine", "create", "Shutdown Ritual", "NOITE", "EXIT"]`.
- **Home Menu sub-menu Dados → opções 6-9** — cadastros de rotinas pré-fabricadas (Morning, Deep Work, Shutdown, Wake Up).

## Notas de implementação

- **File:line refs:**
  - `cli/commands/routine_cmd.py:41-82` — definição do command `create`.
  - `cli/commands/routine_cmd.py:53-63` — `maybe_print_input_summary` (opcional).
  - `cli/commands/routine_cmd.py:65-72` — chamada da factory `make_routine` + `routines.upsert(routine)`.
  - `meta/factories.py:28-64` — `make_routine()` com defaults.
  - `entities/routine.py:80` — classe `Routine` (Pydantic v2, `frozen=True`, `extra="forbid"`).
  - `entities/routine.py:137-178` — validators (`_validate_days_of_week`, `_validate_times`).
- **Como adicionar uma nova flag:** declarar `flag: T = typer.Option(default, "--flag", "-f", help="...")` na assinatura de `create`, e passá-la em `make_routine(... flag=flag)`. A factory faz `**overrides` (`factories.py:36, 63`), então Pydantic aceita qualquer campo válido de `Routine`.
- **Como mudar validação Pydantic:** editar `entities/routine.py:137-178` (validators) ou os `Field(...)` no construtor. Mudanças impactam todos os 14 commands que dependem da entity.
- **Onde fica o estado após submit:** `cli/state.py:routines` (instância de `InMemoryRepository` com auto-save JSON). O `id` é `rou_<YYYYMMDD>_<HHMMSS>`.
