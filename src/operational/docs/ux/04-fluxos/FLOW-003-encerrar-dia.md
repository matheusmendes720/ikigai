# FLOW-003 — Encerrar Dia

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Vou dormir. Em menos de 2 minutos eu registrei o jantar, o shutdown ritual, refleti sobre o dia (deu certo / errado / aprendizado / ajustes) e fiz o check-in final de energia/foco."

**Ponto de entrada:**
- `operational home` → opção `3` (Encerrar Dia)
- Comando direto: `operational routine create "Shutdown Ritual" NOITE EXIT` + `operational block create NOITE --label "Preparação + Jantar"` + `operational journal create --text "..."` + `operational metric energy -e 5 -f 5`

**Pré-condições:**
- Dia atual teve FLOW-001 ou FLOW-002 (ou `demo seed` populou state)
- `Period.NOITE` inferido se hora ≥ `HORARIO_DORMIR_MIN` (ver `state_cmd.py:56`)

**Telas envolvidas:**
- SCR-001 Home Menu
- SCR-009 OKR Reflection (5 perguntas-chave)
- SCR-010 Routine Create (NOITE EXIT)
- SCR-011 Block Create (NOITE)
- SCR-012 Journal Create
- SCR-013 Energy Check-in (final do dia)

**Componentes críticos:**
- CMP-001 Header
- CMP-005 OKR questions panel (`_flow_evening` linhas 220-225)
- CMP-007 confirmation banner (`✔ Dia encerrado!` linha 262)

**Duração típica:** 90s (5 perguntas abertas + 4 comandos)

**Taxa de abandono estimada:** ~25% (etapa de reflexão exige escrever; users pulam com Enter; pode ser desejável)

---

## Fluxo principal (happy path)

1. User digita `operational home`, digita `3`, Enter.
2. `_route("3")` despacha para `_flow_evening` (`cli/home.py:216-262`).
3. Sistema limpa tela, mostra header `🌙 Encerrar Dia` e imprime 5 perguntas-chave (linhas 220-225):
   1. O que deu certo?
   2. O que deu errado?
   3. Maior aprendizado?
   4. Algum desvio do padrão?
   5. Ajustes finos para amanhã?
4. Sistema pergunta `Continuar? (y/n)`, default `y`. User pressiona Enter.
5. **Step 1 — Rotina NOITE EXIT (0 prompts):** `_run_cmd(["routine", "create", "Shutdown Ritual", "NOITE", "EXIT"])` (`home.py:232`).
6. **Step 2 — Bloco NOITE (0 prompts):** `_run_cmd(["block", "create", "NOITE", "--label", "Preparação + Jantar"])` (`home.py:235`).
7. **Step 3 — Reflexão (4 prompts):** `O que deu certo hoje?`, `O que deu errado hoje?`, `Maior aprendizado do dia?`, `Ajustes finos para amanhã?`. Todos com `default=""` — user pode pular com Enter (`home.py:238-241`).
8. Sistema monta string multi-linha com prefixos `✅ Deu certo:`, `❌ Deu errado:`, `💡 Aprendizado:`, `🔧 Ajustes:` para cada resposta não-vazia (`home.py:243-252`).
9. Se houver pelo menos 1 linha: `_run_cmd(["journal", "create", "--text", text])` (`home.py:255`).
10. **Step 4 — Check-in final (2 prompts):** Energia e Foco, defaults `5` e `5`. User aceita ou ajusta (`home.py:258-259`).
11. Sistema invoca `metric energy -e <e> -f <f>` (`home.py:260`).
12. `_run_cmd` chama `Press Enter to continue` — user pressiona Enter.
13. Sucesso: `✔ Dia encerrado!` em verde bold (`home.py:262`).

### Wireflow ASCII (FLOW-003)

