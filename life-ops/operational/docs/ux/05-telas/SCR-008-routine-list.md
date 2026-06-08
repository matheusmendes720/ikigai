# SCR-008 — Routine List

**Comando:** `operational routine list [--period MANHA|TARDE|NOITE] [--json]`
**Arquivo renderizador:** N/A (constrói `rich.table.Table` inline em `routine_cmd.py:108-142`)
**Arquivo de comando:** `src/operational/cli/commands/routine_cmd.py:85-143` (`list_routines`)
**Tipo:** Output tabular Rich (read-only)
**Modo JSON:** Sim (`--json`)
**Dataset:** qualquer

## Propósito

Listar **todas as rotinas salvas** com colunas: Período (🌅/💻/🌙), Tipo (ENTRY/CORE/EXIT), Nome, Horário, Duração, ID. O usuário olha esta tela para responder: *"Quais rotinas eu tenho configuradas? Em que horário? São obrigatórias? Para quais dias da semana?"*. É a tela de "inventário de rotinas".

## Usuário-alvo

O próprio usuário, especialmente em setup inicial ou antes de criar uma nova rotina. Momento: depois de `operational demo seed` (para ver o que foi populado) ou ao auditar o plano semanal. Objetivo: revisar as rotinas cadastradas e identificar gaps (ex: "não tenho rotina de EXIT para a NOITE").

## Entradas

- **Do home menu:** opção `7` (Dados & Histórico) → submenu → "Rotinas" (varia conforme versão).
- **Comando direto:** `operational routine list` (lista todas).
- **Comando direto filtrado:** `operational routine list --period MANHA`.

## Saídas

- **Criar nova rotina:** `operational routine create "Nome" MANHA CORE --start-hour 5 --end-hour 6` (SCR-009 — form).
- **Ver detalhes de uma rotina:** (não há sub-comando `show`; usar `routine list` e rolar até o ID).
- **Filtrar por período:** `operational routine list --period NOITE`.

## Argumentos e flags

| Flag | Tipo | Default | Comportamento se omitido | Exemplo |
|------|------|---------|--------------------------|---------|
| `--period` / `-p` | `Period` enum (`MANHA` / `TARDE` / `NOITE`) | `None` | Lista todos os períodos. | `--period MANHA` |
| `--json` | `bool` | `False` | Emite lista de Pydantic models. | `--json` |

Filtro é aplicado em `routines.list(filters={"period": period})` (`routine_cmd.py:93`).

## Conteúdo principal

Uma única `rich.table.Table` com 6 colunas (`routine_cmd.py:108-142`):

1. **Período** — emoji + nome (`🌅 MANHA`, `💻 TARDE`, `🌙 NOITE`), cor por período (`yellow` / `cyan` / `blue`).
2. **Tipo** — `ENTRY` / `CORE` / `TRANSITION` / `EXIT`, cor por tipo (`green` / `cyan` / `yellow` / `magenta`).
3. **Nome** — texto plano (ex: "Despertar Natural + Hidratacao").
4. **Horário** — `04:00→04:25` (start_time→end_time).
5. **Duração** — `25min` ou `3h30` (calculado inline, tratando wrap-around de meia-noite).
6. **ID** — `rou_demo_00_00_2026_06_02` (cinza, monospace).

Ordenação: por `(period_order, start_time)` ASC (`routine_cmd.py:106`) — MANHÃ primeiro, depois por horário.

## Hierarquia visual

- **1º:** Período + emoji (cabeçalho da "categoria" do dia).
- **2º:** Tipo (ENTRY vs CORE vs EXIT) — para identificar a função da rotina.
- **3º:** Nome + Horário — info operacional.
- **4º:** Duração + ID — referência técnica.

## Wireframe ASCII (com dados reais do golden.csv — 14 rotinas)

```
$ operational routine list
                                                                                
  🕐 Rotinas (14)                                                              
                                                                                
  Período    Tipo        Nome                          Horário         Duração  ID
  ────────  ──────────  ────────────────────────────  ──────────────  ───────  ─────────────────────
  🌅 MANHA  ENTRY       Despertar Natural +            04:00→04:25     25min    rou_demo_00_00_…
                          Hidratacao                                                              
  🌅 MANHA  CORE        Deep Work - Feature JWT        04:30→08:00     3h30     rou_demo_00_01_…
  🌅 MANHA  ENTRY       Despertar Tarde +              05:30→05:45     15min    rou_demo_01_00_…
                          Hidratacao Rapida                                                          
  🌅 MANHA  CORE        Deep Work Reduzido             05:50→08:00     2h10     rou_demo_01_01_…
  🌅 MANHA  ENTRY       Acordar com Cafe Forte         06:00→06:10     10min    rou_demo_02_00_…
  🌅 MANHA  CORE        Deep Work Emergencial          06:15→11:00     4h45     rou_demo_02_01_…
  🌅 MANHA  ENTRY       Acordar Sem Pressa             06:00→06:30     30min    rou_demo_03_00_…
  🌅 MANHA  CORE        Refatoracao Leve               06:30→08:00     1h30     rou_demo_03_01_…
  🌅 MANHA  ENTRY       Despertar + Hidratacao         04:00→04:20     20min    rou_demo_04_00_…
  🌅 MANHA  CORE        Deep Work Manha                04:30→07:30     3h00     rou_demo_04_01_…
  🌅 MANHA  ENTRY       Acordar + Cafe da Cama         05:00→05:20     20min    rou_demo_05_00_…
  🌅 MANHA  ENTRY       Meditacao + Alongamento        05:20→05:50     30min    rou_demo_05_01_…
  🌅 MANHA  ENTRY       Acordar + Meditacao            05:00→05:30     30min    rou_demo_06_00_…
  🌅 MANHA  CORE        Deep Work - Preparacao Semana  05:30→08:00     2h30     rou_demo_06_01_…
```

