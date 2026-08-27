# SCR-013 — Policy Decisions

**Comando:** `operational policy list [--json]` (e variações: `policy setpoints`, `policy decisions`)
**Arquivo renderizador:** N/A (output via `typer.echo` — não usa Rich)
**Arquivo de comando:** `src/operational/cli/commands/policy_cmd.py:40-53` (`decisions`), `policy_cmd.py:14-38` (`setpoints`)
**Tipo:** Output tabular textual (read-only)
**Modo JSON:** Sim (`--json`)
**Dataset:** qualquer

## Propósito

Mostrar as **PolicyDecisions** (decisões geradas pelo PolicyEngine cada noite) e os **PolicySetpoints** (4 regimes canônicos: PUSH, MAINTAIN, REDUCE, RECOVER) que o sistema usa como input. O usuário olha esta tela para responder: *"Por que ontem o sistema recomendou REDUCE? Qual é o regime atual? Os setpoints bateram?"*.

## Usuário-alvo

O próprio usuário, em revisão semanal ou após um dia ruim. Momento: domingo à noite, antes de planejar a semana. Objetivo: auditar a lógica do PolicyEngine — verificar se a transição PUSH→REDUCE aconteceu corretamente, qual foi o `qhe_input` que disparou, etc.

## Entradas

- **Do home menu:** opção `8` (Política & Ajuste) → submenu.
- **Comando direto:** `operational policy list` (atalho que **não existe** — o sub-app é `policy` com comandos `setpoints` e `decisions`).
- **Atalho real:** `operational policy decisions [--json]` ou `operational policy setpoints [--json]`.

## Saídas

- **Ver relatório diário da decisão:** `operational report daily --date 2026-06-04` (SCR-002) — a PolicyDecision aparece indiretamente via `qhe_input` e `severity`.
- **Gerar nova PolicyDecision:** `operational policy apply` (não implementado nesta versão — seria um comando futuro).
- **Limpar histórico:** `operational demo clear` (afeta todos os repos, incluindo `policy_decisions`).

## Argumentos e flags

| Sub-comando | Flag | Tipo | Default | Comportamento se omitido | Exemplo |
|-------------|------|------|---------|--------------------------|---------|
| `decisions` | `--json` | `bool` | `False` | Emite lista de Pydantic models serializados. | `operational policy decisions --json` |
| `setpoints` | `--json` | `bool` | `False` | Emite lista de PolicySetpoints. Se vazio, gera defaults antes. | `operational policy setpoints --json` |
| `setpoints` | (sem args) | — | — | Se vazio, gera 4 setpoints (1 por estado) automaticamente. | `operational policy setpoints` |

> Nota: o sub-comando `list` documentado na spec do agente **não corresponde** a um comando real no `policy_cmd.py`. O comando real é `decisions` (não `list`). Esta doc documenta a spec do agente (renomeando `decisions` → `list`) **e** a implementação real.

## Conteúdo principal

### `policy decisions` (sem `--json`)

Texto plain via `typer.echo` (`policy_cmd.py:49-53`):

```
Policy decisions (7):
  2026-06-02  state=MAINTAIN  severity=INFO  Dentro do padrao ouro. Manter regime. QHE alto.
  2026-06-03  state=REDUCE    severity=WARNING  Desvio leve mas recuperavel. Recomendar sono extra.
  2026-06-04  state=RECOVER   severity=CRITICAL  Hardcore day. Recuperacao 48h obrigatoria.
  2026-06-05  state=MAINTAIN  severity=INFO  Recuperacao OK. Manter ritmo leve.
  2026-06-06  state=REDUCE    severity=WARNING  Lunch pesado causou perda de 30min. Ajustar refeicoes.
  2026-06-07  state=PUSH      severity=INFO  Sabado excelente. QHE alto. Manter.
  2026-06-08  state=MAINTAIN  severity=INFO  Domingo OK. Visita absorvida sem grandes perdas.
```

