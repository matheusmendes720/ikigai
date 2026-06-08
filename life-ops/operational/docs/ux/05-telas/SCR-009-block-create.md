# SCR-009 — Block Create (Form de Criação de Time Block)

**Comando:** `operational block create [period] [flags]`
**Arquivo renderizador:** `cli/commands/block_cmd.py:22-52`
**Arquivo de comando:** `src/operational/cli/commands/block_cmd.py`
**Tipo:** Form curto com 1 argumento posicional + 2 flags. Aceita modo não-interativo.
**Modo JSON:** Sim — `--json` retorna a entidade `TimeBlock` serializada.
**Validação:** Pydantic v2 via factory `make_time_block` (`meta/factories.py:67-107`) → `TimeBlock` (`entities/time_block.py:41`) com validator `_validate_times` (end > start).

## Propósito

Registrar um **time block** (intervalo de tempo calendarizado) para tracking de atividade ad-hoc (PRD-01 §2). Diferente de **Routine** (que é planejada e recorrente), um **TimeBlock** é **o que de fato aconteceu** num intervalo: "das 14h00 às 14h50 estudei ENEM matemática". Valor gerado:

- Alimenta o **dashboard diário** (lista de blocos do dia).
- Habilita o **cálculo de hardwork realizado** vs. orçado (comparação com `DayContext.hardwork_orcado_min`).
- Permite **check-ins retroativos** de energia/foco acoplados a um intervalo (`metric energy --block <id>`).
- É a **âncora temporal** de pomodoros, routine_logs e ajustes finos.

## Usuário-alvo

- **Primário:** practitioner PAV que quer registrar **o que fez** em janelas de tempo (especialmente tarde — período CORE/hardwork).
- **Momento de uso:** tipicamente **retroativo** — você cria o bloco depois de fazer a atividade, ou durante (em pausas de 1min). Não é cadastro em massa; é 3-6 blocos por dia.
- **Frequência:** alta (3-6× por dia). É a "moeda" do tracking.

## Entradas

- **Do Home Menu:**
  - Opção `1` (Manhã) — `home.py:186` chama `["block", "create", "MANHA", "--label", label]`.
  - Opção `2` (Tarde) — `home.py:204` chama com `TARDE`.
  - Opção `3` (Noite) — `home.py:235` chama com `NOITE` e label "Preparação + Jantar".
- **Comando direto:** `operational block create TARDE --label "Deep work — features"`.
- **Auto-trigger:** o command `metric energy` (sem `--block`) **cria um bloco instantâneo de 1 segundo** automaticamente (`metric_cmd.py:181-191`). É um side-effect, não um auto-trigger do block.

## Saídas

- **Persiste em:** `time_blocks.json` (via `cli.state.time_blocks`).
- **Confirmação:** duas linhas — `✓ Bloco criado: <label>` + `id: blk_... · start → end` (`block_cmd.py:46-52`).
- **Redireciona:** volta ao shell / menu. Sem próximo passo sugerido.

## Modos de uso

### Modo 1: Flags (não-interativo)

```bash
operational block create TARDE --label "Deep work — features"
# Bloco criado com start=now, end=now+1h, period=TARDE
# Saída:
#   ✓ Bloco criado: Deep work — features
#   id: blk_20260608_141000  ·  2026-06-08T14:10:00 → 2026-06-08T15:10:00
```

### Modo 2: Mínimo (só argumento posicional)

```bash
operational block create NOITE
# Cria bloco NOITE vazio (label=""), start=now, end=now+1h
```

### Modo 3: Vinculado a rotina

```bash
operational block create TARDE --label "Workout" --routine rou_20260608_064200
# Cria bloco linkado a uma rotina pré-existente
# Útil para alinhar blocos "executados" com rotinas "planejadas"
```

### Modo 4: JSON

```bash
operational block create TARDE --label "Test" --json
# Saída: {"id": "blk_...", "label": "Test", "start": "...", "end": "...", "period": "TARDE", ...}
```

> **⚠ Atenção:** o command **não tem prompts**; é puramente flag-driven. A interatividade (perguntar label) está no flow do menu, não no command.

## Argumentos e flags (TODOS)

| Parâmetro | Tipo | Default | Obrigatório | Validação Pydantic | Exemplo |
|---|---|---|---|---|---|
| `period` | `Period` (enum) | `MANHA` | não (Argument) | enum strict | `TARDE` |
| `--label`, `-l` | str | `""` | não (Option) | `max_length=100` (entity) | `"Deep work"` |
| `--routine`, `-r` | str (UEID) | `None` | não (Option) | `Optional[UEID]`; sem validação de existência | `rou_20260608_064200` |
| `--json` | bool | `False` | não (Option) | — | — |

**Start / End (automáticos):**

A factory `make_time_block` (`meta/factories.py:67-107`) define:

