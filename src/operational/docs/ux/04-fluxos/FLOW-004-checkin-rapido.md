# FLOW-004 — Check-in Rápido

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Estou no meio da tarde, ouvi uma notificação. Em menos de 30 segundos eu registrei meu estado atual (energia, foco) e opcionalmente uma nota."

**Ponto de entrada:**
- `operational home` → opção `4` (Check-in Rápido)
- Comando direto: `operational metric energy -e 7 -f 8` (sem nota) ou `operational journal create --text "..."` (só nota)

**Pré-condições:**
- Nenhuma. Funciona com state vazio. É o fluxo mais "leve" dos 4 principais.

**Telas envolvidas:**
- SCR-001 Home Menu
- SCR-014 Check-in Panel (header com 30s callout)
- SCR-015 Journal Note (opcional, se nota preenchida)

**Componentes críticos:**
- CMP-001 Header
- CMP-008 Hint dim `30 segundos. Registre seu estado atual.` (`home.py:269`)

**Duração típica:** 15s (2 prompts obrigatórios + 1 opcional)

**Taxa de abandono estimada:** < 2% (fluxo é o mais rápido, sem "Continuar?")

---

## Fluxo principal (happy path)

1. User digita `operational home`, digita `4`, Enter.
2. `_route("4")` despacha para `_flow_checkin` (`cli/home.py:265-278`).
3. Sistema limpa tela, mostra header `⚡ Check-in Rápido` e imprime linha dim `30 segundos. Registre seu estado atual.` (linha 269).
4. **Sem "Continuar?"** — entra direto nos prompts. Diferencial: este é o único dos 4 fluxos que pula a confirmação.
5. **Prompt 1 — Energia:** `IntPrompt`? Não — `Prompt.ask("Energia (1-10)", default="7")` (`home.py:270`). Aceita string.
6. **Prompt 2 — Foco:** `Prompt.ask("Foco (1-10)", default="7")` (`home.py:271`).
7. **Prompt 3 — Nota rápida (opcional):** `Prompt.ask("Nota rápida (opcional)", default="")` (`home.py:272`).
8. Sistema monta args: `["metric", "energy", "-e", e, "-f", f]` (`home.py:273`).
9. **Se nota foi preenchida:** chama `_run_cmd(args)` (métrica), depois `_run_cmd(["journal", "create", "--text", f"Check-in: {note}"])` (`home.py:275-276`).
10. **Se nota vazia:** chama `_run_cmd(args)` uma vez só (`home.py:278`).
11. `_run_cmd` chama `Press Enter to continue` — user pressiona Enter.
12. Volta ao menu. Sem banner de "Check-in registrado!" — implícito.

### Wireflow ASCII (FLOW-004)

