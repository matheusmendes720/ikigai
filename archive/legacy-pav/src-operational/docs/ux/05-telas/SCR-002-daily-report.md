# SCR-002 — Daily Report

**Comando:** `operational report daily [--date YYYY-MM-DD] [--json]`
**Arquivo renderizador:** `src/operational/ui/daily_report.py:281-316` (`render_daily_report`)
**Arquivo de comando:** `src/operational/cli/commands/report_cmd.py:45-97` (`daily`)
**Tipo:** Output tabular rico (read-only)
**Modo JSON:** Sim (`--json`)
**Dataset:** qualquer (production / synthetic / golden)

## Propósito

Mostrar um **raio-X completo de um único dia**: quanto dormiu, quanto trabalhou, em que quadrante do plano cartesiano o dia caiu (Q1-Q4), o que funcionou, o que deu errado e qual a **próxima ação recomendada** para corrigir ou manter o ritmo. O usuário olha esta tela para responder: *"Como foi meu dia de hoje e o que ajusto amanhã?"*

## Usuário-alvo

O próprio usuário, no fim do dia (após `operational home → 3 🌙 Encerrar Dia`) ou revisando um dia passado. Momento: à noite, antes do shutdown. Objetivo: validar se cumpriu o plano, registrar reflexões, ver o quadrante e o ajuste fino recomendado.

## Entradas

- **Do home menu:** opção `6 → 1` (Relatórios → Diário). O home chama `_run_cmd(["report", "daily"])`.
- **Comando direto:** `operational report daily`
- **Comando direto com data:** `operational report daily --date 2026-06-04`
- **Com flag JSON:** `operational report daily --date 2026-06-08 --json`

## Saídas

- **Abrir o relatório semanal:** `operational report weekly --start 2026-06-02 --end 2026-06-08`
- **Abrir o dashboard do dia (state):** `operational state show`
- **Exportar o estado:** `operational demo export-csv ./snapshot.csv`
- **Sair:** `Ctrl+C` (TTY) ou simplesmente não responder (TTY prompt).

## Argumentos e flags

| Flag | Tipo | Default | Comportamento se omitido | Exemplo |
|------|------|---------|--------------------------|---------|
| `--date` / `-d` | `str` (YYYY-MM-DD) | hoje (`date.today()`) | Usa a data atual. Typer parseia via `date.fromisoformat` em `report_cmd.py:51`. | `--date 2026-06-04` |
| `--json` | `bool` | `False` | Emite um dict flat em stdout via `format_as_json` (sem Rich). Use para pipe com `jq` ou scripts. | `--json` |

A data é validada pelo `date.fromisoformat` da stdlib; datas malformadas (`2026-13-99`) levantam `ValueError` e o Typer mostra erro de parsing. Para erros de domínio (ex.: dia 30 anos no futuro), o sistema confia no `DaySnapshot` (vazio se não houver dados).

## Conteúdo principal

Os widgets aparecem **na ordem top-to-bottom** abaixo (fonte: `daily_report.py:281-316`):