```python
now = datetime.now(UTC)
s = start or now                    # start = agora
e = end or (s + timedelta(hours=1)) # end = agora + 1h
```

Ou seja, o command **sempre cria blocos "agora + 1h"** se você não passar nada. Para janelas retroativas, é preciso editar o JSON ou usar override via factory (não exposto na CLI).

**Validação cruzada (`model_validator` em `entities/time_block.py:83-100`):**

```python
@model_validator(mode="after")
def _validate_times(self) -> "TimeBlock":
    if self.end <= self.start:
        raise ValueError("end must be > start")
    return self
```

> **⚠ Atenção:** blocos **podem cruzar meia-noite** (não há restrição — diferente de `Routine`). `22:00 → 02:00` é válido para "Madrugada de sono" se você modelar assim.

## Wireframe passo-a-passo

### Estado: Criação bem-sucedida via comando direto

```
$ operational block create TARDE --label "Deep work — features"

╭─ Input Summary ─────────────────────────────╮
│  Criando time block                          │
│    period    : TARDE                         │
│    label     : Deep work — features          │
│    routine_id: —                             │
╰──────────────────────────────────────────────╯
  ✓ Bloco criado: Deep work — features
    id: blk_20260608_141000  ·  2026-06-08T14:10:00 → 2026-06-08T15:10:00
```

### Estado: Invocação via Home Menu (flow Tarde)

```
# _flow_afternoon() em home.py:203-204:
? Label do bloco da tarde [Deep Work — Features]: Deep Work — Features
$ operational block create TARDE --label "Deep Work — Features"
  ✓ Bloco criado: Deep Work — Features
    id: blk_20260608_141000  ·  2026-06-08T14:10:00 → 2026-06-08T15:10:00
```

### Estado: Sem label (aceita, mas vira "sem label" no list)

```bash
$ operational block create NOITE
  ✓ Bloco criado: (sem label)
    id: blk_20260608_210000  ·  2026-06-08T21:00:00 → 2026-06-08T22:00:00
```

No `block list`, blocos sem label aparecem como `(sem label)` em cinza (`block_cmd.py:101`).

### Estado: Erro — `--routine` aponta para UEID inexistente

```bash
$ operational block create TARDE --label "Test" --routine rou_inexistente
# O command NÃO valida a existência da rotina!
  ✓ Bloco criado: Test
    id: blk_20260608_141000  ·  2026-06-08T14:10:00 → 2026-06-08T15:10:00
# O bloco é criado com routine_id="rou_inexistente" no JSON.
# O dashboard depois vai mostrar link quebrado.
```

> **⚠ Atenção:** `routine_id` é `str | None` no command (`block_cmd.py:26`) e validado pelo Pydantic da entity como `Optional[UEID]` (regex pattern), mas **não há lookup** no repositório. Aceita qualquer string no formato `^[a-z]{3,5}_[a-z0-9_]+$` (`types.py:74-80`).

### Estado: Período inválido

```bash
$ operational block create MADRUGADA
# Typer: invalid value: 'MADRUGADA' for 'Period'; must be MANHA, TARDE, or NOITE
# Exit code: 2
```

## Validação e erros

| Cenário | Comportamento | Onde é validado |
|---|---|---|
| `period` inválido | Typer `BadParameter` antes de rodar | Typer binding |
| `label` >100 chars | Pydantic `max_length=100` rejeita | `entities/time_block.py` |
| `--routine` formato errado | Pydantic `UEID` regex rejeita (`^[a-z]{3,5}_[a-z0-9_]+$`) | construtor |
| `--routine` ID válido mas inexistente | **Aceito sem erro** (sem lookup) | gap |
| `start == end` (zero duration) | `model_validator` rejeita | `entities/time_block.py:83-100` |
| `start > end` | idem | idem |
| Bloco cruzando meia-noite | Aceito (sem restrição explícita) | n/a |

## Estados (5)

| Estado | Notas |
|---|---|
| **Vazio** | Não aplicável — `period` tem default `MANHA`; sempre há argumento |
| **Loading** | Não aplicável — operação síncrona |
| **Com dados (sucesso)** | Wireframe "Criação bem-sucedida" |
| **Erro de validação** | Período inválido, label >100, start >= end |
| **Cancelamento (Ctrl+C)** | Nada persistido se a factory não rodou |

## Comportamento interativo

- **Tipo de prompt:** nenhum no command. Toda entrada é via Argument/Option.
- **Validação inline:** Typer (enums) + Pydantic (ranges, formats) em duas camadas.
- **Defaults:** `period=MANHA`, `label=""`, `routine_id=None`, `start=now`, `end=now+1h`.
- **Histórico:** não aplicável.
- **Ctrl+C:** sai com `KeyboardInterrupt`; nada persistido.
- **Ctrl+D:** mesma rota.
- **Timeout:** não há.

## Comportamento especial: blocos automáticos

