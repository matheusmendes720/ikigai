# FLOW-005 — Ver Dashboard do Dia

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Em menos de 5 segundos eu vi onde estou no dia, o que está logado, e se estou no plano."

**Ponto de entrada:**
- `operational home` → opção `5` (Dashboard do Dia) — **default** se user pressiona Enter sem escolher
- `operational home` → Enter no prompt `Choose` (default `"5"`)
- Comando direto: `operational state show`

**Pré-condições:**
- Nenhuma. State vazio renderiza "sem dados" em vez de quebrar.
- Hora do dia determina `Period` exibido (MANHA / TARDE / NOITE) — `state_cmd.py:50-57`

**Telas envolvidas:**
- SCR-001 Home Menu
- SCR-016 State Dashboard (2x2 KPI grid + activity + next-step)

**Componentes críticos:**
- CMP-001 Header
- CMP-009 kpi_card (×4: Sono, Pomodoros, Hardwork, Energia) — `cli/renderers.py:135-159`
- CMP-010 pomodoros_grid (S1/S2/S3) — `ui/components.py:222-238`
- CMP-011 timeline_h (timeline horizontal) — `cli/renderers.py:238-260`
- CMP-012 next_step_panel — `ui/components.py:381-387`

**Duração típica:** 3s (1 comando, leitura visual)

**Taxa de abandono estimada:** 0% (é o que o user veio fazer)

---

## Fluxo principal (happy path)

1. User digita `operational home`, ou apenas pressiona Enter no prompt `Choose` (default é `"5"`, `home.py:109`).
2. `_route("5")` despacha para `_dashboard` (`cli/home.py:281-283`).
3. `_dashboard` é literalmente `_run_cmd(["state", "show"])` — 1 linha.
4. `state show` (`cli/commands/state_cmd.py:71-...`) executa:
   - Parse `--date` (default hoje)
   - `now = _now()` (timezone.utc)
   - `period_now = _period_now(now)` (MANHA/TARDE/NOITE)
   - Carrega 6 repos: sleep_records, time_blocks, pomodoros, routine_logs, ajustes_finos, journals
   - Filtra por data
   - Calcula total_block_min, completed_pomodoros, budget_min
5. Controller chama `render_dashboard(snap, ...)` (em `cli/commands/state_cmd.py:100-...`).
6. Renderiza layout 2x2 KPI grid + activity section + next-step panel (descrito no doc `architecture/01-MVC-LAYERS.md`).
7. `_run_cmd` chama `Press Enter to continue` — user lê e pressiona Enter.
8. Volta ao menu.

### Wireflow ASCII (FLOW-005)

```text
       ╭───────────────╮
       │ ◯  user digita│
       │ "operational  │
       │     home"     │
       │     <Enter>   │  ◀── OU digita "5"
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-001       │
       │ Home Menu     │
       │ default = "5" │  ◀── Enter aceita
       └───┬───────────┘
           │ choice = "5"
           ▼
       ┌───────────────┐
       │ _dashboard()  │  (1 linha:
       │ _run_cmd(["   │   home.py:283)
       │  state","show"│
       │ ])            │
       └───┬───────────┘
           │
           ▼
       ╔═══════════════╗
       ║ state show    ║
       ║ (controller)  ║
       ╚═══════╤═══════╝
               │
               ▼
       ┌───────────────┐
       │ Load 6 repos: │
       │ - sleep       │
       │ - blocks      │
       │ - pomodoros   │
       │ - routine_logs│
       │ - ajustes     │
       │ - journals    │
       └───┬───────────┘
           │ DaySnapshot
           ▼
       ┌───────────────┐
       │ SCR-016       │
       │ Dashboard:    │
       │               │
       │ [Sono] [Pomod]│  ◀── 2x2 KPI grid
       │ [Hard] [Energ]│      (CMP-009 ×4)
       │               │
       │ S1 ▢▢▢▢  S2...│  ◀── pomodoros grid
       │               │      (CMP-010)
       │ Timeline:     │  ◀── horizontal
       │  ████ 04h...  │      (CMP-011)
       │               │
       │ → Manter ritmo│  ◀── next step
       └─────┬─────────┘      (CMP-012)
             │
             ▼
       ┌───────────────┐
       │ ◯  Press      │
       │  Enter to     │
       │  continue     │───→ volta menu
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - -
  : (E1) state vazio        : → render
  :                          :   "sem dados"
  :                          :   em cada KPI
  : (E2) --date 2026-13-99  : → BadParameter
  :                          :   (date parse)
  : (A2) --json             : → payload
  :                          :   estruturado
  - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o home menu (comando direto)

```bash
operational state show
# ou com data específica
operational state show --date 2026-06-07
```

Mesma renderização. Sem overhead do menu.

### A2 — `Enter` puro no `Choose` (atalho do default)

```text
╭──────────────────────────────────────────╮
│ ⚡ TIME-TASKER v0.1.0 | 2026-06-08       │
╰──────────────────────────────────────────╯
Key  Action                       Description
─────────────────────────────────────────
1    🌅  Iniciar Manhã            ...
...
5    📊  Dashboard do Dia         Onde estou · ...

