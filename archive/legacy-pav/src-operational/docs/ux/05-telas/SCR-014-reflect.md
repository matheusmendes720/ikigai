# SCR-014 — Reflect (OKR V3: Entrada + Saída)

**Comandos:**
- `operational reflect entrada [flags]` — OKRs de **manhã** (reflete sobre ontem, planeja hoje)
- `operational reflect saida [flags]` — OKRs de **noite** (reflete sobre hoje, planeja amanhã)
- `operational reflect list [flags]` — listagem tabular

**Arquivo renderizador:** `cli/commands/reflect_cmd.py:29-118` (entrada e saida)
**Arquivo de comando:** `src/operational/cli/commands/reflect_cmd.py`
**Tipo:** **Form LONGO e multi-passo** — 5 prompts em `entrada` e 5 prompts em `saida`. **Não tem modo flag-only** — os campos são textuais/livres (listas e sentenças), não fazem sentido como flags. Aceita `--date` para data customizada e `--json` para saída.
**Modo JSON:** Sim — `--json` retorna a entidade `DailyReflection` serializada.
**Validação:** Pydantic v2 em `entities/v3.py:104` (classe `DailyReflection`) com `max_length` em todos os campos string. Sem `min_length` — campos podem ser vazios.

> **⚠ Risco de fadiga ALTO:** este é o form mais longo do CLI. 10 prompts totais (5 entrada + 5 saida). Documentamos mitigações ao final.

## Propósito

Registrar uma **DailyReflection** (PAV V3 §2) — a reflexão estruturada de OKRs (Objectives & Key Results) pessoais. É o "ritual de entrada/saída" do dia. Dois modos:

- **Entrada (manhã):** fecha o dia de ontem, abre o dia de hoje. 4 perguntas de fechamento (parar_de_fazer, repetir, sempre_fazer, big_win) + 1 estado psicomático.
- **Saída (noite):** fecha o dia de hoje, alimenta o sistema. 4 perguntas de reflexão (deu_certo, deu_errado, maior_aprendizado, ajustes_para_amanha) + 1 estado final.

Valor gerado:

- Alimenta o `report daily` (cada campo vira um panel no relatório).
- Detecta **padrões** ao longo do tempo (e.g. "parar_de_fazer" recorrente → política REDUCE).
- Estado psicomático (`EstadoPsicomatico`) entra no cálculo de Q_HE.
- Mesma entity para entrada e saída — `entrada` cria, `saida` **merge com entrada existente** (preserva campos de manhã).

## Usuário-alvo

- **Primário:** practitioner PAV que usa o sistema como **diário de bordo reflexivo**, não só como tracker.
- **Momento de uso:**
  - `entrada` — **de manhã**, ao acordar (ou no dia seguinte, retroativo).
  - `saida` — **à noite**, antes de dormir.
- **Frequência:** target 1× de cada por dia, mas é a parte mais pulada (fadiga). Pode ser 3-4× por semana.

## Entradas

- **Do Home Menu:** opção `3` (Encerrar Dia) faz **4 prompts** do subconjunto `saida` (`deu_certo`, `deu_errado`, `aprendizado`, `ajustes`) via `journal create --text` (não via `reflect saida`!) (`home.py:238-260`). **Nota:** o flow usa `journal create` (SCR-010), não `reflect saida` (SCR-014). As reflexões estruturadas completas (com `parar_de_fazer`, `big_win`, etc.) **não são acessíveis pelo Home Menu** — só via comando direto.
- **Comando direto:**
  - `operational reflect entrada --date 2026-06-08` (5 prompts)
  - `operational reflect saida --date 2026-06-08` (5 prompts)
- **Auto-trigger:** nenhum.

## Saídas

- **Persiste em:** `daily_reflections.json` (via `cli.state.daily_reflections`).
- **Confirmação:** `✔ OKRs de entrada registrados!` (verde, `reflect_cmd.py:67`) ou `✔ OKRs de saída registrados!` (`reflect_cmd.py:118`).
- **Redireciona:** volta ao shell / menu.

## Modos de uso

### Modo 1: Interativo (padrão, único)

```bash
operational reflect entrada --date 2026-06-08
# 5 prompts em sequência, depois salva.
```

### Modo 2: Data customizada (retroativo)

```bash
operational reflect saida --date 2026-06-07
# Reflexão de saída para o dia 2026-06-07.
```

### Modo 3: JSON (machine-readable)

```bash
operational reflect entrada --date 2026-06-08 --json
# Não pula prompts! --json só muda a saída (texto da confirmação vs. JSON da entity).
```

> **⚠ Atenção:** `--json` aqui **não pula prompts** (diferente de `routine create --json`). É só output format. Para evitar os 5 prompts, seria preciso implementar modo batch (e.g. `--parar "X;Y;Z" --repetir "..."`), que **não existe**.