1. **Header panel** (`build_header_table`, `daily_report.py:50-82`) — Data · TipoDia (CURSO/LIVRE/HARDCORE/DESCANSO) · Quadrante (Q1/Q2/Q3/Q4) · Pomodoros `n/meta`. (CMP-2 `section_panel` + emoji do quadrante via `QUADRANT_EMOJI`.)
2. **EASE table** (`build_ease_table`, `daily_report.py:85-130`) — 10 linhas: Acordou, Dormiu, Sono, Qualidade, Workout, Meditação, Lunch, Jantar < 18h, Luz azul, Transições. Cores via `sev_for_*`. (CMP-2 + CMP-10 `severity_text`.)
3. **HARDWORK table** (`build_hardwork_table`, `daily_report.py:133-170`) — Tipo, Orçado, Realizado, Δ Desvio, Pomodoros. (CMP-2 + CMP-10.)
4. **Pomodoros grid** (`build_pomodoros_grid_section`, `daily_report.py:319-327`) — 3 sessões (S1 manhã, S2 tarde, S3 noite) × 4 rounds. (CMP-5 `pomodoros_grid`.)
5. **Estado Subjetivo** (`build_energia_foco_section`, `daily_report.py:330-335`) — Barras de progresso Energia + Foco (1-10). (CMP-7 `progress_bar`.)
6. **Cartesian panel** (`build_cartesian_panel`, `daily_report.py:204-218`) — Plano X (Produtividade) × Y (Eficiência) com o ponto do dia e legenda do quadrante. (CMP-6 `cartesian_plane`.)
7. **Desvios / Ajustes / Lições** (`build_desvios_ajustes_panel`, `daily_report.py:221-234`) — 3 listas alinhadas, opcionais (só aparece se houver dados).
8. **OKRs V3** (`build_okrs_panel`, `daily_report.py:237-257`) — Big-Win, Parar de fazer, Repetir, Deu certo, Deu errado, Maior aprendizado. (CMP-2 + emoji.)
9. **Next-step panel** (`build_next_step_panel`, `daily_report.py:260-278`) — Recomendação condicional: `crit` se Q3 ou sono < 6h; `ok` se meta batida; `info` caso contrário. (CMP-3 `next_step_panel`.)

## Hierarquia visual

O que o usuário vê **primeiro** (foco), **segundo**, **terceiro**:

- **1º:** Quadrante (emoji + código Q1/Q2/Q3/Q4) e a cor da `next_step_panel` no rodapé. Se vermelho (Q3 ou sono < 6h), o usuário imediatamente lê a recomendação.
- **2º:** KPI block "HARDWORK" — orçado vs realizado + delta. Resposta direta à pergunta "cumpri a meta?".
- **3º:** Cartesiano + Pomodoros grid — visualização da posição e do esforço.
- **4º:** Detalhes (EASE, OKRs, desvios) — para drill-down textual.

## Wireframe ASCII (com dados reais do golden.csv — dia 2026-06-04 = HARDCORE Q1)

```
+==============================================================+
|  📅  2026-06-04     ◆ HARDCORE     🚨 Q1     🍅 2/11          |
+==============================================================+
|                                                              |
|  ── 😴 EASE  ─────────────────────────────────────────────   |
|   ⏰ Acordou            06:00                                 |
|   🌙 Dormiu             02:00                                 |
|   😴 Sono               4.0h 🟡                                |
|   ⭐ Qualidade          4/10  ⚠                                |
|   💪 Workout            não feito                              |
|   🧘 Meditação          não feita                              |
|   🍽️  Lunch             10min eat + 20min rest = 30min ⚠ PESADO|
|   🌆 Jantar < 18h       tarde (luz azul)                       |
|   📱 Luz azul           exposição após 18h                     |
|   🔄 Transições         5/5                                    |
|                                                              |
|  ── 💻 HARDWORK  ─────────────────────────────────────────   |
|   Tipo de Dia           HARDCORE                               |
|   📊 Orçado             660min (11h00m)                        |
|   ⏱️  Realizado          480min (8h00m)                        |
|   Δ Desvio              -180min (MUITO_ABAIXO) 🔴              |
|   🍅 Pomodoros          2/11 rounds ⚠                          |
|                                                              |
|  ── 🍅 Pomodoros Grid — S1 manhã · S2 tarde · S3 noite  ─    |
|    S1 manhã   ▣ ▢ ▢ ▢   1/4                                    |
|    S2 tarde   ▣ ▢ ▢ ▢   1/4                                    |
|    S3 noite   ▢ ▢ ▢ ▢   0/4                                    |
|                                                              |
|  ── ⚡ Estado Subjetivo  ──────────────────────────────────   |
|   ⚡ Energia  ████████░░░░░░░░░░░░  40%  (4/10)                |
|   🎯 Foco     ████████████░░░░░░░░  60%  (6/10)                |
|                                                              |
|  ── 📈 Plano Cartesiano — X: 72 · Y: 72  ─────────────────    |
|  Y%                  X% (Produtividade)                       |
|  100                                                     ◆    |
|   50 ─ ─ ─ ─ ─ ─ ─ ─┊─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─                |
|    0 ┼──────────────────────────────────────────             |
|       0                  50                          100     |
|   Q1  —  Bom — manter ritmo                                  |
|   Ação: Manter                                                |
|                                                              |
|  ── ⚠️  Desvios · 🔧 Ajustes · 📚 Lições  ─────────────────   |
|   ⚠️  Desvio   Sono 4h. Infração GRAVE se repetida (max 2x/mês)|
|   ⚠️  Desvio   Almoço reduzido (5min eat + 20min rest vs padrão)|
|   🔧 Ajuste    RECUPERAÇÃO: dormir 18:00h hoje (9h sono comp.) |
|   📚 Lição     Adrenalina + deadline seguram foco 3h.         |
|                                                              |
|  ── 🎯 OKRs V3 — Reflexão do dia  ─────────────────────────   |
|   🏆 Big-Win            Relatório entregue 5min antes         |
|   ❌ Parar de fazer     Subestimar deadlines                   |
|   ✅ Repetir            Café estratégico 2:30h p/ sonolência   |
|   ❌ Deu errado         Recuperei pouco — sono acumulado cobra |
|   💡 Maior aprendizado  4h sono é sustentável 1 dia, mas cobra|
|                                                              |
|  ✓  RECUPERAR: dormir 18:00h hoje (9h sono compensatório)    |
+==============================================================+
```

