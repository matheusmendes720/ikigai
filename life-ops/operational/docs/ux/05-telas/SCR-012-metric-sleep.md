# SCR-012 — Metric Sleep Form (Registro de Sono)

**Comando:** `operational metric sleep [flags]`
**Arquivo renderizador:** `cli/commands/metric_cmd.py:58-94`
**Arquivo de comando:** `src/operational/cli/commands/metric_cmd.py`
**Tipo:** Form com 5 flags numéricas + 1 flag de data. Aceita modo não-interativo. Invocado também pelo Home Menu flow da manhã.
**Modo JSON:** Sim — `--json` retorna a entidade `SleepRecord` serializada.
**Validação:** Pydantic v2 via factory `make_sleep_record` (`meta/factories.py:165-201`) → `SleepRecord` (`entities/metric.py:101`) com validator de `quality_score ∈ [1,10]` e `duration_hours` com midnight crossing.

## Propósito

Registrar uma **SleepRecord** (PRD-05 §2.1) — uma noite de sono retroativa com horário de dormir, acordar, qualidade auto-reportada (1-10), e flag de "data a que pertence" (tipicamente a data do acordar). É o **input de边界 (boundary)** do dia: delimita início e fim de cada ciclo de 24h. Valor gerado:

- Alimenta o **sleep panel do dashboard diário** (`state show`).
- Habilita cálculo de **duração** (`duration_hours` com midnight crossing).
- Correlaciona com **energy/focus** (sleep ruim → energy baixa).
- Define o **bedtime ideal** para a rotina de noite (policy de PUSH/RECOVER).

## Usuário-alvo

- **Primário:** practitioner PAV que acorda e **imediatamente** registra sono (em 30s).
- **Momento de uso:** **ao acordar** (manhã) — preenche qualidade + horários enquanto lembra; ou **à noite** (antes de dormir) se for dormir "agora" e quiser logar.
- **Frequência:** 1× por dia, obrigatória para o `report daily` fazer sentido.

## Entradas

- **Do Home Menu:** opção `1` (Iniciar Manhã) faz 5 prompts em sequência (`home.py:170-179`):
  1. Qualidade (1-10) → `metric sleep -q X`
  2. Hora dormiu (0-23) → `-bh X`
  3. Minuto dormiu (0-59) → `-bm X`
  4. Hora acordou (0-23) → `-wh X`
  5. Minuto acordou (0-59) → `-wm X`
- **Comando direto:** `operational metric sleep --quality 8 --bed-hour 23 --bed-minute 30 --wake-hour 6 --wake-minute 30`.
- **Auto-trigger:** nenhum.

## Saídas

- **Persiste em:** `sleep_records.json` (via `cli.state.sleep_records`).
- **Confirmação:** `✓ Sono registrado: <id>` + linha dim com data, Q, emoji, label, duração (`metric_cmd.py:93-94`).
- **Redireciona:** volta ao shell / menu.

## Modos de uso

### Modo 1: Flags (não-interativo) — flow da manhã

```bash
operational metric sleep -q 8 -bh 23 -bm 30 -wh 6 -wm 30
# Saída:
#   ✓ Sono registrado: sle_2026_06_08
#   data: 2026-06-08  ·  Q=8/10 🟢 bom  ·  7.0h
```

### Modo 2: Data retroativa (registrar sono de 2 dias atrás)

```bash
operational metric sleep --date 2026-06-06 --quality 6 --bed-hour 1 --bed-minute 0 --wake-hour 8 --wake-minute 15
# Cria entry com date=2026-06-06, id=sle_2026_06_06
# Útil se você esqueceu de logar ontem
```

> **⚠ Atenção:** `duration_hours` lida com **midnight crossing** automaticamente: se `wake_hour < bed_hour`, adiciona 1 dia à wake datetime. `bed=23:00, wake=06:00` → 7.0h. `bed=01:00, wake=08:00` → 7.0h. `bed=00:30, wake=23:00` → NÃO é tratado como "dormiu 22.5h" — é apenas 22.5h, mas validação permite. Fique atento.

### Modo 3: Defaults (mínimo — usa 23:00→07:00, Q=8)

```bash
operational metric sleep
# Defaults: quality=8, bed=23:00, wake=07:00
# Útil em testes; arriscado em produção (você está assumindo dormiu 8h e qualidade 8)
```

### Modo 4: JSON

```bash
operational metric sleep -q 9 -bh 22 -bm 0 -wh 6 -wm 0 --json
# Saída: {"id": "sle_...", "date": "2026-06-08", "bedtime": "22:00:00", "wake_time": "06:00:00", "quality_score": 9, "duration_hours": 8.0, ...}
```

