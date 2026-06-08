# SCR-004 — State Dashboard

**Comando:** `operational state show [--date YYYY-MM-DD] [--json]`
**Arquivo renderizador:** `src/operational/cli/commands/state_cmd.py:133-277` (`_render_dashboard`)
**Arquivo de comando:** `src/operational/cli/commands/state_cmd.py:71-130` (`show`)
**Tipo:** Output dashboard "agora" (read-only)
**Modo JSON:** Sim (`--json`)
**Dataset:** qualquer

## Propósito

Responder a 3 perguntas imediatas: **(1) Em que período do dia estou agora** (MANHÃ/TARDE/NOITE)? **(2) O que está logado** (rotinas, pomodoros, blocos)? **(3) Estou no plano** (orçado vs realizado do período corrente)?. É a tela que o usuário abre pressionando **Enter** no home menu (default da `Prompt.ask` em `home.py:107`).

## Usuário-alvo

O próprio usuário, várias vezes ao dia, especialmente em momentos de transição. Momento: "acabei de almoçar, vou trabalhar" ou "estou com dúvida se fiz o suficiente". Objetivo: decidir o que fazer agora (a `next_step` aponta para a opção correta do menu).

## Entradas

- **Do home menu:** opção `5` (Dashboard do Dia), OU pressionar **Enter** sem digitar nada (default da `Prompt.ask` em `cli/home.py:107`).
- **Comando direto:** `operational state show` (default = hoje).
- **Comando direto com data:** `operational state show --date 2026-06-04` (revisão histórica — sempre retorna como se fosse "agora", mas com os dados do dia).

## Saídas

- **Iniciar o fluxo correto do dia:** `operational home → 1 / 2 / 3` (Manhã / Tarde / Noite) — a `next_step` da tela já indica qual.
- **Drill-down completo:** `operational report daily --date 2026-06-08` (SCR-002).
- **Check-in rápido:** `operational metric energy -e 7 -f 8` (popula o card "Energia/Foco" da próxima vez que abrir).
- **Sair:** `Ctrl+C` ou retorno ao menu.

## Argumentos e flags

| Flag | Tipo | Default | Comportamento se omitido | Exemplo |
|------|------|---------|--------------------------|---------|
| `--date` / `-d` | `str` (YYYY-MM-DD) | `date.today()` (`state_cmd.py:77`) | Lê dados de hoje. | `--date 2026-06-04` |
| `--json` | `bool` | `False` | Emite um dict com `period_now`, `sleep`, `blocks_today`, `pomodoros_completed`, etc. Use para integração com scripts. | `--json` |

Diferente do `daily`, o `state show` **lê 7 repos diretamente** (`state_cmd.py:82-87`) em vez de chamar `get_day_snapshot`. Isso é mais barato para o caso de uso "agora" (não precisa do frozen `DaySnapshot`).

## Conteúdo principal

Widgets na ordem top-to-bottom (`state_cmd.py:148-277`):

1. **Header panel** (`state_cmd.py:156-162`) — Data + período atual (🌅 MANHÃ / 💻 TARDE / 🌙 NOITE) com cor semântica (`yellow1` / `deep_sky_blue1` / `medium_purple`). (CMP-2 `section_panel`.)
2. **KPI grid 2×2** (`state_cmd.py:164-214`):
   - **Sono** (`kpi_card` com `color=sleep`): `Q=8/10 · 20:30→04:00` no footer.
   - **Pomodoros** (`color=hardwork`): `0` ou `n` completos.
   - **Hardwork** (`color=hardwork` ou `warn`): `actual/budget min · pct% atingido`. Cor verde se `>= 100%`, amarelo caso contrário.
   - **Energia/Foco** (`color=energy/warn/crit`): `E8/F9` com média no footer. Cor depende da média (≥7 verde, 5-6 amarelo, <5 vermelho).
   (CMP-1 `kpi_card`.)
3. **Pomodoros grid 3 sessões** (`state_cmd.py:217-233`) — S1 manhã / S2 tarde / S3 noite com células ▣/▢. Distribuição calculada a partir de `n_pomodoros` e `period_now`. (CMP-5 `pomodoros_grid`.)
4. **Time blocks timeline** (`state_cmd.py:236-247`) — Só aparece se houver blocos logados no dia. Renderiza `timeline_h(blocks, width=58, color="hardwork")`. (CMP-11.)
5. **Atividade do Dia** (`state_cmd.py:249-257`) — Tabela com 4 linhas: Rotinas logs, Ajustes finos, Journal, Blocos. Cada linha tem severity `ok`/`warn`/`muted`. (CMP-9 `metric_table`.)
6. **Next-step panel** (`state_cmd.py:259-277`) — Três branches: (a) journal pendente à noite → `warn` "use reflect saida"; (b) zero pomodoros em MANHÃ/TARDE → `warn` "use metric energy"; (c) senão → `ok` "Iniciar [Manhã/Tarde/Noite] → opção N". (CMP-12 `next_step`.)