```text
       ╭───────────────╮
       │ ◯  user digita│
       │ "3" no home   │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-009       │
       │ OKR Questions │  ◀── 5 perguntas
       │ (5 bullets)   │      mostradas
       └───┬───────────┘      antes
           │ Continuar? y
           ▼
       ╔═══════════════╗
       ║ routine create║
       ║ "Shutdown     ║  (step 1, 0 prompts)
       ║  Ritual"      ║
       ║ NOITE EXIT    ║
       ╚═══════╤═══════╝
               │
               ▼
       ╔═══════════════╗
       ║ block create  ║  (step 2, 0 prompts)
       ║ NOITE --label ║
       ╚═══════╤═══════╝
               │
               ▼
       ┌───────────────┐
       │ 4 prompts     │  ◀── default=""
       │ abertos com   │      Enter pula
       │ default ""    │
       └───┬───────────┘
           │ monta string
           ▼
       ┌───────────────┐
       │ if lines:     │  ◀── só roda se
       │   journal     │      user escreveu
       │   create      │      ≥ 1 resposta
       └───┬───────────┘
           │
           ▼
       ╱─────────────╲
      ╱ 2 prompts:     ╲
     ╱  Energia + Foco  ╲──┐
     ╲  final do dia     ╱  │
      ╲────────────────╱   │
               │           │
               ▼           │
       ╔═══════════════╗   │
       ║ metric energy ║   │
       ║ -e -f         ║   │
       ╚═══════╤═══════╝   │
               │           │
               ▼           │
       ┌───────────────┐   │
       │ ◯  Dia        │   │
       │  encerrado! ✓ │───┴──→ volta menu
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - -
  : (E1) Ctrl+C step 3    : → state parcial
  :     (após step 1+2    :   (rotina+bloco
  :      gravados,        :    sim; journal
  :      journal não)     :    não)
  : (E2) user pula TUDO   : → só step 1+2
  :     (4 Enters)        :   rodaram; sem
  :                        :   reflexão
  : (E3) journal.create   : → error_panel
  :     falha (Pydantic)  :
  - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o home menu (comando direto)

```bash
operational routine create "Shutdown Ritual" NOITE EXIT && \
operational block create NOITE --label "Preparação + Jantar" && \
operational journal create --text "✅ Deu certo: entreguei o relatório.
❌ Deu errado: dormi tarde.
💡 Aprendizado: time-boxing funciona.
🔧 Ajustes: acordar 4h amanhã." && \
operational metric energy -e 5 -f 5
```

Útil para quem prefere editar texto num editor e colar no shell.

### A2 — Reflexão via `reflect saida` direto

`cli/commands/reflect_cmd.py:1-...` tem um controller dedicado (`reflect saida`) que faz **só** a etapa de reflexão. É o FLOW-003 com steps 1+2 pulados:

```bash
operational reflect saida
# 4 prompts: deu_certo, deu_errado, maior_aprendizado, ajustes
# persiste em DailyReflection
```

Trade-off: fica em entidade separada (`daily_reflections` vs `journals`). User que prefere separar "reflexão OKR" de "journal livre" usa `reflect`. Ver `docs/ux/00-visao-geral/01-objetivos-produto.md` OBJ-04.

### A3 — User pula toda a reflexão (4 Enters)

1. Step 3: 4 prompts com `default=""` — user pressiona Enter 4 vezes.
2. `lines = []` (todas as condicionais `if X` são falsas).
3. `if lines: ...` é False — `journal create` **não** é chamado.
4. Step 4 (check-in final) ainda roda.
5. State: rotina + bloco + métrica. Sem journal, sem reflexão.

Comportamento **intencional**: encerra o dia "no automático" para quem está cansado. Ver fricção mantida abaixo.

### A4 — Dataset sintético ativo

- Rotina `Shutdown Ritual` provavelmente já existe se seed cobriu 7 dias.
- `upsert` substitui sem aviso. Estado idêntico ao sobrescrito.
- `metric energy -e 5 -f 5` sobrescreve o final do dia no seed.

### A5 — Edição de reflexão existente

Não há `reflect update`. Para editar:

```bash
# 1. Listar
operational journal list
# 2. Deletar (se implementado)
operational journal delete <id>
# 3. Recriar
operational journal create --text "..."
```

Risco: `journal delete` pode não existir. Ver UX-006. Workaround: aceitar que o journal do dia está "fechado".

### A6 — Múltiplas reflexões no mesmo dia (raro)

Se o user roda FLOW-003 duas vezes no mesmo dia:

- Step 1+2: `upsert` (mesmo `id`).
- Step 3: novo `JournalEntry` com timestamps diferentes (não dedupe por data).
- Step 4: `metric energy` sobrescreve.

Resultado: 2+ journals no mesmo dia, ambos visíveis em `journal list`. **Não é bug** — é a semântica de "cada execução é uma entrada".

---

## Exceções e erros

### E1 — `journal create` com texto > limite

- **Causa:** Pydantic `JournalEntry.text` tem `max_length` (provavelmente 2000-5000 chars).
- **Onde:** `cli/commands/journal_cmd.py:1-...` (não lido integralmente).
- **Tratamento:** `error_panel` vermelho com `ValidationError`.
- **Recuperação:** user volta ao menu, encurta texto, retenta. Risco baixo na prática.

### E2 — User escreve emoji que o terminal não suporta

- **Causa:** Windows cmd.exe antigo, terminal sem UTF-8.
- **Onde:** `home.py:243-251` monta string com `✅ ❌ 💡 🔧`.
- **Tratamento:** Rich console substitui por `?` ou ignora. Sem erro fatal.
- **UX-011 (dark mode e encoding)** — fora do escopo deste fluxo.

### E3 — Ctrl+C entre steps

- Após step 1: rotina gravada, sem bloco/reflexão.
- Após step 2: rotina+bloco, sem reflexão.
- Após step 3 (parcial): rotina+bloco+journal (com 1-3 respostas), sem check-in.
- `home()` captura e sai limpo.

### E4 — `metric energy` no fim do dia com valores absurdos

- **Causa:** user digita `-e 99` ou esquece o `-e` (vira `None`).
- **Onde:** `metric_cmd.energy` (linha ~100-198) tem `typer.Option(min=1, max=10)`.
- **Tratamento:** `error_panel` com `BadParameter: Invalid value for '-e'`.
- **Recuperação:** user retenta.

### E5 — State dir não-writable

- **Causa:** permissões Unix erradas em `~/.time-tasker/`.
- **Onde:** `JSONRepository.upsert` tenta escrever, recebe `PermissionError`.
- **Tratamento:** exceção sobe, `_run_cmd` captura, `error_panel`.
- **Diagnóstico:** `operational doctor` reporta `state_dir: FAIL (not writable)`.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-001-home-menu.md` (ref futura)
- `docs/ux/05-telas/SCR-009-okr-reflection.md` (ref futura)
- `docs/ux/05-telas/SCR-010-routine-noite.md` (ref futura)
- `docs/ux/05-telas/SCR-011-block-noite.md` (ref futura)
- `docs/ux/05-telas/SCR-012-journal-create.md` (ref futura)
- `docs/ux/05-telas/SCR-013-energy-final.md` (ref futura)