## Argumentos e flags (TODOS)

| Parâmetro | Tipo | Default | Obrigatório | Validação Pydantic | Exemplo |
|---|---|---|---|---|---|
| `--date`, `-d` | str (ISO) | hoje | não (Option) | `date.fromisoformat()` | `2026-06-08` |
| `--quality`, `-q` | int | `8` | não (Option) | Typer `min=1, max=10`; Pydantic `Field(ge=1, le=10)` | `8` |
| `--bed-hour`, `-bh` | int | `23` | não (Option) | Typer sem range; Pydantic `time(0-23)` | `23` |
| `--bed-minute`, `-bm` | int | `0` | não (Option) | Typer sem range; Pydantic `time(0-59)` | `30` |
| `--wake-hour`, `-wh` | int | `7` | não (Option) | Typer sem range; Pydantic `time(0-23)` | `6` |
| `--wake-minute`, `-wm` | int | `0` | não (Option) | Typer sem range; Pydantic `time(0-59)` | `30` |
| `--json` | bool | `False` | não (Option) | — | — |

> **⚠ Atenção:** `--bed-hour` e `--wake-hour` **não têm `min/max` no Typer** (`metric_cmd.py:62-65`). Se você passar `--bed-hour 25`, o `time(25, 0)` vai levantar `ValueError` no Python, não no Typer. Mensagem: `hour must be in 0..23`.

> **⚠ Atenção:** `--bed-minute` e `--wake-minute` idem. `time(8, 70)` → `ValueError: minute must be in 0..59`.

## Wireframe passo-a-passo

### Estado: Criação bem-sucedida via flow da manhã

```
# _flow_morning() em home.py:170-179:
? Qualidade do sono (1-10) [8]: 8
? Hora que dormiu (0-23) [20]: 23
? Minuto que dormiu (0-59) [30]: 30
? Hora que acordou (0-23) [4]: 6
? Minuto que acordou (0-59) [0]: 30

# Internamente:
$ operational metric sleep -q 8 -bh 23 -bm 30 -wh 6 -wm 30

╭─ Input Summary ──────────────────────────────╮
│  Registrando sono                             │
│    date    : 2026-06-08                        │
│    quality : 8                                 │
│    bedtime : 23:30                             │
│    wake    : 06:30                             │
╰───────────────────────────────────────────────╯
  ✓ Sono registrado: sle_2026_06_08
    data: 2026-06-08  ·  Q=8/10 🟢 bom  ·  7.0h
```

Note: o flow passa `-bh 20` como default (não 23). Bug ou decisão? **Decisão consciente** — assume que o usuário foi dormir 20:00 (jantou cedo, shutdown às 19h30). Mas é contraintuitivo; o default do command é 23.

### Estado: Criação via comando direto (verbose)

```
$ operational metric sleep --quality 9 --bed-hour 22 --bed-minute 0 --wake-hour 6 --wake-minute 0

  ✓ Sono registrado: sle_2026_06_08
    data: 2026-06-08  ·  Q=9/10 🟢 excelente  ·  8.0h
```

### Estado: Listagem pós-registro (`metric list`)

```
╭─── 😴 Sleep Records (5) ──────────────────────────────────────╮
│ Data        Dormiu  Acordou  Duração  Qualidade       Notas  ID
│ ─────────────────────────────────────────────────────────────
│ 2026-06-08  22:00   06:00    8.0h     🟢 9 excelente          sle_...
│ 2026-06-07  23:30   06:30    7.0h     🟢 8 bom                sle_...
│ 2026-06-06  01:00   05:00    4.0h     🟠 4 hardcore           sle_...
│ ...
╰──────────────────────────────────────────────────────────────╯
```

### Estado: Erro — quality fora do range

```bash
$ operational metric sleep --quality 11
# Typer: Invalid value for '--quality': 11 is not in the range 1 <= x <= 10
# Exit code: 2
```

### Estado: Erro — bed-hour inválido (Typer não pega!)

```bash
$ operational metric sleep --bed-hour 25
# ValueError: hour must be in 0..23
# (vem do time(25, 0) no Python)
# Exit code: 1
# Mensagem técnica, não PT-BR
```

> **⚠ Atenção:** diferente de `--quality`, as flags de hora/minuto **não têm validação Typer**. A validação é Pydantic, com mensagem técnica. Inconsistência UX-rugosa.

### Estado: Erro — data malformada

