# SCR-003 — Weekly Report

**Comando:** `operational report weekly [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--json]`
**Arquivo renderizador:** `src/operational/cli/commands/report_cmd.py:105-315` (`weekly` — usa `ui.components` e inline `Table.grid` da `rich`)
**Arquivo de comando:** `src/operational/cli/commands/report_cmd.py:105` (`weekly`)
**Tipo:** Output tabular agregado (read-only)
**Modo JSON:** Sim (`--json`)
**Dataset:** qualquer

## Propósito

Resumir **7 dias de operação** em uma única tela: quantas horas foram trabalhadas no total, qual a média de sono, a tendência de produtividade (sparkline), a distribuição por `TipoDia` e por quadrante Q1-Q4, e a posição cartesiana de cada dia. O usuário olha esta tela para responder: *"Como foi minha semana? Mantive o padrão ouro ou preciso de ajuste estrutural?"*

## Usuário-alvo

O próprio usuário, no fim de semana (sábado à noite ou domingo de manhã). Momento: `home → 6 → 2`. Objetivo: detectar padrão (3 dias bons / 2 ruins / 2 ok?) e decidir o regime do PolicyEngine para a semana seguinte (PUSH / MAINTAIN / REDUCE / RECOVER).

## Entradas

- **Do home menu:** opção `6 → 2` (Relatórios → Semanal). O home chama `_run_cmd(["report", "weekly"])`.
- **Comando direto (default = últimos 7 dias):** `operational report weekly` → usa `start=hoje-6`, `end=hoje`.
- **Comando direto com janela custom:** `operational report weekly --start 2026-06-02 --end 2026-06-08`.
- **Com flag JSON:** `operational report weekly --json` (payload mínimo: `start`, `end`, `n_days`, `n_pomodoros`, `n_reflections`).

## Saídas

- **Drill-down em um dia específico:** `operational report daily --date 2026-06-04`.
- **Ver PolicyDecision da semana:** `operational policy decisions` (`policy_cmd.py:40-53`).
- **Exportar o estado:** `operational demo export-csv ./week.csv`.
- **Sair:** `Ctrl+C` ou retorno ao home menu.

## Argumentos e flags

| Flag | Tipo | Default | Comportamento se omitido | Exemplo |
|------|------|---------|--------------------------|---------|
| `--start` / `-s` | `str` (YYYY-MM-DD) | `date.today() - timedelta(days=6)` (`report_cmd.py:126`) | Pega os últimos 7 dias terminando hoje. | `--start 2026-06-02` |
| `--end` / `-e` | `str` (YYYY-MM-DD) | `date.today()` (`report_cmd.py:127`) | Janela termina hoje. | `--end 2026-06-08` |
| `--json` | `bool` | `False` | Emite um dict agregado (sem Rich). Use para scripts/aggregations. | `--json` |

Diferente do `daily`, o semanal **não valida** que `start <= end`. Se invertido, o loop `for offset in range(...)` itera 0 vezes e gera relatório vazio.

## Conteúdo principal

Widgets na ordem top-to-bottom (`report_cmd.py:168-315`):

1. **Header panel** (`_panel("⚡ WEEKLY", ...)` em `report_cmd.py:177`) — Período `start → end` + número de dias. (CMP-2 `section_panel`.)
2. **KPI grid 2×2** (`report_cmd.py:180-194`) — Hardwork (h + orçado%), Pomodoros (total + média/dia), Sono Médio (com min/max), Reflexões (X/Y dias). Usa `kpi_card` (`ui/components.py:341-361`). (CMP-1.)
3. **Sparklines 7-dias** (`report_cmd.py:197-209`) — 3 sparklines (Sono, Produtividade, Pomodoros) com label "Seg Ter Qua Qui Sex Sab Dom" abaixo. (CMP-8 `sparkline`.)
4. **Distribuição por TipoDia** (`report_cmd.py:212-228`) — Tabela com 4 linhas (CURSO, LIVRE, HARDCORE, DESCANSO), contagem e barra `█` proporcional. (CMP-9 `metric_table` + lookup `TIPO_DIA_COLOR`.)
5. **Distribuição por Quadrante** (`report_cmd.py:231-249`) — 4 linhas (Q1, Q2, Q3, Q4) com cor por quadrante e barra. (CMP-9 + `QUADRANT_COLOR`.)
6. **Posição Diária** (`report_cmd.py:252-275`) — Tabela com 7 linhas (uma por dia): data, Tipo, X%, Y%, Quadrante, 🍅 (pomodoros).
7. **Distribuição do Sono** (`report_cmd.py:278-293`) — Métricas: Média, Mínimo, Máximo, Dias < 6h, Dias 7-9h, Dias > 9h. Cor por severidade (`sev` calculado inline).
8. **Next-step panel** (`report_cmd.py:296-313`) — Três branches: (a) ≥1 dia em Q3 → `crit` "revisar padrão sono+trabalho urgente"; (b) `avg_x < 50` → `warn` "aumentar volume"; (c) senão → `ok` "manter ritmo". (CMP-3.)