## Estados (5)

### Estado 1 — Vazio (sem dados para a data)

- `DaySnapshot` retorna campos vazios: `sleep=None`, `n_pomodoros=0`, `n_blocks=0`, `n_logs=0`.
- KPI cards mostram `—` (cinza) em vez de números.
- Cartesian mostra o ponto na origem (0,0) — `✗` em vermelho.
- `next_step_panel` exibe mensagem `info`: *"Nenhum dado para esta data. Use `operational routine create`..."*
- EASE table mostra todos os campos como `—`.

### Estado 2 — Loading

- **Não aplicável** — a CLI é síncrona. O relatório renderiza em ~20-80 ms (ver `05-DATA-FLOW.md`).
- Exceção: se o `state_dir` tiver milhares de entidades (CSV com 365 dias × 14 entidades), `get_day_snapshot` pode demorar ~500 ms. Nenhuma barra de progresso é mostrada — o prompt do Typer fica "mudo" durante esse tempo.

### Estado 3 — Com dados (exemplo acima — 2026-06-04 HARDCORE)

- Wireframe completo (visto acima).
- Header: `◆ HARDCORE`, `🚨 Q1` (note: quadrante Q1 mesmo com `MUITO_ABAIXO` no delta, porque `productivity_pct=72.7` ainda é `≥ 50`).
- `next_step_panel` em verde (`ok`) — *"Dia dentro do padrão..."* (porque o ponto está em Q1).
- Wait: `build_next_step_panel` (`daily_report.py:260-278`) **força `crit`** se `sleep.duration_hours < 6` — e 4.0h satisfaz isso. Logo a recomendação final é `crit`: *"Aplicar plano de recuperação antes de continuar. Sono < 6h ou Q3 detectado."*

### Estado 4 — Erro

- **Data inválida** (`--date 2026-13-99`): Typer exibe `Error: Invalid value for '--date': invalid date format` e sai com código 1. Não chega a chamar `render_daily_report`.
- **State dir corrompido** (JSON inválido): a exceção sobe para `typer_app`; o usuário vê um traceback Rich. Workaround: `operational doctor doctor` para localizar o arquivo problemático (`doctor_cmd.py:60-99`).
- **Sem permissão de leitura**: `PermissionError` → traceback. Solução: `chmod +r ~/.time-tasker/*.json` ou `operational doctor doctor`.

### Estado 5 — Dataset sintético (golden.csv)

- Carregado via `operational demo import_csv docs/golden.csv` ou via `TIME_TASKER_DATASET=golden` antes de invocar o CLI.
- O layout é **idêntico** ao do production — só mudam os dados. Dia 2026-06-02 vira CURSO Q1 (100% / 100% / 11/12 pomodoros — *"DIA PERFEITO"*). Dia 2026-06-04 vira HARDCORE Q1 (72.7% / 50% / 8/11 pomodoros — *"Modo Hardcore Ativado"*).
- Útil para QA: o golden tem um dia em cada cenário canônico (CURSO, DESVIO_LEVE, HARDCORE, DESCANSO, LIVRE, etc.).