```text
       ╭───────────────╮
       │ ◯  user digita│
       │ "4" no home   │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-014       │
       │ "30s.         │
       │  Registre     │
       │  estado       │
       │  atual."      │
       │ (sem "Continuar?")
       └───┬───────────┘
           │
           ▼
       ╱─────────────╲
      ╱ 1 prompt:      ╲
     ╱  Energia (1-10)  ╲──┐
     ╲  default 7        ╱  │
      ╲────────────────╱   │
               │           │
               ▼           │
       ╱─────────────╲     │
      ╱ 1 prompt:      ╲   │
     ╱  Foco (1-10)     ╲──┤
     ╲  default 7        ╱  │
      ╲────────────────╱   │
               │           │
               ▼           │
       ╱─────────────╲     │
      ╱ 1 prompt:      ╲   │  (default "",
      ╱  Nota (opcional)╲──┤   Enter pula)
     ╲  default ""      ╱  │
      ╲────────────────╱   │
               │           │
       ◇────────◇          │
      / nota       \──vazio─┤
      \ preenchida?/        │
       └─────┬────┘         │
             │ y            │
             ▼              │
       ╔═══════════════╗   │
       ║ metric energy ║   │ (sempre)
       ║ -e -f         ║   │
       ╚═══════╤═══════╝   │
               │           │
               ▼           │
       ┌───────────────┐   │ (só se nota)
       │ SCR-015       │   │
       │ journal       │   │
       │ create        │   │
       │ "Check-in:..." │  │
       └─────┬─────────┘   │
             │             │
             ▼             │
       ┌───────────────┐   │
       │ ◯  Press      │   │
       │  Enter to     │   │
       │  continue     │───┴─→ volta menu
       └───────────────┘     (sem banner)

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - -
  : (E1) -e 99 ou -f 99     : → error_panel
  :     (Pydantic range)    :
  : (E2) journal com nota   : → error_panel
  :     > max_length        :
  : (A2) Ctrl+C nota        : → estado:
  :     parcial             :   metric OK,
  :                          :   journal não
  - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o home menu (comando direto)

```bash
operational metric energy -e 7 -f 8
# 1 comando, 1 linha, ~0.5s de execução
```

Ou, com nota:

```bash
operational metric energy -e 7 -f 8 && \
operational journal create --text "Pico de foco pós-pomodoro"
```

Para o caso "só nota" (sem métrica):

```bash
operational journal create --text "interrupção do colega, perdi 20min"
```

### A2 — Múltiplos check-ins no mesmo dia

Idempotência por dia: `metric energy` é upsert (último vence). A1 do FLOW-002 explica.

**Diferença do FLOW-002:** FLOW-004 é desenhado para ser rodado várias vezes (sem cerimônia, sem preview). O label `30s. Registre seu estado atual.` é literal.

**Workaround para histórico:** rodar `journal create` em vez de `metric energy` (journal é append-only).

### A3 — Check-in sem nota (caminho mais curto)

1. Energia: `7` (Enter).
2. Foco: `7` (Enter).
3. Nota: Enter (pula).
4. `note` é `""` → entra no `else` (`home.py:277-278`).
5. Só chama `_run_cmd(["metric", "energy", "-e", "7", "-f", "7"])`.
6. **1 comando, 2 Enters.** ~5s.

### A4 — Check-in só com nota (raro)

Se o user quer anotar sem mexer em energia/foco:

```bash
operational journal create --text "ansiedade pré-apresentação"
```

Não usa o FLOW-004 — usa comando direto. UX-009 sugere adicionar ao menu "Check-in só nota" se uso crescer.

### A5 — Check-in com nota longa

`Prompt.ask` lê uma linha. Se a nota tem `\n`, **só a primeira linha** é capturada.

Workaround:

```bash
operational journal create --text "Linha 1
Linha 2
Linha 3"
```

(via aspas e bash multi-line). UX-005: doc não menciona essa limitação.

### A6 — Loop "in-process" via menu

Mesma mecânica dos outros fluxos. `typer_app(args, standalone_mode=False)` em `home.py:60`.

---

## Exceções e erros

### E1 — Pydantic `ValidationError` em energia/foco

- **Causa:** `-e 99` ou `f` (string que vira int falha).
- **Onde:** `metric_cmd.energy` (linha ~100-198).
- **Tratamento:** `error_panel` com `BadParameter`.
- **Recuperação:** user retenta. Como não há "Continuar?", o erro é inline.

### E2 — Journal com texto > `max_length`

- **Causa:** Pydantic `JournalEntry.text` limite.
- **Onde:** `journal_cmd.create` (não lido).
- **Tratamento:** `error_panel`.
- **Recuperação:** user volta, encurta nota, retenta.

### E3 — Ctrl+C entre prompts

- Posição 1 (energia): nada gravado.
- Posição 2 (foco): nada gravado (energia e foco são coletados juntos).
- Posição 3 (nota): nada gravado ainda.
- **Pós-métrica, antes do journal (nota preenchida):** métrica gravada, journal não.
- `home()` sai limpo.

### E4 — User digita `-e` ou `-f` com float

- **Causa:** `Prompt.ask` aceita string; controller parseia como int.
- **Onde:** `metric_cmd.energy` (provavelmente `int` type hint).
- **Tratamento:** `error_panel` com `ValueError`.
- **Risco:** "Energia (1-10)" sugere inteiro, mas `Prompt.ask` não força. UX-009 sugere `IntPrompt.ask`.

### E5 — Terminal sem suporte a emoji (legacy Windows)

- **Causa:** header `⚡ Check-in Rápido` usa emoji.
- **Onde:** `home.py:268`.
- **Tratamento:** Rich substitui por `?` ou mostra `[]`. Sem erro fatal.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-001-home-menu.md` (ref futura)
- `docs/ux/05-telas/SCR-014-checkin-panel.md` (ref futura)
- `docs/ux/05-telas/SCR-015-journal-note.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem.

## Componentes críticos

- CMP-001 Header — `cli/home.py:84-93`
- CMP-008 Hint dim `30 segundos. Registre seu estado atual.` — `home.py:269` (não é componente reutilizável, é literal)
- CMP-007 confirmation banner — **ausente** (FLOW-004 não tem banner — escolha deliberada para não atrasar)
- CMP-004 error_panel — `ui/components.py:390-426`

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **Sem "Continuar?"** — é o único dos 4 fluxos principais que pula a confirmação. Trade-off: user entra "por acidente" no fluxo e gasta 3 prompts. Aceitável: prompts têm `default=`, Enter rápido = registro rápido.
2. **Header `30 segundos`** — define expectativa. User sabe que vai ser rápido.
3. **3 prompts (não 5, não 1)** — balanço: o mínimo útil (energia + foco) + 1 bônus (nota). Não precisa de "bloco" ou "rotina" porque check-in é atômico.
4. **Nota é opcional e com `default=""`** — `home.py:272`. Não obriga. Quem quer registrar só estado numérico ignora.
5. **Sem banner de sucesso** — `home.py` não imprime `✔ Check-in registrado!` após o fluxo. A confirmação vem do `_run_cmd` interno (`metric energy` mostra `✓ Sono/Energia registrado`). Decisão: evitar poluição visual.
6. **Roda múltiplas vezes por dia sem fricção** — diferente de FLOW-001/002/003 que são "momentos". Check-in é "tempo todo".

**Fricções mantidas:**

- **Energia e foco são inteiros 1-10, mas prompt usa `Prompt.ask` (string)** — UX-009 sugere `IntPrompt.ask`. Aceita float e string não-numérica que falha no controller. Manter `Prompt.ask` para consistência com outros fluxos.
- **Sem confirmação visual "Check-in registrado"** — user pode ficar na dúvida se salvou. Verificar com `operational state show` ou `metric list`.

## Critérios de sucesso

- **Tempo:** < 30s com 3 Enters (métrica oficial do flow).
- **Abandono:** < 2% (mais leve que qualquer outro fluxo).
- **Frequência:** ≥ 3 check-ins por dia em ≥ 30% dos dias (uso ideal).
- **Erros:** < 0.1 por sessão (zero prompts com range; só `metric energy` pode falhar).

## Onde aparece

- **Home menu opção 4** — `_flow_checkin` (`cli/home.py:265-278`)
- **Comando direto** — `metric energy`, `journal create`
- **Atalho mental** — `4` é "check-in", pode ser invocado a qualquer momento

## Notas de implementação

**File:line refs principais:**

- Fluxo principal: `cli/home.py:265-278`
- `_flow_checkin`: `cli/home.py:265-278`
- Metric energy controller: `cli/commands/metric_cmd.py:100-198`
- Journal controller: `cli/commands/journal_cmd.py:1-...`

**Como adicionar etapa "humor" (1-5):**

```python
# Em _flow_checkin, após "Foco" (linha 271):
h = Prompt.ask("Humor (1-5)", default="3")
args = ["metric", "energy", "-e", e, "-f", f, "--humor", h]  # se o controller suportar
_run_cmd(args)
```

(Requer adicionar `--humor` flag em `metric_cmd.energy` e Pydantic entity `Metric.humor`.)

**Como mudar default de energia/foco:**

- `home.py:270` (energia, default 7)
- `home.py:271` (foco, default 7)

**Como mudar label do header:**

- `home.py:268` (`⚡ Check-in Rápido`)
- `_header` recebe o título, renderiza em painel.

**Consideração sobre timeout:**

Os prompts do FLOW-004 são os mais candidatos a ter timeout (cenário: user abre o menu, clica 4, vai atender o telefone, esquece). UX-004. Solução: wrapper `Prompt.ask` com `prompt_toolkit` ou `pexpect`. Não implementado.