## Hierarquia visual

- **1º:** Header com intervalo e a **next-step panel** no rodapé (se for `crit` em Q3, salta aos olhos).
- **2º:** KPI grid 2×2 (status rápido da semana).
- **3º:** Sparklines (tendência visual — alta/baixa/estável).
- **4º:** Tabelas de distribuição (drill-down numérico).

## Wireframe ASCII (com dados reais do golden.csv — semana 2026-06-02 → 2026-06-08)

```
+==============================================================+
|  📈  WEEKLY REPORT  ·  2026-06-02 → 2026-06-08  ·  7 dias     |
+==============================================================+
|                                                              |
|  +-------------------+  +-------------------+                |
|  |  💻 Hardwork      |  |  🍅 Pomodoros      |                |
|  |  34h00            |  |  54                |                |
|  |  orçado 40h · 85% |  |  média 7.7/dia     |                |
|  +-------------------+  +-------------------+                |
|                                                              |
|  +-------------------+  +-------------------+                |
|  |  😴 Sono Médio    |  |  🎯 Reflexões      |                |
|  |  7.4h             |  |  7/7              |                |
|  |  min 4.0h · 10.0h |  |  dias com OKRs     |                |
|  +-------------------+  +-------------------+                |
|                                                              |
|  ── 📈 Tendências 7-dias  ────────────────────────────────   |
|   😴 Sono          ▂▃▁█▆▅▇  min 4.0h / max 10.0h              |
|   📈 Produtividade ▆▅▃▅▃▆▇  média 84%                          |
|   🍅 Pomodoros     ██▁█▁███  total 54                         |
|     Seg Ter Qua Qui Sex Sab Dom                                |
|                                                              |
|  ── 🗓️ Distribuição por TipoDia  ─────────────────────────   |
|   CURSO    3  █████████                                        |
|   LIVRE    2  ██████                                           |
|   HARDCORE 1  ███                                              |
|   DESCANSO 1  ███                                              |
|                                                              |
|  ── 📊 Distribuição por Quadrante  ───────────────────────   |
|   Q1   5  ████████████████                                     |
|   Q2   0  —                                                   |
|   Q3   1  ███  ← 2026-06-04 (HARDCORE)                         |
|   Q4   1  ███                                                  |
|                                                              |
|  ── 🗓️ Posição Diária (X, Y, Quadrante)  ─────────────────   |
|   Data         Tipo      X    Y    Q    🍅                    |
|   2026-06-02   CURSO     100  100  Q1   11                     |
|   2026-06-03   CURSO     75   75   Q1   6                      |
|   2026-06-04   HARDCORE  73   73   Q1   8                      |
|   2026-06-05   DESCANSO  75   75   Q1   3                      |
|   2026-06-06   CURSO     88   88   Q1   7                      |
|   2026-06-07   LIVRE     89   89   Q1   8                      |
|   2026-06-08   LIVRE     78   78   Q1   7                      |
|                                                              |
|  ── 😴 Distribuição do Sono (7 dias)  ────────────────────   |
|   Média     7.4h                                              |
|   Mínimo    4.0h  🔴                                           |
|   Máximo    10.0h 🟢                                           |
|   Dias < 6h      1  ⚠                                          |
|   Dias 7-9h      5  ✓                                          |
|   Dias > 9h      1                                              |
|                                                              |
|  !  1 dia(s) em Q3 (Crítico). Revisar padrão sono+trabalho   |
|     urgente.                                                 |
+==============================================================+
```

> Nota: os `X` e `Y` no golden.csv usam a fórmula simplificada `y = x` (report_cmd.py:234) — em produção real, `y = efficiency_pct = foco / total`. O exemplo acima reflete o que o report_cmd.py efetivamente produz ao ler o golden.

## Estados (5)

### Estado 1 — Vazio (janela sem dados)

- `n_pomodoros=0`, `avg_sleep=0.0`, todas as sparklines viram `(sem dados)`.
- `next_step_panel` mostra `warn` "Produtividade média 0% (abaixo de 50%). Aumentar volume de trabalho."
- Tabelas de distribuição mostram zeros com `—` em vez de barras.

### Estado 2 — Loading

- **Não aplicável** (CLI síncrona). Mas: o loop `for offset in range((we - ws).days + 1)` chama `get_day_snapshot` para cada dia — 7 iterações × ~80 ms ≈ 560 ms. Aceitável sem barra de progresso.
- Janelas maiores (`--start 2025-01-01 --end 2025-12-31` = 365 dias) demoram ~30s e travam o terminal. Nenhuma indicação de progresso.

### Estado 3 — Com dados (wireframe acima)

- 5 widgets renderizam (header, KPIs, sparklines, TipoDia, Quadrante, Posição Diária, Sono, next-step).
- Severidade das cores reflete a média semanal (84% → majoritariamente verde).

### Estado 4 — Erro