### Modo 4: Listagem

```bash
operational reflect list                  # Rich Table de todas as reflexões
operational reflect list --date 2026-06-08  # filtra
operational reflect list --json            # saída estruturada
```

## Argumentos e flags (TODOS)

| Parâmetro | Tipo | Default | Obrigatório | Validação Pydantic | Exemplo |
|---|---|---|---|---|---|
| `--date`, `-d` | str (ISO) | hoje | não (Option) | `date.fromisoformat()` (raise `ValueError` se malformado) | `2026-06-08` |
| `--json` | bool | `False` | não (Option) | — | — |

**Não há outras flags.** Todos os campos de conteúdo são coletados via `Prompt.ask` no command. Para automatizar via script, **teria que** implementar modo batch — não está implementado.

## Wireframe passo-a-passo

### Estado: `reflect entrada` (5 prompts)

```
$ operational reflect entrada --date 2026-06-08

🌅 OKRs de Entrada — 2026-06-08

Reflita sobre ONTEM para definir intenção de HOJE

  O que fiz ontem que devo PARAR de fazer (separar por ;) ["]:
    Trabalho noturno após 22h; checar email compulsivo
  O que fiz ontem que devo REPETIR (separar por ;) ["]:
    Workout 06:30; pomodoros de 25min
  O que devo SEMPRE fazer (indexador de eficácia) (separar por ;) ["]:
    Meditar 10min ao acordar
  Big-win (única coisa que torna outras mais fáceis) ["]:
    Acordar 06:00 SEM snooze

  Estado geral (1-10) [7]: 8

✔ OKRs de entrada registrados!
```

**Detalhes:**
- Listas são separadas por `;` (ponto-e-vírgula), não `,` (`reflect_cmd.py:23`). Confuso? Decisão consciente: `,` aparece em textos ("meditar, respirar, alongar"), enquanto `;` é raro.
- Defaults são todos `""` (vazio). Enter pula o campo.
- `Estado geral` é convertido de `int` (1-10) para `EstadoPsicomatico` (`enums.py:817-825`):
  - 9-10 → EXCELENTE
  - 7-8 → BOM
  - 5-6 → REGULAR
  - 3-4 → RUIM
  - 1-2 → CRITICO

### Estado: `reflect saida` (5 prompts, MERGE com entrada existente)

```
$ operational reflect saida --date 2026-06-08

🌙 OKRs de Saída — 2026-06-08

Reflita sobre HOJE para alimentar o sistema

  O que deu certo hoje (execução sistemática) (separar por ;) ["]:
    6h de deep work sem interrupção; 2 workouts
  O que deu errado (equívocos) (separar por ;) ["]:
    Procrastinei 1h em redes sociais após almoço
  Maior aprendizado do dia (antítese + síntese) ["]:
    Pomodoro de 25min com pausa de 5min é melhor que 50/10

  Ajustes finos para amanhã (separar por ;) ["]:
    Bloquear redes 14-17h; começar tarefa mais difícil às 09h

  Estado final do dia (1-10) [6]: 7

✔ OKRs de saída registrados!
```

**Comportamento MERGE (`reflect_cmd.py:90-100`):**

```python
existing = daily_reflections.get(UEID(f"ref_{d.strftime('%Y%m%d')}"))
if existing:
    ref_data = existing.model_dump()  # preserva campos de manhã
    ref_data["deu_certo"] = deu_certo
    ref_data["deu_errado"] = deu_errado
    ref_data["maior_aprendizado"] = aprendizado
    ref_data["ajustes_para_amanha"] = ajustes
    ref_data["estado_geral"] = estado
    ref = DailyReflection.model_validate(ref_data)
else:
    # Cria reflection só com campos de saída
    ref = DailyReflection(id=..., deu_certo=..., ...)
```

> **⚠ Atenção:** o merge sobrescreve `estado_geral` (campo único, último ganha). Se você rodou `entrada` com estado 8 e `saida` com estado 5, o estado final é 5. **Perde-se o pico de energia da manhã** (e.g. acordei bem, mas terminei exausto). Sugere-se dois campos: `estado_manha`, `estado_noite`.

### Estado: Listagem (`reflect list`)

```
$ operational reflect list
╭───────────────────────────────────────────────────────────────────╮
│ Data        Estado    Big-Win                       Aprendizado   │
│ ────────────────────────────────────────────────────────────────
│ 2026-06-08  bom       Acordar 06:00 SEM snooze      Pomodoro 25/5 │
│ 2026-06-07  regular   Workout 06:30                  Foco pós-almoço│
╰───────────────────────────────────────────────────────────────────╯
```

### Estado: Erro — data malformada

```bash
$ operational reflect entrada --date "amanhã"
# ValueError: Invalid isoformat string: 'amanhã'
# Exit code: 1
```