- `rationale` é truncado em 60 caracteres (`policy_cmd.py:53`).
- Sem painel Rich, sem cor.

### `policy setpoints` (sem `--json`, vazio inicial)

Texto plain via `typer.echo` (`policy_cmd.py:22-30`) — gera defaults e imprime:

```
PUSH regime: maximum focus.
  PUSH:
    hardwork_budget=8.0h
    pomodoro_cap=10
    sleep_target=7.0h
    qhe_target=0.85
MAINTAIN regime: steady cadence.
  MAINTAIN:
    hardwork_budget=6.0h
    pomodoro_cap=8
    sleep_target=8.0h
    qhe_target=0.75
REDUCE regime: protect recovery.
  REDUCE:
    hardwork_budget=4.0h
    pomodoro_cap=5
    sleep_target=8.0h
    qhe_target=0.65
RECOVER regime: hard stop.
  RECOVER:
    hardwork_budget=2.0h
    pomodoro_cap=2
    sleep_target=9.0h
    qhe_target=0.5
```

> Nota: os 4 setpoints acima batem com os 4 rows do `golden.csv` linhas 10-13. São as constantes canônicas de `operational/entities/policy.py:PolicySetpoints.from_pav_defaults(state)`.

### `policy setpoints` (sem `--json`, já populado)

```
Policy setpoints (4):
  State=PUSH: budget=8.0h  sleep=7.0h  qhe=0.85
  State=MAINTAIN: budget=6.0h  sleep=8.0h  qhe=0.75
  State=REDUCE: budget=4.0h  sleep=8.0h  qhe=0.65
  State=RECOVER: budget=2.0h  sleep=9.0h  qhe=0.5
```

## Hierarquia visual

- **1º:** O regime atual (em `decisions`, é a última linha — a de hoje).
- **2º:** `severity` (CRITICAL > WARNING > INFO) — chamada visual se a decisão foi crítica.
- **3º:** `rationale` (por quê).

## Wireframe ASCII (com dados reais do golden.csv)

```
$ operational policy decisions

Policy decisions (7):
  2026-06-02  state=MAINTAIN  severity=INFO      Dentro do padrao ouro. Manter regime. QHE alto.
  2026-06-03  state=REDUCE    severity=WARNING   Desvio leve mas recuperavel. Recomendar sono
  2026-06-04  state=RECOVER   severity=CRITICAL  Hardcore day. Recuperacao 48h obrigatoria.
  2026-06-05  state=MAINTAIN  severity=INFO      Recuperacao OK. Manter ritmo leve.
  2026-06-06  state=REDUCE    severity=WARNING   Lunch pesado causou perda de 30min. Ajustar
  2026-06-07  state=PUSH      severity=INFO      Sabado excelente. QHE alto. Manter.
  2026-06-08  state=MAINTAIN  severity=INFO      Domingo OK. Visita absorvida sem grandes perda
```

Com `--json`:

```json
[
  {
    "id": "pol_demo_00_2026_06_02",
    "date": "2026-06-02",
    "state": "MAINTAIN",
    "severity": "INFO",
    "rationale": "Dentro do padrao ouro. Manter regime. QHE alto.",
    "setpoints": "{...json inline do MAINTAIN setpoint...}",
    "days_in_state": 3,
    "previous_state": null,
    "qhe_input": 0.78,
    "energy_input": "H",
    "infraction_count": 0,
    "applied": true,
    "applied_at": "2026-06-02T20:30:00+00:00"
  },
  ...
]
```

## Estados (5)

### Estado 1 — Vazio (após `clear`)

```
$ operational demo clear
$ operational policy decisions

No policy decisions yet.
```

Útil para confirmar reset.

### Estado 2 — Loading

- **Não aplicável** (síncrono, ~5 ms).

### Estado 3 — Com dados (wireframe acima)

- 7 linhas (uma por dia). Texto plain, sem cor.

### Estado 4 — Erro

