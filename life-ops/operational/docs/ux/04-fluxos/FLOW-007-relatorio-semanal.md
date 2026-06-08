# FLOW-007 — Gerar Relatório Semanal

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "No domingo à noite, em menos de 30 segundos eu vi a tendência da semana: sono médio, distribuição de quadrantes, sparklines, e se preciso ajustar o setpoint."

**Ponto de entrada:**
- `operational home` → `6` (Relatórios) → `4` (Relatório semanal)
- `operational home` → `6` (Relatórios) → `5` (semanal JSON)
- Comando direto: `operational report weekly [--json]`

**Pré-condições:**
- State tem ≥ 1 dia de dados (relatório fica degradado com < 7 dias, mas renderiza)
- Semana começa em `date.today() - timedelta(days=6)` (segunda implícita) — ver `report_cmd.py:107-...`

**Telas envolvidas:**
- SCR-001 Home Menu
- SCR-006a Reports Submenu
- SCR-018 Weekly Report (7 dias agregados: KPIs médios, sparklines, distribuições, posições diárias, sleep breakdown, next-step)

**Componentes críticos:**
- CMP-001 Header
- CMP-015 metric_table (×N: sono, pomodoros, hardwork, Q1 count) — `cli/renderers.py:406-433`
- CMP-008 sparkline (×N: sono 7d, pomodoros 7d, hardwork 7d) — `ui/components.py:205-219`
- CMP-012 next_step_panel — `ui/components.py:381-387`
- CMP-002 section_panel (TipoDia distribution, Quadrant distribution) — `ui/components.py:364-378`
- CMP-016 inline Table (daily positions) — `report_cmd.py:196-274` (acknowledged compromise)

**Duração típica:** 5s leitura visual (1 comando, render full week)

**Taxa de abandono estimada:** 0% (destino final)

---

## Fluxo principal (happy path)

1. User digita `operational home`, digita `6`, Enter.
2. `_route("6")` despacha para `_menu_reports` (`cli/home.py:321-331`).
3. `_submenu` mostra 7 opções. User digita `4` (Relatório semanal).
4. `_run_cli_command(["report", "weekly"])` — `home.py:327`.
5. `report weekly` (`cli/commands/report_cmd.py:106-315`):
   - `ws = date.today() - timedelta(days=6)` (segunda implícita)
   - `we = date.today()` (domingo implícita)
   - Itera `ws` a `we` (7 dias), chama `get_day_snapshot(d)` para cada
   - Agrega KPIs (média sono, total pomodoros, total hardwork, count por quadrant)
   - Sparklines (7 valores para sono, pomodoros, hardwork)
   - Distribuições (TipoDia, Quadrant)
   - Daily positions table (cada dia: Q? + x + y)
   - Sleep breakdown (média, mín, máx, noites < 6h)
   - Next-step panel (baseado em Q3 count)
6. Renderiza tudo inline (não delega para `ui/weekly_report.py` — `report_cmd.py:101` cita "kept lighter").
7. `_run_cmd` chama `Press Enter to continue` — user lê e pressiona Enter.
8. Volta ao submenu.

### Wireflow ASCII (FLOW-007)