> **Nota:** Os SCR-* ainda não existem. Refs são semânticas.

## Componentes críticos

- CMP-001 Header — `cli/home.py:84-93`
- CMP-005 OKR questions panel — `_flow_evening` linhas 220-225 (não é componente, é inline)
- CMP-007 confirmation banner — `cli/home.py:262`
- CMP-004 error_panel — `ui/components.py:390-426`
- CMP-006 input_summary — `cli/input_summary.py` (auto-em `journal create`)

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **Reflexão tem 4 prompts com `default=""`** — encoraja user a escrever, mas não obriga. Quem está exausto pode pular (A3).
2. **5 perguntas-chave antes de "Continuar?"** — mostra o que vem a seguir. Reduz ansiedade. Se o user não quer responder, digita `n` em 5s.
3. **Texto multi-linha consolidado em 1 journal** — em vez de 4 journals separados. Mais fácil de revisar depois (`journal list` mostra 1 entrada, não 4).
4. **Prefixos emoji `✅ ❌ 💡 🔧`** — codificam visualmente a categoria. User que rola `journal list` vê estrutura.
5. **Rotina + bloco automáticos (sem prompt)** — `Shutdown Ritual` é tão previsível que não precisa perguntar. Segue o pattern de FLOW-001 step 2.
6. **OBJ-04 — Reflexão < 2min** — `docs/ux/00-visao-geral/01-objetivos-produto.md:75-86`. Métrica oficial do produto.

