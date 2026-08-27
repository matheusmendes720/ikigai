# FLOW-006 — Gerar Relatório Diário

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Eu quero ver um relatório completo do dia de hoje (ou de uma data específica) com Cartesian plane, pomodoros, KPIs, OKRs e próxima ação sugerida."

**Ponto de entrada:**
- `operational home` → `6` (Relatórios) → `1` (Relatório diário — hoje)
- `operational home` → `6` (Relatórios) → `2` (com `--date`)
- `operational home` → `6` (Relatórios) → `3` (JSON)
- Comando direto: `operational report daily [--date YYYY-MM-DD] [--json]`

**Pré-condições:**
- Nenhuma. State vazio renderiza "sem dados" (mesmo padrão do FLOW-005).

**Telas envolvidas:**
- SCR-001 Home Menu
- SCR-006a Reports Submenu
- SCR-017 Daily Report (header + KPI grid + pomodoros grid + Cartesian plane + OKR sections + next-step)

**Componentes críticos:**
- CMP-001 Header
- CMP-009 kpi_card (×4: Sono, Pomodoros, Hardwork, Energia/Foco) — `ui/components.py:341-361` (versão canônica)
- CMP-010 pomodoros_grid — `ui/components.py:222-238`
- CMP-014 cartesian_plane (X = produtividade, Y = qualidade) — `ui/components.py:241-327`
- CMP-002 section_panel (×N: deu_certo, deu_errado, maior_aprendizado, big_win, ajustes) — `ui/components.py:364-378`
- CMP-012 next_step_panel — `ui/components.py:381-387`
- CMP-015 metric_table (sleep distribution) — `cli/renderers.py:406-433`

**Duração típica:** 4s leitura visual (1 comando, render full dashboard)

**Taxa de abandono estimada:** 0% (é o destino final do user)

---

## Fluxo principal (happy path)

1. User digita `operational home`, digita `6`, Enter.
2. `_route("6")` despacha para `_menu_reports` (`cli/home.py:321-331`).
3. `_submenu` mostra 7 opções + `b` (back) — `home.py:297-318`.
4. User digita `1` (Relatório diário — hoje) e Enter.
5. `_run_cli_command(["report", "daily"])` — `home.py:323-324` (linha `items[0][2]`).
6. `_run_cmd` chama `typer_app(["report", "daily"], standalone_mode=False)` (`home.py:60`).
7. `report_cmd.daily` (`cli/commands/report_cmd.py:45-97`):
   - `d = date.today()` (sem `--date`)
   - `snap = get_day_snapshot(d)` — lê 14 repos, monta frozen dataclass (`core/services.py:133-277`)
   - `if json:` False
   - `report = render_daily_report(snap)` — `ui/daily_report.py:50-340`
   - `console.print(report)`
8. `render_daily_report` constrói:
   - `compute_day_quadrant(snap)` → `(q_code, x, y)` — `core/services.py:280-...` (provavelmente)
   - Header table (date · tipo_dia · quadrant emoji · pomodoros)
   - Sleep row (bedtime, wake, duration, quality)
   - 4 KPI cards (hardwork orçado/realizado, pomodoros, sleep, energy/focus)
   - Pomodoros grid (S1 manhã, S2 tarde, S3 noite)
   - Cartesian plane (X = produtividade, Y = qualidade)
   - Section panels (deu_certo, deu_errado, maior_aprendizado, big_win, ajustes)
   - Next-step panel baseado em quadrant
9. Retorna `rich.console.Group` com tudo.
10. `console.print(group)` emite tudo no stdout.
11. `_run_cmd` chama `Press Enter to continue` — user lê e pressiona Enter.
12. Volta ao submenu de Reports (loop do `_submenu`).
13. User digita `b` (back) → volta ao menu principal.

### Wireflow ASCII (FLOW-006)

