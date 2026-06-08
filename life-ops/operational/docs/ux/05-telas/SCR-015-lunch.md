# SCR-015 — Lunch Form (Registro de Almoço)

**Comando:** `operational lunch [flags]` (cria registro) ou `operational lunch list [flags]`
**Arquivo renderizador:** `cli/commands/lunch_cmd.py:24-53` (create) + `:56-88` (list)
**Arquivo de comando:** `src/operational/cli/commands/lunch_cmd.py`
**Tipo:** Form curto com 4 flags + 1 flag de data. Aceita modo não-interativo. **Não é invocado pelo Home Menu** — é invocação direta.
**Modo JSON:** Sim — `--json` retorna a entidade `LunchRecord` serializada.
**Validação:** Pydantic v2 em `entities/v3.py:164` (classe `LunchRecord`) com `Field(ge=0, le=120)` em `eat_min`, `Field(ge=0, le=180)` em `rest_min`, `max_length=300` em `notas`.

## Propósito

Registrar uma **LunchRecord** (PAV V3 §2) — o almoço do dia, que é uma **fronteira crítica** do dia PAV: o momento em que você quebra foco, come, descansa, e decide se volta em modo "leve" ou "pesado". Valor gerado:

- **Eat time** (5min ideal) + **rest time** (30min ideal) → calcula `duracao_total` e `within_budget`.
- Flag `pesado` correlaciona com **sonolência pós-almoço** (e cochilo além do orçamento de TARDE).
- Aparece no `report daily` como panel de cabeçalho (boundary TARDE).
- Alimenta o `AjusteFino` quando pesado + sono = "reduzir pomodoros TARDE".

## Usuário-alvo

- **Primário:** practitioner PAV que quer **rastrear a fronteira TARDE** (o que comeu, se descansou o suficiente, se comeu pesado).
- **Momento de uso:** **logo após almoçar** (registrar com fresh memory) ou **final do dia** (registrar retroativo).
- **Frequência:** 1× por dia. Comando curto → target <15s.

## Entradas

- **Do Home Menu:** **NÃO há flow dedicado** para lunch. O sub-menu Dados (opção `7`) **não** tem item de criar lunch. O flow Tarde (opção `2`) **não** chama `lunch create`. É invocação direta apenas.
- **Comando direto:** `operational lunch --eat 5 --rest 30` (mais comum).
- **Auto-trigger:** nenhum.

## Saídas

- **Persiste em:** `lunch_records.json` (via `cli.state.lunch_records`).
- **Confirmação:** 3 linhas — `Lunch <data>` + `eat=Xmin rest=Ymin total=Zmin (✓/✗ estourou)` + emoji `✅ OK` ou `⚠️ PESADO` (`lunch_cmd.py:51-53`).
- **Redireciona:** volta ao shell / menu.

## Modos de uso

### Modo 1: Flags (não-interativo) — uso comum

```bash
operational lunch --eat 5 --rest 30
# Saída:
# Lunch 2026-06-08
#   eat=5min  rest=30min  total=35min  (✓)
#   ✅ OK
```

### Modo 2: Pesado (digestão pesada)

```bash
operational lunch --eat 25 --rest 45 --pesado
# Saída:
# Lunch 2026-06-08
#   eat=25min  rest=45min  total=70min  (✗ estourou)
#   ⚠️ PESADO
```

> **⚠ Atenção:** `--pesado` é **flag booleano** (sem valor). `--pesado=true` também funciona, mas `--pesado` sozinho é o padrão. **Inconsistência** com `--json` e `--date` que tomam valores; mas é convenção de Typer/Click.

### Modo 3: Mínimo (aceita defaults)

```bash
operational lunch
# Defaults: eat=5, rest=30, pesado=False
# Útil em testes; arriscado em produção (você está assumindo almoço perfeito)
```

### Modo 4: Data customizada

```bash
operational lunch --date 2026-06-07 --eat 10 --rest 30
# Cria registro retroativo
```

### Modo 5: Com notas