### Estado: Erro — estado >10

```bash
# No prompt: "  Estado geral (1-10) [7]: 11"
# EstadoPsicomatico.from_score(11) → KeyError ou similar
# Comportamento atual: NÃO HÁ VALIDAÇÃO. 11 vira "EXCELENTE" (boundary)
```

> **⚠ Atenção:** `EstadoPsicomatico.from_score` (`enums.py:817-825`) faz `if score >= 9: return EXCELENTE`. **Não há validação para score > 10 ou < 1**. Aceita silenciosamente.

## Validação e erros

| Cenário | Comportamento | Onde é validado |
|---|---|---|
| `--date` malformado | `date.fromisoformat()` raise `ValueError` | `reflect_cmd.py:38` |
| `parar_de_fazer[i]` >200 chars | Pydantic `max_length=200` rejeita | `entities/v3.py:130-138` |
| `big_win` >300 chars | Pydantic `max_length=300` rejeita | idem |
| `maior_aprendizado` >500 chars | Pydantic `max_length=500` rejeita | idem |
| Estado <1 ou >10 | `from_score` aceita (sem validação) | `enums.py:817-825` |
| `entrada` duplicada (mesmo date) | `upsert` substitui (perde saida!) | `reflect_cmd.py:62` ⚠ |
| `saida` sem `entrada` prévia | Aceito — cria entity só com campos de saída | `reflect_cmd.py:101-112` |
| `saida` com `entrada` prévia | **MERGE**: preserva campos de manhã, sobrescreve `estado_geral` | `reflect_cmd.py:90-100` |

## Estados (5)

| Estado | Notas |
|---|---|
| **Vazio** | Não aplicável — `date` tem default hoje; pode rodar sem flags |
| **Loading** | Não aplicável |
| **Com dados (sucesso)** | Wireframe "entrada" / "saida" |
| **Erro de validação** | Data malformada, campo string >max_length, estado fora de range (silencioso) |
| **Cancelamento (Ctrl+C)** | Nada persistido se a factory não rodou |

## Comportamento interativo

- **Tipo de prompt:** `rich.prompt.Prompt.ask` para todos os 5 campos. Listas via helper `_prompt_list` que faz `split(";")`.
- **Validação inline:** nenhuma no command. Validação é Pydantic no construtor, depois do input. Mensagens vêm só se você exceder limites.
- **Defaults:** todos `""` (vazio). Para `estado_geral`, `default="7"` em entrada, `default="6"` em saida (`reflect_cmd.py:49, 87`).
- **Histórico:** não há.
- **Ctrl+C:** nada persistido.
- **Ctrl+D:** mesma rota.
- **Timeout:** não há.

> **⚠ Comportamento especial — `entrada` pode perder `saida`:** se você rodar `entrada` **depois** de `saida` no mesmo dia, o `upsert` **sobrescreve** a entity inteira — `deu_certo`, `deu_errado`, etc. são perdidos (`reflect_cmd.py:62`). **Ordem importa**: sempre `entrada` antes de `saida`. Não há proteção.

## Comportamento especial: separador `;` em listas

`_prompt_list` (`reflect_cmd.py:21-27`):

```python
def _prompt_list(label: str, default: str = "") -> list[str]:
    raw = Prompt.ask(f"  {label} (separar por ;) ", default=default)
    if not raw.strip():
        return []
    return [s.strip() for s in raw.split(";") if s.strip()]
```

- `""` → lista vazia.
- `"A;B;C"` → `["A", "B", "C"]`.
- `"A; B ;C"` → `["A", "B", "C"]` (strip em cada).
- `"A,B,C"` → `["A,B,C"]` (uma string só — sem split em vírgula!).

> **⚠ Atenção:** usar `,` em vez de `;` cria uma string única. **Inconsistência** com o resto do sistema que geralmente usa `,` como separador (e.g. `days_of_week` em rotinas).

## Comandos relacionados

- `reflect list` — Rich Table das reflexões (`reflect_cmd.py:121-149`).
- `reflect list --date 2026-06-08` — filtra.
- `journal create --text "..."` — versão **minimal** sem estrutura OKR (SCR-010). É o que o Home Menu usa.
- `state show` — dashboard que inclui último reflection.
- `report daily` — relatório que inclui 6 panels (parar_de_fazer, repetir, big_win, deu_certo, deu_errado, maior_aprendizado).

> **Gap conhecido:** o `report daily` lê **campos do journal** (`JournalEntry.licoes_aprendidas`, `desvios`) e **campos do reflection** (`DailyReflection.big_win`, etc.), mas não há sincronização automática. Os dois coexistem.

## Riscos de usabilidade

Específicos deste form (e mitigações):