```text
       ╭───────────────╮
       │ ◯  user       │
       │ "operational  │
       │   home"       │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-001       │
       │ Home Menu     │◀════╮
       └───┬───────────┘    │
           │ digita "6"     │
           ▼                │
       ┌───────────────┐    │
       │ SCR-006a      │    │
       │ Submenu       │    │  (loop até
       │ Reports (7+1) │    │   digitar b)
       └───┬───────────┘    │
           │ digita "1"     │
           ▼                │
       ╔═══════════════╗    │
       ║ report daily  ║    │
       ║ (no --date)   ║    │
       ╚═══════╤═══════╝    │
               │            │
               ▼            │
       ┌───────────────┐    │
       │ core.services │    │
       │ get_day_      │    │
       │  snapshot(d)  │    │
       │ (14 repos)    │    │
       └───┬───────────┘    │
           │ DaySnapshot    │
           ▼                │
       ┌───────────────┐    │
       │ ui.daily_     │    │
       │ report.render │    │
       └─────┬─────────┘    │
             │              │
             ▼              │
       ┌───────────────┐    │
       │ SCR-017       │    │
       │ Daily Report: │    │
       │               │    │
       │ 📅 2026-06-08 │    │
       │ Q1  ◆ Q1:80% │    │  ◀── header
       │               │    │
       │ [Sono][Pomod] │    │  ◀── KPI grid
       │ [Hard][Energ] │    │
       │               │    │
       │ S1▣▣▣▢ S2▣▣▣▣│    │  ◀── pomodoros
       │               │    │
       │    Y↑         │    │
       │ 100│      ◆   │    │  ◀── Cartesian
       │  50┊          │    │      plane
       │  ──┼─────────→│    │
       │    0   50   100│   │
       │               │    │
       │ 🟢 EASE:      │    │  ◀── section
       │  │ rot1 ENTRY │    │      panels
       │  │ rot2 CORE  │    │
       │               │    │
       │ → Manter ritmo│    │  ◀── next step
       └─────┬─────────┘    │
             │              │
             ▼              │
       ┌───────────────┐    │
       │ ◯  Press      │    │
       │  Enter        │────┘
       │  (volta       │
       │   submenu)    │
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - - -
  : (E1) --date 2026-13-99     : → error_panel
  : (E2) state vazio            : → "(sem dados)"
  :                              :   em cada seção
  : (E3) Pydantic entity        : → error_panel
  :     corrompida              :   + log_error
  : (A3) --json                 : → payload flat
  :     (sem render visual)     :
  : (A4) --date 2026-06-07      : → mesmo layout,
  :     (ontem)                 :   dados de ontem
  - - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o home menu (comando direto)

```bash
operational report daily
# ou
operational report daily --date 2026-06-07
# ou
operational report daily --json
```

### A2 — Via submenu Reports opção 2 (com --date explícito)

```bash
operational home
> 6  (Relatórios)
> 2  (Relatório diário — 2026-06-08 --date)
```

A diferença vs opção 1: o comando roda com `--date $(today)` explícito. Render idêntico. É redundante — UX-013 (refatorar submenu).

### A3 — Output JSON (CI / piping)

```bash
operational report daily --json
```

Retorna payload flat (não aninhado) com 30+ campos (`report_cmd.py:59-92`):

```json
{
  "date": "2026-06-08",
  "tipo_dia": "UTIL",
  "sleep_hours": 7.5,
  "sleep_quality": 8,
  "energia": 7,
  "foco": 8,
  "hardwork_orcado_min": 240,
  "hardwork_realizado_min": 200,
  "n_pomodoros": 7,
  "pomodoros_meta": 8,
  "quadrant": "Q1",
  "x": 80.0,
  "y": 70.0,
  "deu_certo": "Entreguei o relatório X",
  ...
}
```

Útil para log scraping, dashboards externos, ou scripts de automação.

### A4 — Data retroativa

```bash
operational report daily --date 2026-06-07
```

Renderiza relatório de ontem. Idempotente.

### A5 — Relatório semanal "enganando" (avançado)

`report weekly` existe (FLOW-007), mas para ver 1 dia fora do padrão, user pode rodar `report daily --date 2026-06-07` e `report daily --date 2026-06-06`, etc. Cobre 7 dias em 7 comandos. UX-005.

### A6 — Dataset sintético (estado populado)

Se `TIME_TASKER_DATASET=synthetic` e state tem 7 dias, `report daily` mostra hoje (último dia do seed). Cartesian plane marca Q1/Q2/Q3/Q4 realista.

---

## Exceções e erros

### E1 — Data malformada

- **Causa:** `--date 2026-13-99`.
- **Onde:** `report_cmd.py:51` — `date.fromisoformat()` lança `ValueError`.
- **Tratamento:** Typer converte em `BadParameter: Invalid value for '--date'`.
- **Recuperação:** `error_panel` mostra; user retenta.

### E2 — State vazio (sem entities para a data)

- **Causa:** primeira execução, ou data sem registros.
- **Onde:** `core/services.py:133-277` — `get_day_snapshot` retorna snapshot com campos None.
- **Tratamento:** renderização com placeholders (em-dash, "(sem dados)"). Sem crash.
- **Mensagem ao user:** visual, não textual.

### E3 — Pydantic entity corrompida em algum repo

- **Causa:** JSON tem `id` duplicado ou field inválido.
- **Onde:** `core/services.py:139-238` itera `repo.list()`.
- **Tratamento:** `log_error` registra; renderização pula a entity. Relatório parcial.
- **Diagnóstico:** `operational doctor` reporta em `_check_state_dir`.

### E4 — Ctrl+C durante render

- **Causa:** user interrompe Rich printing.
- **Onde:** `console.print(group)` é síncrono.
- **Tratamento:** `KeyboardInterrupt` em `home()` (`home.py:477-480`), sai limpo.
- **Risco:** ANSI parcial pode quebrar prompt seguinte. Enter resolve.

### E5 — Cartesian plane sem label Q?

- **Causa:** Q1/Q2/Q3/Q4 são derivados de `compute_day_quadrant`. Se x ou y são NaN (divisão por zero), glyph pode ser `?`.
- **Onde:** `ui/daily_report.py:241-327` (provavelmente linhas que escolhem glyph).
- **Tratamento:** `cartesian_plane` mostra `?` em vez de `◆`/`▲`/`✗`. Renderiza sem crash.
- **Risco:** UX-008 — falta tooltip/legenda explicando o que `◆` significa.

### E6 — Console sem TTY (CI / pipe)

- **Causa:** `operational report daily | less`.
- **Onde:** `ui/__init__.py:35-37` detecta `is_captured()`.
- **Tratamento:** renderiza plain text, sem cores. Quebra visual do Cartesian plane.
- **Workaround:** `--json`.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-001-home-menu.md` (ref futura)
- `docs/ux/05-telas/SCR-006a-reports-submenu.md` (ref futura)
- `docs/ux/05-telas/SCR-017-daily-report.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem. Refs semânticas.

## Componentes críticos

- CMP-001 Header — `cli/home.py:84-93`
- CMP-009 kpi_card — `ui/components.py:341-361` (4 cards)
- CMP-010 pomodoros_grid — `ui/components.py:222-238`
- CMP-014 cartesian_plane — `ui/components.py:241-327`
- CMP-002 section_panel — `ui/components.py:364-378` (N instâncias)
- CMP-012 next_step_panel — `ui/components.py:381-387`
- CMP-004 error_panel — `ui/components.py:390-426`

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **Submenu de Reports é "destino"** — opções 6-9 do menu principal são "para onde você vai ler dados". Diferente de 1-4 (workflows).
2. **Layout fixo (header + KPIs + grid + plane + sections + next-step)** — `ui/daily_report.py:50-340` é uma factory. User sabe o que esperar.
3. **Cartesian plane é o coração** — `CMP-014` mostra X (produtividade) vs Y (qualidade). Quadrante (Q1-Q4) é derivado. Métrica oficial do produto.
4. **OKRs no fim** — `deu_certo`, `deu_errado`, `maior_aprendizado`, `big_win`, `ajustes` são section panels. User rola até o fim para encontrar.
5. **Next-step panel SEMPRE no final** — fecha o relatório com "o que fazer".
6. **JSON mirror via opção 3 do submenu** — `home.py:326` (`["report", "daily", "--json"]`). Redundante com `--json` direto. UX-013.
7. **20-80ms de render** — `architecture/05-DATA-FLOW.md:323` cita a métrica. Robusto para 30 dias de dados.

**Fricções mantidas:**

- **Submenu 7 opções** — UX-009 sugere consolidar. Opção 2 (`--date` explícito) é redundante; opção 3 (`--json`) é mirror do flag. Reduzir para 3 opções (hoje, data, JSON).
- **Cartesian plane sem legenda inline** — UX-008. User precisa saber que `◆` = Q1 (bom). Adicionar caption.
- **Layout assume 120 col** — `ui/__init__.py` define `CONSOLE_WIDTH = 120`. Em 80 col, quebra. UX-003.

## Critérios de sucesso

- **Tempo de leitura:** < 30s para scan completo (header + KPIs + grid + plane + OKRs).
- **Render técnico:** < 500ms para 30 dias de dados (`architecture/05-DATA-FLOW.md:323`).
- **Coerência visual:** layout idêntico para todos os dias (factory pura, sem side effects).
- **Acessibilidade:** cores não-convencionais (red/green) + glyphs (◆▲✗) — funciona para daltônicos? UX-002.

## Onde aparece

- **Home menu opção 6 → 1** — `_menu_reports` (`cli/home.py:323-324`)
- **Home menu opção 6 → 2** — `_menu_reports` (`cli/home.py:325`)
- **Home menu opção 6 → 3** — `_menu_reports` (`cli/home.py:326`)
- **Comando direto** — `operational report daily [--date] [--json]`

## Notas de implementação

**File:line refs principais:**

- Fluxo principal (submenu): `cli/home.py:321-331`
- `_menu_reports`: `cli/home.py:321-331`
- `_submenu` helper: `cli/home.py:297-318`
- Report controller: `cli/commands/report_cmd.py:45-97`
- `daily()`: `cli/commands/report_cmd.py:46-97`
- `get_day_snapshot`: `core/services.py:133-277`
- `DaySnapshot` dataclass: `core/services.py:55-103`
- `compute_day_quadrant`: `core/services.py:280-...` (provavelmente)
- Render: `ui/daily_report.py:50-340`
- `render_daily_report`: `ui/daily_report.py:50-340`
- Data flow end-to-end: `architecture/05-DATA-FLOW.md` (doc completo)

**Como adicionar nova seção "Hábitos do dia":**

```python
# Em ui/daily_report.py, dentro de render_daily_report:
habits_panel = section_panel(
    title="Hábitos do dia",
    body=habits_table_for_day(snap.date),  # helper
    color="primary",
)
# Adicionar ao Group antes do next_step_panel
```

(Requer helper `habits_table_for_day` que filtra `habits.list()` por data.)

**Como mudar o Cartesian plane para mostrar Z (foco):**

```python
# Em ui/daily_report.py, substituir cartesian_plane por:
plane_3d = cartesian_plane(
    x=snap.productivity_pct,
    y=snap.focus_pct,  # novo eixo
    width=18, height=7,
)
```

(Requer `snap.focus_pct` — adicionar em `DaySnapshot`.)

**Como mudar o emoji do quadrant:**

`ui/components.py` (provavelmente) tem dict `QUADRANT_EMOJI`. Q1=`🏆`, Q2=`✓`, Q3=`✗`, Q4=`⚠️`. Editar lá.

**Como mudar a paleta de cores:**

`ui/components.py:87-94` (`COLORS` dict). Editar lá. Cores Rich: `bright_green`, `cyan`, `bold red`, `yellow`, etc.