```bash
operational lunch --eat 5 --rest 30 --notas "Salada + frango grelhado. Sem sobremesa."
# Notas livres (até 300 chars)
```

### Modo 6: JSON

```bash
operational lunch --eat 5 --rest 30 --json
# Saída: {"id": "lun_2026_06_08", "date": "2026-06-08", "eat_min": 5, "rest_min": 30, "pesado": false, ...}
```

## Argumentos e flags (TODOS)

| Parâmetro | Tipo | Default | Obrigatório | Validação Pydantic | Exemplo |
|---|---|---|---|---|---|
| `--date`, `-d` | str (ISO) | hoje | não (Option) | `date.fromisoformat()` | `2026-06-08` |
| `--eat`, `-e` | int | `5` | não (Option) | Typer `min=0, max=120`; Pydantic `Field(ge=0, le=120)` | `10` |
| `--rest`, `-r` | int | `30` | não (Option) | Typer `min=0, max=180`; Pydantic `Field(ge=0, le=180)` | `30` |
| `--pesado`, `-p` | bool | `False` | não (Option, sem valor) | — | `--pesado` (presença = True) |
| `--notas`, `-n` | str | `""` | não (Option) | Pydantic `max_length=300` | `"Salada + frango"` |
| `--json` | bool | `False` | não (Option) | — | — |

> **⚠ Atenção:** `--pesado` é flag **store_true** (presença = True). Para setar False explicitamente, basta omitir.

## Wireframe passo-a-passo

### Estado: Criação bem-sucedida — caso "ideal"

```
$ operational lunch --eat 5 --rest 30

Lunch 2026-06-08
  eat=5min  rest=30min  total=35min  (✓)
  ✅ OK
```

**Análise:**
- `eat=5` está dentro do budget (≤5min). `rest=30` está dentro (≤30min). Logo `within_budget=True` (✓).
- `pesado=False` (default). Emoji `✅ OK`.

### Estado: Criação bem-sucedida — caso "estourou + pesado"

```
$ operational lunch --eat 25 --rest 45 --pesado --notas "Feijoada"

Lunch 2026-06-08
  eat=25min  rest=45min  total=70min  (✗ estourou)
  ⚠️ PESADO
```

> **⚠ Atenção:** a saída **NÃO** chama `maybe_print_input_summary` (diferente de `routine create`, `block create`, etc.). É direto: 3 linhas de output. Mais conciso, mas menos "verbose" para auditoria.

### Estado: Listagem (`lunch list`)

```
$ operational lunch list
╭───────────────────────────────────────────────────────────────────╮
│ Data        Eat (min)  Rest (min)  Total  Pesado  Within budget  │
│ ────────────────────────────────────────────────────────────────
│ 2026-06-08  5          30          35min  -       ✓              │
│ 2026-06-07  25         45          70min  ⚠️      ✗              │
│ 2026-06-06  10         30          40min  -       ✗              │
╰───────────────────────────────────────────────────────────────────╯
```

### Estado: Erro — `eat` fora do range

```bash
$ operational lunch --eat 200
# Typer: Invalid value for '--eat': 200 is not in the range 0 <= x <= 120
# Exit code: 2
```

### Estado: Erro — `rest` fora do range

```bash
$ operational lunch --rest 300
# Typer: Invalid value for '--rest': 300 is not in the range 0 <= x <= 180
# Exit code: 2
```

### Estado: Erro — data malformada

```bash
$ operational lunch --date "sexta"
# ValueError: Invalid isoformat string: 'sexta'
# Exit code: 1
```

### Estado: Notas >300 chars

```bash
$ operational lunch --notas "$(python -c 'print("x"*301)')"
# Pydantic: String should have at most 300 characters
# Exit code: 1
```

## Validação e erros

