# SCR-011 — Habit Create (Form de Criação de Hábito)

**Comando:** `operational habit create [name] [category] [flags]`
**Arquivo renderizador:** `cli/commands/habit_cmd.py:34-61`
**Arquivo de comando:** `src/operational/cli/commands/habit_cmd.py`
**Tipo:** Form com 2 argumentos posicionais + 2 flags numéricas. Aceita modo não-interativo.
**Modo JSON:** Sim — `--json` retorna a entidade `Habit` serializada.
**Validação:** Pydantic v2 via factory `make_habit` (`meta/factories.py:110-141`) → `Habit` (`entities/habit.py:88`) com validators `_validate_name_not_blank` e bounds em `resistance`/`lambda_learning`/`weight_in_qhe`.

## Propósito

Cadastrar um **hábito** (PRD-02 §2, PAV §6) — a definição estática de uma prática recurrente com:
- **Resistência (R):** quão difícil é executar (0=fácil, 10=impossível). Usado em `E_req = R(1-H)`.
- **Peso (w_i):** importância no agregador Q_HE (Quality of Habit Execution), 0-1.
- **Categoria:** PHYSIOLOGICAL / COGNITIVE / SOCIAL / CREATIVE / RITUAL.

Valor gerado:

- Alimenta o **Q_HE diário** (média ponderada de execuções).
- Permite tracking de **streaks** (target_streak).
- Diferencia hábitos **fáceis** (hidratação, R=2) de **difíceis** (meditação 1h, R=8).
- Categorização ajuda em **relatórios filtrados** (`habit list --category cognitive`).

## Usuário-alvo

- **Primário:** practitioner PAV montando seu catálogo de hábitos a trackear (10-20 hábitos típico).
- **Momento de uso:** setup inicial (uma vez por hábito) e ajustes (mudar peso se a prioridade mudou).
- **Frequência:** muito baixa — 1× por hábito, raramente revisita.

## Entradas

- **Do Home Menu:** **não há flow dedicado** para criar hábitos. O sub-menu Dados (opção `7`) **não** tem item de criar hábito. É invocação direta apenas.
- **Comando direto:** `operational habit create "Meditar 10min" ritual --resistance 6 --weight 0.30`.
- **Auto-trigger:** nenhum.

## Saídas

- **Persiste em:** `habits.json` (via `cli.state.habits`).
- **Confirmação:** `✓ Hábito criado: <name>` + linha `dim` com `id`, categoria, R, W (`habit_cmd.py:60-61`).
- **Redireciona:** volta ao shell / menu.

## Modos de uso

### Modo 1: Flags (não-interativo) — uso comum

```bash
operational habit create "Meditar 10min" ritual --resistance 6 --weight 0.30
# Saída:
#   ✓ Hábito criado: Meditar 10min
#   id: hab_20260608_150000  ·  ritual  ·  R=6.0  W=0.3
```

### Modo 2: Mínimo (só argumentos posicionais)

```bash
operational habit create "Beber água"
# Cria hábito PHYSIOLOGICAL, R=5.0, W=0.25 (defaults da factory)
```

> **⚠ Atenção:** o argumento `category` é **obrigatório** no `typer.Argument(...)` se você omitir; o default `HabitCategory.PHYSIOLOGICAL` só se aplica se você **passa a string e Typer parseia o enum**. Se você fizer `habit create "X"` (1 arg só), Typer dá erro de "missing argument 'category'".

### Modo 3: Categoria via flag (alternativa)

```bash
operational habit create "Beber água" --category physiological
# Funciona — Typer aceita category tanto em posição 2 quanto via --category
```

### Modo 4: JSON

```bash
operational habit create "Read 30min" cognitive --resistance 4 --weight 0.20 --json
# Saída: {"id": "hab_...", "name": "Read 30min", "category": "cognitive", "resistance": 4.0, ...}
```

## Argumentos e flags (TODOS)

| Parâmetro | Tipo | Default | Obrigatório | Validação Pydantic | Exemplo |
|---|---|---|---|---|---|
| `name` | str | (sem default) | **sim** (Argument) | `min_length=1, max_length=100`, não-branco após strip (`habit.py:152-174`) | `"Meditar 10min"` |
| `category` | `HabitCategory` (enum) | `PHYSIOLOGICAL` | não (Argument) | enum strict | `ritual` \| `cognitive` \| `social` \| `creative` \| `physiological` |
| `--resistance`, `-r` | float | `5.0` | não (Option) | Typer `min=0.0, max=10.0`; Pydantic `Field(ge=0.0, le=10.0)` | `6.0` |
| `--weight`, `-w` | float | `0.25` | não (Option) | Typer `min=0.0, max=1.0`; Pydantic `Field(ge=0.0, le=1.0)` | `0.30` |
| `--json` | bool | `False` | não (Option) | — | — |