## Hierarquia visual

- **1º:** Período atual (MANHÃ/TARDE/NOITE) com cor distinta — é a resposta imediata "onde estou".
- **2º:** KPI grid 2×2 (Sono + Pomodoros + Hardwork + Energia/Foco) — um "card de status" em < 3 segundos.
- **3º:** Pomodoros grid + Timeline — visualização do que foi feito.
- **4º:** Atividade + Next-step — lista de contadores e o **call-to-action**.

## Wireframe ASCII (com dados reais do golden.csv — dia 2026-06-08, 14:30 — tarde)

```
+==============================================================+
|  ⚡  STATE  ·  2026-06-08  ·  💻 TARDE                         |
+==============================================================+
|                                                              |
|  +--------------------+  +--------------------+               |
|  |  😴  Sono          |  |  🍅  Pomodoros      |               |
|  |  9.0h              |  |  2                 |               |
|  |  Q=9/10 · 20:00→05 |  |  completos hoje     |               |
|  +--------------------+  +--------------------+               |
|                                                              |
|  +--------------------+  +--------------------+               |
|  |  💻  Hardwork      |  |  ⚡  Energia/Foco   |               |
|  |  6h00              |  |  7/6               |               |
|  |  360/240min · 150% |  |  média 6/10 · E7 F6|               |
|  +--------------------+  +--------------------+               |
|                                                              |
|  ── 🍅 Pomodoros (S1 manhã · S2 tarde · S3 noite)  ───────   |
|    S1 manhã   ▣ ▣ ▢ ▢   2/4                                    |
|    S2 tarde   ▢ ▢ ▢ ▢   0/4                                    |
|    S3 noite   ▢ ▢ ▢ ▢   0/4                                    |
|                                                              |
|  ── 📦 Time Blocks (2 blocos, 360min)  ───────────────────   |
|     ████████ 05h Deep Work - Preparacao Semana               |
|     █████████ 08h Deep Work - Review do Plano                 |
|                                                              |
|  ── Atividade do Dia  ───────────────────────────────────   |
|   Métrica                Valor                                |
|   🕐 Rotinas logs        2   ✓                                |
|   🔧 Ajustes finos       1   ✓                                |
|   📓 Journal             pendente ⚠                           |
|   📦 Blocos              2   ✓                                |
|                                                              |
|  !  Journal de hoje não foi feito. Use reflect saida para   |
|     registrar OKRs de saída.                                  |
+==============================================================+
```

> Nota: como `state show` usa `_period_now(now)` baseado no **horário real** (`state_cmd.py:50-56`), o wireframe acima assume que a consulta foi feita às 14:30. O JSON payload resultante é o mesmo do CLI.

## Estados (5)

### Estado 1 — Vazio (sem dados para a data, ou "agora" sem nada logado)

- KPI Sono: `—` com footer `não registrado` (cor `crit`).
- KPI Pomodoros: `0` (cor `hardwork`).
- KPI Hardwork: `0h00` com footer `0/180min · 0%` (cor `warn`).
- KPI Energia/Foco: `—/—` com footer `não registrado` (cor `muted`).
- Pomodoros grid: 0/4 em todas as sessões.
- Time blocks timeline: **não renderiza** (sem blocos).
- Atividade: todos os valores `0` ou `pendente`.
- Next-step: "Nenhum pomodoro registrado em MANHÃ. Use metric energy -e 7 -f 8 para check-in." (severity `warn`).

### Estado 2 — Loading

- **Não aplicável** (CLI síncrona). Mas: as 7 listagens em `state_cmd.py:82-87` chamam `repo.list()` para cada repo; em estado com 365 dias × 14 entidades, isso pode demorar ~200ms. Aceitável sem barra.

### Estado 3 — Com dados (wireframe acima)

- 6 widgets renderizam. Cores semânticas ativas: Sono `dodger_blue2`, Pomodoros `green3`, Hardwork `green3` (atingido) ou `yellow` (abaixo), Energia/Foco `energy`/`warn`/`crit` pela média.

### Estado 4 — Erro

- **Data inválida:** Typer exibe erro de parsing. `date.fromisoformat("2026-13-99")` → `ValueError`.
- **State dir inacessível:** `PermissionError` sobe como traceback.
- **JSON corrompido em um repo:** o `repo.list()` (que faz `_load_all()`) levanta `json.JSONDecodeError`. Mitigação: `operational doctor doctor`.