**Fricções mantidas:**

- **Não há etapa "listar o que deu certo vs errado antes de pedir para escrever"** — a fricção aqui é *forçar* o user a pensar, não a *guiar* o pensamento. UX-009 sugere quebrar em sub-etapas se abandono for > 30%.
- **Sem "revise antes de salvar"** — a reflexão é commit-on-Enter. Sem undo. UX-006.
- **Texto vai como `JournalEntry`, não como `DailyReflection`** — `journal_cmd` é genérico, `reflect_cmd` é específico. Trade-off: journal é mais flexível (livre), reflection é mais estruturado (deu_certo/deu_errado/...). User que quer campos estruturados deve usar `reflect saida` (A2).

## Critérios de sucesso

- **Tempo:** < 2min para 4 prompts preenchidos (métrica OBJ-04).
- **Abandono:** < 30% (reflexão é opcional, mas maioria preenche pelo menos 1 campo).
- **Qualidade:** ≥ 2 dos 4 campos preenchidos em ≥ 50% das sessões.
- **Reuso:** `journal list` mostra ≥ 1 entrada por dia em ≥ 70% dos dias.

## Onde aparece

- **Home menu opção 3** — `_flow_evening` (`cli/home.py:216-262`)
- **Comando direto** — `routine create`, `block create`, `journal create`, `metric energy`, `reflect saida`
- **Atalho mental** — `3` no home menu é "encerrar"
- **Documentação do produto** — `docs/ux/00-visao-geral/01-objetivos-produto.md` OBJ-04

## Notas de implementação

**File:line refs principais:**

- Fluxo principal: `cli/home.py:216-262`
- `_flow_evening`: `cli/home.py:216-262`
- Routine controller: `cli/commands/routine_cmd.py:1-...`
- Block controller: `cli/commands/block_cmd.py:1-...`
- Journal controller: `cli/commands/journal_cmd.py:1-...`
- Reflect controller: `cli/commands/reflect_cmd.py:1-...`
- Energy metric controller: `cli/commands/metric_cmd.py:100-198`

**Como adicionar etapa "listar 3 vitórias do dia" antes da reflexão:**

```python
# Em _flow_evening, antes do step 1 (linha 231):
console.print("[bold]Liste 3 vitórias do dia (qualquer tamanho):[/bold]")
wins = []
for i in range(3):
    w = Prompt.ask(f"  Vitória {i+1}", default="")
    if w:
        wins.append(w)
if wins:
    text = "\n".join(f"🏆 {w}" for w in wins)
    _run_cmd(["journal", "create", "--text", text])
```

**Como mudar perguntas OKR:**

Editar `cli/home.py:220-225` (lista de 5 prints). As perguntas não são derivadas de config — estão hard-coded no fluxo.

**Onde ajustar defaults:**

- Default `5` para energia final em `cli/home.py:258`
- Default `5` para foco final em `cli/home.py:259`
- Default `""` para perguntas de reflexão em `cli/home.py:238-241` (não tem como ajustar — é literal)