Choose [5]: <Enter>
```

`Prompt.ask` aceita `default="5"` (`home.py:109`) e retorna `"5"`. UX deliberada: "press Enter to see where you are" — `docs/tui/05-HOME-MENU.md:104-105`.

### A3 — Output JSON (CI / log scraping)

```bash
operational state show --json
```

Retorna payload com `date`, `period_now`, `sleep`, `pomodoros`, `hardwork`, `energy`. Sem painel. Pipe-friendly.

### A4 — Data retroativa

```bash
operational state show --date 2026-06-07
```

Mostra dashboard de ontem. Útil para preencher dados retroativos.

### A5 — Estado vazio (primeira execução)

Renderiza 4 KPI cards com `—` (em-dash) e footer `(sem dados)`. Activity table mostra "(nenhuma atividade)". Next-step panel mostra "Sem dados ainda. Inicie o dia com opção 1."

### A6 — Via submenu Reports opção 6

`operational home` → `6` (Relatórios) → `6` (Dashboard do dia) — `_menu_reports` em `home.py:329`. Cobre o mesmo `state show` por uma rota alternativa. UX-013: rotas redundantes confundem novato.

---

## Exceções e erros

### E1 — Data malformada em `--date`

- **Causa:** `operational state show --date 2026-13-99`.
- **Onde:** `state_cmd.py:77` — `date.fromisoformat(...)` lança `ValueError`.
- **Tratamento:** Typer converte em `BadParameter: Invalid value for '--date'`.
- **Recuperação:** `error_panel` mostra mensagem; user volta ao menu, retenta.

### E2 — State vazio (sem entities)

- **Causa:** primeira execução, `~/.time-tasker/*.json` ainda não tem dados.
- **Onde:** `state_cmd.py:82-87` — `next((s for s in sleep_records.list() if s.date == d), None)` retorna `None`.
- **Tratamento:** renderização com placeholders (em-dash, "sem dados"). Sem erro.
- **Mensagem ao user:** visual, não textual. User vê cards vazios.

### E3 — Pydantic error em entity corrompida

- **Causa:** JSON no state dir tem `id` duplicado ou field faltando.
- **Onde:** `JSONRepository._load_all` (não lido integralmente) faz `json.loads` mas não valida Pydantic.
- **Tratamento:** erro silencioso ou crash no primeiro `repo.list()`.
- **Workaround:** `operational demo clear` (FLOW-009) regenera.

### E4 — Ctrl+C durante render

- **Causa:** user pressiona Ctrl+C enquanto Rich renderiza.
- **Onde:** `console.print(group)` é síncrono.
- **Tratamento:** `KeyboardInterrupt` capturado em `home()` (`home.py:477-480`), sai limpo.
- **Risco:** ANSI parcial impresso, prompt seguinte pode estar corrompido. Pressionar Enter resolve.

### E5 — Console sem TTY (CI / pipe)

- **Causa:** `operational state show | less` ou rodando em CI.
- **Onde:** `ui/__init__.py:35-37` detecta `is_captured()` e desabilita cores (`no_color=True`).
- **Tratamento:** renderiza plain text, sem ANSI.
- **Recuperação:** usar `--json` se quiser dados estruturados.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-001-home-menu.md` (ref futura)
- `docs/ux/05-telas/SCR-016-state-dashboard.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem. Refs semânticas.

## Componentes críticos

- CMP-001 Header — `cli/home.py:84-93`
- CMP-009 kpi_card — `cli/renderers.py:135-159` (4 instâncias: Sono, Pomodoros, Hardwork, Energia)
- CMP-010 pomodoros_grid — `ui/components.py:222-238`
- CMP-011 timeline_h — `cli/renderers.py:238-260`
- CMP-012 next_step_panel — `ui/components.py:381-387`
- CMP-013 metric_table — `cli/renderers.py:406-433` (activity table)
- CMP-004 error_panel — `ui/components.py:390-426`

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **Default do menu é `5`** — `home.py:109` (`default="5"` em `Prompt.ask`). Decisão de UX: "se você não sabe o que fazer, veja onde está". `docs/tui/05-HOME-MENU.md:105` cita isso como "deliberate UX".
2. **Layout 2x2 KPI grid** — 4 cards em 2 colunas: scan visual cobre sono + pomodoros + hardwork + energia em 1 olhar. Trade-off: ~50 colunas de largura necessárias.
3. **Next-step panel SEMPRE no final** — `state_cmd.py` finaliza com `next_step`. User nunca fica sem saber "o que fazer agora".
4. **Timeline horizontal** — `cli/renderers.py:238-260` mostra o dia em barra única. User vê "onde no tempo" está.
5. **Renderiza mesmo com state vazio** — `_run_cmd` é robusto a `None`. Cards mostram `—`, não crasha. UX-013: poderia mostrar "Bem-vindo! Comece com 1" como onboarding.
6. **OBJ-02 do produto** — `docs/ux/00-visao-geral/01-objetivos-produto.md:44-57`. Métrica: < 5s para 1 olhar cobrir sono + pomodoros + hardwork + Q? + ação.

**Fricções mantidas:**

- **Layout assume ≥ 100 colunas** — kpi_card width=28 (×2 = 56) + padding = ~70. Em terminal 80 col, fica apertado. UX-003 (risco).
- **Cores sem fallback para daltônicos** — `crit` (red) pode ser invisível para ~8% dos homens. UX-002.
- **Próximo passo é genérico** — `next_step` baseado em quadrant. User que está em Q3 vê "Reduzir carga" sem detalhamento. Ver UX-009.

## Critérios de sucesso

- **Tempo:** < 5s para 1 olhar (métrica OBJ-02).
- **Render:** < 500ms para 30 dias de dados (métrica arquitetura — `architecture/05-DATA-FLOW.md:323`).
- **Robustez:** 0 crashes com state vazio.
- **Cobertura:** ≥ 1 sessão por dia em ≥ 60% dos dias (uso esperado).

## Onde aparece

- **Home menu opção 5** — `_dashboard` (`cli/home.py:281-283`)
- **Home menu Enter puro** — default `5` (`home.py:109`)
- **Submenu Reports opção 6** — `_menu_reports` (`home.py:329`)
- **Comando direto** — `operational state show [--date YYYY-MM-DD] [--json]`

## Notas de implementação

**File:line refs principais:**

- Fluxo principal: `cli/home.py:281-283`
- `_dashboard`: `cli/home.py:281-283`
- State controller: `cli/commands/state_cmd.py:71-...`
- State render: `cli/commands/state_cmd.py:100-...` (não lido integralmente)
- Dashboard layout 2x2: `cli/commands/state_cmd.py` (provavelmente linhas 130-200)
- `_period_now`: `state_cmd.py:50-57`
- `_budget_for_period`: `state_cmd.py:63-68`
- Default `5` no `Prompt.ask`: `home.py:109`

**Como adicionar 5º KPI card (Saúde):**

```python
# Em state_cmd.py, dentro de render_dashboard, adicionar:
saude_card = kpi_card(
    title="Saúde",
    value=f"{snap.saude_score}/10",
    color="primary",
    footer="baseado em sono + atividade",
)
# Adicionar ao grid 2x2 (vira 3x2 ou 2x3)
```

(Requer `snap.saude_score` no `DaySnapshot` — `core/services.py:55-103`).

**Como mudar layout para 3x2 (3 colunas):**

```python
# Substituir o grid:
grid = Table.grid(padding=(1, 2))
grid.add_column()  # col 1
grid.add_column()  # col 2
grid.add_column()  # col 3
# Adicionar 6 KPIs em 3 rows de 2 ou 2 rows de 3
```

(Atualmente usa 2x2 fixo.)

**Como mudar `Period` thresholds:**

`_period_now` (`state_cmd.py:50-57`) usa `PAV.HORARIO_ACORDAR_MIN`, `HORARIO_ACORDAR_MAX`, `HORARIO_DORMIR_MIN` de `constants.py`. Mudar lá.

**Como mudar `budget_for_period`:**

`state_cmd.py:63-68` retorna minutos orçados por período:
- MANHA: 180
- TARDE: 240
- NOITE: 0

Hard-coded. Mover para `PAVConstants` se mudar com frequência.