Filtrado por `--period TARDE` retornaria 0 rotinas (o golden só tem rotinas de MANHÃ!):

```
$ operational routine list --period TARDE
                                                                                
  🕐 Rotinas (0)                                                               
                                                                                
  (nenhuma rotina cadastrada para este período)
```

Filtrado por `--period NOITE` idem.

Com `--json`:

```json
[
  {
    "id": "rou_demo_00_00_2026_06_02",
    "name": "Despertar Natural + Hidratacao",
    "period": "MANHA",
    "routine_type": "ENTRY",
    "start_time": "04:00:00",
    "end_time": "04:25:00",
    "mandatory": true,
    "days_of_week": [0, 1, 2, 3, 4, 5, 6],
    "duration_minutes": 25,
    "active_on_weekend": true,
    "created_at": "2026-06-02T04:00:00+00:00",
    "archived": false
  },
  ...
]
```

## Estados (5)

### Estado 1 — Vazio (sem rotinas)

```
$ operational demo clear
$ operational routine list

⚠ Nenhuma rotina cadastrada. Use routine create.
```

Mensagem curta, cor `yellow`, sem painel.

### Estado 2 — Loading

- **Não aplicável** (síncrono, ~10 ms).

### Estado 3 — Com dados (wireframe acima)

- 14 linhas (após `demo seed`). Cores por Período e Tipo. Ordenação por período → horário.

### Estado 4 — Erro

- **`--period INVALIDO`**: Typer exibe `Error: Invalid value for '--period': 'invalido' is not one of 'MANHA', 'TARDE', 'NOITE'`. Saída com código 1.
- **State dir corrompido**: `json.JSONDecodeError` em `routines.list()`. Mitigação: `operational doctor doctor`.

### Estado 5 — Dataset sintético (golden.csv) — caso típico

- 14 rotinas (2 por dia × 7 dias). Todas `MANHA` (o cenário "demo seed" só cria rotinas de manhã). Filtrar por `--period TARDE` ou `--period NOITE` retorna 0 — **não é erro**, é estado vazio.
- Todas com `mandatory=true`, `days_of_week=[0,1,2,3,4,5,6]`, `active_on_weekend=true`.

## Comportamento interativo

- **Aceita input do usuário?** NÃO. Read-only.
- **Tem prompts?** NÃO.
- **Teclas de atalho?** `Ctrl+C` aborta.
- **Mouse?** Sem suporte.

## Comandos relacionados

- `operational routine create` — cria nova rotina (SCR-009).
- `operational routine archive` — soft-delete (a verificar se implementado).
- `operational demo seed` — popula 14 rotinas canônicas.
- `operational home → 1` (Iniciar Manhã) — executa a primeira rotina de `MANHA` do dia.

## Riscos de usabilidade

1. **Coluna `ID` truncada com `…`** (`routine_cmd.py:142` mostra `rou_demo_00_00_…`) — o usuário não consegue copiar o ID completo. Mitigação: mostrar ID completo OU adicionar `--show-id-full`.
2. **Coluna `Duração` não trata durações > 24h** (impossível na prática, mas `routine_cmd.py:130` assume `end_min >= start_min` e adiciona `24*60` se for wrap-around). Wrap-around legítimo: `start=23:00, end=01:00` → `120min`. Funcional, mas não óbvio.
3. **Tabela sem totalizadores** (soma de durações por período). Mitigação: adicionar footer "Total MANHÃ: 18h45".
4. **Sem filtro por `routine_type`** (só por período). Para listar só CORE, não dá.
5. **Coluna `Nome` muito larga** (até 30 chars). Se a rotina tiver nome longo (>30), trunca. Mitigação: `min_width` adaptativo ou `overflow="fold"`.
6. **Não mostra `days_of_week`** na tabela — só no JSON. Usuário que quer auditar "essa rotina roda no domingo?" tem que usar `--json`.

## Métricas de sucesso

- **Tempo até encontrar uma rotina específica**: meta < 5s (se souber o período, filtro; se não, rolar).
- **Taxa de uso do `--period`**: esperado > 50% (filtro é o caso comum).
- **Frequência de criação vs listagem**: ratio > 1:10 (criar é raro, listar para auditar é comum).

## Onde aparece

- Home menu: opção `7` (Dados & Histórico) → submenu.
- Link direto: `operational routine list`.
- Referenciado em `home.py` flow `_flow_morning` (`cli/home.py:157-188`) — antes de iniciar, lista rotinas de MANHÃ.

## Notas de implementação

- Entry point: `cli/commands/routine_cmd.py:85` (`list_routines`).
- Implementação: `rich.table.Table` inline em `routine_cmd.py:108-142` (6 colunas, sort por `period_order, start_time`).
- Cores hardcoded em `routine_cmd.py:21-38` (`ROUTINE_TYPE_COLOR`, `PERIOD_COLOR`, `PERIOD_ICON`). Diferem de `ui/components.py:53-57` (que define `PERIOD_ICON` também — há duplicação).
- Filtro: `routines.list(filters or None)` em `routine_cmd.py:94`. O `Repository.list()` aceita `filters: dict` opcional.
- Console: `make_console(width=120)` em `routine_cmd.py:18` (singleton local, não o de `ui/__init__.py`).
- Performance: ~20 ms (1 `list()` + sort + render).
- Sem `pomodoros_grid`, `cartesian_plane` ou outros componentes do `ui/components.py` — usa só `Table` direto.