- **Sem `policy_decisions` repo carregado** (rara corrupção): `policy_decisions.list()` retorna `[]` → "No policy decisions yet." Sem traceback.
- **Pydantic validation error** em uma PolicyDecision: o `list()` faz `_load_all()` que parseia JSON; erro sobe como `ValidationError` → traceback Rich. Mitigação: `operational doctor doctor` para localizar.

### Estado 5 — Dataset sintético (golden.csv)

- O golden tem exatamente 7 PolicyDecisions (uma por dia, geradas no cenário "demo seed"). As 4 transições canônicas estão presentes: PUSH (sábado 06-07), MAINTAIN (domingo + dias normais), REDUCE (desvios), RECOVER (HARDCORE pós-deadline).

## Comportamento interativo

- **Aceita input do usuário?** NÃO. Read-only.
- **Tem prompts?** NÃO.
- **Teclas de atalho?** `Ctrl+C` aborta.
- **Mouse?** Sem suporte.

## Comandos relacionados

- `operational report daily --date 2026-06-04` — drill-down com `qhe_input` e `severity` refletidos no header e na `next_step`.
- `operational state show` — visão "agora" (não lista PolicyDecisions, mas a `next_step` da tela usa o regime corrente).
- `operational demo seed` — popula 7 PolicyDecisions canônicas.

## Riscos de usabilidade

1. **Texto plain (sem cor, sem painel)** — outras telas (state, daily, weekly) usam Rich; esta usa `typer.echo`. Inconsistência visual forte.
2. **`rationale` truncado em 60 chars** (`policy_cmd.py:53`) — corta informações importantes. Mitigação: aumentar para 200 ou wrap em múltiplas linhas.
3. **Sem data em destaque** — `2026-06-04` e `state=RECOVER` são lidos no mesmo peso visual. Mitigação: aplicar cor `bold red` para `CRITICAL`, `yellow` para `WARNING`, `green` para `INFO`.
4. **`setpoints` no JSON é um string escapado** (não um dict) — armazenado como `setpoints: str` no Pydantic model (`policy_cmd.py:53` referencia `d.setpoints` como string). O `jq .setpoints.budget` não funciona. Mitigação: parsear para dict antes de serializar.
5. **Não há agregação "regime atual"** — o usuário precisa ler a última linha manualmente. Mitigação: header `Regime atual: MAINTAIN (há 2 dias)`.
6. **Ordenação é por `date` ASC** — a decisão **mais recente fica em último**. Convencional seria DESC (mais recente primeiro).

## Métricas de sucesso

- **Tempo até identificar o regime atual**: meta < 3s (rolar até a última linha). Pode melhorar com header.
- **Taxa de uso**: esperado < 10% (uso avançado — auditoria do PolicyEngine).
- **Erros de interpretação**: meta 0% (mas hoje é alto: rationale truncado, sem cor de severity).

## Onde aparece

- Home menu: opção `8` (Política & Ajuste) → submenu.
- Link direto: `operational policy decisions` ou `operational policy setpoints`.
- Usado em QA para verificar que o PolicyEngine fez a transição certa.

## Notas de implementação

- Entry point: `cli/commands/policy_cmd.py:11` (sub-Typer `app`).
- Comando `decisions`: `policy_cmd.py:40-53`. Lê `policy_decisions.list()` (todos os itens) e itera.
- Comando `setpoints`: `policy_cmd.py:14-38`. Se vazio, gera 4 setpoints via `PolicySetpoints.from_pav_defaults(state)` (`operational/entities/policy.py`).
- Output: `typer.echo(...)` direto — sem `console.print`. **Não respeita** `is_captured()`.
- `rationale[:60]` em `policy_cmd.py:53` é a única "formatação" aplicada.
- `setpoints` field: é um `str` (JSON inline), não um dict. Para acessar: `json.loads(d.setpoints)["hardwork_budget_hours"]`.
- Performance: ~10 ms (1 chamada a `list()` por repo).
- Refactor pendente: extrair para `ui/policy.py:render_policy_decisions(items)` com painel Rich + cores por `severity`.