```text
       ╭───────────────╮
       │ ◯  user       │
       │  "6" no home  │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-006a      │
       │ Submenu       │◀════╮
       │ Reports       │    │
       └───┬───────────┘    │
           │ digita "4"     │
           ▼                │
       ╔═══════════════╗    │
       ║ report weekly ║    │
       ╚═══════╤═══════╝    │
               │            │
               ▼            │
       ┌───────────────┐    │
       │ core.services │    │
       │ para 7 dias   │    │
       │ (loop 7×)     │    │
       └─────┬─────────┘    │
             │ 7 snapshots  │
             ▼              │
       ┌───────────────┐    │
       │ report_cmd    │    │
       │ .weekly()     │    │
       │ (inline       │    │
       │  Table/Group) │    │
       └─────┬─────────┘    │
             │              │
             ▼              │
       ┌───────────────┐    │
       │ SCR-018       │    │
       │ Weekly Report:│    │
       │               │    │
       │ 📅 2026-06-02 │    │
       │ → 2026-06-08  │    │
       │               │    │
       │ 😴 Sono (7d): │    │
       │   ▁▂▃▄▅▆▇█    │    │  ◀── sparklines
       │   Média 7.2h  │    │
       │               │    │
       │ 🎯 Pomodoros: │    │
       │   ▁▂▂▃▄▅▅ 7d  │    │
       │               │    │
       │ ⚖️  Distrib Q:│    │
       │   Q1: 4 ████  │    │  ◀── distributions
       │   Q2: 2 ██    │    │
       │   Q3: 1 █     │    │      (Q3 ≥ 1 = crit)
       │   Q4: 0       │    │
       │               │    │
       │ 📅 Daily:     │    │
       │   Seg  Q1 80% │    │  ◀── daily positions
       │   Ter  Q1 75% │    │
       │   ...         │    │
       │               │    │
       │ → Manter ritmo│    │  ◀── next step
       │   (Q3 ≥ 1)    │    │      (severity muda
       └─────┬─────────┘    │       se Q3 ≥ 1)
             │              │
             ▼              │
       ┌───────────────┐    │
       │ ◯  Press      │    │
       │  Enter        │────┘
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - - -
  : (E1) state vazio (0 dias) : → sparklines
  :                            :   "(sem dados)"
  :                            :   distribuições 0
  : (E2) < 7 dias (ex: 3)    : → sparkline
  :                            :   parcial; UI
  :                            :   preenche com —
  : (E3) Q3 ≥ 1              : → next-step
  :                            :   vira "crit"
  :                            :   (ver OBJ-03)
  : (A3) --json               : → payload flat
  - - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o home menu (comando direto)

```bash
operational report weekly
# ou
operational report weekly --json
```

### A2 — Via submenu opção 5 (JSON)

```bash
operational home
> 6  (Relatórios)
> 5  (Relatório semanal — JSON)
```

Redundante com `--json` direto. UX-013.

### A3 — Output JSON (CI / log scraping)

```bash
operational report weekly --json
```

Retorna payload com arrays de 7 dias + agregados:

```json
{
  "week_start": "2026-06-02",
  "week_end": "2026-06-08",
  "sono_media": 7.2,
  "sono_min": 5.8,
  "sono_max": 8.5,
  "pomodoros_total": 32,
  "hardwork_total_min": 1680,
  "q1_count": 4,
  "q2_count": 2,
  "q3_count": 1,
  "q4_count": 0,
  "days": [
    {"date": "2026-06-02", "quadrant": "Q1", "x": 80, "y": 70, ...},
    {"date": "2026-06-03", "quadrant": "Q2", ...},
    ...
  ]
}
```

### A4 — Semana parcial (3 dias de dados)

Sparklines mostram 3 valores + 4 placeholders. Distribuições mostram 3 dias (não 7). Daily positions table tem 3 linhas.

### A5 — Semana sem dados (cold start)

Todas sparklines mostram `(sem dados)`. Distribuições zeradas. Next-step: "Sem dados na semana. Inicie com opção 1."

### A6 — Detectar burnout (OBJ-03)

Se Q3 count ≥ 1, next-step panel vira `crit` (red):

> "⚠️ 3 dias em Q3 detectados. Considere reduzir carga ou recuperar sono."

Lógica em `report_cmd.py:296-301` (citado em `docs/ux/00-visao-geral/01-objetivos-produto.md:67`).

### A7 — Comparação A/B com semana anterior (gap)

OBJ-05: "Comparar semana atual vs anterior" — **não implementado**. Workaround: rodar 2 vezes com `--start` e `--end` hipotéticos (não há esses flags). UX-009.

---

## Exceções e erros

### E1 — State vazio (cold start)

- **Causa:** primeira execução do CLI, `~/.time-tasker/*.json` não tem dados.
- **Onde:** `report_cmd.py:107-...` itera 7 dias; `get_day_snapshot` retorna snapshots com `None` em todos os campos.
- **Tratamento:** sparklines mostram `(sem dados)`, distribuições zeradas, daily positions vazia.
- **Mensagem ao user:** visual, não textual.

### E2 — Data futura (edge case)

- **Causa:** `report_cmd.py:107-...` calcula `ws = today - 6`; se hoje é 2026-06-08, ws = 2026-06-02. OK.
- **Tratamento:** sem erro.
- **Risco:** se clock do sistema está errado (ex: 1970), ws fica no passado distante. Pydantic entity parse falha.

### E3 — Pydantic entity corrompida

- **Causa:** JSON com `id` duplicado.
- **Onde:** `core/services.py:139-238` itera `repo.list()`.
- **Tratamento:** `log_error` registra; relatório pula a entity.
- **Diagnóstico:** `operational doctor`.

### E4 — Ctrl+C durante render

- Mesma mecânica do FLOW-006 E4.
- `home()` sai limpo.

### E5 — Console sem TTY (CI / pipe)

- **Causa:** `operational report weekly | less`.
- **Tratamento:** cores desabilitadas (`is_captured()`), layout pode quebrar (sparklines alinham mal).
- **Workaround:** `--json`.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-001-home-menu.md` (ref futura)
- `docs/ux/05-telas/SCR-006a-reports-submenu.md` (ref futura)
- `docs/ux/05-telas/SCR-018-weekly-report.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem.

## Componentes críticos

- CMP-001 Header — `cli/home.py:84-93`
- CMP-015 metric_table — `cli/renderers.py:406-433` (N instâncias)
- CMP-008 sparkline — `ui/components.py:205-219` (3 sparklines: sono, pomodoros, hardwork)
- CMP-002 section_panel — `ui/components.py:364-378` (distribuições)
- CMP-012 next_step_panel — `ui/components.py:381-387` (vira `crit` se Q3 ≥ 1)
- CMP-016 inline Table — `report_cmd.py:196-274` (daily positions — acknowledged compromise)
- CMP-004 error_panel — `ui/components.py:390-426`

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **Sparklines para tendência** — 7 valores visuais em ~30 chars. User detecta "tô piorando" ou "tô melhorando" em 1 olhar. Sem sparkline, user teria que ler 7 números e compará-los mentalmente.
2. **Distribuição por quadrante** — Q1 count, Q2 count, Q3 count, Q4 count. Responde "quantos dias bons/ruins?" sem pedir breakdown por dia.
3. **Daily positions table** — User que quer detalhe vê cada dia com Q? + x + y. Compromisso: inline em `report_cmd.py:196-274` (não delega para `ui/weekly_report.py`).
4. **Next-step panel detecta burnout** — OBJ-03 do produto (`docs/ux/00-visao-geral/01-objetivos-produto.md:60-73`). Se Q3 ≥ 1, vira `crit`. User recebe alerta visual.
5. **OBJ-05 — comparação A/B** — **gap conhecido**. Workaround: rodar 2 vezes. UX-009.

**Fricções mantidas:**

- **Inline Table construction em `report_cmd.py:196-274`** — viola o pattern "controller NÃO constrói Table" (`report_cmd.py:6-8` cita a regra). Compromisso acknowledged até weekly ser refatorado para `ui/weekly_report.py`. UX-013.
- **Sem filtro de range customizado** — só "últimos 7 dias". User que quer "últimos 14" tem que rodar 2×. UX-005 sugere adicionar `--days 14`.
- **Comparação A/B não implementada** — OBJ-05 gap. UX-009.

## Critérios de sucesso

- **Tempo de leitura:** < 30s para scan completo.
- **Render técnico:** < 1s para 7 dias (50ms × 7 + overhead).
- **Detecção de burnout:** Q3 ≥ 1 → next-step `crit` em 100% dos casos.
- **Coerência:** layout idêntico para todas as semanas.

## Onde aparece

- **Home menu opção 6 → 4** — `_menu_reports` (`cli/home.py:327`)
- **Home menu opção 6 → 5** — `_menu_reports` (`cli/home.py:328`)
- **Comando direto** — `operational report weekly [--json]`
- **OBJ-03 do produto** — `docs/ux/00-visao-geral/01-objetivos-produto.md:60-73`

## Notas de implementação

**File:line refs principais:**

- Fluxo principal (submenu): `cli/home.py:321-331`
- Report weekly controller: `cli/commands/report_cmd.py:106-315`
- Inline table (daily positions): `report_cmd.py:196-274` (acknowledged compromise)
- Sparkline: `ui/components.py:205-219`
- Q3 detection: `report_cmd.py:296-301` (citado por `docs/ux/00-visao-geral/01-objetivos-produto.md:67`)

**Como adicionar range customizado `--days 14`:**

```python
# Em report_cmd.py:weekly, adicionar param:
days: int = typer.Option(7, "--days", help="Número de dias (default 7)")
ws = date.today() - timedelta(days=days - 1)
```

**Como mover inline table para `ui/weekly_report.py`:**

1. Criar `ui/weekly_report.py` com factory `render_weekly_report(snapshots) -> Group`.
2. Mover lógica de `report_cmd.py:196-274` para `ui/weekly_report.py`.
3. Substituir inline construction por `group.add_row(...)`.
4. Atualizar este doc (FLOW-007).

**Como adicionar comparação A/B (OBJ-05):**

```python
# Em report_cmd.py:weekly, antes do render:
prev_ws = ws - timedelta(days=7)
prev_we = we - timedelta(days=7)
prev_snapshots = [get_day_snapshot(prev_ws + timedelta(days=i)) for i in range(7)]
# Calcular diff: prev_sono_media vs curr_sono_media, etc.
# Adicionar section "vs semana anterior"
```

(Requer `core/weekly_aggregator.py:compare_weeks(snapshots_a, snapshots_b)`.)

**Como mudar a janela de 7 dias:**

`report_cmd.py:107-...` define `ws = today - 6`, `we = today`. Para mudar para 14 dias, edite `timedelta(days=6)` para `timedelta(days=13)`. Idealmente extrair para flag `--days`.
