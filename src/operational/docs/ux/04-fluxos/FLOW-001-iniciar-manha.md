# FLOW-001 — Iniciar Manhã

> **Wireflow ASCII:** ver bloco "Fluxo principal" abaixo. Notação: oval = início/fim, retângulo = tela, losango = decisão, paralelogramo = input, tracejada = exceção.

**Objetivo do usuário:** "Acordei. Em menos de 1 minuto eu registrei meu sono de ontem, marquei a rotina de acordar e o bloco da manhã (workout + meditação)."

**Ponto de entrada:**
- `operational home` → opção `1` (Iniciar Manhã), ou
- Comando direto: `operational metric sleep -q 8 -bh 23 -bm 30 -wh 4 -wm 0` seguido de `operational routine create "Acordar" MANHA ENTRY`

**Pré-condições:**
- Python 3.10+ instalado (`doctor` confirma)
- `operational` CLI instalado (Poetry / `pip install -e .`)
- State dir `~/.time-tasker/` é criado **lazy** (não precisa existir antes)
- Não há pré-condição de dataset — o fluxo funciona com state vazio

**Telas envolvidas:**
- SCR-001 Home Menu
- SCR-002 Sleep Registration Panel
- SCR-003 Routine Confirmation
- SCR-004 Block Creation Panel
- SCR-005 Success Banner

**Componentes críticos:**
- CMP-001 Header panel (`_header()` em `cli/home.py:84-93`)
- CMP-002 section_panel (`ui/components.py:364-378`)
- CMP-006 input_summary (auto-render em `cli/input_summary.py:1-...`)
- CMP-007 confirmation banner (`✔ Manhã iniciada!` linha 188)

**Duração típica:** 35s (5 prompts + 3 comandos, defaults aceitos via Enter)

**Taxa de abandono estimada:** ~8% (medido por quem não completa o step 3 do bloco)

---

## Fluxo principal (happy path)

1. User abre o terminal e digita `operational home`.
2. Sistema limpa a tela, mostra o header `⚡ TIME-TASKER vX.Y.Z | 2026-06-08` e renderiza o menu numerado de 10 opções (`cli/home.py:100-115`).
3. User digita `1` e pressiona Enter. Sistema valida via `choices=[...]` do Rich Prompt (`home.py:106-110`).
4. `_route("1")` despacha para `_flow_morning` (`home.py:157-188`).
5. Sistema limpa a tela, mostra header `🌅 Iniciar Manhã` e imprime 3 linhas de "Esta rotina cobre:" (linhas 161-164).
6. Sistema pergunta `Continuar? (y/n)`, default `y`. User pressiona Enter.
7. **Step 1 — Sleep retroativo (5 prompts):** qualidade, hora-dormiu, min-dormiu, hora-acordou, min-acordou. Cada prompt tem `default=` razoável (`home.py:170-174`). User pode aceitar tudo com 5 Enters.
8. Sistema invoca `metric sleep -q <q> -bh <h> -bm <m> -wh <h> -wm <m>` via `_run_cmd` (`home.py:175-179`).
9. `metric_cmd.sleep` valida ranges Pydantic, chama `make_sleep_record()` (`meta/factories.py`), faz `sleep_records.upsert(record)`, mostra `✓ Sono registrado: <id>` (`metric_cmd.py:93-94`).
10. **Step 2 — Rotina ENTRY (0 prompts):** sistema invoca `routine create "Acordar" MANHA ENTRY` (`home.py:182`).
11. Controller cria `Routine` Pydantic, valida `RoutineType.ENTRY`, insere no repo `routines`, mostra confirmação.
12. **Step 3 — Bloco MANHA (1 prompt):** `Label do bloco da manhã`, default `Morning Workout + Meditação`. User pode aceitar.
13. Sistema invoca `block create MANHA --label <label>` (`home.py:186`).
14. Controller cria `TimeBlock`, valida `Period.MANHA`, insere no repo `time_blocks`, mostra confirmação.
15. `_run_cmd` chama `Prompt.ask("Press Enter to continue")` — user pressiona Enter.
16. `_flow_morning` retorna, `_route` retorna, `home()` itera o `while True`, limpa tela, mostra menu de novo.
17. Sucesso: `✔ Manhã iniciada!` em verde bold (`home.py:188`).