1. **Fadiga de 5 prompts** — 10 prompts totais se fizer entrada + saida. Target de tempo: <90s para entrada, <90s para saida. Mitigação: defaults vazios em todos os campos (exceto estado) → Enter-Enter-Enter-Enter se quiser pular.
2. **Sem modo batch via flag** — para scripts/automação, **não há como fornecer as respostas via flags**. Mitigação: editar JSON direto.
3. **Separação `;` contraintuitiva** — usuário acostumado a vírgula digita `A,B,C` e vê `"A,B,C"` salvo como item único. Mitigação: aumentar help do prompt.
4. **`entrada` pode perder `saida`** — rodar entrada 2× no mesmo dia sobrescreve. Mitigação: detectar se saida existe e fazer merge (mas isso não está implementado).
5. **Estado fora de range aceito** — `from_score(11)` retorna EXCELENTE silenciosamente. Mitigação: adicionar validação no command.
6. **Merge sobrescreve `estado_geral`** — perde estado da manhã se rodar saida. Mitigação: criar dois campos (`estado_manha`, `estado_noite`).
7. **Home Menu NÃO aciona `reflect`** — usa `journal create` (SCR-010) que não tem os campos OKR. Usuário que só usa o menu **nunca preenche `parar_de_fazer`, `repetir`, `big_win`, `maior_aprendizado`, `ajustes_para_amanha`**. Mitigação: adicionar reflect ao flow Encerrar Dia (substituir journal).
8. **Mensagens em PT-BR nos prompts, mas erros em inglês** — `ValueError: Invalid isoformat string: 'amanhã'` em vez de "Data inválida".
9. **`big_win` cap 300 chars** — arbitrário. Para "big win" muito elaborado, precisa truncar.
10. **Sem confirmação visual antes de gravar** — após o último prompt, a entity é upsertada direto. Sem preview "você está prestes a registrar: ...".

## Métricas de sucesso

- **Tempo médio de `entrada`:** target <60s (5 prompts, vários opcionais).
- **Tempo médio de `saida`:** target <90s (5 prompts com mais conteúdo).
- **Taxa de conclusão (entrada/saida executados / dias totais):** target >50% (reflexão é opcional; não obrigar é OK).
- **Taxa de campos vazios por reflexão:** target <30%. Se >50% dos campos estão vazios, usuário está "passando reto" — UX precisa encorajar conteúdo.

## Onde aparece

- **NÃO aparece no Home Menu** diretamente. O flow Encerrar Dia (opção `3`) usa `journal create` (SCR-010) em vez de `reflect saida` (`home.py:238-260`).
- Aparece no `report daily` (consome os campos) e `state show` (mostra último reflection).
- Invocação **exclusivamente via comando direto**.

## Notas de implementação

- **File:line refs:**
  - `cli/commands/reflect_cmd.py:29-68` — `entrada()` (5 prompts + save).
  - `cli/commands/reflect_cmd.py:70-118` — `saida()` (5 prompts + merge com existente).
  - `cli/commands/reflect_cmd.py:21-27` — `_prompt_list` helper.
  - `cli/commands/reflect_cmd.py:121-149` — `list_reflections()`.
  - `entities/v3.py:104` — classe `DailyReflection` (Pydantic v2).
  - `entities/v3.py:130-138` — campos com `max_length` (parar_de_fazer, repetir, sempre_fazer, big_win, deu_certo, deu_errado, maior_aprendizado, ajustes_para_amanha, estado_geral).
  - `enums.py:803-825` — `EstadoPsicomatico` + `from_score`.
- **Como adicionar modo batch via flags:** em `entrada()`, adicionar:
  ```python
  parar: list[str] = typer.Option([], "--parar", help="Separar por ;")
  repetir: list[str] = typer.Option([], "--repetir")
  # ... etc
  if not (parar or repetir or sempre or big_win):
      # Fall back to interactive prompts
      ...
  else:
      # Use flags directly, skip prompts
  ```
- **Como mudar validação de `estado_geral`:** adicionar `if not 1 <= int(e) <= 10: raise typer.BadParameter(...)` antes de `from_score(int(e))`.
- **Onde fica o estado após submit:** `cli/state.py:daily_reflections`. O `id` é `ref_YYYY_MM_DD` (determinístico — mesmo date = mesmo id = UPSERT).
- **Refactor sugerido:**
  1. Adicionar `reflect entrada` e `reflect saida` ao Home Menu (substituir `journal create` no flow Encerrar Dia).
  2. Adicionar `--parar`, `--repetir`, etc. como flags (modo batch).
  3. Renomear `estado_geral` para `estado_noite` e adicionar `estado_manha` para preservar manhã.
  4. Adicionar validação de range em `estado_geral` (1-10).
  5. Trocar separador `;` por `,` (consistência) **ou** documentar a escolha.