> **⚠ Atenção:** Typer valida `min=0.0, max=10.0` em `--resistance` **antes** do código rodar (`habit_cmd.py:38`). Mensagem vem em inglês: `Invalid value for '--resistance': 11.0 is not in the range 0.0 <= x <= 10.0`.

> **⚠ Atenção:** o campo `lambda_learning: float` (λ em `H(t) = 1 - e^{-λs}`) **existe na entity** (`habit.py:91`) com default `LAMBDA_LEARNING_DEFAULT = 0.093` (ADR-003), mas **não é exposto na CLI**. Para customizar, é preciso override via factory.

## Wireframe passo-a-passo

### Estado: Criação bem-sucedida via comando direto

```
$ operational habit create "Meditar 10min" ritual --resistance 6 --weight 0.30

╭─ Input Summary ──────────────────────────────╮
│  Criando hábito                              │
│    name      : Meditar 10min                 │
│    category  : ritual                        │
│    resistance: 6.0                           │
│    weight    : 0.3                           │
╰───────────────────────────────────────────────╯
  ✓ Hábito criado: Meditar 10min
    id: hab_20260608_150000  ·  ritual  ·  R=6.0  W=0.3
```

### Estado: Listagem pós-criação (`habit list`)

```
╭─── ✅ Habits (3) ────────────────────────────╮
│ Categoria       Nome                  R     W    ID
│ ─────────────────────────────────────────────
│ 💧 physiological Beber água         ██░░  25%  hab_...
│ 🧘 ritual        Meditar 10min      ████  30%  hab_20260608_150000
│ 🧠 cognitive     Read 30min         ██░░  20%  hab_...
╰─────────────────────────────────────────────╯
```

A `R` (resistance) é barra de 0-10; `W` (weight) é barra de 0-100% (`habit_cmd.py:101-105`).

### Estado: Erro — resistance fora do range

```bash
$ operational habit create "Test" ritual --resistance 11
# Typer: Invalid value for '--resistance': 11.0 is not in the range 0.0 <= x <= 10.0
# Exit code: 2
```

### Estado: Erro — weight fora do range

```bash
$ operational habit create "Test" ritual --weight 1.5
# Typer: Invalid value for '--weight': 1.5 is not in the range 0.0 <= x <= 1.0
# Exit code: 2
```

### Estado: Categoria inválida

```bash
$ operational habit create "Test" espiritual --resistance 5
# Typer: invalid value: 'espiritual' for 'HabitCategory'; must be physiological, ritual, cognitive, social, or creative
# Exit code: 2
```

### Estado: Nome em branco

```bash
$ operational habit create "   " ritual --resistance 5
# Pydantic: Value error, Name must not be blank
# (ou similar — depende da versão do validador)
# Exit code: 1
```

> **⚠ Atenção:** o validador `_validate_name_not_blank` (`habit.py:152-174`) verifica `name.strip() == ""`. Typer não faz strip antes; o Pydantic sim.

## Validação e erros

| Cenário | Comportamento | Onde é validado |
|---|---|---|
| `name` vazio ou só whitespace | Pydantic `_validate_name_not_blank` rejeita | `entities/habit.py:152-174` |
| `name` >100 chars | Pydantic `max_length=100` rejeita | construtor |
| `category` inválido | Typer `BadParameter` antes de rodar | Typer binding |
| `--resistance` <0 ou >10 | Typer `min/max` rejeita | `habit_cmd.py:38` |
| `--weight` <0 ou >1 | Typer `min/max` rejeita | `habit_cmd.py:39` |
| Hábito duplicado (mesmo id) | `habits.upsert()` substitui | `state.py:upsert` |
| `lambda_learning` (não exposto) | Pydantic `Field(ge=0.0, le=1.0)` rejeita; default `0.093` | `habit.py:91` |

## Estados (5)

| Estado | Notas |
|---|---|
| **Vazio** | Não aplicável — `name` é obrigatório (Argument sem default) |
| **Loading** | Não aplicável — operação síncrona |
| **Com dados (sucesso)** | Wireframe "Criação bem-sucedida" |
| **Erro de validação** | Resistance/weight fora do range, nome vazio, categoria inválida |
| **Cancelamento (Ctrl+C)** | Nada persistido |

## Comportamento interativo

- **Tipo de prompt:** nenhum no command.
- **Validação inline:** Typer (enums + min/max) + Pydantic (max_length, name_not_blank).
- **Defaults:** `category=PHYSIOLOGICAL`, `resistance=5.0`, `weight=0.25`, `lambda_learning=0.093`.
- **Histórico:** não aplicável.
- **Ctrl+C:** nada persistido.
- **Ctrl+D:** mesma rota.
- **Timeout:** não há.

## Comportamento especial: cores e ícones por categoria

O `habit list` mapeia cada categoria para cor+ícone (`habit_cmd.py:18-31`):