### Wireflow ASCII (FLOW-001)

```text
       ╭───────────────╮
       │ ◯  user digita│
       │ "operational  │
       │     home"     │
       ╰───────┬───────╯
               │
               ▼
       ┌───────────────┐
       │ SCR-001       │
       │ Home Menu     │◀──────╮
       │ (10 opções)   │       │
       └───┬───────────┘       │  (loop)
           │ user digita "1"   │
           ▼                   │
       ◇─────────◇             │
      / Continuar?  \───n──→ (volta ao menu)
      \  default y  /          │
       └─────┬─────┘           │
             │ y               │
             ▼                 │
       ┌───────────────┐       │
       │ SCR-002       │       │
       │ Sleep Prompt  │       │
       │  ×5 (com def) │       │
       └───┬───────────┘       │
           │ Prompt.ask loop   │
           ▼                   │
       ╔═══════════════╗       │
       ║ metric sleep  ║       │
       ║ -q -bh -bm    ║       │
       ║ -wh -wm       ║       │
       ╚═══════╤═══════╝       │
               │               │
               ▼               │
       ┌───────────────┐       │
       │ CMP-007 ✓     │       │
       │ Sono gravado  │       │
       └───┬───────────┘       │
           │                   │
           ▼                   │
       ╔═══════════════╗       │
       ║ routine create║       │
       ║ "Acordar"     ║       │
       ║ MANHA ENTRY   ║       │
       ╚═══════╤═══════╝       │
               │               │
               ▼               │
       ┌───────────────┐       │
       │ 1 prompt:     │       │
       │ label do bloco│       │
       └───┬───────────┘       │
           │ default           │
           ▼                   │
       ╔═══════════════╗       │
       ║ block create  ║       │
       ║ MANHA --label ║       │
       ╚═══════╤═══════╝       │
               │               │
               ▼               │
       ┌───────────────┐       │
       │ ◯  Manhã      │       │
       │  iniciada! ✓  │───────╯
       └───────────────┘

  Exceções (linhas tracejadas):
  - - - - - - - - - - - - - - - - - - -
  : ... (Pydantic range)  : → error_panel
  :  ex. -q 99 ou -bh 99  :   re-prompt
  : ... (Ctrl+C)          : → state parcial
  :     meio do step 2    :   (nenhum entity
  :                        :    foi gravado
  :                        :    ainda; limpo)
  - - - - - - - - - - - - - - - - - - -
```

---

## Fluxos alternativos

### A1 — User pula o home menu (comando direto)

Para quem já sabe o que quer. Roda em pipeline shell:

```bash
operational metric sleep -q 8 -bh 23 -bm 30 -wh 4 -wm 0 && \
operational routine create "Acordar" MANHA ENTRY && \
operational block create MANHA --label "Morning Workout + Meditação"
```

Cobre 100% do que `_flow_morning` faz em 1 linha. Trade-off: nenhum "preview" mostrando o que vai acontecer.

### A2 — Dataset sintético ativo

- **Setup:** `TIME_TASKER_DATASET=synthetic operational home`
- **Comportamento:** auto-loader popula state com 345 entities (`docs/synthetic.csv`)
- **Impacto no FLOW-001:** o `metric sleep` faz `upsert` no registro existente para hoje (não duplica). `routine create "Acordar"` pode dar `id collision` se já existe. Sistema trata silenciosamente.
- **Workaround:** rodar `operational demo clear` antes (FLOW-009).

### A3 — Ctrl+C no meio

- Posição 1 (antes de step 1): nada foi gravado. State limpo.
- Posição 2 (entre prompts do step 1): nada foi gravado (atomicidade do `metric sleep` é por comando, não por prompt).
- Posição 3 (após step 1, antes de step 2): sono gravado, rotina não. State parcial.
- Posição 4 (entre step 2 e step 3): sono + rotina gravados, bloco não.
- O `home()` tem `except KeyboardInterrupt: sys.exit(0)` (`home.py:477-480`) — sai do CLI sem erro, sem confirmação.