O command `metric energy` **sem `--block`** cria um bloco instantâneo de 1 segundo para registrar check-in (`metric_cmd.py:181-191`):

```python
new_block = TimeBlock(
    id=UEID(f"chk_{now.strftime('%Y%m%d_%H%M%S')}"),
    label="Check-in energia/foco",
    start=now, end=now + timedelta(seconds=1),
    period=period, energia_nivel=energia, foco_nivel=foco,
    created_at=now,
)
```

> **⚠ Atenção:** esses blocos `chk_*` aparecem no `block list` e contam para o "tempo total" do dia (apenas 1 segundo, mas poluem a lista). Filtre com `--label` em versões futuras, ou ignore visualmente.

## Comandos relacionados

- `block list` — Rich Table de todos os blocos, ordenados por data + start (`block_cmd.py:55-107`).
- `block list --period TARDE` — filtra por período.
- `block list --json` — saída estruturada.
- `metric energy --block <id>` — atualiza energia/foco de um bloco existente (`metric_cmd.py:163-178`).
- `state show` — dashboard que lista blocos do dia.

> **Gap conhecido:** não há `block update`, `block delete` ou `block archive`. Edição requer editar JSON ou criar+deletar manualmente.

## Riscos de usabilidade

Específicos deste form:

1. **Default `start=now, end=now+1h`** — se você cria um bloco "agora" para algo que **já acabou** (ex: já estudou das 14h-15h e são 15h30), o bloco fica errado. **Não há como cadastrar bloco retroativo via CLI** — o command sempre usa `datetime.now()`.
2. **Sem flag `--start`/`--end`** — o entity `TimeBlock` aceita start/end arbitrários, mas o command não expõe. Usuário avançado precisa de override via factory ou edição manual.
3. **Sem validação de `--routine`** — aceita UEID inexistente. Usuário pode linkar bloco a rotina "fantasma" sem aviso.
4. **Blocos automáticos `chk_*`** poluem `block list`. Podem ser confundidos com blocos reais.
5. **Default `period=MANHA`** é arbitrário — se você esquece de passar, o bloco é MANHA mesmo sendo de noite.
6. **Label default `""` (vazio)** é comum em testes mas em produção vira "bloco anônimo" no dashboard. Usuário precisa lembrar de passar `--label`.
7. **Sem agrupamento por data explícita** — `block list` agrupa implicitamente por data (`block_cmd.py:74`), mas blocos criados à meia-noite podem aparecer no dia errado dependendo do fuso.

## Métricas de sucesso

- **Tempo médio de cadastro:** target <5s (label curto + Enter).
- **Taxa de uso do Home Menu flow vs. CLI direta:** target 60% flow / 40% direto. (Flows do menu já montam o `period` e pedem label; CLI direta é para power users.)
- **Taxa de blocos com label:** target >80% (vs. blocos anônimos).

## Onde aparece

- **Home Menu opção `1` (Iniciar Manhã)** — `home.py:185-186`: prompt "Label do bloco da manhã" + `block create MANHA --label X`.
- **Home Menu opção `2` (Iniciar Tarde)** — `home.py:203-204`: idem para `TARDE` com default "Deep Work — Features".
- **Home Menu opção `3` (Encerrar Dia)** — `home.py:235`: `block create NOITE --label "Preparação + Jantar"` (sem prompt, label hardcoded).
- **Command `metric energy` (check-in rápido)** — cria bloco `chk_*` automaticamente (`metric_cmd.py:181-191`).

## Notas de implementação

- **File:line refs:**
  - `cli/commands/block_cmd.py:22-52` — definição do command `create`.
  - `cli/commands/block_cmd.py:30-34` — `maybe_print_input_summary`.
  - `cli/commands/block_cmd.py:36-41` — chamada da factory `make_time_block` + `time_blocks.upsert(block)`.
  - `meta/factories.py:67-107` — `make_time_block()` com defaults.
  - `entities/time_block.py:41` — classe `TimeBlock` (Pydantic v2, `frozen=True`).
  - `entities/time_block.py:83-100` — `_validate_times` (end > start).
- **Como adicionar `--start`/`--end`:** adicionar `start: str = typer.Option(None, "--start", help="ISO datetime")` e parsear com `datetime.fromisoformat()`; passar para `make_time_block(start=parsed_start)`. A factory já aceita `start` e `end` como kwargs (`factories.py:71-72`).
- **Como adicionar validação de `--routine`:** após `block = make_time_block(...)`, fazer `existing = routines.get(routine_id); if existing is None: console.print("[red]Rotina não encontrada[/red]"); raise typer.Exit(1)`. O repositório `routines` é importável de `cli.state`.
- **Onde fica o estado após submit:** `cli/state.py:time_blocks`. O `id` é `blk_<YYYYMMDD>_<HHMMSS>` (timestamp do start).