| Categoria | Ícone | Cor |
|---|---|---|
| `physiological` | 💧 | blue |
| `ritual` | 🧘 | magenta |
| `cognitive` | 🧠 | cyan |
| `social` | 👥 | yellow |
| `creative` | 🎨 | green |

> **⚠ Atenção:** a comparação é `cat_value = h.category.value if hasattr(h.category, "value") else str(h.category)` (`habit_cmd.py:98`). Funciona para `StrEnum` mas é defensiva contra strings cruas.

## Comandos relacionados

- `habit list` — Rich Table ordenada por `weight_in_qhe` desc (`habit_cmd.py:82`).
- `habit list --category cognitive` — filtra por categoria.
- `habit list --json` — saída estruturada.
- `state show` — dashboard que mostra hábitos ativos.
- `qhe show` (a confirmar) — pode usar habits para cálculo de Q_HE.

> **Gap conhecido:** não há `habit update`, `habit delete`, `habit archive`. Edição requer editar JSON ou criar+deletar. Não há command de **marcar hábito como cumprido no dia** (precisa ser via `routine log` ou entity `HabitState`, que não está exposta na CLI).

## Riscos de usabilidade

Específicos deste form:

1. **Default `resistance=5.0`** é meio da escala — usuário que aceita sem pensar cadastra tudo como "médio", perdendo a utilidade de distinguir fácil/difícil.
2. **Default `weight=0.25`** sugere "1 hábito por vez", mas usuário pode somar pesos >1 (sem warning), o que **viola a normalização** do Q_HE (deveria ser soma=1). Sistema não normaliza automaticamente.
3. **Sem flag `--lambda`** — o `lambda_learning` é fixo em `0.093` para todos os hábitos. Não é possível ter "hábitos de aprendizado rápido" (λ=0.5) vs "lentos" (λ=0.05).
4. **Sem flag `--frequency`** — entity tem `Literal["DAILY", "WEEKLY", "WAVE"]` (default `DAILY`), mas não é exposto.
5. **Sem flag `--target-streak`** — entity tem `target_streak: int | None` (≥ 0), mas não é exposto.
6. **Typer valida `min/max` em inglês** — mensagem técnica, não traduzida.
7. **Sem preview de Q_HE resultante** — não há "se você adicionar este hábito com W=0.30, sua Q_HE totalizará 0.55 (somando 0.25 do anterior + 0.30)". Usuário não sabe se está normalizando.

## Métricas de sucesso

- **Tempo médio de cadastro:** target <10s.
- **Distribuição de resistance:** target Gaussiana centrada em 4-6, com caudas em 1-2 (fáceis) e 8-9 (desafiadores). Se tudo é 5.0, defaults não estão sendo ajustados.
- **Soma de weights dos hábitos do usuário:** target ≈ 1.0 (normalizado). Se muito >1, normalização é falha do UX.

## Onde aparece

- **Não há flow no Home Menu** para criar hábitos. É invocação direta apenas.
- Aparece no `state show` (dashboard) e no cálculo de Q_HE (se/quando implementado).
- Aparece indiretamente no `routine list` (rotinas categorizadas como "workout"/"meditação" podem linkar a hábitos).

## Notas de implementação

- **File:line refs:**
  - `cli/commands/habit_cmd.py:34-61` — definição do command `create`.
  - `cli/commands/habit_cmd.py:38-39` — `typer.Option(..., min=0.0, max=10.0)` (resistance) e `min=0.0, max=1.0` (weight).
  - `cli/commands/habit_cmd.py:49-54` — chamada da factory `make_habit` + `habits.upsert(habit)`.
  - `meta/factories.py:110-141` — `make_habit()` com defaults.
  - `entities/habit.py:88` — classe `Habit` (Pydantic v2, `frozen=True`, `extra="forbid"`).
  - `entities/habit.py:152-174` — `_validate_name_not_blank`.
  - `entities/habit.py:176-226` — factory `Habit.from_pav_defaults(name, category, resistance, weight_in_qhe, **overrides)`.
- **Como adicionar `--lambda`:** adicionar `lambda_learning: float = typer.Option(0.093, "--lambda", "-l", min=0.0, max=1.0)` e passar `lambda_learning=lambda_learning` em `make_habit(...)`.
- **Como adicionar `--frequency`:** adicionar `frequency: Literal["DAILY", "WEEKLY", "WAVE"] = typer.Option("DAILY", "--frequency", "-f")` e passar como override.
- **Onde fica o estado após submit:** `cli/state.py:habits`. O `id` é `hab_<YYYYMMDD>_<HHMMSS>` (timestamp).
- **Atenção ao `make_habit` vs `Habit.from_pav_defaults`:** o command usa `make_habit` (factory simples), não `Habit.from_pav_defaults` (que preenche defaults PAV-aware). Para usar o from_pav_defaults, é preciso importar diretamente a entity.
