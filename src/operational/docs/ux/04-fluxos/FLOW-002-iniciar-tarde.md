# FLOW-002 — Iniciar Tarde

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Voltei do almoço. Em menos de 1 minuto eu registrei o bloco da tarde, criei a rotina CORE de hardwork e fiz um check-in de energia/foco."

**Ponto de entrada:**
- `operational home` → opção `2` (Iniciar Tarde)
- Comando direto: `operational block create TARDE --label "Deep Work"` + `operational routine create "Hardwork" TARDE CORE` + `operational metric energy -e 7 -f 8`

**Pré-condições:**
- FLOW-001 normalmente já foi rodado (manhã registrada), mas não é estritamente necessário
- `Period.TARDE` inferido automaticamente se hora atual ∈ [6, HORARIO_DORMIR_MIN) (ver `state_cmd.py:50-57`)

**Telas envolvidas:**
- SCR-001 Home Menu
- SCR-006 Block Create (TARDE)
- SCR-007 Routine Create (CORE)
- SCR-008 Energy Check-in

**Componentes críticos:**
- CMP-001 Header panel
- CMP-002 section_panel
- CMP-007 confirmation banner (`✔ Tarde iniciada!` linha 213)

**Duração típica:** 25s (3 prompts + 3 comandos)

**Taxa de abandono estimada:** ~5% (fluxo é mais leve que a manhã, menos campos)

---

## Fluxo principal (happy path)

1. User digita `operational home`, vê menu, digita `2`, Enter.
2. `_route("2")` despacha para `_flow_afternoon` (`cli/home.py:191-213`).
3. Sistema limpa tela, mostra header `💻 Iniciar Tarde` e imprime 3 linhas "Esta rotina cobre:" (linhas 195-198).
4. Sistema pergunta `Continuar? (y/n)`, default `y`. User pressiona Enter.
5. **Step 1 — Bloco TARDE (1 prompt):** `Label do bloco da tarde`, default `Deep Work — Features`. User aceita ou customiza.
6. Sistema invoca `block create TARDE --label <label>` (`home.py:204`).
7. **Step 2 — Rotina CORE (1 prompt):** `Nome da rotina CORE`, default `Hardwork Dev`. User aceita ou renomeia.
8. Sistema invoca `routine create <nome> TARDE CORE` (`home.py:207`).
9. **Step 3 — Check-in energia/foco (2 prompts):** Energia e Foco (1-10 cada), defaults `7` e `8`. User pode aceitar.
10. Sistema invoca `metric energy -e <e> -f <f>` (`home.py:211`).
11. `_run_cmd` chama `Prompt.ask("Press Enter to continue")` — user pressiona Enter.
12. `home()` itera, mostra menu de novo.
13. Sucesso: `✔ Tarde iniciada!` em verde bold (`home.py:213`).

### Wireflow ASCII (FLOW-002)