| Cenário | Comportamento | Onde é validado |
|---|---|---|
| `--eat` <0 ou >120 | Typer `min/max` rejeita com mensagem em inglês | `lunch_cmd.py:27` |
| `--rest` <0 ou >180 | Typer `min/max` rejeita | `lunch_cmd.py:28` |
| `--date` malformado | `date.fromisoformat()` raise `ValueError` | `lunch_cmd.py:34` |
| `--notas` >300 chars | Pydantic `max_length=300` rejeita | `entities/v3.py:172` |
| `--pesado` parsing | Typer converte `--pesado` (presença) em `True`; omissão = `False` | `lunch_cmd.py:29` |
| `eat + rest` muito alto | Sem validação cross-field (e.g. 120 + 180 = 300min = 5h) | gap |
| Lunch duplicado (mesmo date) | `lunch_records.upsert()` substitui | `state.py:upsert` |

## Estados (5)

| Estado | Notas |
|---|---|
| **Vazio** | Não aplicável — todas as flags têm default |
| **Loading** | Não aplicável |
| **Com dados (sucesso)** | Wireframe "caso ideal" / "estourou + pesado" |
| **Erro de validação** | eat/rest fora do range, data malformada, notas >300 |
| **Cancelamento (Ctrl+C)** | Nada persistido |

## Comportamento interativo

- **Tipo de prompt:** nenhum no command. Toda entrada é via flags.
- **Validação inline:** Typer (enums + min/max) + Pydantic (max_length).
- **Defaults:** `eat=5, rest=30, pesado=False, notas=""`. Aceitar todos os defaults **assume o almoço "ideal"** — o que raramente é verdade.
- **Histórico:** não aplicável.
- **Ctrl+C:** nada persistido.
- **Ctrl+D:** mesma rota.
- **Timeout:** não há.

## Comportamento especial: emoji + within_budget

`within_budget` é um computed field na entity (`entities/v3.py:within_budget`):

```python
@property
def within_budget(self) -> bool:
    return self.eat_min <= 5 and self.rest_min <= 30
```

**Mapeamento de emoji (no command, `lunch_cmd.py:49-50`):**

| Condição | Emoji | Texto |
|---|---|---|
| `pesado=True` | ⚠️ | "PESADO" |
| `pesado=False` | ✅ | "OK" |

| Condição | Símbolo | Texto |
|---|---|---|
| `within_budget=True` | ✓ | (vazio) |
| `within_budget=False` | ✗ | "estourou" |

> **⚠ Atenção:** emojis `✅` (U+2705) e `⚠️` (U+26A0 + U+FE0F) — o segundo é **variação selector** (FE0F) para garantir render correto. Sem isso, alguns terminais mostram caractere genérico.

## Comportamento especial: UPSERT por data

O `id` é `lun_YYYY_MM_DD` (`lunch_cmd.py:37`). Mesmo date = mesmo id = UPSERT:

```bash
$ operational lunch --eat 5 --rest 30
Lunch 2026-06-08
  eat=5min  rest=30min  total=35min  (✓)
  ✅ OK
$ operational lunch --eat 25 --rest 45 --pesado  # sobrescreve o anterior
Lunch 2026-06-08
  eat=25min  rest=45min  total=70min  (✗ estourou)
  ⚠️ PESADO
```

> **⚠ Atenção:** silencioso. Útil para "ajustar"; arriscado para "registrar histórico" (não há versioning).

## Comandos relacionados

- `lunch list` — Rich Table dos registros (`lunch_cmd.py:56-88`).
- `lunch list --date 2026-06-08` — filtra.
- `state show` — dashboard que inclui último lunch.
- `report daily` — relatório que mostra lunch como boundary TARDE.
- `metric energy -e X -f Y` — check-in (não vinculado, mas útil registrar pós-almoço).

> **Gap conhecido:** não há `lunch update` (precisa rodar com mesmo `--date` para UPSERT); não há `lunch delete`; não há `lunch archive`.

## Riscos de usabilidade

Específicos deste form:

1. **Sem confirmação visual antes de gravar** — flags são executadas direto. Sem "preview do que vai ser salvo".
2. **Default `eat=5, rest=30`** é o cenário **ideal** PAV (5min comendo, 30min descansando). Aceitar defaults sem pensar = "almoço perfeito" registrado, o que é raro.
3. **Sem `notas` default** — usuário que pula notas perde contexto (comi o quê? onde?). Sem incentivo a anotar.
4. **Múltiplas almoço por dia não suportado** — só 1 lunch por data. Para "coffee break das 16h", precisaria de outra entity (`SnackRecord`?).
5. **Sem flag `--local`** (restaurante, casa, delivery) — entity não tem esse campo, mas seria útil para relatórios ("almoço fora custa X").
6. **`pesado` é auto-reportado** — sem input de "energia pós-almoço" para correlacionar. Pesado é heurística, não medida.
7. **Sem flag `--sono-pos`** — o "cochilo além do orçamento" correlaciona com pesado, mas não há campo para registrar. Fica em metric energy + ajuste fino manual.
8. **Mensagem de Typer em inglês** — `Invalid value for '--eat': 200 is not in the range 0 <= x <= 120` é técnica.
9. **`within_budget` é hard-coded (≤5 e ≤30)** — não configurável. Para usuário com meta diferente (e.g. eat=10, rest=20), precisa editar entity.
10. **Sem integração com `state show`** — lunch aparece, mas **não é destacado** como boundary crítica. Pode passar despercebido no dashboard.

## Métricas de sucesso

- **Tempo médio de cadastro:** target <10s (3-4 flags).
- **Taxa de uso:** target >80% dos dias. (Lunch é fronteira importante; cobertura baixa = dashboard impreciso.)
- **Taxa de `pesado=True`:** target <20% (maioria deve ter almoços leves).
- **Taxa de `within_budget=True`:** target >50% (mais da metade dentro do ideal).

## Onde aparece

- **NÃO aparece no Home Menu.** Não há flow que invoque `lunch create`.
- Aparece no `state show` (dashboard) e `report daily` (relatório).
- Invocação **exclusivamente via comando direto**.

> **Refactor sugerido:** adicionar `lunch create` ao flow Tarde (opção `2` do Home Menu) entre "almoçar" e "pomodoro". Usuário esquece de logar; menu ajudaria.

## Notas de implementação

- **File:line refs:**
  - `cli/commands/lunch_cmd.py:24-53` — definição do command `create`.
  - `lunch_cmd.py:34` — `date.fromisoformat(target_date) if target_date else date.today()`.
  - `lunch_cmd.py:36-44` — construção da entity `LunchRecord` (não usa factory `make_lunch_record` — **gap**).
  - `lunch_cmd.py:49-53` — output (3 linhas).
  - `entities/v3.py:164` — classe `LunchRecord` (Pydantic v2, `frozen=True`).
  - `entities/v3.py:duracao_total` — computed `eat_min + rest_min`.
  - `entities/v3.py:within_budget` — computed `eat_min <= 5 and rest_min <= 30`.
- **Como adicionar `--energia-pos`:** adicionar `energia_pos: int | None = typer.Option(None, "--energia-pos", min=1, max=10)` (precisa adicionar campo na entity primeiro via Pydantic).
- **Onde fica o estado após submit:** `cli/state.py:lunch_records`. O `id` é `lun_YYYY_MM_DD` (determinístico — mesmo date = mesmo id = UPSERT).
- **Gap arquitetural:** o command **não usa** uma factory `make_lunch_record` (diferente de routine/block/habit/journal/sleep). Constrói a entity direto. Adicionar factory em `meta/factories.py` para consistência.
- **Refactor sugerido:**
  1. Adicionar `lunch create` ao Home Menu flow Tarde (opção `2`).
  2. Adicionar factory `make_lunch_record` em `meta/factories.py`.
  3. Adicionar campo `energia_pos: int | None` (1-10) na entity + flag.
  4. Adicionar campo `local: Literal["CASA", "RESTAURANTE", "DELIVERY", "TRABALHO"]` na entity + flag.
  5. Adicionar coluna "Lunch" ao `state show` com destaque visual (boundary TARDE).
  6. Internacionalizar mensagens Typer (PT-BR).