```bash
$ operational metric sleep --date "hoje"
# ValueError: Invalid isoformat string: 'hoje'
# Exit code: 1
```

## Validação e erros

| Cenário | Comportamento | Onde é validado |
|---|---|---|
| `--quality` <1 ou >10 | Typer `min/max` rejeita com mensagem em inglês | `metric_cmd.py:61` |
| `--bed-hour` 0-23 OK | `time(0-23)` aceita | Pydantic stdlib `time` |
| `--bed-hour` <0 ou >23 | `ValueError: hour must be in 0..23` (técnico) | Pydantic stdlib `time` |
| `--bed-minute` 0-59 OK | `time(0-59)` aceita | idem |
| `--bed-minute` <0 ou >59 | `ValueError: minute must be in 0..59` (técnico) | idem |
| `--date` malformado | `date.fromisoformat()` raise `ValueError` | `metric_cmd.py:69` |
| `wake < bed` (mesma noite) | Aceito, `duration_hours` calcula com midnight crossing | `metric.py:duration_hours` |
| `wake == bed` (zero duração) | **Aceito** (sem validação explícita de duração mínima) | gap |
| Duração absurda (e.g. 22h) | Aceito (sem range check) | gap |
| Sleep duplicado (mesmo date) | `sleep_records.upsert()` substitui | `state.py:upsert` |

## Estados (5)

| Estado | Notas |
|---|---|
| **Vazio** | Não aplicável — todas as flags têm default; pode rodar sem nenhum input |
| **Loading** | Não aplicável |
| **Com dados (sucesso)** | Wireframe "Criação bem-sucedida" |
| **Erro de validação** | Quality fora de 1-10, hora >23, minuto >59, data malformada |
| **Cancelamento (Ctrl+C)** | Nada persistido |

## Comportamento interativo

- **Tipo de prompt:** nenhum no command. Toda entrada é via flags.
- **Validação inline:** Typer (apenas `quality`); Pydantic + stdlib `time` para o resto.
- **Defaults:** `date=hoje, quality=8, bed=23:00, wake=07:00`. **Cuidado:** se você aceita todos os defaults, está mentindo — está dizendo que dormiu 23:00→07:00 com qualidade 8.
- **Histórico:** não aplicável.
- **Ctrl+C:** nada persistido.
- **Ctrl+D:** mesma rota.
- **Timeout:** não há.

## Comportamento especial: emoji + label de qualidade

A qualidade (1-10) é mapeada para emoji + label pelo command (`metric_cmd.py:34-55`):

| Score | Emoji | Label |
|---|---|---|
| 9-10 | 🟢 | excelente |
| 7-8 | 🟢 | bom |
| 5-6 | 🟡 | regular |
| 4 | 🟠 | hardcore |
| 1-3 | 🔴 | crítico |

> **⚠ Atenção:** a tabela é **redundante** — "9-10 excelente" e "7-8 bom" usam o mesmo emoji 🟢. Diferenciação é só no label e no score numérico.

## Comportamento especial: midnight crossing

O `duration_hours` é um computed field que lida com `wake < bed`:

```python
# entities/metric.py:duration_hours (resumido)
def duration_hours(self) -> float:
    bed_dt = datetime.combine(self.date, self.bedtime)
    wake_dt = datetime.combine(self.date, self.wake_time)
    if wake_dt < bed_dt:
        wake_dt += timedelta(days=1)
    return (wake_dt - bed_dt).total_seconds() / 3600
```

> **⚠ Atenção:** se `bed=00:30` e `wake=23:00` **no mesmo date**, a entity computa duração de 22.5h (correto se você dormiu 1 madruga e acordou 23h do mesmo "dia civil"). Mas se você acordar no dia **seguinte** (e.g. dormiu 00:30 e acordou 06:00 do outro dia), precisa passar `--date` do dia do acordar. Ex: `bed=00:30` em 2026-06-07, `wake=06:00` em 2026-06-08 → `date=2026-06-08`, `bed_hour=0, bed_minute=30, wake_hour=6, wake_minute=0`. Sistema trata como "8h dormido em 2026-06-08".

## Comandos relacionados

- `metric list` — Rich Table de todos os sleep records (`metric_cmd.py:97-142`).
- `metric energy -e X -f Y` — check-in de energia/foco (vinculável a um bloco via `--block`).
- `state show` — dashboard que mostra último sleep + summary.
- `report daily` — relatório que inclui sleep no panel de cabeçalho.
- `reflect entrada` — OKR V3 que referencia "sono de ontem".