### Estado 5 — Dataset sintético (golden.csv, dia 2026-06-04 = HARDCORE)

- 2026-06-04 às 14:00 (TARDE) mostra:
  - Sono: `4.0h` `Q=4/10 · 02:00→06:00` (cor `crit`).
  - Pomodoros: `2`.
  - Hardwork: `8h00` `480/240min · 200%` (cor `hardwork`).
  - Energia/Foco: `4/4` média 4/10 (cor `crit`).
  - Time blocks: 2 blocos (Deep Work Emergencial 06:15-11:00 + Continuação Relatório 11:15-15:00).
- Atividade: Journal = `pendente` (severity `warn`) → `next_step` em `crit`/`warn`.

## Comportamento interativo

- **Aceita input do usuário?** NÃO. Read-only.
- **Tem prompts?** NÃO.
- **Teclas de atalho?** `Ctrl+C` aborta.
- **Mouse?** Sem suporte.

## Comandos relacionados

- `operational home` → opção `5` (atalho para esta tela — default do `Prompt.ask`).
- `operational home` → opção `6` → `1` (relatório diário completo).
- `operational metric energy -e 7 -f 8` — check-in de energia/foco (popula o card 4).
- `operational reflect saida` — fecha o Journal.

## Riscos de usabilidade

1. **`_period_now` em `state_cmd.py:50-56` usa horário UTC (`datetime.now(timezone.utc)`)** — não usa o fuso local. Em SP (UTC-3), às 02:00 local = 05:00 UTC = MANHÃ (porque `PAV.HORARIO_ACORDAR_MIN <= h <= PAV.HORARIO_ACORDAR_MAX` = `4 <= h <= 11`). Se o usuário mora em fuso diferente, a "tarde" pode aparecer descolada. Mitigação: usar `datetime.now()` (naive, hora local) ou `timezone='America/Sao_Paulo'`.
2. **Time blocks timeline só renderiza se houver blocos**: pode confundir usuários que esperam ver uma barra vazia indicando "nada planejado". Mitigação: adicionar um placeholder `(nenhum bloco planejado para hoje)`.
3. **Cálculo `s1`/`s2`/`s3` em `state_cmd.py:217-223` é uma heurística simples** que depende de `period_now` (não da distribuição canônica `distribute_pomodoros_across_sessions` que o `daily_report` usa). Pode haver divergência entre a tela "agora" e o relatório "do dia".
4. **Card "Energia/Foco" mostra `—/—` mesmo se apenas um dos dois foi registrado** (lógica em `state_cmd.py:191-200`). Ex: `energia=7, foco=None` → mostra `7/—` (parece dado faltando, não "ainda não preenchi").
5. **Layout assume console ≥ 100 col** (4 cards de `width=30` em grid 2×2 = ~64 col + padding). Em terminais estreitos, faz wrap.

## Métricas de sucesso

- **Press Enter para ver onde estou** — meta: < 3s para identificar período (1º widget).
- **Taxa de uso a partir do home menu**: esperado > 50% (é o default).
- **Aderência à recomendação da `next_step`**: % de vezes que o usuário executa a ação sugerida (Iniciar Manhã / Tarde / Noite / Check-in / Reflect). Meta: > 30% (sinal de que a recomendação é útil).

## Onde aparece

- Home menu: opção `5` (e default do `Prompt.ask` em `home.py:107`).
- Link direto: `operational state show`.
- Pode ser referenciado como "dashboard rápido" no help de outros comandos.

## Notas de implementação

- Entry point: `cli/commands/state_cmd.py:71` (`show`).
- Renderer: `_render_dashboard` em `state_cmd.py:133-277` — usa `kpi_card`, `pomodoros_grid`, `metric_table`, `next_step`, `timeline_h` de `cli/renderers.py`.
- Diferente do `daily` report, **não usa** `ui/daily_report.py` nem `get_day_snapshot`. Lê 7 repos diretamente em `state_cmd.py:82-87` (routines logs, ajustes, journals, pomodoros, time_blocks, sleep_records). Custo: 7×O(n) por `list()`. Em datasets grandes, isso é mais lento que `get_day_snapshot` (~80ms).
- Cálculo do período: `_period_now(now)` em `state_cmd.py:50-56`; usa constantes `PAV.HORARIO_ACORDAR_MIN`/`MAX` e `PAV.HORARIO_DORMIR_MIN` de `operational/constants.py`.
- Cores do período: hardcoded no dict em `state_cmd.py:149-153` (não usa `PERIOD_ICON` de `ui/components.py:53-57`).
- Largura do console: `make_console(width=120)` em `state_cmd.py:43`.