## Comportamento interativo

- **Aceita input do usuário?** NÃO. Read-only. Não há prompts depois que o relatório começa a renderizar.
- **Tem prompts?** NÃO, exceto o retorno ao home menu (`Press Enter to continue`).
- **Teclas de atalho?** `Ctrl+C` aborta o processo inteiro. Não há tecla `q` no relatório (somente no home menu).
- **Mouse?** Sem suporte — o terminal não captura cliques para read-only views.

## Comandos relacionados

- `operational report weekly --start 2026-06-02 --end 2026-06-08` — agrega 7 dias.
- `operational state show` — visão "agora" (2×2 KPI grid + activity table).
- `operational doctor doctor` — diagnóstico de ambiente.
- `operational demo export-csv ./out.csv` — exporta o estado (incluindo o `DaySnapshot` da data consultada).
- `operational reflect saida` — abre o formulário de reflexão (Big-Win, Parar de Fazer, etc.) que popula o painel "OKRs V3".

## Riscos de usabilidade

1. **Quadrante Q3 sem legenda inline**: se o usuário não conhece o vocabulário Q1-Q4, pode ver `🚨 Q3` e pânico sem entender que isso é `x<50 AND y<50`. Mitigação: a próxima-ação embaixo sempre diz "Revisão urgente".
2. **Cor `bold red` (Q3) pode ser invisível para daltônicos** (protanopia/deuteranopia). Mitigação: o `✗` no cartesiano e o emoji 🚨 transmitem a mesma informação por outra via.
3. **Layout quebra em terminais < 100 col**: o `cartesian_plane` tem `width=18` e os 9 widgets empilhados precisam de ~120 col. Mitigação: `make_console` (`renderers.py:37-75`) detecta largura via `shutil.get_terminal_size()` e degrada para 60 col mínimo.
4. **Texto "MANHÃ / TARDE / NOITE" em maiúsculas no campo "Período"** pode confundir usuário i18n. Mitigação: padronizado em PT-BR.
5. **`build_next_step_panel` usa `sleep.duration_hours < 6` como gatilho `crit`**, mas se o snapshot não tem `sleep`, `duration_hours` é `None` e a comparação levanta `TypeError` em runtime. (Ver nota no wireframe: o `2026-06-04` com 4.0h dispara `crit` mesmo em Q1.)

## Métricas de sucesso

- **Tempo até encontrar a info**: meta < 5s para o quadrante (topo) e < 15s para "cumpri a meta?" (HARDWORK).
- **Taxa de uso do `--json`**: esperado < 5% (tela primariamente humana); > 20% indicaria que usuários estão construindo dashboards próprios.
- **Erros de comando**: contagem de `--date` malformados por dia. Meta: < 1% dos comandos.

## Onde aparece

- Home menu: opção `6` (Relatórios) → submenu `1` (Diário).
- Link direto: `operational report daily [--date]`.
- Pode ser referenciado em `--help` de `state show` como "relatório completo do dia".

## Notas de implementação

- Entry point: `cli/commands/report_cmd.py:45` (`daily`).
- Renderer: `ui/daily_report.py:281` (`render_daily_report`) → retorna `rich.console.Group`.
- Cálculo do quadrante: `core.services.compute_day_quadrant(snap)` (`core/services.py:280-318`); usa `productivity_pct` e `efficiency_pct` de `core/budget.py:73-100`.
- Data source: 14 repos em `cli/state.py` (routines, sleep_records, pomodoros, transicoes, etc.) lidos por `get_day_snapshot(d)` em `core/services.py:133-277`.
- Linha do Group final: `console.print(report)` em `report_cmd.py:97`.
- Largura do console: `CONSOLE_WIDTH = 120` em `ui/__init__.py:43`; respeita `is_captured()` para `--json` e pipes.