> **Gap conhecido:** não há `metric sleep update` (precisa rodar com mesmo `--date` para UPSERT); não há `metric sleep delete`. Edição requer edição de JSON.

## Riscos de usabilidade

Específicos deste form:

1. **6 flags numéricas** — `--quality`, `--bed-hour`, `--bed-minute`, `--wake-hour`, `--wake-minute`, `--date`. **Fadiga de flags**: usuário pode esquecer `-bh` vs `-wh`, ou `-bm` vs `-wm`. Mitigação: o Home Menu flow já quebra em 5 prompts sequenciais.
2. **Inconsistência de validação Typer** — `quality` tem `min/max` (mensagem clara em inglês); `bed-hour` etc. não têm (mensagem técnica do Python). Inconsistência confunde.
3. **Default `bh=20` no flow da manhã, `bh=23` no command** — duas "verdades" para o mesmo campo. Bug ou decisão? Provavelmente bug: o `home.py:171` foi escrito assumindo "20h" como bedtime saudável (jantar cedo, 19h30), enquanto o `metric_cmd.py:62` usa 23h como default. **Esclarecer em refactor futuro**.
4. **Sem confirmação visual antes de gravar** — flags são executadas direto. Se você digita `-q 8 -bh 23 -bm 30 -wh 6 -wm 30` e aperta Enter, o sleep é gravado. Sem "preview".
5. **Sem cálculo de duração preview** — você só vê `7.0h` **após** gravar, não antes. Para "seria 7h?", precisa calcular mentalmente.
6. **Aceita duração absurda** — 22h de sono é aceito (e.g. `bed=00:30, wake=22:30` no mesmo date). Não há range check em `duration_hours`.
7. **Mensagens de erro em inglês** — `ValueError: hour must be in 0..23` é do stdlib, não localizada.
8. **Múltiplas noites "overlap"** — se você dormiu 22:00→06:00 em 2026-06-08 e **tirou um cochilo** 14:00→15:00 no mesmo dia, ambos os records usam `date=2026-06-08`. O sistema **não distingue** sono noturno de cochilo. `duration_hours` de 8h + 1h = 9h "dormidos" no dia, sem flag de tipo.

## Métricas de sucesso

- **Tempo médio de registro via flow da manhã:** target <30s (5 prompts + Enter em cada).
- **Taxa de erro de validação:** target <5%.
- **Cobertura (dias com sleep logado / total de dias):** target >90%. Se <70%, o flow está com friction demais.

## Onde aparece

- **Home Menu opção `1` (Iniciar Manhã)** — `home.py:170-179`: 5 prompts sequenciais + `_run_cmd(["metric", "sleep", "-q", q, "-bh", bh, "-bm", bm, "-wh", wh, "-wm", wm])`.
- **Não aparece** nas opções `2` (Tarde) ou `3` (Noite) — assume que o sleep foi logado de manhã.

## Notas de implementação

- **File:line refs:**
  - `cli/commands/metric_cmd.py:58-94` — definição do command `sleep`.
  - `cli/commands/metric_cmd.py:69` — `date.fromisoformat(record_date) if record_date else date.today()`.
  - `cli/commands/metric_cmd.py:81-86` — chamada da factory `make_sleep_record` + `sleep_records.upsert(record)`.
  - `meta/factories.py:165-201` — `make_sleep_record()` com defaults `23:00, 07:00, quality=8`.
  - `entities/metric.py:101` — classe `SleepRecord` (Pydantic v2, `frozen=True`).
  - `entities/metric.py:duration_hours` — computed field com midnight crossing.
  - `metric_cmd.py:34-55` — helpers `_sleep_emoji` e `_sleep_label`.
- **Como adicionar `--deep-sleep-pct`:** adicionar `deep_sleep_pct: float | None = typer.Option(None, "--deep", min=0.0, max=100.0)` e passar como override para `make_sleep_record`.
- **Como adicionar `--source`:** adicionar `source: Literal["MANUAL", "GARMIN", "OURA", "APPLE_HEALTH"] = typer.Option("MANUAL", "--source")` (entity já tem o campo).
- **Onde fica o estado após submit:** `cli/state.py:sleep_records`. O `id` é `sle_YYYY_MM_DD` (factory, `factories.py:190`) — **mesmo date = mesmo id = UPSERT**.
- **Refactor sugerido:** alinhar defaults do `home.py:171` (`bh=20`) com `metric_cmd.py:62` (`bh=23`). Provavelmente decisão era "wake=4h" → acordei muito cedo; ajustar.