- **Data inválida em `--start` ou `--end`:** `date.fromisoformat` levanta `ValueError` → Typer exibe erro de parsing e sai com código 1.
- **`start > end`:** não levanta erro, mas o relatório fica vazio. (Risco de usabilidade!)
- **State dir corrompido:** `json.JSONDecodeError` sobe para o traceback. Workaround: `operational doctor doctor`.
- **`--json` + erro:** o payload JSON não é emitido; o erro vai para stderr.

### Estado 5 — Dataset sintético (golden.csv) — usado para QA

- O golden é **a semana de 7 dias** acima (2026-06-02 → 2026-06-08) com cenários canônicos:
  - 1 CURSO perfeito (2026-06-02, "DIA PERFEITO", 11/12 pomodoros).
  - 1 CURSO desvio leve (2026-06-03, Q3 segundo a fórmula `y=x` que não bate com `efficiency_pct` real).
  - 1 HARDCORE (2026-06-04, deadline 16:55).
  - 1 DESCANSO (2026-06-05, sono 10h, recuperação).
  - 1 CURSO com lunch pesado (2026-06-06, cochilo).
  - 1 LIVRE perfeito (2026-06-07, fim de semana, Q1).
  - 1 LIVRE com visita (2026-06-08, interrupção social absorvida).
- Layout idêntico ao production.

## Comportamento interativo

- **Aceita input do usuário?** NÃO. Read-only.
- **Tem prompts?** NÃO, exceto o "Press Enter to continue" do home menu.
- **Teclas de atalho?** `Ctrl+C` aborta. Não há `q` específico.
- **Mouse?** Sem suporte.

## Comandos relacionados

- `operational report daily --date 2026-06-04` — drill-down em um dia.
- `operational policy decisions` — lista as 7 PolicyDecisions da semana (1/dia).
- `operational state show` — visão "agora".
- `operational demo week` — seed do golden + chama `report weekly` em sequência.

## Riscos de usabilidade

1. **Loop silencioso ao usar `start > end`**: o comando aceita e devolve relatório vazio. Mitigação: adicionar `if start > end: raise typer.BadParameter(...)` em `report_cmd.py:126-127` (issue conhecida, ver `INTEGRATION-BACKLOG.md`).
2. **Tabela "Posição Diária" usa fórmula simplificada `y=x`** (`report_cmd.py:234`, `report_cmd.py:262`) — o que distorce a leitura do quadrante. O usuário que conhece a fórmula canônica `y = efficiency_pct` vai notar a discrepância. Mitigação documentada: a versão V3 está marcada como "kept lighter — delegate to daily report for now" (`report_cmd.py:101`).
3. **Sparkline com 7 valores fixos**: se a janela não tem 7 dias, o `_resample` estica/comprime (`renderers.py:387-398`), o que pode suavizar tendências enganosamente. Mitigação: documentar no help.
4. **Janelas > 30 dias** degradam a performance (~30s travado). Mitigação: cachear snapshots ou mover para query indexada.
5. **Não há botão "drill-down" do dia**: o usuário precisa copiar a data e digitar `report daily --date 2026-06-04`. Mitigação: implementar hyperlinks Rich (SGR 8) — fora do escopo V3.
6. **A distribuição do quadrante mistura a fórmula simplificada** com a canônica. No golden, todos os 7 dias caem em Q1; numa semana real (com `efficiency_pct` calculado), espera-se mais variabilidade.

## Métricas de sucesso

- **Tempo até encontrar a info**: meta < 5s para o quadrante semanal.
- **Janela mais usada**: esperado `default` (últimos 7 dias, ~70%); janela custom (30%).
- **Taxa de drill-down**: % de sessões que abrem `report daily` após `report weekly` — meta > 40% (sinal de que o weekly gera perguntas).

## Onde aparece

- Home menu: opção `6 → 2`.
- Referenciado em `policy_cmd.py:42` ("policy decisions") como input da próxima semana.
- Atalho de demo: `operational demo week` (`demo_cmd.py:66-77`) roda seed + `report weekly` em sequência.

## Notas de implementação

- Entry point: `cli/commands/report_cmd.py:105` (`weekly`).
- Renderer: construtor inline em `report_cmd.py:168-315` (mistura `rich.table.Table` e componentes de `ui.components`).
- Diferente do `daily`, **não** delega para `ui/weekly_report.py` — comentário em `report_cmd.py:101`: "kept lighter — delegate to daily report for now". Refactor pendente.
- Loop de dias: `for offset in range((we - ws).days + 1)` em `report_cmd.py:136`; para cada dia, chama `get_day_snapshot(d)`.
- Sparklines: `sparkline(sleep_by_day, color="sleep", label=...)` em `report_cmd.py:202-204`; usa bloco `▁▂▃▄▅▆▇█`.
- Largura do console: respeitada via `CONSOLE_WIDTH` em `report_cmd.py:116`.
- Próximo refactor: extrair para `ui/weekly_report.py:render_weekly_report(snap_list)` seguindo o padrão de `ui/daily_report.py`.