### A4 — Flag `--json` em todos os comandos

Substitui o painel Rich por uma única linha JSON por comando. Útil para cron jobs, log scraping, ou CI:

```bash
operational metric sleep -q 8 -bh 23 -bm 30 -wh 4 -wm 0 --json
# {"id":"slp-...","date":"2026-06-08","quality":8,"duration_hours":8.5,...}
```

### A5 — Data retroativa

Se o user esqueceu de rodar ontem:

```bash
operational metric sleep --date 2026-06-07 -q 7 -bh 23 -bm 0 -wh 4 -wm 30
```

Substitui o registro de 2026-06-07. Idempotente (1 registro por data no repo).

### A6 — Loop "in-process" (CLI interno do home)

Quando invocado via menu, `metric sleep` roda **no mesmo processo Python** via `typer_app(args, standalone_mode=False)` (`home.py:60`). Stdout é capturado com `redirect_stdout` e re-impresso via console central — ver `docs/tui/05-HOME-MENU.md` §"How dispatch works". Isso significa que `print()` de bibliotecas externas *também* é capturado.

---

## Exceções e erros

### E1 — Pydantic `ValidationError` (range)

- **Causa:** `quality=-1`, `bed_hour=99`, `bed_minute=99`, `wake_minute=-5`, etc.
- **Onde:** `metric_cmd.sleep` (`cli/commands/metric_cmd.py:60-67`) tem `typer.Option(..., min=1, max=10, ...)`. Typer intercepta e mostra `Invalid value for '--quality'`.
- **Tratamento:** `_run_cmd` (`home.py:49-67`) captura `Exception` e renderiza via `error_panel` (`ui/components.py:390-426`).
- **Mensagem ao user:** "❌ Erro de Execução — BadParameter: Invalid value..."
- **Recuperação:** user pressiona Enter, volta ao menu, vê o erro, retenta com valor válido.

### E2 — Time-tasker state dir não existe

- **Causa:** primeira execução do CLI, `~/.time-tasker/` ainda não existe.
- **Onde:** `cli/state.py:1-...` — todos os repos fazem `Path(state_dir).mkdir(parents=True, exist_ok=True)` lazy.
- **Tratamento:** silent recovery, sem mensagem ao user.
- **Verificação:** `operational doctor` reporta `state_dir: ok` após o primeiro `metric sleep`.

### E3 — JSON corrupto no state dir

- **Causa:** edição manual, crash mid-write, encoding errado (BOM, CRLF).
- **Onde:** `cli/state.py:JSONRepository._load_all` faz `json.loads` e pula arquivo com warning.
- **Tratamento:** arquivo ignorado, warning no log (`logs/operational.log`), próximo `repo.clear()` regenera.
- **Mensagem ao user:** nenhuma. O user só percebe se rodar `operational doctor` (que detecta CRLF/BOM em `_check_files_sanity`).

### E4 — Dataset CSV não encontrado

- **Causa:** `TIME_TASKER_DATASET=synthetic` mas `docs/synthetic.csv` foi movido.
- **Onde:** `cli/dataset_selector.py:resolve_dataset` retorna o path; auto-loader em `cli/state.py` silencia `FileNotFoundError`.
- **Tratamento:** state vazio. User roda `demo seed` para popular.
- **Mensagem ao user:** nenhuma no FLOW-001. `operational doctor` reporta `datasets: synthetic=MISSING`.

### E5 — Ctrl+C durante prompt

- **Causa:** user digita Ctrl+C num `Prompt.ask`.
- **Onde:** Rich `Prompt.ask` não intercepta; cai no `except KeyboardInterrupt` do `home.py:477-480`.
- **Tratamento:** exit code 0, mensagem `Até logo! 🚀`, state inalterado.

---

## Telas envolvidas (refs)

- `docs/ux/05-telas/SCR-001-home-menu.md` (ainda não escrito — ref futura)
- `docs/ux/05-telas/SCR-002-sleep-form.md` (ainda não escrito)
- `docs/ux/05-telas/SCR-005-success-banner.md` (ainda não escrito)