```text
       ╭───────────────╮
       │ ◯  user abre  │
       │  operational  │
       │     home      │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-001       │◀──────╮
       │ Home Menu     │       │
       └───┬───────────┘       │  (loop)
           │ digita "2"        │
           ▼                   │
       ┌───────────────┐       │
       │ Continuar?    │       │
       │   y / n       │       │
       └───┬───────────┘       │
           │ y                 │
           ▼                   │
       ╱─────────────╲         │
      ╱ 1 prompt:      ╲       │
     ╱  label bloco     ╲───┐  │
     ╲  TARDE (default) ╱   │  │
      ╲────────────────╱    │  │
               │            │  │
               ▼            │  │
       ╔═══════════════╗    │  │
       ║ block create  ║    │  │
       ║ TARDE --label ║    │  │
       ╚═══════╤═══════╝    │  │
               │            │  │
               ▼            │  │
       ╱─────────────╲      │  │
      ╱ 1 prompt:      ╲    │  │
     ╱  nome rotina     ╲───┘  │
     ╲  CORE  (default) ╱      │
      ╲────────────────╱       │
               │               │
               ▼               │
       ╔═══════════════╗       │
       ║ routine create║       │
       ║ <name>        ║       │
       ║ TARDE CORE    ║       │
       ╚═══════╤═══════╝       │
               │               │
               ▼               │
       ╱─────────────╲         │
      ╱ 2 prompts:     ╲       │
     ╱  Energia + Foco  ╲──┐   │
     ╲  (1-10, default) ╱  │   │
      ╲────────────────╱   │   │
               │           │   │
               ▼           │   │
       ╔═══════════════╗   │   │
       ║ metric energy ║   │   │
       ║ -e -f         ║   │   │
       ╚═══════╤═══════╝   │   │
               │           │   │
               ▼           │   │
       ┌───────────────┐   │   │
       │ ◯  Tarde      │   │   │
       │  iniciada! ✓  │───┴──→╯
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - -
  : (E1) range -e/f        : → error_panel
  :     ex. -e 99          :   (BadParameter)
  : (E2) Ctrl+C step 1    : → state parcial
  :                        :  (bloco não
  :                        :   foi gravado)
  : (A3) user digita "n"  : → volta ao menu
  :     em "Continuar?"    :   sem efeito
  - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o home menu (comando direto)

```bash
operational block create TARDE --label "Deep Work — Features" && \
operational routine create "Hardwork Dev" TARDE CORE && \
operational metric energy -e 7 -f 8
```

3 comandos em 1 linha. Cobre 100% do `_flow_afternoon`. Útil para scripts pós-almoço.

### A2 — Re-rodar check-in várias vezes ao longo da tarde

O FLOW-002 só faz **1** check-in. Para check-ins múltiplos, o user pode:

```bash
operational metric energy -e 8 -f 9   # 14h
operational metric energy -e 6 -f 5   # 16h (pós-pomodoro ruim)
operational metric energy -e 7 -f 7   # 18h (recuperado)
```

Cada chamada é um novo `upsert` no mesmo dia — o repo mantém **uma** métrica por dia (`sleep_records.list()` filtra por data, ver `state_cmd.py:82`). Múltiplos registros sobrescrevem o último.

> **Nota:** comportamento idempotente (último vence). Se quiser histórico, ver FLOW-004 (check-in via journal).

### A3 — User cancela com "n" em "Continuar?"

Fluxo curto:

1. `_flow_afternoon` chama `Prompt.ask("Continuar?", default="y")`.
2. User digita `n`, Enter.
3. `if ... != "y": return` (`home.py:200-201`) — função retorna sem efeito.
4. Volta ao menu principal. State inalterado.

### A4 — Dataset sintético ativo

Se `TIME_TASKER_DATASET=synthetic` e state já tem blocos TARDE para hoje:

- `block create TARDE --label ...` faz `upsert` (substitui o anterior). Ver `cli/state.py:upsert`.
- `routine create "Hardwork Dev" TARDE CORE` faz `upsert` (mesmo `id` se nome colide).
- `metric energy` sobrescreve a métrica de energia do dia.

Comportamento: o último input vence. Não há acumulação. UX-019.

### A5 — Energy/foco com nota rápida

Se o user quer anexar uma nota ao check-in (causa: "tô focado pq dormi bem"):

```bash
operational metric energy -e 8 -f 9
operational journal create --text "Pico de foco pós-almoço leve"
```

O FLOW-002 não tem essa etapa built-in; tem que ser feito fora. UX-009 sugere unificar.

### A6 — Loop "in-process" via menu

Mesma mecânica do FLOW-001 — `typer_app(args, standalone_mode=False)`, `redirect_stdout`, `strip_ansi` (`cli/home.py:49-67`). Ver `docs/tui/05-HOME-MENU.md`.

---

## Exceções e erros

### E1 — Pydantic `ValidationError` em `metric energy`

- **Causa:** `-e 99` ou `-e -1`. Pydantic `IntPrompt.ask` (não usado) ou `typer.Option(min=1, max=10)` rejeita.
- **Onde:** `cli/commands/metric_cmd.py` (energy command, não lido integralmente; ver `metric_cmd.py:100-198`).
- **Tratamento:** `_run_cmd` captura `Exception` e renderiza `error_panel` vermelho.
- **Recuperação:** user volta ao menu, vê o erro, retenta.

### E2 — `routine create` com nome duplicado

- **Causa:** user já criou rotina com mesmo nome e `Routine.id` colide.
- **Onde:** `cli/state.py:JSONRepository.upsert` (não lido integralmente).
- **Tratamento:** Pydantic permite; repo faz `upsert` silencioso. Não há erro visível.
- **Risco:** UX-006 — sem aviso de substituição. User pensa que criou 2 rotinas, mas sobrescreveu.

### E3 — Time-tasker state dir não existe

- Mesma mecânica do FLOW-001 E2. Silent recovery, sem mensagem.

### E4 — `block create TARDE` sem `Period.TARDE` configurado

- **Causa:** Pydantic entity `TimeBlock` tem `period: Period` com valores enum. Se valor inválido, rejeita.
- **Tratamento:** Typer intercepta antes do controller.
- **Recuperação:** user vê `Invalid value for 'PERIOD'`, retenta.

### E5 — Ctrl+C entre prompts

- Step 1 cancelado: nada gravado.
- Step 2 cancelado: bloco gravado, rotina não.
- Step 3 cancelado: bloco + rotina gravados, energia não.
- `except KeyboardInterrupt` em `home()` (`home.py:477-480`) sai limpo.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-001-home-menu.md` (ref futura)
- `docs/ux/05-telas/SCR-006-block-create.md` (ref futura)
- `docs/ux/05-telas/SCR-007-routine-create.md` (ref futura)
- `docs/ux/05-telas/SCR-008-energy-checkin.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem. Refs são semânticas.

## Componentes críticos

- CMP-001 Header — `cli/home.py:84-93`
- CMP-007 confirmation banner — `cli/home.py:213`
- CMP-004 error_panel — `ui/components.py:390-426`
- CMP-006 input_summary — `cli/input_summary.py:1-...` (auto-render em `metric energy`)

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **3 etapas em vez de 1 prompt com tudo** — mantém coerência com FLOW-001 (manhã tem 3 etapas, tarde tem 3 etapas).
2. **Check-in de energia no final** — é o "termômetro" que vai aparecer no próximo relatório. Captura o estado pós-almoço.
3. **Default `7`/`8` para energia/foco** — alinhado com PAV `ENERGY_DEFAULT`/`FOCUS_DEFAULT`. Usuário pode aceitar.
4. **Sem almoço explícito** — FLOW-002 não pede `LunchRecord`. Workaround: `operational lunch record --eat 30 --rest 15 --pesado false` (controller existe, ver `lunch_cmd.py:1-...`).

**Fricções mantidas:**

- **Não há etapa "registrar almoço"** — almoço é opcional, e o FLOW-002 confia que o user registrou fora. Trade-off: almoço fica meio "invisível" no fluxo. UX-009 sugere adicionar.
- **Check-in é único** — múltiplos check-ins (14h, 16h, 18h) sobrescrevem. UX-019. Workaround: journal.

## Critérios de sucesso

- **Tempo:** < 30s com 4 Enters (label + nome + energia + foco).
- **Abandono:** < 5% (mais leve que manhã).
- **Erros:** < 0.3 por sessão.
- **Cobertura:** ≥ 80% dos dias têm check-in de tarde (medido por `state show`).

## Onde aparece

- **Home menu opção 2** — `_flow_afternoon` (`cli/home.py:191-213`)
- **Comando direto** — `block create`, `routine create`, `metric energy`
- **Atalho mental** — `2` no home menu é "tarde"

## Notas de implementação

**File:line refs principais:**

- Fluxo principal: `cli/home.py:191-213`
- `_flow_afternoon`: `cli/home.py:191-213`
- Block controller: `cli/commands/block_cmd.py:1-...`
- Routine controller: `cli/commands/routine_cmd.py:1-...`
- Energy metric controller: `cli/commands/metric_cmd.py:100-198`

**Como adicionar etapa "registrar almoço":**

```python
# Em _flow_afternoon, após step 2 (linha 207):
if Prompt.ask("Registrar almoço agora?", choices=["y", "n"], default="n") == "y":
    eat = Prompt.ask("Tempo de almoço (min)", default="30")
    rest = Prompt.ask("Descanso pós-almoço (min)", default="15")
    pesado = Prompt.ask("Pesado?", choices=["y", "n"], default="n")
    _run_cmd(["lunch", "record", "--eat", eat, "--rest", rest, "--pesado", pesado])
```

**Como mudar defaults:**

- Default `Deep Work — Features` em `cli/home.py:203`
- Default `Hardwork Dev` em `cli/home.py:206`
- Default `7` para energia em `cli/home.py:209`
- Default `8` para foco em `cli/home.py:210`