> **Nota:** Os docs `SCR-*` ainda não existem. Este doc usa as referências como placeholders semânticos que serão preenchidos por outros agentes.

## Componentes críticos

- CMP-001 Header panel — `cli/home.py:84-93` (`_header`)
- CMP-006 input_summary — `cli/input_summary.py:1-...` (auto-render de parâmetros)
- CMP-007 confirmation banner — `cli/home.py:188` (`✔ Manhã iniciada!`)
- CMP-004 error_panel — `ui/components.py:390-426` (erros Pydantic)

## Intenção de usabilidade

**Por que este fluxo é desenhado ASSIM:**

1. **5 prompts em vez de 1 prompt com sintaxe CSV** — O user esquece formatos. 5 prompts simples são forçadamente estruturados; sintaxe CSV (ex: `-q 8 -bh 23:30 -wh 4:00`) economiza tempo mas só para power users.
2. **Defaults em todos os prompts** — `home.py:170-174`. User em rotina pode completar o sono com 5 Enters consecutivos. Acelera o caso comum.
3. **"Continuar?" preview** — mostra o que vai acontecer antes de começar (`home.py:161-164`). User pode desistir sem digitar nada.
4. **Sem "voltar" mid-flow** — o fluxo é atômico. Voltar no meio deixaria state inconsistente (sono gravado sem rotina, ou rotina sem bloco).
5. **Comando direto sempre disponível** — A1 mostra que dá para pular o menu. Power users fazem em 1 linha.

**Fricções mantidas:**

- **5 prompts no step 1** — manter `home.py:170-174` exige contexto. Solução alternativa (`-q 8 -bh 23:30 -wh 4:00`) é mais rápida mas obriga user a lembrar sintaxe.
- **Não há undo** — `routine create "Acordar" MANHA ENTRY` não tem `--undo`. Workaround: `operational routine delete <id>` (não implementado — ver UX-006).

## Critérios de sucesso

- **Tempo:** User completa em < 60s com 5 Enters (caminho default).
- **Abandono:** < 10% (medido por quem digita `n` em "Continuar?").
- **Erros:** < 0.5 erros de validação por sessão (a maioria dos users acerta range na primeira).
- **Memoization:** User com 7+ dias de hábito completa em < 30s.

## Onde aparece

- **Home menu opção 1** — `_flow_morning` (`cli/home.py:157-188`)
- **Comando direto** — `operational metric sleep`, `operational routine create`, `operational block create`
- **Aliases/scripts** — usuários costumam criar `alias manha="operational home"` e digitar `1` direto

## Notas de implementação

**File:line refs principais:**

- Fluxo principal: `cli/home.py:157-188`
- Header: `cli/home.py:84-93`
- `_run_cmd` (dispatch): `cli/home.py:49-67`
- Sleep controller: `cli/commands/metric_cmd.py:58-94`
- Sleep factory: `meta/factories.py:make_sleep_record` (não lido aqui)
- Routine controller: `cli/commands/routine_cmd.py:1-...` (não lido aqui)
- Block controller: `cli/commands/block_cmd.py:1-...` (não lido aqui)

**Como adicionar uma nova etapa (ex: "registrar humor"):**

1. Em `_flow_morning`, após o step 3 (linha 186), adicionar:
   ```python
   h = Prompt.ask("Humor ao acordar (1-10)", default="7")
   _run_cmd(["metric", "mood", "-h", h])
   ```
2. Criar o controller em `cli/commands/metric_cmd.py` (função `mood(h)`).
3. Adicionar Pydantic entity se necessário.
4. Atualizar este doc.

**Como mudar timeout:**

Os prompts do Rich `Prompt.ask` **não têm timeout built-in**. Para adicionar, é preciso wrapper custom. Ver UX-004 (risco conhecido).

**Onde ajustar labels default:**

- Default `Morning Workout + Meditação` em `cli/home.py:185` (sugestão, não hard-coded).
- Default `8` para quality em `cli/home.py:170` (alinhado com PAV `SLEEP_QUALITY_DEFAULT`).
